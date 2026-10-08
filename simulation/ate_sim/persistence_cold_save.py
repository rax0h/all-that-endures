"""Atomic P3B cold-session save, acknowledgement and recovery.

This module composes the accepted P1 transaction, P2C current-link journal and
P3A sealed-prefix append.  It deliberately does not own simulation mutation
tracking or detached/export behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_right
import pickle
import re
import uuid
import zlib

from .core import Event
from .incremental_store import (
    RecordChange,
    NewSegment,
    StoreConflictError,
    StoreError,
    StoreIntegrityError,
)
from .persistence_adapters import (
    COLLECTION_LAYOUT,
    AGENCY_ACTIONS_NAMESPACE,
    PACKED_LIST_KIND,
    PACKED_LIST_KEY,
    PACKED_LIST_PAYLOAD,
    IDENTITY_LINKS,
    IDENTITY_LINK_SCHEMA,
    META,
    RECORD_SCHEMA,
)
from .persistence_events import (
    CHUNK_SIZE,
    DESCRIPTOR_KEY,
    DESCRIPTOR_SCHEMA,
    EVENT_STORAGE,
    SEALED_EVENTS,
    SealedEventPrefix,
    SealedPrefixDescriptor,
    _decode_segment,
    _descriptor_value,
    _validate_sealed_event,
    prepare_sealed_append,
)
from .persistence_session import (
    COMMIT_DESCRIPTOR_KEY,
    SESSION_DESCRIPTOR_SCHEMA,
    TAIL_DESCRIPTOR_KEY,
    ColdCommitDescriptor,
    ColdTailDescriptor,
    _cold_namespaces,
    _read_event_descriptors,
    _validate_suffix_event,
)

_TOKEN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class RecordEvidence:
    namespace: str
    key: object
    record_schema: int
    delete: bool
    key_bytes: bytes
    value_bytes: bytes | None


@dataclass(frozen=True)
class SegmentEvidence:
    namespace: str
    ordinal: int
    element_count: int
    first_id: object
    last_id: object
    value_bytes: bytes


@dataclass(frozen=True)
class ColdSavePlan:
    expected_generation: int
    target_generation: int
    token: str
    before_head_metadata: object
    before_namespace_counts: object
    before_prefix: SealedPrefixDescriptor
    after_prefix: SealedPrefixDescriptor
    before_tail: ColdTailDescriptor
    after_tail: ColdTailDescriptor
    before_commit: ColdCommitDescriptor
    committed_n: int
    changes: tuple[RecordChange, ...]
    new_segments: tuple[NewSegment, ...]
    metadata: object
    expected_namespace_counts: object
    record_evidence: tuple[RecordEvidence, ...]
    segment_evidence: tuple[SegmentEvidence, ...]
    transfer_events: int
    dirty_owners: frozenset
    deleted_owners: frozenset
    pending_identity: tuple
    manifest_dirty: bool
    layout_value: object | None

    @property
    def transfer_chunks(self) -> int:
        return self.transfer_events // CHUNK_SIZE


def _cold_save_phase(_phase, _session, _plan):
    """Private deterministic failure-injection seam for focused tests."""
    return None


def _encoded_copy(codec, value):
    """Return a detached typed copy plus its canonical evidence bytes."""
    payload = codec.encode(value)
    return codec.decode(payload), payload


def _head_metadata_tuple(codec, metadata):
    return codec.encode({
        "simulation_position": metadata["simulation_position"],
        "seed": metadata["seed"],
        "next_ids": metadata["next_ids"],
        "namespaces": tuple(sorted(set(metadata["namespaces"]))),
    })


def _counts_tuple(codec, counts):
    # P1 publishes namespace_counts in sorted namespace order.  TypedCodec
    # preserves dict insertion order, so acknowledgement evidence must use the
    # same canonical order rather than rejecting an equal mapping.
    return codec.encode({
        namespace: counts[namespace]
        for namespace in sorted(counts)
    })


def _event_chunk(log, number):
    if number < 0 or number >= len(log._chunks):
        raise StoreIntegrityError("pending EventLog chunk is outside resident suffix")
    try:
        raw = pickle.loads(zlib.decompress(log._chunks[number]))
    except Exception as exc:
        raise StoreIntegrityError("invalid pending EventLog chunk") from exc
    if type(raw) is not list or len(raw) != CHUNK_SIZE:
        raise StoreIntegrityError("pending EventLog chunk has wrong size")
    return tuple(raw)


def _storage_event(log, index, decoded):
    """Read only resident suffix authority; never visit the disk prefix."""
    if type(index) is not int or index < log._disk_count or index >= log._count:
        raise StoreIntegrityError("cold suffix event index is outside resident authority")
    local = index - log._disk_count
    pending = len(log._chunks) * CHUNK_SIZE
    if local < pending:
        number, offset = divmod(local, CHUNK_SIZE)
        chunk = decoded.get(number)
        if chunk is None:
            chunk = _event_chunk(log, number)
            decoded[number] = chunk
        return chunk[offset]
    offset = local - pending
    if offset < 0 or offset >= len(log._tail):
        raise StoreIntegrityError("cold EventLog tail count disagrees with suffix")
    return log._tail[offset]


def _indexed_suffix_year(log, index):
    """Return EventLog's resident indexed year for one absolute suffix index."""
    if index < log._disk_count or index >= log._count:
        raise StoreIntegrityError("cold EventLog year lookup is outside suffix")
    position = bisect_right(log._offsets, index) - 1
    if position < 0 or position >= len(log._years):
        raise StoreIntegrityError("cold EventLog year index misses resident suffix")
    return log._years[position]


