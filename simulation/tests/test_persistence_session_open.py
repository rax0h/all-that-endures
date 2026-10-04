import copy
import gc
import sqlite3
import weakref

import pytest

from ate_sim.core import Event, Layer, World
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import (
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    META,
    RECORD_SCHEMA,
    SCHEMA,
    WorldCodec,
    _read_manifest,
    write_snapshot,
)
from ate_sim.persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedPrefixDescriptor,
    _descriptor_value,
    prepare_sealed_append,
)
from ate_sim.persistence_schema import ROOT_FIELDS
from ate_sim.persistence_session import (
    COMMIT_DESCRIPTOR_KEY,
    SESSION_DESCRIPTOR_SCHEMA,
    TAIL_DESCRIPTOR_KEY,
    open_world_session,
    write_cold_snapshot,
)
from ate_sim.persistence_tracking import (
    _BINDINGS,
    _binding,
    bind_snapshot,
)


RULES = "stage-0.5-p3b-live-open-tests"
TOKEN = "abcdef0123456789abcdef0123456789"


def event(event_id, *, year=10, data=None, sealed=False):
    value = Event(
        event_id,
        year,
        "live-open",
        Layer.REALITY,
        (),
        None,
        (),
        {} if data is None else data,
    )
    if sealed:
        value.seal()
    return value


def collection_namespaces():
    return {
        root + "." + name
        for root, names in ROOT_FIELDS.items()
        for name, kind in names.items()
        if kind != "state"
    }


def append_prefix(store, segment_count):
    next_id = 1
    remaining = segment_count
    while remaining:
        count = min(remaining, 4)
        batch = [
            event(i, sealed=True)
            for i in range(
                next_id, next_id + count * CHUNK_SIZE
            )
        ]
        prepared = prepare_sealed_append(store, batch)
        head = store.head_metadata()
        namespaces = tuple(
            sorted(
                set(head["namespaces"])
                | {EVENT_STORAGE, SEALED_EVENTS}
            )
        )
        store.commit(
            prepared.expected_generation,
            prepared.record_changes,
            prepared.new_segments,
            dict(head, namespaces=namespaces),
        )
        next_id += count * CHUNK_SIZE
        remaining -= count


def source_records(tmp_path, total_events, *, wallets=None):
    world = World(843000)
    world.year = 77
    world.next_event = total_events + 1
    if wallets is not None:
        world.currency.wallets = wallets
    path = tmp_path / f"source-{total_events}-{id(world)}.sqlite"
    write_snapshot(world, path, rules_id=RULES)
    store = TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )
    try:
        with store.read_transaction():
            manifest = _read_manifest(store)
            copied = {}
            for namespace in collection_namespaces():
                if namespace == "world.events":
                    continue
                copied[namespace] = store.read_records(
                    namespace, expected_record_schema=RECORD_SCHEMA
                )
            head = store.head_metadata()
    finally:
        store.close()
    return manifest, copied, head


