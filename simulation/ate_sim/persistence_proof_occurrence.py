"""Complete pinned raw placement pages; inactive until outer World authority.

No payloads/objects are decoded and no production certificate is constructed.
Both owner/group views still need full topology transition cross-consistency.
"""
from dataclasses import dataclass

from .incremental_store import StoreError, StoreConflictError, StoreIntegrityError
from .persistence_lazy_store import _identity_occurrence_checksum, _identity_state_checksum, INTERVAL_INDEXES, INTERVAL_TABLES
from .persistence_proof_content import _namespace, _integer, _bytes
from .persistence_proof_nodes import _digest
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_order import OrderEntry, OrderRoot, root_commitment, verify_page
from .persistence_proof_version import _guard_operational_metadata, VersionProofBudgetError


@dataclass(frozen=True)
class OwnerScope:
    namespace: str
    typed_key: bytes


@dataclass(frozen=True)
class GroupScope:
    incarnation_id: int


@dataclass(frozen=True)
class RawOccurrence:
    namespace: str
    typed_key: bytes
    path: bytes
    incarnation_id: int


@dataclass(frozen=True)
class OccurrenceCertificate:
    store_identity: str
    generation: int
    codec_version: int
    scope: OwnerScope | GroupScope
    next_incarnation_id: int
    order: OrderRoot


@dataclass(frozen=True)
class OccurrencePage:
    rows: tuple[RawOccurrence, ...]
    next_after: tuple[str, bytes, bytes] | None


class OccurrenceProofBudgetError(StoreError):
    """Requires a separately budgeted, certificate-checked source path."""


MAX_FIELD_BYTES = 4096
# Schema work belongs to explicit verified construction, never first access.
INDEXES = (
    ('lazy_identity_occurrence_current', ('owner_namespace','owner_key','occurrence_path','incarnation_id'), True),
    ('ate_occurrence_owner_closed', ('owner_namespace','owner_key','valid_to','occurrence_path','valid_from'), False),
    ('ate_occurrence_group_current', ('incarnation_id','owner_namespace','owner_key','occurrence_path'), True),
    ('ate_occurrence_group_closed', ('incarnation_id','valid_to','owner_namespace','owner_key','occurrence_path','valid_from'), False),
)
REQUIRED_INTERVALS = ('lazy_identity_occurrence_interval','lazy_identity_state_interval')


def create_occurrence_indexes(db):
    if not db.in_transaction:
        raise StoreError('occurrence index construction requires caller transaction')
    for name, fields, partial in INDEXES:
        db.execute(f'CREATE INDEX IF NOT EXISTS {name} ON lazy_identity_occurrence_versions('
                   + ','.join(fields) + ')' + (' WHERE valid_to IS NULL' if partial else ''))
    _require_indexes(db)


def _require_indexes(db,*,include_order=True,intervals=REQUIRED_INTERVALS):
    requirements=(INDEXES if include_order else ())+tuple((name,INTERVAL_INDEXES[name],False) for name in intervals)
    for name, fields, partial in requirements:
        row = db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=8192 THEN sql END "
                         "FROM sqlite_schema WHERE type='index' AND name=?", (name,)).fetchone()
        table=INTERVAL_TABLES[name] if name in INTERVAL_TABLES else 'lazy_identity_occurrence_versions'
        expected = f'CREATE INDEX {name} ON {table}('+','.join(fields)+')'+(
            ' WHERE valid_to IS NULL' if partial else '')
        # Column names alone miss collation, DESC and a changed partial predicate;
        # those can force an unbounded temporary sort or exclude visible rows.
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split()) != ''.join(expected.lower().split()):
            raise StoreError('occurrence proof indexes require explicit checked-copy construction')


def _id(value):
    if type(value) is not int or not 0 < value < 2**63:
        raise StoreIntegrityError('invalid occurrence proof incarnation/allocator')
    return value.to_bytes(8,'big')


def occurrence_domain(store_identity, codec_version, scope):
    if type(scope) is OwnerScope:
        parts = (b'owner', _namespace(scope.namespace), _bytes(scope.typed_key))
    elif type(scope) is GroupScope:
        parts = (b'group', _id(scope.incarnation_id))
    else:
        raise StoreIntegrityError('invalid occurrence proof scope')
    return _digest(b'ate-occurrence-proof-domain/1', _namespace(store_identity), _integer(codec_version,1), *parts)


def group_order_key(namespace, typed_key, path):
    return b''.join(part.replace(b'\x00',b'\x00\xff')+b'\x00\x00'
                    for part in (_namespace(namespace),_bytes(typed_key),_bytes(path)))


def member_commitment(domain, row):
    if type(row) is not RawOccurrence:
        raise StoreIntegrityError('invalid raw occurrence')
    return _digest(b'ate-occurrence-proof-member/1', domain, _namespace(row.namespace),
                   _bytes(row.typed_key), _bytes(row.path), _id(row.incarnation_id))


