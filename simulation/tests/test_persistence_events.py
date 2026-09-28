import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import EventLog, FrozenDict
from ate_sim.incremental_store import (
    NewSegment,
    RecordChange,
    StoreConflictError,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_events import (
    CACHE_SIZE,
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SEGMENT_FORMAT,
    SealedEventPrefix,
    prepare_sealed_append,
)

SCHEMA = "ate-p3a-events/1"
RULES = "stage-0.5-p3a-tests"


def metadata(*, namespaces=()):
    return {
        "simulation_position": 0,
        "seed": 843000,
        "next_ids": {},
        "namespaces": tuple(namespaces),
    }


def make_store(path):
    return TransactionalStore.create(
        path,
        simulation_schema=SCHEMA,
        rules_id=RULES,
        codec=WorldCodec(),
        metadata=metadata(),
    )


def open_store(path):
    return TransactionalStore.open(
        path,
        codec=WorldCodec(),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )


def event(event_id, year=None, *, sealed=True):
    if year is None:
        year = -9 + (event_id - 1) // 3
    value = Event(
        event_id,
        year,
        "record",
        Layer.REALITY,
        (Ref("person", event_id % 11 + 1),),
        None,
        () if event_id == 1 else (event_id - 1,),
        {"n": event_id, "nested": [event_id, {"ok": True}]},
    )
    if sealed:
        value.seal()
    return value


def events(first_id, count, *, year_offset=-9):
    return [
        event(i, year=year_offset + (i - 1) // 3)
        for i in range(first_id, first_id + count)
    ]


def commit_preparation(store, prepared):
    head = store.head_metadata()
    head["namespaces"] = tuple(
        sorted(set(head["namespaces"]) | {EVENT_STORAGE, SEALED_EVENTS})
    )
    return store.commit(
        prepared.expected_generation,
        prepared.record_changes,
        prepared.new_segments,
        head,
    )


def append_chunks(store, first_id, chunks, *, year_offset=-9, batch=4):
    remaining = chunks
    next_id = first_id
    while remaining:
        count = min(remaining, batch)
        batch_events = events(
            next_id,
            count * CHUNK_SIZE,
            year_offset=year_offset,
        )
        prepared = prepare_sealed_append(store, batch_events, max_chunks=batch)
        assert prepared.consumed_events == count * CHUNK_SIZE
        commit_preparation(store, prepared)
        remaining -= count
        next_id += count * CHUNK_SIZE
    return next_id


def descriptor_value(segment_count, event_count, last_year):
    return (1, CHUNK_SIZE, segment_count, event_count, last_year)


def test_values_order_types_year_queries_and_tail_not_exported(tmp_path):
    source_events = [
        event(i, sealed=False)
        for i in range(1, 4 * CHUNK_SIZE + 8)
    ]
    log = EventLog(source_events)
    log.seal_before(10**9)
    assert len(log._chunks) == 4 and len(log._tail) == 7
    assert all(e.__dict__.get("_sealed") is True for e in source_events[:4 * CHUNK_SIZE])
    assert all(not e.__dict__.get("_sealed", False) for e in source_events[4 * CHUNK_SIZE:])

    path = tmp_path / "events.sqlite"
    with make_store(path) as store:
        with pytest.raises((ValueError, StoreFormatError)):
            prepare_sealed_append(store, log)
        prepared = prepare_sealed_append(store, source_events[:4 * CHUNK_SIZE])
        commit_preparation(store, prepared)
        reader = SealedEventPrefix(store)
        try:
            assert len(reader) == 4 * CHUNK_SIZE
            assert reader[0] == source_events[0]
            assert reader[CHUNK_SIZE - 1] == source_events[CHUNK_SIZE - 1]
            assert reader[CHUNK_SIZE] == source_events[CHUNK_SIZE]
            assert reader[-1] == source_events[4 * CHUNK_SIZE - 1]
            assert type(reader[0]) is Event
            assert type(reader[0].layer) is Layer
            assert type(reader[0].data) is FrozenDict
            assert reader[0].causes == source_events[0].causes
            assert reader[CHUNK_SIZE - 2:CHUNK_SIZE + 2] == source_events[CHUNK_SIZE - 2:CHUNK_SIZE + 2]
            assert reader[-5:-1] == source_events[4 * CHUNK_SIZE - 5:4 * CHUNK_SIZE - 1]
            assert reader.between(-5, -3) == [
                e for e in source_events[:4 * CHUNK_SIZE] if -5 <= e.year <= -3
            ]
            assert reader.between(100000, 100001) == []
            assert reader.between(4, 3) == []
            with pytest.raises(IndexError):
                _ = reader[len(reader)]
        finally:
            reader.close()


@pytest.mark.parametrize("segment_count", [4, 40])
def test_lazy_open_point_cache_traversal_and_eviction_metrics(tmp_path, segment_count):
    path = tmp_path / f"lazy-{segment_count}.sqlite"
    with make_store(path) as store:
        append_chunks(store, 1, segment_count)
        reader = SealedEventPrefix(store)
        try:
            assert reader.diagnostics().segment_reads == 0
            assert reader.resident_segments == 0

            reader.reset_diagnostics()
            target = CHUNK_SIZE + 17 if segment_count > 1 else 17
            first = reader[target]
            stats = reader.diagnostics()
            assert stats.segment_reads == 1
            assert stats.segment_read_bytes > 0
            assert stats.resident_segments == 1

            assert reader[target] == first
            assert reader.diagnostics().segment_reads == 1

            retained = reader[0]
            reader.reset_diagnostics()
            for ordinal in range(segment_count):
                _ = reader[ordinal * CHUNK_SIZE]
            assert reader.resident_segments <= CACHE_SIZE
            reads_before_reload = reader.diagnostics().segment_reads
            if segment_count > CACHE_SIZE:
                assert 0 not in reader._cache
                reloaded = reader[0]
                assert reloaded == retained
                assert reloaded is not retained
                assert reader.diagnostics().segment_reads == reads_before_reload + 1

            with pytest.raises(TypeError):
                retained.kind = "rewrite"
            with pytest.raises(TypeError):
                retained.data["new"] = 1
        finally:
            reader.close()


def test_year_range_uses_logarithmic_search_not_full_prefix_scan(tmp_path):
    path = tmp_path / "years.sqlite"
    with make_store(path) as store:
        append_chunks(store, 1, 40)
        reader = SealedEventPrefix(store)
        try:
            target_year = (20 * CHUNK_SIZE) // 3
            reader.reset_diagnostics()
            result = reader.between(target_year, target_year + 1)
            stats = reader.diagnostics()
            assert result
            assert all(target_year <= e.year <= target_year + 1 for e in result)
            assert stats.segment_reads < 20
            assert stats.segment_reads < reader.segment_count
            assert stats.segment_read_bytes > 0
        finally:
            reader.close()


@pytest.mark.parametrize("old_segments", [4, 40])
def test_fixed_view_and_one_chunk_append_are_bounded(tmp_path, old_segments):
    path = tmp_path / f"append-{old_segments}.sqlite"
    with make_store(path) as store:
        next_id = append_chunks(store, 1, old_segments)
        old_view = SealedEventPrefix(store)
        try:
            assert len(old_view) == old_segments * CHUNK_SIZE
            new_chunk = events(next_id, CHUNK_SIZE)
            store.reset_diagnostics()
            prepared = prepare_sealed_append(store, new_chunk)
            prep_stats = store.diagnostics()
            assert prep_stats.payload_reads == 1
            assert prepared.before.segment_count == old_segments
            assert prepared.after.segment_count == old_segments + 1
            assert len(prepared.new_segments) == 1
            assert len(prepared.record_changes) == 1

            store.reset_diagnostics()
            commit_preparation(store, prepared)
            writes = store.diagnostics()
            assert writes.payload_writes == 2
            assert writes.payload_write_bytes < 2_000_000

            assert len(old_view) == old_segments * CHUNK_SIZE
            with SealedEventPrefix(store) as new_view:
                assert len(new_view) == (old_segments + 1) * CHUNK_SIZE
                assert new_view[-1].id == next_id + CHUNK_SIZE - 1
        finally:
            old_view.close()

        empty = prepare_sealed_append(store, [])
        store.reset_diagnostics()
        generation = store.generation
        assert empty.is_noop
        assert commit_preparation(store, empty) == generation
        assert store.diagnostics().payload_writes == 0


def test_preparation_is_capped_and_does_not_consume_unbounded_input(tmp_path):
    path = tmp_path / "bounded.sqlite"
    with make_store(path) as store:
        source = events(1, 8 * CHUNK_SIZE)
        prepared = prepare_sealed_append(store, source)
        assert prepared.consumed_events == 4 * CHUNK_SIZE
        assert len(prepared.new_segments) == 4
        assert source[4 * CHUNK_SIZE].id == prepared.consumed_events + 1


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_commit_failure_or_lost_ack_is_old_or_new_complete(tmp_path, phase):
    path = tmp_path / f"failure-{phase}.sqlite"
    with make_store(path) as store:
        source = events(1, CHUNK_SIZE)
        prepared = prepare_sealed_append(store, source)
        original = store._phase_hook

        def fail(current):
            if current == phase:
                raise OSError("injected P3A failure")
            return original(current)

        store._phase_hook = fail
        if phase == "before_commit":
            with pytest.raises(OSError, match="injected"):
                commit_preparation(store, prepared)
            assert store.generation == 0
            assert store.db.execute(
                "SELECT COUNT(*) FROM segments WHERE namespace=?", (SEALED_EVENTS,)
            ).fetchone()[0] == 0
            assert all(e.__dict__.get("_sealed") is True for e in source)
            store._phase_hook = original
            assert commit_preparation(store, prepared) == 1
        else:
            with pytest.raises(OSError, match="injected"):
                commit_preparation(store, prepared)
            assert store.generation == 1
            store._phase_hook = original
            with pytest.raises(StoreConflictError):
                commit_preparation(store, prepared)

        with SealedEventPrefix(store) as reader:
            assert len(reader) == CHUNK_SIZE
            assert reader[-1].id == CHUNK_SIZE
            reader.verify_full()


def test_stale_preparation_cannot_publish_duplicate_or_partial_prefix(tmp_path):
    path = tmp_path / "stale.sqlite"
    first = make_store(path)
    second = open_store(path)
    try:
        source = events(1, CHUNK_SIZE)
        p1 = prepare_sealed_append(first, source)
        p2 = prepare_sealed_append(second, source)
        assert commit_preparation(first, p1) == 1
        with pytest.raises(StoreConflictError):
            commit_preparation(second, p2)
        with SealedEventPrefix(first) as reader:
            assert len(reader) == CHUNK_SIZE
            assert reader.verify_full()["segments"] == 1
    finally:
        second.close()
        first.close()


def _crash_script():
    return r"""
import os, signal, sys
from ate_sim.core import Event, Layer
from ate_sim.incremental_store import TransactionalStore
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_events import (
    CHUNK_SIZE, EVENT_STORAGE, SEALED_EVENTS, prepare_sealed_append
)
path, phase = sys.argv[1], sys.argv[2]
s = TransactionalStore.open(
    path, codec=WorldCodec(),
    expected_simulation_schema='ate-p3a-events/1',
    expected_rules_id='stage-0.5-p3a-tests',
)
events = []
for i in range(1, CHUNK_SIZE + 1):
    e = Event(i, i // 3, 'record', Layer.REALITY, (), None, (), {'n': i})
    e.seal()
    events.append(e)
p = prepare_sealed_append(s, events)
head = s.head_metadata()
head['namespaces'] = tuple(sorted(set(head['namespaces']) | {EVENT_STORAGE, SEALED_EVENTS}))
s._phase_hook = lambda current: os.kill(os.getpid(), signal.SIGKILL) if current == phase else None
s.commit(p.expected_generation, p.record_changes, p.new_segments, head)
"""


@pytest.mark.parametrize("phase,expected_generation", [
    ("during_writes", 0),
    ("after_commit", 1),
])
def test_subprocess_writer_death_recovers_complete_prefix(tmp_path, phase, expected_generation):
    path = tmp_path / f"death-{phase}.sqlite"
    store = make_store(path)
    store.close()
    env = dict(os.environ)
    root = Path(__file__).parents[2]
    env["PYTHONPATH"] = (
        str(root) + os.pathsep + str(root / "simulation")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    proc = subprocess.run(
        [sys.executable, "-c", _crash_script(), str(path), phase],
        env=env,
    )
    assert proc.returncode != 0
    with open_store(path) as recovered:
        assert recovered.generation == expected_generation
        recovered.verify_all()
        if expected_generation == 0:
            assert recovered.db.execute(
                "SELECT COUNT(*) FROM segments WHERE namespace=?", (SEALED_EVENTS,)
            ).fetchone()[0] == 0
        else:
            with SealedEventPrefix(recovered) as reader:
                assert len(reader) == CHUNK_SIZE
                reader.verify_full()


@pytest.mark.parametrize("case", ["id", "chronology", "unsealed", "mutable", "partial"])
def test_append_rejects_invalid_inputs_without_mutating_source(tmp_path, case):
    path = tmp_path / f"bad-{case}.sqlite"
    with make_store(path) as store:
        source = events(1, CHUNK_SIZE)
        if case == "id":
            object.__setattr__(source[50], "id", 999)
        elif case == "chronology":
            object.__setattr__(source[50], "year", source[49].year - 1)
        elif case == "unsealed":
            source[50] = event(51, year=source[50].year, sealed=False)
        elif case == "mutable":
            bad = event(51, year=source[50].year, sealed=False)
            object.__setattr__(bad, "_sealed", True)
            source[50] = bad
        else:
            source = source[:-1]
        before_generation = store.generation
        with pytest.raises((ValueError, StoreFormatError, StoreIntegrityError)):
            prepare_sealed_append(store, source)
        assert store.generation == before_generation
        assert store.db.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 0


@pytest.mark.parametrize("case", ["element_count", "first_id", "last_id", "version"])
def test_reader_rejects_segment_header_or_envelope_mismatch(tmp_path, case):
    path = tmp_path / f"header-{case}.sqlite"
    with make_store(path) as store:
        source = events(1, CHUNK_SIZE)
        envelope = (SEGMENT_FORMAT if case != "version" else "sealed-events/v99", tuple(source))
        segment = NewSegment(
            SEALED_EVENTS,
            0,
            envelope,
            CHUNK_SIZE - 1 if case == "element_count" else CHUNK_SIZE,
            2 if case == "first_id" else 1,
            CHUNK_SIZE - 1 if case == "last_id" else CHUNK_SIZE,
        )
        change = RecordChange(
            EVENT_STORAGE,
            DESCRIPTOR_KEY,
            descriptor_value(1, CHUNK_SIZE, source[-1].year),
            record_schema=DESCRIPTOR_SCHEMA,
        )
        store.commit(
            0,
            [change],
            [segment],
            metadata(namespaces=(EVENT_STORAGE, SEALED_EVENTS)),
        )
        with SealedEventPrefix(store) as reader:
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _ = reader[0]


def test_wrong_descriptor_schema_and_last_year_are_detected_at_right_boundary(tmp_path):
    wrong_schema = tmp_path / "wrong-schema.sqlite"
    with make_store(wrong_schema) as store:
        store.commit(
            0,
            [RecordChange(
                EVENT_STORAGE, DESCRIPTOR_KEY,
                descriptor_value(0, 0, None),
                record_schema=DESCRIPTOR_SCHEMA + 1,
            )],
            [],
            metadata(namespaces=(EVENT_STORAGE, SEALED_EVENTS)),
        )
        with pytest.raises(StoreFormatError):
            SealedEventPrefix(store)

    wrong_year = tmp_path / "wrong-year.sqlite"
    with make_store(wrong_year) as store:
        source = events(1, CHUNK_SIZE)
        prepared = prepare_sealed_append(store, source)
        commit_preparation(store, prepared)
        bad = descriptor_value(1, CHUNK_SIZE, source[-1].year + 1)
        store.commit(
            store.generation,
            [RecordChange(EVENT_STORAGE, DESCRIPTOR_KEY, bad)],
            [],
            store.head_metadata(),
        )
        with SealedEventPrefix(store) as reader:
            assert reader[0].id == 1
            with pytest.raises(StoreIntegrityError, match="last year"):
                reader.verify_full()


def test_missing_or_corrupt_uncached_segment_fails_on_access_and_full_verify(tmp_path):
    for case in ("missing", "corrupt"):
        path = tmp_path / f"{case}.sqlite"
        with make_store(path) as store:
            append_chunks(store, 1, 2)
        db = __import__("sqlite3").connect(path)
        if case == "missing":
            db.execute(
                "DELETE FROM segments WHERE namespace=? AND ordinal=1",
                (SEALED_EVENTS,),
            )
        else:
            db.execute(
                "UPDATE segments SET payload=? WHERE namespace=? AND ordinal=1",
                (b"corrupt", SEALED_EVENTS),
            )
        db.commit(); db.close()

        with open_store(path) as store:
            reader = SealedEventPrefix(store)
            try:
                assert reader.diagnostics().segment_reads == 0
                assert reader[0].id == 1
                with pytest.raises((StoreIntegrityError, StoreFormatError)):
                    _ = reader[CHUNK_SIZE]
                with pytest.raises((StoreIntegrityError, StoreFormatError)):
                    reader.verify_full()
            finally:
                reader.close()


def test_backup_relocation_close_store_close_and_retained_immutability(tmp_path):
    source = tmp_path / "a" / "events.sqlite"
    backup = tmp_path / "elsewhere" / "events.sqlite"
    source.parent.mkdir(parents=True)
    with make_store(source) as store:
        append_chunks(store, 1, 6)
        store.backup(backup)

    source.unlink()
    store = open_store(backup)
    reader = SealedEventPrefix(store)
    retained = reader[0]
    for ordinal in range(1, 6):
        _ = reader[ordinal * CHUNK_SIZE]
    assert reader.resident_segments <= CACHE_SIZE
    assert 0 not in reader._cache
    assert retained.id == 1
    with pytest.raises(TypeError):
        retained.kind = "changed"

    reader.close()
    assert reader.resident_segments == 0
    with pytest.raises(StoreError):
        _ = reader[0]
    store.close()

    store = open_store(backup)
    reader = SealedEventPrefix(store)
    cached = reader[0]
    store.close()
    with pytest.raises(StoreError):
        _ = reader[0]
    with pytest.raises(StoreError):
        len(reader)
    assert cached.id == 1


@pytest.mark.parametrize("damage", ["corrupt", "delete"])
def test_full_verification_bypasses_warmed_cache_and_detects_storage_damage(
    tmp_path, damage
):
    path = tmp_path / f"cached-{damage}.sqlite"
    with make_store(path) as store:
        append_chunks(store, 1, 4)
        reader = SealedEventPrefix(store)
        try:
            cached_ordinal = 1
            cached_event = reader[cached_ordinal * CHUNK_SIZE]
            assert cached_event.id == cached_ordinal * CHUNK_SIZE + 1
            assert cached_ordinal in reader._cache

            if damage == "corrupt":
                store.db.execute(
                    "UPDATE segments SET payload=? WHERE namespace=? AND ordinal=?",
                    (b"corrupt", SEALED_EVENTS, cached_ordinal),
                )
            else:
                store.db.execute(
                    "DELETE FROM segments WHERE namespace=? AND ordinal=?",
                    (SEALED_EVENTS, cached_ordinal),
                )
            store.db.commit()

            # Ordinary point access still uses the warmed immutable cache.
            assert reader[cached_ordinal * CHUNK_SIZE] is cached_event

            reader.reset_diagnostics()
            with pytest.raises(StoreIntegrityError):
                reader.verify_full()
            # The scrub rereads storage rather than trusting the cached object.
            assert reader.diagnostics().segment_reads >= 1
            assert reader.resident_segments <= CACHE_SIZE
        finally:
            reader.close()


def test_full_verification_rereads_every_segment_when_prefix_is_warmed(tmp_path):
    path = tmp_path / "warmed-healthy.sqlite"
    with make_store(path) as store:
        append_chunks(store, 1, 4)
        reader = SealedEventPrefix(store)
        try:
            for ordinal in range(4):
                assert reader[ordinal * CHUNK_SIZE].id == ordinal * CHUNK_SIZE + 1
            assert reader.resident_segments == 4

            reader.reset_diagnostics()
            result = reader.verify_full()
            stats = reader.diagnostics()

            assert result["segments"] == 4
            assert result["events"] == 4 * CHUNK_SIZE
            assert stats.segment_reads == 4
            assert stats.segment_read_bytes > 0
            assert stats.resident_segments == 4
        finally:
            reader.close()


def test_full_verification_reports_captured_prefix_without_reopening_or_pinning(tmp_path):
    path = tmp_path / "verify.sqlite"
    with make_store(path) as store:
        append_chunks(store, 1, 4)
        reader = SealedEventPrefix(store)
        assert not store.db.in_transaction
        reader.reset_diagnostics()
        result = reader.verify_full()
        stats = reader.diagnostics()
        assert result["segments"] == 4
        assert result["events"] == 4 * CHUNK_SIZE
        assert stats.segment_reads == 4
        # Full verification streams checked storage reads and does not populate
        # an otherwise-cold ordinary reader cache.
        assert stats.resident_segments == 0
        assert not store.db.in_transaction
        reader.close()
        assert store.generation >= 1
