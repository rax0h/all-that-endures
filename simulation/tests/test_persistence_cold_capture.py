import copy

import pytest

from ate_sim.core import Event, Layer, World
from ate_sim.incremental_store import (
    NewSegment,
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from ate_sim.persistence_adapters import (
    COLLECTION_LAYOUT,
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    SCHEMA,
    WorldCodec,
    _complete_identity_groups,
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


def test_bad_link_into_pending_history_fails_without_cold_read_and_keeps_outer_txn(
    tmp_path,
):
    target = (
        ("field", "currency"),
        ("field", "wallets"),
        ("key", 1),
    )
    owner = (
        ("field", "events"),
        ("index", CHUNK_SIZE),
        ("field", "data"),
    )
    store, _fixture = build_cold_store(
        tmp_path,
        disk_segments=1,
        pending_chunks=1,
        tail_count=1,
        wallet={"index": CHUNK_SIZE},
        identity_links=[(target, owner)],
    )
    try:
        store.reset_diagnostics()
        with store.read_transaction():
            with pytest.raises(Exception):
                _capture_cold_world(store)
            assert store.db.in_transaction
            assert store.generation >= 1
            assert store.diagnostics().payload_reads > 0
        # No segment payload was ever read; a point prefix reader would have
        # incremented payload reads by a segment-sized payload.
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
            "UPDATE segments SET payload_checksum='0' || substr(payload_checksum,2) "
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
