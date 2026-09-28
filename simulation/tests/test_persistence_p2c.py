import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import World
from ate_sim.incremental_store import (
    RecordChange, StoreConflictError, StoreFormatError, StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    COLLECTION_LAYOUT,
    IDENTITY_DELTAS,
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    IDENTITY_STORAGE_CURRENT,
    META,
    SCHEMA,
    WorldCodec,
    _write_legacy_snapshot,
    convert_legacy_snapshot,
    read_snapshot,
    write_snapshot,
)
from ate_sim.persistence_tracking import bind_snapshot

RULES = "stage-0.5-p2c-tests"


def open_store(path):
    return TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )


def current_rows(store):
    return store.read_records(
        IDENTITY_LINKS, expected_record_schema=IDENTITY_LINK_SCHEMA
    )


def test_default_snapshot_uses_only_current_identity_authority(tmp_path):
    shared = {"value": 1}
    world = World(901)
    world.currency.wallets = {1: {"a": shared, "b": shared}}
    path = tmp_path / "current.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with open_store(path) as store:
        manifest = store.read_record(META, "manifest")
        assert set(manifest) == {"schema", "collections", "identity_storage"}
        assert manifest["identity_storage"] == IDENTITY_STORAGE_CURRENT
        namespaces = set(store.head_metadata()["namespaces"])
        assert IDENTITY_LINKS in namespaces
        assert IDENTITY_DELTAS not in namespaces
        rows = current_rows(store)
        assert len(rows) == 1

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["a"] is restored.currency.wallets[1]["b"]


@pytest.mark.parametrize("saves", [20, 200])
def test_current_links_do_not_accumulate_alias_history(tmp_path, saves):
    world = World(902)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    path = tmp_path / f"toggle-{saves}.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    max_read_bytes = 0
    max_write_bytes = 0
    with bind_snapshot(world, path, rules_id=RULES) as session:
        for i in range(saves):
            row = world.currency.wallets[1]
            if i % 2 == 0:
                row["b"] = row["a"]
            else:
                del row["b"]
            session.reset_diagnostics()
            session.save()
            save_stats = session.diagnostics()
            max_write_bytes = max(max_write_bytes, save_stats.payload_write_bytes)

            session.reset_diagnostics()
            rows = current_rows(session.store)
            read_stats = session.diagnostics()
            expected = 1 if i % 2 == 0 else 0
            assert len(rows) == expected
            assert read_stats.payload_reads == expected
            max_read_bytes = max(max_read_bytes, read_stats.payload_read_bytes)
            namespaces = set(session.store.head_metadata()["namespaces"])
            assert IDENTITY_LINKS in namespaces
            assert IDENTITY_DELTAS not in namespaces

        session.reset_diagnostics()
        generation = session.generation
        assert session.save() == generation
        assert session.diagnostics().payload_writes == 0

    # Current identity reads remain bounded by live rows, not lifetime edits.
    assert max_read_bytes < 4096
    assert max_write_bytes < 20000

    restored = read_snapshot(path, rules_id=RULES)
    assert "b" not in restored.currency.wallets[1]
    with bind_snapshot(restored, path, rules_id=RULES) as session:
        restored.currency.wallets[1]["b"] = restored.currency.wallets[1]["a"]
        session.save()
        assert len(current_rows(session.store)) == 1
        assert IDENTITY_DELTAS not in set(session.store.head_metadata()["namespaces"])
    final = read_snapshot(path, rules_id=RULES)
    assert final.currency.wallets[1]["a"] is final.currency.wallets[1]["b"]


def test_multi_owner_and_repeated_same_target_collapse_to_final_state(tmp_path):
    world = World(903)
    world.currency.wallets = {
        1: {"a": {"value": 1}, "b": {"value": 2}},
        2: {},
    }
    path = tmp_path / "collapse.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(world, path, rules_id=RULES) as session:
        left = world.currency.wallets[1]
        other = world.currency.wallets[2]
        left["b"] = left["a"]
        left["b"] = {"value": 22}
        left["b"] = left["a"]
        other["x"] = left["a"]
        del other["x"]
        other["x"] = left["a"]
        session.save()
        rows = current_rows(session.store)
        assert len(rows) == 2
        assert len({target for target, _owner, _schema in rows}) == 2

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["a"] is restored.currency.wallets[1]["b"]
    assert restored.currency.wallets[2]["x"] is restored.currency.wallets[1]["a"]
    restored.currency.wallets[2]["x"]["value"] = 9
    assert restored.currency.wallets[1]["b"]["value"] == 9


