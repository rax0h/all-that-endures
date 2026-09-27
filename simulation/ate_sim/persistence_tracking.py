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
    META, RECORD_SCHEMA, SCHEMA, WorldCodec, _audit, _roots, _kind,
    _restore_collection, _identity_groups,
)
from .persistence_schema import RECORD_FIELDS, ROOT_FIELDS, ROOT_TYPES


_BINDINGS = {}
_ORIGINAL_SETATTR = {}
_EVENTLOG_INSTALLED = False


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
                token = bound.before_assignment(self, name, value)
                if token is not None and token[0] in ("owned", "root_collection"):
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

    def append(log, event):
        original_append(log, event)
        bound = _binding(log)
        if bound is not None:
            bound.event_appended(log, event)

    def seal_before(log, year):
        before = len(log._chunks)
        original_seal(log, year)
        bound = _binding(log)
        if bound is not None and len(log._chunks) != before:
            bound.event_chunks_changed(log)

    EventLog.append = append
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
        wrapped = self.session._bind_nested(value, owners, initial=False)
        return ("owned", getattr(obj, name), owners, wrapped)

    def after_assignment(self, obj, name, value, token):
        if token is None or self.session._suspended:
            return
        if token[0] == "root_scalar":
            _, namespace, old = token
            if old != value:
                self.session._mark((namespace, 0))
            return
        if token[0] == "root_collection":
            self.session._finish_root_assignment(token)
            return
        _, old, owners, wrapped = token
        if old is not wrapped:
            self.session._detach(old, owners)
        self.session._mark_many(owners)

    def event_appended(self, log, event):
        self.session._event_appended(log, event)

    def event_chunks_changed(self, log):
        self.session._event_chunks_changed(log)


