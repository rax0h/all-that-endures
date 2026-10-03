import pytest

from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import EventLog, FrozenDict
from ate_sim.incremental_store import (
    RecordChange,
    StoreError,
    StoreFormatError,
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
    SealedEventPrefix,
    prepare_sealed_append,
)

SCHEMA = "ate-p3b-eventlog/1"
RULES = "stage-0.5-p3b-eventlog-tests"


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


def event(event_id, *, sealed=False):
    year = (event_id - 1) // 7 - 500
    value = Event(
        event_id,
        year,
        "record",
        Layer.REALITY,
        (Ref("person", event_id % 13 + 1),),
        None,
        () if event_id == 1 else (event_id - 1,),
        {"n": event_id, "nested": [event_id, {"ok": True}]},
    )
    if sealed:
        value.seal()
    return value


def events(first_id, count, *, sealed=False):
    return [event(i, sealed=sealed) for i in range(first_id, first_id + count)]


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


def append_segments(store, segment_count):
    next_id = 1
    remaining = segment_count
    while remaining:
        count = min(remaining, 4)
        source = events(next_id, count * CHUNK_SIZE, sealed=True)
        prepared = prepare_sealed_append(store, source)
        assert prepared.consumed_events == count * CHUNK_SIZE
        commit_preparation(store, prepared)
        next_id += count * CHUNK_SIZE
        remaining -= count
    return next_id


def initialize_empty_prefix(store):
    value = (1, CHUNK_SIZE, 0, 0, None)
    return store.commit(
        store.generation,
        [
            RecordChange(
                EVENT_STORAGE,
                DESCRIPTOR_KEY,
                value,
                record_schema=DESCRIPTOR_SCHEMA,
            )
        ],
        [],
        metadata(namespaces=(EVENT_STORAGE, SEALED_EVENTS)),
    )


def test_empty_disk_pending_and_tail_ranges(tmp_path):
    store = make_store(tmp_path / "empty.sqlite")
    try:
        initialize_empty_prefix(store)
        reader = SealedEventPrefix(store)
        log = EventLog.from_disk_prefix(reader)
        assert len(log) == 0
        assert log[:] == []
        assert list(log) == []
        assert log.between(-10, 10) == []
        stats = log.storage_stats()
        for key in (
            "events",
            "sealed_events",
            "resident_events",
            "cold_bytes",
            "segments",
            "disk_events",
            "disk_segments",
            "pending_sealed_events",
            "pending_sealed_segments",
            "pending_sealed_bytes",
            "tail_events",
            "decoded_cache_segments",
            "decoded_cache_events",
            "disk_cache_segments",
            "pending_cache_segments",
            "disk_segment_reads",
            "disk_segment_read_bytes",
            "resident_compressed_bytes",
        ):
            assert stats[key] == 0
        reader.close()
    finally:
        store.close()


@pytest.mark.parametrize(
    "count,expected_chunks,expected_tail",
    [
        (0, 0, 0),
        (CHUNK_SIZE - 1, 0, CHUNK_SIZE - 1),
        (CHUNK_SIZE, 1, 0),
        (CHUNK_SIZE + 1, 1, 1),
    ],
)
def test_in_memory_boundaries_and_strict_seal_timing_unchanged(
    count, expected_chunks, expected_tail
):
    source = events(1, count)
    retained = source[0] if source else None
    log = EventLog(source)
    if count >= CHUNK_SIZE:
        boundary_year = source[CHUNK_SIZE - 1].year
        log.seal_before(boundary_year)
        assert len(log._chunks) == 0
        assert source[0].__dict__.get("_sealed", False) is False
        log.seal_before(boundary_year + 1)
    else:
        log.seal_before(10**9)

    assert len(log._chunks) == expected_chunks
    assert len(log._tail) == expected_tail
    assert len(log) == count
    if retained is not None and expected_chunks:
        assert retained.__dict__.get("_sealed") is True
        assert type(retained.data) is FrozenDict
        with pytest.raises(TypeError):
            retained.data["rewrite"] = True


