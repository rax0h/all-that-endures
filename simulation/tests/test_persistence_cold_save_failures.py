import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys

import pytest

from ate_sim.core import Event, Layer, World
from ate_sim.engine import Simulation
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import (
    StoreConflictError,
    StoreError,
)
from ate_sim.persistence_events import CHUNK_SIZE, SEALED_EVENTS
from ate_sim.persistence_session import open_world_session, write_cold_snapshot
import ate_sim.persistence_cold_save as cold_save


RULES = "stage-0.5-p3b-cold-save-failure-tests"


def event(event_id, *, year=10, data=None):
    return Event(
        event_id,
        year,
        "cold-save-failure",
        Layer.REALITY,
        (),
        None,
        (),
        {"index": event_id} if data is None else data,
    )


def world_with_events(count, *, seed=74001):
    world = World(seed)
    world.year = 10
    log = EventLog()
    for event_id in range(1, count + 1):
        value = event(event_id)
        log.append(value)
        world.event_ids.add(event_id)
    world.events = log
    world.next_event = count + 1
    return world


@pytest.mark.parametrize("failure_phase", ["during_writes", "before_commit"])
def test_failure_before_commit_proves_old_and_preserves_retry(
    tmp_path, failure_phase
):
    path = tmp_path / "rollback.sqlite"
    world = World(1)
    world.currency.wallets[1] = {
        "values": [1],
        "mapping": {"a": 1},
        "items": {1, 2},
    }
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        generation = session.generation
        dirty = session.dirty

        def fail(phase):
            if phase == failure_phase:
                raise RuntimeError("injected rollback")

        session.store._phase_hook = fail
        with pytest.raises(RuntimeError, match="injected rollback"):
            session.save()

        assert session.cold_state == "active"
        assert session.generation == generation
        assert session.dirty == dirty
        assert alias == [1, 2]

        session.store._phase_hook = lambda _phase: None
        assert session.save() == generation + 1
    finally:
        session.close()

    restored = open_world_session(path, rules_id=RULES)
    try:
        assert restored.world.currency.wallets[1]["values"] == [1, 2]
    finally:
        restored.close()


def test_after_commit_lost_ack_is_resolved_without_second_generation(tmp_path):
    path = tmp_path / "lost-ack.sqlite"
    world = World(2)
    world.currency.wallets[1] = {"value": 1}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.currency.wallets[1]["value"] = 2
        before = session.generation

        def lose_ack(phase):
            if phase == "after_commit":
                raise RuntimeError("lost acknowledgement")

        session.store._phase_hook = lose_ack
        assert session.save() == before + 1
        assert session.cold_state == "active"
        assert session.generation == before + 1
        session.store._phase_hook = lambda _phase: None
        assert session.save() == before + 1
    finally:
        session.close()


def test_unreadable_ack_blocks_mutation_emit_step_and_log_until_resolve(
    tmp_path, monkeypatch
):
    path = tmp_path / "blocked.sqlite"
    world = World(3)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    sim = Simulation(session.world)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        before_generation = session.generation
        before_year = session.world.year
        before_next = session.world.next_event
        before_events = session.world.events._count

        original = cold_save._capture_successor
        calls = {"count": 0}

        def unreadable(*args, **kwargs):
            calls["count"] += 1
            raise StoreError("injected acknowledgement read failure")

        monkeypatch.setattr(cold_save, "_capture_successor", unreadable)
        with pytest.raises(StoreError):
            session.save()
        assert calls["count"] == 1
        assert session.cold_state == "recovery-required"
        assert session.generation == before_generation

        alias_before = list(alias)
        with pytest.raises(StoreError):
            alias.append(3)
        assert list(alias) == alias_before

        with pytest.raises(StoreError):
            session.world.emit("blocked", Layer.REALITY)
        assert session.world.next_event == before_next
        assert session.world.events._count == before_events

        with pytest.raises(StoreError):
            sim.step()
        assert session.world.year == before_year

        with pytest.raises(StoreError):
            len(session.world.events)

        monkeypatch.setattr(cold_save, "_capture_successor", original)
        assert session.resolve_save() == before_generation + 1
        assert session.cold_state == "active"
        assert alias == [1, 2]
    finally:
        session.close()


