"""Verified ordered transitions with disposable caller-transaction SQL staging."""
from contextlib import closing, contextmanager
from dataclasses import dataclass
from itertools import chain
import sqlite3
import sys
import uuid

from .incremental_store import StoreError, StoreIntegrityError
from .persistence_proof_batch import update_sorted
from .persistence_proof_nodes import MAX_COUNT, key_locator
from .persistence_proof_order import (
    OrderEntry, OrderRoot, entry_commitment, _check_entry, _check_root,
)


@dataclass(frozen=True)
class OrderEdit:
    key: bytes
    value: bytes | None
    old: OrderEntry | None
    previous: OrderEntry | None
    following: OrderEntry | None


def _transaction(db):
    if not db.in_transaction:
        raise StoreError('ordered proof staging requires a caller transaction')


def _pair(key, value, *, deletion=False):
    if (type(key) is not bytes or not (deletion and value is None)
            and (type(value) is not bytes or len(value) != 32)):
        raise StoreIntegrityError('invalid ordered proof change')


@contextmanager
def _tables(db, schemas):
    names = []
    try:
        for schema in schemas:
            name = 'ate_order_' + uuid.uuid4().hex
            db.execute(f'CREATE TEMP TABLE {name} ({schema}) WITHOUT ROWID')
            names.append(name)
        yield names
    finally:
        failing = sys.exc_info()[0] is not None
        for name in reversed(names):
            try:
                db.execute(f'DROP TABLE IF EXISTS {name}')
            except sqlite3.Error:
                # A closed/failed connection must not hide the original
                # callback/SQL error. This is cleanup, never proof fallback.
                if not failing:
                    raise


def _write_delta(proof_map, db, table, key, commitment):
    db.execute(f'INSERT INTO {table} VALUES(?,?,?)',
               (key_locator(proof_map.map_domain, key), key, commitment))


def _apply(proof_map, db, table, parent):
    with closing(db.execute(f'SELECT key,value FROM {table} ORDER BY locator')) as rows:
        return update_sorted(proof_map, parent, rows)


_DELTA = 'locator BLOB PRIMARY KEY, key BLOB NOT NULL, value BLOB'


def build_ordered(proof_map, db, rows):
    """Construct from a fully checked, strictly ordered source stream."""
    _transaction(db)
    source = iter(rows); previous_input = None; end = object()

    def take():
        nonlocal previous_input
        item = next(source, end)
        if item is end:
            return None
        if type(item) not in (tuple, list) or len(item) != 2:
            raise StoreIntegrityError('invalid ordered source row')
        key, value = item
        _pair(key, value)
        if previous_input is not None and key <= previous_input:
            raise StoreIntegrityError('ordered source keys must be strictly increasing')
        previous_input = key
        return key, value

    with _tables(db, [_DELTA]) as (delta,):
        current = take(); first = current[0] if current is not None else None
        previous = last = None; count = 0
        while current is not None:
            following = take()
            key, value = current
            entry = OrderEntry(key, value, previous, following[0] if following is not None else None)
            _write_delta(proof_map, db, delta, key, entry_commitment(proof_map.map_domain, entry))
            previous = last = key; count += 1; current = following
        index = _apply(proof_map, db, delta, proof_map.empty)
        if index.count != count:
            raise StoreIntegrityError('ordered construction count disagreement')
        return OrderRoot(index, first, last)


