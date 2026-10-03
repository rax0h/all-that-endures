import gc
import weakref

import pytest

from ate_sim.core import Event, Layer, Ref, World
from ate_sim.event_log import EventLog, FrozenDict
from ate_sim.incremental_store import StoreError, StoreFormatError
from ate_sim.persistence_adapters import (
    WorldCodec,
    _at_path,
    _complete_identity_groups,
    read_snapshot,
    write_snapshot,
)
from ate_sim.persistence_events import CHUNK_SIZE
from ate_sim.persistence_identity import IdentityOccurrenceIndex
from ate_sim.persistence_schema import RECORD_FIELDS
from ate_sim.persistence_tracking import IncrementalWorldSession, bind_snapshot


RULES = "stage-0.5-p3b-identity-tests"


class ColdPrefixProbe:
    """Descriptor-only prefix that fails if identity code asks for payloads."""

    def __init__(self, segments):
        self.segment_count = segments
        self.event_count = segments * CHUNK_SIZE
        self.last_year = 0 if segments else None
        self.segment_reads = 0

    def __len__(self):
        return self.event_count

    def __getitem__(self, index):
        self.segment_reads += 1
        raise AssertionError("identity traversal read cold event payload")


def make_event(event_id, *, year=1, data=None, sealed=False):
    value = Event(
        event_id,
        year,
        "identity-probe",
        Layer.REALITY,
        (Ref("person", 1),),
        None,
        (),
        {} if data is None else data,
    )
    if sealed:
        value.seal()
    return value


def cold_log(segments, *, pending_chunks=1):
    prefix = ColdPrefixProbe(segments)
    first = segments * CHUNK_SIZE + 1
    suffix = [
        make_event(first + i, sealed=True)
        for i in range(pending_chunks * CHUNK_SIZE)
    ]
    next_id = first + len(suffix)
    mutable_a = make_event(next_id, data={"slot": "a"})
    sealed_tail = make_event(next_id + 1, data={"slot": "sealed"}, sealed=True)
    mutable_b = make_event(next_id + 2, data={"slot": "b"})
    suffix.extend((mutable_a, sealed_tail, mutable_b))
    log = EventLog.from_disk_prefix(
        prefix,
        suffix,
        pending_sealed_events=pending_chunks * CHUNK_SIZE,
    )
    return prefix, log, mutable_a, sealed_tail, mutable_b


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_cold_identity_scan_is_history_independent_and_uses_absolute_tail_paths(
    segments,
):
    prefix, log, mutable_a, sealed_tail, mutable_b = cold_log(segments)
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        cold_event_identity=True,
    )
    owner = ("probe.events", 0)
    root_path = (("field", "events"),)
    index.bootstrap([(owner, log, root_path)])

    rows = index.owner_occurrences[owner]
    paths_by_object = {id(obj): path for _ident, obj, path in rows}
    start = segments * CHUNK_SIZE + CHUNK_SIZE
    assert paths_by_object[id(mutable_a)] == root_path + (("index", start),)
    assert paths_by_object[id(mutable_b)] == root_path + (("index", start + 2),)
    assert id(sealed_tail) not in paths_by_object
    assert prefix.segment_reads == 0
    assert len(log._cache) == 0

    stats = index.diagnostics()
    # EventLog root + two mutable Events + their two mutable data mappings.
    assert stats["occurrences"] == 5
    print(
        "P3B_IDENTITY_HISTORY "
        f"segments={segments} owners={stats['owners']} "
        f"occurrences={stats['occurrences']} identities={stats['identities']} "
        f"cold_reads={prefix.segment_reads} pending_cache={len(log._cache)}"
    )


def test_cold_identity_path_rejects_sealed_history_without_payload_read():
    prefix, log, mutable_a, sealed_tail, mutable_b = cold_log(40)
    world = World(1)
    world.events = log
    start = 40 * CHUNK_SIZE + CHUNK_SIZE

    with pytest.raises(StoreFormatError, match="sealed EventLog history"):
        _at_path(
            world,
            (("field", "events"), ("index", 0)),
            cold_event_identity=True,
        )
    with pytest.raises(StoreFormatError, match="sealed EventLog history"):
        _at_path(
            world,
            (("field", "events"), ("index", start + 1)),
            cold_event_identity=True,
        )
    assert (
        _at_path(
            world,
            (("field", "events"), ("index", start)),
            cold_event_identity=True,
        )
        is mutable_a
    )
    groups = _complete_identity_groups(world, cold_event_identity=True)
    assert id(mutable_a) in groups
    assert id(mutable_b) in groups
    assert id(sealed_tail) not in groups
    assert prefix.segment_reads == 0
    assert len(log._cache) == 0


