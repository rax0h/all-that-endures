"""Checked backing dependencies published by the existing hybrid transaction.

A dependency borrows the World publisher's token; it creates no older snapshot
pin. An unowned backing must remain immutable in World authority while its
canonical proxy keeps a private overlay. Retirement must consult this authority
before deleting that backing. World borrows this participant only in its explicit
checked-catalog mode; ordinary legacy open and complete-format migration remain
separate activation boundaries.

One mandatory row per backing contains at most MAX_PINS publisher tokens.
Released tokens are pruned on subsequent edits, avoiding one immortal row per
alias visit. Complete-format conversion must create empty rows for all existing
backings; absence is then corruption, not an empty dependency set.
"""
import weakref

from .incremental_store import StoreConflictError, StoreIntegrityError, StoreError
from .persistence_lazy_store import VersionChange, MAX_PINS
from .persistence_lazy_families import ParticipantDelta
from .persistence_lazy_budget import resident_bytes
from .persistence_lazy_nested_history import HISTORY_TYPES

NAMESPACE = 'aux.lazy.history.dependencies'
TAG = 'history-backing-dependencies/v1'
KINDS = ('list', 'map', 'set', 'sequence')


def dependency_value(kind, tokens=()):
    tokens = tuple(sorted(set(tokens)))
    if kind not in KINDS or len(tokens) > MAX_PINS or any(type(t) is not str or not t for t in tokens):
        raise ValueError('invalid backing dependency roster')
    return TAG, kind, tokens


def _checked_value(store, pin, incarnation, *, required=True):
    if type(incarnation) is not int or incarnation < 1:
        raise ValueError('invalid backing incarnation')
    try:
        value = store.read_version(pin, NAMESPACE, incarnation, expected_record_schema=1).value
    except KeyError as exc:
        if not required:
            return None
        raise StoreIntegrityError('mandatory backing dependency authority is absent') from exc
    if (type(value) is not tuple or len(value) != 3 or value[0] != TAG
            or value[1] not in KINDS or type(value[2]) is not tuple
            or len(value[2]) > MAX_PINS
            or any(type(t) is not str or not t for t in value[2])
            or tuple(sorted(set(value[2]))) != value[2]):
        raise StoreIntegrityError('invalid backing dependency authority')
    return value


def _active_tokens(store, tokens):
    active = []
    for token in tokens:
        try:
            _uuid, generation, _checksum = store._checked_pin_row(token)
        except StoreConflictError:
            continue  # Checked absence: final pin release invalidates the lease.
        if generation < 0 or generation > int(store._checked_head_row()[0]):
            raise StoreIntegrityError('backing dependency publisher generation is invalid')
        active.append(token)
    return tuple(active)


def active_backing_dependencies(store, pin, incarnation):
    with store.read_snapshot(pin):
        return _active_tokens(store, _checked_value(store, pin, incarnation)[2])


def expired_backing_dependency_changes(store, pin, incarnation):
    """Bounded pruning only; the retirement queue deletes the final empty row."""
    with store.read_snapshot(pin):
        value = _checked_value(store, pin, incarnation)
        active = _active_tokens(store, value[2])
        return (() if active == value[2] else
                (VersionChange(NAMESPACE, incarnation, dependency_value(value[1], active)),))


