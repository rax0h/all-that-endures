"""Bounded evidence for topology-stable scalar edits, never object authority.

Canonical objects remain in the existing identity registry. Certificates retain
only weak object references and routes to existing session tables. They are
invalid outside the exact DB/pin/topology epoch that established those routes.
"""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
import weakref
import sys

from .persistence_lazy_budget import resident_bytes


def register_callbacks(classes):
    """Capture implementation functions once, before user hook replacement."""
    global _CALLBACKS, _SCALAR_CALLBACK, _PREFLIGHT, _SHARED, _NESTED_NAMESPACES
    global _VALUE_PREFLIGHTS, _CHANGE_PREFLIGHTS
    if '_CALLBACKS' in globals():
        raise RuntimeError('value-route callbacks are already registered')
    tables = tuple(classes[name] for name in (
        'LazyRecordTable', 'LazyAspirationTable', 'LazySkillTable', 'LazySoulTable',
        'LazyResourceTable', 'LazyMaterialLotTable', 'LazySocialEdgeTable',
        '_LazySimpleMaterialObjectTable', '_LazyInstitutionRecordTable', 'LazyScalarRecordTable'))
    _CALLBACKS = frozenset(table.changed for table in tables[:-1])
    _VALUE_PREFLIGHTS = frozenset(table.preflight_value for table in tables)
    _CHANGE_PREFLIGHTS = frozenset(table.preflight_change for table in tables)
    _SCALAR_CALLBACK = classes['LazyScalarRecordTable'].changed
    _PREFLIGHT = classes['LazyRecordTable'].preflight_shared_record
    _SHARED = classes['LazyRecordTable'].shared_record_changed
    _NESTED_NAMESPACES = frozenset(classes['NESTED_RECORD_FIELDS'])


def ordinary_table(table):
    # Deliberately closed callbacks. A custom/reentrant notifier retains the
    # existing path, including notifications installed between pre/post hooks.
    changed = getattr(table.changed, '__func__', None)
    if changed is not _SCALAR_CALLBACK and changed not in _CALLBACKS:
        return False
    if not ordinary_route_hooks(table):
        return False
    if changed is _SCALAR_CALLBACK:
        return table._namespace not in _NESTED_NAMESPACES
    return changed in _CALLBACKS


def eligible(table, obj, field, value):
    from .persistence_record_runtime import _identity_free_scalar
    from .persistence_schema import RECORD_FIELDS
    session = table._session
    bridge, recursive = session._identity_bridge, session._recursive_histories
    return (bridge is not None and not bridge._synchronizing and not recursive._synchronizing
            and field in RECORD_FIELDS.get(type(obj), ())
            and _identity_free_scalar(getattr(obj, field)) and _identity_free_scalar(value)
            and ordinary_table(table)
            and ordinary_route_hooks(table))


def ordinary_route_hooks(table):
    return (getattr(table.preflight_shared_record, '__func__', None) is _PREFLIGHT
            and getattr(table.shared_record_changed, '__func__', None) is _SHARED
            and getattr(table.preflight_value, '__func__', None) in _VALUE_PREFLIGHTS
            and getattr(table.preflight_change, '__func__', None) in _CHANGE_PREFLIGHTS)


@contextmanager
def value_notification(session, owner):
    bridge = session._identity_bridge
    previous = getattr(bridge, '_value_owner_notification', None)
    bridge._value_owner_notification = owner
    try:
        yield
    finally:
        bridge._value_owner_notification = previous


def _epoch(session):
    from .persistence_record_runtime import _assignment_epoch
    return (_assignment_epoch(session), session.store._phase_hook)


def _available(session):
    bridge, recursive, coord = session._identity_bridge, session._recursive_histories, session._identity_coordinator
    return (not session.store.db.in_transaction and coord._prepared is None
            and not coord._routing and not bridge._synchronizing and not recursive._synchronizing
            and not bridge._pending_owners and not recursive._pending_backings)


@dataclass(frozen=True)
class ValueRouteProof:
    subject: object
    epoch: tuple
    routes: tuple
    hooks: tuple


class ValueRouteCache:
    def __init__(self, coordinator):
        self.entry_limit = min(128, coordinator.occurrence_limit)
        self.byte_limit = min(64*1024, coordinator.byte_limit//8)
        self._entries = OrderedDict()
        self.bytes = self.hits = self.misses = 0

    @staticmethod
    def _hooks(routes):
        return tuple((table.changed, table.preflight_shared_record, table.shared_record_changed,
                      table.preflight_value, table.preflight_change)
                     for table,key in routes)

    def get(self, session, obj):
        session._ensure_people_mutation_allowed()
        session.store._require_pin(session.pin)
        row = self._entries.pop(id(obj), None)
        if row is not None:
            proof, size = row
            self.bytes -= size
            if (_available(session) and proof.subject() is obj and proof.epoch == _epoch(session)
                    and all(ordinary_table(table) for table,key in proof.routes)
                    and proof.hooks == self._hooks(proof.routes)):
                self._entries[id(obj)] = row
                self.bytes += size
                self.hits += 1
                return proof.routes
        self.misses += 1
        return None

    def remember(self, session, obj, routes):
        if not _available(session) or not all(ordinary_table(t) for t,k in routes):
            return
        proof = ValueRouteProof(weakref.ref(obj), _epoch(session), routes, self._hooks(routes))
        # Do not traverse the session-owned table dictionaries. Charge all
        # retained proof metadata plus conservative mapping/LRU overhead.
        size = (sys.getsizeof(proof)+sys.getsizeof(proof.__dict__)+128
                + resident_bytes((proof.subject,proof.epoch,proof.routes,proof.hooks),
                                 seen={id(table) for table,key in routes}))
        if size > self.byte_limit:
            return
        old = self._entries.pop(id(obj), None)
        if old is not None: self.bytes -= old[1]
        self._entries[id(obj)] = proof, size
        self.bytes += size
        while len(self._entries) > self.entry_limit or self.bytes > self.byte_limit:
            _, (_, weight) = self._entries.popitem(last=False)
            self.bytes -= weight

    def clear(self):
        self._entries.clear()
        self.bytes = 0

    def diagnostics(self):
        return dict(entries=len(self._entries), bytes=self.bytes, entry_limit=self.entry_limit,
                    byte_limit=self.byte_limit, hits=self.hits, misses=self.misses)
