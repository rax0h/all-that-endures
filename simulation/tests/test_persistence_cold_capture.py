import copy
import gc
import sqlite3
import struct
import weakref

import pytest

from ate_sim.core import Event, Layer, Ref, World
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
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    ROOT_TYPES,
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
import ate_sim.persistence_session as persistence_session
from ate_sim.persistence_session import (
    COMMIT_DESCRIPTOR_KEY,
    SESSION_DESCRIPTOR_SCHEMA,
    TAIL_DESCRIPTOR_KEY,
    _capture_cold_world,
)
from ate_sim.persistence_tracking import bind_snapshot


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


def source_records(tmp_path, total_events, *, wallet=None, source_world=None):
    world = World(843000) if source_world is None else source_world
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
    source_world=None,
):
    disk_events = disk_segments * CHUNK_SIZE
    sealed_events = disk_events + pending_chunks * CHUNK_SIZE
    total_events = sealed_events + tail_count
    manifest, copied, source_head = source_records(
        tmp_path, total_events, wallet=wallet, source_world=source_world
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


@pytest.mark.parametrize("zone", ["disk", "pending", "sealed_tail"])
@pytest.mark.parametrize("direction", ["target", "owner"])
def test_forbidden_historical_identity_links_fail_before_cold_io(
    tmp_path, monkeypatch, zone, direction
):
    first_tail = 2 * CHUNK_SIZE
    index = {
        "disk": 0,
        "pending": CHUNK_SIZE,
        "sealed_tail": first_tail,
    }[zone]
    current = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
    )
    historical = (
        ("field", "events"),
        ("index", index),
        ("field", "data"),
    )
    link = (
        (historical, current)
        if direction == "target"
        else (current, historical)
    )
    store, _fixture = build_cold_store(
        tmp_path,
        disk_segments=1,
        pending_chunks=1,
        tail_count=2,
        wallet={},
        identity_links=[link],
        individually_sealed=(first_tail,),
    )
    original_chunk = EventLog._chunk
    monkeypatch.setattr(
        EventLog,
        "_chunk",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("cold capture decoded pending history")
        ),
    )
    segment_sql = []

    def no_segment_sql(action, arg1, arg2, _database, _source):
        if arg1 == "segments" or arg2 == "segments":
            segment_sql.append((action, arg1, arg2))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    store.db.set_authorizer(no_segment_sql)
    try:
        with store.read_transaction():
            with pytest.raises(
                (StoreFormatError, StoreIntegrityError),
                match="sealed EventLog history",
            ):
                _capture_cold_world(store)
            assert store.db.in_transaction
            assert store.checked_head().generation == store.generation
        assert segment_sql == []
    finally:
        store.db.set_authorizer(None)
        monkeypatch.setattr(EventLog, "_chunk", original_chunk)
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


@pytest.mark.parametrize("segments", [4, 40, 400])
def test_capture_bounds_are_independent_of_prefix_length(
    tmp_path, segments
):
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=segments,
        pending_chunks=1,
        tail_count=3,
    )
    try:
        store.reset_diagnostics()
        with store.read_transaction():
            capture = _capture_cold_world(store)
            groups = _complete_identity_groups(
                capture.world, mutable_event_tail_only=True
            )
            diag = store.diagnostics()
            prefix_diag = capture.prefix.diagnostics()
            stats = capture.world.events.storage_stats()
            print(
                "P3B_COLD_CAPTURE_BOUNDS "
                f"segments={segments} payload_reads={diag.payload_reads} "
                f"payload_bytes={diag.payload_read_bytes} "
                f"segment_reads={prefix_diag.segment_reads} "
                f"disk_cache={prefix_diag.resident_segments} "
                f"pending_cache={stats['pending_cache_segments']} "
                f"pending_bytes={stats['pending_sealed_bytes']} "
                f"tail_events={stats['tail_events']} "
                f"projected_groups={len(groups)} "
                f"projected_paths={sum(len(v) for v in groups.values())}"
            )
            assert prefix_diag.segment_reads == 0
            assert prefix_diag.resident_segments == 0
            assert stats["pending_cache_segments"] == 0
            assert stats["tail_events"] == 3
            assert stats["disk_segments"] == segments
        before_reads = store.diagnostics().payload_reads
        first = capture.world.events[0]
        assert first.id == 1
        after_first = store.diagnostics().payload_reads
        assert after_first == before_reads + 1
        assert capture.world.events[0] is first
        assert store.diagnostics().payload_reads == after_first
        capture.prefix.close()
    finally:
        store.close()