class BackingDependencyPool:
    def __init__(self, store, pin):
        store._require_pin(pin)
        self.store, self.pin, self.token = store, pin, pin.token
        self._aliases = {}
        self._persisted = {}
        self._new = set()
        self._prepared = None
        self._prepared_target = None
        self.closed = False

    def acquire(self, alias):
        if self.closed:
            raise StoreError('backing dependency pool is closed')
        if self._prepared is not None:
            raise StoreConflictError('backing dependencies have a frozen save plan')
        if (type(alias) not in HISTORY_TYPES or alias._store is not self.store
                or alias._pin != self.pin):
            raise StoreConflictError('backing dependency has a different publisher lease')
        incarnation, kind = alias._incarnation, alias._kind
        previous = self._aliases.get(incarnation)
        if previous is not None:
            if previous[0]() is not alias or previous[1] != kind:
                raise StoreIntegrityError('backing dependency has a different canonical proxy')
            return
        pool_ref = weakref.ref(self)
        def collected(ref):
            pool = pool_ref()
            if pool is not None:
                row = pool._aliases.get(incarnation)
                if row is not None and row[0] is ref:
                    del pool._aliases[incarnation]
                    if incarnation not in pool._persisted and (
                            pool._prepared_target is None or incarnation not in pool._prepared_target):
                        pool._new.discard(incarnation)
        self._aliases[incarnation] = weakref.ref(alias, collected), kind
        if alias._new:
            self._new.add(incarnation)

    def protected_incarnations(self):
        return tuple(self._aliases)

    def prepare_delta(self):
        if self.closed:
            raise StoreError('backing dependency pool is closed')
        if self._prepared is not None:
            return self._prepared
        target = {inc: row[1] for inc, row in self._aliases.items()}
        changes = []
        with self.store.read_snapshot(self.pin):
            for inc in sorted(set(target) ^ set(self._persisted)):
                kind = target.get(inc, self._persisted.get(inc))
                previous = _checked_value(self.store, self.pin, inc, required=inc not in self._new)
                if previous is not None and previous[1] != kind:
                    raise StoreIntegrityError('backing dependency kind disagrees with canonical proxy')
                tokens = set(() if previous is None else _active_tokens(self.store, previous[2]))
                if inc in target:
                    tokens.add(self.token)
                else:
                    if previous is None or self.token not in previous[2]:
                        raise StoreIntegrityError('published backing dependency disappeared')
                    tokens.discard(self.token)
                value = dependency_value(kind, tokens)
                if value != previous:
                    changes.append(VersionChange(NAMESPACE, inc, value))
        self._prepared_target = target
        self._prepared = ParticipantDelta.freeze(self.store.codec, 'history-dependencies',
                                                 version_changes=changes)
        return self._prepared

    def _check_plan(self, delta, pin):
        if self.closed or delta is not self._prepared:
            raise StoreConflictError('backing dependency acknowledgement has a different frozen plan')
        if (pin.token != self.token or pin.store_identity != self.store.store_identity
                or pin.captured_head not in (self.pin.captured_head, self.pin.captured_head + 1)
                or (delta.version_bytes and pin.captured_head != self.pin.captured_head + 1)):
            raise StoreConflictError('backing dependency acknowledgement has a different publisher lease')
        self.store._require_pin(pin)

    def validate_publication(self, delta, pin):
        self._check_plan(delta, pin)
        with self.store.read_snapshot(pin):
            for change in delta.decode(self.store.codec)[0]:
                if _checked_value(self.store, pin, change.key) != change.value:
                    raise StoreIntegrityError('backing dependency publication disagrees with frozen plan')

    def accept_delta(self, delta, pin):
        self.validate_publication(delta, pin)
        self.pin = pin
        self._persisted = self._prepared_target
        self._prepared = self._prepared_target = None
        self._new.difference_update(self._persisted)

    def abort_delta(self):
        # Only the central receipt/recovery authority may authorize this call.
        self._prepared = self._prepared_target = None
        self._new.intersection_update(self._aliases)

    def close(self, *, abandon_stale=False):
        if self.closed:
            return
        if self._prepared is not None:
            if not abandon_stale:
                raise StoreConflictError('backing dependencies have a frozen save plan')
            with self.store.read_snapshot(self.pin):
                if int(self.store._checked_head_row()[0]) <= self.pin.captured_head:
                    raise StoreConflictError('cannot abandon a current frozen dependency plan')
        # The existing publisher release is the final fallible boundary. On a
        # failed release, all dependency/proxy metadata remains usable.
        self.store.release_pin(self.pin)
        self.closed = True
        self._aliases.clear()
        self._persisted.clear()
        self._new.clear()
        # This is permanent lease invalidation, never a thaw for retry. Native
        # release rejects pending/committed attempts and an advanced own token.
        self._prepared = self._prepared_target = None

    def diagnostics(self):
        return {'dependencies': len(self._aliases), 'published_dependencies': len(self._persisted),
                'metadata_python_bytes': resident_bytes((self._aliases, self._persisted, self._new))}
