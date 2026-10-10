"""Internal P3B cold World capture; not a public session API."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from itertools import islice
from pathlib import Path
import os
import re
import tempfile
import uuid

from .core import Event, Layer, Ref, World
from .event_log import EventLog
from .incremental_store import (
    CheckedHead,
    CodecError,
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from .persistence_adapters import (
    COLLECTION_LAYOUT,
    AGENCY_ACTIONS_NAMESPACE,
    PACKED_LIST_KIND,
    IDENTITY_DELTAS,
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    IDENTITY_STORAGE_CURRENT,
    META,
    RECORD_SCHEMA,
    ROOT_FIELDS,
    ROOT_TYPES,
    SCHEMA,
    WorldCodec,
    _audit,
    _complete_identity_groups,
    _events,
    _read_manifest,
    read_snapshot,
    write_snapshot,
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
    _descriptor_value,
    prepare_sealed_append,
    _validate_sealed_event,
)
from .persistence_schema import RECORD_FIELDS


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
        expected_records = (
            1
            if (namespace == AGENCY_ACTIONS_NAMESPACE and _kind == PACKED_LIST_KIND)
            or (namespace == 'world.event_ids' and _kind in ('event-ids-range/v1', 'event-ids-exceptions/v1'))
            else size
        )
        if (records, segments) != (expected_records, 0):
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
        if (
            type(description) is not tuple
            or len(description) != 3
            or type(description[1]) is not int
            or type(description[2]) is not int
            or description != expected_event_description
        ):
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
        head_next = head.metadata["next_ids"]
        if (
            type(head.metadata["simulation_position"]) is not int
            or type(head_next) is not dict
            or any(type(value) is not int for value in head_next.values())
            or world.seed != head.metadata["seed"]
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



def _bootstrap_phase(_phase):
    """Private failure-injection seam for cold bootstrap validation tests."""
    return None


def _io_dict(value):
    return {
        "payload_reads": value.payload_reads,
        "payload_read_bytes": value.payload_read_bytes,
        "payload_writes": value.payload_writes,
        "payload_write_bytes": value.payload_write_bytes,
    }


def _preflight_destination(destination):
    destination = Path(destination)
    if os.path.lexists(destination):
        raise FileExistsError(destination)
    return destination


def _preflight_conversion_paths(source, destination):
    source = Path(source)
    destination = Path(destination)
    try:
        same_resolved = (
            source.resolve(strict=True)
            == destination.resolve(strict=False)
        )
    except (FileNotFoundError, OSError):
        same_resolved = os.path.abspath(source) == os.path.abspath(destination)
    if same_resolved:
        raise ValueError("source and destination must be different paths")
    if os.path.lexists(destination):
        if destination.exists():
            try:
                if os.path.samefile(source, destination):
                    raise ValueError(
                        "source and destination refer to the same file"
                    )
            except FileNotFoundError:
                pass
        raise FileExistsError(destination)
    return source, destination


def _validate_bootstrap_events(world):
    events = world.events
    if type(events) is list:
        disk_events = 0
        total_events = len(events)
        iterable = iter(events)
    elif type(events) is EventLog:
        if events._disk_prefix is not None or events._disk_count != 0:
            raise CodecError(
                "disk-backed EventLog is already cold-session state"
            )
        if type(events._count) is not int or events._count < 0:
            raise CodecError("invalid EventLog count")
        disk_events = len(events._chunks) * CHUNK_SIZE
        total_events = events._count
        if disk_events > total_events:
            raise CodecError("EventLog sealed prefix exceeds logical count")
        iterable = _events(events)
    else:
        raise CodecError("world.events must be list or in-memory EventLog")

    previous_year = None
    disk_last_year = None
    count = 0
    for index, event in enumerate(iterable):
        if type(event) is not Event:
            raise CodecError("world.events requires exact Event values")
        if type(event.id) is not int or event.id != index + 1:
            raise CodecError("events require exact consecutive integer IDs")
        if type(event.year) is not int:
            raise CodecError("events require integer years")
        if previous_year is not None and event.year < previous_year:
            raise CodecError("events require nondecreasing years")
        sealed = event.__dict__.get("_sealed", False)
        if type(sealed) is not bool:
            raise CodecError("invalid event sealed flag")
        if index < disk_events and sealed is not True:
            raise CodecError("EventLog sealed chunk contains unsealed Event")
        if sealed:
            _validate_sealed_event(event)
        if index + 1 == disk_events:
            disk_last_year = event.year
        previous_year = event.year
        count += 1
    if count != total_events:
        raise CodecError("EventLog count disagrees with logical events")
    if type(world.next_event) is not int or world.next_event != total_events + 1:
        raise CodecError("World next_event disagrees with events")
    if type(world.year) is not int:
        raise CodecError("World year must be an exact integer")
    for name in ("seed", "next_person", "next_household", "next_settlement"):
        if type(getattr(world, name)) is not int:
            raise CodecError(f"World {name} must be an exact integer")
    return {
        "disk_events": disk_events,
        "total_events": total_events,
        "disk_last_year": disk_last_year,
        "last_year": previous_year,
    }


def _reject_bound_bootstrap_graph(value, binding_lookup, active=None):
    """Reject any live P2-owned object reachable from an unbound source World."""
    if active is None:
        active = set()
    if binding_lookup(value) is not None:
        raise StoreError(
            "cold snapshot creation requires an unbound World and cannot borrow "
            "state bound to another persistence session"
        )
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes) or cls is Layer:
        return
    ident = id(value)
    if ident in active:
        return
    active.add(ident)
    try:
        if is_dataclass(value):
            for name in RECORD_FIELDS.get(cls, ()):
                _reject_bound_bootstrap_graph(
                    getattr(value, name), binding_lookup, active
                )
        elif isinstance(value, EventLog):
            for event in _events(value):
                _reject_bound_bootstrap_graph(
                    event, binding_lookup, active
                )
        elif isinstance(value, dict):
            for key, child in value.items():
                _reject_bound_bootstrap_graph(
                    key, binding_lookup, active
                )
                _reject_bound_bootstrap_graph(
                    child, binding_lookup, active
                )
        elif isinstance(value, (list, tuple, set, frozenset)):
            for child in value:
                _reject_bound_bootstrap_graph(
                    child, binding_lookup, active
                )
    finally:
        active.remove(ident)


def _normalized_bootstrap_view(world):
    if type(world) is not World:
        raise CodecError("expected World from this package registry")
    if (
        world.__dict__.get("_index_current_people")
        or world.advancement.__dict__.get("_rank_cache") is not None
    ):
        raise CodecError("cold snapshot requires a completed simulation step")

    # Import lazily so the cold capture module does not own P2 tracking.
    from .persistence_tracking import _binding
    _reject_bound_bootstrap_graph(world, _binding)

    source_links = []
    _audit(world, (), {}, set(), source_links)
    info = _validate_bootstrap_events(world)

    if type(world.events) is list:
        event_root = (("field", "events"),)
        if any(
            target == event_root or owner == event_root
            for target, owner in source_links
        ):
            raise CodecError(
                "shared canonical event list is legacy-only; "
                "cold bootstrap cannot preserve its container identity"
            )
        normalized_log = EventLog(world.events)
        view = object.__new__(World)
        for name in RECORD_FIELDS[World]:
            object.__setattr__(
                view,
                name,
                normalized_log if name == "events" else getattr(world, name),
            )
    else:
        normalized_log = world.events
        view = world

    groups = _complete_identity_groups(
        view, mutable_event_tail_only=True
    )
    codec = WorldCodec(identity_links_recorded=True)
    links = []
    for paths in groups.values():
        if len(paths) < 2:
            continue
        ordered = sorted(paths, key=codec.encode)
        anchor = ordered[0]
        for target in ordered[1:]:
            if not target:
                raise StoreIntegrityError(
                    "cold identity projection cannot target the World root"
                )
            links.append((target, anchor))
    _verify_identity_graph(
        view, links, mutable_event_tail_only=True
    )
    return view, normalized_log, info, links


def _cold_namespaces():
    return tuple(sorted(
        _expected_collection_namespaces()
        | {META, IDENTITY_LINKS, EVENT_STORAGE, SEALED_EVENTS}
    ))


def _transfer_sealed_prefix(store, source_log, disk_events):
    if disk_events == 0:
        return {
            "transferred_events": 0,
            "deleted_event_rows": 0,
            "transfer_commits": 0,
            "largest_transfer_batch_chunks": 0,
        }

    source_iter = iter(_events(source_log))
    transferred = 0
    commits = 0
    largest = 0
    try:
        while transferred < disk_events:
            batch_events = min(
                4 * CHUNK_SIZE, disk_events - transferred
            )
            batch = tuple(islice(source_iter, batch_events))
            if len(batch) != batch_events:
                raise StoreIntegrityError(
                    "source EventLog ended during sealed transfer"
                )
            prepared = prepare_sealed_append(store, batch)
            if (
                prepared.consumed_events != batch_events
                or len(prepared.new_segments) > 4
            ):
                raise StoreIntegrityError(
                    "sealed transfer exceeded bounded preparation"
                )
            _bootstrap_phase("before_transfer_commit")
            head = store.head_metadata()
            head["namespaces"] = tuple(sorted(
                set(head["namespaces"]) | {EVENT_STORAGE, SEALED_EVENTS}
            ))
            changes = list(prepared.record_changes)
            changes.extend(
                RecordChange("world.events", index, delete=True)
                for index in range(
                    transferred, transferred + batch_events
                )
            )
            store.commit(
                prepared.expected_generation,
                changes,
                prepared.new_segments,
                head,
            )
            _bootstrap_phase("after_transfer_commit")
            transferred += batch_events
            commits += 1
            largest = max(largest, len(prepared.new_segments))
            del prepared, changes, batch
    finally:
        close = getattr(source_iter, "close", None)
        if close is not None:
            close()

    return {
        "transferred_events": transferred,
        "deleted_event_rows": transferred,
        "transfer_commits": commits,
        "largest_transfer_batch_chunks": largest,
    }


def _projected_link_changes(store, projected_links):
    rows = store.read_records(
        IDENTITY_LINKS, expected_record_schema=IDENTITY_LINK_SCHEMA
    )
    existing = {target: owner for target, owner, _schema in rows}
    desired = {}
    for target, owner in projected_links:
        if target in desired:
            raise StoreIntegrityError(
                "duplicate projected cold identity target"
            )
        desired[target] = owner

    changes = []
    for target in existing.keys() - desired.keys():
        changes.append(
            RecordChange(IDENTITY_LINKS, target, delete=True)
        )
    for target, owner in desired.items():
        changes.append(
            RecordChange(
                IDENTITY_LINKS,
                target,
                owner,
                record_schema=IDENTITY_LINK_SCHEMA,
            )
        )
    return changes


def _finalize_cold_store(
    store, *, event_count, disk_events, disk_last_year, last_year,
    projected_links
):
    manifest = _read_manifest(store)
    collections = dict(manifest["collections"])
    collections["world.events"] = (
        COLD_EVENT_KIND,
        event_count,
        disk_events // CHUNK_SIZE,
    )
    cold_manifest = {
        "schema": SCHEMA,
        "collections": collections,
        "identity_storage": IDENTITY_STORAGE_CURRENT,
        "event_storage": COLD_EVENT_STORAGE,
    }
    token = uuid.uuid4().hex
    final_generation = store.generation + 1
    descriptor = SealedPrefixDescriptor(
        disk_events // CHUNK_SIZE,
        disk_events,
        disk_last_year if disk_events else None,
    )

    changes = _projected_link_changes(store, projected_links)
    changes.extend([
        RecordChange(
            META, "manifest", cold_manifest,
            record_schema=RECORD_SCHEMA,
        ),
        RecordChange(META, COLLECTION_LAYOUT, delete=True),
        RecordChange(
            EVENT_STORAGE,
            DESCRIPTOR_KEY,
            _descriptor_value(descriptor),
            record_schema=DESCRIPTOR_SCHEMA,
        ),
        RecordChange(
            EVENT_STORAGE,
            TAIL_DESCRIPTOR_KEY,
            (1, disk_events, disk_events, event_count, last_year),
            record_schema=SESSION_DESCRIPTOR_SCHEMA,
        ),
        RecordChange(
            EVENT_STORAGE,
            COMMIT_DESCRIPTOR_KEY,
            (1, final_generation, token),
            record_schema=SESSION_DESCRIPTOR_SCHEMA,
        ),
    ])
    metadata = store.head_metadata()
    metadata["namespaces"] = _cold_namespaces()
    _bootstrap_phase("before_final_commit")
    generation = store.commit(
        store.generation, changes, (), metadata
    )
    _bootstrap_phase("after_final_commit")
    if generation != final_generation:
        raise StoreIntegrityError(
            "cold final generation was not published exactly once"
        )
    return generation, token


def _validate_private_cold_store(
    store, *, event_count, disk_events, projected_links
):
    _bootstrap_phase("before_validation")
    scrub = store.verify_all()
    rows = store.read_records(
        "world.events", expected_record_schema=RECORD_SCHEMA
    )
    keys = [key for key, _value, _schema in rows]
    expected = list(range(disk_events, event_count))
    if (
        any(type(key) is not int for key in keys)
        or sorted(keys) != expected
    ):
        raise StoreIntegrityError(
            "final cold suffix rows are not exactly [F,N)"
        )

    capture = None
    try:
        with store.read_transaction():
            capture = _capture_cold_world(store)
        if list(capture.identity_links) != list(projected_links):
            # Link order is deterministic in the writer and record row order is
            # not authority, so compare encoded sets below when order differs.
            codec = WorldCodec(identity_links_recorded=True)
            if {
                codec.encode(link) for link in capture.identity_links
            } != {
                codec.encode(link) for link in projected_links
            }:
                raise StoreIntegrityError(
                    "cold capture identity authority disagrees with projection"
                )
        if (
            capture.tail_descriptor.disk_events != disk_events
            or capture.tail_descriptor.sealed_events != disk_events
            or capture.tail_descriptor.total_events != event_count
        ):
            raise StoreIntegrityError(
                "cold capture partition disagrees with bootstrap"
            )
        verified = capture.prefix.verify_full()
        if (
            verified["events"] != disk_events
            or verified["segments"] != disk_events // CHUNK_SIZE
        ):
            raise StoreIntegrityError(
                "cold prefix verification disagrees with bootstrap"
            )
    finally:
        if capture is not None:
            capture.prefix.close()
    _bootstrap_phase("after_validation")
    return scrub


def _fsync_publication_dir(path):
    TransactionalStore._fsync_dir(path)


def _publish_private_cold_file(private_path, destination):
    os.link(private_path, destination)
    _bootstrap_phase("after_publication_link")
    _fsync_publication_dir(destination.parent)
    _bootstrap_phase("after_publication_fsync")


def write_cold_snapshot(world, destination, *, rules_id):
    """Create a fully validated cold snapshot without mutating an unbound World.

    A list-backed canonical event root is normalized only in a temporary export
    view and produces F=0. If that list container itself is shared elsewhere,
    cold bootstrap rejects it because the accepted cold format cannot preserve
    that container alias. Shared Event values/children that remain in the
    current projection are supported.
    """
    destination = _preflight_destination(destination)
    view, source_log, info, projected_links = _normalized_bootstrap_view(world)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".ate-cold-", dir=destination.parent
    ) as directory:
        private_path = Path(directory) / "snapshot.sqlite"
        staging = write_snapshot(
            view, private_path, rules_id=rules_id
        )
        _bootstrap_phase("after_staging")

        store = TransactionalStore.open(
            private_path,
            codec=WorldCodec(identity_links_recorded=True),
            expected_simulation_schema=SCHEMA,
            expected_rules_id=rules_id,
        )
        try:
            store.reset_diagnostics()
            transfer = _transfer_sealed_prefix(
                store, source_log, info["disk_events"]
            )
            transfer_io = _io_dict(store.diagnostics())

            store.reset_diagnostics()
            generation, token = _finalize_cold_store(
                store,
                event_count=info["total_events"],
                disk_events=info["disk_events"],
                disk_last_year=info["disk_last_year"],
                last_year=info["last_year"],
                projected_links=projected_links,
            )
            finalize_io = _io_dict(store.diagnostics())

            store.reset_diagnostics()
            _validate_private_cold_store(
                store,
                event_count=info["total_events"],
                disk_events=info["disk_events"],
                projected_links=projected_links,
            )
            validation_io = _io_dict(store.diagnostics())
        finally:
            store.close()

        file_bytes = private_path.stat().st_size
        _bootstrap_phase("before_publication")
        _publish_private_cold_file(private_path, destination)

    return {
        "final_generation": generation,
        "commit_token": token,
        "event_count": info["total_events"],
        "disk_segments": info["disk_events"] // CHUNK_SIZE,
        "disk_events": info["disk_events"],
        "remaining_suffix_records": (
            info["total_events"] - info["disk_events"]
        ),
        **transfer,
        "staging_io": _io_dict(staging),
        "transfer_io": transfer_io,
        "finalize_io": finalize_io,
        "validation_io": validation_io,
        "final_file_bytes": file_bytes,
    }


def _capture_cold_baseline_ordinals(
    store, manifest, *, excluded_namespaces=()
):
    """Capture stable root ordinals from the same pinned cold generation."""
    excluded_namespaces = set(excluded_namespaces)
    result = {}
    for namespace, description in manifest["collections"].items():
        if namespace in excluded_namespaces:
            continue
        if type(description) is not tuple or len(description) != 3:
            raise StoreFormatError(
                f"invalid collection description: {namespace}"
            )
        kind = {
            "dict-stable/v1": "dict",
            "RecordTable-stable/v1": "RecordTable",
            "set-stable/v1": "set",
        }.get(description[0], description[0])
        if kind not in ("dict", "RecordTable", "set"):
            continue
        rows = store.read_records(
            namespace, expected_record_schema=RECORD_SCHEMA
        )
        ordinals = {}
        seen = set()
        for key, envelope, _schema in rows:
            if type(envelope) is not tuple or len(envelope) != 2:
                raise StoreFormatError("invalid entry envelope")
            ordinal, value = envelope
            if type(ordinal) is not int or ordinal < 0 or ordinal in seen:
                raise StoreIntegrityError(
                    f"invalid persisted ordinal: {namespace}"
                )
            seen.add(ordinal)
            identity = value if kind == "set" else key
            if identity in ordinals:
                raise StoreIntegrityError(
                    f"duplicate persisted collection member: {namespace}"
                )
            ordinals[identity] = ordinal
        result[namespace] = ordinals
    return result


def open_world_session(path, *, rules_id):
    """Open one cold-format World as an owned durable tracked session.

    The returned IncrementalWorldSession owns the captured P1 store and supports
    bounded atomic cold save/resolve semantics. Detached/export integration
    remains a separate P3B slice.
    """
    path = Path(path)
    store = TransactionalStore.open(
        path,
        codec=WorldCodec(identity_links_recorded=True),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    )
    capture = None
    try:
        with store.read_transaction():
            try:
                raw_manifest = store.read_record(
                    META, "manifest", expected_record_schema=RECORD_SCHEMA
                )
            except KeyError as exc:
                raise StoreFormatError(
                    "cold World session is missing its manifest"
                ) from exc
            if type(raw_manifest) is not dict:
                raise StoreFormatError("invalid cold World manifest")
            mode = raw_manifest.get("event_storage")
            if mode is None:
                raise StoreFormatError(
                    "open_world_session requires cold event storage; "
                    "run convert_event_storage first"
                )
            if mode != COLD_EVENT_STORAGE:
                raise StoreFormatError(
                    f"unsupported cold event storage mode: {mode!r}"
                )
            capture = _capture_cold_world(store)
            baseline_ordinals = _capture_cold_baseline_ordinals(
                store, capture.manifest
            )
    except Exception:
        if capture is not None:
            capture.prefix.close()
        store.close()
        raise

    from .persistence_tracking import IncrementalWorldSession
    return IncrementalWorldSession._from_cold_capture(
        store, capture, baseline_ordinals
    )


def convert_event_storage(source, destination, *, rules_id):
    """Explicit full-cost P2-to-cold conversion with no source mutation.

    Current P2C and genuine legacy P2A/P2B inputs are restored through the
    accepted pinned/full-scrub reader. Already-cold input is rejected; use the
    P1 store backup operation when a byte-for-byte cold copy is desired.
    """
    source, destination = _preflight_conversion_paths(
        source, destination
    )
    with TransactionalStore.open(
        source,
        codec=WorldCodec(),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    ) as probe:
        with probe.read_transaction():
            manifest = probe.read_record(
                META, "manifest", expected_record_schema=RECORD_SCHEMA
            )
            if (
                type(manifest) is dict
                and manifest.get("event_storage") == COLD_EVENT_STORAGE
            ):
                raise StoreFormatError(
                    "source is already cold; use TransactionalStore.backup "
                    "for cold-store relocation"
                )

    world = read_snapshot(source, rules_id=rules_id)
    result = write_cold_snapshot(
        world, destination, rules_id=rules_id
    )
    result["source_format"] = "p2-record-snapshot"
    return result