def certificate_commitment(certificate):
    if (type(certificate) is not OccurrenceCertificate or type(certificate.generation) is not int
            or not 0 <= certificate.generation < 2**63):
        raise StoreIntegrityError('invalid occurrence certificate')
    allocator = _id(certificate.next_incarnation_id)
    domain = occurrence_domain(certificate.store_identity,certificate.codec_version,certificate.scope)
    if type(certificate.scope) is GroupScope and certificate.scope.incarnation_id >= certificate.next_incarnation_id:
        raise StoreIntegrityError('occurrence group exceeds accepted allocator')
    return _digest(b'ate-occurrence-certificate/1',domain,certificate.generation.to_bytes(8,'big'),allocator,
                   root_commitment(domain,certificate.order))


def _check_allocator(store,generation,expected):
    columns = ("CASE WHEN typeof(next_incarnation_id)='integer' THEN next_incarnation_id END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
    rows = store._interval_rows('lazy_identity_state',columns,(),(),generation,'lazy_identity_state_interval',limit=2)
    store._metadata_rows += len(rows)
    if len(rows) != 1:
        raise StoreIntegrityError('occurrence allocator interval completeness disagreement')
    value,start,end,end_type,checksum = rows[0]
    if (type(value) is not int or value != expected or type(start) is not int or not 0 <= start <= generation
            or end_type not in ('null','integer') or end_type=='integer' and (end<=generation or end<=start)
            or checksum != _identity_state_checksum(value,start,end)):
        raise StoreIntegrityError('occurrence allocator source disagreement')


def _cursor(scope,after):
    if after is None: return None
    if type(after) is not tuple or len(after)!=3:
        raise StoreIntegrityError('invalid occurrence raw cursor')
    ns,key,path = after
    _namespace(ns);_bytes(key);_bytes(path)
    if type(scope) is OwnerScope and (ns,key)!=(scope.namespace,scope.typed_key):
        raise StoreIntegrityError('occurrence cursor belongs to another owner')
    return after


def _position(scope,row):
    return row.path if type(scope) is OwnerScope else group_order_key(row.namespace,row.typed_key,row.path)


def _rows(store,generation,head,scope,allocator,*,boundary=None,descending=False,limit=1):
    owner = type(scope) is OwnerScope
    relation, order = ('<','DESC') if descending else ('>','ASC')
    fields = 'occurrence_path' if owner else 'owner_namespace,owner_key,occurrence_path'
    seek = '' if boundary is None else (f' AND occurrence_path{relation}?' if owner else
                                       f' AND ({fields}){relation}(?,?,?)')
    tail = () if boundary is None else (boundary[2],) if owner else boundary
    suffix = seek+' ORDER BY '+','.join(f'{f} {order}' for f in fields.split(','))+' LIMIT ?'
    where,args = ('owner_namespace=? AND owner_key=?',(scope.namespace,scope.typed_key)) if owner else ('incarnation_id=?',(scope.incarnation_id,))
    columns = (f"CASE WHEN typeof(owner_namespace)='text' AND length(CAST(owner_namespace AS BLOB))<={MAX_FIELD_BYTES} THEN CAST(owner_namespace AS BLOB) END,"
        f"CASE WHEN typeof(owner_key)='blob' AND length(owner_key)<={MAX_FIELD_BYTES} THEN owner_key END,"
        f"CASE WHEN typeof(occurrence_path)='blob' AND length(occurrence_path)<={MAX_FIELD_BYTES} THEN occurrence_path END,"
        "CASE WHEN typeof(incarnation_id)='integer' THEN incarnation_id END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END,"
        "CASE WHEN typeof(owner_namespace)='text' THEN length(CAST(owner_namespace AS BLOB)) END,"
        "CASE WHEN typeof(owner_key)='blob' THEN length(owner_key) END,"
        "CASE WHEN typeof(occurrence_path)='blob' THEN length(occurrence_path) END")
    current = INDEXES[0][0] if owner else INDEXES[2][0]
    closed = INDEXES[1][0] if owner else INDEXES[3][0]
    streams = [store.db.execute(f'SELECT {columns} FROM lazy_identity_occurrence_versions INDEXED BY {current} '
        f'WHERE {where} AND valid_to IS NULL'+suffix,args+tail+(limit,)).fetchall()]
    if generation != head:
        streams.append(store.db.execute(f'SELECT {columns} FROM lazy_identity_occurrence_versions INDEXED BY {closed} '
            f'WHERE {where} AND valid_to=?'+suffix,args+(generation+1,)+tail+(limit,)).fetchall())
    result=[]
    for stream in streams:
        for ns,key,path,inc,start,end,end_type,checksum,nslen,keylen,pathlen in stream:
            if any(type(n) is int and n>MAX_FIELD_BYTES for n in (nslen,keylen,pathlen)):
                raise OccurrenceProofBudgetError('occurrence field exceeds bounded page path')
            if (any(type(n) is not int for n in (nslen,keylen,pathlen))
                    or any(type(v) is not bytes for v in (ns,key,path))
                    or (len(ns),len(key),len(path))!=(nslen,keylen,pathlen)):
                raise StoreIntegrityError('invalid physical occurrence field types')
            try: namespace=ns.decode('utf-8')
            except UnicodeDecodeError as exc: raise StoreIntegrityError('invalid occurrence namespace encoding') from exc
            _namespace(namespace)
            # Do NOT filter newer rows in SQL: an old pin could otherwise scan
            # an arbitrarily large newly populated scope before its LIMIT.
            # Fetch a bounded candidate prefix and reject this fast path when
            # a legitimate newer placement intervenes. No partial/unchecked
            # old-pin answer or hidden compatibility scan is returned.
            if generation!=head and type(start) is int and start==head and end_type=='null':
                raise OccurrenceProofBudgetError('newer placements require a separately budgeted old-pin selection path')
            if (type(inc) is not int or not 0<inc<allocator or type(start) is not int or not 0<=start<=generation
                    or end_type not in ('null','integer') or end_type=='integer' and (end<=generation or end<=start)
                    or checksum != _identity_occurrence_checksum(namespace,key,path,inc,start,end)):
                raise StoreIntegrityError('invalid physical occurrence interval/checksum')
            # A second visible interval may name ANOTHER incarnation, so the
            # uniqueness probe must use the exact placement, not group scope.
            witnesses=store._interval_rows('lazy_identity_occurrence_versions','1',
                ('owner_namespace','owner_key','occurrence_path'),(namespace,key,path),generation,
                'lazy_identity_occurrence_interval',limit=2)
            store._metadata_rows+=len(witnesses)
            if len(witnesses)!=1:
                raise StoreIntegrityError('overlapping visible occurrence placement')
            result.append(RawOccurrence(namespace,key,path,inc))
    result.sort(key=lambda row:_position(scope,row),reverse=descending)
    if any(_position(scope,a)==_position(scope,b) for a,b in zip(result,result[1:])):
        raise StoreIntegrityError('duplicate visible occurrence positions')
    return result[:limit]


def read_occurrence_page(store,pin,certificate,expected_commitment,*,after=None,limit=128,max_metadata_bytes=1048576):
    actual=certificate_commitment(certificate)
    if type(expected_commitment) is not bytes or len(expected_commitment)!=32 or expected_commitment!=actual:
        raise StoreIntegrityError('occurrence certificate commitment disagreement')
    if (certificate.store_identity!=store.store_identity or certificate.store_identity!=pin.store_identity
            or certificate.generation!=pin.captured_head or certificate.codec_version!=store.codec.version):
        raise StoreConflictError('occurrence certificate store/codec/pin disagreement')
    if (type(limit) is not int or not 1<=limit<=128 or type(max_metadata_bytes) is not int
            or not 1<=max_metadata_bytes<=64*1024*1024):
        raise StoreIntegrityError('invalid occurrence page/metadata budget')
    scope=certificate.scope;after=_cursor(scope,after)
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('occurrence proof reader cannot borrow an arbitrary transaction')
    def preflight():
        try: _guard_operational_metadata(store,max_metadata_bytes)
        except VersionProofBudgetError as exc: raise OccurrenceProofBudgetError(str(exc)) from exc
    with store.read_snapshot(pin,_preflight=preflight) as generation:
        head=int(store._checked_head_row()[0])
        if generation not in (head,head-1):raise StoreConflictError('occurrence pin exceeds retained snapshots')
        if any(name not in store._interval_indexes for name in REQUIRED_INTERVALS):
            raise StoreError('occurrence proof reader cannot use legacy interval selection')
        _require_indexes(store.db);_check_allocator(store,generation,certificate.next_incarnation_id)
        domain=occurrence_domain(certificate.store_identity,certificate.codec_version,scope)
        nodes=ProofNodeStore(store.db);m=ProofMap(domain,lambda d:nodes.read(domain,d),None)
        def source(**kwargs):return _rows(store,generation,head,scope,certificate.next_incarnation_id,**kwargs)
        fetched=source(boundary=after,limit=limit+1);page=fetched[:limit];entries=[];boundary_entry=None
        def cursor(row):return row.namespace,row.typed_key,row.path
        if page:
            predecessors=source(boundary=cursor(page[0]),descending=True)
            previous=_position(scope,predecessors[0]) if predecessors else None
            for i,row in enumerate(page):
                following=_position(scope,fetched[i+1]) if i+1<len(fetched) else None
                entries.append(OrderEntry(_position(scope,row),member_commitment(domain,row),previous,following))
                previous=_position(scope,row)
        else:
            final=source(descending=True)
            if final:
                previous=source(boundary=cursor(final[0]),descending=True)
                boundary_entry=OrderEntry(_position(scope,final[0]),member_commitment(domain,final[0]),
                    _position(scope,previous[0]) if previous else None,None)
        position_after=None if after is None else after[2] if type(scope) is OwnerScope else group_order_key(*after)
        verified=verify_page(m,certificate.order,root_commitment(domain,certificate.order),rows=entries,
                             after=position_after,limit=limit,boundary=boundary_entry)
        next_after=cursor(page[-1]) if verified and verified[-1].following is not None else None
        return OccurrencePage(tuple(page),next_after)