def test_composite_operations_match_independent_in_memory_log(tmp_path):
    store = make_store(tmp_path / "composite.sqlite")
    reader = None
    try:
        append_segments(store, 1)
        reader = SealedEventPrefix(store)
        suffix = events(CHUNK_SIZE + 1, CHUNK_SIZE + 23)
        for item in suffix[:CHUNK_SIZE]:
            item.seal()
        suffix[-1].seal()
        tail_refs = tuple(suffix[CHUNK_SIZE:])
        log = EventLog.from_disk_prefix(
            reader, suffix, pending_sealed_events=CHUNK_SIZE
        )

        control_source = events(1, 2 * CHUNK_SIZE + 23)
        control_source[-1].seal()
        control = EventLog(control_source)
        control.seal_before(10**9)

        assert log == control
        assert len(log) == len(control)
        for index in (0, CHUNK_SIZE - 1, CHUNK_SIZE, -1):
            assert log[index] == control[index]
        for selection in (
            slice(CHUNK_SIZE - 3, CHUNK_SIZE + 4),
            slice(CHUNK_SIZE + 4, CHUNK_SIZE - 5, -2),
            slice(None, None, -997),
        ):
            assert log[selection] == control[selection]

        boundary_year = control[CHUNK_SIZE - 1].year
        assert control[CHUNK_SIZE].year == boundary_year
        for first, last in (
            (-600, -490),
            (boundary_year, boundary_year),
            (boundary_year - 1, boundary_year + 1),
            (10_000, 10_010),
            (5, 4),
        ):
            assert log.between(first, last) == control.between(first, last)

        reader.reset_diagnostics()
        assert log.between(reader.last_year + 1, 100_000) == control.between(
            reader.last_year + 1, 100_000
        )
        assert reader.diagnostics().segment_reads == 0

        assert tuple(log._tail) == tail_refs
        assert all(a is b for a, b in zip(log._tail, tail_refs))
        assert log._tail[-1].__dict__.get("_sealed") is True
        assert type(log[0]) is Event
        assert type(log[0].data) is FrozenDict
        assert log[CHUNK_SIZE].causes == control[CHUNK_SIZE].causes

        stats = log.storage_stats()
        assert stats["disk_events"] == CHUNK_SIZE
        assert stats["pending_sealed_events"] == CHUNK_SIZE
        assert stats["tail_events"] == 23
        assert stats["pending_sealed_bytes"] > 0
        assert stats["resident_compressed_bytes"] == stats["pending_sealed_bytes"]
        assert stats["decoded_cache_segments"] <= 2 * CACHE_SIZE
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_prepare_then_adopt_exactly_four_of_five_pending_chunks(tmp_path):
    store = make_store(tmp_path / "adopt.sqlite")
    old_reader = new_reader = None
    try:
        append_segments(store, 1)
        old_reader = SealedEventPrefix(store)
        disk_count = CHUNK_SIZE
        suffix = events(disk_count + 1, 5 * CHUNK_SIZE + 11)
        for item in suffix[:5 * CHUNK_SIZE]:
            item.seal()
        tail_refs = tuple(suffix[5 * CHUNK_SIZE:])
        log = EventLog.from_disk_prefix(
            old_reader, suffix, pending_sealed_events=5 * CHUNK_SIZE
        )

        selected = log[disk_count : disk_count + 4 * CHUNK_SIZE]
        store.reset_diagnostics()
        prepared = prepare_sealed_append(store, selected)
        prep_io = store.diagnostics()
        assert prep_io.payload_reads == 1
        assert prep_io.payload_writes == 0
        assert prepared.consumed_events == 4 * CHUNK_SIZE
        assert log.disk_event_count == CHUNK_SIZE
        assert log.pending_sealed_event_count == 5 * CHUNK_SIZE

        with pytest.raises(ValueError, match="boundary"):
            log._adopt_committed_prefix(
                old_reader, transferred_events=CHUNK_SIZE
            )
        assert log.pending_sealed_event_count == 5 * CHUNK_SIZE

        store.reset_diagnostics()
        generation = commit_preparation(store, prepared)
        commit_io = store.diagnostics()
        receipt = store.db.execute(
            "SELECT record_writes,record_deletes,segment_writes,payload_bytes "
            "FROM save_receipts WHERE generation=?",
            (generation,),
        ).fetchone()
        assert receipt[:3] == (1, 0, 4)
        assert commit_io.payload_writes == 5
        assert commit_io.payload_write_bytes == receipt[3]

        new_reader = SealedEventPrefix(store)
        returned = log._adopt_committed_prefix(
            new_reader, transferred_events=prepared.consumed_events
        )
        assert returned is old_reader
        assert log.disk_event_count == 5 * CHUNK_SIZE
        assert log.pending_sealed_event_count == CHUNK_SIZE
        assert log.tail_event_count == 11
        assert log[5 * CHUNK_SIZE].id == 5 * CHUNK_SIZE + 1
        assert log[6 * CHUNK_SIZE - 1].id == 6 * CHUNK_SIZE
        assert tuple(log._tail) == tail_refs
        assert all(a is b for a, b in zip(log._tail, tail_refs))
        print(
            "P3B_TRANSFER "
            f"prepare_reads={prep_io.payload_reads} "
            f"commit_writes={commit_io.payload_writes} "
            f"record_deletes={receipt[1]} "
            f"segment_writes={receipt[2]} "
            f"payload_write_bytes={commit_io.payload_write_bytes} "
            f"pending_bytes={log.storage_stats()['pending_sealed_bytes']}"
        )
        old_reader.close()
        old_reader = None
    finally:
        if new_reader is not None:
            new_reader.close()
        if old_reader is not None:
            old_reader.close()
        store.close()


