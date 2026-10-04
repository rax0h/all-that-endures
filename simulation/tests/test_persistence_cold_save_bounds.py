import gc
import weakref

import pytest

from ate_sim import Simulation, generate_world
from ate_sim.core import Layer, World
from ate_sim.incremental_store import TransactionalStore
from ate_sim.persistence_adapters import SCHEMA, WorldCodec
from ate_sim.persistence_cold_save import prepare_cold_save
from ate_sim.persistence_events import CHUNK_SIZE
from ate_sim.persistence_session import open_world_session, write_cold_snapshot
from ate_sim.persistence_tracking import _BINDINGS

from simulation.tests.test_persistence_session_open import (
    RULES as STRUCTURAL_RULES,
    build_cold_path,
)


RULES = "stage-0.5-p3b-cold-save-bounds-tests"


def _typed_events_equal(session, right):
    codec = WorldCodec(identity_links_recorded=True)
    left = session.world
    assert len(left.events) == len(right.events)
    for a, b in zip(left.events, right.events):
        # Bound mutable payload containers are tracker subclasses.  Compare the
        # exact persisted typed Event values, not tracker implementation types.
        assert codec.encode(session._plain(a)) == codec.encode(b)


def _session_binding_count(session):
    return sum(
        1 for bound in _BINDINGS.values()
        if bound.session is session
    )


def _log_owner_rows(session):
    return sum(
        len(rows)
        for owner, rows in session._identity_index.owner_occurrences.items()
        if owner[0] == "world.events"
    )