def update_ordered(proof_map, db, root, expected_commitment, edits):
    """Authenticate parent-local witnesses and publish no authority itself."""
    _transaction(db); _check_root(proof_map, root, expected_commitment)
    source = iter(edits)
    sentinel = object(); first_edit = next(source, sentinel)
    if first_edit is sentinel:
        return root
    schemas = [
        'key BLOB PRIMARY KEY, value BLOB, prev BLOB, nxt BLOB, '
        'actual INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0',
        'key BLOB PRIMARY KEY, value BLOB', _DELTA,
    ]
    with _tables(db, schemas) as (parent, changes, delta):
        def ghost(key):
            if key is not None:
                db.execute(f'INSERT OR IGNORE INTO {parent}(key) VALUES(?)', (key,))

        ghost(root.first); ghost(root.last)

        def remember(entry):
            # Validate shape before selecting with an untrusted key. Reuse
            # exact parent preimages only inside this staging transaction.
            entry_commitment(proof_map.map_domain, entry)
            found = db.execute(f'SELECT value,prev,nxt,actual FROM {parent} WHERE key=?', (entry.key,)).fetchone()
            fields = entry.value, entry.previous, entry.following
            if found is not None and found[3]:
                if found[:3] != fields:
                    raise StoreIntegrityError('inconsistent ordered parent witness')
                return
            _check_entry(proof_map, root, entry)
            ghost(entry.key); ghost(entry.previous); ghost(entry.following)
            db.execute(f'UPDATE {parent} SET value=?,prev=?,nxt=?,actual=1 WHERE key=?', (*fields, entry.key))

        expected_count = root.index.count; previous_key = None
        for edit in chain((first_edit,), source):
            if type(edit) is not OrderEdit:
                raise StoreIntegrityError('invalid ordered edit')
            _pair(edit.key, edit.value, deletion=True)
            if previous_key is not None and edit.key <= previous_key:
                raise StoreIntegrityError('ordered edits must be strictly increasing')
            previous_key = edit.key
            left, right = edit.previous, edit.following
            if edit.old is not None:
                remember(edit.old)
                if edit.old.key != edit.key:
                    raise StoreIntegrityError('ordered old witness key disagreement')
                for neighbor, wanted in ((left, edit.old.previous), (right, edit.old.following)):
                    if neighbor is None:
                        if wanted is not None:
                            raise StoreIntegrityError('missing ordered parent neighbor')
                    else:
                        remember(neighbor)
                        if neighbor.key != wanted:
                            raise StoreIntegrityError('wrong ordered parent neighbor')
                if (left is not None and left.following != edit.key
                        or right is not None and right.previous != edit.key):
                    raise StoreIntegrityError('ordered parent links are not reciprocal')
                if edit.value is None:
                    expected_count -= 1
            else:
                if proof_map.get(root.index, edit.key) is not None:
                    raise StoreIntegrityError('ordered insertion/deletion absence disagreement')
                if edit.value is None:
                    if left is not None or right is not None:
                        raise StoreIntegrityError('surplus absent-deletion witness')
                else:
                    if left is not None:
                        remember(left)
                    if right is not None:
                        remember(right)
                    if (left is None and (right.key if right is not None else None) != root.first
                            or right is None and (left.key if left is not None else None) != root.last
                            or left is not None and (left.key >= edit.key or left.following != (right.key if right is not None else None))
                            or right is not None and (right.key <= edit.key or right.previous != (left.key if left is not None else None))):
                        raise StoreIntegrityError('unproven ordered insertion gap')
                    ghost(edit.key); expected_count += 1
            db.execute(f'INSERT INTO {changes} VALUES(?,?)', (edit.key, edit.value))
        if not 0 <= expected_count <= MAX_COUNT:
            raise StoreIntegrityError('ordered transition count overflow')
        db.execute(f'UPDATE {parent} SET value=(SELECT value FROM {changes} c WHERE c.key={parent}.key), '
                   f'deleted=(SELECT value IS NULL FROM {changes} c WHERE c.key={parent}.key), '
                   f'actual=CASE WHEN actual=0 THEN 2 ELSE actual END '
                   f'WHERE key IN (SELECT key FROM {changes})')
        # Ghost keys preserve the unmodified outer boundary of each disjoint
        # affected interval. Only authenticated/new entries become leaves.
        query = (f'SELECT key,value,actual,LAG(key) OVER (ORDER BY key),LEAD(key) OVER (ORDER BY key) '
                 f'FROM {parent} WHERE deleted=0 ORDER BY key')
        with closing(db.execute(query)) as rows:
            for key, value, actual, previous, following in rows:
                if actual:
                    entry = OrderEntry(key, value, previous, following)
                    _write_delta(proof_map, db, delta, key, entry_commitment(proof_map.map_domain, entry))
        with closing(db.execute(f'SELECT key FROM {changes} WHERE value IS NULL')) as rows:
            for key, in rows:
                _write_delta(proof_map, db, delta, key, None)
        first, last = db.execute(f'SELECT min(key),max(key) FROM {parent} WHERE deleted=0').fetchone()
        index = _apply(proof_map, db, delta, root.index)
        result = OrderRoot(index, first, last)
        if index.count != expected_count or (not expected_count and (first is not None or last is not None)):
            raise StoreIntegrityError('ordered transition count/boundary disagreement')
        return root if result == root else result
