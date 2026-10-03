import gc
import weakref

import pytest

from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import (
    RecordChange,
    StoreError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedEventPrefix,
    prepare_sealed_append,
)
from ate_sim.persistence_identity import (
    IdentityOccurrenceIndex,
    iter_mutable_event_items,
    iter_mutable_event_owners,
)
from ate_sim.persistence_schema import RECORD_FIELDS


SCHEMA = "ate-p3b-identity/1"
RULES = "stage-0.5-p3b-identity-tests"


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


def make_event(event_id, *, year=None, data=None, sealed=False):
    if year is None:
        year = (event_id - 1) // 7 - 500
    value = Event(
        event_id,
        year,
        "identity-probe",
        Layer.REALITY,
        (Ref("person", event_id % 13 + 1),),
        None,
        () if event_id == 1 else (event_id - 1,),
        {"n": event_id} if data is None else data,
    )
    if sealed:
        value.seal()
    return value


def events(first_id, count, *, sealed=False, year=None):
    return [
        make_event(i, sealed=sealed, year=year)
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


def cold_log(store, disk_segments, *, pending_chunks=1, tail=4):
    first = append_segments(store, disk_segments)
    reader = SealedEventPrefix(store)
    suffix = events(first, pending_chunks * CHUNK_SIZE + tail)
    for item in suffix[: pending_chunks * CHUNK_SIZE]:
        item.seal()
    if tail > 1:
        suffix[pending_chunks * CHUNK_SIZE + 1].seal()
    log = EventLog.from_disk_prefix(
        reader,
        suffix,
        pending_sealed_events=pending_chunks * CHUNK_SIZE,
    )
    return reader, log, suffix


def index(*, tail_only=True):
    return IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        mutable_event_tail_only=tail_only,
    )


def encoded_links(idx, links):
    return {idx.codec.encode(link) for link in links}


def seed_links_for(idx, *objects):
    links = []
    for obj in objects:
        links.extend(idx._links_for(idx.occurrences[id(obj)][1]))
    idx.seed_explicit_links(links)
    return links


def test_mutable_event_helper_in_memory_absolute_indices_and_holes():
    assert list(iter_mutable_event_items(EventLog())) == []

    source = events(1, CHUNK_SIZE + 4)
    log = EventLog(source)
    log.seal_before(10**9)
    assert len(log._chunks) == 1
    assert len(log._tail) == 4

    log._tail[1].seal()
    rows = list(iter_mutable_event_items(log))
    assert [item[0] for item in rows] == [
        CHUNK_SIZE,
        CHUNK_SIZE + 2,
        CHUNK_SIZE + 3,
    ]
    assert rows[0][1] is log._tail[0]
    assert rows[1][1] is log._tail[2]
    assert rows[2][1] is log._tail[3]

    owners = list(iter_mutable_event_owners(log))
    assert [owner for owner, _event, _path in owners] == [
        ("world.events", CHUNK_SIZE),
        ("world.events", CHUNK_SIZE + 2),
        ("world.events", CHUNK_SIZE + 3),
    ]
    assert [path for _owner, _event, path in owners] == [
        (("field", "events"), ("index", CHUNK_SIZE)),
        (("field", "events"), ("index", CHUNK_SIZE + 2)),
        (("field", "events"), ("index", CHUNK_SIZE + 3)),
    ]

    # The identity helper changes no public EventLog behavior.
    assert [event.id for event in log] == list(range(1, CHUNK_SIZE + 5))