def build_cold_path(
    tmp_path,
    *,
    disk_segments=1,
    pending_chunks=0,
    tail_count=3,
    wallets=None,
    tail_payload=None,
    identity_links=(),
    individually_sealed=(),
):
    disk_events = disk_segments * CHUNK_SIZE
    sealed_events = disk_events + pending_chunks * CHUNK_SIZE
    total_events = sealed_events + tail_count
    manifest, copied, source_head = source_records(
        tmp_path, total_events, wallets=wallets
    )
    path = tmp_path / (
        f"live-{disk_segments}-{pending_chunks}-{tail_count}-"
        f"{len(identity_links)}-{id(copied)}.sqlite"
    )
    store = TransactionalStore.create(
        path,
        simulation_schema=SCHEMA,
        rules_id=RULES,
        codec=WorldCodec(identity_links_recorded=True),
    )
    try:
        append_prefix(store, disk_segments)
        suffix = []
        for index in range(disk_events, total_events):
            data = (
                copy.deepcopy(tail_payload)
                if index == sealed_events and tail_payload is not None
                else {"index": index}
            )
            value = event(index + 1, data=data)
            if index < sealed_events or index in individually_sealed:
                value.seal()
            suffix.append((index, value))

        collections = dict(manifest["collections"])
        collections["world.events"] = (
            "EventLog-disk/v1",
            total_events,
            sealed_events // CHUNK_SIZE,
        )
        cold_manifest = {
            "schema": SCHEMA,
            "collections": collections,
            "identity_storage": "current-links/v1",
            "event_storage": "sealed-prefix-tail/v1",
        }

        changes = []
        for namespace, rows in copied.items():
            for key, value, schema in rows:
                changes.append(
                    RecordChange(
                        namespace, key, value, record_schema=schema
                    )
                )
        for index, value in suffix:
            changes.append(
                RecordChange(
                    "world.events",
                    index,
                    (index, value),
                    record_schema=RECORD_SCHEMA,
                )
            )
        for target, owner in identity_links:
            changes.append(
                RecordChange(
                    IDENTITY_LINKS,
                    target,
                    owner,
                    record_schema=IDENTITY_LINK_SCHEMA,
                )
            )

        prefix_last = 10 if disk_events else None
        overall_last = 10 if total_events else None
        changes.extend([
            RecordChange(
                META,
                "manifest",
                cold_manifest,
                record_schema=RECORD_SCHEMA,
            ),
            RecordChange(
                EVENT_STORAGE,
                DESCRIPTOR_KEY,
                _descriptor_value(
                    SealedPrefixDescriptor(
                        disk_segments, disk_events, prefix_last
                    )
                ),
                record_schema=DESCRIPTOR_SCHEMA,
            ),
            RecordChange(
                EVENT_STORAGE,
                TAIL_DESCRIPTOR_KEY,
                (
                    1,
                    disk_events,
                    sealed_events,
                    total_events,
                    overall_last,
                ),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ),
        ])
        final_generation = store.generation + 1
        changes.append(
            RecordChange(
                EVENT_STORAGE,
                COMMIT_DESCRIPTOR_KEY,
                (1, final_generation, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            )
        )
        namespaces = tuple(
            sorted(
                collection_namespaces()
                | {
                    META,
                    IDENTITY_LINKS,
                    EVENT_STORAGE,
                    SEALED_EVENTS,
                }
            )
        )
        store.commit(
            store.generation,
            changes,
            (),
            {
                "simulation_position": source_head["simulation_position"],
                "seed": source_head["seed"],
                "next_ids": source_head["next_ids"],
                "namespaces": namespaces,
            },
        )
        generation = store.generation
    finally:
        store.close()
    return path, {
        "D": disk_events,
        "F": sealed_events,
        "N": total_events,
        "generation": generation,
    }


@pytest.mark.parametrize(
    "disk_segments,pending_chunks,tail_count",
    [
        (0, 0, 0),
        (0, 0, 3),
        (1, 0, 0),
        (1, 1, 3),
    ],
)
def test_open_world_session_partition_shapes_are_clean_and_lazy(
    tmp_path, disk_segments, pending_chunks, tail_count
):
    path, expected = build_cold_path(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=tail_count,
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        assert session.generation == expected["generation"]
        assert session.dirty == frozenset()
        assert session.deleted == frozenset()
        assert session._pending_identity_current == {}
        assert session._identity_dirty_owners == set()
        stats = session.world.events.storage_stats()
        assert stats["disk_events"] == expected["D"]
        assert stats["pending_sealed_events"] == (
            expected["F"] - expected["D"]
        )
        assert stats["tail_events"] == expected["N"] - expected["F"]
        assert stats["disk_segment_reads"] == 0
        assert stats["disk_cache_segments"] == 0

        assert session.cold_state == "active"
        assert session.generation == expected["generation"]
        assert session.dirty == frozenset()
    finally:
        session.close()


def test_open_rejects_legacy_with_conversion_instruction_and_wrong_rules(
    tmp_path,
):
    path = tmp_path / "legacy.sqlite"
    write_snapshot(World(44), path, rules_id=RULES)
    with pytest.raises(StoreFormatError, match="convert_event_storage"):
        open_world_session(path, rules_id=RULES)
    with pytest.raises(StoreFormatError):
        open_world_session(path, rules_id="wrong-rules")


def test_old_segment_corruption_is_deferred_until_access(tmp_path):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=2, pending_chunks=0, tail_count=2
    )
    db = sqlite3.connect(path)
    db.execute(
        "UPDATE segments SET payload=? WHERE namespace=? AND ordinal=?",
        (b"corrupt", SEALED_EVENTS, 0),
    )
    db.commit()
    db.close()

    session = open_world_session(path, rules_id=RULES)
    try:
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0
        with pytest.raises((StoreIntegrityError, StoreFormatError)):
            _ = session.world.events[0]
    finally:
        session.close()


def test_open_restores_mutable_tail_parent_child_alias_and_tracks_owner(
    tmp_path,
):
    disk_segments = 1
    pending_chunks = 1
    first_tail = (disk_segments + pending_chunks) * CHUNK_SIZE
    wallets = {1: {"shared": {"child": [1, 2, 3]}}}
    tail_payload = {"shared": {"child": [1, 2, 3]}}
    event_parent = (
        ("field", "events"),
        ("index", first_tail),
        ("field", "data"),
        ("key", "shared"),
    )
    wallet_parent = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "shared"),
    )
    event_child = event_parent + (("key", "child"),)
    wallet_child = wallet_parent + (("key", "child"),)
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=2,
        wallets=wallets,
        tail_payload=tail_payload,
        identity_links=[
            (event_parent, wallet_parent),
            (wallet_child, event_child),
        ],
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        tail = session.world.events[first_tail]
        current = session.world.currency.wallets[1]["shared"]
        assert tail.data["shared"] is current
        assert tail.data["shared"]["child"] is current["child"]
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0

        current["child"].append(4)
        assert ("world.currency.wallets", 1) in session.dirty
        assert ("world.events", first_tail) in session.dirty
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0
    finally:
        session.close()


