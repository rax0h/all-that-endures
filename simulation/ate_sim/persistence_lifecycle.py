"""Explicit lifecycle/history operations for accepted P3B cold sessions."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import pickle
import weakref
import zlib

from .core import Event
from .event_log import EventLog, FrozenDict, FrozenList
from .incremental_store import StoreError, StoreIntegrityError
from .persistence_events import CHUNK_SIZE, _validate_sealed_event
from .persistence_session import _validate_suffix_event
from .record_index import RecordTable
from .persistence_event_ids import EventIdSet


def _lifecycle_phase(_phase, _session):
    """Private deterministic failure-injection seam for lifecycle tests."""
    return None


def _begin(session, operation, *, allow_stale=False):
    session._begin_lifecycle_operation(operation, allow_stale=allow_stale)


def _end(session, operation):
    session._end_lifecycle_operation(operation)


def verify_history(session):
    """Explicitly scrub the captured prefix plus current resident suffix."""
    _begin(session, "verify_history")
    try:
        log = session.world.events
        prefix = log._disk_prefix
        if prefix is None:
            raise StoreIntegrityError("cold session lost its disk EventLog prefix")
        before = prefix.diagnostics()
        verified = prefix.verify_full()
        previous_year = prefix.last_year
        expected_index = log._disk_count
        inspected = 0

        for number in range(len(log._chunks)):
            chunk = log._chunk(number)
            if len(chunk) != CHUNK_SIZE:
                raise StoreIntegrityError("pending cold EventLog chunk has wrong size")
            for event in chunk:
                _validate_suffix_event(event, expected_index)
                if event.__dict__.get("_sealed") is not True:
                    raise StoreIntegrityError(
                        "pending cold EventLog event is not sealed"
                    )
                _validate_sealed_event(event)
                if previous_year is not None and event.year < previous_year:
                    raise StoreIntegrityError(
                        "cold EventLog suffix chronology violation"
                    )
                previous_year = event.year
                expected_index += 1
                inspected += 1

        for event in log._tail:
            _validate_suffix_event(event, expected_index)
            if previous_year is not None and event.year < previous_year:
                raise StoreIntegrityError(
                    "cold EventLog tail chronology violation"
                )
            previous_year = event.year
            expected_index += 1
            inspected += 1

        if expected_index != log._count:
            raise StoreIntegrityError("cold EventLog suffix count mismatch")
        if log._count:
            if previous_year != log._last_year:
                raise StoreIntegrityError("cold EventLog last year mismatch")
        elif log._last_year is not None:
            raise StoreIntegrityError("empty cold EventLog has a last year")
        if session.world.next_event != log._count + 1:
            raise StoreIntegrityError("World next_event disagrees with EventLog")

        after = prefix.diagnostics()
        return {
            "captured_generation": verified["generation"],
            "disk_events": verified["events"],
            "disk_segments": verified["segments"],
            "pending_sealed_events": len(log._chunks) * CHUNK_SIZE,
            "tail_events": len(log._tail),
            "checked_segment_reads": (
                after.segment_reads - before.segment_reads
            ),
            "checked_segment_read_bytes": (
                after.segment_read_bytes - before.segment_read_bytes
            ),
            "inspected_suffix_events": inspected,
        }
    finally:
        _end(session, "verify_history")


def _standalone_log(old_log, session):
    """Stage a portable in-memory EventLog without changing the source."""
    old_log._ensure_backend_readable()
    prefix = old_log._disk_prefix
    if prefix is None:
        raise StoreIntegrityError("cold detach requires a captured disk prefix")

    chunks = []
    years = []
    offsets = []
    expected_id = 1
    previous_year = None
    absolute = 0

    def inspect(event, *, require_sealed):
        nonlocal expected_id, previous_year, absolute
        _validate_suffix_event(event, absolute)
        if event.id != expected_id:
            raise StoreIntegrityError("detach event ID discontinuity")
        if previous_year is not None and event.year < previous_year:
            raise StoreIntegrityError("detach event chronology violation")
        if require_sealed:
            if event.__dict__.get("_sealed") is not True:
                raise StoreIntegrityError("detach sealed history is mutable")
            _validate_sealed_event(event)
        if not years or years[-1] != event.year:
            years.append(event.year)
            offsets.append(absolute)
        previous_year = event.year
        expected_id += 1
        absolute += 1

    for ordinal in range(prefix.segment_count):
        events = prefix._read_segment_from_store(ordinal)
        for event in events:
            inspect(event, require_sealed=True)
        chunks.append(
            zlib.compress(
                pickle.dumps(list(events), protocol=5),
                level=1,
            )
        )
        _lifecycle_phase("after_disk_chunk", session)

    for number, compressed in enumerate(old_log._chunks):
        try:
            events = pickle.loads(zlib.decompress(compressed))
        except Exception as exc:
            raise StoreIntegrityError("invalid pending cold EventLog chunk") from exc
        if type(events) is not list or len(events) != CHUNK_SIZE:
            raise StoreIntegrityError("invalid pending cold EventLog chunk")
        for event in events:
            inspect(event, require_sealed=True)
        # Immutable bytes can be reused after validation.
        chunks.append(compressed)

    tail = list(old_log._tail)
    for event in tail:
        inspect(event, require_sealed=False)

    if absolute != old_log._count:
        raise StoreIntegrityError("detach EventLog count mismatch")
    if previous_year != old_log._last_year:
        raise StoreIntegrityError("detach EventLog last year mismatch")

    new_log = EventLog()
    new_log._disk_prefix = None
    new_log._disk_count = 0
    new_log._chunks = chunks
    new_log._tail = tail
    new_log._count = old_log._count
    new_log._years = years
    new_log._offsets = offsets
    new_log._cache.clear()
    new_log._last_year = old_log._last_year
    return new_log


def _stage_plain_graph(
    session, old_log, new_log, *, replacements=None
):
    """Stage wrapper removal/current-graph rewiring without source mutation."""
    from .persistence_tracking import (
        TrackedDict, TrackedList, TrackedSet,
        _RootDict, _RootList, _RootSet, _RootRecordTable,
    )

    memo = {id(old_log): new_log}
    if replacements:
        memo.update(replacements)
    assignments = []
    cache_removals = []
    index_rebindings = []

    def stage(value):
        from .persistence_lazy_household_members import LazyHouseholdMembers
        from .persistence_lazy_nested_history import HISTORY_TYPES
        if isinstance(value, (LazyHouseholdMembers, *HISTORY_TYPES)):
            ident = id(value)
            if ident in memo:
                return memo[ident]
            result = list(value)
            memo[ident] = result
            return result
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes):
            return value
        if cls in (FrozenDict, FrozenList):
            return value
        ident = id(value)
        if ident in memo:
            return memo[ident]

        if cls is tuple:
            result = tuple(stage(item) for item in value)
            memo[ident] = result
            return result
        if cls is frozenset:
            result = frozenset(stage(item) for item in value)
            memo[ident] = result
            return result

        if isinstance(value, _RootRecordTable):
            result = RecordTable()
            memo[ident] = result
            for key, child in value.items():
                staged_key = stage(key)
                staged_child = stage(child)
                # Staging must not call RecordTable.__setitem__: that would
                # rewrite the live IndexedRecord's _index_table/_index_key
                # before publication. Build the detached table structurally,
                # then rebind record index metadata only during publication.
                dict.__setitem__(result, staged_key, staged_child)
                if hasattr(staged_child, "_index_table"):
                    index_rebindings.append(
                        (staged_child, result, staged_key)
                    )
            return result
        if isinstance(value, (TrackedDict, _RootDict)):
            result = {}
            memo[ident] = result
            for key, child in value.items():
                result[stage(key)] = stage(child)
            return result
        if isinstance(value, (TrackedList, _RootList)):
            result = []
            memo[ident] = result
            result.extend(stage(child) for child in value)
            return result
        if isinstance(value, (TrackedSet, _RootSet, EventIdSet)):
            result = set()
            memo[ident] = result
            result.update(stage(child) for child in value)
            return result

        if isinstance(value, EventLog):
            if value is old_log:
                return new_log
            return value

        if is_dataclass(value):
            memo[ident] = value
            declared = {field.name for field in fields(cls)}
            for field in fields(cls):
                child = getattr(value, field.name)
                replacement = stage(child)
                if replacement is not child:
                    assignments.append((value, field.name, replacement))
            removable = []
            for name in tuple(getattr(value, "__dict__", ())):
                if (
                    name not in declared
                    and not (cls is Event and name == "_sealed")
                    and name != "_ate_persistence_lifetime"
                ):
                    removable.append(name)
            if removable:
                cache_removals.append((value, tuple(removable)))
            return value

        # Bound mutable state should have been normalized to tracking wrappers.
        # Plain containers may still occur in untracked cache/value positions;
        # preserve them unless a staged child actually needs replacement.
        if isinstance(value, dict):
            memo[ident] = value
            for key, child in list(value.items()):
                replacement = stage(child)
                if replacement is not child:
                    raise StoreIntegrityError(
                        "detach found an untracked mutable dictionary boundary"
                    )
            return value
        if isinstance(value, list):
            memo[ident] = value
            for child in value:
                replacement = stage(child)
                if replacement is not child:
                    raise StoreIntegrityError(
                        "detach found an untracked mutable list boundary"
                    )
            return value
        if isinstance(value, set):
            memo[ident] = value
            return value
        return value

    # The canonical EventLog root is remapped without traversing history, but
    # its resident tail Events remain the same objects and must shed any tracked
    # payload wrappers before the session closes.
    for event in new_log._tail:
        if stage(event) is not event:
            raise StoreIntegrityError("detach cannot replace resident tail Events")

    staged_world = stage(session.world)
    if staged_world is not session.world:
        raise StoreIntegrityError("detach cannot replace the World object")
    return assignments, cache_removals, index_rebindings


def _publish_detach(
    session,
    old_log,
    new_log,
    assignments,
    cache_removals,
    index_rebindings,
):
    """Publish a fully staged standalone graph; remaining steps are teardown."""
    old_prefix = old_log._disk_prefix
    pending_old_prefix = session._cold_old_prefix_pending
    lifetime = session._cold_lifetime

    session._suspended += 1
    try:
        for obj, name, replacement in assignments:
            object.__setattr__(obj, name, replacement)
        for obj, names in cache_removals:
            for name in names:
                obj.__dict__.pop(name, None)
        for record, table, key in index_rebindings:
            object.__setattr__(record, "_index_table", weakref.ref(table))
            object.__setattr__(record, "_index_key", key)
        session.world.__dict__.pop("_ate_persistence_lifetime", None)
        new_log.__dict__.pop("_ate_persistence_lifetime", None)
    finally:
        session._suspended -= 1

    session._clear_bindings()
    session._cold_operation_depth = 0
    session._cold_operation_name = None
    session._active = False
    session._cold_state = "closed"
    if lifetime is not None:
        lifetime.close()
    if old_prefix is not None:
        old_prefix.close()
    if pending_old_prefix is not None and pending_old_prefix is not old_prefix:
        pending_old_prefix.close()
    session._cold_old_prefix_pending = None
    session._cold_plan = None
    session._cold_publication_phase = None
    session._memo.clear()
    session._memo_reverse.clear()
    session._bound_root_originals.clear()
    session._bootstrap_originals.clear()
    session.store.close()
    return session.world


def detach(session, *, materialize_history=False):
    """Explicitly detach one cold World into a portable in-memory World."""
    _begin(session, "detach", allow_stale=True)
    published = False
    try:
        if not materialize_history:
            raise StoreError(
                "cold history requires detach(materialize_history=True)"
            )
        old_log = session.world.events
        _lifecycle_phase("before_history", session)
        new_log = _standalone_log(old_log, session)
        _lifecycle_phase("after_history", session)
        assignments, cache_removals, index_rebindings = _stage_plain_graph(
            session, old_log, new_log
        )
        _lifecycle_phase("before_publish", session)
        world = _publish_detach(
            session,
            old_log,
            new_log,
            assignments,
            cache_removals,
            index_rebindings,
        )
        published = True
        return world
    finally:
        if not published:
            _end(session, "detach")