def _validate_live_partition(session):
    log = session.world.events
    before_tail = session._cold_tail_descriptor
    before_prefix = session._cold_prefix_descriptor
    if log._disk_prefix is None:
        raise StoreIntegrityError("cold session lost its disk EventLog prefix")
    if log._disk_count != before_tail.disk_events:
        raise StoreIntegrityError("runtime disk boundary differs from captured authority")
    if (
        before_prefix.event_count != before_tail.disk_events
        or before_prefix.segment_count * CHUNK_SIZE != before_tail.disk_events
    ):
        raise StoreIntegrityError("captured cold prefix/tail boundary disagrees")
    if (
        log._disk_prefix.event_count != before_prefix.event_count
        or log._disk_prefix.segment_count != before_prefix.segment_count
        or log._disk_prefix.last_year != before_prefix.last_year
    ):
        raise StoreIntegrityError("runtime prefix differs from captured descriptor")
    D = before_tail.disk_events
    F = D + len(log._chunks) * CHUNK_SIZE
    N = log._count
    if not (0 <= D <= F <= N) or F % CHUNK_SIZE:
        raise StoreIntegrityError("runtime cold EventLog partition is invalid")
    if N != D + len(log._chunks) * CHUNK_SIZE + len(log._tail):
        raise StoreIntegrityError("runtime cold EventLog resident counts disagree")
    if type(session.world.next_event) is not int or session.world.next_event != N + 1:
        raise StoreIntegrityError("World next_event disagrees with cold EventLog")
    last_year = log._last_year
    if (N == 0 and last_year is not None) or (N and type(last_year) is not int):
        raise StoreIntegrityError("runtime cold EventLog last year is invalid")
    if N:
        if N == D:
            actual_last_year = before_prefix.last_year
        elif log._tail:
            actual_last_year = log._tail[-1].year
        else:
            actual_last_year = _event_chunk(
                log, len(log._chunks) - 1
            )[-1].year
        if actual_last_year != last_year:
            raise StoreIntegrityError(
                "runtime cold EventLog last year disagrees with resident state"
            )
    return log, D, F, N, last_year


def _check_captured_store_baseline(session):
    """Bounded stale/corruption check with no historical segment reads."""
    with session.store.read_transaction():
        head = session.store.checked_head()
        prefix, tail, commit = _read_event_descriptors(session.store)
    if head.generation != session.generation:
        raise StoreConflictError(
            f"expected generation {session.generation}, found {head.generation}"
        )
    codec = session.codec
    if (
        _head_metadata_tuple(codec, head.metadata)
        != _head_metadata_tuple(codec, session._cold_head.metadata)
        or _counts_tuple(codec, head.namespace_counts)
        != _counts_tuple(codec, session._cold_head.namespace_counts)
        or prefix != session._cold_prefix_descriptor
        or tail != session._cold_tail_descriptor
        or commit != session._cold_commit_descriptor
    ):
        raise StoreIntegrityError("cold session captured baseline changed unexpectedly")
    return head


def _record_existed(session, namespace, key, D, N0):
    if namespace == "world.events":
        return type(key) is int and D <= key < N0
    return key in session._cold_persisted_keys.get(namespace, ())