def test_failed_commit_leaves_composite_source_authoritative(tmp_path):
    store = make_store(tmp_path / "failed.sqlite")
    reader = None
    try:
        append_segments(store, 1)
        reader = SealedEventPrefix(store)
        suffix = events(CHUNK_SIZE + 1, CHUNK_SIZE + 2)
        for item in suffix[:CHUNK_SIZE]:
            item.seal()
        log = EventLog.from_disk_prefix(
            reader, suffix, pending_sealed_events=CHUNK_SIZE
        )
        prepared = prepare_sealed_append(
            store, log[CHUNK_SIZE : 2 * CHUNK_SIZE]
        )
        original = store._phase_hook

        def fail(phase):
            if phase == "before_commit":
                raise OSError("injected failure")
            return original(phase)

        store._phase_hook = fail
        with pytest.raises(OSError, match="injected failure"):
            commit_preparation(store, prepared)
        store._phase_hook = original

        assert store.generation == prepared.expected_generation
        assert log.disk_event_count == CHUNK_SIZE
        assert log.pending_sealed_event_count == CHUNK_SIZE
        assert log[CHUNK_SIZE].id == CHUNK_SIZE + 1
    finally:
        if reader is not None:
            reader.close()
        store.close()


@pytest.mark.parametrize("segment_count", [4, 40])
def test_open_point_repeat_and_cache_bound_measurements(tmp_path, segment_count):
    store = make_store(tmp_path / f"measure-{segment_count}.sqlite")
    reader = None
    try:
        append_segments(store, segment_count)
        reader = SealedEventPrefix(store)
        reader.reset_diagnostics()
        log = EventLog.from_disk_prefix(reader)

        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        assert log.storage_stats()["disk_cache_segments"] == 0

        target = CHUNK_SIZE + 17
        first = log[target]
        assert first.id == target + 1
        after_first = reader.diagnostics()
        assert after_first.segment_reads == 1
        assert after_first.segment_read_bytes > 0
        assert after_first.resident_segments == 1

        assert log[target] == first
        assert reader.diagnostics().segment_reads == 1

        retained = log[0]
        reader.reset_diagnostics()
        for ordinal in range(segment_count):
            assert log[ordinal * CHUNK_SIZE].id == ordinal * CHUNK_SIZE + 1
        traversed = reader.diagnostics()
        assert traversed.resident_segments <= CACHE_SIZE
        assert log.storage_stats()["disk_cache_segments"] <= CACHE_SIZE
        if segment_count > CACHE_SIZE:
            assert 0 not in reader._cache
            reads = traversed.segment_reads
            again = log[0]
            assert again == retained
            assert again is not retained
            assert reader.diagnostics().segment_reads == reads + 1
        measured = reader.diagnostics()
        print(
            "P3B_CACHE "
            f"segments={segment_count} "
            f"segment_reads={measured.segment_reads} "
            f"segment_read_bytes={measured.segment_read_bytes} "
            f"cache_segments={measured.resident_segments}"
        )
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_active_read_transaction_factory_does_not_nest_or_end_transaction(tmp_path):
    store = make_store(tmp_path / "active-read.sqlite")
    reader = None
    try:
        append_segments(store, 1)
        with pytest.raises(
            StoreError, match="active caller-owned read transaction"
        ):
            SealedEventPrefix.from_active_read_transaction(store)

        with store.read_transaction() as generation:
            reader = SealedEventPrefix.from_active_read_transaction(store)
            assert store.db.in_transaction
            assert reader.captured_generation == generation
            assert reader.diagnostics().segment_reads == 0
            assert reader.last_year == event(CHUNK_SIZE).year
        assert not store.db.in_transaction
        assert reader[0].id == 1
    finally:
        if reader is not None:
            reader.close()
        store.close()


@pytest.mark.parametrize("close_reader", [False, True])
def test_composite_fails_explicitly_after_borrowed_backend_closes(
    tmp_path, close_reader
):
    store = make_store(tmp_path / f"closed-{close_reader}.sqlite")
    append_segments(store, 1)
    reader = SealedEventPrefix(store)
    tail = events(CHUNK_SIZE + 1, 2)
    log = EventLog.from_disk_prefix(reader, tail)
    if close_reader:
        reader.close()
    else:
        store.close()

    operations = (
        lambda: len(log),
        lambda: log[-1],
        lambda: list(log),
        lambda: log.between(tail[0].year, tail[-1].year),
        lambda: log.storage_stats(),
        lambda: log.append(event(CHUNK_SIZE + 3)),
        lambda: log.seal_before(10**9),
    )
    for operation in operations:
        with pytest.raises(StoreError):
            operation()

    if close_reader:
        store.close()


def test_storage_preparation_never_freezes_mutable_tail(tmp_path):
    store = make_store(tmp_path / "mutable.sqlite")
    try:
        source = events(1, CHUNK_SIZE)
        log = EventLog(source)
        with pytest.raises(StoreFormatError):
            prepare_sealed_append(store, log[:CHUNK_SIZE])
        assert all(
            item.__dict__.get("_sealed", False) is False for item in source
        )
        source[0].data["still"] = "mutable"
        assert source[0].data["still"] == "mutable"
    finally:
        store.close()