@pytest.mark.parametrize("segments", [4, 40])
def test_real_cold_projection_has_zero_segment_reads_and_zero_pending_decodes(
    tmp_path, segments
):
    store = make_store(tmp_path / f"history-{segments}.sqlite")
    reader = None
    try:
        reader, log, _suffix = cold_log(store, segments)
        forbidden_calls = 0

        def forbidden_chunk(_number):
            nonlocal forbidden_calls
            forbidden_calls += 1
            raise AssertionError("identity projection decoded a pending chunk")

        log._chunk = forbidden_chunk
        reader.reset_diagnostics()
        rows = list(iter_mutable_event_items(log))
        start = (segments + 1) * CHUNK_SIZE
        assert [absolute for absolute, _event in rows] == [
            start,
            start + 2,
            start + 3,
        ]
        assert reader.diagnostics().segment_reads == 0
        assert forbidden_calls == 0
        assert len(log._cache) == 0

        idx = index()
        idx.bootstrap([
            (("probe", 0), log, (("field", "events"),))
        ])
        stats = idx.diagnostics()
        # EventLog root + 3 mutable Events + 3 mutable data dicts.
        assert stats["occurrences"] == 7
        assert stats["paths"] == 7
        assert reader.diagnostics().segment_reads == 0
        assert forbidden_calls == 0
        assert len(log._cache) == 0
        print(
            "P3B_IDENTITY_HISTORY "
            f"segments={segments} helper_events={len(rows)} "
            f"occurrences={stats['occurrences']} paths={stats['paths']} "
            f"cold_reads={reader.diagnostics().segment_reads} "
            f"pending_decodes={forbidden_calls}"
        )
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_default_occurrence_index_rejects_disk_log_before_history_read(tmp_path):
    store = make_store(tmp_path / "default-reject.sqlite")
    reader = None
    try:
        reader, log, _suffix = cold_log(
            store, 1, pending_chunks=0, tail=1
        )
        reader.reset_diagnostics()

        def forbidden_chunk(_number):
            raise AssertionError("default index attempted pending history")

        log._chunk = forbidden_chunk
        idx = index(tail_only=False)
        with pytest.raises(
            ValueError, match="mutable_event_tail_only=True"
        ):
            idx.bootstrap([
                (("probe", 0), log, (("field", "events"),))
            ])
        assert reader.diagnostics().segment_reads == 0
        assert len(log._cache) == 0
        assert idx.owner_occurrences == {}
        assert idx.occurrences == {}
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_root_alias_projection_and_nonlog_sealed_event_remain_current():
    child = []
    shared = {"child": child}
    first = make_event(1, year=0, data=shared)
    second = make_event(2, year=0, data=shared)
    log = EventLog([first, second])
    sealed_elsewhere = make_event(99, year=0, sealed=True)
    root = {
        "left": log,
        "right": log,
        "sealed_a": sealed_elsewhere,
        "sealed_b": sealed_elsewhere,
    }

    idx = index()
    root_path = (("field", "root"),)
    idx.bootstrap([(("root", 0), root, root_path)])

    log_paths = idx.occurrences[id(log)][1]
    assert log_paths == {
        root_path + (("key", "left"),),
        root_path + (("key", "right"),),
    }
    assert len(idx.occurrences[id(shared)][1]) == 4
    assert len(idx.occurrences[id(child)][1]) == 4
    # Sealedness excludes only the occurrence reached through EventLog history.
    assert len(idx.occurrences[id(sealed_elsewhere)][1]) == 2


def test_explicit_link_into_excluded_history_fails_without_cold_read(tmp_path):
    store = make_store(tmp_path / "excluded-link.sqlite")
    reader = None
    try:
        append_segments(store, 4)
        reader = SealedEventPrefix(store)
        shared = {"value": 7}
        tail = make_event(4 * CHUNK_SIZE + 1, data=shared)
        log = EventLog.from_disk_prefix(reader, [tail])
        root = {"events": log, "current": shared}
        root_path = (("field", "root"),)

        reader.reset_diagnostics()
        idx = index()
        idx.bootstrap([(("root", 0), root, root_path)])
        event_data_path = (
            root_path
            + (("key", "events"),)
            + (("index", 4 * CHUNK_SIZE),)
            + (("field", "data"),)
        )
        current_path = root_path + (("key", "current"),)
        idx.seed_explicit_links([(event_data_path, current_path)])
        assert idx.links_by_ident[id(shared)]

        excluded = (
            root_path
            + (("key", "events"),)
            + (("index", 0),)
        )
        with pytest.raises(
            RuntimeError, match="does not match live graph"
        ):
            idx.seed_explicit_links([(excluded, current_path)])
        assert reader.diagnostics().segment_reads == 0
        assert len(log._cache) == 0
    finally:
        if reader is not None:
            reader.close()
        store.close()


@pytest.mark.parametrize("close_reader", [False, True])
def test_helper_suspended_iteration_checks_borrowed_lifetime(
    tmp_path, close_reader
):
    store = make_store(tmp_path / f"lifetime-{close_reader}.sqlite")
    reader = None
    try:
        append_segments(store, 1)
        reader = SealedEventPrefix(store)
        tail = events(CHUNK_SIZE + 1, 2)
        log = EventLog.from_disk_prefix(reader, tail)
        iterator = iter_mutable_event_items(log)
        first_index, first_event = next(iterator)
        assert first_index == CHUNK_SIZE
        assert first_event is tail[0]

        if close_reader:
            reader.close()
        else:
            store.close()

        with pytest.raises(StoreError):
            next(iterator)
        assert first_event.id == CHUNK_SIZE + 1
        assert first_event.__dict__.get("_sealed", False) is False
    finally:
        if reader is not None:
            reader.close()
        store.close()