def test_open_restores_mutable_tail_event_alias(tmp_path):
    disk_segments = 1
    first_tail = disk_segments * CHUNK_SIZE
    shared_event = event(first_tail + 1, data={"shared": [1, 2]})
    wallets = {1: {"event": shared_event}}
    event_path = (("field", "events"), ("index", first_tail))
    wallet_path = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "event"),
    )
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=0,
        tail_count=2,
        wallets=wallets,
        tail_payload={"shared": [1, 2]},
        identity_links=[(event_path, wallet_path)],
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        assert (
            session.world.events[first_tail]
            is session.world.currency.wallets[1]["event"]
        )
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0
    finally:
        session.close()


def test_sealing_retires_log_owners_and_reanchors_surviving_current_alias(
    tmp_path,
):
    disk_segments = 1
    first_tail = disk_segments * CHUNK_SIZE
    wallets = {1: {"shared": {"child": [1, 2, 3]}}}
    tail_payload = {"shared": {"child": [1, 2, 3]}}
    event_parent = (
        ("field", "events"),
        ("index", first_tail),
        ("field", "data"),
        ("key", "shared"),
    )
    wallet_parent = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "shared"),
    )
    event_child = event_parent + (("key", "child"),)
    wallet_child = wallet_parent + (("key", "child"),)
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=0,
        tail_count=CHUNK_SIZE + 1,
        wallets=wallets,
        tail_payload=tail_payload,
        identity_links=[
            (event_parent, wallet_parent),
            (wallet_child, event_child),
        ],
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        retained = session.world.events[first_tail]
        retained_ref = weakref.ref(retained)
        shared = session.world.currency.wallets[1]["shared"]
        old_child = shared["child"]
        log_owner = ("world.events", first_tail)
        wallet_owner = ("world.currency.wallets", 1)
        assert retained.data["shared"] is shared
        assert log_owner in session._identity_index.owner_occurrences

        session.world.events.seal_before(11)
        assert retained.__dict__["_sealed"] is True
        assert log_owner not in session._identity_index.owner_occurrences
        assert log_owner not in session._identity_dirty_owners
        assert _binding(retained) is None
        assert log_owner not in old_child._owners
        assert wallet_owner in old_child._owners
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0

        old_child.append(4)
        assert wallet_owner in session.dirty
        assert session.world.currency.wallets[1]["shared"]["child"][-1] == 4

        del retained
        gc.collect()
        assert retained_ref() is None
    finally:
        session.close()