def test_unreadable_initial_ack_can_resolve_proven_durable_old(
    tmp_path, monkeypatch
):
    path = tmp_path / "durable-old.sqlite"
    world = World(31)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        before = session.generation
        original_capture = cold_save._capture_successor

        session.store._phase_hook = (
            lambda phase: (_ for _ in ()).throw(
                RuntimeError("commit never started")
            )
            if phase == "before_transaction" else None
        )
        monkeypatch.setattr(
            cold_save,
            "_capture_successor",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                StoreError("ack unreadable")
            ),
        )
        with pytest.raises(StoreError, match="uncertain"):
            session.save()

        assert session.cold_state == "recovery-required"
        assert session.generation == before
        assert session.store.generation == before
        frozen = list(alias)
        with pytest.raises(StoreError):
            alias.pop()
        assert list(alias) == frozen

        session.store._phase_hook = lambda _phase: None
        monkeypatch.setattr(cold_save, "_capture_successor", original_capture)
        assert session.resolve_save() == before
        assert session.cold_state == "active"
        assert session.dirty
        assert session.save() == before + 1
    finally:
        session.close()


def test_publication_failure_before_adoption_resolves_once(
    tmp_path, monkeypatch
):
    path = tmp_path / "before-adoption.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        tail_identity = id(log._tail)
        log.seal_before(11)
        before = session.generation

        def fail_before_adoption(phase, _session, _plan):
            if phase == "before_adoption":
                raise RuntimeError("before adoption")

        monkeypatch.setattr(
            cold_save, "_cold_save_phase", fail_before_adoption
        )
        with pytest.raises(RuntimeError, match="before adoption"):
            session.save()

        assert session.cold_state == "recovery-required"
        assert session._cold_publication_phase == "prepared"
        assert log._disk_count == 0
        assert id(log._tail) == tail_identity

        monkeypatch.setattr(
            cold_save, "_cold_save_phase",
            lambda _phase, _session, _plan: None,
        )
        assert session.resolve_save() == before + 1
        assert session.resolve_save() == before + 1
        assert log._disk_count == CHUNK_SIZE
        assert id(log._tail) == tail_identity
    finally:
        session.close()


def test_publication_failure_after_adoption_resolves_idempotently(
    tmp_path, monkeypatch
):
    path = tmp_path / "adoption.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        tail_identity = id(log._tail)
        log.seal_before(11)
        before = session.generation
        fired = {"value": False}

        def fail_after_adoption(phase, _session, _plan):
            if phase == "after_adoption" and not fired["value"]:
                fired["value"] = True
                raise RuntimeError("after adoption")

        monkeypatch.setattr(
            cold_save, "_cold_save_phase", fail_after_adoption
        )
        with pytest.raises(RuntimeError, match="after adoption"):
            session.save()

        assert session.cold_state == "recovery-required"
        assert session._cold_publication_phase == "adopted"
        assert session.world.events is log
        assert id(log._tail) == tail_identity
        assert log._disk_count == CHUNK_SIZE

        monkeypatch.setattr(
            cold_save, "_cold_save_phase",
            lambda _phase, _session, _plan: None,
        )
        assert session.resolve_save() == before + 1
        assert session.cold_state == "active"
        assert session.resolve_save() == before + 1
        assert log._disk_count == CHUNK_SIZE
        assert session.generation == before + 1
    finally:
        session.close()


def test_stale_writer_with_equal_values_and_later_head_cannot_publish(tmp_path):
    path = tmp_path / "stale.sqlite"
    world = World(4)
    world.currency.wallets[1] = {"value": 0}
    write_cold_snapshot(world, path, rules_id=RULES)
    left = open_world_session(path, rules_id=RULES)
    right = open_world_session(path, rules_id=RULES)
    try:
        start = left.generation
        left.world.currency.wallets[1]["value"] = 1
        right.world.currency.wallets[1]["value"] = 1
        assert left.save() == start + 1

        left.world.currency.wallets[1]["value"] = 2
        assert left.save() == start + 2

        with pytest.raises(StoreConflictError):
            right.save()
        assert right.cold_state == "stale"
        retained = right.world.currency.wallets[1]
        before = dict(retained)
        with pytest.raises(StoreError):
            retained["value"] = 3
        assert dict(retained) == before
    finally:
        left.close()
        right.close()


