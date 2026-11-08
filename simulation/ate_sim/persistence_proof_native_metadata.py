"""Admitted public head snapshots and cached immutable-prefix context checks."""
from contextlib import contextmanager
import sqlite3

from .incremental_store import StoreError,StoreConflictError
from .persistence_sqlite_guard import require_persistent_sources
from . import persistence_proof_native_sources as sources


def _binding(store,authority,pin,epoch,pair):
    require_persistent_sources(store.db)
    if authority.epoch!=epoch or authority.read_pin!=pin or authority.pair!=pair:
        raise StoreConflictError('native metadata lost original accepted context')
    if sources.active(store) is not authority:
        raise StoreConflictError('native metadata entered publisher context')
    sources.before_snapshot(store,authority,pin)


def _context(store,authority,pin,epoch,pair):
    if not store.db.in_transaction:raise StoreConflictError('native metadata lost original snapshot')
    _binding(store,authority,pin,epoch,pair)


@contextmanager
def codec_guard(store):
    try:
        with store.db.readonly_callback():yield
    except sqlite3.Error as exc:
        raise StoreError('native metadata codec cannot replace or write its snapshot') from exc


def _transaction(store):
    if (store.db.in_transaction and not store._active_read_transaction
            and not getattr(store,'_checked_snapshot_depth',0)):
        raise StoreError('native metadata cannot borrow an arbitrary transaction')


@contextmanager
def head_row(store,authority):
    require_persistent_sources(store.db)
    _transaction(store)
    pin,epoch,pair=authority.read_pin,authority.epoch,authority.pair
    borrowed=store.db.in_transaction
    with sources._snapshot(store,authority,pin=pin) as manifest:
        require_persistent_sources(store.db)
        row=store._checked_head_row(expected_manifest=manifest)
        _context(store,authority,pin,epoch,pair)
        with codec_guard(store):yield row
        _context(store,authority,pin,epoch,pair)
    # ROLLBACK/transaction release can invoke SQLite trace callbacks too.
    _binding(store,authority,pin,epoch,pair)
    if store.db.in_transaction!=borrowed:
        raise StoreConflictError('native metadata cleanup changed transaction ownership')


def prefix_guard(store,*,binding=None):
    authority=sources.active(store)
    if authority is None:
        if binding is not None:raise StoreConflictError('native prefix lost original source authority')
        return None
    # No cached body is fetched. The exact original store, current admitted
    # pin/epoch and persistent source context authorize reuse of its immutable
    # prefix cache, while the existing reader still enforces captured bounds.
    require_persistent_sources(store.db)
    _transaction(store)
    expected=(authority,authority.read_pin,authority.epoch,authority.pair) if binding is None else binding
    if expected[0] is not authority:raise StoreConflictError('native prefix authority changed')
    _,pin,epoch,pair=expected
    _binding(store,authority,pin,epoch,pair)
    store._require_pin(pin)
    _binding(store,authority,pin,epoch,pair)
    return expected
