import copy
import struct

import pytest

from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import EventLog, FrozenDict
from ate_sim.incremental_store import (
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    WorldCodec,
    _at_path,
    _complete_identity_groups,
    _restore_identity,
    _verify_identity_graph,
)
from ate_sim.persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedEventPrefix,
    prepare_sealed_append,
)


SCHEMA = "ate-p3b-cold-identity-restore/1"
RULES = "stage-0.5-p3b-cold-identity-restore-tests"


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


def event(event_id, *, year=None, data=None, sealed=False):
    if year is None:
        year = (event_id - 1) // 7 - 500
    value = Event(
        event_id,
        year,
        "restore-probe",
        Layer.REALITY,
        (Ref("person", event_id % 13 + 1),),
        None,
        () if event_id == 1 else (event_id - 1,),
        (
            {"n": event_id, "nested": [event_id, {"ok": True}]}
            if data is None else data
        ),
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


def disk_log(tmp_path, segment_count, *, pending_chunks=1, tail_count=4):
    store = make_store(tmp_path / f"restore-{segment_count}-{pending_chunks}.sqlite")
    next_id = append_segments(store, segment_count)
    reader = SealedEventPrefix(store)
    suffix = events(next_id, pending_chunks * CHUNK_SIZE + tail_count)
    for item in suffix[: pending_chunks * CHUNK_SIZE]:
        item.seal()
    tail = suffix[pending_chunks * CHUNK_SIZE :]
    if len(tail) > 1:
        tail[1].seal()
    log = EventLog.from_disk_prefix(
        reader,
        suffix,
        pending_sealed_events=pending_chunks * CHUNK_SIZE,
    )
    return store, reader, log, tuple(tail)


def path(*components):
    return tuple(components)


def frozen_identity_state(log):
    return {
        "disk_prefix": log._disk_prefix,
        "disk_count": log._disk_count,
        "chunks": tuple(log._chunks),
        "count": log._count,
        "years": tuple(log._years),
        "offsets": tuple(log._offsets),
        "last_year": log._last_year,
        "pending_bytes": sum(map(len, log._chunks)),
    }


@pytest.mark.parametrize("segments", [4, 40])
def test_cold_lookup_and_projected_verification_read_zero_history(
    tmp_path, monkeypatch, segments
):
    store, reader, log, tail = disk_log(tmp_path, segments)
    try:
        reader.reset_diagnostics()
        pending_decodes = 0

        def forbidden_chunk(_number):
            nonlocal pending_decodes
            pending_decodes += 1
            raise AssertionError("cold identity restore decoded pending history")

        def forbidden_iteration(_log):
            raise AssertionError("cold identity restore used logical EventLog iteration")

        log._chunk = forbidden_chunk
        monkeypatch.setattr(EventLog, "__iter__", forbidden_iteration)

        root = {"events": log, "alias": log}
        events_path = path(("key", "events"))
        alias_path = path(("key", "alias"))
        first = (segments + 1) * CHUNK_SIZE

        assert _at_path(
            root,
            events_path + (("index", first),),
            mutable_event_tail_only=True,
        ) is tail[0]

        groups = _complete_identity_groups(
            root, mutable_event_tail_only=True
        )
        assert len(groups) == 14
        assert sum(len(paths) for paths in groups.values()) == 27

        links = [(alias_path, events_path)]
        _verify_identity_graph(
            root, links, mutable_event_tail_only=True
        )

        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        assert len(log._cache) == 0
        assert pending_decodes == 0
        print(
            "P3B_IDENTITY_RESTORE_COLD "
            f"segments={segments} groups={len(groups)} "
            f"paths={sum(len(v) for v in groups.values())} "
            f"segment_reads={reader.diagnostics().segment_reads} "
            f"disk_cache={reader.resident_segments} "
            f"pending_decodes={pending_decodes} pending_cache={len(log._cache)}"
        )
    finally:
        reader.close()
        store.close()


def test_default_helpers_reject_disk_log_before_history_read(tmp_path):
    store, reader, log, _tail = disk_log(tmp_path, 4)
    try:
        reader.reset_diagnostics()
        log._chunk = lambda _number: (_ for _ in ()).throw(
            AssertionError("default identity helper decoded pending history")
        )
        root = {"events": log}
        with pytest.raises(StoreFormatError, match="mutable_event_tail_only"):
            _at_path(root, path(("key", "events")))
        with pytest.raises(StoreFormatError, match="mutable_event_tail_only"):
            _complete_identity_groups(root)
        assert reader.diagnostics().segment_reads == 0
        assert len(log._cache) == 0
    finally:
        reader.close()
        store.close()


def test_excluded_and_malformed_eventlog_paths_fail_without_history_io(tmp_path):
    store, reader, log, _tail = disk_log(tmp_path, 4)
    try:
        reader.reset_diagnostics()
        log._chunk = lambda _number: (_ for _ in ()).throw(
            AssertionError("excluded identity path decoded pending history")
        )
        root = {"events": log, "alias": log}
        d = 4 * CHUNK_SIZE
        f = 5 * CHUNK_SIZE
        bad_paths = [
            path(("key", "events"), ("index", 0)),
            path(("key", "events"), ("index", d)),
            path(("key", "events"), ("index", f + 1)),
            path(("key", "events"), ("index", 0), ("field", "data")),
            path(("key", "alias"), ("index", d)),
            path(("key", "events"), ("index", -1)),
            path(("key", "events"), ("index", True)),
            path(("key", "events"), ("index", f + 99)),
            path(("key", "events"), ("index",)),
        ]
        for bad in bad_paths:
            with pytest.raises(StoreFormatError):
                _at_path(root, bad, mutable_event_tail_only=True)
        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        assert len(log._cache) == 0
    finally:
        reader.close()
        store.close()


@pytest.mark.parametrize("close_reader", [False, True])
def test_closed_backend_fails_before_cold_path_resolution(
    tmp_path, close_reader
):
    store, reader, log, tail = disk_log(tmp_path, 1, pending_chunks=0, tail_count=2)
    root = {"events": log, "current": tail[0]}
    target = path(("key", "current"))
    owner = path(("key", "events"), ("index", CHUNK_SIZE))
    before = root["current"]
    if close_reader:
        reader.close()
    else:
        store.close()
    with pytest.raises(StoreError):
        _restore_identity(
            root, [(target, owner)], mutable_event_tail_only=True
        )
    assert root["current"] is before
    if close_reader:
        store.close()


def test_restore_parent_and_descendant_aliases_in_both_directions(tmp_path):
    store = make_store(tmp_path / "parent-descendant.sqlite")
    reader = None
    try:
        append_segments(store, 1)
        reader = SealedEventPrefix(store)
        first = CHUNK_SIZE
        log_child = []
        log_parent = {"child": log_child}
        current_child = []
        current_parent = {"child": current_child}
        tail_event = event(
            first + 1,
            year=100,
            data={"payload": log_parent},
        )
        log = EventLog.from_disk_prefix(reader, [tail_event])
        root = {"events": log, "current": current_parent}

        log_parent_path = path(
            ("key", "events"),
            ("index", first),
            ("field", "data"),
            ("key", "payload"),
        )
        current_parent_path = path(("key", "current"))
        log_child_path = log_parent_path + (("key", "child"),)
        current_child_path = current_parent_path + (("key", "child"),)
        links = [
            (log_parent_path, current_parent_path),
            (current_child_path, log_child_path),
        ]

        assert log_parent is not current_parent
        assert log_child is not current_child
        _restore_identity(
            root, links, mutable_event_tail_only=True
        )
        assert tail_event.data["payload"] is current_parent
        assert tail_event.data["payload"]["child"] is current_child
        assert _at_path(
            root, log_child_path, mutable_event_tail_only=True
        ) is current_child
        _verify_identity_graph(
            root, links, mutable_event_tail_only=True
        )
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_restore_mutable_tail_event_reference_preserves_log_boundaries(tmp_path):
    store = make_store(tmp_path / "tail-relink.sqlite")
    reader = None
    try:
        next_id = append_segments(store, 1)
        reader = SealedEventPrefix(store)
        pending = events(next_id, CHUNK_SIZE, sealed=True)
        first_tail = next_id + CHUNK_SIZE
        original = event(first_tail, year=900, data={"v": [1, 2]})
        log = EventLog.from_disk_prefix(
            reader,
            [*pending, original],
            pending_sealed_events=CHUNK_SIZE,
        )
        replacement = event(first_tail, year=900, data={"v": [1, 2]})
        root = {"events": log, "current": replacement}
        log_id = id(log)
        before = frozen_identity_state(log)

        target = path(("key", "events"), ("index", first_tail - 1))
        owner = path(("key", "current"))
        _restore_identity(
            root, [(target, owner)], mutable_event_tail_only=True
        )

        assert id(log) == log_id
        assert log._tail[0] is replacement
        assert log[first_tail - 1] is replacement
        assert frozen_identity_state(log) == before
        _verify_identity_graph(
            root, [(target, owner)], mutable_event_tail_only=True
        )
    finally:
        if reader is not None:
            reader.close()
        store.close()


@pytest.mark.parametrize(
    "replacement_factory,match",
    [
        (lambda current, index: {"not": "event"}, "exact Event"),
        (
            lambda current, index: event(
                index + 2, year=current.year, data=copy.deepcopy(current.data)
            ),
            "stable event ID",
        ),
        (
            lambda current, index: event(
                index + 1, year=current.year + 1, data=copy.deepcopy(current.data)
            ),
            "event year",
        ),
        (
            lambda current, index: event(
                index + 1,
                year=current.year,
                data=copy.deepcopy(current.data),
                sealed=True,
            ),
            "sealed Event",
        ),
    ],
)
def test_private_tail_relink_rejects_invalid_replacements(
    replacement_factory, match
):
    current = event(1, year=7, data={"x": 1})
    log = EventLog([current])
    replacement = replacement_factory(current, 0)
    with pytest.raises(ValueError, match=match):
        log._relink_mutable_tail(0, replacement)
    assert log._tail[0] is current


def test_sealed_event_outside_log_remains_current_but_log_path_is_excluded():
    mutable = event(1, year=0)
    sealed = event(2, year=0, sealed=True)
    log = EventLog([mutable, sealed])
    root = {"events": log, "sealed_a": sealed, "sealed_b": sealed}
    a = path(("key", "sealed_a"))
    b = path(("key", "sealed_b"))
    log_path = path(("key", "events"), ("index", 1))

    _verify_identity_graph(
        root, [(b, a)], mutable_event_tail_only=True
    )
    groups = _complete_identity_groups(
        root, mutable_event_tail_only=True
    )
    assert set(groups[id(sealed)]) == {a, b}
    assert _at_path(root, a, mutable_event_tail_only=True) is sealed
    with pytest.raises(StoreFormatError, match="sealed EventLog history"):
        _at_path(root, log_path, mutable_event_tail_only=True)


def nan_with_bits(bits):
    return struct.unpack(">d", bits.to_bytes(8, "big"))[0]


def test_exact_typed_copy_check_accepts_matching_nan_bits():
    left = {"v": nan_with_bits(0x7FF8000000000042)}
    right = {"v": nan_with_bits(0x7FF8000000000042)}
    root = {"left": left, "right": right}
    _restore_identity(
        root,
        [(path(("key", "right")), path(("key", "left")))],
        mutable_event_tail_only=True,
    )
    assert root["right"] is left


@pytest.mark.parametrize(
    "left,right",
    [
        (
            {"v": nan_with_bits(0x7FF8000000000042)},
            {"v": nan_with_bits(0x7FF8000000000043)},
        ),
        ({"v": True}, {"v": 1}),
        ({"v": 1}, {"v": 1.0}),
        ({"v": 0.0}, {"v": -0.0}),
    ],
)
def test_exact_typed_copy_check_rejects_representation_mismatches(left, right):
    root = {"left": left, "right": right}
    original = root["right"]
    with pytest.raises(StoreIntegrityError, match="copies disagree"):
        _restore_identity(
            root,
            [(path(("key", "right")), path(("key", "left")))],
            mutable_event_tail_only=True,
        )
    assert root["right"] is original


@pytest.mark.parametrize("late_failure", ["missing", "unsupported"])
def test_complete_restore_batch_validates_before_any_relink(late_failure):
    left = {"x": [1]}
    right = {"x": [1]}
    tuple_copy = ({"y": 2},)
    tuple_owner = {"y": 2}
    root = {
        "left": left,
        "right": right,
        "tuple": tuple_copy,
        "tuple_owner": tuple_owner,
    }
    valid = (path(("key", "right")), path(("key", "left")))
    if late_failure == "missing":
        invalid = (
            path(("key", "missing")),
            path(("key", "tuple_owner")),
        )
        error = StoreFormatError
    else:
        invalid = (
            path(("key", "tuple"), ("index", 0)),
            path(("key", "tuple_owner")),
        )
        error = StoreFormatError

    old_right = root["right"]
    with pytest.raises(error):
        _restore_identity(
            root, [valid, invalid], mutable_event_tail_only=True
        )
    assert root["right"] is old_right
    assert root["right"] is not root["left"]


@pytest.mark.parametrize("disk_backed", [False, True])
def test_late_tail_id_validation_precedes_every_relink(tmp_path, disk_backed):
    store = make_store(tmp_path / "preflight-id.sqlite")
    reader = None
    try:
        original = event(1, year=0)
        if disk_backed:
            initialize_empty_prefix(store)
            reader = SealedEventPrefix(store)
            log = EventLog.from_disk_prefix(reader, [original])
        else:
            log = EventLog([original])
        # Simulate a malformed loaded graph. Equal payload copies alone do
        # not prove an Event's ID agrees with its absolute tail position.
        original.id = 7
        replacement = copy.deepcopy(original)
        left, right = {"v": []}, {"v": []}
        root = {"left": left, "right": right, "events": log,
                "replacement": replacement}
        before = frozen_identity_state(log)
        links = [
            (path(("key", "right")), path(("key", "left"))),
            (path(("key", "events"), ("index", 0)),
             path(("key", "replacement"))),
        ]
        with pytest.raises(ValueError, match="stable event ID"):
            _restore_identity(root, links, mutable_event_tail_only=True)
        assert root["right"] is right
        assert root["right"] is not left
        assert log._tail[0] is original
        assert frozen_identity_state(log) == before
        if reader is not None:
            assert reader.diagnostics().segment_reads == 0
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_projected_verifier_preserves_conflict_cycle_and_unexplained_rejection():
    shared = {}
    root = {"a": shared, "b": shared, "c": shared}
    a = path(("key", "a"))
    b = path(("key", "b"))
    c = path(("key", "c"))

    with pytest.raises(StoreIntegrityError, match="not explained"):
        _verify_identity_graph(
            root, [], mutable_event_tail_only=True
        )
    with pytest.raises(StoreIntegrityError, match="conflicting"):
        _verify_identity_graph(
            root,
            [(b, a), (b, c)],
            mutable_event_tail_only=True,
        )

    cycle = {}
    cycle["self"] = cycle
    with pytest.raises(StoreIntegrityError, match="cycle"):
        _complete_identity_groups(
            cycle, mutable_event_tail_only=True
        )


def test_distinct_whole_logs_rejected_and_shared_log_never_value_compared(
    tmp_path, monkeypatch
):
    store = make_store(tmp_path / "whole-log.sqlite")
    reader = None
    try:
        next_id = append_segments(store, 4)
        reader = SealedEventPrefix(store)
        suffix_a = events(next_id, 2)
        suffix_b = events(next_id, 2)
        log_a = EventLog.from_disk_prefix(reader, suffix_a)
        log_b = EventLog.from_disk_prefix(reader, suffix_b)
        reader.reset_diagnostics()

        def forbidden_iteration(_log):
            raise AssertionError("whole-log alias attempted history comparison")

        monkeypatch.setattr(EventLog, "__iter__", forbidden_iteration)
        a = path(("key", "a"))
        b = path(("key", "b"))

        distinct = {"a": log_a, "b": log_b}
        old_b = distinct["b"]
        with pytest.raises(
            StoreIntegrityError, match="distinct EventLog aliases"
        ):
            _restore_identity(
                distinct, [(b, a)], mutable_event_tail_only=True
            )
        assert distinct["b"] is old_b
        assert reader.diagnostics().segment_reads == 0

        shared = {"a": log_a, "b": log_a}
        _restore_identity(
            shared, [(b, a)], mutable_event_tail_only=True
        )
        assert shared["a"] is shared["b"] is log_a
        _verify_identity_graph(
            shared, [(b, a)], mutable_event_tail_only=True
        )
        assert reader.diagnostics().segment_reads == 0
    finally:
        if reader is not None:
            reader.close()
        store.close()
