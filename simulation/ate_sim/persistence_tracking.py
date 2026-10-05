"""Opt-in P2B mutation ownership and incremental snapshot updates.

This layer binds an already-P2A-snapshotted live World. It is deliberately
separate from checkpoint.py and from query indexes. Unbound simulation objects
keep their existing behavior.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
import weakref

from .core import World, Event
from .event_log import EventLog, FrozenDict, FrozenList
from .record_index import RecordTable, IndexedRecord
from .incremental_store import (
    RecordChange, StoreConflictError, StoreError, StoreFormatError,
    StoreIntegrityError, TransactionalStore,
)
from .persistence_adapters import (
    META, RECORD_SCHEMA, SCHEMA,
    IDENTITY_DELTAS, IDENTITY_DELTA_SCHEMA,
    IDENTITY_LINKS, IDENTITY_LINK_SCHEMA, IDENTITY_STORAGE_CURRENT,
    WorldCodec, _audit, _roots, _kind, _restore_collection, _identity_groups,
    _verify_identity_graph, _read_manifest, _identity_mode, _read_identity_links,
    COLLECTION_LAYOUT,
)
from .persistence_schema import RECORD_FIELDS, ROOT_FIELDS, ROOT_TYPES
from .persistence_identity import (
    IdentityOccurrenceIndex,
    iter_mutable_event_items,
    iter_mutable_event_owners,
)


_BINDINGS = {}
_ORIGINAL_SETATTR = {}
_EVENTLOG_INSTALLED = False


class _ColdLifetime:
    """Tiny runtime-only guard retained by a cold World after session close."""

    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        self.closed = False

    def _session(self):
        session = self._session_ref()
        if self.closed or session is None or not session._active:
            raise StoreError("cold World session is closed")
        return session

    def ensure_mutation(self, _operation="mutation"):
        self._session()._ensure_mutation_allowed()

    def ensure_simulation(self, _operation="simulation"):
        self._session()._ensure_mutation_allowed()

    def begin_step(self):
        session = self._session()
        session._ensure_mutation_allowed()
        if session._cold_step_depth:
            raise StoreError("reentrant cold simulation step is not allowed")
        session._cold_step_depth += 1

    def end_step(self):
        session = self._session_ref()
        if session is not None and session._cold_step_depth:
            session._cold_step_depth -= 1

    def ensure_eventlog_read(self):
        session = self._session()
        if session._suspended:
            return
        if (
            session._cold_state == "recovery-required"
            and session._cold_publication_phase is not None
        ):
            raise StoreError(
                "cold EventLog is unavailable until save acknowledgement resolves"
            )

    def begin_operation(self, operation, *, allow_stale=False):
        session = self._session()
        session._begin_lifecycle_operation(
            operation, allow_stale=allow_stale
        )

    def end_operation(self, operation):
        session = self._session_ref()
        if session is not None and session._active:
            session._end_lifecycle_operation(operation)

    def close(self):
        self.closed = True
        self._session_ref = lambda: None


def _binding(value):
    return _BINDINGS.get(id(value))


def _mutable_record(value):
    return is_dataclass(value) and not type(value).__dataclass_params__.frozen


def _install_assignment_hooks():
    """Install inert-unless-bound dataclass assignment hooks once."""
    for cls in RECORD_FIELDS:
        if cls.__dataclass_params__.frozen or cls in _ORIGINAL_SETATTR:
            continue
        original = getattr(cls, "__setattr__", object.__setattr__)
        _ORIGINAL_SETATTR[cls] = original

        def hooked(self, name, value, _original=original):
            bound = _binding(self)
            token = None
            assigned = value
            if bound is not None:
                if not bound.session._suspended:
                    bound.session._ensure_mutation_allowed(
                        subject=self, field=name, value=value
                    )
                token = bound.before_assignment(self, name, value)
                if token is not None and token[0] in ("owned", "root_collection", "root_collection_normalize"):
                    assigned = token[-1]
            _original(self, name, assigned)
            if bound is not None:
                bound.after_assignment(self, name, assigned, token)

        cls.__setattr__ = hooked


def _install_eventlog_hooks():
    global _EVENTLOG_INSTALLED
    if _EVENTLOG_INSTALLED:
        return
    _EVENTLOG_INSTALLED = True
    original_append = EventLog.append
    original_seal = EventLog.seal_before
    original_event_seal = Event.seal

    def append(log, event):
        bound = _binding(log)
        if bound is not None:
            bound.session._ensure_mutation_allowed()
            bound.event_append_preflight(log, event)
        original_append(log, event)
        if bound is not None:
            bound.event_appended(log, event)

    def event_seal(event):
        was_sealed = event.__dict__.get("_sealed") is True
        bound = _binding(event)
        if bound is not None:
            bound.session._ensure_mutation_allowed()
        original_event_seal(event)
        if was_sealed:
            return
        if bound is not None:
            bound.event_sealed(event)

    def seal_before(log, year):
        bound = _binding(log)
        if bound is not None:
            bound.session._ensure_mutation_allowed()
        before = len(log._chunks)
        retired = []
        cursor = 0
        while (
            len(log._tail) - cursor >= log.chunk_size
            and log._tail[cursor + log.chunk_size - 1].year < year
        ):
            retired.extend(
                log._tail[cursor:cursor + log.chunk_size]
            )
            cursor += log.chunk_size
        original_seal(log, year)
        if bound is not None and len(log._chunks) != before:
            start = log._disk_count + before * log.chunk_size
            bound.event_chunks_changed(log, start, tuple(retired))

    EventLog.append = append
    Event.seal = event_seal
    EventLog.seal_before = seal_before


class _ObjectBinding:
    def __init__(self, session, owners=(), root_fields=None):
        self.session = session
        self.owners = set(owners)
        self.root_fields = root_fields

    def add_owners(self, owners):
        self.owners.update(owners)

    def before_assignment(self, obj, name, value):
        if self.session._suspended or name not in RECORD_FIELDS.get(type(obj), ()):
            return None
        if self.root_fields is not None:
            spec = self.root_fields.get(name)
            if spec is None:
                return None
            namespace, kind = spec
            if kind == "state":
                raise StoreError("bound root state objects cannot be replaced in P2B")
            if kind == "int":
                return ("root_scalar", namespace, getattr(obj, name))
            return self.session._prepare_root_assignment(namespace, getattr(obj, name), value, kind)
        owners = frozenset(self.owners)
        wrapped = self.session._prepare_nested(
            value, owners, preflight=False
        )
        return ("owned", getattr(obj, name), owners, wrapped)

    def after_assignment(self, obj, name, value, token):
        if token is None or self.session._suspended:
            return
        if token[0] == "root_scalar":
            _, namespace, old = token
            if old != value:
                self.session._mark((namespace, 0))
            return
        if token[0] in ("root_collection", "root_collection_normalize"):
            self.session._finish_root_assignment(token)
            return
        _, old, owners, wrapped = token
        if old is not wrapped:
            self.session._detach(old, owners)
        self.session._mark_many(owners)

    def event_append_preflight(self, log, event):
        self.session._preflight_event_append(log, event)

    def event_appended(self, log, event):
        self.session._event_appended(log, event)

    def event_sealed(self, event):
        self.session._event_sealed(event)

    def event_chunks_changed(self, log, first_index, retired_events):
        self.session._event_chunks_changed(
            log, first_index, retired_events
        )


class _NestedMixin:
    _ate_tracked_kind = None

    def _setup(self, session, owners):
        self._session = session
        self._owners = set(owners)

    def _add_owners(self, owners):
        self._owners.update(owners)

    def _guard(self):
        self._session._ensure_mutation_allowed()

    def _touch(self):
        self._session._ensure_mutation_allowed()
        if not self._session._suspended:
            self._session._mark_many(self._owners)

    def _bind(self, value):
        # Nested simulation state may intentionally share an existing mutable
        # descendant (for example mastery samples and their source event data).
        # The identity manifest records that legal topology change.
        if self._session._contains_identity(value, self):
            raise StoreError("cycles are not supported by P2B")
        return self._session._prepare_nested(value, self._owners, allow_existing=True)

    def _detach_value(self, value):
        self._session._detach(value, self._owners)


class TrackedDict(_NestedMixin, dict):
    _ate_tracked_kind = "dict"

    def __setitem__(self, key, value):
        old = self.get(key, _MISSING)
        value = self._bind(value)
        dict.__setitem__(self, key, value)
        if old is not _MISSING and old is not value:
            self._detach_value(old)
        self._touch()

    def __delitem__(self, key):
        self._guard()
        old = self[key]
        dict.__delitem__(self, key)
        self._detach_value(old)
        self._touch()

    def update(self, other=(), **kwargs):
        for key, value in dict(other, **kwargs).items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def pop(self, key, *default):
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        value = self[key]
        del self[key]
        return value

    def popitem(self):
        if not self:
            raise KeyError("popitem(): dictionary is empty")
        key = next(reversed(self))
        return key, self.pop(key)

    def clear(self):
        self._guard()
        old = list(self.values())
        dict.clear(self)
        for value in old:
            self._detach_value(value)
        self._touch()

    def __ior__(self, other):
        self.update(other)
        return self


class TrackedList(_NestedMixin, list):
    _ate_tracked_kind = "list"

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            old = self[index]
            values = [self._bind(v) for v in value]
            trial = list(self)
            list.__setitem__(trial, index, list(values))
            list.__setitem__(self, index, values)
            for item in old:
                self._detach_value(item)
        else:
            old = self[index]
            wrapped = self._bind(value)
            list.__setitem__(self, index, wrapped)
            if old is not wrapped:
                self._detach_value(old)
        self._touch()

    def __delitem__(self, index):
        self._guard()
        old = self[index]
        list.__delitem__(self, index)
        if isinstance(index, slice):
            for item in old:
                self._detach_value(item)
        else:
            self._detach_value(old)
        self._touch()

    def append(self, value):
        list.append(self, self._bind(value))
        self._touch()

    def extend(self, values):
        list.extend(self, [self._bind(v) for v in values])
        self._touch()

    def insert(self, index, value):
        list.insert(self, index, self._bind(value))
        self._touch()

    def pop(self, index=-1):
        self._guard()
        value = self[index]
        result = list.pop(self, index)
        self._detach_value(value)
        self._touch()
        return result

    def remove(self, value):
        index = self.index(value)
        self.pop(index)

    def clear(self):
        self._guard()
        old = list(self)
        list.clear(self)
        for value in old:
            self._detach_value(value)
        self._touch()

    def sort(self, *args, **kwargs):
        self._guard()
        list.sort(self, *args, **kwargs)
        self._touch()

    def reverse(self):
        self._guard()
        list.reverse(self)
        self._touch()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n):
        self._guard()
        # Repetition aliases existing mutable children. P2B forbids creating
        # new shared-mutable topology through a container operator.
        if n > 1 and any(self._session._is_mutable(v) for v in self):
            raise StoreError("list repetition would create unsupported mutable aliases")
        list.__imul__(self, n)
        self._touch()
        return self


class TrackedSet(_NestedMixin, set):
    _ate_tracked_kind = "set"

    def add(self, value):
        self._guard()
        before = len(self)
        set.add(self, value)
        if len(self) != before:
            self._touch()

    def discard(self, value):
        self._guard()
        before = len(self)
        set.discard(self, value)
        if len(self) != before:
            self._touch()

    def remove(self, value):
        self._guard()
        set.remove(self, value)
        self._touch()

    def pop(self):
        self._guard()
        value = set.pop(self)
        self._touch()
        return value

    def clear(self):
        self._guard()
        if self:
            set.clear(self)
            self._touch()

    def update(self, *others):
        self._guard()
        before = set(self)
        set.update(self, *others)
        if self != before:
            self._touch()

    def intersection_update(self, *others):
        self._guard()
        before = set(self)
        set.intersection_update(self, *others)
        if self != before:
            self._touch()

    def difference_update(self, *others):
        self._guard()
        before = set(self)
        set.difference_update(self, *others)
        if self != before:
            self._touch()

    def symmetric_difference_update(self, other):
        self._guard()
        before = set(self)
        set.symmetric_difference_update(self, other)
        if self != before:
            self._touch()

    def __ior__(self, other):
        self.update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self


class _RootDict(dict):
    _ate_tracked_kind = "dict"

    def _setup(self, session, namespace, kind, ordinals):
        self._session = session
        self._namespace = namespace
        self._kind = kind
        self._ordinals = dict(ordinals)
        self._next_ordinal = max(self._ordinals.values(), default=-1) + 1

    def ordinal(self, key):
        return self._ordinals[key]

    def _stable(self):
        if self._kind == "dict":
            self._kind = "dict-stable/v1"
        self._session._manifest_dirty = True

    def __setitem__(self, key, value):
        self._session._ensure_mutation_allowed()
        owner = (self._namespace, key)
        exists = key in self
        old = self.get(key, _MISSING)
        wrapped = self._session._prepare_nested(value, {owner})
        dict.__setitem__(self, key, wrapped)
        if exists and old is not wrapped:
            self._session._detach(old, {owner})
        if not exists:
            self._ordinals[key] = self._next_ordinal
            self._next_ordinal += 1
            self._session._manifest_dirty = True
        self._session._changed_member_work += 1
        self._session._mark(owner)

    def __delitem__(self, key):
        self._session._ensure_mutation_allowed()
        owner = (self._namespace, key)
        old = self[key]
        dict.__delitem__(self, key)
        self._ordinals.pop(key)
        self._session._detach(old, {owner})
        self._session._delete(owner)
        self._stable()
        self._session._changed_member_work += 1

    def update(self, other=(), **kwargs):
        for key, value in dict(other, **kwargs).items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def pop(self, key, *default):
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        value = self[key]
        del self[key]
        return value

    def popitem(self):
        if not self:
            raise KeyError("popitem(): dictionary is empty")
        key = next(reversed(self))
        return key, self.pop(key)

    def clear(self):
        for key in list(self):
            del self[key]

    def __ior__(self, other):
        self.update(other)
        return self


class _RootRecordTable(RecordTable):
    _ate_tracked_kind = "dict"

    def _setup(self, session, namespace, kind, ordinals):
        self._session = session
        self._namespace = namespace
        self._kind = kind
        self._ordinals = dict(ordinals)
        self._next_ordinal = max(self._ordinals.values(), default=-1) + 1

    def ordinal(self, key):
        return self._ordinals[key]

    def _stable(self):
        if self._kind in ("dict", "RecordTable"):
            self._kind = "RecordTable-stable/v1"
        self._session._manifest_dirty = True

    def __setitem__(self, key, record):
        self._session._ensure_mutation_allowed()
        owner = (self._namespace, key)
        exists = key in self
        old = self.get(key, _MISSING)
        record = self._session._prepare_nested(record, {owner})
        dict.__setitem__(self, key, record)
        if isinstance(record, IndexedRecord):
            record._index_table = weakref.ref(self)
            record._index_key = key
        self.changed(key)
        if exists and old is not record:
            self._session._detach(old, {owner})
        if not exists:
            self._ordinals[key] = self._next_ordinal
            self._next_ordinal += 1
            self._session._manifest_dirty = True
        self._session._changed_member_work += 1
        self._session._mark(owner)

    def __delitem__(self, key):
        self._session._ensure_mutation_allowed()
        owner = (self._namespace, key)
        old = self[key]
        dict.__delitem__(self, key)
        self.changed(key)
        self._ordinals.pop(key)
        self._session._detach(old, {owner})
        self._session._delete(owner)
        self._stable()
        self._session._changed_member_work += 1

    def update(self, records=(), **kwargs):
        for key, record in dict(records, **kwargs).items():
            self[key] = record

    def clear(self):
        for key in list(self):
            del self[key]
        self.__dict__.pop("_indexes", None)

    def pop(self, key, *default):
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        record = self[key]
        del self[key]
        return record

    def popitem(self):
        if not self:
            raise KeyError("popitem(): dictionary is empty")
        key = next(reversed(self))
        return key, self.pop(key)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def __ior__(self, other):
        self.update(other)
        return self


class _RootList(list):
    _ate_tracked_kind = "list"

    def _setup(self, session, namespace, kind="list"):
        self._session = session
        self._namespace = namespace
        self._kind = kind

    def append(self, value):
        index = len(self)
        owner = (self._namespace, index)
        wrapped = self._session._prepare_nested(value, {owner})
        list.append(self, wrapped)
        self._session._changed_member_work += 1
        self._session._mark(owner)
        self._session._manifest_dirty = True

    def extend(self, values):
        prepared = list(values)
        for value in prepared:
            self.append(value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            trial = list(self)
            raw = list(value)
            list.__setitem__(trial, index, raw)  # validate extended slices first
            self._replace_from(trial)
            return
        if index < 0:
            index += len(self)
        owner = (self._namespace, index)
        old = self[index]
        wrapped = self._session._prepare_nested(value, {owner})
        list.__setitem__(self, index, wrapped)
        if old is not wrapped:
            self._session._detach(old, {owner})
        self._session._changed_member_work += 1
        self._session._mark(owner)

    def __delitem__(self, index):
        trial = list(self)
        list.__delitem__(trial, index)
        self._replace_from(trial)

    def insert(self, index, value):
        trial = list(self)
        list.insert(trial, index, value)
        self._replace_from(trial)

    def pop(self, index=-1):
        trial = list(self)
        result = list.pop(trial, index)
        self._replace_from(trial)
        return result

    def remove(self, value):
        trial = list(self)
        list.remove(trial, value)
        self._replace_from(trial)

    def clear(self):
        self._replace_from([])

    def sort(self, *args, **kwargs):
        trial = list(self)
        trial.sort(*args, **kwargs)
        self._replace_from(trial)

    def reverse(self):
        trial = list(self)
        trial.reverse()
        self._replace_from(trial)

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n):
        trial = list(self)
        trial *= n
        self._replace_from(trial)
        return self

    def _replace_from(self, raw):
        self._session._ensure_mutation_allowed()
        old = list(self)
        prepared = [
            self._session._prepare_nested(value, {(self._namespace, i)}, allow_existing=True)
            for i, value in enumerate(raw)
        ]
        list.clear(self)
        list.extend(self, prepared)
        limit = max(len(old), len(prepared))
        for i in range(limit):
            old_value = old[i] if i < len(old) else _MISSING
            new_value = prepared[i] if i < len(prepared) else _MISSING
            if old_value is new_value:
                continue
            if old_value is not _MISSING:
                self._session._detach(old_value, {(self._namespace, i)})
            if new_value is _MISSING:
                self._session._delete((self._namespace, i))
            else:
                self._session._mark((self._namespace, i))
            self._session._changed_member_work += 1
        if len(old) != len(prepared):
            self._session._manifest_dirty = True


class _RootSet(set):
    _ate_tracked_kind = "set"

    def _setup(self, session, namespace, kind, ordinals):
        self._session = session
        self._namespace = namespace
        self._kind = kind
        self._ordinals = dict(ordinals)
        self._by_ordinal = {ordinal: value for value, ordinal in self._ordinals.items()}
        self._next_ordinal = max(self._by_ordinal, default=-1) + 1

    def value_for_ordinal(self, ordinal):
        return self._by_ordinal[ordinal]

    def _stable(self):
        if self._kind == "set":
            self._kind = "set-stable/v1"
        self._session._manifest_dirty = True

    def add(self, value):
        self._session._ensure_mutation_allowed()
        self._session._changed_member_work += 1
        if value in self:
            return
        ordinal = self._next_ordinal
        self._next_ordinal += 1
        set.add(self, value)
        self._ordinals[value] = ordinal
        self._by_ordinal[ordinal] = value
        self._session._mark((self._namespace, ordinal))
        self._session._manifest_dirty = True

    def _discard_existing(self, value):
        ordinal = self._ordinals.pop(value)
        self._by_ordinal.pop(ordinal)
        set.remove(self, value)
        self._session._delete((self._namespace, ordinal))
        self._stable()

    def discard(self, value):
        self._session._ensure_mutation_allowed()
        self._session._changed_member_work += 1
        if value in self:
            self._discard_existing(value)

    def remove(self, value):
        self._session._ensure_mutation_allowed()
        self._session._changed_member_work += 1
        if value not in self:
            raise KeyError(value)
        self._discard_existing(value)

    def pop(self):
        self._session._ensure_mutation_allowed()
        if not self:
            raise KeyError("pop from an empty set")
        value = next(iter(self))
        self.remove(value)
        return value

    def clear(self):
        for value in list(self):
            self.discard(value)

    def update(self, *others):
        for other in others:
            for value in other:
                self.add(value)

    def intersection_update(self, *others):
        keep = set(self).intersection(*others)
        for value in list(self):
            if value not in keep:
                self.discard(value)

    def difference_update(self, *others):
        remove = set().union(*others) if others else set()
        for value in list(remove):
            self.discard(value)

    def symmetric_difference_update(self, other):
        for value in list(other):
            if value in self:
                self.discard(value)
            else:
                self.add(value)

    def __ior__(self, other):
        self.update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def __ixor__(self, other):
        self.symmetric_difference_update(other)
        return self


_MISSING = object()


class IncrementalWorldSession:
    """Bind one live World to one durable snapshot and track current mutation."""

    def __init__(self, world, path, *, rules_id):
        if type(world) is not World:
            raise TypeError("expected World")
        codec = WorldCodec(identity_links_recorded=True)
        store = TransactionalStore.open(
            path, codec=codec, expected_simulation_schema=SCHEMA,
            expected_rules_id=rules_id,
        )
        self._initialize_runtime(
            world, store, codec=codec, cold_mode=False
        )
        try:
            with self.store.read_transaction():
                self.generation = self.store.generation
                self._manifest = _read_manifest(self.store)
                if type(self._manifest) is not dict or self._manifest.get("schema") != SCHEMA:
                    raise StoreFormatError("incremental binding requires a P2A snapshot")
                head_namespaces = set(self.store.head_metadata()["namespaces"])
                self._identity_mode, self._initial_links = _read_identity_links(
                    self.store, self._manifest, head_namespaces
                )
                if self._identity_mode == "legacy":
                    delta_rows = (
                        self.store.read_records(
                            IDENTITY_DELTAS,
                            expected_record_schema=IDENTITY_DELTA_SCHEMA,
                        )
                        if IDENTITY_DELTAS in head_namespaces else []
                    )
                    self._identity_delta_next = len(delta_rows)
                    self._has_identity_deltas = bool(delta_rows)
                else:
                    self._committed_identity_targets = dict(self._initial_links)
                    self._live_identity_targets = dict(self._initial_links)
                self._validate_baseline()
                self._validate_bound_identity()
            self._normalize_bootstrap()
            self._bind_roots()
            self._bootstrap_identity_index()
        except Exception:
            self._undo_bound_roots()
            self._undo_bootstrap()
            self._clear_bindings()
            self.store.close()
            self._active = False
            raise
        finally:
            self._suspended = 0

    @classmethod
    def _from_cold_capture(cls, store, capture, baseline_ordinals):
        """Bind an already-validated cold capture without rereading history."""
        if type(capture.world) is not World:
            raise TypeError("cold capture did not restore a World")
        if not isinstance(store.codec, WorldCodec):
            raise StoreFormatError("cold session requires WorldCodec")
        self = cls.__new__(cls)
        self._initialize_runtime(
            capture.world,
            store,
            codec=store.codec,
            cold_mode=True,
        )
        try:
            self.generation = capture.generation
            self._manifest = capture.manifest
            self._identity_mode = "current"
            self._initial_links = list(capture.identity_links)
            self._committed_identity_targets = dict(self._initial_links)
            self._live_identity_targets = dict(self._initial_links)
            self._baseline_ordinals = {
                namespace: dict(ordinals)
                for namespace, ordinals in baseline_ordinals.items()
            }
            self._cold_head = capture.head
            self._cold_prefix_descriptor = capture.prefix_descriptor
            self._cold_tail_descriptor = capture.tail_descriptor
            self._cold_commit_descriptor = capture.commit_descriptor
            self._cold_committed_n = capture.tail_descriptor.total_events
            self._normalize_bootstrap()
            self._bind_roots()
            self._bootstrap_identity_index()
            self._initialize_cold_persisted_keys()
            self._cold_lifetime = _ColdLifetime(self)
            object.__setattr__(
                self.world, "_ate_persistence_lifetime", self._cold_lifetime
            )
            self.world.events._ate_persistence_lifetime = self._cold_lifetime
        except Exception:
            self._undo_bound_roots()
            self._undo_bootstrap()
            self._clear_bindings()
            capture.prefix.close()
            self.store.close()
            self._active = False
            raise
        finally:
            self._suspended = 0
        return self

    def _initialize_runtime(self, world, store, *, codec, cold_mode):
        _install_assignment_hooks()
        _install_eventlog_hooks()
        self.world = world
        self.codec = codec
        self.store = store
        self.generation = store.generation
        self._cold_mode = bool(cold_mode)
        self._dirty = set()
        self._deleted = set()
        self._manifest_dirty = False
        self._active = True
        self._suspended = 1
        self._bound_ids = set()
        self._memo = {}
        self._memo_reverse = {}
        self._root_containers = {}
        self._scalar_fields = {}
        self._baseline_ordinals = {}
        self._identity_dirty = False
        self._identity_dirty_owners = set()
        self._identity_index = None
        self._identity_mode = None
        self._identity_delta_next = 0
        self._pending_identity_patch = None
        self._has_identity_deltas = False
        self._committed_identity_targets = {}
        self._live_identity_targets = {}
        self._pending_identity_current = {}
        self._changed_member_work = 0
        self._bootstrap_originals = {}
        self._bound_root_originals = {}
        self._initial_links = []
        self._cold_state = "active" if self._cold_mode else None
        self._cold_plan = None
        self._cold_publication_phase = None
        self._cold_old_prefix_pending = None
        self._cold_persisted_keys = {}
        self._cold_step_depth = 0
        self._cold_operation_depth = 0
        self._cold_operation_name = None
        self._cold_head = None
        self._cold_prefix_descriptor = None
        self._cold_tail_descriptor = None
        self._cold_commit_descriptor = None
        self._cold_committed_n = 0
        self._cold_lifetime = None
        self._excluded_namespaces = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _ensure_active(self):
        if not self._active:
            raise StoreError("incremental World session is closed")
        if self._cold_mode:
            self.store._ensure_open()

    def _ensure_cold_operation(self, operation):
        self._ensure_active()
        if not self._cold_mode:
            raise StoreError(f"{operation} is only available for cold World sessions")
        if self._cold_operation_depth:
            raise StoreError(f"reentrant cold session {operation} is not allowed")

    def _ensure_mutation_allowed(
        self, *, subject=None, field=None, value=_MISSING
    ):
        self._ensure_active()
        external_guard = getattr(self, "_external_mutation_guard", None)
        if external_guard is not None:
            external_guard(subject=subject, field=field, value=value)
        if self._cold_mode and self._cold_state != "active":
            raise StoreError(
                f"cold World session mutation is blocked while {self._cold_state}"
            )
        if self._cold_mode and self._cold_operation_depth:
            raise StoreError(
                "cold World session mutation is blocked during "
                f"{self._cold_operation_name or 'an active operation'}"
            )

    def _begin_lifecycle_operation(self, operation, *, allow_stale=False):
        self._ensure_active()
        if not self._cold_mode:
            raise StoreError(
                f"{operation} is only available for cold World sessions"
            )
        if self._cold_operation_depth:
            raise StoreError(
                f"reentrant cold session {operation} is not allowed"
            )
        if self._cold_step_depth:
            raise StoreError(
                f"{operation} requires a completed simulation step"
            )
        if self.world.__dict__.get("_index_current_people"):
            raise StoreError(
                f"{operation} cannot run inside current_people_scope"
            )
        allowed = self._cold_state == "active" or (
            allow_stale and self._cold_state == "stale"
        )
        if not allowed:
            raise StoreError(
                f"cold session cannot {operation} while {self._cold_state}"
            )
        self._cold_operation_depth = 1
        self._cold_operation_name = operation

    def _end_lifecycle_operation(self, operation):
        if (
            self._cold_operation_depth != 1
            or self._cold_operation_name != operation
        ):
            raise StoreError("cold lifecycle operation guard changed")
        self._cold_operation_depth = 0
        self._cold_operation_name = None

    def _initialize_cold_persisted_keys(self):
        if not self._cold_mode:
            return
        from .persistence_events import (
            DESCRIPTOR_KEY, EVENT_STORAGE
        )
        from .persistence_session import (
            COMMIT_DESCRIPTOR_KEY, TAIL_DESCRIPTOR_KEY
        )
        keys = {
            META: {"manifest"},
            IDENTITY_LINKS: set(self._committed_identity_targets),
            EVENT_STORAGE: {
                DESCRIPTOR_KEY,
                TAIL_DESCRIPTOR_KEY,
                COMMIT_DESCRIPTOR_KEY,
            },
        }
        if self._cold_head.namespace_counts.get(META, (0, 0))[0] == 2:
            keys[META].add(COLLECTION_LAYOUT)
        for namespace, (_obj, _name) in self._scalar_fields.items():
            keys[namespace] = {0}
        for namespace, container in self._root_containers.items():
            if namespace == "world.events" or namespace in self._excluded_namespaces:
                continue
            kind = self._base_kind(self._description(namespace)[0])
            if kind in ("dict", "RecordTable"):
                keys[namespace] = set(container)
            elif kind == "list":
                keys[namespace] = set(range(len(container)))
            elif kind == "set":
                keys[namespace] = set(container._by_ordinal)
        self._cold_persisted_keys = keys

    def _is_mutable(self, value):
        return isinstance(value, _NestedMixin) or type(value) in (dict, list, set, RecordTable, EventLog) or _mutable_record(value)

    def _register_binding(self, value, binding):
        ident = id(value)
        existing = _BINDINGS.get(ident)
        if existing is not None and existing.session is not self:
            raise StoreError("object is already bound to another persistence session")
        _BINDINGS[ident] = binding
        self._bound_ids.add(ident)

    def _remember_memo(self, source, replacement):
        self._memo[id(source)] = (source, replacement)
        self._memo_reverse[id(replacement)] = id(source)

    def _drop_memo_if_unowned(self, value):
        bound = _binding(value)
        if bound is not None and bound.session is self and bound.owners:
            return
        if isinstance(value, _NestedMixin) and value._owners:
            return
        source_id = self._memo_reverse.get(id(value))
        if source_id is None:
            return
        pair = self._memo.get(source_id)
        if pair is None or pair[1] is not value:
            return
        self._memo_reverse.pop(id(value), None)
        self._memo.pop(source_id, None)

    def _discard_owner_binding(self, value, owner):
        bound = _binding(value)
        if bound is not None and bound.session is self:
            bound.owners.discard(owner)
            if not bound.owners and bound.root_fields is None:
                _BINDINGS.pop(id(value), None)
                self._bound_ids.discard(id(value))
        if isinstance(value, _NestedMixin):
            value._owners.discard(owner)
        self._drop_memo_if_unowned(value)

    @staticmethod
    def _base_kind(kind):
        return {
            "dict-stable/v1": "dict",
            "RecordTable-stable/v1": "RecordTable",
            "set-stable/v1": "set",
            "EventLog-disk/v1": "EventLog",
        }.get(kind, kind)

    def _validate_baseline(self):
        counts = self.store.verify_all()
        if counts["segments"]:
            raise StoreFormatError("P2B requires P2A record snapshots")
        head = self.store.head_metadata()
        if (
            head["simulation_position"] != self.world.year
            or head["seed"] != self.world.seed
            or head["next_ids"] != {
                key: getattr(self.world, key)
                for key in ("next_person", "next_household", "next_settlement", "next_event")
            }
        ):
            raise StoreIntegrityError("live World metadata does not match bound snapshot")
        compare = WorldCodec(identity_links_recorded=True)
        for root, obj in _roots(self.world):
            for name, expected in ROOT_FIELDS[root].items():
                if expected == "state":
                    continue
                namespace = root + "." + name
                description = self._manifest["collections"].get(namespace)
                if type(description) is not tuple or len(description) != 3:
                    raise StoreFormatError(f"missing collection description: {namespace}")
                live = getattr(obj, name)
                live_kind = _kind(live, expected)
                stored_kind = self._base_kind(description[0])
                if live_kind != stored_kind:
                    raise StoreIntegrityError(f"live collection kind differs from snapshot: {namespace}")
                restored = _restore_collection(self.store, namespace, expected, description)
                rows = self.store.read_records(namespace, expected_record_schema=RECORD_SCHEMA)
                ordinals = {}
                for key, envelope, _ in rows:
                    if type(envelope) is not tuple or len(envelope) != 2:
                        raise StoreFormatError("invalid entry envelope")
                    ordinal, stored_value = envelope
                    if live_kind in ("dict", "RecordTable"):
                        ordinals[key] = ordinal
                    elif live_kind == "set":
                        ordinals[stored_value] = ordinal
                    else:
                        ordinals[key] = ordinal
                self._baseline_ordinals[namespace] = ordinals
                if live_kind in ("dict", "RecordTable"):
                    if list(live) != list(restored):
                        raise StoreIntegrityError(f"live key/order differs from snapshot: {namespace}")
                    for key in live:
                        if compare.encode(self._plain(live[key])) != compare.encode(self._plain(restored[key])):
                            raise StoreIntegrityError(f"live value differs from snapshot: {namespace}")
                elif live_kind in ("list", "EventLog"):
                    if len(live) != len(restored):
                        raise StoreIntegrityError(f"live sequence size differs from snapshot: {namespace}")
                    for left, right in zip(live, restored):
                        if compare.encode(self._plain(left)) != compare.encode(self._plain(right)):
                            raise StoreIntegrityError(f"live sequence differs from snapshot: {namespace}")
                elif live_kind == "set":
                    if {compare.encode(v) for v in live} != {compare.encode(v) for v in restored}:
                        raise StoreIntegrityError(f"live set differs from snapshot: {namespace}")
                elif live != restored:
                    raise StoreIntegrityError(f"live scalar differs from snapshot: {namespace}")

    def _normalize_bootstrap(self):
        if type(self.world.events) is list:
            self._bootstrap_originals["events"] = self.world.events
            object.__setattr__(self.world, "events", EventLog(self.world.events))
        for name in ("people", "households"):
            value = getattr(self.world, name)
            if type(value) is dict:
                self._bootstrap_originals[name] = value
                object.__setattr__(self.world, name, RecordTable(value))

    def _undo_bootstrap(self):
        for name, value in self._bootstrap_originals.items():
            object.__setattr__(self.world, name, value)
        self._bootstrap_originals.clear()

    def _undo_bound_roots(self):
        for (_ident, name), (obj, value) in reversed(tuple(self._bound_root_originals.items())):
            object.__setattr__(obj, name, value)
        self._bound_root_originals.clear()

    def _bind_roots(self):
        for root, obj in _roots(self.world):
            field_specs = {}
            for name, kind in ROOT_FIELDS[root].items():
                namespace = root + "." + name
                if namespace in self._excluded_namespaces:
                    continue
                field_specs[name] = (namespace, kind)
                if kind == "state":
                    continue
                value = getattr(obj, name)
                if kind == "int":
                    self._scalar_fields[namespace] = (obj, name)
                    continue
                wrapped = self._bind_root_collection(namespace, value, kind)
                if wrapped is not value:
                    self._bound_root_originals[(id(obj), name)] = (obj, value)
                    object.__setattr__(obj, name, wrapped)
            bound = _binding(obj)
            if bound is None:
                bound = _ObjectBinding(self, root_fields=field_specs)
                self._register_binding(obj, bound)
            else:
                bound.root_fields = field_specs

    def _bind_root_collection(self, namespace, value, expected):
        description = self._manifest["collections"].get(namespace)
        if type(description) is not tuple or len(description) != 3:
            raise StoreFormatError(f"missing collection description: {namespace}")
        stored_kind, size, _chunks = description
        if len(value) != size:
            raise StoreIntegrityError(f"live World disagrees with snapshot size: {namespace}")
        live_kind = _kind(value, expected)
        ordinals = self._baseline_ordinals.get(namespace, {})
        if expected == "dict":
            if live_kind == "RecordTable":
                # Runtime query normalization is rebuildable behavior, not a
                # persistence mutation. Keep the stored adapter kind until a
                # structural persistence change actually requires versioning.
                kind = stored_kind
                wrapped = _RootRecordTable()
                wrapped._setup(self, namespace, kind, ordinals)
                for key, record in value.items():
                    owner = (namespace, key)
                    record = self._bind_nested(record, {owner}, initial=True)
                    dict.__setitem__(wrapped, key, record)
                    if isinstance(record, IndexedRecord):
                        object.__setattr__(record, "_index_table", weakref.ref(wrapped))
                        object.__setattr__(record, "_index_key", key)
            else:
                kind = stored_kind
                wrapped = _RootDict()
                wrapped._setup(self, namespace, kind, ordinals)
                for key, item in value.items():
                    dict.__setitem__(
                        wrapped, key,
                        self._bind_nested(item, {(namespace, key)}, initial=True),
                    )
            self._root_containers[namespace] = wrapped
            return wrapped
        if expected == "list":
            wrapped = _RootList()
            wrapped._setup(self, namespace, "list")
            for i, item in enumerate(value):
                list.append(wrapped, self._bind_nested(item, {(namespace, i)}, initial=True))
            self._root_containers[namespace] = wrapped
            return wrapped
        if expected == "set":
            wrapped = _RootSet(value)
            wrapped._setup(self, namespace, stored_kind, ordinals)
            self._root_containers[namespace] = wrapped
            return wrapped
        if expected == "events":
            if live_kind == "EventLog":
                binding = _binding(value)
                if binding is None:
                    binding = _ObjectBinding(self)
                    self._register_binding(value, binding)
                items = (
                    iter_mutable_event_items(value)
                    if self._cold_mode
                    else enumerate(value)
                )
                for i, event in items:
                    self._bind_nested(
                        event, {(namespace, i)}, initial=True
                    )
                self._root_containers[namespace] = value
                return value
            wrapped = _RootList()
            wrapped._setup(self, namespace, "list")
            for i, item in enumerate(value):
                list.append(wrapped, self._bind_nested(item, {(namespace, i)}, initial=True))
            self._root_containers[namespace] = wrapped
            return wrapped
        raise StoreFormatError(f"unsupported bound collection kind: {stored_kind}")

    def _validate_incoming(self, value, owners, *, allow_existing=False, active=None):
        if active is None:
            active = set()
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
            return
        ident = id(value)
        if ident in active:
            raise StoreError("cycles are not supported by P2B")
        memo = self._memo.get(ident)
        if memo is not None:
            source, _replacement = memo
            if source is not value:
                raise StoreIntegrityError("identity memo address reused for a different object")
            # Re-observing the retained raw source is sound proof of sharing.
            return
        tracked_owners = None
        if isinstance(value, _NestedMixin):
            if value._session is not self:
                raise StoreError("cross-session mutable alias")
            tracked_owners = value._owners
        else:
            bound = _binding(value)
            if bound is not None:
                if bound.session is not self:
                    raise StoreError("cross-session mutable alias")
                tracked_owners = bound.owners
        if tracked_owners is not None:
            if set(owners) - set(tracked_owners) and not allow_existing:
                raise StoreError("mutation creates unsupported shared mutable ownership")
            return
        active.add(ident)
        try:
            if _mutable_record(value):
                for name in RECORD_FIELDS[type(value)]:
                    self._validate_incoming(
                        getattr(value, name), owners,
                        allow_existing=allow_existing, active=active,
                    )
            elif cls in (dict, RecordTable):
                for key, child in value.items():
                    self._validate_incoming(key, owners, allow_existing=allow_existing, active=active)
                    self._validate_incoming(child, owners, allow_existing=allow_existing, active=active)
            elif cls in (list, tuple, set, frozenset):
                for child in value:
                    self._validate_incoming(child, owners, allow_existing=allow_existing, active=active)
        finally:
            active.remove(ident)

    def _prepare_nested(
        self, value, owners, *, allow_existing=False, preflight=True
    ):
        if preflight:
            self._ensure_mutation_allowed()
        self._validate_incoming(value, owners, allow_existing=allow_existing)
        return self._bind_nested(
            value, owners, initial=False, allow_existing=allow_existing
        )

    def _propagate_owners(self, value, owners, seen=None):
        if seen is None:
            seen = set()
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
            return
        ident = id(value)
        if ident in seen:
            return
        seen.add(ident)
        if isinstance(value, _NestedMixin):
            value._add_owners(owners)
        bound = _binding(value)
        if bound is not None and bound.session is self:
            bound.add_owners(owners)
        if is_dataclass(value):
            for name in RECORD_FIELDS.get(cls, ()):
                self._propagate_owners(getattr(value, name), owners, seen)
        elif isinstance(value, dict):
            for key, child in value.items():
                self._propagate_owners(key, owners, seen)
                self._propagate_owners(child, owners, seen)
        elif isinstance(value, EventLog):
            items = (
                iter_mutable_event_items(value)
                if self._cold_mode
                else enumerate(value)
            )
            for _index, child in items:
                self._propagate_owners(child, owners, seen)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for child in value:
                self._propagate_owners(child, owners, seen)

    def _bind_nested(self, value, owners, *, initial, allow_existing=False):
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes):
            return value
        if cls in (FrozenDict, FrozenList) or cls is frozenset:
            return value
        if cls is tuple:
            return tuple(
                self._bind_nested(v, owners, initial=initial, allow_existing=allow_existing)
                for v in value
            )
        if isinstance(value, _NestedMixin):
            if value._session is not self:
                raise StoreError("cross-session mutable alias")
            previous = set(value._owners)
            new = set(owners) - previous
            if new and not (initial or allow_existing):
                raise StoreError("mutation creates unsupported shared mutable ownership")
            if new:
                self._propagate_owners(value, owners)
                if not initial:
                    self._identity_dirty = True
                    self._mark_many(previous | set(owners))
            return value
        existing = _binding(value)
        if existing is not None:
            if existing.session is not self:
                raise StoreError("cross-session mutable alias")
            new = set(owners) - existing.owners
            if new and not (initial or allow_existing):
                raise StoreError("mutation creates unsupported shared mutable ownership")
            if new:
                self._propagate_owners(value, owners)
                if not initial:
                    self._identity_dirty = True
            return value
        memo = self._memo.get(id(value))
        if memo is not None:
            source, replacement = memo
            if source is not value:
                raise StoreIntegrityError("identity memo address reused for a different object")
            bound = _binding(replacement)
            previous = set(bound.owners) if bound is not None else set(getattr(replacement, "_owners", ()))
            new = set(owners) - previous
            if new:
                self._propagate_owners(replacement, owners)
                if not initial:
                    self._identity_dirty = True
                    self._mark_many(previous | set(owners))
            return replacement
        if _mutable_record(value):
            bound = _ObjectBinding(self, owners)
            self._register_binding(value, bound)
            self._remember_memo(value, value)
            for name in RECORD_FIELDS[type(value)]:
                child = getattr(value, name)
                replacement = self._bind_nested(
                    child, owners, initial=initial, allow_existing=allow_existing
                )
                if replacement is not child:
                    object.__setattr__(value, name, replacement)
            return value
        if cls in (dict, RecordTable):
            wrapped = TrackedDict()
            wrapped._setup(self, owners)
            self._remember_memo(value, wrapped)
            for key, child in value.items():
                dict.__setitem__(
                    wrapped, key,
                    self._bind_nested(child, owners, initial=initial, allow_existing=allow_existing),
                )
            return wrapped
        if cls is list:
            wrapped = TrackedList()
            wrapped._setup(self, owners)
            self._remember_memo(value, wrapped)
            for child in value:
                list.append(
                    wrapped,
                    self._bind_nested(child, owners, initial=initial, allow_existing=allow_existing),
                )
            return wrapped
        if cls is set:
            wrapped = TrackedSet(value)
            wrapped._setup(self, owners)
            self._remember_memo(value, wrapped)
            return wrapped
        return value

    def _contains_identity(self, value, target, seen=None):
        if value is target:
            return True
        if seen is None:
            seen = set()
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
            return False
        ident = id(value)
        if ident in seen:
            return False
        seen.add(ident)
        if is_dataclass(value):
            return any(
                self._contains_identity(getattr(value, name), target, seen)
                for name in RECORD_FIELDS.get(cls, ())
            )
        if isinstance(value, dict):
            return any(
                self._contains_identity(key, target, seen)
                or self._contains_identity(child, target, seen)
                for key, child in value.items()
            )
        if isinstance(value, EventLog):
            items = (
                iter_mutable_event_items(value)
                if self._cold_mode
                else enumerate(value)
            )
            return any(
                self._contains_identity(child, target, seen)
                for _index, child in items
            )
        if isinstance(value, (list, tuple, set, frozenset)):
            return any(
                self._contains_identity(child, target, seen)
                for child in value
            )
        return False

    @staticmethod
    def _namespace_path(namespace):
        parts = namespace.split(".")
        if not parts or parts[0] != "world":
            raise StoreFormatError(f"invalid World namespace: {namespace}")
        return tuple(("field", part) for part in parts[1:])

    def _owner_path(self, owner):
        namespace, key = owner
        base = self._namespace_path(namespace)
        kind = self._base_kind(self._manifest["collections"][namespace][0])
        if kind in ("dict", "RecordTable"):
            return base + (("key", key),)
        if kind in ("list", "EventLog"):
            return base + (("index", key),)
        if kind == "set":
            return base + (("index", key),)
        return base

    def _iter_identity_owners(self):
        for root, obj in _roots(self.world):
            for name, expected in ROOT_FIELDS[root].items():
                if expected in ("state", "int"):
                    continue
                namespace = root + "." + name
                if namespace in self._excluded_namespaces:
                    continue
                value = getattr(obj, name)
                if expected == "dict":
                    for key, child in value.items():
                        yield (namespace, key), child, self._owner_path((namespace, key))
                elif expected == "events" and self._cold_mode:
                    yield from iter_mutable_event_owners(value)
                elif expected in ("list", "events"):
                    for i, child in enumerate(value):
                        yield (
                            (namespace, i),
                            child,
                            self._owner_path((namespace, i)),
                        )
                elif expected == "set":
                    continue

    def _bootstrap_identity_index(self):
        self._identity_index = IdentityOccurrenceIndex(
            self.codec,
            RECORD_FIELDS,
            mutable_event_tail_only=self._cold_mode,
        )
        self._identity_index.bootstrap(self._iter_identity_owners())
        self._identity_index.seed_explicit_links(self._initial_links)

    def _merge_current_identity_patch(self, removes, adds):
        touched = set()
        for target, _owner in removes:
            self._live_identity_targets.pop(target, None)
            touched.add(target)
        for target, owner in adds:
            self._live_identity_targets[target] = owner
            touched.add(target)
        for target in touched:
            before = self._committed_identity_targets.get(target, _MISSING)
            after = self._live_identity_targets.get(target, _MISSING)
            if (
                (before is _MISSING and after is _MISSING)
                or (before is not _MISSING and after is not _MISSING and before == after)
            ):
                self._pending_identity_current.pop(target, None)
            else:
                self._pending_identity_current[target] = after
        self._identity_dirty = bool(self._pending_identity_current)

    def _merge_identity_patch(self, removes, adds):
        if self._identity_mode == "current":
            self._merge_current_identity_patch(removes, adds)
            return
        pending_removes, pending_adds = {}, {}
        if self._pending_identity_patch is not None:
            for link in self._pending_identity_patch[0]:
                pending_removes[self.codec.encode(link)] = link
            for link in self._pending_identity_patch[1]:
                pending_adds[self.codec.encode(link)] = link
        for link in removes:
            token = self.codec.encode(link)
            if token in pending_adds:
                pending_adds.pop(token)
            else:
                pending_removes[token] = link
        for link in adds:
            token = self.codec.encode(link)
            if token in pending_removes:
                pending_removes.pop(token)
            else:
                pending_adds[token] = link
        if pending_removes or pending_adds:
            self._pending_identity_patch = (
                tuple(pending_removes[token] for token in sorted(pending_removes)),
                tuple(pending_adds[token] for token in sorted(pending_adds)),
            )
            self._identity_dirty = True
        else:
            self._pending_identity_patch = None
            self._identity_dirty = False

    def _refresh_identity_index(self):
        if not self._identity_dirty_owners:
            return
        owners = sorted(
            self._identity_dirty_owners,
            key=lambda owner: (owner[0], self.codec.encode(owner[1])),
        )
        for owner in owners:
            value = None if owner in self._deleted else self._owner_value(owner)
            removed, added = self._identity_index.refresh(
                owner, value, self._owner_path(owner)
            )
            # Preserve refresh order. List shifts can create a temporary
            # old-index/new-index alias which a later owner refresh removes;
            # final-state reducers must see add then remove, not grouped phases.
            self._merge_identity_patch(removed, added)
        self._identity_dirty_owners.clear()

    def _owner_value(self, owner):
        namespace, key = owner
        if namespace in self._scalar_fields:
            obj, name = self._scalar_fields[namespace]
            return getattr(obj, name)
        container = self._root_containers.get(namespace)
        if container is None:
            return None
        kind = self._base_kind(self._description(namespace)[0])
        try:
            if kind in ("dict", "RecordTable"):
                return container[key]
            if kind == "EventLog" and self._cold_mode:
                first = (
                    container._disk_count
                    + len(container._chunks) * container.chunk_size
                )
                local = key - first
                if local < 0 or local >= len(container._tail):
                    return None
                event = container._tail[local]
                if event.__dict__.get("_sealed") is True:
                    return None
                return event
            if kind in ("list", "EventLog"):
                return container[key]
            if kind == "set":
                return container.value_for_ordinal(key)
        except (KeyError, IndexError):
            return None
        return None

    def _remove_owner_recursive(self, value, owner, seen=None):
        if seen is None:
            seen = set()
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes, FrozenDict, FrozenList):
            return
        ident = id(value)
        if ident in seen:
            return
        seen.add(ident)
        current = self._owner_value(owner)
        if current is not None and self._contains_identity(current, value):
            return
        # Owner tags are live tracking metadata. Persisted identity is repaired
        # from this owner's occurrence index at save time. Descendants are
        # released before their parent so memo pairs cannot retain a detached
        # mutable graph after its last owner disappears.
        if is_dataclass(value):
            for name in RECORD_FIELDS.get(cls, ()):
                self._remove_owner_recursive(getattr(value, name), owner, seen)
        elif isinstance(value, dict):
            for key, child in value.items():
                self._remove_owner_recursive(key, owner, seen)
                self._remove_owner_recursive(child, owner, seen)
        elif isinstance(value, EventLog):
            items = (
                iter_mutable_event_items(value)
                if self._cold_mode
                else enumerate(value)
            )
            for _index, child in items:
                self._remove_owner_recursive(child, owner, seen)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for child in value:
                self._remove_owner_recursive(child, owner, seen)
        self._discard_owner_binding(value, owner)

    def _detach(self, value, owners):
        if self._suspended or not self._is_mutable(value):
            return
        for owner in owners:
            self._remove_owner_recursive(value, owner)

    def _prepare_root_assignment(self, namespace, old, value, kind):
        # indexed(owner, name) performs an exact dict -> RecordTable runtime
        # normalization. Accept it only when keys/order and record identities
        # are unchanged; this is rebuildable query behavior, not persisted data.
        if kind == "dict" and type(value) is RecordTable:
            if list(value) != list(old) or any(value[key] is not old[key] for key in old):
                raise StoreError("RecordTable normalization changed canonical root data")
            current = self._root_containers[namespace]
            wrapped = _RootRecordTable()
            wrapped._setup(
                self, namespace, getattr(current, "_kind", "dict"),
                dict(getattr(current, "_ordinals", {})),
            )
            for key, record in value.items():
                record = self._prepare_nested(
                    record, {(namespace, key)}, allow_existing=True
                )
                dict.__setitem__(wrapped, key, record)
                if isinstance(record, IndexedRecord):
                    object.__setattr__(record, "_index_table", weakref.ref(wrapped))
                    object.__setattr__(record, "_index_key", key)
            return ("root_collection_normalize", namespace, old, wrapped)

        # The retained agency action tail is the one canonical list replacement
        # performed by normal simulation.
        if namespace != "world.agency.actions" or kind != "list" or type(value) is not list:
            raise StoreError("bound root collection replacement is unsupported in P2B")
        wrapped = _RootList()
        wrapped._setup(self, namespace, "list")
        for i, item in enumerate(value):
            list.append(
                wrapped,
                self._prepare_nested(item, {(namespace, i)}, allow_existing=True),
            )
        return ("root_collection", namespace, old, wrapped)

    def _finish_root_assignment(self, token):
        if token[0] == "root_collection_normalize":
            _, namespace, _old, wrapped = token
            self._root_containers[namespace] = wrapped
            return
        _, namespace, old, wrapped = token
        old_values = list(old)
        self._root_containers[namespace] = wrapped
        limit = max(len(old_values), len(wrapped))
        for i in range(limit):
            before = old_values[i] if i < len(old_values) else _MISSING
            after = wrapped[i] if i < len(wrapped) else _MISSING
            if before is after:
                continue
            if before is not _MISSING:
                self._detach(before, {(namespace, i)})
            if after is _MISSING:
                self._delete((namespace, i))
            else:
                self._mark((namespace, i))
            self._changed_member_work += 1
        self._manifest_dirty = True

    def _mark(self, owner):
        self._ensure_active()
        self._deleted.discard(owner)
        self._dirty.add(owner)
        self._identity_dirty_owners.add(owner)

    def _mark_many(self, owners):
        for owner in owners:
            self._mark(owner)

    def _delete(self, owner):
        self._ensure_active()
        self._dirty.discard(owner)
        self._deleted.add(owner)
        self._identity_dirty_owners.add(owner)

    def _mark_storage_only(self, owner):
        """Journal a persisted value without granting mutable identity authority."""
        self._ensure_active()
        self._deleted.discard(owner)
        self._dirty.add(owner)
        self._identity_dirty_owners.discard(owner)

    def _preflight_event_append(self, log, event):
        """Reject invalid/foreign appends before EventLog mutates."""
        self._ensure_active()
        log._ensure_backend_readable()
        if event.id != log._count + 1:
            raise ValueError("events require consecutive stable IDs")
        if log._last_year is not None and event.year < log._last_year:
            raise ValueError("event time cannot run backwards")
        owner = ("world.events", log._count)
        self._validate_incoming(
            event, {owner}, allow_existing=True
        )

    def _event_appended(self, log, event):
        namespace = "world.events"
        index = len(log) - 1
        owner = (namespace, index)
        sealed = event.__dict__.get("_sealed") is True
        if not (self._cold_mode and sealed):
            self._bind_nested(
                event, {owner}, initial=False, allow_existing=True
            )
            self._mark(owner)
        else:
            self._mark_storage_only(owner)
        self._changed_member_work += 1
        self._manifest_dirty = True

    def _retire_log_owners(self, owner_events):
        """Retire exact LOG owners from current and stale tracked graphs."""
        pairs = tuple(owner_events)
        if not pairs:
            return
        owners = tuple(owner for owner, _event in pairs)
        stale = {
            owner: tuple(
                row[1]
                for row in self._identity_index.owner_occurrences.get(
                    owner, ()
                )
            )
            for owner in owners
        }

        self._identity_dirty_owners.difference_update(owners)
        removed, added = self._identity_index.retire_owners(owners)
        self._merge_identity_patch(removed, added)

        for owner, event in pairs:
            seen = set()
            self._remove_owner_recursive(event, owner, seen)
            for value in stale[owner]:
                self._remove_owner_recursive(value, owner, seen)

    def _event_sealed(self, event):
        if not self._cold_mode:
            return
        bound = _binding(event)
        if bound is None or bound.session is not self:
            return
        owners = tuple(
            owner for owner in bound.owners
            if owner[0] == "world.events"
        )
        for owner in owners:
            # Sealing changes the row value even though the Event immediately
            # stops being mutable LOG identity.
            self._mark_storage_only(owner)
        self._retire_log_owners(
            (owner, event) for owner in owners
        )

    def _event_chunks_changed(self, log, first_index, retired_events):
        self._manifest_dirty = True
        if not self._cold_mode:
            return
        if not retired_events:
            return
        if (
            type(first_index) is not int
            or len(retired_events) % log.chunk_size
        ):
            raise StoreIntegrityError("invalid cold sealing retirement boundary")
        pairs = []
        for offset, event in enumerate(retired_events):
            index = first_index + offset
            if event.id != index + 1 or event.__dict__.get("_sealed") is not True:
                raise StoreIntegrityError(
                    "sealed EventLog retirement disagrees with stable history"
                )
            pairs.append((("world.events", index), event))
        self._retire_log_owners(pairs)

    def _validate_bound_identity(self):
        if self._identity_mode == "current" or self._has_identity_deltas:
            _verify_identity_graph(self.world, self._initial_links)
            return
        links = []
        _audit(self.world, (), {}, set(), links)
        if _identity_groups(links) != _identity_groups(self._initial_links):
            raise StoreIntegrityError("live World identity does not match snapshot manifest")

    def _current_identity_links(self):
        seen = {}
        active = set()
        links = []

        def walk(value, path):
            cls = type(value)
            if value is None or cls in (bool, int, float, str, bytes) or cls in (FrozenDict, FrozenList):
                return
            ident = id(value)
            if ident in active:
                raise StoreError("cycle in bound World")
            record = is_dataclass(value)
            mutable = isinstance(value, (dict, list, set, EventLog)) or (
                record and not cls.__dataclass_params__.frozen
            )
            if mutable and ident in seen:
                links.append((path, seen[ident][0]))
                return
            if mutable:
                seen[ident] = (path, value)
            active.add(ident)
            try:
                if record:
                    for name in RECORD_FIELDS.get(cls, ()):
                        walk(getattr(value, name), path + (("field", name),))
                elif isinstance(value, dict):
                    for key, child in value.items():
                        walk(key, path + (("map_key", key),))
                        walk(child, path + (("key", key),))
                elif isinstance(value, EventLog):
                    items = (
                        iter_mutable_event_items(value)
                        if self._cold_mode
                        else enumerate(value)
                    )
                    for i, child in items:
                        walk(child, path + (("index", i),))
                elif isinstance(value, (list, tuple)):
                    for i, child in enumerate(value):
                        walk(child, path + (("index", i),))
                elif isinstance(value, (set, frozenset)):
                    for i, child in enumerate(value):
                        walk(child, path + (("index", i),))
            finally:
                active.remove(ident)

        walk(self.world, ())
        return links

    def _description(self, namespace):
        current = self._manifest["collections"][namespace]
        value = self._root_containers.get(namespace)
        if value is None:
            return current
        if type(value) is EventLog:
            if self._cold_mode:
                sealed = value._disk_count + len(value._chunks) * value.chunk_size
                return (
                    "EventLog-disk/v1",
                    len(value),
                    sealed // value.chunk_size,
                )
            return ("EventLog", len(value), len(value._chunks))
        kind = getattr(value, "_kind", current[0])
        return (kind, len(value), 0)

    def _plain(self, value, memo=None):
        if memo is None:
            memo = {}
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes) or cls in (FrozenDict, FrozenList):
            return value
        if cls is tuple:
            return tuple(self._plain(v, memo) for v in value)
        if cls is frozenset:
            return frozenset(self._plain(v, memo) for v in value)
        ident = id(value)
        if ident in memo:
            return memo[ident]
        if is_dataclass(value):
            clone = object.__new__(cls)
            memo[ident] = clone
            for field in fields(cls):
                object.__setattr__(clone, field.name, self._plain(getattr(value, field.name), memo))
            if cls is Event and "_sealed" in vars(value):
                object.__setattr__(clone, "_sealed", vars(value)["_sealed"])
            return clone
        if isinstance(value, dict):
            clone = {}
            memo[ident] = clone
            for key, child in value.items():
                clone[self._plain(key, memo)] = self._plain(child, memo)
            return clone
        if isinstance(value, list):
            clone = []
            memo[ident] = clone
            clone.extend(self._plain(v, memo) for v in value)
            return clone
        if isinstance(value, set):
            clone = set()
            memo[ident] = clone
            clone.update(self._plain(v, memo) for v in value)
            return clone
        return value

    def _record_value(self, namespace, key):
        if namespace in self._scalar_fields:
            obj, name = self._scalar_fields[namespace]
            return (0, getattr(obj, name))
        container = self._root_containers[namespace]
        kind = self._base_kind(self._description(namespace)[0])
        if kind in ("dict", "RecordTable"):
            return (container.ordinal(key), container[key])
        if kind in ("list", "EventLog"):
            return (key, container[key])
        if kind == "set":
            return (key, container.value_for_ordinal(key))
        raise StoreFormatError(f"unsupported incremental namespace: {namespace}")

    def _metadata(self):
        namespaces = tuple(self._manifest["collections"]) + (META,)
        if self._identity_mode == "current":
            namespaces += (IDENTITY_LINKS,)
        elif self._has_identity_deltas or self._pending_identity_patch is not None:
            namespaces += (IDENTITY_DELTAS,)
        return {
            "simulation_position": self.world.year,
            "seed": self.world.seed,
            "next_ids": {
                key: getattr(self.world, key)
                for key in ("next_person", "next_household", "next_settlement", "next_event")
            },
            "namespaces": namespaces,
        }

    def _changes(self):
        self._refresh_identity_index()
        changes = []
        for namespace, key in sorted(self._deleted, key=lambda x: (x[0], self.codec.encode(x[1]))):
            changes.append(RecordChange(namespace, key, delete=True))
        for namespace, key in sorted(self._dirty, key=lambda x: (x[0], self.codec.encode(x[1]))):
            envelope = self._plain(self._record_value(namespace, key))
            changes.append(RecordChange(namespace, key, envelope, record_schema=RECORD_SCHEMA))
        if self._identity_mode == "current":
            for target in sorted(
                self._pending_identity_current,
                key=self.codec.encode,
            ):
                owner = self._pending_identity_current[target]
                changes.append(RecordChange(
                    IDENTITY_LINKS,
                    target,
                    None if owner is _MISSING else owner,
                    record_schema=IDENTITY_LINK_SCHEMA,
                    delete=owner is _MISSING,
                ))
        elif self._pending_identity_patch is not None:
            patch = (
                "identity-delta/v1",
                self._pending_identity_patch[0],
                self._pending_identity_patch[1],
            )
            changes.append(RecordChange(
                IDENTITY_DELTAS,
                self._identity_delta_next,
                patch,
                record_schema=IDENTITY_DELTA_SCHEMA,
            ))
        if self._manifest_dirty:
            collections = dict(self._manifest["collections"])
            for namespace in self._root_containers:
                collections[namespace] = self._description(namespace)
            changes.append(RecordChange(META, COLLECTION_LAYOUT, collections, record_schema=RECORD_SCHEMA))
        return changes

    def _acknowledged(self, changes, metadata, expected_generation):
        if self.store.generation != expected_generation + 1:
            return False
        expected_head = dict(metadata)
        expected_head["namespaces"] = tuple(sorted(set(metadata["namespaces"])))
        if self.store.head_metadata() != expected_head:
            return False
        for change in changes:
            try:
                value = self.store.read_record(
                    change.namespace, change.key,
                    expected_record_schema=change.record_schema,
                )
            except KeyError:
                if change.delete:
                    continue
                return False
            if change.delete:
                return False
            if self.codec.encode(value) != self.codec.encode(change.value):
                return False
        return True

    def save(self):
        """Commit one legacy incremental save or one atomic cold generation."""
        self._ensure_active()
        if self._cold_mode:
            from .persistence_cold_save import save_cold
            return save_cold(self)
        if not self._dirty and not self._deleted and not self._manifest_dirty:
            return self.generation
        changes = self._changes()
        metadata = self._metadata()
        expected = self.generation
        try:
            generation = self.store.commit(expected, changes, (), metadata)
        except Exception:
            if self._acknowledged(changes, metadata, expected):
                generation = expected + 1
            else:
                raise
        self.generation = generation
        if self._manifest_dirty:
            self._manifest["collections"] = next(
                c.value for c in changes if c.namespace == META and c.key == COLLECTION_LAYOUT
            )
        self._dirty.clear()
        self._deleted.clear()
        self._manifest_dirty = False
        if self._identity_mode == "current":
            for target, owner in self._pending_identity_current.items():
                if owner is _MISSING:
                    self._committed_identity_targets.pop(target, None)
                else:
                    self._committed_identity_targets[target] = owner
            self._pending_identity_current.clear()
        elif self._pending_identity_patch is not None:
            self._identity_delta_next += 1
            self._has_identity_deltas = True
            self._pending_identity_patch = None
        self._identity_dirty = False
        self._identity_dirty_owners.clear()
        return generation

    def resolve_save(self):
        if not self._cold_mode:
            raise StoreError("resolve_save is only available for cold World sessions")
        from .persistence_cold_save import resolve_cold_save
        return resolve_cold_save(self)

    def detach(self, *, materialize_history=False):
        if not self._cold_mode:
            raise StoreError("detach is only available for cold World sessions")
        from .persistence_lifecycle import detach
        return detach(self, materialize_history=materialize_history)

    def verify_history(self):
        if not self._cold_mode:
            raise StoreError(
                "verify_history is only available for cold World sessions"
            )
        from .persistence_lifecycle import verify_history
        return verify_history(self)

    @property
    def cold_state(self):
        return self._cold_state

    def diagnostics(self):
        return self.store.diagnostics()

    def reset_diagnostics(self):
        self.store.reset_diagnostics()

    @property
    def dirty(self):
        return frozenset(self._dirty)

    @property
    def deleted(self):
        return frozenset(self._deleted)

    @property
    def changed_member_work(self):
        return self._changed_member_work

    def reset_changed_member_work(self):
        self._changed_member_work = 0

    def _clear_bindings(self):
        for ident in self._bound_ids:
            bound = _BINDINGS.get(ident)
            if bound is not None and bound.session is self:
                _BINDINGS.pop(ident, None)
        self._bound_ids.clear()

    def _unwrap_value(self, value, memo):
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes) or cls in (FrozenDict, FrozenList):
            return value
        ident = id(value)
        if ident in memo:
            return memo[ident]
        if cls is tuple:
            result = tuple(self._unwrap_value(v, memo) for v in value)
            memo[ident] = result
            return result
        if cls is frozenset:
            result = frozenset(self._unwrap_value(v, memo) for v in value)
            memo[ident] = result
            return result
        if isinstance(value, _RootRecordTable):
            result = RecordTable()
            memo[ident] = result
            for key, record in value.items():
                result[key] = self._unwrap_value(record, memo)
            return result
        if isinstance(value, (TrackedDict, _RootDict)):
            result = {}
            memo[ident] = result
            for key, child in value.items():
                result[self._unwrap_value(key, memo)] = self._unwrap_value(child, memo)
            return result
        if isinstance(value, (TrackedList, _RootList)):
            result = []
            memo[ident] = result
            result.extend(self._unwrap_value(v, memo) for v in value)
            return result
        if isinstance(value, (TrackedSet, _RootSet)):
            result = set()
            memo[ident] = result
            result.update(self._unwrap_value(v, memo) for v in value)
            return result
        if is_dataclass(value):
            memo[ident] = value
            declared = {field.name for field in fields(cls)}
            for field in fields(cls):
                child = getattr(value, field.name)
                replacement = self._unwrap_value(child, memo)
                if replacement is not child:
                    object.__setattr__(value, field.name, replacement)
            # P2A restores dataclasses from declared fields only. Mirror that
            # state on detach so stale query caches cannot affect continuation.
            for name in tuple(getattr(value, "__dict__", ())):
                if (
                    name not in declared
                    and not (cls is Event and name == "_sealed")
                    and name != "_ate_persistence_lifetime"
                ):
                    value.__dict__.pop(name, None)
            return value
        if isinstance(value, EventLog):
            memo[ident] = value
            if self._cold_mode:
                # Close teardown owns only the resident mutable tail.  Do not
                # consult the disk prefix here: direct store.close(), stale and
                # recovery-required sessions must still release bindings.
                events = (
                    event for event in value._tail
                    if event.__dict__.get("_sealed", False) is not True
                )
            else:
                events = iter(value)
            for event in events:
                self._unwrap_value(event, memo)
            return value
        return value

    def _unbind_world(self):
        memo = {}
        self._suspended += 1
        try:
            # Walk the entire declared World graph, not only root collections,
            # so non-field query caches are discarded exactly as P2A restore does.
            self._unwrap_value(self.world, memo)
        finally:
            self._suspended -= 1

    def close(self):
        if not self._active:
            return
        if self._cold_mode and self._cold_operation_depth:
            raise StoreError("cannot close during an active cold session operation")
        error = None
        try:
            self._unbind_world()
        except StoreError as exc:
            # A caller may have directly closed the owned store.  Cold close
            # must still be an idempotent resource-release operation; the
            # earlier mutation/read attempt already surfaced the closed-store
            # error, so teardown does not re-raise it.
            if not (self._cold_mode and getattr(self.store, "_closed", False)):
                error = exc
        except Exception as exc:
            error = exc
        finally:
            self._active = False
            current_prefix = (
                self.world.events._disk_prefix
                if self._cold_mode
                and isinstance(self.world.events, EventLog)
                else None
            )
            pending_old_prefix = (
                self._cold_old_prefix_pending if self._cold_mode else None
            )
            self._clear_bindings()
            if current_prefix is not None:
                current_prefix.close()
            if (
                pending_old_prefix is not None
                and pending_old_prefix is not current_prefix
            ):
                pending_old_prefix.close()
            self._cold_old_prefix_pending = None
            self._cold_plan = None
            self._cold_publication_phase = None
            if self._cold_mode:
                self._cold_state = "closed"
                if self._cold_lifetime is not None:
                    self._cold_lifetime.close()
            self._memo.clear()
            self._memo_reverse.clear()
            self._bound_root_originals.clear()
            self._bootstrap_originals.clear()
            self.store.close()
        if error is not None:
            raise error


def bind_snapshot(world, path, *, rules_id):
    """Bind a live World to an existing exact P2A snapshot."""
    probe = TransactionalStore.open(
        path,
        codec=WorldCodec(),
        expected_simulation_schema=SCHEMA,
        expected_rules_id=rules_id,
    )
    try:
        with probe.read_transaction():
            manifest = probe.read_record(
                META, "manifest", expected_record_schema=RECORD_SCHEMA
            )
            if (
                type(manifest) is dict
                and manifest.get("event_storage") is not None
            ):
                raise StoreFormatError(
                    "bind_snapshot does not accept cold event storage; "
                    "use open_world_session"
                )
    finally:
        probe.close()
    return IncrementalWorldSession(world, path, rules_id=rules_id)
