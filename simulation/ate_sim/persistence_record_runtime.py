"""Native record bindings borrow the existing registry and World publisher.

The binding is private backing metadata, never a registered canonical object.
Only actual dirty record bodies are retained strongly; clean native records are
weakly held by the existing assignment-binding table and incarnation registry.
"""
import weakref

from .incremental_store import StoreError, StoreIntegrityError
from .persistence_lazy_store import VersionChange
from .persistence_record_headers import (
    RecordReference, NAMESPACE, record_header, checked_record_header,
)


def mutable_record(value):
    from .persistence_schema import RECORD_FIELDS
    return type(value) in RECORD_FIELDS and not type(value).__dataclass_params__.frozen


def record_backing(value):
    from .persistence_tracking import _binding
    bound = _binding(value)
    return getattr(bound, '_record_backing', None)


def backing_for(value, registry=None):
    if registry is not None and type(value) is float:
        import math
        if math.isnan(value):
            backing = registry.nonreflexive_root_for(value).backing
            if backing is None:
                raise StoreIntegrityError('native NaN lacks checked backing metadata')
            return backing
    return record_backing(value) or value


def canonical_for(backing):
    from .persistence_nonreflexive_keys import NonreflexiveKeyBacking
    return backing.canonical() if type(backing) in (RecordBacking, NonreflexiveKeyBacking) else backing


class RecordBacking:
    _kind = 'record'

    def __init__(self, runtime, record, incarnation, header, *, new):
        session = runtime.session()
        self._runtime = runtime
        self._store, self._pin = session.store, session.pin
        self._incarnation, self._new = incarnation.value, new
        self._record_ref = weakref.ref(record)
        self._dirty_record = record if new else None
        self._header = header
        self._base_bytes = None if new else self._store.codec.encode(header)
        self._recursive_pending_children = {}

    def canonical(self):
        result = self._record_ref()
        if result is None:
            raise StoreIntegrityError('record backing lost its native canonical object')
        return result

    def _ensure(self):
        session = self._runtime.session()
        if session.store is not self._store or session.pin != self._pin:
            raise StoreError('record backing has a different publisher lease')
        self._store._require_pin(self._pin)

    def storage_reference(self):
        self._ensure()
        return RecordReference(self._incarnation)

    def has_pending_overlay(self):
        return self._new or self._store.codec.encode(self._header) != self._base_bytes

    def pending_changes(self):
        if not self.has_pending_overlay():
            return ()
        return (VersionChange(NAMESPACE, (self._incarnation, 0), self._header),)

    def _clear_cache(self):
        # No clean payload cache: the fixed native body is the caller's alias.
        pass

    def accept_save(self, pin):
        self._pin = pin
        self._new = False
        self._base_bytes = self._store.codec.encode(self._header)
        self._dirty_record = None

    def changed(self):
        session = self._runtime.session()
        self._dirty_record = self.canonical()
        self._runtime.retain_pending_children(self)
        # Register actual D, including a private unowned alias. Preparation
        # selects owning payloads; private edits never resurrect an old owner.
        session._nested_dirty[self._incarnation] = self


class RecordBinding:
    """Extend the existing native assignment binding, preserving eager owners."""
    def __init__(self, runtime, record, backing, previous=None):
        tracker = runtime.session()._eager_tracker
        if previous is not None and previous.session is not tracker:
            raise StoreError('cross-session native record')
        self._tracker_ref = weakref.ref(tracker)
        self._record_backing = backing
        self.owners = set(() if previous is None else previous.owners)
        self.root_fields = None if previous is None else previous.root_fields
        self._closed = False
        ident = id(record)
        def collected(ref):
            from .persistence_tracking import _BINDINGS
            if _BINDINGS.get(ident) is self and self._record_ref is ref:
                _BINDINGS.pop(ident, None)
            tracker = self._tracker_ref()
            if tracker is not None:
                tracker._bound_ids.discard(ident)
        self._record_ref = weakref.ref(record, collected)

    @property
    def session(self):
        tracker = self._tracker_ref()
        if self._closed or tracker is None:
            raise StoreError('native record session is closed')
        return tracker

    def close(self):
        self._closed = True
        self._record_backing._dirty_record = None
        self._record_backing._recursive_pending_children.clear()
        self._record_backing = None
        self.owners.clear()
        self.root_fields = None

    def add_owners(self, owners):
        self.owners.update(owners)

    def before_assignment(self, obj, name, value):
        from .persistence_adapters import _check_record, CACHES
        from .persistence_schema import RECORD_FIELDS
        from .core import Event
        tracker = self.session
        if tracker._suspended:
            return None
        _check_record(obj)
        if type(obj) is Event and vars(obj).get('_sealed', False):
            raise TypeError('sealed historical events are immutable; append a new cause')
        if type(obj) is Event and name == '_sealed':
            if type(value) is not bool:
                raise TypeError('Event seal state must be a boolean')
            self._record_backing._ensure()
            return 'event-state', name, value, value
        if name not in RECORD_FIELDS[type(obj)]:
            from .record_index import IndexedRecord
            if name in CACHES.get(type(obj), ()) or (
                    isinstance(obj, IndexedRecord) and name in ('_index_table', '_index_key')):
                return None
            raise TypeError('native record assignment has an undeclared field')
        backing = self._record_backing
        backing._ensure()
        runtime = backing._runtime
        runtime.validate_native(value)
        runtime.check_assignment_cycle(obj, value)
        runtime.session()._shared_object_routes(obj)
        stored = runtime._admit_validated(value)
        assigned = runtime.admitted_value(stored)
        return 'owned', name, stored, assigned

    def after_assignment(self, obj, name, value, token):
        if token is None or self.session._suspended:
            return
        from .persistence_schema import RECORD_FIELDS
        backing = self._record_backing
        fields = list(backing._header[2])
        if token[0] != 'event-state':
            fields[RECORD_FIELDS[type(obj)].index(name)] = token[2]
        backing._header = record_header(obj, values=tuple(fields))
        backing.changed()
        backing._runtime.invalidate_advancement_ancestors(obj)
        session = backing._runtime.session()
        for table, key in session._shared_object_routes(obj):
            table.changed(key)
        self.session._mark_many(session._nested_eager_owners(obj))

    def event_sealed(self, event):
        self.session._event_sealed(event)


def bind_record(runtime, record, incarnation, header, *, new):
    from .persistence_tracking import _binding, _install_assignment_hooks
    previous = _binding(record)
    backing = getattr(previous, '_record_backing', None)
    if backing is not None:
        backing._ensure()
        if backing._incarnation != incarnation.value:
            raise StoreIntegrityError('native record has another backing incarnation')
        return backing
    checked_record_header(header)
    _install_assignment_hooks()
    backing = RecordBacking(runtime, record, incarnation, header, new=new)
    binding = RecordBinding(runtime, record, backing, previous)
    runtime.session()._eager_tracker._register_binding(record, binding)
    return backing