def test_direct_store_close_rejects_mutation_emit_and_simulation_before_change(
    tmp_path,
):
    path = tmp_path / "direct-close.sqlite"
    world = World(5)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    alias = session.world.currency.wallets[1]["values"]
    before_next = session.world.next_event
    before_count = session.world.events._count
    before_alias = list(alias)
    session.store.close()

    with pytest.raises(StoreError):
        alias.append(2)
    assert list(alias) == before_alias

    with pytest.raises(StoreError):
        session.world.emit("closed", Layer.REALITY)
    assert session.world.next_event == before_next
    assert session.world.events._count == before_count

    with pytest.raises(StoreError):
        Simulation(session.world)

    session.close()
    assert session.cold_state == "closed"


def test_preparing_state_blocks_reentrant_operations_and_mutation(
    tmp_path, monkeypatch
):
    path = tmp_path / "reentrant.sqlite"
    world = World(6)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        results = {}

        def probe(phase, _session, _plan):
            if phase != "before_commit_call":
                return
            for name, call in (
                ("save", session.save),
                ("resolve", session.resolve_save),
                ("close", session.close),
                ("mutation", lambda: alias.append(3)),
            ):
                try:
                    call()
                except StoreError:
                    results[name] = "blocked"
                else:
                    results[name] = "allowed"

        monkeypatch.setattr(cold_save, "_cold_save_phase", probe)
        generation = session.save()
        assert generation == session.generation
        assert results == {
            "save": "blocked",
            "resolve": "blocked",
            "close": "blocked",
            "mutation": "blocked",
        }
        assert alias == [1, 2]
    finally:
        session.close()


def test_save_inside_current_people_scope_fails_before_preparation(tmp_path):
    path = tmp_path / "scope.sqlite"
    write_cold_snapshot(World(7), path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        with session.world.current_people_scope():
            with pytest.raises(StoreError, match="current_people_scope"):
                session.save()
        assert session.cold_state == "active"
    finally:
        session.close()



def _writer_death_script():
    return r'''
import os, signal, sys
from ate_sim.persistence_session import open_world_session
path, rules, phase = sys.argv[1], sys.argv[2], sys.argv[3]
session = open_world_session(path, rules_id=rules)
shared = session.world.currency.wallets[1]["left"]
shared["value"] = 2
session.world.events.seal_before(11)
session.store._phase_hook = (
    lambda p: os.kill(os.getpid(), signal.SIGKILL)
    if p == phase else None
)
session.save()
'''


@pytest.mark.parametrize(
    "phase,published",
    [
        ("during_writes", False),
        ("before_commit", False),
        ("after_commit", True),
    ],
)
def test_writer_process_death_reopens_exact_old_or_new_partition(
    tmp_path, phase, published
):
    world = world_with_events(CHUNK_SIZE, seed=55)
    shared = {"value": 1}
    world.currency.wallets[1] = {"left": shared, "right": shared}
    path = tmp_path / f"death-{phase}.sqlite"
    write_cold_snapshot(world, path, rules_id=RULES)

    baseline = open_world_session(path, rules_id=RULES)
    start_generation = baseline.generation
    baseline.close()

    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = (
        str(root) + os.pathsep + str(root / "simulation")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _writer_death_script(),
            str(path),
            RULES,
            phase,
        ],
        env=env,
    )
    assert proc.returncode != 0

    restored = open_world_session(path, rules_id=RULES)
    try:
        assert restored.generation == start_generation + int(published)
        wallet = restored.world.currency.wallets[1]
        assert wallet["left"] is wallet["right"]
        assert wallet["left"]["value"] == (2 if published else 1)

        stats = restored.world.events.storage_stats()
        assert stats["disk_events"] == (
            CHUNK_SIZE if published else 0
        )
        rows = restored.store.read_records(
            "world.events", expected_record_schema=1
        )
        assert len(rows) == (0 if published else CHUNK_SIZE)
        assert len(restored.world.events) == CHUNK_SIZE
    finally:
        restored.close()