def test_current_alias_anchor_replacement_is_atomic_final_state(tmp_path):
    shared = {"value": 1}
    world = World(904)
    world.currency.wallets = {1: {"a": shared, "b": shared}}
    path = tmp_path / "anchor.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(world, path, rules_id=RULES) as session:
        row = world.currency.wallets[1]
        del row["a"]
        row["c"] = row["b"]
        session.save()
        rows = current_rows(session.store)
        assert len(rows) == 1

    restored = read_snapshot(path, rules_id=RULES)
    row = restored.currency.wallets[1]
    assert "a" not in row
    assert row["b"] is row["c"]


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_local_alias_save_writes_only_affected_current_link(tmp_path, groups):
    world = World(905)
    for i in range(groups):
        shared = {"value": i}
        world.currency.wallets[i] = {"a": shared, "b": shared}
    path = tmp_path / f"groups-{groups}.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(world, path, rules_id=RULES) as session:
        session.reset_diagnostics()
        world.currency.wallets[0]["c"] = world.currency.wallets[0]["a"]
        session.save()
        stats = session.diagnostics()
        generation = session.generation
        changed_identity = session.store.db.execute(
            "SELECT COUNT(*),COALESCE(SUM(LENGTH(payload)),0) "
            "FROM records WHERE namespace=? AND last_changed_generation=?",
            (IDENTITY_LINKS, generation),
        ).fetchone()
        assert changed_identity[0] == 1
        assert changed_identity[1] < 4096
        assert stats.payload_writes == 2
        assert stats.payload_write_bytes < 20000
        assert len(current_rows(session.store)) == groups + 1

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[0]["a"] is restored.currency.wallets[0]["b"]
    assert restored.currency.wallets[0]["b"] is restored.currency.wallets[0]["c"]


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_current_identity_and_world_edits_fail_or_ack_atomically(
    tmp_path, monkeypatch, phase
):
    world = World(906)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    path = tmp_path / f"atomic-{phase}.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(world, path, rules_id=RULES) as session:
        world.currency.wallets[1]["b"] = world.currency.wallets[1]["a"]
        world.currency.wallets[2] = {"iron": 2}
        original = session.store._phase_hook

        def fail(current):
            if current == phase:
                raise OSError("injected P2C commit failure")
            return original(current)

        monkeypatch.setattr(session.store, "_phase_hook", fail)
        if phase == "before_commit":
            with pytest.raises(OSError, match="injected"):
                session.save()
            old = read_snapshot(path, rules_id=RULES)
            assert list(old.currency.wallets) == [1]
            assert "b" not in old.currency.wallets[1]
            monkeypatch.setattr(session.store, "_phase_hook", original)
            assert session.save() == 2
        else:
            assert session.save() == 2
            monkeypatch.setattr(session.store, "_phase_hook", original)

        assert session.save() == 2
        rows = current_rows(session.store)
        assert len(rows) == 1
        assert IDENTITY_DELTAS not in set(session.store.head_metadata()["namespaces"])

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["a"] is restored.currency.wallets[1]["b"]
    assert restored.currency.wallets[2] == {"iron": 2}


def _writer_death_script():
    return r"""
import os, signal, sys
from ate_sim.persistence_adapters import read_snapshot
from ate_sim.persistence_tracking import bind_snapshot
path, rules = sys.argv[1], sys.argv[2]
world = read_snapshot(path, rules_id=rules)
session = bind_snapshot(world, path, rules_id=rules)
world.currency.wallets[1]['b'] = world.currency.wallets[1]['a']
world.currency.wallets[2] = {'iron': 2}
session.store._phase_hook = (
    lambda phase: os.kill(os.getpid(), signal.SIGKILL)
    if phase == 'during_writes' else None
)
session.save()
"""


def test_subprocess_writer_death_never_publishes_mixed_identity_state(tmp_path):
    world = World(907)
    world.currency.wallets = {1: {"a": {"value": 1}}}
    path = tmp_path / "death.sqlite"
    write_snapshot(world, path, rules_id=RULES)
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = (
        str(root) + os.pathsep + str(root / "simulation")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [sys.executable, "-c", _writer_death_script(), str(path), RULES],
        env=env,
    )
    assert proc.returncode != 0
    restored = read_snapshot(path, rules_id=RULES)
    assert list(restored.currency.wallets) == [1]
    assert "b" not in restored.currency.wallets[1]
    with open_store(path) as store:
        store.verify_all()
        assert len(current_rows(store)) == 0


def test_genuine_legacy_p2b_conversion_preserves_source_and_continuation(tmp_path):
    world = Simulation(generate_world(908, mature=False)).run(1)
    world.currency.wallets[-999] = {"a": {"value": 1}}
    source = tmp_path / "legacy.sqlite"
    _write_legacy_snapshot(world, source, rules_id=RULES)

    with bind_snapshot(world, source, rules_id=RULES) as session:
        for i in range(13):
            row = world.currency.wallets[-999]
            if i % 2 == 0:
                row["b"] = row["a"]
            else:
                del row["b"]
            row["a"]["value"] = i
            if i == 0:
                world.currency.wallets[-998] = {"iron": 2}
            session.save()
        assert len(session.store.read_records(IDENTITY_DELTAS)) == 13
        assert session.store.read_record(META, COLLECTION_LAYOUT)

    with open_store(source) as store:
        manifest = store.read_record(META, "manifest")
        assert set(manifest) == {"schema", "collections", "identity_links"}
        assert IDENTITY_LINKS not in set(store.head_metadata()["namespaces"])

    before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "converted.sqlite"
    convert_legacy_snapshot(source, destination, rules_id=RULES)
    after_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert before_hash == after_hash

    legacy = read_snapshot(source, rules_id=RULES)
    converted = read_snapshot(destination, rules_id=RULES)
    assert legacy.digest() == converted.digest()
    assert legacy.currency.wallets[-999]["a"] is legacy.currency.wallets[-999]["b"]
    assert converted.currency.wallets[-999]["a"] is converted.currency.wallets[-999]["b"]

    with open_store(destination) as store:
        manifest = store.read_record(META, "manifest")
        assert manifest["identity_storage"] == IDENTITY_STORAGE_CURRENT
        namespaces = set(store.head_metadata()["namespaces"])
        assert IDENTITY_LINKS in namespaces
        assert IDENTITY_DELTAS not in namespaces

    assert Simulation(legacy).run(1).digest() == Simulation(converted).run(1).digest()


