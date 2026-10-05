import pickle

import pytest

from ate_sim import checkpoint
from ate_sim.core import Layer, World
from ate_sim.incremental_store import (
    StoreConflictError,
    StoreError,
    StoreFormatError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    bind_snapshot,
    read_snapshot,
    write_snapshot,
)
from ate_sim.persistence_events import CHUNK_SIZE
from ate_sim.persistence_session import open_world_session, write_cold_snapshot
import ate_sim.core as core
import ate_sim.persistence_adapters as adapters
import ate_sim.persistence_lifecycle as lifecycle

from simulation.tests.test_persistence_session_open import (
    RULES,
    build_cold_path,
)


def _alias_path(first_tail):
    event_parent = (
        ("field", "events"),
        ("index", first_tail),
        ("field", "data"),
        ("key", "shared"),
    )
    wallet_parent = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "shared"),
    )
    event_child = event_parent + (("key", "child"),)
    wallet_child = wallet_parent + (("key", "child"),)
    return event_parent, wallet_parent, event_child, wallet_child


def test_detach_requires_explicit_materialization_without_side_effect(tmp_path):
    path, expected = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=1, tail_count=2
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        generation = session.generation
        with pytest.raises(StoreError, match="materialize_history=True"):
            session.detach()
        assert session.cold_state == "active"
        assert session.generation == generation == expected["generation"]
        assert session.world.events is log
        assert not session.store._closed
    finally:
        session.close()


def test_materializing_detach_preserves_world_tail_aliases_edits_and_portability(
    tmp_path,
):
    disk_segments = 1
    pending_chunks = 1
    first_tail = (disk_segments + pending_chunks) * CHUNK_SIZE
    event_parent, wallet_parent, event_child, wallet_child = _alias_path(
        first_tail
    )
    path, expected = build_cold_path(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=2,
        wallets={1: {"shared": {"child": [1, 2, 3]}}},
        tail_payload={"shared": {"child": [1, 2, 3]}},
        identity_links=[
            (event_parent, wallet_parent),
            (wallet_child, event_child),
        ],
    )
    session = open_world_session(path, rules_id=RULES)
    old_log = session.world.events
    tail = old_log[first_tail]
    current = session.world.currency.wallets[1]["shared"]
    old_wrapper = current["child"]
    assert tail.data["shared"] is current
    old_wrapper.append(4)
    world = session.world

    detached = session.detach(materialize_history=True)
    assert detached is world
    assert session.cold_state == "closed"
    assert detached.events is not old_log
    assert detached.events._disk_prefix is None
    stats = detached.events.storage_stats()
    assert stats["disk_events"] == 0
    assert stats["pending_sealed_events"] == expected["F"]
    assert stats["tail_events"] == expected["N"] - expected["F"]
    assert detached.events[first_tail] is tail
    assert detached.currency.wallets[1]["shared"] is tail.data["shared"]
    assert detached.currency.wallets[1]["shared"]["child"] is (
        tail.data["shared"]["child"]
    )
    assert detached.currency.wallets[1]["shared"]["child"] == [1, 2, 3, 4]
    assert "_ate_persistence_lifetime" not in detached.__dict__
    assert "_ate_persistence_lifetime" not in detached.events.__dict__

    with pytest.raises(StoreError):
        len(old_log)
    with pytest.raises(StoreError):
        old_wrapper.append(5)

    data = checkpoint.dumps(detached)
    restored = checkpoint.loads(data)
    assert restored.digest() == detached.digest()
    restored_shared = restored.currency.wallets[1]["shared"]
    restored_tail = restored.events[first_tail]
    assert restored_shared is restored_tail.data["shared"]
    assert restored_shared["child"] is restored_tail.data["shared"]["child"]

    before = detached.next_event
    detached.emit("after-detach", Layer.REALITY)
    assert detached.next_event == before + 1
    session.close()