class _NestedMixin:
    _ate_tracked_kind = None

    def _setup(self, session, owners):
        self._session = session
        self._owners = set(owners)

    def _add_owners(self, owners):
        self._owners.update(owners)

    def _touch(self):
        self._session._ensure_active()
        if not self._session._suspended:
            self._session._mark_many(self._owners)

    def _bind(self, value):
        return self._session._bind_nested(value, self._owners, initial=False)

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
        value = self[index]
        result = list.pop(self, index)
        self._detach_value(value)
        self._touch()
        return result

    def remove(self, value):
        index = self.index(value)
        self.pop(index)

    def clear(self):
        old = list(self)
        list.clear(self)
        for value in old:
            self._detach_value(value)
        self._touch()

    def sort(self, *args, **kwargs):
        list.sort(self, *args, **kwargs)
        self._touch()

    def reverse(self):
        list.reverse(self)
        self._touch()

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n):
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
        before = len(self)
        set.add(self, value)
        if len(self) != before:
            self._touch()

    def discard(self, value):
        before = len(self)
        set.discard(self, value)
        if len(self) != before:
            self._touch()

    def remove(self, value):
        set.remove(self, value)
        self._touch()

    def pop(self):
        value = set.pop(self)
        self._touch()
        return value

    def clear(self):
        if self:
            set.clear(self)
            self._touch()

    def update(self, *others):
        before = set(self)
        set.update(self, *others)
        if self != before:
            self._touch()

    def intersection_update(self, *others):
        before = set(self)
        set.intersection_update(self, *others)
        if self != before:
            self._touch()

    def difference_update(self, *others):
        before = set(self)
        set.difference_update(self, *others)
        if self != before:
            self._touch()

    def symmetric_difference_update(self, other):
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

    def ordinal(self, key):
        return self._ordinals[key]

    def __setitem__(self, key, value):
        self._session._ensure_active()
        exists = key in self
        old = self.get(key)
        owner = (self._namespace, key)
        if exists and old is not value:
            self._session._detach(old, {owner})
        value = self._session._bind_nested(value, {owner}, initial=False)
        dict.__setitem__(self, key, value)
        if not exists:
            self._ordinals[key] = len(self._ordinals)
            self._session._manifest_dirty = True
        self._session._mark(owner)

    def __delitem__(self, key):
        self._session._ensure_active()
        owner = (self._namespace, key)
        old = self[key]
        self._session._detach(old, {owner})
        ordinal = self._ordinals.pop(key)
        dict.__delitem__(self, key)
        self._session._delete(owner)
        for other, old_ordinal in list(self._ordinals.items()):
            if old_ordinal > ordinal:
                self._ordinals[other] = old_ordinal - 1
                self._session._mark((self._namespace, other))
        self._session._manifest_dirty = True

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

    def _setup(self, session, namespace, ordinals):
        self._session = session
        self._namespace = namespace
        self._ordinals = dict(ordinals)

    def ordinal(self, key):
        return self._ordinals[key]

    def __setitem__(self, key, record):
        self._session._ensure_active()
        exists = key in self
        old = self.get(key)
        owner = (self._namespace, key)
        if exists and old is not record:
            self._session._detach(old, {owner})
        record = self._session._bind_nested(record, {owner}, initial=False)
        dict.__setitem__(self, key, record)
        if isinstance(record, IndexedRecord):
            record._index_table = weakref.ref(self)
            record._index_key = key
        self.changed(key)
        if not exists:
            self._ordinals[key] = len(self._ordinals)
            self._session._manifest_dirty = True
        self._session._mark(owner)

    def __delitem__(self, key):
        self._session._ensure_active()
        owner = (self._namespace, key)
        old = self[key]
        self._session._detach(old, {owner})
        ordinal = self._ordinals.pop(key)
        dict.__delitem__(self, key)
        self.changed(key)
        self._session._delete(owner)
        for other, old_ordinal in list(self._ordinals.items()):
            if old_ordinal > ordinal:
                self._ordinals[other] = old_ordinal - 1
                self._session._mark((self._namespace, other))
        self._session._manifest_dirty = True

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

    def _setup(self, session, namespace):
        self._session = session
        self._namespace = namespace

    def append(self, value):
        index = len(self)
        owner = (self._namespace, index)
        list.append(self, self._session._bind_nested(value, {owner}, initial=False))
        self._session._mark(owner)
        self._session._manifest_dirty = True

    def extend(self, values):
        for value in values:
            self.append(value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            self._replace_all_after(lambda: list.__setitem__(self, index, list(value)))
            return
        if index < 0:
            index += len(self)
        owner = (self._namespace, index)
        old = self[index]
        if old is not value:
            self._session._detach(old, {owner})
        list.__setitem__(self, index, self._session._bind_nested(value, {owner}, initial=False))
        self._session._mark(owner)

    def __delitem__(self, index):
        self._replace_all_after(lambda: list.__delitem__(self, index))

    def insert(self, index, value):
        self._replace_all_after(lambda: list.insert(self, index, value))

    def pop(self, index=-1):
        result = self[index]
        self._replace_all_after(lambda: list.pop(self, index))
        return result

    def remove(self, value):
        self.pop(self.index(value))

    def clear(self):
        self._replace_all_after(lambda: list.clear(self))

    def sort(self, *args, **kwargs):
        self._replace_all_after(lambda: list.sort(self, *args, **kwargs))

    def reverse(self):
        self._replace_all_after(lambda: list.reverse(self))

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, n):
        self._replace_all_after(lambda: list.__imul__(self, n))
        return self

    def _replace_all_after(self, operation):
        self._session._ensure_active()
        old = list(self)
        for i, value in enumerate(old):
            self._session._detach(value, {(self._namespace, i)})
        operation()
        raw = list(self)
        list.clear(self)
        for i, value in enumerate(raw):
            list.append(self, self._session._bind_nested(value, {(self._namespace, i)}, initial=False))
            self._session._mark((self._namespace, i))
        for i in range(len(self), len(old)):
            self._session._delete((self._namespace, i))
        self._session._manifest_dirty = True


