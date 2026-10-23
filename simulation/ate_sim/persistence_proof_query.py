"""Pinned physical query pages; accepted outer authority is mandatory.

This adapter returns raw membership metadata, never admitted World objects.
The default store/World readers do not select it. Certificates supplied here
must be anchored by fully verified import/transition and eventual manifests.
"""
from dataclasses import dataclass

from .incremental_store import StoreError, StoreConflictError, StoreIntegrityError
from .persistence_lazy_store import _query_checksum
from .persistence_proof_content import _namespace, _integer, _bytes
from .persistence_proof_nodes import _digest
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_order import OrderEntry, OrderRoot, query_order_key, root_commitment, verify_page


@dataclass(frozen=True)
class QueryScope:
    namespace: str
    index_name: str
    index_value: bytes


@dataclass(frozen=True)
class QueryCertificate:
    store_identity: str
    generation: int
    codec_version: int
    scope: QueryScope
    order: OrderRoot


@dataclass(frozen=True)
class QueryPage:
    positions: tuple[tuple[bytes, int], ...]
    next_after: tuple[int, bytes] | None


MAX_QUERY_KEY_BYTES = 4096


class QueryProofBudgetError(StoreError):
    """Requires a separately budgeted, certificate-checked source path."""


def query_domain(store_identity, codec_version, scope):
    if type(scope) is not QueryScope:
        raise StoreIntegrityError('invalid query proof scope')
    return _digest(b'ate-query-proof-domain/1', _namespace(store_identity),
        _integer(codec_version, 1), _namespace(scope.namespace),
        _namespace(scope.index_name), _bytes(scope.index_value))


def member_commitment(domain, typed_record_key, ordinal):
    query_order_key(ordinal, typed_record_key)
    return _digest(b'ate-query-proof-member/1', domain, typed_record_key, ordinal.to_bytes(8, 'big'))


def certificate_commitment(certificate):
    if (type(certificate) is not QueryCertificate or type(certificate.generation) is not int
            or not 0 <= certificate.generation < 2**63):
        raise StoreIntegrityError('invalid query certificate')
    domain = query_domain(certificate.store_identity, certificate.codec_version, certificate.scope)
    return _digest(b'ate-query-certificate/1', domain, certificate.generation.to_bytes(8, 'big'),
                   root_commitment(domain, certificate.order))


def _cursor(after):
    if after is None:
        return None
    if type(after) is not tuple or len(after) != 2:
        raise StoreIntegrityError('invalid raw query cursor')
    ordinal, key = after
    query_order_key(ordinal, key)
    return ordinal, key


def _rows(store, generation, head, scope, *, boundary=None, descending=False, limit=1):
    # Internal fixed identifiers/operators; all source values are parameters.
    relation = '<' if descending else '>'
    seek = '' if boundary is None else f' AND (ordinal,record_key){relation}(?,?)'
    order = 'DESC' if descending else 'ASC'
    suffix = seek + f' ORDER BY ordinal {order},record_key {order} LIMIT ?'
    base = (scope.namespace, scope.index_name, scope.index_value)
    tail = (() if boundary is None else boundary) + (limit,)
    # A corrupt TEXT value with early NUL can defeat length(TEXT). Guard
    # storage classes and byte lengths inside SQL BEFORE transferring bodies.
    columns = (f"CASE WHEN typeof(record_key)='blob' AND length(record_key)<={MAX_QUERY_KEY_BYTES} THEN record_key END,"
        "CASE WHEN typeof(ordinal)='integer' THEN ordinal END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END,"
        "CASE WHEN typeof(record_key)='blob' THEN length(record_key) END,typeof(valid_to)")
    where = 'namespace=? AND index_name=? AND index_value=? '
    if generation == head:
        groups = [store.db.execute(f'SELECT {columns} FROM lazy_query_versions INDEXED BY lazy_query_current '
            f'WHERE {where}AND valid_to IS NULL AND valid_from<=?' + suffix,
            base + (generation,) + tail).fetchall()]
    else:
        groups = [store.db.execute(f'SELECT {columns} FROM lazy_query_versions INDEXED BY lazy_query_open_generation '
            f'WHERE {where}AND valid_to IS NULL AND valid_from<=?' + suffix,
            base + (generation,) + tail).fetchall(),
            store.db.execute(f'SELECT {columns} FROM lazy_query_versions INDEXED BY lazy_query_closed_generation '
            f'WHERE {where}AND valid_to=? AND valid_from<=?' + suffix,
            base + (generation+1, generation) + tail).fetchall()]
    rows = []
    for group in groups:
        for key, ordinal, start, end, checksum, key_size, end_type in group:
            if type(key_size) is int and key_size > MAX_QUERY_KEY_BYTES:
                raise QueryProofBudgetError('query key exceeds proof-page metadata budget')
            if type(key_size) is not int or type(key) is not bytes or len(key) != key_size:
                raise StoreIntegrityError('invalid physical query key')
            query_order_key(ordinal, key)
            if (type(start) is not int or not 0 <= start <= generation
                    or end_type not in ('null', 'integer')
                    or end is not None and (type(end) is not int or end <= generation or end <= start)
                    or checksum != _query_checksum(scope.namespace, scope.index_name,
                        scope.index_value, key, ordinal, start, end)):
                raise StoreIntegrityError('invalid physical query row')
            # Limited ordered streams can hide another interval at the same
            # position, including a closed interval absent from the fast stream.
            # Seek all visible intervals for this exact position; constants only
            # cross into Python, and the existing index skips expired backlog.
            witnesses = store._interval_rows('lazy_query_versions', '1',
                ('namespace', 'index_name', 'index_value', 'record_key', 'ordinal'),
                (scope.namespace, scope.index_name, scope.index_value, key, ordinal),
                generation, 'lazy_query_interval', limit=2)
            store._metadata_rows += len(witnesses)
            if len(witnesses) != 1:
                raise StoreIntegrityError('overlapping visible query positions')
            rows.append((key, ordinal))
    rows.sort(key=lambda row:(row[1], row[0]), reverse=descending)
    for previous, current in zip(rows, rows[1:]):
        if previous == current:
            raise StoreIntegrityError('overlapping visible query positions')
    return rows[:limit]