def _expected_counts(session, changes, new_segments, D, N0):
    counts = dict(session._cold_head.namespace_counts)
    # changes is already coalesced to one final action per typed key.  Determine
    # baseline presence only for those touched keys; copying every persisted-key
    # set here makes a local edit scale with unrelated world size.
    for change in changes:
        namespace, key = change.namespace, change.key
        existed = _record_existed(session, namespace, key, D, N0)
        before = counts.get(namespace, (0, 0))
        records, segments = before
        if change.delete:
            if existed:
                records -= 1
        elif not existed:
            records += 1
        if records < 0:
            raise StoreIntegrityError("cold save namespace record count underflow")
        if records == 0 and segments == 0:
            counts.pop(namespace, None)
        else:
            counts[namespace] = (records, segments)
    for segment in new_segments:
        records, segments = counts.get(segment.namespace, (0, 0))
        counts[segment.namespace] = (records, segments + 1)
    return counts


def _put_change(change_map, codec, change):
    marker = (change.namespace, codec.encode(change.key))
    if marker in change_map:
        raise StoreIntegrityError(
            f"duplicate cold save record action: {(change.namespace, change.key)!r}"
        )
    change_map[marker] = change


def _current_layout(session):
    collections = dict(session._manifest["collections"])
    for namespace in session._root_containers:
        collections[namespace] = session._description(namespace)
    return collections


def _cold_metadata(session):
    return {
        "simulation_position": session.world.year,
        "seed": session.world.seed,
        "next_ids": {
            key: getattr(session.world, key)
            for key in ("next_person", "next_household", "next_settlement", "next_event")
        },
        "namespaces": _cold_namespaces(),
    }


def _change_evidence(codec, changes):
    out = []
    for change in changes:
        copied_key, key_bytes = _encoded_copy(codec, change.key)
        value_bytes = None
        if not change.delete:
            _copy, value_bytes = _encoded_copy(codec, change.value)
        out.append(RecordEvidence(
            change.namespace,
            copied_key,
            change.record_schema,
            change.delete,
            key_bytes,
            value_bytes,
        ))
    return tuple(out)


def _segment_evidence(codec, segments):
    out = []
    for segment in segments:
        copied_first, _ = _encoded_copy(codec, segment.first_id)
        copied_last, _ = _encoded_copy(codec, segment.last_id)
        _copy, value_bytes = _encoded_copy(codec, segment.value)
        out.append(SegmentEvidence(
            segment.namespace,
            segment.ordinal,
            segment.element_count,
            copied_first,
            copied_last,
            value_bytes,
        ))
    return tuple(out)


