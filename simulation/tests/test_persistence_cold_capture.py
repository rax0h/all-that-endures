import copy
import gc
import sqlite3
import struct
import weakref

import pytest

from ate_sim.core import Event, Layer, Ref, World
from ate_sim.agency import ActionRecord
from ate_sim.event_log import EventLog
from ate_sim.incremental_store import (
    CodecError,
    NewSegment,
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    COLLECTION_LAYOUT,
    IDENTITY_DELTAS,
    IDENTITY_DELTA_SCHEMA,
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    SCHEMA,
    WorldCodec,
    _complete_identity_groups,
    _read_manifest,
    read_snapshot,
    write_snapshot,
)
from ate_sim.persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedEventPrefix,
    SealedPrefixDescriptor,
    _descriptor_value,
    prepare_sealed_append,
)
from ate_sim.persistence_schema import ROOT_TYPES
from ate_sim.persistence_tracking import IncrementalWorldSession
from ate_sim.persistence_session import (
    COMMIT_DESCRIPTOR_KEY,
    SESSION_DESCRIPTOR_SCHEMA,
    TAIL_DESCRIPTOR_KEY,
    _capture_cold_world,
)


RULES = "stage-0.5-p3b-cold-capture-tests"
TOKEN = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize('case', [
    'boolean_total', 'boolean_chunks', 'float_total', 'float_chunks',
    'float_head_year', 'boolean_head_next_person',
])
def test_cold_capture_rejects_typed_metadata_mismatch(tmp_path, case):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1,
    )
    try:
        metadata = store.head_metadata()
        changes = []
        if case.startswith(('boolean_total', 'boolean_chunks', 'float_total', 'float_chunks')):
            manifest = copy.deepcopy(fixture['manifest'])
            descriptions = {
                'boolean_total': ('EventLog-disk/v1', True, 0),
                'boolean_chunks': ('EventLog-disk/v1', 1, False),
                'float_total': ('EventLog-disk/v1', 1.0, 0),
                'float_chunks': ('EventLog-disk/v1', 1, 0.0),
            }
            manifest['collections']['world.events'] = descriptions[case]
            changes.append(RecordChange(META, 'manifest', manifest, record_schema=RECORD_SCHEMA))
        elif case == 'float_head_year':
            metadata['simulation_position'] = float(metadata['simulation_position'])
        else:
            assert metadata['next_ids']['next_person'] == 1
            metadata['next_ids']['next_person'] = True
        changes.append(RecordChange(
            EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
            (1, store.generation + 1, TOKEN), record_schema=1,
        ))
        store.commit(store.generation, changes, (), metadata)
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                result = _capture_cold_world(store)
                result.prefix.close()
    finally:
        store.close()



def event(event_id, *, year=10, data=None, sealed=False):
    value = Event(
        event_id,
        year,
        "capture",
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
            sorted(set(head["namespaces"]) | {EVENT_STORAGE, SEALED_EVENTS})
        )
        store.commit(
            prepared.expected_generation,
            prepared.record_changes,
            prepared.new_segments,
            dict(head, namespaces=namespaces),
        )
        next_id += count * CHUNK_SIZE
        remaining -= count
    return next_id


def source_records(tmp_path, total_events, *, wallet=None):
    world = World(843000)
    world.year = 77
    world.next_event = total_events + 1
    if wallet is not None:
        world.currency.wallets = {1: wallet}
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


def build_cold_store(
    tmp_path,
    *,
    disk_segments=1,
    pending_chunks=1,
    tail_count=3,
    wallet=None,
    tail_payload=None,
    identity_links=(),
    individually_sealed=(),
):
    disk_events = disk_segments * CHUNK_SIZE
    sealed_events = disk_events + pending_chunks * CHUNK_SIZE
    total_events = sealed_events + tail_count
    manifest, copied, source_head = source_records(
        tmp_path, total_events, wallet=wallet
    )

    path = tmp_path / (
        f"cold-{disk_segments}-{pending_chunks}-{tail_count}-"
        f"{len(identity_links)}-{id(copied)}.sqlite"
    )
    store = TransactionalStore.create(
        path,
        simulation_schema=SCHEMA,
        rules_id=RULES,
        codec=WorldCodec(identity_links_recorded=True),
    )
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
            | {META, IDENTITY_LINKS, EVENT_STORAGE, SEALED_EVENTS}
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
    return store, {
        "D": disk_events,
        "F": sealed_events,
        "N": total_events,
        "suffix": suffix,
        "manifest": cold_manifest,
    }