def test_corrupt_new_segment_during_lost_ack_never_trims_runtime(
    tmp_path,
):
    path = tmp_path / "corrupt-new.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        log.seal_before(11)
        before_generation = session.generation
        before_disk = log._disk_count
        before_pending = len(log._chunks)

        def corrupt_then_lose(phase):
            if phase != "after_commit":
                return
            session.store.db.execute(
                "UPDATE segments SET payload=? "
                "WHERE namespace=? AND ordinal=?",
                (b"corrupt", SEALED_EVENTS, 0),
            )
            session.store.db.commit()
            raise RuntimeError("lost ack after corruption")

        session.store._phase_hook = corrupt_then_lose
        with pytest.raises(StoreError, match="uncertain"):
            session.save()

        assert session.cold_state == "recovery-required"
        assert session.generation == before_generation
        assert log._disk_count == before_disk
        assert len(log._chunks) == before_pending
        assert session.store.generation == before_generation + 1
        with pytest.raises(StoreError):
            session.resolve_save()
        assert log._disk_count == before_disk
        assert len(log._chunks) == before_pending
    finally:
        session.close()


def test_before_commit_failure_proves_old_and_retry_is_single_generation(
    tmp_path,
):
    path = tmp_path / "before-commit.sqlite"
    world = World(8)
    world.currency.wallets[1] = {"value": 1}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.currency.wallets[1]["value"] = 2
        before = session.generation

        def fail(phase):
            if phase == "before_commit":
                raise RuntimeError("injected before commit")

        session.store._phase_hook = fail
        with pytest.raises(RuntimeError, match="before commit"):
            session.save()
        assert session.cold_state == "active"
        assert session.generation == before
        assert session.store.generation == before
        assert session.world.currency.wallets[1]["value"] == 2
        assert session.dirty == frozenset(
            {("world.currency.wallets", 1)}
        )

        session.store._phase_hook = lambda _phase: None
        assert session.save() == before + 1
        assert session.store.generation == before + 1
    finally:
        session.close()


def test_unreadable_ack_of_proven_rollback_blocks_then_resolves_old(
    tmp_path, monkeypatch
):
    path = tmp_path / "rollback-unreadable.sqlite"
    world = World(9)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        before = session.generation
        original_capture = cold_save._capture_successor

        def fail_write(phase):
            if phase == "during_writes":
                raise RuntimeError("rolled back write")

        session.store._phase_hook = fail_write
        monkeypatch.setattr(
            cold_save,
            "_capture_successor",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                StoreError("ack read unavailable")
            ),
        )
        with pytest.raises(StoreError, match="uncertain"):
            session.save()
        assert session.cold_state == "recovery-required"
        assert session.store.generation == before

        with pytest.raises(StoreError):
            alias.append(3)
        assert alias == [1, 2]

        session.store._phase_hook = lambda _phase: None
        monkeypatch.setattr(cold_save, "_capture_successor", original_capture)
        assert session.resolve_save() == before
        assert session.cold_state == "active"
        assert session.dirty == frozenset(
            {("world.currency.wallets", 1)}
        )
        assert alias == [1, 2]

        assert session.save() == before + 1
    finally:
        session.close()