def test_close_is_no_write_and_does_not_read_cold_prefix(tmp_path):
    path, expected = build_cold_path(
        tmp_path, disk_segments=40, pending_chunks=0, tail_count=3
    )
    with open_world_session(path, rules_id=RULES) as session:
        world = session.world
        reader = world.events._disk_prefix
        world.currency.wallets[7] = {"value": 1}
        assert session.dirty
        assert reader.diagnostics().segment_reads == 0
        assert session.store.generation == expected["generation"]
    assert reader.diagnostics().segment_reads == 0
    assert reader.resident_segments == 0

    check = TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )
    try:
        assert check.generation == expected["generation"]
    finally:
        check.close()
    with pytest.raises(StoreError):
        len(world.events)


def test_direct_store_close_invalidates_disk_history(tmp_path):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    session = open_world_session(path, rules_id=RULES)
    session.store.close()
    with pytest.raises(StoreError):
        _ = session.world.events[0]
    with pytest.raises(StoreError):
        session.close()
    assert not session._active


def test_open_failure_after_partial_binding_leaks_no_global_bindings(
    tmp_path, monkeypatch
):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=2
    )
    from ate_sim.persistence_tracking import IncrementalWorldSession

    before = dict(_BINDINGS)
    original = IncrementalWorldSession._bind_root_collection
    calls = {"count": 0}

    def fail_after_some(self, namespace, value, expected):
        calls["count"] += 1
        if calls["count"] == 3:
            raise RuntimeError("injected cold bind failure")
        return original(self, namespace, value, expected)

    monkeypatch.setattr(
        IncrementalWorldSession,
        "_bind_root_collection",
        fail_after_some,
    )
    with pytest.raises(RuntimeError, match="injected cold bind failure"):
        open_world_session(path, rules_id=RULES)
    assert _BINDINGS == before


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_open_close_event_history_bookkeeping_is_constant(tmp_path, segments):
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=segments,
        pending_chunks=1,
        tail_count=3,
    )
    session = open_world_session(path, rules_id=RULES)
    reader = session.world.events._disk_prefix
    try:
        log_owners = {
            owner: rows
            for owner, rows in session._identity_index.owner_occurrences.items()
            if owner[0] == "world.events"
        }
        log_occurrences = sum(len(rows) for rows in log_owners.values())
        stats = session.world.events.storage_stats()
        row = {
            "segments": segments,
            "segment_reads": reader.diagnostics().segment_reads,
            "disk_cache": reader.resident_segments,
            "log_owners": len(log_owners),
            "log_occurrences": log_occurrences,
            "pending": stats["pending_sealed_events"],
            "tail": stats["tail_events"],
        }
        print(
            "P3B_LIVE_OPEN_BOUNDS "
            + " ".join(f"{key}={value}" for key, value in row.items())
        )
        assert row["segment_reads"] == 0
        assert row["disk_cache"] == 0
        assert row["log_owners"] == 3
        assert row["pending"] == CHUNK_SIZE
        assert row["tail"] == 3
    finally:
        session.close()
    assert reader.diagnostics().segment_reads == 0
    assert reader.resident_segments == 0


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_local_alias_mutation_marks_only_affected_owner(tmp_path, groups):
    world = World(99100 + groups)
    for index in range(groups):
        shared = {"values": [index]}
        world.currency.wallets[index] = {
            "left": shared,
            "right": shared,
        }
    path = tmp_path / f"aliases-{groups}.sqlite"
    write_cold_snapshot(world, path, rules_id=RULES)
    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.currency.wallets[0]["left"]["values"].append(-1)
        assert session._identity_dirty_owners == {
            ("world.currency.wallets", 0)
        }
        assert session.dirty == frozenset(
            {("world.currency.wallets", 0)}
        )
        print(
            "P3B_LIVE_OPEN_ALIAS_SCALE "
            f"groups={groups} dirty_owners="
            f"{len(session._identity_dirty_owners)}"
        )
    finally:
        session.close()