def test_batched_retirement_after_chunk_seal_reanchors_surviving_aliases():
    child = []
    shared = {"child": child}
    source = events(1, CHUNK_SIZE + 2, year=0)
    source[0].data = shared
    source[1].data = shared
    log = EventLog(source)

    current_a = ("world.current", "a")
    current_b = ("world.current", "b")
    child_owner = ("world.current", "child")
    current_a_path = (("field", "zzcurrent"), ("key", "a"))
    current_b_path = (("field", "zzcurrent"), ("key", "b"))
    child_path = (("field", "zzcurrent"), ("key", "child"))

    idx = index()
    owners = list(iter_mutable_event_owners(log))
    owners.extend([
        (current_a, shared, current_a_path),
        (current_b, shared, current_b_path),
        (child_owner, child, child_path),
    ])
    idx.bootstrap(owners)
    before_links = seed_links_for(idx, shared, child)
    assert any(
        ("field", "events") in path
        for link in before_links
        for path in link
    )

    log.seal_before(1)
    assert len(log._chunks) == 1
    retired = [("world.events", i) for i in range(CHUNK_SIZE)]
    removed, added = idx.retire_owners(retired)
    assert idx.last_retirement_work["owners"] == CHUNK_SIZE
    assert not any(owner in idx.owner_occurrences for owner in retired)

    for group in (
        idx.links_by_ident[id(shared)],
        idx.links_by_ident[id(child)],
    ):
        for target, owner in group:
            assert ("field", "events") not in target
            assert ("field", "events") not in owner

    assert len(idx.links_by_ident[id(shared)]) == 1
    assert len(idx.links_by_ident[id(child)]) == 2
    assert encoded_links(idx, removed).isdisjoint(
        encoded_links(idx, added)
    )

    # Collapse to one survivor, then zero, without rescanning unrelated owners.
    removed2, added2 = idx.retire_owners([current_b])
    assert id(shared) in idx.occurrences
    assert len(idx.occurrences[id(shared)][1]) == 1
    assert id(shared) not in idx.links_by_ident
    assert encoded_links(idx, removed2).isdisjoint(
        encoded_links(idx, added2)
    )

    idx.retire_owners([current_a, child_owner])
    assert id(shared) not in idx.occurrences
    assert id(child) not in idx.occurrences
    assert idx.retire_owners(retired) == ([], [])


def test_individually_sealed_tail_owner_can_be_retired_idempotently():
    log = EventLog(events(1, 3, year=0))
    idx = index()
    idx.bootstrap(iter_mutable_event_owners(log))
    assert set(idx.owner_occurrences) == {
        ("world.events", 0),
        ("world.events", 1),
        ("world.events", 2),
    }

    log._tail[0].seal()
    assert [i for i, _event in iter_mutable_event_items(log)] == [1, 2]
    removed, added = idx.retire_owners([("world.events", 0)])
    assert removed == []
    assert added == []
    assert ("world.events", 0) not in idx.owner_occurrences
    assert idx.retire_owners([
        ("world.events", 0),
        ("world.events", 0),
        ("world.events", 999),
    ]) == ([], [])


def test_retirement_validates_complete_owner_batch_before_mutating():
    shared = {}
    owner_a = ("world.current", "a")
    owner_b = ("world.current", "b")
    path_a = (("field", "current"), ("key", "a"))
    path_b = (("field", "current"), ("key", "b"))
    idx = index()
    idx.bootstrap([
        (owner_a, shared, path_a),
        (owner_b, shared, path_b),
    ])
    seed_links_for(idx, shared)
    before_owners = set(idx.owner_occurrences)
    before_paths = set(idx.path_to_ident)
    before_links = {
        ident: tuple(group)
        for ident, group in idx.links_by_ident.items()
    }

    with pytest.raises(TypeError):
        idx.retire_owners([owner_a, []])

    assert set(idx.owner_occurrences) == before_owners
    assert set(idx.path_to_ident) == before_paths
    assert idx.links_by_ident == before_links