@pytest.mark.parametrize(
    "disk_segments,pending_chunks,tail_count",
    [
        (0, 0, 0),
        (1, 0, 0),
        (0, 0, 3),
        (0, 6, 2),
        (1, 1, 3),
    ],
)
def test_capture_partition_shapes_and_exact_world(
    tmp_path, disk_segments, pending_chunks, tail_count
):
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=tail_count,
    )
    try:
        with store.read_transaction() as generation:
            capture = _capture_cold_world(store)
            assert capture.generation == generation
            assert capture.prefix.captured_generation == generation
            assert capture.commit_descriptor.captured_generation == generation
            world = capture.world
            assert world.seed == 843000
            assert world.year == 77
            assert world.next_event == fixture["N"] + 1
            assert len(world.events) == fixture["N"]
            stats = world.events.storage_stats()
            assert stats["disk_events"] == fixture["D"]
            assert stats["pending_sealed_events"] == (
                fixture["F"] - fixture["D"]
            )
            assert stats["tail_events"] == fixture["N"] - fixture["F"]
        assert capture.prefix.captured_generation == generation
        if fixture["D"]:
            assert capture.world.events[0].id == 1
        capture.prefix.close()
    finally:
        store.close()


def test_capture_restores_tail_parent_and_descendant_aliases(tmp_path):
    wallet = {"shared": {"child": [1, 2, 3]}}
    tail_payload = {"shared": {"child": [1, 2, 3]}}
    disk_segments = 1
    pending_chunks = 1
    first_tail = (disk_segments + pending_chunks) * CHUNK_SIZE
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
    links = [
        (event_parent, wallet_parent),
        (wallet_child, event_child),
    ]
    store, _fixture = build_cold_store(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=2,
        wallet=wallet,
        tail_payload=tail_payload,
        identity_links=links,
    )
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        world = capture.world
        tail = world.events[first_tail]
        current = world.currency.wallets[1]["shared"]
        assert tail.data["shared"] is current
        assert tail.data["shared"]["child"] is current["child"]
        capture.prefix.close()
    finally:
        store.close()


@pytest.mark.parametrize("history_kind", ["disk", "pending", "sealed_tail"])
@pytest.mark.parametrize("excluded_side", ["target", "owner"])
def test_forbidden_history_identity_paths_fail_before_cold_io(
    tmp_path, monkeypatch, history_kind, excluded_side
):
    disk_segments = 1
    pending_chunks = 1
    individually_sealed = ()
    if history_kind == "disk":
        excluded_index = 0
    elif history_kind == "pending":
        excluded_index = CHUNK_SIZE
    else:
        excluded_index = 2 * CHUNK_SIZE + 1
        individually_sealed = (excluded_index,)
    current = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
    )
    excluded = (
        ("field", "events"),
        ("index", excluded_index),
        ("field", "data"),
    )
    link = (excluded, current) if excluded_side == "target" else (current, excluded)
    seen = {}
    original = SealedEventPrefix.from_active_read_transaction.__func__

    def capture_reader(cls, store):
        reader = original(cls, store)
        seen["reader"] = reader
        return reader

    monkeypatch.setattr(
        SealedEventPrefix,
        "from_active_read_transaction",
        classmethod(capture_reader),
    )
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=pending_chunks,
        tail_count=3,
        wallet={"index": excluded_index},
        identity_links=[link],
        individually_sealed=individually_sealed,
    )
    fixture.pop("suffix", None)
    try:
        store.reset_diagnostics()
        with store.read_transaction():
            with pytest.raises(StoreFormatError, match="sealed EventLog history"):
                _capture_cold_world(store)
            assert store.db.in_transaction
            assert store.checked_head().generation == store.generation
        reader = seen["reader"]
        assert reader.diagnostics().segment_reads == 0
        assert reader.resident_segments == 0
        with pytest.raises(StoreError, match="reader is closed"):
            len(reader)
    finally:
        store.close()