def test_legacy_session_save_regression(tmp_path):
    world = World(1234)
    path = tmp_path / "legacy-save.sqlite"
    write_snapshot(world, path, rules_id=RULES)
    with bind_snapshot(world, path, rules_id=RULES) as session:
        before = session.generation
        world.currency.wallets[1] = {"value": 2}
        assert session.save() == before + 1


def test_review_newly_appended_full_chunk_retires_without_identity_refresh(
    tmp_path,
):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=0
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = None
        child = None
        for index in range(CHUNK_SIZE):
            value = event(index + 1, data={"child": []})
            session.world.events.append(value)
            if index == 0:
                first = value
                child = value.data["child"]
        del value
        first_ref = weakref.ref(first)
        owner = ("world.events", 0)

        session.world.events.seal_before(11)

        assert _binding(first) is None
        assert owner not in child._owners
        del first
        del child
        gc.collect()
        assert first_ref() is None
    finally:
        session.close()


def test_review_replaced_tail_child_is_reclaimed_when_chunk_seals(tmp_path):
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=CHUNK_SIZE,
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = session.world.events[0]
        first.data = {"replacement": []}
        child = first.data["replacement"]
        child_ref = weakref.ref(child)

        session.world.events.seal_before(11)

        del child
        gc.collect()
        assert child_ref() is None
    finally:
        session.close()


def test_review_individual_tail_seal_retires_log_identity(tmp_path):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = session.world.events[0]
        owner = ("world.events", 0)
        first.seal()

        assert _binding(first) is None
        assert owner not in session._identity_index.owner_occurrences
        stats = session.world.events.storage_stats()
        assert stats["disk_events"] == 0
        assert stats["pending_sealed_events"] == 0
        assert len(session.world.events._chunks) == 0
    finally:
        session.close()


def test_review_tracked_set_is_reclaimed_when_sole_log_owner_retires(tmp_path):
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=CHUNK_SIZE,
        tail_payload={"items": {1, 2}},
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = session.world.events[0]
        items = first.data["items"]
        items_ref = weakref.ref(items)
        owner = ("world.events", 0)

        session.world.events.seal_before(11)

        assert owner not in items._owners
        del items
        gc.collect()
        assert items_ref() is None
    finally:
        session.close()


def test_review_append_already_sealed_event_has_no_log_identity(tmp_path):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=0
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        value = event(1, sealed=True)
        owner = ("world.events", 0)

        session.world.events.append(value)

        assert len(session.world.events) == 1
        assert session.world.events[0] is value
        assert value.__dict__["_sealed"] is True
        assert _binding(value) is None
        assert owner not in session._identity_index.owner_occurrences
        assert owner in session.dirty
    finally:
        session.close()


def test_review_foreign_append_rejection_is_atomic(tmp_path):
    left_path, _left_expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=0
    )
    right_path, _right_expected = build_cold_path(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=1,
        wallets={1: {"child": []}},
    )
    left = open_world_session(left_path, rules_id=RULES)
    right = open_world_session(right_path, rules_id=RULES)
    try:
        foreign_event = right.world.events[0]
        foreign_child = right.world.currency.wallets[1]["child"]
        right_event_count = len(right.world.events)
        right_dirty = right.dirty
        left_before = (
            len(left.world.events),
            left.dirty,
            frozenset(left._identity_dirty_owners),
            left._manifest_dirty,
            tuple(left.world.events._years),
            tuple(left.world.events._offsets),
            left.world.events._last_year,
        )

        with pytest.raises(StoreError, match="cross-session"):
            left.world.events.append(foreign_event)
        assert (
            len(left.world.events),
            left.dirty,
            frozenset(left._identity_dirty_owners),
            left._manifest_dirty,
            tuple(left.world.events._years),
            tuple(left.world.events._offsets),
            left.world.events._last_year,
        ) == left_before
        assert len(right.world.events) == right_event_count
        assert right.dirty == right_dirty

        fresh = event(1, data={"foreign": foreign_child})
        with pytest.raises(StoreError, match="cross-session"):
            left.world.events.append(fresh)
        assert (
            len(left.world.events),
            left.dirty,
            frozenset(left._identity_dirty_owners),
            left._manifest_dirty,
            tuple(left.world.events._years),
            tuple(left.world.events._offsets),
            left.world.events._last_year,
        ) == left_before

        left.close()
        foreign_child.append(9)
        assert ("world.currency.wallets", 1) in right.dirty
        assert len(right.world.events) == right_event_count
    finally:
        left.close()
        right.close()