def test_publication_failure_before_adoption_resolves_without_early_trim(
    tmp_path, monkeypatch
):
    path = tmp_path / "before-adoption.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        log.seal_before(11)
        before = session.generation
        before_chunks = tuple(log._chunks)
        fired = {"value": False}

        def fail_before_adoption(phase, _session, _plan):
            if phase == "before_adoption" and not fired["value"]:
                fired["value"] = True
                raise RuntimeError("before adoption")

        monkeypatch.setattr(
            cold_save, "_cold_save_phase", fail_before_adoption
        )
        with pytest.raises(RuntimeError, match="before adoption"):
            session.save()

        assert session.cold_state == "recovery-required"
        assert session._cold_publication_phase == "prepared"
        assert session.generation == before
        assert session.store.generation == before + 1
        assert log._disk_count == 0
        assert tuple(log._chunks) == before_chunks

        monkeypatch.setattr(
            cold_save, "_cold_save_phase",
            lambda _phase, _session, _plan: None,
        )
        assert session.resolve_save() == before + 1
        assert session.cold_state == "active"
        assert log._disk_count == CHUNK_SIZE
        assert len(log._chunks) == 0
    finally:
        session.close()


def test_equal_value_competitor_token_is_not_mistaken_for_our_ack(
    tmp_path, monkeypatch
):
    path = tmp_path / "foreign-token.sqlite"
    world = World(10)
    world.currency.wallets[1] = {"value": 0}
    write_cold_snapshot(world, path, rules_id=RULES)
    winner = open_world_session(path, rules_id=RULES)
    loser = open_world_session(path, rules_id=RULES)
    try:
        winner.world.currency.wallets[1]["value"] = 1
        loser.world.currency.wallets[1]["value"] = 1
        before = loser.generation
        original_commit = loser.store.commit
        fired = {"value": False}

        def competitor_then_ambiguous(
            expected_generation, changes, new_segments, metadata
        ):
            if not fired["value"]:
                fired["value"] = True
                assert winner.save() == before + 1
                raise RuntimeError("local acknowledgement lost")
            return original_commit(
                expected_generation, changes, new_segments, metadata
            )

        monkeypatch.setattr(loser.store, "commit", competitor_then_ambiguous)
        with pytest.raises(StoreConflictError):
            loser.save()

        assert loser.cold_state == "stale"
        assert loser.generation == before
        assert winner.generation == before + 1
        assert winner.world.currency.wallets[1]["value"] == (
            loser.world.currency.wallets[1]["value"]
        )
        with pytest.raises(StoreError):
            loser.world.currency.wallets[1]["value"] = 2
    finally:
        winner.close()
        loser.close()


def test_recovery_checks_changed_record_evidence_not_just_token(
    tmp_path,
):
    path = tmp_path / "corrupt-record.sqlite"
    world = World(11)
    world.currency.wallets[1] = {"value": 1}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.currency.wallets[1]["value"] = 2
        before = session.generation

        def corrupt_then_lose(phase):
            if phase != "after_commit":
                return
            # Damage the exact changed record while preserving the save head and
            # commit token. Resolution must require checked record evidence.
            typed_key = session.codec.encode(1)
            session.store.db.execute(
                "UPDATE records SET payload_checksum='bad' "
                "WHERE namespace=? AND typed_key=?",
                ("world.currency.wallets", typed_key),
            )
            session.store.db.commit()
            raise RuntimeError("lost ack after record corruption")

        session.store._phase_hook = corrupt_then_lose
        with pytest.raises(StoreError, match="uncertain"):
            session.save()
        assert session.cold_state == "recovery-required"
        assert session.generation == before
        assert session.store.generation == before + 1
        with pytest.raises(StoreError):
            session.resolve_save()
        assert session.generation == before
    finally:
        session.close()


def test_warmed_new_segment_cache_cannot_hide_corruption_on_resolution(
    tmp_path, monkeypatch
):
    path = tmp_path / "warmed-corrupt.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        log = session.world.events
        log.seal_before(11)
        before = session.generation
        fired = {"value": False}

        def fail_after_adoption(phase, _session, _plan):
            if phase != "after_adoption" or fired["value"]:
                return
            fired["value"] = True
            # Warm the replacement reader's decoded cache, then corrupt the
            # underlying committed segment. resolve_save must bypass that cache
            # through checked P1 evidence.
            assert log._disk_prefix[0].id == 1
            assert log._disk_prefix.resident_segments == 1
            session.store.db.execute(
                "UPDATE segments SET payload=? "
                "WHERE namespace=? AND ordinal=?",
                (b"corrupt", SEALED_EVENTS, 0),
            )
            session.store.db.commit()
            raise RuntimeError("after adoption corruption")

        monkeypatch.setattr(
            cold_save, "_cold_save_phase", fail_after_adoption
        )
        with pytest.raises(RuntimeError, match="after adoption corruption"):
            session.save()
        assert session.cold_state == "recovery-required"
        assert session.store.generation == before + 1

        monkeypatch.setattr(
            cold_save, "_cold_save_phase",
            lambda _phase, _session, _plan: None,
        )
        with pytest.raises(StoreError):
            session.resolve_save()
        assert session.cold_state == "recovery-required"
        assert session.generation == before
    finally:
        session.close()


