"""Private certificates for closed, short, read-only catalog operations.

Never place a gameplay callback or public iterator yield inside this context.
Borrowed transactions cannot mint certificates. A write permanently invalidates
the scope, including a write later rolled back to a savepoint.
"""
from collections import OrderedDict
from contextlib import contextmanager

from .persistence_lazy_budget import resident_bytes


def _immutable(value):
    return (value is None or type(value) in (bool, int, float, str, bytes)
            or type(value) in (tuple, frozenset) and all(_immutable(v) for v in value))


class OwnedOpenRead:
    """Authority issued only after the private opener starts its own BEGIN."""
    def __init__(self, store, pin):
        self.store, self.pin, self.db, self.codec = store, pin, store.db, store.codec
        self.changes = store.db.total_changes

    def matches(self, store, pin):
        return (store is self.store and pin == self.pin and store.db is self.db
                and store.codec is self.codec and self.db.in_transaction
                and store._active_read_transaction and self.db.total_changes == self.changes)


class ValidationScope:
    def __init__(self, store, pin, *, eligible, byte_limit):
        self.store, self.pin = store, pin
        self.db, self.codec = store.db, store.codec
        self.byte_limit = min(256*1024, byte_limit)
        self._cache = OrderedDict()
        self.bytes = 0
        self._valid = eligible
        self._epoch = self._current_epoch() if eligible else None
        self._native_custody = self._capture_native_custody() if eligible else None

    def _capture_native_custody(self):
        from .persistence_proof_world_session import _WorldProofAuthority
        from .persistence_sqlite_guard import GuardedConnection
        st, db = self.store, self.db
        authority = getattr(st, '_world_proof_authority', None)
        if (type(authority) is not _WorldProofAuthority or type(db) is not GuardedConnection
                or not authority.proof_only or not authority._opening_admitted
                or authority.busy or authority.uncertain or authority.epoch is None
                or authority.read_pin != self.pin or st._active_read_transaction
                or not getattr(st, '_checked_snapshot_owns_transaction', False)
                or db._sql_callback_generation != 0 or db.row_factory is not None
                or db.text_factory is not str or db._known_authorizer is not None
                or getattr(db, '_native_write_guard', None) is not None):
            return None
        return (authority, authority.pair, authority.epoch, authority.read_components,
                db._schema_statement_generation, db._transaction_generation)

    def native_epoch(self, store, authority):
        """Reuse entry checks only while the exact owned read view survives."""
        custody = self._native_custody
        if custody is None:return None
        db = self.db
        if (not self._valid or store is not self.store or store._closed
                or getattr(store, '_validation_scope', None) is not self
                or store.db is not db or store.codec is not self.codec
                or not db.in_transaction or store._active_read_transaction
                or not getattr(store, '_checked_snapshot_owns_transaction', False)
                or not getattr(store, '_checked_snapshot_depth', 0)
                or store._checked_snapshot_generation != self.pin.captured_head
                or db.total_changes != self._epoch[0]
                or store._phase_hook is not self._epoch[-1]
                or db._schema_statement_generation != custody[4]
                or db._transaction_generation != custody[5]
                or db._sql_callback_generation != 0 or db.row_factory is not None
                or db.text_factory is not str or db._known_authorizer is not None
                or db._callback_guard or getattr(db, '_native_sql_callback_depth', 0)
                or getattr(db, '_native_write_guard', None) is not None
                or authority is not custody[0]
                or getattr(store, '_world_proof_authority', None) is not authority
                or authority.store is not store or not authority.proof_only
                or not authority._opening_admitted or authority.busy or authority.uncertain
                or authority.read_pin != self.pin or authority.pair is not custody[1]
                or authority.epoch is not custody[2] or authority.read_components is not custody[3]):
            self.invalidate()
            return None
        return custody[2]

    @property
    def entries(self):
        return len(self._cache)

    def _current_epoch(self):
        return (self.db.total_changes,
                self.db.execute('PRAGMA data_version').fetchone()[0],
                self.db.execute('PRAGMA schema_version').fetchone()[0],
                self.store._phase_hook)

    def invalidate(self):
        self._valid = False
        self._cache.clear()
        self.bytes = 0

    def can_reuse(self, store, pin):
        if not self._valid:
            return False
        if self._native_custody is not None:
            if pin != self.pin:
                self.invalidate()
                return False
            return self.native_epoch(store, self._native_custody[0]) is not None
        if (store is not self.store or pin != self.pin or store._closed
                or store.db is not self.db or store.codec is not self.codec
                or not self.db.in_transaction or not getattr(store, '_checked_snapshot_depth', 0)
                or self._current_epoch() != self._epoch):
            self.invalidate()
            return False
        return True

    def lookup(self, kind, key):
        if not self.can_reuse(self.store, self.pin):
            return None
        marker = kind, key
        cached = self._cache.get(marker)
        if cached is None:
            return None
        self._cache.move_to_end(marker)
        return cached[0]

    def remember(self, kind, key, proof):
        if self.byte_limit <= 0:return
        if not self.can_reuse(self.store, self.pin) or not _immutable((key, proof)):
            return
        marker = kind, key
        size = resident_bytes((marker, proof)) + 128
        if size > self.byte_limit:
            return
        old = self._cache.pop(marker, None)
        if old is not None: self.bytes -= old[1]
        self._cache[marker] = proof, size
        self.bytes += size
        while self.entries > 256 or self.bytes > self.byte_limit:
            _, (_, weight) = self._cache.popitem(last=False)
            self.bytes -= weight


@contextmanager
def checked_read_operation(store, pin, *, byte_limit=256*1024):
    """Internal operations only; ordinary read_snapshot retains its contract."""
    store._ensure_open()
    previous = getattr(store, '_validation_scope', None)
    if previous is not None and previous.can_reuse(store, pin):
        yield previous
        return
    opener = getattr(store, '_owned_open_read', None)
    owned_open = opener is not None and opener.matches(store, pin)
    eligible = (not getattr(store, '_checked_snapshot_depth', 0)
                and (owned_open or not store.db.in_transaction and not store._active_read_transaction))
    with store.read_snapshot(pin):
        scope = ValidationScope(store, pin, eligible=eligible, byte_limit=byte_limit)
        store._validation_scope = scope
        try:
            yield scope
        finally:
            scope.invalidate()
            store._validation_scope = previous