def test_conversion_rejects_current_source_and_existing_destination(tmp_path):
    source = tmp_path / "current.sqlite"
    write_snapshot(World(909), source, rules_id=RULES)
    with pytest.raises(StoreFormatError, match="not a legacy"):
        convert_legacy_snapshot(source, tmp_path / "dest.sqlite", rules_id=RULES)

    legacy = tmp_path / "legacy.sqlite"
    _write_legacy_snapshot(World(910), legacy, rules_id=RULES)
    destination = tmp_path / "exists.sqlite"
    destination.write_text("keep")
    with pytest.raises(FileExistsError):
        convert_legacy_snapshot(legacy, destination, rules_id=RULES)
    assert destination.read_text() == "keep"


@pytest.mark.parametrize("damage", ["unknown_mode", "mixed_manifest", "mixed_namespace"])
def test_current_identity_mode_rejects_unknown_or_mixed_authorities(tmp_path, damage):
    path = tmp_path / f"{damage}.sqlite"
    write_snapshot(World(911), path, rules_id=RULES)
    with open_store(path) as store:
        manifest = store.read_record(META, "manifest")
        head = store.head_metadata()
        changes = []
        if damage == "unknown_mode":
            manifest["identity_storage"] = "future/v99"
            changes.append(RecordChange(META, "manifest", manifest))
        elif damage == "mixed_manifest":
            manifest["identity_links"] = []
            changes.append(RecordChange(META, "manifest", manifest))
        else:
            head["namespaces"] += (IDENTITY_DELTAS,)
            changes.append(RecordChange(
                IDENTITY_DELTAS, 0,
                ("identity-delta/v1", (), ()),
            ))
        store.commit(store.generation, changes, (), head)
    with pytest.raises(StoreFormatError):
        read_snapshot(path, rules_id=RULES)


def test_current_identity_wrong_schema_invalid_path_and_corrupt_payload_rejected(tmp_path):
    cases = ("schema", "path", "corrupt")
    for index, case in enumerate(cases):
        world = World(920 + index)
        shared = {"value": 1}
        world.currency.wallets = {1: {"a": shared, "b": shared}}
        path = tmp_path / f"bad-{case}.sqlite"
        write_snapshot(world, path, rules_id=RULES)
        with open_store(path) as store:
            rows = current_rows(store)
            target, owner, _schema = rows[0]
            if case == "schema":
                store.commit(
                    store.generation,
                    [RecordChange(
                        IDENTITY_LINKS, target, owner,
                        record_schema=IDENTITY_LINK_SCHEMA + 1,
                    )],
                    (),
                    store.head_metadata(),
                )
            elif case == "path":
                bad_target = (("field", "does_not_exist"),)
                store.commit(
                    store.generation,
                    [RecordChange(IDENTITY_LINKS, target, delete=True),
                     RecordChange(IDENTITY_LINKS, bad_target, owner)],
                    (),
                    store.head_metadata(),
                )
            else:
                store.db.execute(
                    "UPDATE records SET payload=? WHERE namespace=?",
                    (b"corrupt", IDENTITY_LINKS),
                )
                store.db.commit()
        with pytest.raises((StoreFormatError, StoreIntegrityError)):
            read_snapshot(path, rules_id=RULES)


def test_current_identity_stale_writer_and_backup_relocation(tmp_path):
    shared = {"value": 1}
    world = World(930)
    world.currency.wallets = {1: {"a": shared, "b": shared}}
    source = tmp_path / "source.sqlite"
    backup = tmp_path / "elsewhere" / "backup.sqlite"
    write_snapshot(world, source, rules_id=RULES)

    first = open_store(source)
    second = open_store(source)
    try:
        head = first.head_metadata()
        rows = current_rows(first)
        target, owner, _schema = rows[0]
        assert first.commit(
            first.generation,
            [RecordChange(IDENTITY_LINKS, target, delete=True)],
            (),
            head,
        ) == 2
        with pytest.raises(StoreConflictError):
            second.commit(
                1,
                [RecordChange(IDENTITY_LINKS, target, owner)],
                (),
                head,
            )
        first.backup(backup)
    finally:
        second.close()
        first.close()

    source.unlink()
    restored = read_snapshot(backup, rules_id=RULES)
    assert "b" in restored.currency.wallets[1]
    assert restored.currency.wallets[1]["a"] is not restored.currency.wallets[1]["b"]