def _seed_all_links(index):
    links = []
    for _obj, paths in index.occurrences.values():
        links.extend(index._links_for(paths))
    index.seed_explicit_links(links)
    return links


def _has_event_path(link):
    return any(
        component == ("field", "events")
        for path in link
        for component in path
    )


def test_batched_retirement_reanchors_shared_parent_and_child_to_current_owners():
    codec = WorldCodec(identity_links_recorded=True)
    index = IdentityOccurrenceIndex(
        codec, RECORD_FIELDS, cold_event_identity=True
    )
    child = []
    parent = {"child": child}
    log_owner = ("world.events", 50)
    wallet_a = ("world.currency.wallets", 1)
    wallet_b = ("world.currency.wallets", 2)
    log_path = (("field", "events"), ("index", 50), ("field", "data"))
    current_a = (("field", "currency"), ("field", "wallets"), ("key", 1))
    current_b = (("field", "currency"), ("field", "wallets"), ("key", 2))
    index.bootstrap(
        [
            (log_owner, parent, log_path),
            (wallet_a, parent, current_a),
            (wallet_b, parent, current_b),
        ]
    )
    _seed_all_links(index)

    removed, added, affected = index.retire_owners([log_owner])
    assert set(affected) == {id(parent), id(child)}
    assert index.last_retirement_work == {
        "owners": 1,
        "occurrences": 2,
        "identities": 2,
    }
    assert not any(_has_event_path(link) for group in index.links_by_ident.values() for link in group)
    parent_links = index.links_by_ident[id(parent)]
    child_links = index.links_by_ident[id(child)]
    assert len(parent_links) == 1
    assert len(child_links) == 1
    for links in (parent_links, child_links):
        for target, owner in links:
            assert ("field", "events") not in target
            assert ("field", "events") not in owner
    assert removed
    assert added or parent_links


@pytest.mark.parametrize("unrelated_groups", [100, 300, 1000])
def test_batched_retirement_work_is_independent_of_unrelated_alias_groups(
    unrelated_groups,
):
    index = IdentityOccurrenceIndex(
        WorldCodec(identity_links_recorded=True),
        RECORD_FIELDS,
        cold_event_identity=True,
    )
    local = {}
    log_owner = ("world.events", 7)
    owners = [
        (
            log_owner,
            local,
            (("field", "events"), ("index", 7), ("field", "data")),
        ),
        (
            ("world.currency.wallets", -1),
            local,
            (("field", "currency"), ("field", "wallets"), ("key", -1)),
        ),
        (
            ("world.currency.wallets", -2),
            local,
            (("field", "currency"), ("field", "wallets"), ("key", -2)),
        ),
    ]
    for group in range(unrelated_groups):
        shared = {"group": group}
        owners.extend(
            [
                (
                    ("world.currency.wallets", group * 2 + 10),
                    shared,
                    (("field", "currency"), ("field", "wallets"), ("key", group * 2 + 10)),
                ),
                (
                    ("world.currency.wallets", group * 2 + 11),
                    shared,
                    (("field", "currency"), ("field", "wallets"), ("key", group * 2 + 11)),
                ),
            ]
        )
    index.bootstrap(owners)
    _seed_all_links(index)
    before = index.diagnostics()
    index.retire_owners([log_owner])
    work = index.last_retirement_work
    assert work == {"owners": 1, "occurrences": 1, "identities": 1}
    after = index.diagnostics()
    assert after["owners"] == before["owners"] - 1
    print(
        "P3B_IDENTITY_RETIRE "
        f"unrelated_groups={unrelated_groups} "
        f"owner_rows={before['owners']} occurrence_rows={before['occurrences']} "
        f"retire_owners={work['owners']} retire_occurrences={work['occurrences']} "
        f"retire_identities={work['identities']}"
    )