def _three_way_tail_alias_fixture(tmp_path, name):
    shared = {"child": [1, 2, 3]}
    wallets = {1: {"left": copy.deepcopy(shared), "right": copy.deepcopy(shared)}}
    first_tail = 0
    event_shared = (
        ("field", "events"),
        ("index", first_tail),
        ("field", "data"),
        ("key", "shared"),
    )
    wallet_left = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "left"),
    )
    wallet_right = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "right"),
    )
    wallet_left_child = wallet_left + (("key", "child"),)
    wallet_right_child = wallet_right + (("key", "child"),)
    event_child = event_shared + (("key", "child"),)
    path, _expected = build_cold_path(
        tmp_path / name,
        disk_segments=0,
        pending_chunks=0,
        tail_count=CHUNK_SIZE,
        wallets=wallets,
        tail_payload={"shared": copy.deepcopy(shared)},
        identity_links=[
            (event_shared, wallet_left),
            (wallet_right, wallet_left),
            (event_child, wallet_left_child),
            (wallet_right_child, wallet_left_child),
        ],
    )
    return path


def test_review_retirement_matches_with_or_without_prior_identity_refresh(
    tmp_path,
):
    outcomes = []
    for refresh_first in (False, True):
        path = _three_way_tail_alias_fixture(
            tmp_path, f"refresh-{refresh_first}"
        )
        session = open_world_session(path, rules_id=RULES)
        try:
            left = session.world.currency.wallets[1]["left"]
            right = session.world.currency.wallets[1]["right"]
            tail = session.world.events[0]
            assert left is right
            assert tail.data["shared"] is left
            if refresh_first:
                session._identity_dirty_owners.add(("world.events", 0))
                session._refresh_identity_index()

            session.world.events.seal_before(11)

            assert left is right
            assert all(
                ("field", "events") not in target
                and ("field", "events") not in owner
                for target, owner in session._live_identity_targets.items()
            )
            assert any(
                ("field", "wallets") in target
                and ("field", "wallets") in owner
                for target, owner in session._live_identity_targets.items()
            )
            left["child"].append(4)
            assert ("world.currency.wallets", 1) in session.dirty
            outcomes.append((
                dict(session._live_identity_targets),
                dict(session._pending_identity_current),
            ))
        finally:
            session.close()
    assert outcomes[0] == outcomes[1]


def test_review_individual_seal_then_chunk_retirement_is_idempotent(
    tmp_path,
):
    wallet_event = event(1, data={"value": 1})
    event_path = (("field", "events"), ("index", 0))
    wallet_path = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
        ("key", "event"),
    )
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=CHUNK_SIZE,
        wallets={1: {"event": wallet_event}},
        tail_payload={"value": 1},
        identity_links=[(event_path, wallet_path)],
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = session.world.events[0]
        wallet_owner = ("world.currency.wallets", 1)
        log_owner = ("world.events", 0)
        assert session.world.currency.wallets[1]["event"] is first

        first.seal()
        binding = _binding(first)
        assert binding is not None
        assert binding.owners == {wallet_owner}
        assert log_owner not in session._identity_index.owner_occurrences

        session.world.events.seal_before(11)
        binding = _binding(first)
        assert binding is not None
        assert binding.owners == {wallet_owner}
        assert session.world.currency.wallets[1]["event"] is first
        assert log_owner not in session._identity_index.owner_occurrences
        assert session.world.events.storage_stats()["disk_segment_reads"] == 0
    finally:
        session.close()


