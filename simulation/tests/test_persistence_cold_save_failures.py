import sqlite3

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


def test_failure_before_commit_proves_old_and_preserves_retry(tmp_path):
    path = tmp_path / "rollback.sqlite"
    world = World(1)
    world.currency.wallets[1] = {"values": [1]}
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        alias = session.world.currency.wallets[1]["values"]
        alias.append(2)
        generation = session.generation
        dirty = session.dirty

        def fail(phase):
            if phase == "during_writes":
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