def test_retirement_releases_index_only_event_references_and_does_not_accumulate():
    source = [
        make_event(i, year=(i - 1) // CHUNK_SIZE)
        for i in range(1, 2 * CHUNK_SIZE + 2)
    ]
    log = EventLog(source)
    victim_ref = weakref.ref(source[0])
    source[0] = None

    idx = index()
    idx.bootstrap(iter_mutable_event_owners(log))
    assert len(idx.owner_occurrences) == 2 * CHUNK_SIZE + 1

    log.seal_before(1)
    idx.retire_owners(
        ("world.events", i) for i in range(CHUNK_SIZE)
    )
    gc.collect()
    assert victim_ref() is None
    assert len(idx.owner_occurrences) == CHUNK_SIZE + 1

    log.seal_before(2)
    idx.retire_owners(
        ("world.events", i)
        for i in range(CHUNK_SIZE, 2 * CHUNK_SIZE)
    )
    assert len(idx.owner_occurrences) == 1
    assert set(idx.owner_occurrences) == {
        ("world.events", 2 * CHUNK_SIZE)
    }
    assert all(
        not (
            len(path) >= 2
            and path[0] == ("field", "events")
            and path[1][0] == "index"
            and path[1][1] < 2 * CHUNK_SIZE
        )
        for path in idx.path_to_ident
    )


@pytest.mark.parametrize("unrelated_groups", [100, 300, 1000])
def test_local_retirement_work_does_not_scale_with_unrelated_alias_groups(
    unrelated_groups,
):
    local = {"local": True}
    event = make_event(1, year=0, data=local)
    log = EventLog([event])

    owners = list(iter_mutable_event_owners(log))
    local_a = ("world.current", "local-a")
    local_b = ("world.current", "local-b")
    owners.extend([
        (
            local_a,
            local,
            (("field", "zzcurrent"), ("key", "local-a")),
        ),
        (
            local_b,
            local,
            (("field", "zzcurrent"), ("key", "local-b")),
        ),
    ])

    unrelated = []
    unrelated_owners = []
    for group in range(unrelated_groups):
        shared = {"group": group}
        unrelated.append(shared)
        owner_a = ("world.unrelated", group * 2)
        owner_b = ("world.unrelated", group * 2 + 1)
        unrelated_owners.extend((owner_a, owner_b))
        owners.extend([
            (
                owner_a,
                shared,
                (("field", "unrelated"), ("key", group * 2)),
            ),
            (
                owner_b,
                shared,
                (("field", "unrelated"), ("key", group * 2 + 1)),
            ),
        ])

    idx = index()
    idx.bootstrap(owners)
    all_links = []
    all_links.extend(idx._links_for(idx.occurrences[id(local)][1]))
    for shared in unrelated:
        all_links.extend(idx._links_for(idx.occurrences[id(shared)][1]))
    idx.seed_explicit_links(all_links)

    unrelated_link_state = {
        id(shared): tuple(idx.links_by_ident[id(shared)])
        for shared in unrelated
    }
    row_ids = {
        owner: id(idx.owner_occurrences[owner])
        for owner in unrelated_owners
    }

    calls = 0
    original_links_for = idx._links_for

    def counted(paths):
        nonlocal calls
        calls += 1
        return original_links_for(paths)

    idx._links_for = counted
    removed, added = idx.retire_owners([("world.events", 0)])
    work = idx.last_retirement_work
    assert work == {
        "owners": 1,
        "occurrences": 2,
        "identities": 2,
    }
    assert calls == 1
    assert all(
        id(idx.owner_occurrences[owner]) == row_ids[owner]
        for owner in unrelated_owners
    )
    assert all(
        tuple(idx.links_by_ident[id(shared)])
        == unrelated_link_state[id(shared)]
        for shared in unrelated
    )
    assert encoded_links(idx, removed).isdisjoint(
        encoded_links(idx, added)
    )
    stats = idx.diagnostics()
    print(
        "P3B_IDENTITY_SCALE "
        f"unrelated_groups={unrelated_groups} "
        f"retired_owners={work['owners']} "
        f"removed_occurrences={work['occurrences']} "
        f"affected_groups={work['identities']} "
        f"links_for_calls={calls} "
        f"removed_links={len(removed)} added_links={len(added)} "
        f"total_owners={stats['owners']} total_paths={stats['paths']}"
    )
