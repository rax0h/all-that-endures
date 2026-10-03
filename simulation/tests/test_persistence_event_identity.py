from dataclasses import dataclass
import gc
from itertools import chain
import weakref

import pytest

from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import StoreError, TransactionalStore
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_events import (
    CHUNK_SIZE,
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


SCHEMA = "ate-p3b-event-identity/1"
RULES = "stage-0.5-p3b-event-identity-tests"


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
        "identity",
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
    return [
        event(i, sealed=sealed)
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


def disk_log(tmp_path, segment_count):
    store = make_store(tmp_path / f"identity-{segment_count}.sqlite")
    next_id = append_segments(store, segment_count)
    reader = SealedEventPrefix(store)
    suffix = events(next_id, CHUNK_SIZE + 4)
    for item in suffix[:CHUNK_SIZE]:
        item.seal()
    suffix[CHUNK_SIZE + 1].seal()
    log = EventLog.from_disk_prefix(
        reader, suffix, pending_sealed_events=CHUNK_SIZE
    )
    return store, reader, log, tuple(suffix[CHUNK_SIZE:])


def seed_all_links(index):
    links = []
    for _obj, paths in index.occurrences.values():
        links.extend(index._links_for(paths))
    index.seed_explicit_links(links)
    return links


def test_mutable_event_helper_equivalence_and_absolute_holes(tmp_path):
    assert list(iter_mutable_event_items(EventLog())) == []

    source = events(1, CHUNK_SIZE + 3)
    for item in source[:CHUNK_SIZE]:
        item.seal()
    source[CHUNK_SIZE + 1].seal()
    log = EventLog(source, pending_sealed_events=CHUNK_SIZE)
    expected = [
        (CHUNK_SIZE, source[CHUNK_SIZE]),
        (CHUNK_SIZE + 2, source[CHUNK_SIZE + 2]),
    ]
    rows = list(iter_mutable_event_items(log))
    assert rows == expected
    assert all(
        actual is original
        for (_i, actual), (_j, original) in zip(rows, expected)
    )
    assert len(list(log)) == CHUNK_SIZE + 3
    assert log[CHUNK_SIZE + 1] is source[CHUNK_SIZE + 1]

    store, reader, cold, tail = disk_log(tmp_path, 4)
    try:
        first = 5 * CHUNK_SIZE
        assert list(iter_mutable_event_items(cold)) == [
            (first, tail[0]),
            (first + 2, tail[2]),
            (first + 3, tail[3]),
        ]
    finally:
        reader.close()
        store.close()


@pytest.mark.parametrize("segment_count", [4, 40])
def test_real_cold_projection_reads_zero_history_and_has_fixed_counts(
    tmp_path, segment_count
):
    store, reader, log, _tail = disk_log(tmp_path, segment_count)
    try:
        reader.reset_diagnostics()

        def forbidden_pending_decode(_number):
            raise AssertionError("identity discovery decoded pending history")

        log._chunk = forbidden_pending_decode
        index = IdentityOccurrenceIndex(
            WorldCodec(identity_links_recorded=True),
            RECORD_FIELDS,
            mutable_event_tail_only=True,
        )
        index.bootstrap([
            (("probe", 0), log, (("field", "events"),)),
        ])
        stats = index.diagnostics()
        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        assert len(log._cache) == 0

        mutable_paths = [
            path
            for _ident, obj, path in index.owner_occurrences[("probe", 0)]
            if type(obj) is Event
        ]
        first = (segment_count + 1) * CHUNK_SIZE
        assert mutable_paths == [
            (("field", "events"), ("index", first)),
            (("field", "events"), ("index", first + 2)),
            (("field", "events"), ("index", first + 3)),
        ]
        print(
            "P3B_IDENTITY_COLD "
            f"segments={segment_count} owners={stats['owners']} "
            f"occurrences={stats['occurrences']} paths={stats['paths']} "
            f"links={stats['links']} reads={reader.diagnostics().segment_reads} "
            f"disk_cache={reader.resident_segments} pending_cache={len(log._cache)}"
        )
    finally:
        reader.close()
        store.close()


def test_default_index_rejects_disk_log_before_history_read(tmp_path):
    store, reader, log, _tail = disk_log(tmp_path, 4)
    try:
        reader.reset_diagnostics()
        log._chunk = lambda _number: (_ for _ in ()).throw(
            AssertionError("pending history was decoded")
        )
        index = IdentityOccurrenceIndex(
            WorldCodec(identity_links_recorded=True), RECORD_FIELDS
        )
        with pytest.raises(ValueError, match="mutable_event_tail_only"):
            index.bootstrap([
                (("probe", 0), log, (("field", "events"),)),
            ])
        assert reader.diagnostics().segment_reads == 0
        assert len(log._cache) == 0
        assert index.owner_occurrences == {}
    finally:
        reader.close()
        store.close()


def test_root_log_aliases_tail_sharing_and_nonlog_sealed_event_survive():
    shared_child = []
    shared_parent = {"child": shared_child}
    mutable = event(1, year=0, data=shared_parent)
    sealed = event(2, year=0, data={"frozen": True}, sealed=True)
    later = event(3, year=0, data={"later": True})
    log = EventLog([mutable, sealed, later])
    root = {
        "log_a": log,
        "log_b": log,
        "parent": shared_parent,
        "child": shared_child,
        "sealed_a": sealed,
        "sealed_b": sealed,
    }
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        mutable_event_tail_only=True,
    )
    index.bootstrap([
        (("root", 0), root, (("field", "root"),)),
    ])

    assert len(index.occurrences[id(log)][1]) == 2
    assert len(index.occurrences[id(shared_parent)][1]) == 3
    # The child appears through both log aliases, directly, and below the
    # separately reachable shared parent.
    assert len(index.occurrences[id(shared_child)][1]) == 4

    sealed_paths = index.occurrences[id(sealed)][1]
    assert len(sealed_paths) == 2
    assert all(("index", 1) not in path for path in sealed_paths)


def test_explicit_link_into_excluded_log_occurrence_fails_without_disk_read(
    tmp_path,
):
    store, reader, log, _tail = disk_log(tmp_path, 4)
    shared = {}
    a = (("field", "current_a"),)
    b = (("field", "current_b"),)
    excluded = (("field", "events"), ("index", 0))
    try:
        reader.reset_diagnostics()
        index = IdentityOccurrenceIndex(
            WorldCodec(identity_links_recorded=True),
            RECORD_FIELDS,
            mutable_event_tail_only=True,
        )
        index.bootstrap([
            (("log", 0), log, (("field", "events"),)),
            (("current", "a"), shared, a),
            (("current", "b"), shared, b),
        ])
        index.seed_explicit_links([(b, a)])
        assert index.links_by_ident[id(shared)] == ((b, a),)

        with pytest.raises(RuntimeError, match="does not match live graph"):
            index.seed_explicit_links([(excluded, a)])
        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        assert len(log._cache) == 0
    finally:
        reader.close()
        store.close()


@pytest.mark.parametrize("close_reader", [False, True])
def test_helper_checks_borrowed_lifetime_when_resumed(
    tmp_path, close_reader
):
    store, reader, log, _tail = disk_log(tmp_path, 4)
    iterator = iter_mutable_event_items(log)
    returned = next(iterator)[1]
    before = (
        returned.id,
        returned.year,
        returned.data["n"],
        returned.__dict__.get("_sealed", False),
    )
    if close_reader:
        reader.close()
    else:
        store.close()
    with pytest.raises(StoreError):
        next(iterator)
    assert (
        returned.id,
        returned.year,
        returned.data["n"],
        returned.__dict__.get("_sealed", False),
    ) == before
    if close_reader:
        store.close()


def test_batched_retirement_after_real_sealing_reanchors_survivors():
    child = []
    parent = {"child": child}
    one_survivor = []
    source = []
    for i in range(1, CHUNK_SIZE + 3):
        year = 0 if i <= CHUNK_SIZE else 1
        data = {"n": i}
        if i == 1:
            data = parent
        elif i == 2:
            data = {"one": one_survivor}
        source.append(event(i, year=year, data=data))
    log = EventLog(source)

    external = [
        (("current", "parent-a"), parent, (("field", "z_parent_a"),)),
        (("current", "parent-b"), parent, (("field", "z_parent_b"),)),
        (("current", "child-a"), child, (("field", "z_child_a"),)),
        (("current", "child-b"), child, (("field", "z_child_b"),)),
        (("current", "one"), one_survivor, (("field", "z_one"),)),
    ]
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        mutable_event_tail_only=True,
    )
    index.bootstrap(chain(iter_mutable_event_owners(log), external))
    seed_all_links(index)

    unique_event = source[2]
    unique_id = id(unique_event)
    log.seal_before(1)
    assert len(log._chunks) == 1
    retired = [("world.events", i) for i in range(CHUNK_SIZE)]
    removed, added = index.retire_owners(retired)

    assert removed
    assert added
    assert unique_id not in index.occurrences
    assert id(parent) in index.occurrences
    assert id(child) in index.occurrences
    assert id(one_survivor) in index.occurrences
    assert len(index.occurrences[id(one_survivor)][1]) == 1
    assert id(one_survivor) not in index.links_by_ident
    parent_paths = index.occurrences[id(parent)][1]
    child_paths = index.occurrences[id(child)][1]
    assert len(parent_paths) == 2
    # Each surviving parent path also contributes a descendant child path,
    # in addition to the two direct child owners.
    assert len(child_paths) == 4
    assert all(("field", "events") not in path for path in parent_paths)
    assert all(("field", "events") not in path for path in child_paths)
    assert len(index.links_by_ident[id(parent)]) == 1
    assert len(index.links_by_ident[id(child)]) == 3

    assert not any(
        owner[0] == "world.events" and owner[1] < CHUNK_SIZE
        for owner in index.owner_occurrences
    )
    assert index.retire_owners(retired) == ([], [])
    assert index.last_retirement_work["owners_removed"] == 0