def test_capture_requires_caller_owned_read_transaction(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        before = store.diagnostics()
        with pytest.raises(StoreError, match="caller-owned"):
            _capture_cold_world(store)
        assert store.diagnostics() == before
    finally:
        store.close()


def test_checked_head_detects_post_open_corruption(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        store.db.execute(
            "UPDATE save_head SET seed=seed+1 WHERE singleton=1"
        )
        store.db.commit()
        with store.read_transaction():
            with pytest.raises(
                StoreIntegrityError, match="checksum mismatch"
            ):
                _capture_cold_world(store)
            assert store.db.in_transaction
    finally:
        store.close()


def test_capture_bounds_are_enforced_across_4_40_400_segments(
    tmp_path, monkeypatch
):
    measurements = []
    original_chunk = EventLog._chunk
    original_prefix_iter = SealedEventPrefix.__iter__

    for segments in (4, 40, 400):
        store, fixture = build_cold_store(
            tmp_path,
            disk_segments=segments,
            pending_chunks=1,
            tail_count=3,
        )
        fixture.pop("suffix", None)
        gc.collect()
        sql_segment_touches = []

        def authorizer(action, arg1, arg2, _db, _source):
            if action == sqlite3.SQLITE_READ and arg1 == "segments":
                sql_segment_touches.append((arg1, arg2))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        def forbidden_pending_decode(_self, _number):
            raise AssertionError("cold capture decoded a pending chunk")

        def forbidden_prefix_iteration(_self):
            raise AssertionError("cold capture iterated immutable prefix history")
            yield

        try:
            store.reset_diagnostics()
            store.db.set_authorizer(authorizer)
            monkeypatch.setattr(EventLog, "_chunk", forbidden_pending_decode)
            monkeypatch.setattr(SealedEventPrefix, "__iter__", forbidden_prefix_iteration)
            with store.read_transaction():
                capture = _capture_cold_world(store)
                groups = _complete_identity_groups(
                    capture.world, mutable_event_tail_only=True
                )
                diag = store.diagnostics()
                prefix_diag = capture.prefix.diagnostics()
                stats = capture.world.events.storage_stats()
                measurement = {
                    "segments": segments,
                    "payload_reads": diag.payload_reads,
                    "payload_bytes": diag.payload_read_bytes,
                    "segment_reads": prefix_diag.segment_reads,
                    "disk_cache": prefix_diag.resident_segments,
                    "pending_cache": stats["pending_cache_segments"],
                    "pending_chunks": len(capture.world.events._chunks),
                    "pending_bytes": stats["pending_sealed_bytes"],
                    "tail_events": stats["tail_events"],
                    "year_entries": len(capture.world.events._years),
                    "offset_entries": len(capture.world.events._offsets),
                    "groups": len(groups),
                    "paths": sum(len(v) for v in groups.values()),
                }
                print(
                    "P3B_COLD_CAPTURE_BOUNDS "
                    + " ".join(f"{key}={value}" for key, value in measurement.items())
                )
                measurements.append(measurement)
                assert sql_segment_touches == []
                assert prefix_diag.segment_reads == 0
                assert prefix_diag.resident_segments == 0
                assert stats["pending_cache_segments"] == 0
                assert stats["tail_events"] == 3
                assert stats["disk_segments"] == segments
            store.db.set_authorizer(None)
            monkeypatch.setattr(EventLog, "_chunk", original_chunk)
            monkeypatch.setattr(SealedEventPrefix, "__iter__", original_prefix_iter)

            before_reads = store.diagnostics().payload_reads
            first = capture.world.events[0]
            assert first.id == 1
            after_first = store.diagnostics().payload_reads
            assert after_first == before_reads + 1
            assert capture.world.events[0] is first
            assert store.diagnostics().payload_reads == after_first
            capture.prefix.close()
        finally:
            store.db.set_authorizer(None)
            monkeypatch.setattr(EventLog, "_chunk", original_chunk)
            monkeypatch.setattr(SealedEventPrefix, "__iter__", original_prefix_iter)
            store.close()

    for key in (
        "payload_reads",
        "segment_reads",
        "disk_cache",
        "pending_cache",
        "pending_chunks",
        "tail_events",
        "year_entries",
        "offset_entries",
        "groups",
        "paths",
    ):
        assert len({m[key] for m in measurements}) == 1, (key, measurements)
    assert [m["segments"] for m in measurements] == [4, 40, 400]
    assert measurements[0]["payload_bytes"] <= measurements[1]["payload_bytes"]
    assert measurements[1]["payload_bytes"] <= measurements[2]["payload_bytes"]



def _republish(store, changes=(), *, metadata=None, new_segments=(), update_commit=True):
    changes = list(changes)
    if metadata is None:
        metadata = store.head_metadata()
    if update_commit and not any(
        change.namespace == EVENT_STORAGE
        and change.key == COMMIT_DESCRIPTOR_KEY
        for change in changes
    ):
        changes.append(
            RecordChange(
                EVENT_STORAGE,
                COMMIT_DESCRIPTOR_KEY,
                (1, store.generation + 1, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            )
        )
    return store.commit(
        store.generation,
        changes,
        tuple(new_segments),
        metadata,
    )


def _replace_suffix_event(store, index, value, *, ordinal=None):
    if ordinal is None:
        ordinal = index
    _republish(
        store,
        [
            RecordChange(
                "world.events",
                index,
                (ordinal, value),
                record_schema=RECORD_SCHEMA,
            )
        ],
    )


def _root_object(world, root):
    return world if root == "world" else getattr(world, root.split(".", 1)[1])


def _all_non_event_root_encodings(world):
    codec = WorldCodec(identity_links_recorded=True)
    result = {}
    for root, fields in ROOT_FIELDS.items():
        obj = _root_object(world, root)
        for name, kind in fields.items():
            if kind == "state" or (root == "world" and name == "events"):
                continue
            result[root + "." + name] = codec.encode(getattr(obj, name))
    return result


def _configured_oracle_world(total_events):
    world = World(843000)
    world.year = 77
    world.next_event = total_events + 1
    world.currency.wallets = {
        7: {"nested": [True, 1, 1.0, 0.0, -0.0]},
        2: {"second": {"value": 9}},
        11: {"third": ("x", 3)},
    }
    world.currency.minted = {"iron": 17, "bronze": 2}
    world.genealogy.parents = {9: (4, 5), 3: (1, 2)}
    world.genealogy.children = {1: [3], 2: [3], 4: [9]}
    world.agency.actions = [
        ActionRecord(76, 3, "learn", "curiosity", 0.625, None),
        ActionRecord(77, 9, "work", "wealth", 0.375, 41),
    ]
    world.event_ids = {9, 3, 17}
    world.warfare.tensions = {(3, 9): 0.25, (2, 7): 0.75}
    return world


def _build_configured_cold_store(
    tmp_path, *, disk_segments=1, pending_chunks=1, tail_count=4
):
    d = disk_segments * CHUNK_SIZE
    f = d + pending_chunks * CHUNK_SIZE
    n = f + tail_count
    oracle = _configured_oracle_world(n)
    source_path = tmp_path / f"configured-source-{d}-{f}-{n}.sqlite"
    write_snapshot(oracle, source_path, rules_id=RULES)
    source = TransactionalStore.open(
        source_path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )
    try:
        with source.read_transaction():
            manifest = _read_manifest(source)
            copied = {}
            for namespace in collection_namespaces():
                if namespace == "world.events":
                    continue
                copied[namespace] = source.read_records(
                    namespace, expected_record_schema=RECORD_SCHEMA
                )
            source_head = source.head_metadata()
    finally:
        source.close()

    path = tmp_path / f"configured-cold-{d}-{f}-{n}.sqlite"
    store = TransactionalStore.create(
        path,
        simulation_schema=SCHEMA,
        rules_id=RULES,
        codec=WorldCodec(identity_links_recorded=True),
    )
    append_prefix(store, disk_segments)

    changes = []
    for namespace, rows in copied.items():
        for key, value, schema in rows:
            changes.append(RecordChange(namespace, key, value, record_schema=schema))
    suffix_expectations = {}
    for index in range(d, n):
        value = event(index + 1, year=10, data={"index": index})
        if index < f:
            value.seal()
        changes.append(
            RecordChange(
                "world.events", index, (index, value), record_schema=RECORD_SCHEMA
            )
        )
        suffix_expectations[index] = WorldCodec(
            identity_links_recorded=True
        ).encode(value)

    collections = dict(manifest["collections"])
    collections["world.events"] = (
        "EventLog-disk/v1", n, f // CHUNK_SIZE
    )
    cold_manifest = {
        "schema": SCHEMA,
        "collections": collections,
        "identity_storage": "current-links/v1",
        "event_storage": "sealed-prefix-tail/v1",
    }
    changes.extend(
        [
            RecordChange(META, "manifest", cold_manifest, record_schema=RECORD_SCHEMA),
            RecordChange(
                EVENT_STORAGE,
                DESCRIPTOR_KEY,
                _descriptor_value(
                    SealedPrefixDescriptor(
                        disk_segments, d, 10 if d else None
                    )
                ),
                record_schema=DESCRIPTOR_SCHEMA,
            ),
            RecordChange(
                EVENT_STORAGE,
                TAIL_DESCRIPTOR_KEY,
                (1, d, f, n, 10 if n else None),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ),
            RecordChange(
                EVENT_STORAGE,
                COMMIT_DESCRIPTOR_KEY,
                (1, store.generation + 1, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ),
        ]
    )
    namespaces = tuple(
        sorted(
            collection_namespaces()
            | {META, IDENTITY_LINKS, EVENT_STORAGE, SEALED_EVENTS}
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
    return store, oracle, {"D": d, "F": f, "N": n, "suffix": suffix_expectations}


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "extra",
        "below_d",
        "bool_key",
        "wrong_ordinal",
        "bool_ordinal",
        "wrong_id",
        "bool_id",
        "float_year",
        "decreasing",
        "first_before_prefix",
    ],
)
def test_cold_capture_rejects_malformed_suffix(tmp_path, case):
    disk_segments = 1 if case in ("below_d", "first_before_prefix") else 0
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=disk_segments,
        pending_chunks=0,
        tail_count=12,
    )
    d, n = fixture["D"], fixture["N"]
    try:
        if case == "missing":
            _republish(
                store,
                [RecordChange("world.events", d, delete=True)],
            )
        elif case == "extra":
            _republish(
                store,
                [
                    RecordChange(
                        "world.events",
                        n,
                        (n, event(n + 1)),
                        record_schema=RECORD_SCHEMA,
                    )
                ],
            )
        elif case == "below_d":
            _republish(
                store,
                [
                    RecordChange("world.events", d, delete=True),
                    RecordChange(
                        "world.events",
                        0,
                        (0, event(1)),
                        record_schema=RECORD_SCHEMA,
                    ),
                ],
            )
        elif case == "bool_key":
            _republish(
                store,
                [
                    RecordChange("world.events", 0, delete=True),
                    RecordChange(
                        "world.events",
                        False,
                        (0, event(1)),
                        record_schema=RECORD_SCHEMA,
                    ),
                ],
            )
        elif case == "wrong_ordinal":
            _replace_suffix_event(store, d, event(d + 1), ordinal=d + 1)
        elif case == "bool_ordinal":
            _replace_suffix_event(store, d, event(d + 1), ordinal=True)
        elif case == "wrong_id":
            _replace_suffix_event(store, d, event(d + 2))
        elif case == "bool_id":
            bad = event(d + 1)
            object.__setattr__(bad, "id", True)
            _replace_suffix_event(store, d, bad)
        elif case == "float_year":
            _replace_suffix_event(store, d, event(d + 1, year=10.0))
        elif case == "decreasing":
            _replace_suffix_event(store, d + 7, event(d + 8, year=9))
        elif case == "first_before_prefix":
            _replace_suffix_event(store, d, event(d + 1, year=9))
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _capture_cold_world(store)
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    ["unsealed_pending", "sealed_mutable_pending", "sealed_mutable_tail"],
)
def test_cold_capture_rejects_invalid_sealing(tmp_path, case):
    pending = 1 if "pending" in case else 0
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=0,
        pending_chunks=pending,
        tail_count=2,
        individually_sealed=(0,) if case == "sealed_mutable_tail" else (),
    )
    index = 0
    try:
        bad = event(1)
        if case != "unsealed_pending":
            object.__setattr__(bad, "_sealed", True)
        _replace_suffix_event(store, index, bad)
        with store.read_transaction():
            with pytest.raises(StoreFormatError):
                _capture_cold_world(store)
    finally:
        store.close()


def test_world_codec_rejects_malformed_sealed_flag_before_capture(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        bad = event(1)
        object.__setattr__(bad, "_sealed", 1)
        with pytest.raises(CodecError, match="sealed flag"):
            _republish(
                store,
                [
                    RecordChange(
                        "world.events",
                        0,
                        (0, bad),
                        record_schema=RECORD_SCHEMA,
                    )
                ],
            )
        with store.read_transaction():
            capture = _capture_cold_world(store)
        capture.prefix.close()
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    [
        "missing_prefix",
        "extra_descriptor",
        "bool_d",
        "float_f",
        "bool_n",
        "f_before_d",
        "n_before_f",
        "unaligned_d",
        "unaligned_f",
        "last_year",
        "bad_token",
        "bad_commit_version",
        "bool_commit_generation",
        "generation_mismatch",
        "prefix_tail_mismatch",
        "head_segment_count",
        "suffix_head_count",
        "sealed_namespace_record",
        "events_namespace_segment",
        "bad_overlay_layout",
        "missing_overlay_root",
    ],
)
def test_cold_capture_rejects_descriptor_and_layout_damage(tmp_path, case):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=1, tail_count=2
    )
    d, f, n = fixture["D"], fixture["F"], fixture["N"]
    try:
        changes = []
        new_segments = []
        update_commit = True
        if case == "missing_prefix":
            changes.append(RecordChange(EVENT_STORAGE, DESCRIPTOR_KEY, delete=True))
        elif case == "extra_descriptor":
            changes.append(
                RecordChange(
                    EVENT_STORAGE, "rogue/v1", (1,), record_schema=DESCRIPTOR_SCHEMA
                )
            )
        elif case == "bool_d":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, True, f, n, 10), record_schema=1))
        elif case == "float_f":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, float(f), n, 10), record_schema=1))
        elif case == "bool_n":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, f, False, 10), record_schema=1))
        elif case == "f_before_d":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, d - CHUNK_SIZE, n, 10), record_schema=1))
        elif case == "n_before_f":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, f, f - 1, 10), record_schema=1))
        elif case == "unaligned_d":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d + 1, f, n, 10), record_schema=1))
        elif case == "unaligned_f":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, f + 1, n, 10), record_schema=1))
        elif case == "last_year":
            changes.append(RecordChange(EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, (1, d, f, n, 11), record_schema=1))
        elif case == "bad_token":
            update_commit = False
            changes.append(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, store.generation + 1, "ABC"), record_schema=1))
        elif case == "bad_commit_version":
            update_commit = False
            changes.append(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (2, store.generation + 1, TOKEN), record_schema=1))
        elif case == "bool_commit_generation":
            update_commit = False
            changes.append(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, True, TOKEN), record_schema=1))
        elif case == "generation_mismatch":
            update_commit = False
            changes.append(RecordChange(EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY, (1, store.generation + 99, TOKEN), record_schema=1))
        elif case == "prefix_tail_mismatch":
            changes.append(
                RecordChange(
                    EVENT_STORAGE,
                    DESCRIPTOR_KEY,
                    _descriptor_value(SealedPrefixDescriptor(2, 2 * CHUNK_SIZE, 10)),
                    record_schema=DESCRIPTOR_SCHEMA,
                )
            )
        elif case == "head_segment_count":
            new_segments.append(
                NewSegment(
                    SEALED_EVENTS,
                    1,
                    ("probe-segment",),
                    1,
                    None,
                    None,
                )
            )
        elif case == "suffix_head_count":
            changes.append(
                RecordChange(
                    "world.events",
                    n,
                    (n, event(n + 1)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "sealed_namespace_record":
            changes.append(RecordChange(SEALED_EVENTS, "rogue", 1))
        elif case == "events_namespace_segment":
            new_segments.append(
                NewSegment("world.events", 0, ("probe",), 1, None, None)
            )
        elif case in ("bad_overlay_layout", "missing_overlay_root"):
            layout = copy.deepcopy(fixture["manifest"]["collections"])
            if case == "bad_overlay_layout":
                layout["world.events"] = ("EventLog-disk/v1", True, f // CHUNK_SIZE)
            else:
                layout.pop(next(key for key in layout if key != "world.events"))
            changes.append(
                RecordChange(
                    META,
                    COLLECTION_LAYOUT,
                    layout,
                    record_schema=RECORD_SCHEMA,
                )
            )
        _republish(
            store,
            changes,
            new_segments=new_segments,
            update_commit=update_commit,
        )
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _capture_cold_world(store)
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    [
        "legacy_current",
        "unknown_event",
        "unknown_identity",
        "mixed_manifest",
        "missing_root",
        "unknown_root",
        "identity_delta_authority",
    ],
)
def test_cold_capture_rejects_wrong_modes(tmp_path, case):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        manifest = copy.deepcopy(fixture["manifest"])
        metadata = store.head_metadata()
        changes = []
        if case == "legacy_current":
            manifest.pop("event_storage")
        elif case == "unknown_event":
            manifest["event_storage"] = "unknown/v1"
        elif case == "unknown_identity":
            manifest["identity_storage"] = "unknown/v1"
        elif case == "mixed_manifest":
            manifest["identity_links"] = []
        elif case == "missing_root":
            manifest["collections"].pop(next(iter(manifest["collections"])))
        elif case == "unknown_root":
            manifest["collections"]["world.unknown"] = ("dict", 0, 0)
        elif case == "identity_delta_authority":
            metadata["namespaces"] = tuple(
                sorted(set(metadata["namespaces"]) | {IDENTITY_DELTAS})
            )
            changes.append(
                RecordChange(
                    IDENTITY_DELTAS,
                    0,
                    ("identity-delta/v1", (), ()),
                    record_schema=IDENTITY_DELTA_SCHEMA,
                )
            )
        changes.append(
            RecordChange(META, "manifest", manifest, record_schema=RECORD_SCHEMA)
        )
        _republish(store, changes, metadata=metadata)
        with store.read_transaction():
            if case == "legacy_current":
                with pytest.raises(StoreFormatError, match="requires conversion"):
                    _capture_cold_world(store)
            else:
                with pytest.raises((StoreFormatError, StoreIntegrityError)):
                    _capture_cold_world(store)
    finally:
        store.close()


@pytest.mark.parametrize("namespace", ["world.events", "world.currency.wallets"])
def test_cold_capture_eagerly_rejects_current_record_checksum_damage(
    tmp_path, namespace
):
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=1,
        wallet={"value": 1},
    )
    try:
        row = store.db.execute(
            "SELECT typed_key,payload_checksum FROM records WHERE namespace=? LIMIT 1",
            (namespace,),
        ).fetchone()
        assert row is not None
        typed_key, checksum = row
        damaged = ("1" if checksum[0] == "0" else "0") + checksum[1:]
        store.db.execute(
            "UPDATE records SET payload_checksum=? WHERE namespace=? AND typed_key=?",
            (damaged, namespace, typed_key),
        )
        store.db.commit()
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError, match="checksum mismatch"):
                _capture_cold_world(store)
    finally:
        store.close()


def test_cold_capture_rejects_integer_world_head_counter_disagreement(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        metadata = store.head_metadata()
        metadata["next_ids"]["next_person"] += 1
        _republish(store, metadata=metadata)
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError, match="checked head"):
                _capture_cold_world(store)
    finally:
        store.close()


def test_capture_restores_all_non_event_root_values_and_order(tmp_path):
    store, oracle, fixture = _build_configured_cold_store(tmp_path)
    try:
        expected = _all_non_event_root_encodings(oracle)
        with store.read_transaction():
            capture = _capture_cold_world(store)
        actual = _all_non_event_root_encodings(capture.world)
        assert actual == expected
        assert list(capture.world.currency.wallets) == [7, 2, 11]
        assert list(capture.world.genealogy.parents) == [9, 3]
        capture.prefix.close()
    finally:
        store.close()


def test_capture_restores_exact_event_values_flags_and_special_types(tmp_path):
    store, oracle, fixture = _build_configured_cold_store(
        tmp_path, disk_segments=1, pending_chunks=2, tail_count=4
    )
    d, f, n = fixture["D"], fixture["F"], fixture["N"]
    try:
        special = Event(
            f + 1,
            10,
            "special",
            Layer.CULTURE,
            (Ref("person", 7), Ref("settlement", 2)),
            Ref("settlement", 2),
            (1, CHUNK_SIZE),
            {
                "typed": [
                    True,
                    1,
                    1.0,
                    0.0,
                    -0.0,
                    struct.unpack(">d", bytes.fromhex("7ff8000000000042"))[0],
                ]
            },
        )
        sealed_tail = Event(
            f + 2,
            10,
            "sealed-special",
            Layer.SOCIAL,
            (Ref("person", 11),),
            None,
            (special.id,),
            {"nested": [0.0, -0.0]},
        )
        sealed_tail.seal()
        _republish(
            store,
            [
                RecordChange(
                    "world.events",
                    f,
                    (f, special),
                    record_schema=RECORD_SCHEMA,
                ),
                RecordChange(
                    "world.events",
                    f + 1,
                    (f + 1, sealed_tail),
                    record_schema=RECORD_SCHEMA,
                ),
            ],
        )
        codec = WorldCodec(identity_links_recorded=True)
        with store.read_transaction():
            capture = _capture_cold_world(store)

        for index in range(n):
            actual = capture.world.events[index]
            if index < d:
                expected = event(index + 1, sealed=True)
            elif index == f:
                expected = special
            elif index == f + 1:
                expected = sealed_tail
            else:
                expected = event(
                    index + 1,
                    data={"index": index},
                    sealed=index < f,
                )
            assert codec.encode(actual) == codec.encode(expected)
            assert ("_sealed" in vars(actual)) == ("_sealed" in vars(expected))
            if "_sealed" in vars(expected):
                assert vars(actual)["_sealed"] is vars(expected)["_sealed"]
        capture.prefix.close()
    finally:
        store.close()


def test_capture_failure_after_reader_allocation_closes_reader_only(
    tmp_path, monkeypatch
):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    d = fixture["D"]
    _replace_suffix_event(store, d, event(d + 2))
    seen = {}
    original = SealedEventPrefix.from_active_read_transaction.__func__

    def spy(cls, candidate_store):
        reader = original(cls, candidate_store)
        seen["reader"] = reader
        return reader

    monkeypatch.setattr(
        SealedEventPrefix,
        "from_active_read_transaction",
        classmethod(spy),
    )
    try:
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError):
                _capture_cold_world(store)
            assert store.db.in_transaction
            assert store.checked_head().generation == store.generation
        assert not store._closed
        with pytest.raises(StoreError, match="reader is closed"):
            len(seen["reader"])
    finally:
        store.close()


