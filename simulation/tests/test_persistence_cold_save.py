import pytest

from ate_sim.core import Event, Layer, World
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import TransactionalStore
from ate_sim.persistence_adapters import RECORD_SCHEMA, SCHEMA, WorldCodec
from ate_sim.persistence_cold_save import prepare_cold_save
from ate_sim.persistence_events import CHUNK_SIZE
from ate_sim.persistence_session import open_world_session, write_cold_snapshot


RULES = "stage-0.5-p3b-cold-save-tests"


def event(event_id, *, year=10, data=None):
    return Event(
        event_id,
        year,
        "cold-save",
        Layer.REALITY,
        (),
        None,
        (),
        {"index": event_id} if data is None else data,
    )


def world_with_events(count, *, seed=843000):
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


def append_events(world, count, *, year=10):
    for _ in range(count):
        value = event(world.next_event, year=year)
        world.next_event += 1
        world.events.append(value)
        world.event_ids.add(value.id)


def suffix_keys(path):
    with TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    ) as store:
        return sorted(
            key
            for key, _value, _schema in store.read_records(
                "world.events", expected_record_schema=RECORD_SCHEMA
            )
        )


def test_cold_save_true_noop_does_not_advance_generation(tmp_path):
    path = tmp_path / "noop.sqlite"
    write_cold_snapshot(World(1), path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        before = session.generation
        diagnostics = session.diagnostics()
        assert session.save() == before
        assert session.generation == before
        assert session.diagnostics().payload_writes == diagnostics.payload_writes
        assert session.cold_state == "active"
    finally:
        session.close()


def test_cold_save_q0_current_edit_commits_and_reopens(tmp_path):
    path = tmp_path / "q0.sqlite"
    write_cold_snapshot(World(2), path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        before = session.generation
        session.world.currency.wallets[7] = {"coins": 4}
        assert session.save() == before + 1
        assert session.world.currency.wallets[7]["coins"] == 4
        assert session.dirty == frozenset()
    finally:
        session.close()

    restored = open_world_session(path, rules_id=RULES)
    try:
        assert restored.world.currency.wallets[7]["coins"] == 4
    finally:
        restored.close()


def test_cold_save_one_persisted_chunk_moves_rows_to_segment(tmp_path):
    path = tmp_path / "one.sqlite"
    write_cold_snapshot(
        world_with_events(CHUNK_SIZE), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        retained_log = session.world.events
        session.world.events.seal_before(11)
        before = session.generation
        assert session.save() == before + 1
        assert session.world.events is retained_log
        stats = retained_log.storage_stats()
        assert stats["disk_events"] == CHUNK_SIZE
        assert stats["pending_sealed_events"] == 0
        assert stats["disk_segment_reads"] == 1
    finally:
        session.close()

    assert suffix_keys(path) == []
    restored = open_world_session(path, rules_id=RULES)
    try:
        assert len(restored.world.events) == CHUNK_SIZE
        assert restored.world.events[0].id == 1
        assert restored.world.events[-1].id == CHUNK_SIZE
    finally:
        restored.close()


def test_cold_save_selected_chunk_straddles_committed_n(tmp_path):
    persisted = 1000
    path = tmp_path / "straddle.sqlite"
    write_cold_snapshot(
        world_with_events(persisted), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        append_events(session.world, CHUNK_SIZE - persisted)
        session.world.events.seal_before(11)
        plan = prepare_cold_save(session)
        assert plan is not None
        event_actions = [
            change for change in plan.changes
            if change.namespace == "world.events"
        ]
        deletes = {change.key for change in event_actions if change.delete}
        writes = {change.key for change in event_actions if not change.delete}
        assert deletes == set(range(persisted))
        assert not (writes & set(range(persisted, CHUNK_SIZE)))

        assert session.save() == plan.expected_generation + 1
    finally:
        session.close()

    assert suffix_keys(path) == []


def test_cold_save_drains_five_pending_chunks_as_four_then_one(tmp_path):
    path = tmp_path / "five.sqlite"
    write_cold_snapshot(World(5), path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        append_events(session.world, 5 * CHUNK_SIZE)
        session.world.events.seal_before(11)
        start = session.generation

        assert session.save() == start + 1
        stats = session.world.events.storage_stats()
        assert stats["disk_events"] == 4 * CHUNK_SIZE
        assert stats["pending_sealed_events"] == CHUNK_SIZE
        assert suffix_keys(path) == list(
            range(4 * CHUNK_SIZE, 5 * CHUNK_SIZE)
        )

        assert session.save() == start + 2
        stats = session.world.events.storage_stats()
        assert stats["disk_events"] == 5 * CHUNK_SIZE
        assert stats["pending_sealed_events"] == 0
        assert suffix_keys(path) == []

        assert session.save() == start + 2
    finally:
        session.close()


def test_individually_sealed_tail_row_is_saved_without_log_identity(tmp_path):
    path = tmp_path / "individual.sqlite"
    write_cold_snapshot(
        world_with_events(1), path, rules_id=RULES
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        value = session.world.events[0]
        value.seal()
        assert ("world.events", 0) in session.dirty
        session.save()
    finally:
        session.close()

    restored = open_world_session(path, rules_id=RULES)
    try:
        value = restored.world.events[0]
        assert value.__dict__.get("_sealed") is True
        assert restored.world.events.storage_stats()["disk_events"] == 0
    finally:
        restored.close()