def test_individually_sealed_tail_owner_retires_without_renumbering():
    log = EventLog([
        event(1, year=0),
        event(2, year=0),
        event(3, year=0),
    ])
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        mutable_event_tail_only=True,
    )
    index.bootstrap(iter_mutable_event_owners(log))
    middle = log[1]
    middle.seal()
    assert [i for i, _e in iter_mutable_event_items(log)] == [0, 2]
    removed, added = index.retire_owners([("world.events", 1)])
    assert added == []
    assert ("world.events", 1) not in index.owner_occurrences
    assert id(middle) not in index.occurrences
    assert removed == []


def test_retirement_validates_full_owner_batch_before_mutation():
    shared = {}
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True), {}
    )
    owner = ("world.test", 1)
    path = (("field", "test"), ("key", 1))
    index.bootstrap([(owner, shared, path)])
    before = index.diagnostics()
    with pytest.raises(TypeError, match="hashable owner iterable"):
        index.retire_owners([owner, ["not", "hashable"]])
    assert index.diagnostics() == before
    assert owner in index.owner_occurrences


@dataclass
class Box:
    payload: object = None


def test_retirement_releases_index_only_references_and_preserves_survivor():
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True), {Box: ("payload",)}
    )
    box = Box()
    ref = weakref.ref(box)
    first = ("world.boxes", 1)
    second = ("world.boxes", 2)
    index.bootstrap([
        (first, box, (("field", "boxes"), ("key", 1))),
        (second, box, (("field", "boxes"), ("key", 2))),
    ])
    seed_all_links(index)
    del box
    gc.collect()
    assert ref() is not None

    index.retire_owners([first])
    gc.collect()
    survivor = ref()
    assert survivor is not None
    assert len(index.occurrences[id(survivor)][1]) == 1
    del survivor

    index.retire_owners([second])
    gc.collect()
    assert ref() is None