def prepare_cold_save(session, *, force=False, token=None):
    """Freeze one bounded cold save plan without persistent mutation.

    force/token are internal P4 composition seams. Defaults preserve the
    accepted P3B behavior.
    """
    if type(force) is not bool:
        raise TypeError("force must be bool")
    if token is not None and (
        type(token) is not str or _TOKEN.fullmatch(token) is None
    ):
        raise ValueError("explicit cold save token is invalid")
    session.store._ensure_open()
    _check_captured_store_baseline(session)
    log, D, F, N, last_year = _validate_live_partition(session)

    # Finalize only touched identity owners.  This mutates the in-memory pending
    # link journal, never the committed identity baseline.
    session._refresh_identity_index()

    q = min((F - D) // CHUNK_SIZE, 4)
    D1 = D + q * CHUNK_SIZE
    no_journal = (
        not session._dirty
        and not session._deleted
        and not session._manifest_dirty
        and not session._pending_identity_current
    )
    if q == 0 and no_journal and not force:
        return None

    selected = ()
    append = None
    if q:
        selected_parts = []
        for number in range(q):
            selected_parts.extend(_event_chunk(log, number))
        selected = tuple(selected_parts)
        append = prepare_sealed_append(session.store, selected)
        if append.expected_generation != session.generation:
            raise StoreConflictError(
                f"expected generation {session.generation}, "
                f"found {append.expected_generation}"
            )
        if append.before != session._cold_prefix_descriptor:
            raise StoreIntegrityError(
                "sealed append preparation disagrees with captured prefix"
            )
        if append.consumed_events != q * CHUNK_SIZE or len(append.new_segments) != q:
            raise StoreIntegrityError("cold save transfer exceeded bounded plan")
        after_prefix = append.after
        new_segments = append.new_segments
    else:
        after_prefix = session._cold_prefix_descriptor
        new_segments = ()

    N0 = session._cold_committed_n
    if N0 != session._cold_tail_descriptor.total_events:
        raise StoreIntegrityError("cold committed event baseline disagrees")

    from .persistence_tracking import _MISSING

    change_map = {}
    dirty = frozenset(session._dirty)
    deleted = frozenset(session._deleted)

    # The capped agency action tail remains a normal mutable runtime list with
    # exact P2 identity/mutation behavior. Physically, however, index-keyed
    # persistence turns a rolling 50k tail into ~50k writes per save. Coalesce
    # only that bounded family into one checked payload record.
    agency_changed = any(
        owner[0] == AGENCY_ACTIONS_NAMESPACE
        for owner in dirty | deleted
    )
    if agency_changed:
        description = session._manifest["collections"][
            AGENCY_ACTIONS_NAMESPACE
        ]
        stored_kind, stored_size, _chunks = description
        if session._base_kind(stored_kind) != "list":
            raise StoreIntegrityError(
                "agency actions are not stored as a list"
            )
        if stored_kind != PACKED_LIST_KIND:
            persisted = session._cold_persisted_keys.get(
                AGENCY_ACTIONS_NAMESPACE,
                set(range(stored_size)),
            )
            for key in sorted(persisted, key=session.codec.encode):
                if key == PACKED_LIST_KEY:
                    continue
                _put_change(
                    change_map,
                    session.codec,
                    RecordChange(
                        AGENCY_ACTIONS_NAMESPACE,
                        key,
                        delete=True,
                    ),
                )
        container = session._root_containers[AGENCY_ACTIONS_NAMESPACE]
        container._kind = PACKED_LIST_KIND
        session._manifest_dirty = True
        envelope = (
            0,
            (
                PACKED_LIST_PAYLOAD,
                tuple(container),
            ),
        )
        detached, _bytes = _encoded_copy(session.codec, envelope)
        _put_change(
            change_map,
            session.codec,
            RecordChange(
                AGENCY_ACTIONS_NAMESPACE,
                PACKED_LIST_KEY,
                detached,
                record_schema=RECORD_SCHEMA,
            ),
        )

    # Non-event owner journal follows the accepted P2C serializer.
    for namespace, key in sorted(
        deleted, key=lambda item: (item[0], session.codec.encode(item[1]))
    ):
        if namespace in ("world.events", AGENCY_ACTIONS_NAMESPACE):
            continue
        _put_change(
            change_map, session.codec,
            RecordChange(namespace, key, delete=True),
        )
    for namespace, key in sorted(
        dirty, key=lambda item: (item[0], session.codec.encode(item[1]))
    ):
        if namespace in ("world.events", AGENCY_ACTIONS_NAMESPACE):
            continue
        envelope = session._plain(session._record_value(namespace, key))
        detached, _bytes = _encoded_copy(session.codec, envelope)
        _put_change(
            change_map, session.codec,
            RecordChange(
                namespace, key, detached, record_schema=RECORD_SCHEMA
            ),
        )

    # Selected segment authority replaces only suffix rows which actually
    # existed in the captured baseline.  New selected Events are segment-only.
    for index in range(D, min(D1, N0)):
        _put_change(
            change_map, session.codec,
            RecordChange("world.events", index, delete=True),
        )

    # Dirty/new suffix events outside the selected transfer remain row authority.
    decoded_chunks = {}
    for namespace, key in sorted(
        dirty, key=lambda item: (item[0], session.codec.encode(item[1]))
    ):
        if namespace != "world.events" or key < D1:
            continue
        event = _storage_event(log, key, decoded_chunks)
        _validate_suffix_event(event, key)
        if event.year != _indexed_suffix_year(log, key):
            raise StoreIntegrityError(
                "dirty cold Event year disagrees with EventLog year index"
            )
        detached = session._plain(event)
        detached, _bytes = _encoded_copy(session.codec, detached)
        _put_change(
            change_map, session.codec,
            RecordChange(
                "world.events",
                key,
                (key, detached),
                record_schema=RECORD_SCHEMA,
            ),
        )

    pending_identity = tuple(sorted(
        session._pending_identity_current.items(),
        key=lambda item: session.codec.encode(item[0]),
    ))
    for target, owner in pending_identity:
        _put_change(
            change_map, session.codec,
            RecordChange(
                IDENTITY_LINKS,
                target,
                None if owner is _MISSING else owner,
                record_schema=IDENTITY_LINK_SCHEMA,
                delete=owner is _MISSING,
            ),
        )

    layout_value = None
    if session._manifest_dirty:
        layout_value = _current_layout(session)
        detached_layout, _bytes = _encoded_copy(session.codec, layout_value)
        layout_value = detached_layout
        _put_change(
            change_map, session.codec,
            RecordChange(
                META,
                COLLECTION_LAYOUT,
                layout_value,
                record_schema=RECORD_SCHEMA,
            ),
        )

    after_tail = ColdTailDescriptor(D1, F, N, last_year)
    target = session.generation + 1
    if token is None:
        token = uuid.uuid4().hex
        if _TOKEN.fullmatch(token) is None:
            raise StoreIntegrityError("generated invalid cold save token")

    if append is not None:
        for change in append.record_changes:
            _put_change(change_map, session.codec, change)

    _put_change(
        change_map, session.codec,
        RecordChange(
            EVENT_STORAGE,
            TAIL_DESCRIPTOR_KEY,
            (1, D1, F, N, last_year),
            record_schema=SESSION_DESCRIPTOR_SCHEMA,
        ),
    )
    _put_change(
        change_map, session.codec,
        RecordChange(
            EVENT_STORAGE,
            COMMIT_DESCRIPTOR_KEY,
            (1, target, token),
            record_schema=SESSION_DESCRIPTOR_SCHEMA,
        ),
    )

    changes = tuple(
        change_map[key]
        for key in sorted(change_map, key=lambda item: (item[0], item[1]))
    )
    metadata, _metadata_bytes = _encoded_copy(session.codec, _cold_metadata(session))
    expected_counts = _expected_counts(
        session, changes, new_segments, D, N0
    )
    record_evidence = _change_evidence(session.codec, changes)
    segment_evidence = _segment_evidence(session.codec, new_segments)

    return ColdSavePlan(
        expected_generation=session.generation,
        target_generation=target,
        token=token,
        before_head_metadata=_head_metadata_tuple(
            session.codec, session._cold_head.metadata
        ),
        before_namespace_counts=_counts_tuple(
            session.codec, session._cold_head.namespace_counts
        ),
        before_prefix=session._cold_prefix_descriptor,
        after_prefix=after_prefix,
        before_tail=session._cold_tail_descriptor,
        after_tail=after_tail,
        before_commit=session._cold_commit_descriptor,
        committed_n=N0,
        changes=changes,
        new_segments=tuple(new_segments),
        metadata=metadata,
        expected_namespace_counts=_counts_tuple(
            session.codec, expected_counts
        ),
        record_evidence=record_evidence,
        segment_evidence=segment_evidence,
        transfer_events=D1 - D,
        dirty_owners=dirty,
        deleted_owners=deleted,
        pending_identity=pending_identity,
        manifest_dirty=session._manifest_dirty,
        layout_value=layout_value,
    )


def _verify_old_state(session, plan, head, prefix, tail, commit):
    return (
        head.generation == plan.expected_generation
        and _head_metadata_tuple(session.codec, head.metadata)
            == plan.before_head_metadata
        and _counts_tuple(session.codec, head.namespace_counts)
            == plan.before_namespace_counts
        and prefix == plan.before_prefix
        and tail == plan.before_tail
        and commit == plan.before_commit
    )


def _verify_successor_records(session, plan):
    for evidence in plan.record_evidence:
        try:
            value = session.store.read_record(
                evidence.namespace,
                evidence.key,
                expected_record_schema=evidence.record_schema,
            )
        except KeyError:
            if evidence.delete:
                continue
            raise StoreIntegrityError(
                f"missing acknowledged cold save record: "
                f"{(evidence.namespace, evidence.key)!r}"
            )
        if evidence.delete:
            raise StoreIntegrityError(
                f"acknowledged cold save deletion is still present: "
                f"{(evidence.namespace, evidence.key)!r}"
            )
        if session.codec.encode(value) != evidence.value_bytes:
            raise StoreIntegrityError(
                f"acknowledged cold save record value mismatch: "
                f"{(evidence.namespace, evidence.key)!r}"
            )


def _verify_successor_segments(session, plan):
    for evidence in plan.segment_evidence:
        try:
            checked = session.store.read_segment_checked(
                evidence.namespace, evidence.ordinal
            )
        except KeyError as exc:
            raise StoreIntegrityError(
                f"missing acknowledged cold save segment: "
                f"{(evidence.namespace, evidence.ordinal)!r}"
            ) from exc
        if (
            checked.element_count != evidence.element_count
            or session.codec.encode(checked.first_id)
                != session.codec.encode(evidence.first_id)
            or session.codec.encode(checked.last_id)
                != session.codec.encode(evidence.last_id)
            or checked.created_generation != plan.target_generation
            or session.codec.encode(checked.value) != evidence.value_bytes
        ):
            raise StoreIntegrityError(
                f"acknowledged cold save segment mismatch: "
                f"{(evidence.namespace, evidence.ordinal)!r}"
            )


def _capture_successor(session, plan, *, full_evidence):
    prefix_reader = None
    try:
        with session.store.read_transaction():
            head = session.store.checked_head()
            prefix, tail, commit = _read_event_descriptors(session.store)

            if head.generation == plan.expected_generation:
                if _verify_old_state(
                    session, plan, head, prefix, tail, commit
                ):
                    return "old", head, None
                raise StoreIntegrityError(
                    "cold save old-generation acknowledgement evidence changed"
                )

            if head.generation != plan.target_generation:
                return "foreign", head, None
            if head.parent_generation != plan.expected_generation:
                return "foreign", head, None
            if (
                commit.captured_generation != plan.target_generation
                or commit.commit_token != plan.token
            ):
                return "foreign", head, None

            expected_metadata = _head_metadata_tuple(
                session.codec, plan.metadata
            )
            actual_metadata = _head_metadata_tuple(
                session.codec, head.metadata
            )
            actual_counts = _counts_tuple(
                session.codec, head.namespace_counts
            )
            mismatches = []
            if actual_metadata != expected_metadata:
                mismatches.append("head metadata")
            if actual_counts != plan.expected_namespace_counts:
                expected_counts = session.codec.decode(
                    plan.expected_namespace_counts
                )
                mismatches.append(
                    "namespace counts "
                    f"expected={expected_counts!r} "
                    f"actual={head.namespace_counts!r}"
                )
            if prefix != plan.after_prefix:
                mismatches.append("prefix descriptor")
            if tail != plan.after_tail:
                mismatches.append("tail descriptor")
            if mismatches:
                raise StoreIntegrityError(
                    "own-token cold save successor evidence mismatch: "
                    + ", ".join(mismatches)
                )

            if full_evidence:
                _verify_successor_records(session, plan)
                _verify_successor_segments(session, plan)

            prefix_reader = SealedEventPrefix.from_active_read_transaction(
                session.store
            )
            if (
                prefix_reader.captured_generation != plan.target_generation
                or prefix_reader.event_count != plan.after_prefix.event_count
                or prefix_reader.segment_count != plan.after_prefix.segment_count
                or prefix_reader.last_year != plan.after_prefix.last_year
            ):
                raise StoreIntegrityError(
                    "acknowledged replacement prefix disagrees with save plan"
                )
            return "ours", head, prefix_reader
    except Exception:
        if prefix_reader is not None:
            prefix_reader.close()
        raise


def _apply_persisted_key_changes(session, plan):
    D = plan.before_tail.disk_events
    N0 = plan.committed_n
    for change in plan.changes:
        namespace, key = change.namespace, change.key
        if namespace == "world.events":
            continue
        keys = session._cold_persisted_keys.setdefault(namespace, set())
        if change.delete:
            keys.discard(key)
        else:
            keys.add(key)
    # Event rows are represented as a contiguous range and intentionally are
    # not retained as an O(history) Python key set.
    session._cold_committed_n = plan.after_tail.total_events


def _validate_acknowledged_journal(session, plan, *, allow_applied=False):
    """Prove publication bookkeeping is pending or, on retry, already applied."""
    from .persistence_tracking import _MISSING

    if not allow_applied:
        if not plan.dirty_owners.issubset(session._dirty):
            raise StoreIntegrityError(
                "cold save dirty journal changed while publication was guarded"
            )
        if not plan.deleted_owners.issubset(session._deleted):
            raise StoreIntegrityError(
                "cold save delete journal changed while publication was guarded"
            )
        if plan.manifest_dirty:
            if plan.layout_value is None or not session._manifest_dirty:
                raise StoreIntegrityError(
                    "acknowledged layout journal changed while publication was guarded"
                )
        for target, owner in plan.pending_identity:
            if target not in session._pending_identity_current:
                raise StoreIntegrityError(
                    "identity journal changed while cold save was guarded"
                )
            current = session._pending_identity_current[target]
            if current is not owner and (
                current is _MISSING or owner is _MISSING or current != owner
            ):
                raise StoreIntegrityError(
                    "identity journal changed while cold save was guarded"
                )
        return

    # Once publication enters bookkeeping, a retry may observe any prefix of
    # our own idempotent cleanup. Supported mutation remains blocked, and the
    # durable successor is re-proved before publication resumes.
    if plan.manifest_dirty:
        if plan.layout_value is None:
            raise StoreIntegrityError("acknowledged layout journal lacks a layout")
        if not session._manifest_dirty:
            if session._manifest.get("collections") != dict(plan.layout_value):
                raise StoreIntegrityError(
                    "acknowledged layout journal changed while publication was guarded"
                )
    for target, owner in plan.pending_identity:
        if target in session._pending_identity_current:
            current = session._pending_identity_current[target]
            if current is not owner and (
                current is _MISSING or owner is _MISSING or current != owner
            ):
                raise StoreIntegrityError(
                    "identity journal changed while cold save was guarded"
                )
            continue
        committed = session._committed_identity_targets.get(target, _MISSING)
        if owner is _MISSING:
            if committed is not _MISSING:
                raise StoreIntegrityError(
                    "identity journal changed while cold save was guarded"
                )
        elif committed is not owner and (
            committed is _MISSING or committed != owner
        ):
            raise StoreIntegrityError(
                "identity journal changed while cold save was guarded"
            )

def _apply_acknowledged_journal(session, plan):
    from .persistence_tracking import _MISSING

    session._dirty.difference_update(plan.dirty_owners)
    session._deleted.difference_update(plan.deleted_owners)
    if plan.manifest_dirty:
        session._manifest["collections"] = dict(plan.layout_value)
        session._manifest_dirty = False
    for target, owner in plan.pending_identity:
        if owner is _MISSING:
            session._committed_identity_targets.pop(target, None)
        else:
            session._committed_identity_targets[target] = owner
        session._pending_identity_current.pop(target, None)
    session._identity_dirty = bool(session._pending_identity_current)
    session._identity_dirty_owners.clear()


def publish_cold_save(session, plan, prefix):
    """Adopt one proved successor and clear only its acknowledged journal."""
    if session._cold_plan is not plan:
        if session.generation == plan.target_generation and session._cold_plan is None:
            if prefix is not None:
                prefix.close()
            return session.generation
        raise StoreIntegrityError("cold save publication plan changed")

    log = session.world.events
    phase = session._cold_publication_phase
    if phase not in ("prepared", "adopted", "bookkeeping"):
        if prefix is not None:
            prefix.close()
        raise StoreIntegrityError("invalid cold save publication phase")

    if phase == "prepared":
        if prefix is None:
            raise StoreIntegrityError("cold save publication lacks replacement prefix")
        _cold_save_phase("before_adoption", session, plan)
        try:
            old_prefix = log._adopt_committed_prefix(
                prefix, transferred_events=plan.transfer_events
            )
        except Exception:
            prefix.close()
            raise
        session._cold_publication_phase = "adopted"
        session._cold_old_prefix_pending = old_prefix
        phase = "adopted"
        _cold_save_phase("after_adoption", session, plan)
    else:
        if prefix is not None:
            prefix.close()
        if (
            log._disk_count != plan.after_tail.disk_events
            or log._disk_prefix is None
            or log._disk_prefix.event_count != plan.after_prefix.event_count
            or log._disk_prefix.segment_count != plan.after_prefix.segment_count
            or log._disk_prefix.last_year != plan.after_prefix.last_year
        ):
            raise StoreIntegrityError(
                "partially published runtime prefix disagrees with save plan"
            )

    if phase == "adopted":
        _cold_save_phase("before_bookkeeping", session, plan)
        _validate_acknowledged_journal(session, plan)
        # Mark the retry boundary before destructive cleanup. A failure anywhere
        # after this point can safely resume idempotently from mixed pre/post
        # journal state without weakening first-pass validation.
        session._cold_publication_phase = "bookkeeping"
    else:
        _validate_acknowledged_journal(session, plan, allow_applied=True)

    _apply_acknowledged_journal(session, plan)
    _cold_save_phase("after_journal_cleanup", session, plan)
    _apply_persisted_key_changes(session, plan)

    session.generation = plan.target_generation
    session._cold_prefix_descriptor = plan.after_prefix
    session._cold_tail_descriptor = plan.after_tail
    session._cold_commit_descriptor = ColdCommitDescriptor(
        plan.target_generation, plan.token
    )
    # Head is replaced by the resolver/normal acknowledgement before publication.
    old_prefix = session._cold_old_prefix_pending
    session._cold_old_prefix_pending = None
    if old_prefix is not None:
        old_prefix.close()
    session._cold_plan = None
    session._cold_publication_phase = None
    session._cold_state = "active"
    return session.generation


def _resolve_cold_save_once(session, plan, *, full_evidence):
    try:
        status, head, prefix = _capture_successor(
            session, plan, full_evidence=full_evidence
        )
    except Exception:
        session._cold_state = "recovery-required"
        raise

    if status == "old":
        session._cold_plan = None
        session._cold_publication_phase = None
        session._cold_state = "active"
        return "old", plan.expected_generation

    if status == "foreign":
        session._cold_state = "stale"
        session._cold_plan = None
        session._cold_publication_phase = None
        if prefix is not None:
            prefix.close()
        raise StoreConflictError(
            f"cold session generation/token conflict at head {head.generation}"
        )

    session._cold_head = head
    session._cold_state = "recovery-required"
    try:
        generation = publish_cold_save(session, plan, prefix)
    except Exception:
        session._cold_state = "recovery-required"
        raise
    return "ours", generation


def save_cold(session):
    """Prepare and publish one atomic cold save generation."""
    session._ensure_cold_operation("save")
    session._cold_operation_depth += 1
    try:
        if session._cold_state != "active":
            raise StoreError(
                f"cold session cannot save while {session._cold_state}"
            )
        if session._cold_step_depth:
            raise StoreError("cold save requires a completed simulation step")
        if session.world.__dict__.get("_index_current_people"):
            raise StoreError("cold save cannot run inside current_people_scope")

        session._cold_state = "preparing"
        plan = None
        try:
            plan = prepare_cold_save(session)
        except StoreConflictError:
            session._cold_state = "stale"
            raise
        except Exception:
            session._cold_state = "active"
            raise

        if plan is None:
            session._cold_state = "active"
            return session.generation

        session._cold_plan = plan
        session._cold_publication_phase = "prepared"
        try:
            _cold_save_phase("before_commit_call", session, plan)
        except Exception:
            session._cold_plan = None
            session._cold_publication_phase = None
            session._cold_state = "active"
            raise
        try:
            generation = session.store.commit(
                plan.expected_generation,
                plan.changes,
                plan.new_segments,
                plan.metadata,
            )
        except StoreConflictError:
            session._cold_state = "stale"
            session._cold_plan = None
            session._cold_publication_phase = None
            raise
        except Exception as original:
            session._cold_state = "recovery-required"
            try:
                status, generation = _resolve_cold_save_once(
                    session, plan, full_evidence=True
                )
            except Exception as resolution:
                if session._cold_state == "recovery-required":
                    raise StoreError(
                        "cold save outcome is uncertain; resolve_save is required"
                    ) from resolution
                raise
            if status == "old":
                raise original
            return generation

        if generation != plan.target_generation:
            session._cold_state = "recovery-required"
            raise StoreIntegrityError(
                "cold store returned an unexpected committed generation"
            )

        # A normal acknowledgement pins the successor head/descriptors and the
        # replacement prefix in one checked read snapshot.  EventLog adoption
        # then checks every newly transferred segment value before trimming.
        try:
            status, head, prefix = _capture_successor(
                session, plan, full_evidence=False
            )
            if status != "ours":
                if prefix is not None:
                    prefix.close()
                if status == "foreign":
                    session._cold_state = "stale"
                    session._cold_plan = None
                    session._cold_publication_phase = None
                    raise StoreConflictError(
                        "cold save successor was replaced by another writer"
                    )
                session._cold_state = "recovery-required"
                raise StoreIntegrityError(
                    "committed cold successor was not visible"
                )
            session._cold_head = head
            session._cold_state = "recovery-required"
            return publish_cold_save(session, plan, prefix)
        except Exception:
            if session._cold_state != "stale":
                session._cold_state = "recovery-required"
            raise
    finally:
        session._cold_operation_depth -= 1

def resolve_cold_save(session):
    """Resolve one retained uncertain save plan without committing."""
    session._ensure_cold_operation("resolve")
    session._cold_operation_depth += 1
    try:
        if session._cold_state == "stale":
            raise StoreConflictError("cold session is stale")
        if session._cold_state == "closed":
            raise StoreError("cold session is closed")
        plan = session._cold_plan
        if plan is None:
            if session._cold_state != "active":
                raise StoreError(
                    f"cold session has no resolvable plan while {session._cold_state}"
                )
            try:
                _check_captured_store_baseline(session)
            except StoreConflictError:
                session._cold_state = "stale"
                raise
            return session.generation

        if session._cold_state not in ("recovery-required", "preparing"):
            raise StoreError(
                f"cold save cannot resolve while {session._cold_state}"
            )
        session._cold_state = "recovery-required"
        _status, generation = _resolve_cold_save_once(
            session, plan, full_evidence=True
        )
        return generation
    finally:
        session._cold_operation_depth -= 1