def test_close_from_recovery_does_not_resolve_or_advance_again(
    tmp_path, monkeypatch
):
    path = tmp_path / "close-recovery.sqlite"
    world = World(12)
    world.currency.wallets[1] = {"value": 1}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    session.world.currency.wallets[1]["value"] = 2
    before = session.generation
    original_capture = cold_save._capture_successor

    monkeypatch.setattr(
        cold_save,
        "_capture_successor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            StoreError("ack unavailable")
        ),
    )
    with pytest.raises(StoreError, match="uncertain"):
        session.save()
    assert session.cold_state == "recovery-required"
    durable = session.store.generation
    assert durable == before + 1

    # close is teardown only: no save, no resolve, no generation change.
    session.close()
    assert session.cold_state == "closed"

    monkeypatch.setattr(cold_save, "_capture_successor", original_capture)
    reopened = open_world_session(path, rules_id=RULES)
    try:
        assert reopened.generation == durable
        assert reopened.world.currency.wallets[1]["value"] == 2
    finally:
        reopened.close()


def _writer_death_script():
    return r"""
import os, signal, sys
from ate_sim.core import Event, Layer, World
from ate_sim.event_log import EventLog
from ate_sim.persistence_events import CHUNK_SIZE
from ate_sim.persistence_session import open_world_session, write_cold_snapshot

path, rules, phase = sys.argv[1:4]
world = World(99041)
world.year = 10
shared = {"value": 1}
world.currency.wallets[1] = {"left": shared, "right": shared}
log = EventLog()
for event_id in range(1, CHUNK_SIZE + 1):
    value = Event(
        event_id, 10, "death", Layer.REALITY, (), None, (),
        {"index": event_id},
    )
    log.append(value)
    world.event_ids.add(event_id)
world.events = log
world.next_event = CHUNK_SIZE + 1
write_cold_snapshot(world, path, rules_id=rules)

session = open_world_session(path, rules_id=rules)
session.world.currency.wallets[1]["left"]["value"] = 2
session.world.events.seal_before(11)

def kill(current):
    if current == phase:
        os.kill(os.getpid(), signal.SIGKILL)

session.store._phase_hook = kill
session.save()
"""


@pytest.mark.parametrize(
    "phase,new_state",
    [("during_writes", False), ("after_commit", True)],
)
def test_subprocess_writer_death_reopens_complete_old_or_new_partition(
    tmp_path, phase, new_state
):
    path = tmp_path / f"death-{phase}.sqlite"
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = (
        str(root) + os.pathsep + str(root / "simulation")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _writer_death_script(),
            str(path),
            RULES,
            phase,
        ],
        env=env,
    )
    assert proc.returncode != 0

    reopened = open_world_session(path, rules_id=RULES)
    try:
        row = reopened.world.currency.wallets[1]
        assert row["left"] is row["right"]
        assert row["left"]["value"] == (2 if new_state else 1)
        stats = reopened.world.events.storage_stats()
        assert stats["disk_events"] == (
            CHUNK_SIZE if new_state else 0
        )
        assert stats["pending_sealed_events"] == 0
        assert stats["tail_events"] == (
            0 if new_state else CHUNK_SIZE
        )
        assert len(reopened.world.events) == CHUNK_SIZE
        assert reopened.world.events[0].id == 1
        assert reopened.world.events[-1].id == CHUNK_SIZE
    finally:
        reopened.close()