def test_repeated_seal_retire_cycles_do_not_accumulate_history_entries():
    source = []
    for i in range(1, 2 * CHUNK_SIZE + 2):
        if i <= CHUNK_SIZE:
            year = 0
        elif i <= 2 * CHUNK_SIZE:
            year = 1
        else:
            year = 2
        source.append(event(i, year=year))
    log = EventLog(source)
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        mutable_event_tail_only=True,
    )
    index.bootstrap(iter_mutable_event_owners(log))

    log.seal_before(1)
    index.retire_owners([
        ("world.events", i) for i in range(CHUNK_SIZE)
    ])
    assert len(log._chunks) == 1
    assert min(owner[1] for owner in index.owner_occurrences) == CHUNK_SIZE

    log.seal_before(2)
    index.retire_owners([
        ("world.events", i)
        for i in range(CHUNK_SIZE, 2 * CHUNK_SIZE)
    ])
    assert len(log._chunks) == 2
    assert set(index.owner_occurrences) == {
        ("world.events", 2 * CHUNK_SIZE)
    }
    assert all(
        (("field", "events"),) != path[:1]
        or path == (
            ("field", "events"), ("index", 2 * CHUNK_SIZE)
        )
        or len(path) > 2
        for path in index.path_to_ident
    )


@pytest.mark.parametrize("unrelated_groups", [100, 300, 1000])
def test_local_retirement_work_is_independent_of_unrelated_alias_groups(
    unrelated_groups,
):
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True), {}
    )
    local = {}
    log_owner = ("world.events", 7)
    owners = [
        (
            log_owner,
            local,
            (("field", "a_events"), ("index", 7)),
        ),
        (
            ("world.current", -1),
            local,
            (("field", "z_current"), ("key", -1)),
        ),
        (
            ("world.current", -2),
            local,
            (("field", "z_current"), ("key", -2)),
        ),
    ]
    for group in range(unrelated_groups):
        shared = {"group": group}
        owners.extend([
            (
                ("world.current", group * 2 + 10),
                shared,
                (("field", "unrelated"), ("key", group * 2 + 10)),
            ),
            (
                ("world.current", group * 2 + 11),
                shared,
                (("field", "unrelated"), ("key", group * 2 + 11)),
            ),
        ])
    index.bootstrap(owners)
    seed_all_links(index)
    before = index.diagnostics()
    removed, added = index.retire_owners([log_owner])
    work = index.last_retirement_work

    assert work["owners_requested"] == 1
    assert work["owners_removed"] == 1
    assert work["occurrences_removed"] == 1
    assert work["affected_groups"] == 1
    assert work["surviving_paths_examined"] == 2
    assert work["removed_links"] == len(removed)
    assert work["added_links"] == len(added)
    assert before["owners"] - index.diagnostics()["owners"] == 1
    print(
        "P3B_IDENTITY_SCALE "
        f"unrelated_groups={unrelated_groups} "
        f"owner_rows={before['owners']} paths={before['paths']} "
        f"owners_requested={work['owners_requested']} "
        f"owners_removed={work['owners_removed']} "
        f"occurrences_removed={work['occurrences_removed']} "
        f"affected_groups={work['affected_groups']} "
        f"surviving_paths={work['surviving_paths_examined']} "
        f"removed_links={work['removed_links']} "
        f"added_links={work['added_links']}"
    )
