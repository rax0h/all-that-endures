"""P3A sealed-event disk segments and a bounded immutable-prefix reader.

This module is intentionally not wired into World or EventLog.  It prepares
bounded P1 changes/segments for a caller-owned transaction and borrows an open
TransactionalStore for lazy reads.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Iterator

from .core import Event, Layer, Ref
from .event_log import EventLog, FrozenDict, FrozenList
from .incremental_store import (
    NewSegment,
    RecordChange,
    StoreError,
    StoreFormatError,
    StoreIntegrityError,
    TransactionalStore,
)
from .persistence_adapters import WorldCodec


SEALED_EVENTS = "world_sealed_events"
EVENT_STORAGE = "world_event_storage"
DESCRIPTOR_KEY = "sealed-prefix/v1"
DESCRIPTOR_SCHEMA = 1
DESCRIPTOR_FORMAT = 1
SEGMENT_FORMAT = "sealed-events/v1"
CHUNK_SIZE = EventLog.chunk_size
CACHE_SIZE = EventLog.cache_size
MAX_PREPARE_CHUNKS = 4


@dataclass(frozen=True)
class SealedPrefixDescriptor:
    segment_count: int
    event_count: int
    last_year: int | None


@dataclass(frozen=True)
class SealedAppendPreparation:
    expected_generation: int
    record_changes: tuple[RecordChange, ...]
    new_segments: tuple[NewSegment, ...]
    consumed_events: int
    before: SealedPrefixDescriptor
    after: SealedPrefixDescriptor

    @property
    def is_noop(self) -> bool:
        return not self.record_changes and not self.new_segments


@dataclass(frozen=True)
class PrefixReadDiagnostics:
    segment_reads: int
    segment_read_bytes: int
    resident_segments: int


_EMPTY = SealedPrefixDescriptor(0, 0, None)


def _descriptor_value(descriptor: SealedPrefixDescriptor) -> tuple[Any, ...]:
    return (
        DESCRIPTOR_FORMAT,
        CHUNK_SIZE,
        descriptor.segment_count,
        descriptor.event_count,
        descriptor.last_year,
    )


def _decode_descriptor(value: Any) -> SealedPrefixDescriptor:
    if type(value) is not tuple or len(value) != 5:
        raise StoreFormatError("invalid sealed-event descriptor")
    version, chunk_size, segment_count, event_count, last_year = value
    if version != DESCRIPTOR_FORMAT or chunk_size != CHUNK_SIZE:
        raise StoreFormatError("unsupported sealed-event descriptor")
    if (
        type(segment_count) is not int
        or segment_count < 0
        or type(event_count) is not int
        or event_count < 0
        or event_count != segment_count * CHUNK_SIZE
    ):
        raise StoreIntegrityError("sealed-event descriptor count mismatch")
    if segment_count == 0:
        if last_year is not None:
            raise StoreIntegrityError("empty sealed-event prefix has a last year")
    elif type(last_year) is not int:
        raise StoreFormatError("invalid sealed-event descriptor last year")
    return SealedPrefixDescriptor(segment_count, event_count, last_year)


def _read_descriptor(
    store: TransactionalStore, *, allow_absent: bool
) -> SealedPrefixDescriptor:
    try:
        value = store.read_record(
            EVENT_STORAGE,
            DESCRIPTOR_KEY,
            expected_record_schema=DESCRIPTOR_SCHEMA,
        )
    except KeyError:
        namespaces = set(store.head_metadata()["namespaces"])
        if EVENT_STORAGE in namespaces or SEALED_EVENTS in namespaces:
            raise StoreIntegrityError("event storage namespace lacks its descriptor")
        if allow_absent:
            return _EMPTY
        raise StoreFormatError("sealed-event storage is not initialized")
    namespaces = set(store.head_metadata()["namespaces"])
    if EVENT_STORAGE not in namespaces or SEALED_EVENTS not in namespaces:
        raise StoreIntegrityError("event descriptor is outside the published namespace inventory")
    return _decode_descriptor(value)


def _validate_immutable_value(value: Any, active: set[int] | None = None) -> None:
    if active is None:
        active = set()
    cls = type(value)
    if value is None or cls in (bool, int, float, str, bytes) or cls is Layer:
        return
    ident = id(value)
    if ident in active:
        raise StoreFormatError("cycle in sealed event payload")
    active.add(ident)
    try:
        if cls is FrozenDict:
            for key, child in value.items():
                _validate_immutable_value(key, active)
                _validate_immutable_value(child, active)
            return
        if cls is FrozenList:
            for child in value:
                _validate_immutable_value(child, active)
            return
        if cls in (tuple, frozenset):
            for child in value:
                _validate_immutable_value(child, active)
            return
        if is_dataclass(value) and cls.__dataclass_params__.frozen:
            for field in fields(value):
                _validate_immutable_value(getattr(value, field.name), active)
            return
    finally:
        active.remove(ident)
    raise StoreFormatError(
        f"mutable/incompatible value in sealed event payload: {cls.__name__}"
    )


def _validate_sealed_event(event: Any) -> Event:
    if type(event) is not Event:
        raise StoreFormatError("sealed-event segments require Event values")
    if event.__dict__.get("_sealed") is not True:
        raise StoreFormatError("sealed-event input must already be sealed")
    if type(event.id) is not int or event.id < 1:
        raise StoreFormatError("invalid sealed event ID")
    if type(event.year) is not int:
        raise StoreFormatError("invalid sealed event year")
    if type(event.kind) is not str or type(event.layer) is not Layer:
        raise StoreFormatError("invalid sealed event kind/layer")
    if type(event.actors) is not tuple or any(type(actor) is not Ref for actor in event.actors):
        raise StoreFormatError("invalid sealed event actors")
    if event.location is not None and type(event.location) is not Ref:
        raise StoreFormatError("invalid sealed event location")
    if type(event.causes) is not tuple or any(type(cause) is not int for cause in event.causes):
        raise StoreFormatError("invalid sealed event causes")
    if type(event.data) is not FrozenDict:
        raise StoreFormatError("sealed event data must be frozen")
    _validate_immutable_value(event.data)
    return event


def _decode_segment(value: Any, ordinal: int) -> tuple[Event, ...]:
    if (
        type(value) is not tuple
        or len(value) != 2
        or value[0] != SEGMENT_FORMAT
        or type(value[1]) is not tuple
        or len(value[1]) != CHUNK_SIZE
    ):
        raise StoreFormatError("invalid sealed-event segment envelope")
    events = value[1]
    expected_id = ordinal * CHUNK_SIZE + 1
    previous_year = None
    for event in events:
        _validate_sealed_event(event)
        if event.id != expected_id:
            raise StoreIntegrityError("sealed-event segment ID discontinuity")
        if previous_year is not None and event.year < previous_year:
            raise StoreIntegrityError("sealed-event segment chronology violation")
        previous_year = event.year
        expected_id += 1
    return events


def prepare_sealed_append(
    store: TransactionalStore,
    events: Sequence[Event],
    *,
    max_chunks: int = MAX_PREPARE_CHUNKS,
) -> SealedAppendPreparation:
    """Prepare a bounded immutable-prefix append without committing it.

    The caller owns P1.commit and therefore can atomically compose this result
    with other changes in P3B.  At most four chunks are inspected/prepared.
    """
    if not isinstance(store, TransactionalStore):
        raise TypeError("store must be a TransactionalStore")
    if (
        isinstance(events, (str, bytes, bytearray))
        or not isinstance(events, Sequence)
    ):
        raise TypeError("events must be a finite sequence")
    if type(max_chunks) is not int or not 1 <= max_chunks <= MAX_PREPARE_CHUNKS:
        raise ValueError(f"max_chunks must be in 1..{MAX_PREPARE_CHUNKS}")
    total = len(events)
    if total % CHUNK_SIZE:
        raise ValueError("sealed-event append requires complete chunks")

    with store.read_transaction() as generation:
        before = _read_descriptor(store, allow_absent=True)

    if total == 0:
        return SealedAppendPreparation(
            generation, (), (), 0, before, before
        )

    chunk_count = min(total // CHUNK_SIZE, max_chunks)
    prepared: list[NewSegment] = []
    next_id = before.event_count + 1
    previous_year = before.last_year
    final_year = previous_year

    for local_ordinal in range(chunk_count):
        start = local_ordinal * CHUNK_SIZE
        chunk = tuple(events[start + i] for i in range(CHUNK_SIZE))
        for event in chunk:
            _validate_sealed_event(event)
            if event.id != next_id:
                raise StoreIntegrityError("sealed-event append ID discontinuity")
            if previous_year is not None and event.year < previous_year:
                raise StoreIntegrityError("sealed-event append chronology violation")
            previous_year = event.year
            final_year = event.year
            next_id += 1
        ordinal = before.segment_count + local_ordinal
        prepared.append(
            NewSegment(
                SEALED_EVENTS,
                ordinal,
                (SEGMENT_FORMAT, chunk),
                CHUNK_SIZE,
                chunk[0].id,
                chunk[-1].id,
            )
        )

    consumed = chunk_count * CHUNK_SIZE
    after = SealedPrefixDescriptor(
        before.segment_count + chunk_count,
        before.event_count + consumed,
        final_year,
    )
    change = RecordChange(
        EVENT_STORAGE,
        DESCRIPTOR_KEY,
        _descriptor_value(after),
        record_schema=DESCRIPTOR_SCHEMA,
    )
    return SealedAppendPreparation(
        generation,
        (change,),
        tuple(prepared),
        consumed,
        before,
        after,
    )


class SealedEventPrefix(Sequence):
    """Read-only view of one committed immutable sealed-event prefix."""

    def __init__(self, store: TransactionalStore):
        if not isinstance(store, TransactionalStore):
            raise TypeError("store must be a TransactionalStore")
        self._store = store
        self._store_identity = (id(store), id(store.db))
        self._closed = False
        self._cache: OrderedDict[int, tuple[Event, ...]] = OrderedDict()
        self._segment_reads = 0
        self._segment_read_bytes = 0
        with store.read_transaction() as generation:
            descriptor = _read_descriptor(store, allow_absent=False)
            self._generation = generation
            self._descriptor = descriptor

    @property
    def captured_generation(self) -> int:
        return self._generation

    @property
    def segment_count(self) -> int:
        self._ensure_readable()
        return self._descriptor.segment_count

    @property
    def resident_segments(self) -> int:
        return len(self._cache)

    def diagnostics(self) -> PrefixReadDiagnostics:
        return PrefixReadDiagnostics(
            self._segment_reads,
            self._segment_read_bytes,
            len(self._cache),
        )

    def reset_diagnostics(self) -> None:
        self._segment_reads = 0
        self._segment_read_bytes = 0

    def _ensure_readable(self) -> None:
        if self._closed:
            raise StoreError("sealed-event reader is closed")
        if (id(self._store), id(self._store.db)) != self._store_identity:
            raise StoreError("sealed-event reader store identity changed")
        self._store._ensure_open()

    def _load_segment(self, ordinal: int) -> tuple[Event, ...]:
        self._ensure_readable()
        if ordinal < 0 or ordinal >= self._descriptor.segment_count:
            raise IndexError(ordinal)
        cached = self._cache.get(ordinal)
        if cached is not None:
            self._cache.move_to_end(ordinal)
            return cached
        try:
            checked = self._store.read_segment_checked(SEALED_EVENTS, ordinal)
        except KeyError as exc:
            raise StoreIntegrityError(
                f"missing sealed-event segment: {ordinal}"
            ) from exc
        self._segment_reads += 1
        self._segment_read_bytes += checked.payload_bytes
        expected_first = ordinal * CHUNK_SIZE + 1
        expected_last = expected_first + CHUNK_SIZE - 1
        if (
            checked.element_count != CHUNK_SIZE
            or checked.first_id != expected_first
            or checked.last_id != expected_last
            or checked.created_generation > self._generation
        ):
            raise StoreIntegrityError("sealed-event segment metadata mismatch")
        events = _decode_segment(checked.value, ordinal)
        if events[0].id != checked.first_id or events[-1].id != checked.last_id:
            raise StoreIntegrityError("sealed-event payload disagrees with segment metadata")
        self._cache[ordinal] = events
        self._cache.move_to_end(ordinal)
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return events

    def __len__(self) -> int:
        self._ensure_readable()
        return self._descriptor.event_count

    def __getitem__(self, index):
        self._ensure_readable()
        count = self._descriptor.event_count
        if isinstance(index, slice):
            start, stop, step = index.indices(count)
            return [self[i] for i in range(start, stop, step)]
        if type(index) is not int:
            raise TypeError("sealed-event indices must be integers or slices")
        if index < 0:
            index += count
        if index < 0 or index >= count:
            raise IndexError(index)
        ordinal, offset = divmod(index, CHUNK_SIZE)
        return self._load_segment(ordinal)[offset]

    def __iter__(self) -> Iterator[Event]:
        for index in range(len(self)):
            yield self[index]

    def _lower_year(self, year: int) -> int:
        low, high = 0, self._descriptor.event_count
        while low < high:
            mid = (low + high) // 2
            if self[mid].year < year:
                low = mid + 1
            else:
                high = mid
        return low

    def _upper_year(self, year: int) -> int:
        low, high = 0, self._descriptor.event_count
        while low < high:
            mid = (low + high) // 2
            if self[mid].year <= year:
                low = mid + 1
            else:
                high = mid
        return low

    def between(self, first_year: int, last_year: int) -> list[Event]:
        self._ensure_readable()
        if last_year < first_year or self._descriptor.event_count == 0:
            return []
        start = self._lower_year(first_year)
        stop = self._upper_year(last_year)
        return self[start:stop]

    def verify_full(self) -> dict[str, int | None]:
        """Explicitly scrub every captured event segment and cross-segment order."""
        self._ensure_readable()
        expected_id = 1
        previous_year = None
        final_year = None
        for ordinal in range(self._descriptor.segment_count):
            events = self._load_segment(ordinal)
            for event in events:
                if event.id != expected_id:
                    raise StoreIntegrityError("sealed-event full verification ID mismatch")
                if previous_year is not None and event.year < previous_year:
                    raise StoreIntegrityError(
                        "sealed-event full verification chronology violation"
                    )
                expected_id += 1
                previous_year = event.year
                final_year = event.year
        if expected_id - 1 != self._descriptor.event_count:
            raise StoreIntegrityError("sealed-event full verification count mismatch")
        if final_year != self._descriptor.last_year:
            raise StoreIntegrityError("sealed-event descriptor last year mismatch")
        return {
            "generation": self._generation,
            "segments": self._descriptor.segment_count,
            "events": self._descriptor.event_count,
            "last_year": self._descriptor.last_year,
        }

    def close(self) -> None:
        if not self._closed:
            self._cache.clear()
            self._closed = True

    def __enter__(self) -> "SealedEventPrefix":
        self._ensure_readable()
        return self

    def __exit__(self, *_args) -> None:
        self.close()
