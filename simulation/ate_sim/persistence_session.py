"""Internal P3B cold World capture; not a public session API."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .core import Event, Layer, Ref
from .event_log import EventLog
from .incremental_store import (
    CheckedHead,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from .persistence_adapters import (
    COLLECTION_LAYOUT,
    IDENTITY_DELTAS,
    IDENTITY_LINKS,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    ROOT_TYPES,
    SCHEMA,
    WorldCodec,
    _read_cold_manifest,
    _read_current_identity_links,
    _restore_collection,
    _restore_identity,
    _verify_identity_graph,
)
from .persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedEventPrefix,
    SealedPrefixDescriptor,
    _decode_descriptor,
    _validate_sealed_event,
)


TAIL_DESCRIPTOR_KEY = "session-tail/v1"
COMMIT_DESCRIPTOR_KEY = "session-commit/v1"
SESSION_DESCRIPTOR_SCHEMA = 1
COLD_EVENT_KIND = "EventLog-disk/v1"
COLD_EVENT_STORAGE = "sealed-prefix-tail/v1"
_TOKEN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class ColdTailDescriptor:
    disk_events: int
    sealed_events: int
    total_events: int
    last_event_year: int | None


@dataclass(frozen=True)
class ColdCommitDescriptor:
    captured_generation: int
    commit_token: str


@dataclass(frozen=True)
class ColdWorldCapture:
    world: object
    prefix: SealedEventPrefix
    generation: int
    head: CheckedHead
    manifest: dict
    identity_links: tuple
    prefix_descriptor: SealedPrefixDescriptor
    tail_descriptor: ColdTailDescriptor
    commit_descriptor: ColdCommitDescriptor


def _require_active_capture_transaction(store):
    if not isinstance(store, TransactionalStore):
        raise TypeError("store must be a TransactionalStore")
    store._ensure_open()
    if not isinstance(store.codec, WorldCodec):
        raise StoreFormatError("cold World capture requires WorldCodec")
    if (
        not getattr(store, "_active_read_transaction", False)
        or not store.db.in_transaction
    ):
        raise StoreError(
            "_capture_cold_world requires an active caller-owned read transaction"
        )


def _decode_tail_descriptor(value):
    if type(value) is not tuple or len(value) != 5:
        raise StoreFormatError("invalid cold event tail descriptor")
    version, disk_events, sealed_events, total_events, last_year = value
    if (
        type(version) is not int
        or version != 1
        or type(disk_events) is not int
        or type(sealed_events) is not int
        or type(total_events) is not int
    ):
        raise StoreFormatError("invalid cold event tail descriptor")
    if (
        disk_events < 0
        or sealed_events < disk_events
        or total_events < sealed_events
        or disk_events % CHUNK_SIZE
        or sealed_events % CHUNK_SIZE
    ):
        raise StoreIntegrityError("cold event partition counts disagree")
    if total_events == 0:
        if last_year is not None:
            raise StoreIntegrityError("empty cold EventLog has a last year")
    elif type(last_year) is not int:
        raise StoreFormatError("invalid cold EventLog last year")
    return ColdTailDescriptor(
        disk_events, sealed_events, total_events, last_year
    )


def _decode_commit_descriptor(value):
    if type(value) is not tuple or len(value) != 3:
        raise StoreFormatError("invalid cold session commit descriptor")
    version, generation, token = value
    if type(version) is not int or version != 1:
        raise StoreFormatError("invalid cold session commit descriptor")
    if type(generation) is not int or generation < 0:
        raise StoreFormatError("invalid cold session commit generation")
    if type(token) is not str or _TOKEN.fullmatch(token) is None:
        raise StoreFormatError("invalid cold session commit token")
    return ColdCommitDescriptor(generation, token)


def _expected_collection_namespaces():
    return {
        root + "." + name
        for root, names in ROOT_FIELDS.items()
        for name, kind in names.items()
        if kind != "state"
    }


def _count(head, namespace):
    return head.namespace_counts.get(namespace, (0, 0))


def _validate_head_inventory(head, manifest, links, event_records):
    collection_namespaces = _expected_collection_namespaces()
    expected_inventory = (
        collection_namespaces
        | {META, IDENTITY_LINKS, EVENT_STORAGE, SEALED_EVENTS}
    )
    namespaces = head.metadata["namespaces"]
    if type(namespaces) is not tuple or set(namespaces) != expected_inventory:
        raise StoreFormatError("wrong namespace inventory for cold World capture")
    if IDENTITY_DELTAS in namespaces:
        raise StoreFormatError("identity deltas are not cold capture authority")

    meta_rows = 2 if COLLECTION_LAYOUT in {
        key
        for key, _value, _schema in event_records["metadata_rows"]
    } else 1
    if _count(head, META) != (meta_rows, 0):
        raise StoreIntegrityError("snapshot metadata count disagrees with head")
    if _count(head, IDENTITY_LINKS) != (len(links), 0):
        raise StoreIntegrityError("identity link count disagrees with head")
    if _count(head, EVENT_STORAGE) != (3, 0):
        raise StoreIntegrityError("event descriptor count disagrees with head")

    tail = event_records["tail"]
    prefix = event_records["prefix"]
    if _count(head, SEALED_EVENTS) != (0, prefix.segment_count):
        raise StoreIntegrityError("sealed-event segment count disagrees with head")
    if _count(head, "world.events") != (
        tail.total_events - tail.disk_events,
        0,
    ):
        raise StoreIntegrityError("event suffix count disagrees with head")

    descriptions = manifest["collections"]
    for namespace in collection_namespaces:
        records, segments = _count(head, namespace)
        if namespace == "world.events":
            if segments:
                raise StoreIntegrityError("world.events cannot contain segments")
            continue
        description = descriptions[namespace]
        if type(description) is not tuple or len(description) != 3:
            raise StoreFormatError(
                f"invalid collection description: {namespace}"
            )
        _kind, size, _chunks = description
        if type(size) is not int or size < 0:
            raise StoreFormatError(
                f"invalid collection description: {namespace}"
            )
        if (records, segments) != (size, 0):
            raise StoreIntegrityError(
                f"collection count disagrees with head: {namespace}"
            )


def _read_event_descriptors(store):
    rows = store.read_records(
        EVENT_STORAGE, expected_record_schema=DESCRIPTOR_SCHEMA
    )
    values = {}
    for key, value, _schema in rows:
        if key in values:
            raise StoreIntegrityError("duplicate event storage descriptor")
        values[key] = value
    expected = {
        DESCRIPTOR_KEY,
        TAIL_DESCRIPTOR_KEY,
        COMMIT_DESCRIPTOR_KEY,
    }
    if set(values) != expected:
        raise StoreFormatError("missing/unknown cold event descriptor")
    prefix = _decode_descriptor(values[DESCRIPTOR_KEY])
    tail = _decode_tail_descriptor(values[TAIL_DESCRIPTOR_KEY])
    commit = _decode_commit_descriptor(values[COMMIT_DESCRIPTOR_KEY])
    if prefix.event_count != tail.disk_events:
        raise StoreIntegrityError("prefix/tail disk boundary mismatch")
    if prefix.segment_count != tail.disk_events // CHUNK_SIZE:
        raise StoreIntegrityError("prefix segment count disagrees with tail")
    return prefix, tail, commit


def _validate_suffix_event(event, absolute_index):
    if type(event) is not Event:
        raise StoreFormatError("cold event suffix requires Event values")
    if type(event.id) is not int or event.id != absolute_index + 1:
        raise StoreIntegrityError("cold event suffix ID discontinuity")
    if type(event.year) is not int:
        raise StoreFormatError("invalid cold event year")
    sealed = event.__dict__.get("_sealed", False)
    if type(sealed) is not bool:
        raise StoreFormatError("invalid event sealed flag")
    if type(event.kind) is not str or type(event.layer) is not Layer:
        raise StoreFormatError("invalid cold event kind/layer")
    if (
        type(event.actors) is not tuple
        or any(type(actor) is not Ref for actor in event.actors)
    ):
        raise StoreFormatError("invalid cold event actors")
    if event.location is not None and type(event.location) is not Ref:
        raise StoreFormatError("invalid cold event location")
    if (
        type(event.causes) is not tuple
        or any(type(cause) is not int for cause in event.causes)
    ):
        raise StoreFormatError("invalid cold event causes")
    if sealed:
        _validate_sealed_event(event)
    return event


def _read_suffix(store, tail, prefix):
    rows = store.read_records(
        "world.events", expected_record_schema=RECORD_SCHEMA
    )
    expected_count = tail.total_events - tail.disk_events
    if len(rows) != expected_count:
        raise StoreIntegrityError("missing/extra cold event suffix rows")

    by_index = {}
    for key, envelope, _schema in rows:
        if type(key) is not int or key < tail.disk_events:
            raise StoreIntegrityError("invalid cold event suffix key")
        if key >= tail.total_events or key in by_index:
            raise StoreIntegrityError("invalid cold event suffix key")
        if type(envelope) is not tuple or len(envelope) != 2:
            raise StoreFormatError("invalid cold event suffix envelope")
        ordinal, event = envelope
        if type(ordinal) is not int or ordinal != key:
            raise StoreIntegrityError("cold event suffix ordinal mismatch")
        by_index[key] = event

    expected_keys = list(range(tail.disk_events, tail.total_events))
    if set(by_index) != set(expected_keys):
        raise StoreIntegrityError("cold event suffix is not contiguous")

    suffix = []
    previous_year = prefix.last_year
    for index in expected_keys:
        event = _validate_suffix_event(by_index[index], index)
        if previous_year is not None and event.year < previous_year:
            raise StoreIntegrityError("cold event suffix chronology violation")
        if index < tail.sealed_events:
            if event.__dict__.get("_sealed") is not True:
                raise StoreFormatError(
                    "pending cold event history must already be sealed"
                )
            _validate_sealed_event(event)
        previous_year = event.year
        suffix.append(event)

    final_year = suffix[-1].year if suffix else prefix.last_year
    if final_year != tail.last_event_year:
        raise StoreIntegrityError("cold EventLog last year mismatch")
    return suffix


def _capture_cold_world(store):
    """Capture one complete unbound cold-format World from a caller snapshot."""
    _require_active_capture_transaction(store)
    prefix_reader = None
    try:
        head = store.checked_head()
        manifest = _read_cold_manifest(store)
        metadata_rows = store.read_records(
            META, expected_record_schema=RECORD_SCHEMA
        )
        prefix_descriptor, tail_descriptor, commit_descriptor = (
            _read_event_descriptors(store)
        )
        if commit_descriptor.captured_generation != head.generation:
            raise StoreIntegrityError("cold commit generation disagrees with head")

        links = _read_current_identity_links(store)
        event_records = {
            "metadata_rows": metadata_rows,
            "prefix": prefix_descriptor,
            "tail": tail_descriptor,
        }
        _validate_head_inventory(
            head, manifest, links, event_records
        )

        description = manifest["collections"]["world.events"]
        expected_event_description = (
            COLD_EVENT_KIND,
            tail_descriptor.total_events,
            tail_descriptor.sealed_events // CHUNK_SIZE,
        )
        if description != expected_event_description:
            raise StoreIntegrityError(
                "cold EventLog collection description disagrees with descriptors"
            )

        prefix_reader = SealedEventPrefix.from_active_read_transaction(store)
        if prefix_reader.captured_generation != head.generation:
            raise StoreIntegrityError("cold prefix generation disagrees with head")
        if (
            prefix_reader.event_count != prefix_descriptor.event_count
            or prefix_reader.segment_count != prefix_descriptor.segment_count
            or prefix_reader.last_year != prefix_descriptor.last_year
        ):
            raise StoreIntegrityError("captured prefix disagrees with descriptor")

        suffix = _read_suffix(
            store, tail_descriptor, prefix_descriptor
        )
        log = EventLog.from_disk_prefix(
            prefix_reader,
            suffix,
            pending_sealed_events=(
                tail_descriptor.sealed_events
                - tail_descriptor.disk_events
            ),
        )

        objects = {
            root: object.__new__(cls)
            for root, cls in ROOT_TYPES.items()
        }
        for root, obj in objects.items():
            for name, kind in ROOT_FIELDS[root].items():
                namespace = root + "." + name
                if kind == "state":
                    value = objects[namespace]
                elif namespace == "world.events":
                    value = log
                else:
                    value = _restore_collection(
                        store,
                        namespace,
                        kind,
                        manifest["collections"][namespace],
                    )
                object.__setattr__(obj, name, value)
        world = objects["world"]

        expected_next = {
            key: getattr(world, key)
            for key in (
                "next_person",
                "next_household",
                "next_settlement",
                "next_event",
            )
        }
        if (
            world.seed != head.metadata["seed"]
            or world.year != head.metadata["simulation_position"]
            or head.metadata["next_ids"] != expected_next
        ):
            raise StoreIntegrityError("World disagrees with checked head")
        if world.next_event != tail_descriptor.total_events + 1:
            raise StoreIntegrityError("World next_event disagrees with EventLog")

        _restore_identity(
            world, links, mutable_event_tail_only=True
        )
        _verify_identity_graph(
            world, links, mutable_event_tail_only=True
        )

        return ColdWorldCapture(
            world=world,
            prefix=prefix_reader,
            generation=head.generation,
            head=head,
            manifest=manifest,
            identity_links=tuple(links),
            prefix_descriptor=prefix_descriptor,
            tail_descriptor=tail_descriptor,
            commit_descriptor=commit_descriptor,
        )
    except Exception:
        if prefix_reader is not None:
            prefix_reader.close()
        raise