def test_review_detached_former_payload_cannot_resurrect_log_owner(tmp_path):
    path, _expected = build_cold_path(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=1,
        tail_payload={"old": []},
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        first = session.world.events[0]
        owner = ("world.events", 0)
        old_child = first.data["old"]
        first.data = {"replacement": []}
        assert owner not in old_child._owners

        dirty_before = session.dirty
        old_child.append(9)
        assert session.dirty == dirty_before

        first.seal()
        session._refresh_identity_index()
        session._refresh_identity_index()
        assert owner not in session._identity_index.owner_occurrences
        assert owner not in session._identity_dirty_owners
    finally:
        session.close()


def test_review_invalid_id_and_year_append_reject_without_partial_tracking(
    tmp_path,
):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=0
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        baseline = (
            len(session.world.events),
            session.dirty,
            frozenset(session._identity_dirty_owners),
            session._manifest_dirty,
        )
        with pytest.raises(ValueError, match="consecutive stable IDs"):
            session.world.events.append(event(2))
        assert (
            len(session.world.events),
            session.dirty,
            frozenset(session._identity_dirty_owners),
            session._manifest_dirty,
        ) == baseline

        session.world.events.append(event(1, year=10))
        after_valid = (
            len(session.world.events),
            session.dirty,
            frozenset(session._identity_dirty_owners),
            session._manifest_dirty,
            tuple(session.world.events._years),
            tuple(session.world.events._offsets),
            session.world.events._last_year,
        )
        with pytest.raises(ValueError, match="time cannot run backwards"):
            session.world.events.append(event(2, year=9))
        assert (
            len(session.world.events),
            session.dirty,
            frozenset(session._identity_dirty_owners),
            session._manifest_dirty,
            tuple(session.world.events._years),
            tuple(session.world.events._offsets),
            session.world.events._last_year,
        ) == after_valid
    finally:
        session.close()


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_review_append_seal_close_never_reads_cold_segments(
    tmp_path, segments
):
    path, expected = build_cold_path(
        tmp_path,
        disk_segments=segments,
        pending_chunks=0,
        tail_count=0,
    )
    session = open_world_session(path, rules_id=RULES)
    reader = session.world.events._disk_prefix
    try:
        for offset in range(CHUNK_SIZE):
            session.world.events.append(
                event(expected["D"] + offset + 1)
            )
        session.world.events.seal_before(11)
        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
    finally:
        session.close()
    assert reader.diagnostics().segment_reads == 0
    assert reader.resident_segments == 0


@pytest.mark.parametrize("groups", [100, 300, 1000])
def test_review_retirement_work_ignores_unrelated_alias_groups(
    tmp_path, groups
):
    world = World(88100 + groups)
    for index in range(groups):
        shared = {"values": [index]}
        world.currency.wallets[index] = {
            "left": shared,
            "right": shared,
        }
    event_shared = world.currency.wallets[0]["left"]
    world.events = [
        event(1, data={"shared": event_shared})
    ]
    world.event_ids = {1}
    world.next_event = 2
    path = tmp_path / f"retirement-scale-{groups}.sqlite"
    write_cold_snapshot(world, path, rules_id=RULES)

    session = open_world_session(path, rules_id=RULES)
    try:
        session.world.events[0].seal()
        work = dict(session._identity_index.last_retirement_work)
        assert work["owners_requested"] == 1
        assert work["owners_removed"] == 1
        assert work["occurrences_removed"] < 10
        assert work["affected_groups"] < 10
        print(
            "P3B_LIVE_OPEN_RETIRE_SCALE "
            f"groups={groups} "
            f"owners={work['owners_requested']} "
            f"occurrences={work['occurrences_removed']} "
            f"affected={work['affected_groups']}"
        )
    finally:
        session.close()


def test_review_repeated_append_seal_releases_identity_retention(tmp_path):
    path, _expected = build_cold_path(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=0
    )
    session = open_world_session(path, rules_id=RULES)
    try:
        baseline_memo = len(session._memo)
        baseline_bound = len(session._bound_ids)
        next_id = 1
        for _batch in range(2):
            for _offset in range(CHUNK_SIZE):
                value = event(next_id, data={"child": []})
                session.world.events.append(value)
                next_id += 1
            del value
            session.world.events.seal_before(11)
            gc.collect()
            assert len(session._memo) == baseline_memo
            assert len(session._bound_ids) == baseline_bound
            assert not any(
                owner[0] == "world.events"
                for bound in _BINDINGS.values()
                if bound.session is session
                for owner in bound.owners
            )
            assert session.world.events.storage_stats()["disk_segment_reads"] == 0
    finally:
        session.close()