def _position(row):
    key, ordinal = row
    return query_order_key(ordinal, key)


def read_query_page(store, pin, certificate, expected_commitment, *, after=None, limit=128):
    actual = certificate_commitment(certificate)
    if type(expected_commitment) is not bytes or len(expected_commitment) != 32 or actual != expected_commitment:
        raise StoreIntegrityError('query certificate commitment disagreement')
    if (certificate.store_identity != store.store_identity or certificate.store_identity != pin.store_identity
            or certificate.generation != pin.captured_head or certificate.codec_version != store.codec.version):
        raise StoreConflictError('query certificate store/codec/pin disagreement')
    if type(limit) is not int or not 1 <= limit <= 128:
        raise StoreIntegrityError('invalid query page limit')
    after = _cursor(after)
    if (store.db.in_transaction and not store._active_read_transaction
            and not getattr(store, '_checked_snapshot_depth', 0)):
        raise StoreError('query proof reader cannot borrow an arbitrary transaction')
    with store.read_snapshot(pin) as generation:
        head = int(store._checked_head_row()[0])
        if generation not in (head, head-1):
            raise StoreConflictError('query pin exceeds two-snapshot visibility')
        scope = certificate.scope
        domain = query_domain(certificate.store_identity, certificate.codec_version, scope)
        nodes = ProofNodeStore(store.db)
        m = ProofMap(domain, lambda d:nodes.read(domain,d), None)
        fetched = _rows(store,generation,head,scope,boundary=after,limit=limit+1)
        page = fetched[:limit]
        boundary_entry = None
        if page:
            first = page[0]
            predecessors = _rows(store,generation,head,scope,boundary=(first[1],first[0]),descending=True)
            previous = _position(predecessors[0]) if predecessors else None
            entries = []
            for i,row in enumerate(page):
                following = _position(fetched[i+1]) if i+1 < len(fetched) else None
                key,ordinal = row
                entries.append(OrderEntry(_position(row),member_commitment(domain,key,ordinal),previous,following))
                previous = _position(row)
        else:
            entries = []
            final = _rows(store,generation,head,scope,descending=True)
            if final:
                key,ordinal = final[0]
                previous = _rows(store,generation,head,scope,boundary=(ordinal,key),descending=True)
                boundary_entry = OrderEntry(_position(final[0]),member_commitment(domain,key,ordinal),
                    _position(previous[0]) if previous else None,None)
        verified = verify_page(m,certificate.order,root_commitment(domain,certificate.order),
            rows=entries,after=query_order_key(*after) if after is not None else None,
            limit=limit,boundary=boundary_entry)
        next_after = (page[-1][1],page[-1][0]) if verified and verified[-1].following is not None else None
        return QueryPage(tuple(page),next_after)