def test_independent_control_matches_through_save_reopen_cycles(tmp_path):
    seed = 99031
    source = Simulation(generate_world(seed, mature=False)).run(2)
    control = Simulation(generate_world(seed, mature=False)).run(2)
    assert source.digest() == control.digest()

    source_shared = {"values": [7, 8]}
    control_shared = {"values": [7, 8]}
    source.currency.wallets[-700] = {
        "left": source_shared,
        "right": source_shared,
    }
    control.currency.wallets[-700] = {
        "left": control_shared,
        "right": control_shared,
    }
    assert source.digest() == control.digest()

    path = tmp_path / "continuation.sqlite"
    write_cold_snapshot(source, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        for cycle in range(3):
            assert session.world.digest() == control.digest()
            assert session.world.currency.wallets[-700]["left"] is (
                session.world.currency.wallets[-700]["right"]
            )

            Simulation(control).run(2)
            Simulation(session.world).run(2)
            assert session.world.digest() == control.digest()
            _typed_events_equal(session, control)

            before = session.generation
            generation = session.save()
            assert generation in (before, before + 1)
            session.close()

            session = open_world_session(path, rules_id=RULES)
            assert session.world.digest() == control.digest()
            assert session.world.next_event == control.next_event
            assert session.world.year == control.year
            assert session.world.currency.wallets[-700]["left"] is (
                session.world.currency.wallets[-700]["right"]
            )
            _typed_events_equal(session, control)

        # Subsequent simulation after the final restore remains deterministic.
        Simulation(control).run(3)
        Simulation(session.world).run(3)
        assert session.world.digest() == control.digest()
        _typed_events_equal(session, control)
    finally:
        session.close()


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_cold_save_history_bounds_are_independent_of_old_prefix(
    tmp_path, segments
):
    path, expected = build_cold_path(
        tmp_path,
        disk_segments=segments,
        pending_chunks=5,
        tail_count=3,
        wallets={1: {"values": [1]}},
    )
    session = open_world_session(path, rules_id=STRUCTURAL_RULES)
    try:
        log = session.world.events
        original_prefix = log._disk_prefix
        baseline_memo = len(session._memo)
        baseline_bindings = _session_binding_count(session)
        baseline_log_rows = _log_owner_rows(session)
        before_pending_bytes = log.storage_stats()[
            "pending_sealed_bytes"
        ]

        plan4 = prepare_cold_save(session)
        assert plan4 is not None
        assert plan4.transfer_chunks == 4
        assert len(plan4.new_segments) == 4
        deletes4 = sum(
            1 for change in plan4.changes
            if change.namespace == "world.events" and change.delete
        )
        del plan4
        gc.collect()

        session.reset_diagnostics()
        generation = session.generation
        assert session.save() == generation + 1
        io4 = session.diagnostics()
        stats4 = log.storage_stats()
        assert original_prefix.diagnostics().segment_reads == 0
        assert stats4["disk_events"] == expected["D"] + 4 * CHUNK_SIZE
        assert stats4["pending_sealed_events"] == CHUNK_SIZE
        assert stats4["disk_cache_segments"] <= 4
        assert session._cold_plan is None

        prefix_after_four = log._disk_prefix
        reads_before_one = prefix_after_four.diagnostics().segment_reads
        plan1 = prepare_cold_save(session)
        assert plan1 is not None
        assert plan1.transfer_chunks == 1
        assert len(plan1.new_segments) == 1
        deletes1 = sum(
            1 for change in plan1.changes
            if change.namespace == "world.events" and change.delete
        )
        del plan1
        gc.collect()

        session.reset_diagnostics()
        assert session.save() == generation + 2
        io1 = session.diagnostics()
        stats1 = log.storage_stats()
        assert prefix_after_four.diagnostics().segment_reads == reads_before_one
        assert stats1["pending_sealed_events"] == 0
        assert stats1["disk_events"] == expected["D"] + 5 * CHUNK_SIZE
        assert stats1["disk_cache_segments"] <= 4

        # No-op: bounded validity reads are allowed, but no payload writes,
        # segment reads or generation advance.
        prefix_noop = log._disk_prefix
        segment_reads_before = prefix_noop.diagnostics().segment_reads
        session.reset_diagnostics()
        assert session.save() == generation + 2
        noop_io = session.diagnostics()
        assert noop_io.payload_writes == 0
        assert prefix_noop.diagnostics().segment_reads == segment_reads_before

        # A fixed local current-owner mutation remains q=0 and does not touch
        # historical segment payloads.
        session.world.currency.wallets[1]["values"].append(2)
        assert session.dirty == frozenset(
            {("world.currency.wallets", 1)}
        )
        local_plan = prepare_cold_save(session)
        assert local_plan is not None
        assert local_plan.transfer_chunks == 0
        local_records = len(local_plan.record_evidence)
        del local_plan
        gc.collect()

        prefix_before_local = log._disk_prefix
        local_reads_before = prefix_before_local.diagnostics().segment_reads
        session.reset_diagnostics()
        assert session.save() == generation + 3
        local_io = session.diagnostics()
        # q=0 still installs a generation-pinned replacement reader.  The old
        # reader must not be touched, and the new reader starts with no segment
        # payload reads.
        assert (
            prefix_before_local.diagnostics().segment_reads
            == local_reads_before
        )
        assert log._disk_prefix.diagnostics().segment_reads == 0

        after = log.storage_stats()
        assert after["pending_sealed_bytes"] < before_pending_bytes
        assert len(session._memo) == baseline_memo
        assert _session_binding_count(session) == baseline_bindings
        assert _log_owner_rows(session) == baseline_log_rows
        assert session._cold_plan is None

        print(
            "P3B_COLD_SAVE_BOUNDS "
            f"segments={segments} "
            f"four_segment_reads={stats4['disk_segment_reads']} "
            f"four_payload_reads={io4.payload_reads} "
            f"four_payload_writes={io4.payload_writes} "
            f"four_write_bytes={io4.payload_write_bytes} "
            f"four_deletes={deletes4} "
            f"one_segment_reads={stats1['disk_segment_reads']} "
            f"one_payload_reads={io1.payload_reads} "
            f"one_payload_writes={io1.payload_writes} "
            f"one_write_bytes={io1.payload_write_bytes} "
            f"one_deletes={deletes1} "
            f"noop_payload_reads={noop_io.payload_reads} "
            f"noop_payload_writes={noop_io.payload_writes} "
            f"local_payload_reads={local_io.payload_reads} "
            f"local_payload_writes={local_io.payload_writes} "
            f"local_write_bytes={local_io.payload_write_bytes} "
            f"local_records={local_records} "
            f"memo={len(session._memo)} "
            f"bindings={_session_binding_count(session)} "
            f"log_occurrences={_log_owner_rows(session)} "
            f"pending_bytes={after['pending_sealed_bytes']} "
            f"cache={after['disk_cache_segments']}"
        )
    finally:
        session.close()


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_cold_save_local_alias_work_is_affected_owner_bounded(
    tmp_path, groups
):
    world = World(88000 + groups)
    for index in range(groups):
        shared = {"values": [index]}
        world.currency.wallets[index] = {
            "left": shared,
            "right": shared,
        }

    path = tmp_path / f"alias-{groups}.sqlite"
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.currency.wallets[0]["left"]["values"].append(-1)
        assert session.dirty == frozenset(
            {("world.currency.wallets", 0)}
        )
        plan = prepare_cold_save(session)
        assert plan is not None
        assert plan.transfer_chunks == 0
        record_count = len(plan.record_evidence)
        changed_member_work = session.changed_member_work
        del plan

        session.reset_diagnostics()
        session.save()
        io = session.diagnostics()
        assert session.dirty == frozenset()
        assert record_count <= 4
        print(
            "P3B_COLD_SAVE_ALIAS_SCALE "
            f"groups={groups} "
            f"record_actions={record_count} "
            f"changed_member_work={changed_member_work} "
            f"payload_reads={io.payload_reads} "
            f"payload_writes={io.payload_writes} "
            f"payload_write_bytes={io.payload_write_bytes}"
        )
    finally:
        session.close()


def test_repeated_append_seal_save_releases_event_backend_state(tmp_path):
    path = tmp_path / "reclaim.sqlite"
    write_cold_snapshot(World(731), path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        baseline_memo = len(session._memo)
        baseline_bindings = _session_binding_count(session)
        for batch in range(3):
            first = None
            for offset in range(CHUNK_SIZE):
                value = session.world.emit(
                    "reclaim",
                    Layer.REALITY,
                    batch=batch,
                    offset=offset,
                )
                if offset == 0:
                    first = value
            value = None
            first_ref = weakref.ref(first)
            session.world.events.seal_before(session.world.year + 1)
            first = None
            session.save()
            gc.collect()

            assert first_ref() is None
            assert session._cold_plan is None
            assert session.world.events.storage_stats()[
                "pending_sealed_events"
            ] == 0
            assert session.world.events.storage_stats()[
                "disk_cache_segments"
            ] <= 4
            assert _log_owner_rows(session) == 0
            assert len(session._memo) == baseline_memo
            assert _session_binding_count(session) == baseline_bindings
            print(
                "P3B_COLD_SAVE_RECLAIM "
                f"batch={batch + 1} "
                f"disk_segments={session.world.events.storage_stats()['disk_segments']} "
                f"memo={len(session._memo)} "
                f"bindings={_session_binding_count(session)} "
                f"log_occurrences={_log_owner_rows(session)}"
            )
    finally:
        session.close()