def test_direct_tail_seal_retires_log_owner_and_preserves_current_alias(tmp_path):
    world = World(41)
    shared = {"iron": 3}
    world.currency.wallets = {1: shared}
    world.events = EventLog(
        [make_event(1, year=0, data={"payload": shared})]
    )
    world.next_event = 2
    path = tmp_path / "tail-seal.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(
        world, path, rules_id=RULES, _cold_event_identity=True
    ) as session:
        event = world.events[0]
        retained_child = event.data["payload"]
        assert retained_child is world.currency.wallets[1]
        event.seal()
        assert type(event.data) is FrozenDict
        assert event.data["payload"] is not retained_child
        work = session._identity_index.last_retirement_work
        assert work["owners"] == 1
        assert ("world.events", 0) not in session._identity_index.owner_occurrences
        assert retained_child._owners == {("world.currency.wallets", 1)}

        session.save()
        assert not session.dirty
        retained_child["iron"] = 8
        assert session.dirty == {("world.currency.wallets", 1)}
        session.save()

    restored = read_snapshot(path, rules_id=RULES)
    assert restored.currency.wallets[1]["iron"] == 8
    assert restored.events[0].__dict__.get("_sealed") is True
    assert restored.events[0].data["payload"]["iron"] == 3


def test_full_chunk_seal_retires_log_owners_in_one_batch_and_releases_events(tmp_path):
    world = World(42)
    world.events = EventLog(
        make_event(i, year=0, data={"n": i})
        for i in range(1, CHUNK_SIZE + 1)
    )
    world.next_event = CHUNK_SIZE + 1
    path = tmp_path / "chunk-seal.sqlite"
    write_snapshot(world, path, rules_id=RULES)

    with bind_snapshot(
        world, path, rules_id=RULES, _cold_event_identity=True
    ) as session:
        retained = world.events[0]
        retained_ref = weakref.ref(retained)
        world.events.seal_before(1)
        work = session._identity_index.last_retirement_work
        assert work["owners"] == CHUNK_SIZE
        assert not any(
            owner[0] == "world.events"
            for owner in session._identity_index.owner_occurrences
        )
        assert not session._identity_dirty_owners.intersection(
            {("world.events", i) for i in range(CHUNK_SIZE)}
        )
        del retained
        gc.collect()
        assert retained_ref() is None
        print(
            "P3B_IDENTITY_CHUNK_RETIRE "
            f"owners={work['owners']} occurrences={work['occurrences']} "
            f"identities={work['identities']} memo={len(session._memo)} "
            f"bindings={len(session._bound_ids)}"
        )


def test_cold_identity_mode_keeps_cross_session_alias_rejection(tmp_path):
    left = World(51)
    right = World(52)
    left.currency.wallets = {1: {"iron": 1}}
    right.currency.wallets = {1: {"iron": 2}}
    left_path = tmp_path / "left.sqlite"
    right_path = tmp_path / "right.sqlite"
    write_snapshot(left, left_path, rules_id=RULES)
    write_snapshot(right, right_path, rules_id=RULES)

    with bind_snapshot(
        left, left_path, rules_id=RULES, _cold_event_identity=True
    ), bind_snapshot(
        right, right_path, rules_id=RULES, _cold_event_identity=True
    ):
        with pytest.raises(StoreError, match="cross-session"):
            right.currency.wallets[1] = left.currency.wallets[1]



def test_session_identity_owner_enumerator_uses_absolute_mutable_tail_only():
    prefix, log, mutable_a, sealed_tail, mutable_b = cold_log(40)
    world = World(61)
    world.events = log

    session = object.__new__(IncrementalWorldSession)
    session.world = world
    session._cold_event_identity = True
    session._owner_path = lambda owner: (
        ("namespace", owner[0]),
        ("index", owner[1]),
    )

    event_rows = [
        (owner, child, path)
        for owner, child, path in session._iter_identity_owners()
        if owner[0] == "world.events"
    ]
    start = 40 * CHUNK_SIZE + CHUNK_SIZE
    assert [owner for owner, _child, _path in event_rows] == [
        ("world.events", start),
        ("world.events", start + 2),
    ]
    assert [child for _owner, child, _path in event_rows] == [
        mutable_a,
        mutable_b,
    ]
    assert sealed_tail not in [child for _owner, child, _path in event_rows]
    assert prefix.segment_reads == 0
    assert len(log._cache) == 0