def test_successful_capture_reader_and_store_lifetime_boundaries(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
            generation = capture.generation
        assert capture.prefix.captured_generation == generation
        assert capture.world.events[0].id == 1
        capture.prefix.close()
        with pytest.raises(StoreError):
            len(capture.world.events)
    finally:
        store.close()

    store2, fixture2 = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    with store2.read_transaction():
        capture2 = _capture_cold_world(store2)
    store2.close()
    with pytest.raises(StoreError):
        len(capture2.world.events)


def test_capture_generation_is_fixed_across_later_publication(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=2, pending_chunks=0, tail_count=1
    )
    writer = None
    try:
        with store.read_transaction() as generation:
            capture = _capture_cold_world(store)
            assert capture.generation == generation
            assert capture.prefix.captured_generation == generation
            assert capture.commit_descriptor.captured_generation == generation

        writer = TransactionalStore.open(
            store.path,
            codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA,
            expected_rules_id=RULES,
        )
        metadata = writer.head_metadata()
        writer.commit(
            writer.generation,
            [
                RecordChange(
                    EVENT_STORAGE,
                    COMMIT_DESCRIPTOR_KEY,
                    (1, writer.generation + 1, "fedcba9876543210fedcba9876543210"),
                    record_schema=SESSION_DESCRIPTOR_SCHEMA,
                )
            ],
            (),
            metadata,
        )
        assert writer.generation == generation + 1
        assert capture.generation == generation
        assert capture.prefix.captured_generation == generation
        assert len(capture.prefix) == fixture["D"]
        assert capture.world.events[0].id == 1

        with store.read_transaction():
            fresh = _capture_cold_world(store)
        assert fresh.generation == generation + 1
        assert fresh.prefix.captured_generation == generation + 1
        fresh.prefix.close()
        capture.prefix.close()
    finally:
        if writer is not None:
            writer.close()
        store.close()


def test_legacy_snapshot_and_binding_apis_reject_cold_but_noncold_still_work(
    tmp_path,
):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    cold_path = store.path
    store.close()
    with pytest.raises(StoreFormatError):
        read_snapshot(cold_path, rules_id=RULES)
    with pytest.raises(StoreFormatError):
        IncrementalWorldSession(World(843000), cold_path, rules_id=RULES)

    ordinary = World(843000)
    ordinary.year = 12
    ordinary_path = tmp_path / "ordinary-p2.sqlite"
    write_snapshot(ordinary, ordinary_path, rules_id=RULES)
    restored = read_snapshot(ordinary_path, rules_id=RULES)
    assert restored.seed == ordinary.seed
    assert restored.year == ordinary.year
    session = IncrementalWorldSession(ordinary, ordinary_path, rules_id=RULES)
    session.close()


def test_capture_releases_decoded_pending_events_but_retains_tail(
    tmp_path, monkeypatch
):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=4, pending_chunks=2, tail_count=3
    )
    fixture.pop("suffix", None)
    gc.collect()
    observed = {}
    original = EventLog.from_disk_prefix.__func__

    def spy(cls, prefix, suffix=(), *, pending_sealed_events=0):
        suffix = list(suffix)
        observed["pending"] = [
            weakref.ref(value)
            for value in suffix[:pending_sealed_events]
        ]
        observed["tail"] = [
            weakref.ref(value)
            for value in suffix[pending_sealed_events:]
        ]
        return original(
            cls,
            prefix,
            suffix,
            pending_sealed_events=pending_sealed_events,
        )

    monkeypatch.setattr(EventLog, "from_disk_prefix", classmethod(spy))
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        gc.collect()
        assert observed["pending"]
        assert all(ref() is None for ref in observed["pending"])
        assert all(ref() is not None for ref in observed["tail"])
        stats = capture.world.events.storage_stats()
        assert stats["pending_sealed_segments"] == 2
        assert stats["pending_cache_segments"] == 0
        assert stats["tail_events"] == 3
        assert capture.prefix.resident_segments == 0
        capture.prefix.close()
    finally:
        store.close()


