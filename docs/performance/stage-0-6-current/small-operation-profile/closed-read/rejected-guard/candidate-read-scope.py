"""Snapshot facts for one closed, owned, read-only proof metadata operation."""
import sqlite3
import sys

from .incremental_store import StoreError, StoreConflictError
from .persistence_sqlite_guard import GuardedConnection, _WRITES, _READ_PRAGMAS, _ARGUMENT_PRAGMAS
from .persistence_validation_scope import ValidationScope
from .persistence_proof_projection import _require_closed_codec

_REGISTRIES = ('_record_by_name', '_record_by_type', '_enum_by_name', '_enum_by_type')


def eligible(store, authority, byte_limit):
    if (authority is None or not authority.proof_only or authority.busy or authority.uncertain
            or not authority._opening_admitted or type(store.db) is not GuardedConnection
            or getattr(store.db, '_native_write_guard', None) is not None
            or store.db._callback_guard or getattr(store.db, '_native_sql_callback_depth', 0)
            or byte_limit < 32768):
        return False
    try:
        _require_closed_codec(store)
    except StoreError:
        return False
    return all(type(getattr(store.codec, name, None)) is dict
               and len(getattr(store.codec, name)) <= 128 for name in _REGISTRIES)


class ClosedProofReadScope(ValidationScope):
    """No certificate survives this owned SQLite read view or a guard failure."""
    freeze_factories = True
    freeze_callbacks = True
    depth = 0

    def __init__(self, store, pin, authority, byte_limit):
        super().__init__(store, pin, eligible=False, byte_limit=byte_limit)
        self.authority = authority
        self.accepted_epoch, self.pair = authority.epoch, authority.pair
        self.components, self.read_pin = authority.read_components, authority.read_pin
        self.hook = store._phase_hook
        self.row_factory, self.text_factory = self.db.row_factory, self.db.text_factory
        self.active_read = store._active_read_transaction
        self.changes = self.db.total_changes
        self.registries = tuple((name, getattr(self.codec, name), dict(getattr(self.codec, name)))
                                for name in _REGISTRIES)
        # Copied hash tables own only references to the codec's existing types.
        # Reserve their measured shallow metadata and fixed guard bookkeeping
        # within the existing group transient budget, rather than adding a cache.
        self.metadata_bytes = 4096 + sum(sys.getsizeof(copy) for _, _, copy in self.registries)
        self.cache_limit = max(0, self.byte_limit - self.metadata_bytes)
        self.denied = None
        self.previous = self.db._known_authorizer
        if authority._epoch() != self.accepted_epoch:
            raise StoreConflictError('closed proof read lost its admitted entry epoch')
        self._valid = True

    def reject(self, reason):
        self.denied = reason
        self.invalidate()
        raise StoreError(reason)

    def activate(self):
        previous = self.previous
        def authorize(action, first, second, database, source):
            denied = action in _WRITES
            if action == sqlite3.SQLITE_PRAGMA:
                denied = ((first or '').lower() not in _READ_PRAGMAS
                          or second is not None and (first or '').lower() not in _ARGUMENT_PRAGMAS)
            if action == sqlite3.SQLITE_FUNCTION and (second or '').lower() == 'load_extension':
                denied = True
            if denied:
                self.denied = 'closed proof read cannot write or replace its snapshot'
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK if previous is None else self.db._invoke_sql_callback(
                previous, action, first, second, database, source)
        self.authorizer = authorize
        self.db._native_write_guard = self
        sqlite3.Connection.set_authorizer(self.db, authorize)
        self.db._known_authorizer = authorize

    def check(self):
        st, a = self.store, self.authority
        if (self.denied or not self._valid or st._closed or st.db is not self.db
                or st.codec is not self.codec or st._phase_hook is not self.hook
                or self.db.row_factory is not self.row_factory or self.db.text_factory is not self.text_factory
                or not self.db.in_transaction or self.db.total_changes != self.changes
                or not getattr(st, '_checked_snapshot_depth', 0)
                or getattr(st, '_checked_snapshot_generation', None) != self.pin.captured_head
                or st._active_read_transaction != self.active_read
                or self.db._native_write_guard is not self
                or self.db._known_authorizer is not self.authorizer
                or self.db._callback_guard or getattr(self.db, '_native_sql_callback_depth', 0)
                or getattr(st, '_world_proof_authority', None) is not a
                or not a.proof_only or a.busy or a.uncertain or not a._opening_admitted
                or a.epoch != self.accepted_epoch or a.pair is not self.pair
                or a.read_components is not self.components or a.read_pin != self.read_pin
                or self.read_pin != self.pin):
            self.reject(self.denied or 'closed proof read custody changed')
        try:
            _require_closed_codec(st)
            if any(getattr(self.codec, name, None) is not original or original != copy
                   for name, original, copy in self.registries):
                self.reject('closed proof codec registry changed')
        except StoreError:
            self.denied = self.denied or 'closed proof codec changed'
            self.invalidate()
            raise

    def after_callback(self):
        self.check()

    def can_reuse(self, store, pin):
        if not self._valid:
            if self.denied:
                raise StoreError(self.denied)
            return False
        self.check()
        if store is not self.store or pin != self.pin:
            self.invalidate()
            return False
        return True

    def epoch_for(self, authority):
        if authority is self.authority and self.can_reuse(self.store, self.pin):
            return self.accepted_epoch
        return None

    def remember(self, kind, key, proof):
        super().remember(kind, key, proof)
        while self.entries and self.bytes > self.cache_limit:
            _, (_, weight) = self._cache.popitem(last=False)
            self.bytes -= weight

    def release(self):
        self.invalidate()
        self.db._native_write_guard = None
        sqlite3.Connection.set_authorizer(self.db, self.previous)
        self.db._known_authorizer = self.previous