def test_detach_staging_failure_leaves_cold_session_usable(tmp_path, monkeypatch):
    path, _ = build_cold_path(
        tmp_path, disk_segments=2, pending_chunks=1, tail_count=2
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        alias = session.world.currency.wallets
        before = session.generation

        def fail(phase, _session):
            if phase == "before_publish":
                raise RuntimeError("detach staging fault")

        monkeypatch.setattr(lifecycle, "_lifecycle_phase", fail)
        with pytest.raises(RuntimeError, match="detach staging fault"):
            session.detach(materialize_history=True)

        assert session.cold_state == "active"
        assert session.generation == before
        assert session.world.events is log
        assert not session.store._closed
        session.world.currency.wallets[99] = {"value": 1}
        assert ("world.currency.wallets", 99) in session.dirty
        assert alias is session.world.currency.wallets
    finally:
        session.close()


def test_stale_detach_materializes_local_branch_without_touching_winner(tmp_path):
    source = World(991)
    source.currency.wallets[1] = {"value": 0}
    path = tmp_path / "stale-detach.sqlite"
    write_cold_snapshot(source, path, rules_id=RULES)
    winner = open_world_session(path, rules_id=RULES)
    loser = open_world_session(path, rules_id=RULES)
    try:
        start = winner.generation
        winner.world.currency.wallets[1]["value"] = 1
        loser.world.currency.wallets[1]["value"] = 2
        assert winner.save() == start + 1
        with pytest.raises(StoreConflictError):
            loser.save()
        assert loser.cold_state == "stale"

        local = loser.detach(materialize_history=True)
        assert local.currency.wallets[1]["value"] == 2
        local.currency.wallets[1]["value"] = 3

        winner.close()
        winner = open_world_session(path, rules_id=RULES)
        assert winner.world.currency.wallets[1]["value"] == 1
        assert winner.generation == start + 1
    finally:
        winner.close()
        loser.close()


def test_digest_guard_blocks_mutation_and_releases_after_failure(
    tmp_path, monkeypatch
):
    world = World(992)
    world.currency.wallets[1] = {"values": [1]}
    path = tmp_path / "digest-guard.sqlite"
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        original = core._digest_world_unchecked

        def fail_digest(_world):
            with pytest.raises(StoreError):
                alias.append(2)
            raise RuntimeError("digest fault")

        monkeypatch.setattr(core, "_digest_world_unchecked", fail_digest)
        with pytest.raises(RuntimeError, match="digest fault"):
            session.world.digest()
        assert session.cold_state == "active"
        assert alias == [1]

        monkeypatch.setattr(core, "_digest_world_unchecked", original)
        alias.append(2)
        assert alias == [1, 2]
    finally:
        session.close()


def test_checkpoint_and_direct_pickle_reject_cold_before_traversal(
    tmp_path, monkeypatch
):
    path, _ = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        prefix = session.world.events._disk_prefix
        reads = prefix.diagnostics().segment_reads

        monkeypatch.setattr(
            core,
            "_digest_world_unchecked",
            lambda _world: (_ for _ in ()).throw(
                AssertionError("digest must not run")
            ),
        )
        with pytest.raises(StoreError, match="detach"):
            checkpoint.dumps(session.world)

        target = tmp_path / "blocked.chk"
        with pytest.raises(StoreError, match="detach"):
            checkpoint.save(session.world, target)
        assert not target.exists()

        existing = tmp_path / "existing.chk"
        existing.write_bytes(b"keep")
        with pytest.raises(StoreError, match="detach"):
            checkpoint.save(session.world, existing)
        assert existing.read_bytes() == b"keep"

        with pytest.raises(StoreError, match="disk-backed EventLog"):
            pickle.dumps(session.world.events)
        assert prefix.diagnostics().segment_reads == reads
    finally:
        session.close()


def test_legacy_p2_entrypoints_reject_cold_before_scrub_or_audit(
    tmp_path, monkeypatch
):
    path, _ = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )

    monkeypatch.setattr(
        TransactionalStore,
        "verify_all",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("cold P2 rejection must precede verify_all")
        ),
    )
    with pytest.raises(StoreFormatError, match="open_world_session"):
        read_snapshot(path, rules_id=RULES)

    with pytest.raises(StoreFormatError, match="open_world_session"):
        bind_snapshot(World(993), path, rules_id=RULES)

    session = open_world_session(path, rules_id=RULES)
    try:
        monkeypatch.setattr(
            adapters,
            "_audit",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("cold write rejection must precede audit")
            ),
        )
        target = tmp_path / "legacy-write.sqlite"
        with pytest.raises(StoreFormatError, match="detach"):
            write_snapshot(session.world, target, rules_id=RULES)
        assert not target.exists()
    finally:
        session.close()