@pytest.mark.parametrize("damage", ["checksum", "missing"])
def test_lazy_capture_defers_unread_segment_damage_to_access_and_full_verify(
    tmp_path, damage
):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=4, pending_chunks=0, tail_count=1
    )
    try:
        if damage == "checksum":
            checksum = store.db.execute(
                "SELECT payload_checksum FROM segments "
                "WHERE namespace=? AND ordinal=0",
                (SEALED_EVENTS,),
            ).fetchone()[0]
            damaged = ("1" if checksum[0] == "0" else "0") + checksum[1:]
            store.db.execute(
                "UPDATE segments SET payload_checksum=? "
                "WHERE namespace=? AND ordinal=0",
                (damaged, SEALED_EVENTS),
            )
        else:
            store.db.execute(
                "DELETE FROM segments WHERE namespace=? AND ordinal=0",
                (SEALED_EVENTS,),
            )
        store.db.commit()

        with store.read_transaction():
            capture = _capture_cold_world(store)
        assert capture.prefix.diagnostics().segment_reads == 0
        with pytest.raises(StoreIntegrityError):
            _ = capture.world.events[0]
        with pytest.raises(StoreIntegrityError):
            capture.prefix.verify_full()
        capture.prefix.close()
    finally:
        store.close()


def test_healthy_capture_explicit_full_verification_control(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=4, pending_chunks=0, tail_count=1
    )
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        assert capture.prefix.diagnostics().segment_reads == 0
        result = capture.prefix.verify_full()
        assert result["segments"] == 4
        assert result["events"] == 4 * CHUNK_SIZE
        assert capture.prefix.diagnostics().segment_reads == 4
        capture.prefix.close()
    finally:
        store.close()