def test_lazy_capture_does_not_scrub_unread_cold_segment(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path,
        disk_segments=4,
        pending_chunks=0,
        tail_count=1,
    )
    try:
        store.db.execute(
            "UPDATE segments SET payload_checksum=(CASE substr(payload_checksum,1,1) WHEN '0' THEN '1' ELSE '0' END) || substr(payload_checksum,2) "
            "WHERE namespace=? AND ordinal=0",
            (SEALED_EVENTS,),
        )
        store.db.commit()
        with store.read_transaction():
            capture = _capture_cold_world(store)
        with pytest.raises(StoreIntegrityError):
            _ = capture.world.events[0]
        capture.prefix.close()
    finally:
        store.close()


def commit_cold_changes(
    store, changes=(), *, new_segments=(), metadata=None
):
    """Publish test-only cold damage while keeping commit generation coherent."""
    expected = store.generation
    next_generation = expected + 1
    rows = list(changes)
    if not any(
        change.namespace == EVENT_STORAGE
        and change.key == COMMIT_DESCRIPTOR_KEY
        for change in rows
    ):
        rows.append(
            RecordChange(
                EVENT_STORAGE,
                COMMIT_DESCRIPTOR_KEY,
                (1, next_generation, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            )
        )
    if metadata is None:
        metadata = store.head_metadata()
    return store.commit(
        expected, rows, tuple(new_segments), metadata
    )


def event_copy_with(value, **updates):
    clone = copy.deepcopy(value)
    for name, replacement in updates.items():
        object.__setattr__(clone, name, replacement)
    return clone


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
        "decreasing_year",
        "below_prefix_year",
    ],
)
def test_cold_capture_rejects_malformed_suffix(tmp_path, case):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=12
    )
    d, n = fixture["D"], fixture["N"]
    try:
        first = store.read_record(
            "world.events", d, expected_record_schema=RECORD_SCHEMA
        )[1]
        second = store.read_record(
            "world.events", d + 1, expected_record_schema=RECORD_SCHEMA
        )[1]
        last = store.read_record(
            "world.events", n - 1, expected_record_schema=RECORD_SCHEMA
        )[1]
        changes = []
        if case == "missing":
            changes.append(RecordChange("world.events", n - 1, delete=True))
        elif case == "extra":
            changes.append(
                RecordChange(
                    "world.events",
                    n,
                    (n, event(n + 1, year=10)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "below_d":
            changes.extend([
                RecordChange("world.events", n - 1, delete=True),
                RecordChange(
                    "world.events",
                    d - 1,
                    (d - 1, event(d, year=10)),
                    record_schema=RECORD_SCHEMA,
                ),
            ])
        elif case == "bool_key":
            changes.extend([
                RecordChange("world.events", n - 1, delete=True),
                RecordChange(
                    "world.events",
                    True,
                    (True, event(2, year=10)),
                    record_schema=RECORD_SCHEMA,
                ),
            ])
        elif case == "wrong_ordinal":
            changes.append(
                RecordChange(
                    "world.events", d, (d + 1, first),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "bool_ordinal":
            changes.append(
                RecordChange(
                    "world.events", d, (True, first),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "wrong_id":
            changes.append(
                RecordChange(
                    "world.events",
                    d,
                    (d, event_copy_with(first, id=d + 2)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "bool_id":
            changes.append(
                RecordChange(
                    "world.events",
                    d,
                    (d, event_copy_with(first, id=True)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "float_year":
            changes.append(
                RecordChange(
                    "world.events",
                    d,
                    (d, event_copy_with(first, year=10.0)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        elif case == "decreasing_year":
            changes.append(
                RecordChange(
                    "world.events",
                    d + 1,
                    (d + 1, event_copy_with(second, year=9)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        else:
            changes.append(
                RecordChange(
                    "world.events",
                    d,
                    (d, event_copy_with(first, year=9)),
                    record_schema=RECORD_SCHEMA,
                )
            )
        commit_cold_changes(store, changes)
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _capture_cold_world(store)
    finally:
        store.close()


def test_cold_capture_rejects_invalid_sealing(tmp_path):
    # Unsealed pending event.
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=1, tail_count=1
    )
    try:
        envelope = store.read_record(
            "world.events", 0, expected_record_schema=RECORD_SCHEMA
        )
        bad = event_copy_with(envelope[1])
        bad.__dict__.pop("_sealed", None)
        commit_cold_changes(
            store,
            [RecordChange(
                "world.events", 0, (0, bad),
                record_schema=RECORD_SCHEMA,
            )],
        )
        with store.read_transaction():
            with pytest.raises(StoreFormatError, match="must already be sealed"):
                _capture_cold_world(store)
    finally:
        store.close()

    # A persisted sealed flag cannot bless mutable data.
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        bad = event(1, data={"still": ["mutable"]})
        object.__setattr__(bad, "_sealed", True)
        commit_cold_changes(
            store,
            [RecordChange(
                "world.events", 0, (0, bad),
                record_schema=RECORD_SCHEMA,
            )],
        )
        with store.read_transaction():
            with pytest.raises(StoreFormatError, match="sealed event data"):
                _capture_cold_world(store)
    finally:
        store.close()

    # WorldCodec itself rejects malformed sealed-flag representation.
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        bad = event(1)
        object.__setattr__(bad, "_sealed", 1)
        with pytest.raises(CodecError, match="sealed flag"):
            commit_cold_changes(
                store,
                [RecordChange(
                    "world.events", 0, (0, bad),
                    record_schema=RECORD_SCHEMA,
                )],
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    [
        "missing_prefix",
        "extra_descriptor",
        "bool_d",
        "bool_f",
        "bool_n",
        "d_after_f",
        "f_after_n",
        "unaligned_d",
        "unaligned_f",
        "last_year",
        "bad_token",
        "bad_version",
        "bad_generation",
        "prefix_head_segments",
        "suffix_head_count",
        "record_in_segment_namespace",
        "segment_in_record_namespace",
        "bad_overlay",
        "overlay_boolean_total",
        "overlay_float_chunks",
    ],
)
def test_cold_capture_rejects_descriptor_and_layout_damage(tmp_path, case):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=1, tail_count=1
    )
    try:
        tail = store.read_record(
            EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
            expected_record_schema=SESSION_DESCRIPTOR_SCHEMA,
        )
        version, d, f, n, last_year = tail
        changes = []
        segments = []
        metadata = None
        if case == "missing_prefix":
            changes.append(RecordChange(EVENT_STORAGE, DESCRIPTOR_KEY, delete=True))
        elif case == "extra_descriptor":
            changes.append(
                RecordChange(
                    EVENT_STORAGE, "unexpected/v1", (1,),
                    record_schema=SESSION_DESCRIPTOR_SCHEMA,
                )
            )
        elif case in {"bool_d", "bool_f", "bool_n"}:
            values = [version, d, f, n, last_year]
            values[{"bool_d": 1, "bool_f": 2, "bool_n": 3}[case]] = True
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY, tuple(values),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "d_after_f":
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
                (1, 2 * CHUNK_SIZE, CHUNK_SIZE, n, last_year),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "f_after_n":
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
                (1, d, 3 * CHUNK_SIZE, n, last_year),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "unaligned_d":
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
                (1, d + 1, f, n, last_year),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "unaligned_f":
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
                (1, d, f + 1, n + 1, last_year),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "last_year":
            changes.append(RecordChange(
                EVENT_STORAGE, TAIL_DESCRIPTOR_KEY,
                (1, d, f, n, last_year + 1),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "bad_token":
            changes.append(RecordChange(
                EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                (1, store.generation + 1, "ABC"),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "bad_version":
            changes.append(RecordChange(
                EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                (2, store.generation + 1, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "bad_generation":
            changes.append(RecordChange(
                EVENT_STORAGE, COMMIT_DESCRIPTOR_KEY,
                (1, store.generation, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            ))
        elif case == "prefix_head_segments":
            segments.append(NewSegment(
                SEALED_EVENTS,
                fixture["D"] // CHUNK_SIZE,
                ("unused-test-segment", ()),
                0,
                None,
                None,
            ))
        elif case == "suffix_head_count":
            changes.append(RecordChange(
                "world.events", n, (n, event(n + 1)),
                record_schema=RECORD_SCHEMA,
            ))
        elif case == "record_in_segment_namespace":
            changes.append(RecordChange(
                SEALED_EVENTS, "unexpected-record", 1,
                record_schema=RECORD_SCHEMA,
            ))
        elif case == "segment_in_record_namespace":
            segments.append(NewSegment(
                "world.event_ids", 0, ("unexpected-segment", ()),
                0, None, None,
            ))
        else:
            manifest = copy.deepcopy(fixture["manifest"])
            if case == "bad_overlay":
                overlay = {"world.events": manifest["collections"]["world.events"]}
            else:
                overlay = copy.deepcopy(manifest["collections"])
                overlay["world.events"] = (
                    ("EventLog-disk/v1", True, f // CHUNK_SIZE)
                    if case == "overlay_boolean_total"
                    else ("EventLog-disk/v1", n, 1.0)
                )
            changes.append(RecordChange(
                META, COLLECTION_LAYOUT, overlay,
                record_schema=RECORD_SCHEMA,
            ))
        commit_cold_changes(
            store, changes, new_segments=segments, metadata=metadata
        )
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _capture_cold_world(store)
    finally:
        store.close()


@pytest.mark.parametrize(
    "case",
    [
        "non_cold",
        "unknown_event_mode",
        "unknown_identity_mode",
        "mixed_keys",
        "missing_root",
        "unknown_root",
        "identity_delta_authority",
    ],
)
def test_cold_capture_rejects_wrong_modes(tmp_path, case):
    if case == "non_cold":
        path = tmp_path / "ordinary-p2c.sqlite"
        write_snapshot(World(843000), path, rules_id=RULES)
        store = TransactionalStore.open(
            path,
            codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA,
            expected_rules_id=RULES,
        )
        try:
            with store.read_transaction():
                with pytest.raises(StoreFormatError, match="requires conversion"):
                    _capture_cold_world(store)
        finally:
            store.close()
        return

    store, fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        manifest = copy.deepcopy(fixture["manifest"])
        changes = []
        metadata = None
        if case == "unknown_event_mode":
            manifest["event_storage"] = "unknown/v9"
        elif case == "unknown_identity_mode":
            manifest["identity_storage"] = "unknown/v9"
        elif case == "mixed_keys":
            manifest["identity_links"] = []
        elif case == "missing_root":
            manifest["collections"].pop("world.event_ids")
        elif case == "unknown_root":
            manifest["collections"]["world.unknown"] = ("list", 0, 0)
        else:
            metadata = store.head_metadata()
            metadata["namespaces"] = tuple(
                sorted(set(metadata["namespaces"]) | {IDENTITY_DELTAS})
            )
            changes.append(RecordChange(
                IDENTITY_DELTAS, 0, ("identity-delta/v1", (), ()),
                record_schema=1,
            ))
        if case != "identity_delta_authority":
            changes.append(RecordChange(
                META, "manifest", manifest, record_schema=RECORD_SCHEMA
            ))
        commit_cold_changes(store, changes, metadata=metadata)
        with store.read_transaction():
            with pytest.raises((StoreFormatError, StoreIntegrityError)):
                _capture_cold_world(store)
    finally:
        store.close()


@pytest.mark.parametrize("namespace", ["world.events", "world.seed"])
def test_cold_capture_eagerly_rejects_current_record_checksum_damage(
    tmp_path, namespace
):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        changed = store.db.execute(
            """
            UPDATE records
            SET payload_checksum =
                (CASE substr(payload_checksum,1,1)
                    WHEN '0' THEN '1' ELSE '0' END)
                || substr(payload_checksum,2)
            WHERE rowid = (
                SELECT rowid FROM records
                WHERE namespace=? LIMIT 1
            )
            """,
            (namespace,),
        ).rowcount
        assert changed == 1
        store.db.commit()
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError, match="checksum mismatch"):
                _capture_cold_world(store)
    finally:
        store.close()


def test_cold_capture_rejects_real_world_head_counter_disagreement(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    try:
        metadata = store.head_metadata()
        metadata["next_ids"] = dict(metadata["next_ids"])
        metadata["next_ids"]["next_event"] += 1
        commit_cold_changes(store, metadata=metadata)
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError, match="World disagrees"):
                _capture_cold_world(store)
    finally:
        store.close()


def test_capture_restores_every_declared_non_event_root_field_exactly(tmp_path):
    source = World(843000)
    source.currency.wallets = {
        9: {"nested": [True, 1, 1.0, -0.0]},
        2: {"order": {"b": 2, "a": 1}},
    }
    source.genealogy.parents = {
        7: (1, 2),
        3: (None, 1),
    }
    source.event_ids = {9, 2, 5}
    store, _fixture = build_cold_store(
        tmp_path,
        disk_segments=0,
        pending_chunks=0,
        tail_count=2,
        source_world=source,
    )
    codec = WorldCodec(identity_links_recorded=True)
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        for root, _cls in ROOT_TYPES.items():
            expected_root = (
                source
                if root == "world"
                else getattr(source, root.split(".")[1])
            )
            actual_root = (
                capture.world
                if root == "world"
                else getattr(capture.world, root.split(".")[1])
            )
            for name, kind in ROOT_FIELDS[root].items():
                if root == "world" and name == "events":
                    continue
                expected = getattr(expected_root, name)
                actual = getattr(actual_root, name)
                assert codec.encode(actual) == codec.encode(expected), (
                    root, name, kind
                )
                if isinstance(expected, dict):
                    assert list(actual) == list(expected)
        capture.prefix.close()
    finally:
        store.close()


def _custom_tail_event(index, *, sealed, year, variant):
    value = Event(
        index + 1,
        year,
        f"capture-{variant}",
        Layer.REALITY,
        (Ref("person", 3), Ref("person", 8)),
        Ref("settlement", 2),
        (1, max(1, index)),
        {
            "typed": [
                True,
                1,
                1.0,
                -0.0,
                struct.unpack(">d", bytes.fromhex("7ff8000000000042"))[0],
            ],
            "variant": variant,
        },
    )
    if sealed:
        value.seal()
    return value


def test_capture_restores_exact_event_values_flags_and_boundaries(tmp_path):
    store, fixture = build_cold_store(
        tmp_path,
        disk_segments=1,
        pending_chunks=1,
        tail_count=3,
        individually_sealed=(2 * CHUNK_SIZE + 1,),
    )
    f = fixture["F"]
    custom = [
        _custom_tail_event(f, sealed=False, year=10, variant="open"),
        _custom_tail_event(f + 1, sealed=True, year=10, variant="sealed"),
        _custom_tail_event(f + 2, sealed=False, year=11, variant="later"),
    ]
    try:
        changes = [
            RecordChange(
                "world.events", f + offset,
                (f + offset, value),
                record_schema=RECORD_SCHEMA,
            )
            for offset, value in enumerate(custom)
        ]
        changes.append(RecordChange(
            EVENT_STORAGE,
            TAIL_DESCRIPTOR_KEY,
            (1, fixture["D"], fixture["F"], fixture["N"], 11),
            record_schema=SESSION_DESCRIPTOR_SCHEMA,
        ))
        commit_cold_changes(store, changes)
        with store.read_transaction():
            capture = _capture_cold_world(store)

        codec = WorldCodec(identity_links_recorded=True)
        # Disk prefix oracle.
        for index in range(fixture["D"]):
            expected = event(index + 1, year=10, sealed=True)
            assert codec.encode(capture.world.events[index]) == codec.encode(expected)
        # Pending suffix oracle.
        for index in range(fixture["D"], fixture["F"]):
            expected = event(
                index + 1, year=10, data={"index": index}, sealed=True
            )
            assert codec.encode(capture.world.events[index]) == codec.encode(expected)
        # Mutable/individually-sealed tail oracle.
        for offset, expected in enumerate(custom):
            actual = capture.world.events[f + offset]
            assert codec.encode(actual) == codec.encode(expected)
            assert ("_sealed" in actual.__dict__) == (
                "_sealed" in expected.__dict__
            )
            assert actual.__dict__.get("_sealed", False) is expected.__dict__.get(
                "_sealed", False
            )
        capture.prefix.close()
    finally:
        store.close()


def test_capture_failure_after_reader_creation_closes_reader_and_preserves_owner(
    tmp_path, monkeypatch
):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    d = fixture["D"]
    envelope = store.read_record(
        "world.events", d, expected_record_schema=RECORD_SCHEMA
    )
    commit_cold_changes(
        store,
        [RecordChange(
            "world.events",
            d,
            (d, event_copy_with(envelope[1], id=d + 2)),
            record_schema=RECORD_SCHEMA,
        )],
    )
    created = []
    original = SealedEventPrefix.from_active_read_transaction

    def capture_reader(cls, target_store):
        reader = original(target_store)
        created.append(reader)
        return reader

    monkeypatch.setattr(
        SealedEventPrefix,
        "from_active_read_transaction",
        classmethod(capture_reader),
    )
    try:
        with store.read_transaction():
            with pytest.raises(StoreIntegrityError, match="ID discontinuity"):
                _capture_cold_world(store)
            assert store.db.in_transaction
            assert store.checked_head().generation == store.generation
            assert len(created) == 1
            with pytest.raises(StoreError, match="reader is closed"):
                len(created[0])
        assert not store._closed
    finally:
        store.close()


def test_capture_success_reader_and_store_lifetime_boundaries(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        assert len(capture.prefix) == CHUNK_SIZE
        assert capture.world.events[0].id == 1
        capture.prefix.close()
        with pytest.raises(StoreError, match="reader is closed"):
            len(capture.world.events)

        with store.read_transaction():
            capture2 = _capture_cold_world(store)
        store.close()
        with pytest.raises(StoreError, match="store is closed"):
            len(capture2.world.events)
    finally:
        if not store._closed:
            store.close()


def test_capture_generation_remains_fixed_across_later_publication(tmp_path):
    store, fixture = build_cold_store(
        tmp_path, disk_segments=1, pending_chunks=0, tail_count=1
    )
    writer = TransactionalStore.open(
        store.path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=RULES,
    )
    try:
        with store.read_transaction() as generation:
            capture = _capture_cold_world(store)
            assert capture.generation == generation
            assert capture.prefix.captured_generation == generation
            assert capture.commit_descriptor.captured_generation == generation
            assert capture.head.generation == generation
        metadata = writer.head_metadata()
        published = writer.commit(
            writer.generation,
            [RecordChange(
                EVENT_STORAGE,
                COMMIT_DESCRIPTOR_KEY,
                (1, writer.generation + 1, TOKEN),
                record_schema=SESSION_DESCRIPTOR_SCHEMA,
            )],
            (),
            metadata,
        )
        assert published == generation + 1
        assert capture.generation == generation
        assert capture.prefix.captured_generation == generation
        assert len(capture.prefix) == fixture["D"]
        assert capture.world.events[0].id == 1
        capture.prefix.close()
    finally:
        writer.close()
        store.close()


def test_legacy_apis_reject_cold_input(tmp_path):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=0, pending_chunks=0, tail_count=1
    )
    path = store.path
    store.close()
    with pytest.raises(StoreFormatError):
        read_snapshot(path, rules_id=RULES)
    with pytest.raises(StoreFormatError):
        bind_snapshot(World(843000), path, rules_id=RULES)


def test_capture_does_not_retain_decoded_pending_events(tmp_path, monkeypatch):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=4, pending_chunks=1, tail_count=3
    )
    pending_refs = []
    tail_refs = []
    original = persistence_session._read_suffix

    def observed_read_suffix(target_store, tail, prefix):
        values = original(target_store, tail, prefix)
        pending = tail.sealed_events - tail.disk_events
        pending_refs.extend(weakref.ref(value) for value in values[:pending])
        tail_refs.extend(weakref.ref(value) for value in values[pending:])
        return values

    monkeypatch.setattr(
        persistence_session, "_read_suffix", observed_read_suffix
    )
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        gc.collect()
        assert pending_refs
        assert all(ref() is None for ref in pending_refs)
        assert len(tail_refs) == 3
        assert all(ref() is not None for ref in tail_refs)
        stats = capture.world.events.storage_stats()
        assert stats["pending_sealed_segments"] == 1
        assert stats["pending_cache_segments"] == 0
        assert stats["tail_events"] == 3
        capture.prefix.close()
    finally:
        store.close()


def test_capture_enforces_4_40_400_read_and_retention_bounds(
    tmp_path, monkeypatch
):
    metrics = []
    original_chunk = EventLog._chunk
    original_prefix_iter = SealedEventPrefix.__iter__

    def forbidden_chunk(*_args):
        raise AssertionError("capture decoded a pending EventLog chunk")

    def forbidden_prefix_iter(*_args):
        raise AssertionError("capture iterated historical prefix")

    for segments in (4, 40, 400):
        store, _fixture = build_cold_store(
            tmp_path,
            disk_segments=segments,
            pending_chunks=1,
            tail_count=3,
        )
        segment_sql = []

        def no_segment_sql(action, arg1, arg2, _database, _source):
            if arg1 == "segments" or arg2 == "segments":
                segment_sql.append((action, arg1, arg2))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        try:
            store.reset_diagnostics()
            store.db.set_authorizer(no_segment_sql)
            monkeypatch.setattr(EventLog, "_chunk", forbidden_chunk)
            monkeypatch.setattr(
                SealedEventPrefix, "__iter__", forbidden_prefix_iter
            )
            with store.read_transaction():
                capture = _capture_cold_world(store)
                groups = _complete_identity_groups(
                    capture.world, mutable_event_tail_only=True
                )
                diagnostics = store.diagnostics()
                prefix = capture.prefix.diagnostics()
                stats = capture.world.events.storage_stats()
                row = {
                    "segments": segments,
                    "payload_reads": diagnostics.payload_reads,
                    "payload_bytes": diagnostics.payload_read_bytes,
                    "segment_reads": prefix.segment_reads,
                    "disk_cache": prefix.resident_segments,
                    "pending_segments": stats["pending_sealed_segments"],
                    "pending_cache": stats["pending_cache_segments"],
                    "pending_bytes": stats["pending_sealed_bytes"],
                    "tail_events": stats["tail_events"],
                    "years": len(capture.world.events._years),
                    "offsets": len(capture.world.events._offsets),
                    "groups": len(groups),
                    "paths": sum(len(paths) for paths in groups.values()),
                }
                metrics.append(row)
                print(
                    "P3B_COLD_CAPTURE_ENFORCED "
                    + " ".join(f"{key}={value}" for key, value in row.items())
                )
            assert segment_sql == []
            assert prefix.segment_reads == 0
            assert prefix.resident_segments == 0
            assert stats["pending_cache_segments"] == 0
            assert stats["pending_sealed_segments"] == 1
            assert stats["tail_events"] == 3

            # Remove capture-time guards before proving first point read/cache.
            store.db.set_authorizer(None)
            monkeypatch.setattr(EventLog, "_chunk", original_chunk)
            monkeypatch.setattr(
                SealedEventPrefix, "__iter__", original_prefix_iter
            )
            before = store.diagnostics().payload_reads
            first = capture.world.events[0]
            assert first.id == 1
            after = store.diagnostics().payload_reads
            assert after == before + 1
            assert capture.world.events[0] is first
            assert store.diagnostics().payload_reads == after
            capture.prefix.close()
        finally:
            store.db.set_authorizer(None)
            monkeypatch.setattr(EventLog, "_chunk", original_chunk)
            monkeypatch.setattr(
                SealedEventPrefix, "__iter__", original_prefix_iter
            )
            store.close()

    assert {row["payload_reads"] for row in metrics} == {metrics[0]["payload_reads"]}
    assert {row["segment_reads"] for row in metrics} == {0}
    assert {row["disk_cache"] for row in metrics} == {0}
    assert {row["pending_segments"] for row in metrics} == {1}
    assert {row["pending_cache"] for row in metrics} == {0}
    assert {row["tail_events"] for row in metrics} == {3}
    assert {row["years"] for row in metrics} == {metrics[0]["years"]}
    assert {row["offsets"] for row in metrics} == {metrics[0]["offsets"]}
    assert {row["groups"] for row in metrics} == {metrics[0]["groups"]}
    assert {row["paths"] for row in metrics} == {metrics[0]["paths"]}


@pytest.mark.parametrize("damage", ["checksum", "missing"])
def test_lazy_capture_defers_unread_segment_damage_but_access_and_scrub_fail(
    tmp_path, damage
):
    store, _fixture = build_cold_store(
        tmp_path, disk_segments=4, pending_chunks=0, tail_count=1
    )
    try:
        if damage == "checksum":
            changed = store.db.execute(
                """
                UPDATE segments
                SET payload_checksum =
                    (CASE substr(payload_checksum,1,1)
                        WHEN '0' THEN '1' ELSE '0' END)
                    || substr(payload_checksum,2)
                WHERE namespace=? AND ordinal=0
                """,
                (SEALED_EVENTS,),
            ).rowcount
        else:
            changed = store.db.execute(
                "DELETE FROM segments WHERE namespace=? AND ordinal=0",
                (SEALED_EVENTS,),
            ).rowcount
        assert changed == 1
        store.db.commit()
        with store.read_transaction():
            capture = _capture_cold_world(store)
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
        result = capture.prefix.verify_full()
        assert result["segments"] == 4
        assert result["events"] == fixture["D"]
        capture.prefix.close()
    finally:
        store.close()