class _RootSet(set):
    _ate_tracked_kind = "set"

    def _setup(self, session, namespace):
        self._session = session
        self._namespace = namespace

    def _mutate(self, operation):
        self._session._ensure_active()
        old = self._ordered()
        operation()
        new = self._ordered()
        for i in range(max(len(old), len(new))):
            if i >= len(new):
                self._session._delete((self._namespace, i))
            elif i >= len(old) or old[i] != new[i]:
                self._session._mark((self._namespace, i))
        if old != new:
            self._session._manifest_dirty = True

    def _ordered(self):
        return sorted(self, key=self._session.codec.encode)

    def add(self, value):
        self._mutate(lambda: set.add(self, value))

    def discard(self, value):
        self._mutate(lambda: set.discard(self, value))

    def remove(self, value):
        self._mutate(lambda: set.remove(self, value))

    def pop(self):
        box = []
        self._mutate(lambda: box.append(set.pop(self)))
        return box[0]

    def clear(self):
        self._mutate(lambda: set.clear(self))

    def update(self, *others):
        self._mutate(lambda: set.update(self, *others))

    def intersection_update(self, *others):
        self._mutate(lambda: set.intersection_update(self, *others))

    def difference_update(self, *others):
        self._mutate(lambda: set.difference_update(self, *others))

    def symmetric_difference_update(self, other):
        self._mutate(lambda: set.symmetric_difference_update(self, other))

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
    """Bind one live World to one P2A snapshot and persist dirty owners only."""

    def __init__(self, world, path, *, rules_id):
        if type(world) is not World:
            raise TypeError("expected World")
        _install_assignment_hooks()
        _install_eventlog_hooks()
        self.world = world
        self.codec = WorldCodec()
        self.store = TransactionalStore.open(
            path, codec=self.codec, expected_simulation_schema=SCHEMA,
            expected_rules_id=rules_id,
        )
        self.generation = self.store.generation
        self._dirty = set()
        self._deleted = set()
        self._manifest_dirty = False
        self._active = True
        self._suspended = 1
        self._bound_ids = set()
        self._memo = {}
        self._root_containers = {}
        self._scalar_fields = {}
        self._baseline_ordinals = {}
        self._identity_dirty = False
        self._changed_member_work = 0
        self._bootstrap_originals = {}
        try:
            with self.store.read_transaction():
                self.generation = self.store.generation
                self._manifest = self.store.read_record(
                    META, "manifest", expected_record_schema=RECORD_SCHEMA
                )
                if type(self._manifest) is not dict or self._manifest.get("schema") != SCHEMA:
                    raise StoreFormatError("incremental binding requires a P2A snapshot")
                self._initial_links = self._manifest.get("identity_links")
                if type(self._initial_links) is not list:
                    raise StoreFormatError("invalid identity manifest")
                self._validate_baseline()
                self._validate_bound_identity()
            self._normalize_bootstrap()
            self._bind_roots()
        except Exception:
            self._undo_bootstrap()
            self._clear_bindings()
            self.store.close()
            raise
        finally:
            self._suspended = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _ensure_active(self):
        if not self._active:
            raise StoreError("incremental World session is closed")

    def _is_mutable(self, value):
        return isinstance(value, _NestedMixin) or type(value) in (dict, list, set, RecordTable, EventLog) or _mutable_record(value)

    def _register_binding(self, value, binding):
        ident = id(value)
        existing = _BINDINGS.get(ident)
        if existing is not None and existing.session is not self:
            raise StoreError("object is already bound to another persistence session")
        _BINDINGS[ident] = binding
        self._bound_ids.add(ident)

    @staticmethod
    def _base_kind(kind):
        return {
            "dict-stable/v1": "dict",
            "RecordTable-stable/v1": "RecordTable",
            "set-stable/v1": "set",
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

    def _bind_roots(self):
        for root, obj in _roots(self.world):
            field_specs = {}
            for name, kind in ROOT_FIELDS[root].items():
                namespace = root + "." + name
                field_specs[name] = (namespace, kind)
                if kind == "state":
                    continue
                value = getattr(obj, name)
                if kind == "int":
                    self._scalar_fields[namespace] = (obj, name)
                    continue
                wrapped = self._bind_root_collection(namespace, value, kind)
                if wrapped is not value:
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
        kind, size, _chunks = description
        if len(value) != size:
            raise StoreIntegrityError(f"live World disagrees with snapshot size: {namespace}")
        if kind in ("dict", "RecordTable"):
            ordinals = {key: i for i, key in enumerate(value)}
            if kind == "RecordTable":
                wrapped = _RootRecordTable()
                wrapped._setup(self, namespace, ordinals)
                for key, record in value.items():
                    owner = (namespace, key)
                    record = self._bind_nested(record, {owner}, initial=True)
                    dict.__setitem__(wrapped, key, record)
                    if isinstance(record, IndexedRecord):
                        object.__setattr__(record, "_index_table", weakref.ref(wrapped))
                        object.__setattr__(record, "_index_key", key)
            else:
                wrapped = _RootDict()
                wrapped._setup(self, namespace, kind, ordinals)
                for key, item in value.items():
                    dict.__setitem__(
                        wrapped, key,
                        self._bind_nested(item, {(namespace, key)}, initial=True),
                    )
            self._root_containers[namespace] = wrapped
            return wrapped
        if kind == "list":
            wrapped = _RootList()
            wrapped._setup(self, namespace)
            for i, item in enumerate(value):
                list.append(wrapped, self._bind_nested(item, {(namespace, i)}, initial=True))
            self._root_containers[namespace] = wrapped
            return wrapped
        if kind == "set":
            wrapped = _RootSet(value)
            wrapped._setup(self, namespace)
            self._root_containers[namespace] = wrapped
            return wrapped
        if kind == "EventLog":
            if type(value) is not EventLog:
                raise StoreFormatError("bound event history must be EventLog")
            binding = _ObjectBinding(self)
            self._register_binding(value, binding)
            for i, event in enumerate(value):
                self._bind_nested(event, {(namespace, i)}, initial=True)
            self._root_containers[namespace] = value
            return value
        raise StoreFormatError(f"unsupported bound collection kind: {kind}")

    def _bind_nested(self, value, owners, *, initial):
        cls = type(value)
        if value is None or cls in (bool, int, float, str, bytes):
            return value
        if cls in (FrozenDict, FrozenList) or cls is tuple or cls is frozenset:
            # Immutable containers can contain mutable children only in tuples.
            if cls is tuple:
                rebuilt = tuple(self._bind_nested(v, owners, initial=initial) for v in value)
                return rebuilt
            return value
        if isinstance(value, _NestedMixin):
            new = set(owners) - value._owners
            if new and not initial:
                raise StoreError("mutation creates unsupported shared mutable ownership")
            value._add_owners(owners)
            return value
        existing = _binding(value)
        if existing is not None:
            if existing.session is not self:
                raise StoreError("cross-session mutable alias")
            new = set(owners) - existing.owners
            if new and not initial:
                raise StoreError("mutation creates unsupported shared mutable ownership")
            existing.add_owners(owners)
            return value
        if id(value) in self._memo:
            replacement = self._memo[id(value)]
            bound = _binding(replacement)
            if bound is not None:
                new = set(owners) - bound.owners
                if new and not initial:
                    raise StoreError("mutation creates unsupported shared mutable ownership")
                bound.add_owners(owners)
            elif hasattr(replacement, "_add_owners"):
                replacement._add_owners(owners)
            return replacement
        if _mutable_record(value):
            bound = _ObjectBinding(self, owners)
            self._register_binding(value, bound)
            self._memo[id(value)] = value
            for name in RECORD_FIELDS[type(value)]:
                child = getattr(value, name)
                replacement = self._bind_nested(child, owners, initial=initial)
                if replacement is not child:
                    object.__setattr__(value, name, replacement)
            return value
        if cls in (dict, RecordTable):
            wrapped = TrackedDict()
            wrapped._setup(self, owners)
            self._memo[id(value)] = wrapped
            for key, child in value.items():
                dict.__setitem__(wrapped, key, self._bind_nested(child, owners, initial=initial))
            return wrapped
        if cls is list:
            wrapped = TrackedList()
            wrapped._setup(self, owners)
            self._memo[id(value)] = wrapped
            for child in value:
                list.append(wrapped, self._bind_nested(child, owners, initial=initial))
            return wrapped
        if cls is set:
            wrapped = TrackedSet(value)
            wrapped._setup(self, owners)
            self._memo[id(value)] = wrapped
            return wrapped
        return value

    def _detach(self, value, owners):
        if self._suspended or not self._is_mutable(value):
            return
        bound = _binding(value)
        if bound is not None:
            if len(bound.owners) > len(set(bound.owners) - set(owners)):
                remaining = set(bound.owners) - set(owners)
                if bound.owners and remaining and len(bound.owners) > 1:
                    raise StoreError("mutation would alter established shared-mutable identity")
                bound.owners = remaining
            return
        if isinstance(value, _NestedMixin):
            remaining = set(value._owners) - set(owners)
            if value._owners and remaining and len(value._owners) > 1:
                raise StoreError("mutation would alter established shared-mutable identity")
            value._owners = remaining

    def _mark(self, owner):
        self._ensure_active()
        self._deleted.discard(owner)
        self._dirty.add(owner)

    def _mark_many(self, owners):
        for owner in owners:
            self._mark(owner)

    def _delete(self, owner):
        self._ensure_active()
        self._dirty.discard(owner)
        self._deleted.add(owner)

    def _event_appended(self, log, event):
        namespace = "world.events"
        index = len(log) - 1
        self._bind_nested(event, {(namespace, index)}, initial=False)
        self._mark((namespace, index))
        self._manifest_dirty = True

    def _event_chunks_changed(self, log):
        self._manifest_dirty = True

    def _validate_bound_identity(self):
        links = []
        _audit(self.world, (), {}, set(), links)
        if links != self._initial_links:
            raise StoreIntegrityError("live World identity does not match snapshot manifest")

    def _description(self, namespace):
        current = self._manifest["collections"][namespace]
        kind = current[0]
        value = self._root_containers.get(namespace)
        if value is None:
            return current
        chunks = len(value._chunks) if kind == "EventLog" else 0
        return (kind, len(value), chunks)

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
        kind = self._manifest["collections"][namespace][0]
        if kind in ("dict", "RecordTable"):
            return (container.ordinal(key), container[key])
        if kind in ("list", "EventLog"):
            return (key, container[key])
        if kind == "set":
            values = sorted(container, key=self.codec.encode)
            return (key, values[key])
        raise StoreFormatError(f"unsupported incremental namespace: {namespace}")

    def _metadata(self):
        return {
            "simulation_position": self.world.year,
            "seed": self.world.seed,
            "next_ids": {
                key: getattr(self.world, key)
                for key in ("next_person", "next_household", "next_settlement", "next_event")
            },
            "namespaces": tuple(self._manifest["collections"]) + (META,),
        }

    def _changes(self):
        changes = []
        for namespace, key in sorted(self._deleted, key=lambda x: (x[0], self.codec.encode(x[1]))):
            changes.append(RecordChange(namespace, key, delete=True))
        for namespace, key in sorted(self._dirty, key=lambda x: (x[0], self.codec.encode(x[1]))):
            envelope = self._plain(self._record_value(namespace, key))
            changes.append(RecordChange(namespace, key, envelope, record_schema=RECORD_SCHEMA))
        if self._manifest_dirty:
            manifest = {
                "schema": self._manifest["schema"],
                "collections": dict(self._manifest["collections"]),
                "identity_links": self._manifest["identity_links"],
            }
            for namespace in self._root_containers:
                manifest["collections"][namespace] = self._description(namespace)
            changes.append(RecordChange(META, "manifest", self._plain(manifest), record_schema=RECORD_SCHEMA))
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
        """Commit only journaled owners. Dirty state clears after confirmed commit."""
        self._ensure_active()
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
            self._manifest = next(c.value for c in changes if c.namespace == META and c.key == "manifest")
        self._dirty.clear()
        self._deleted.clear()
        self._manifest_dirty = False
        return generation

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
                if name not in declared and not (cls is Event and name == "_sealed"):
                    value.__dict__.pop(name, None)
            return value
        if isinstance(value, EventLog):
            memo[ident] = value
            for event in value:
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
        self._unbind_world()
        self._active = False
        self._clear_bindings()
        self.store.close()


def bind_snapshot(world, path, *, rules_id):
    """Bind a live World to an existing exact P2A snapshot."""
    return IncrementalWorldSession(world, path, rules_id=rules_id)
