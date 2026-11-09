"""Full construction audits with disk inventories and sorted row streams.

Only explicit offline conversion selects this implementation. Every payload and
checksum is still read; no proof or predecessor audit is assumed valid.
"""
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from itertools import zip_longest
import tempfile

from .incremental_store import StoreIntegrityError, _framed_sha


_ORDER_WORKSPACE = ContextVar('ate_construction_order_workspace', default=None)


@contextmanager
def construction_spills(workspace):
    token = _ORDER_WORKSPACE.set(workspace)
    try:
        yield
    finally:
        _ORDER_WORKSPACE.reset(token)


def ordered_memberships(store, pin, namespace, index, value):
    """Checked ordered projection; reuse one private spool across tiny histories."""
    import sqlite3
    from .persistence_conversion_workspace import ConversionWorkspace
    shared = _ORDER_WORKSPACE.get()
    with (nullcontext(shared) if shared is not None else ConversionWorkspace(store.codec,directory=None)) as workspace:
        workspace._stream += 1
        stream = workspace._stream
        workspace.db.execute('CREATE TABLE IF NOT EXISTS membership_order('
            'stream INTEGER,ordinal INTEGER,key BLOB,checksum TEXT,PRIMARY KEY(stream,ordinal)) WITHOUT ROWID')
        count = root = 0
        cursor = None
        try:
            for key, ordinal in store.iter_query_memberships(pin, namespace, index, value):
                encoded = store.codec.encode(key)
                checksum = _framed_sha(b'construction-order/v1',str(ordinal).encode(),encoded)
                try:
                    workspace.db.execute('INSERT INTO membership_order VALUES (?,?,?,?)', (stream,ordinal,encoded,checksum))
                except sqlite3.IntegrityError as exc:
                    raise StoreIntegrityError('duplicate construction membership ordinal') from exc
                count += 1;root ^= int(checksum,16)
            actual_count = actual_root = 0
            cursor = workspace.db.execute('SELECT ordinal,key,checksum FROM membership_order WHERE stream=? ORDER BY ordinal',(stream,))
            for ordinal, key, checksum in cursor:
                if checksum != _framed_sha(b'construction-order/v1',str(ordinal).encode(),key):
                    raise StoreIntegrityError('construction membership checksum mismatch')
                actual_count += 1;actual_root ^= int(checksum,16)
                yield store.codec.decode(key), ordinal
            if (actual_count,actual_root)!=(count,root):
                raise StoreIntegrityError('construction membership inventory mismatch')
        finally:
            if cursor is not None:cursor.close()
            workspace.db.execute('DELETE FROM membership_order WHERE stream=?',(stream,))


def clean_insertion_keys(owner):
    count = 0
    for key, _ordinal in ordered_memberships(owner._store, owner._pin, owner._namespace, 'insertion', 0):
        count += 1
        yield key
    if count != owner._baseline_count:
        raise StoreIntegrityError('construction insertion cardinality mismatch')


def verify_lazy_generation(store, generation):
    from .persistence_lazy_store import _order_checksum, _query_checksum
    from .persistence_conversion_workspace import ConversionWorkspace, DiskSet
    counts = {}
    db, codec = store.db, store.codec
    visible = 'valid_from<=? AND (valid_to IS NULL OR ?<valid_to)'
    with tempfile.TemporaryDirectory(prefix='ate-conversion-audit-') as directory:
        with ConversionWorkspace(codec, directory=directory) as workspace:
            for (namespace,) in db.execute('SELECT namespace FROM lazy_namespace_state WHERE '+visible,
                                           (generation, generation)):
                state = store._namespace_state_at(namespace, generation)
                if state is None:
                    raise StoreIntegrityError('visible lazy namespace has no state')
                expected_count, next_ordinal = state[:2]
                queries = DiskSet(workspace)
                previous, count = None, 0
                rows = db.execute('SELECT typed_key,valid_from,valid_to,payload,payload_checksum,'
                    'codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions '
                    'WHERE namespace=? AND '+visible+' ORDER BY typed_key,valid_from',
                    (namespace, generation, generation))
                for key, *row in rows:
                    if previous == key:
                        raise StoreIntegrityError('overlapping visible lazy record versions')
                    previous = key
                    codec.decode(key)
                    store._check_record_row(namespace, key, tuple(row), decode=True)
                    for name, value, ordinal in store._decode_memberships(row[6]):
                        queries.add(codec.encode((name, codec.encode(value), key, ordinal)))
                    count += 1
                if count != expected_count:
                    raise StoreIntegrityError('lazy namespace count does not match visible records')
                keys = db.execute('SELECT typed_key FROM lazy_record_versions WHERE namespace=? AND '
                                  +visible+' ORDER BY typed_key,valid_from', (namespace, generation, generation))
                orders = db.execute('SELECT typed_key,ordinal,valid_from,valid_to,row_checksum '
                    'FROM lazy_order_versions WHERE namespace=? AND '+visible+' ORDER BY typed_key,valid_from',
                    (namespace, generation, generation))
                order_count = 0
                for key_row, order in zip_longest(keys, orders):
                    if key_row is None or order is None or key_row[0] != order[0]:
                        raise StoreIntegrityError('lazy collection order does not match visible owners')
                    key, ordinal, start, end, checksum = order
                    if checksum != _order_checksum(namespace, key, ordinal, start, end):
                        raise StoreIntegrityError('lazy order checksum mismatch')
                    if ordinal >= next_ordinal:
                        raise StoreIntegrityError('collection ordinal is outside namespace counter')
                    order_count += 1
                if order_count != expected_count:
                    raise StoreIntegrityError('lazy collection order is incomplete')
                if db.execute('SELECT ordinal FROM lazy_order_versions WHERE namespace=? AND '+visible+
                    ' GROUP BY ordinal HAVING count(*)>1 LIMIT 1', (namespace, generation, generation)).fetchone():
                    raise StoreIntegrityError('duplicate visible collection ordinal')
                def actual_queries():
                    for name, value, key, ordinal, start, end, checksum in db.execute(
                        'SELECT index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum '
                        'FROM lazy_query_versions WHERE namespace=? AND '+visible, (namespace, generation, generation)):
                        if checksum != _query_checksum(namespace, name, value, key, ordinal, start, end):
                            raise StoreIntegrityError('lazy query checksum mismatch')
                        yield codec.encode((name, value, key, ordinal))
                if not queries.equals(actual_queries()):
                    raise StoreIntegrityError('lazy query membership is incomplete or contains extra rows')
                counts[namespace] = expected_count
                # The inventories have been fully authenticated and are disposable.
                workspace.db.execute('DELETE FROM conversion_sets')
                workspace.db.commit()
    return counts
