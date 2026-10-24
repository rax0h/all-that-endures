"""Checked raw collection order/counters; successor publication remains gated."""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _order_checksum,_namespace_checksum
from .persistence_proof_content import _namespace,_integer
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_order import query_order_key
from .persistence_proof_query import QueryPage,_cursor
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight
from .persistence_proof_publication import _guard_construction,MAX_BODY_BYTES
from .persistence_proof_occurrence import _require_indexes
from .persistence_sqlite_guard import require_persistent_sources

@dataclass(frozen=True)
class CollectionCertificate:
    store_identity:str
    generation:int
    codec_version:int
    namespace:str
    declared:bool
    member_count:int
    next_ordinal:int
    root:Root

def domain(identity,codec,namespace):return _digest(b'ate-collection-domain/1',_namespace(identity),_integer(codec,1),_namespace(namespace))
def member(d,key,ordinal):return _digest(b'ate-collection-member/1',d,query_order_key(ordinal,key))
def certificate_commitment(c):
    if (type(c) is not CollectionCertificate or type(c.generation) is not int or not 0<=c.generation<2**63 or type(c.declared) is not bool
        or type(c.member_count) is not int or type(c.next_ordinal) is not int or not 0<=c.member_count<=c.next_ordinal<2**63
        or not c.declared and (c.member_count or c.next_ordinal)):raise StoreIntegrityError('invalid collection certificate')
    d=domain(c.store_identity,c.codec_version,c.namespace);OrderedSeekMap(None,d)._reference(c.root)
    if c.root.count!=c.member_count:raise StoreIntegrityError('collection count/root disagreement')
    return _digest(b'ate-collection-certificate/1',d,c.generation.to_bytes(8,'big'),bytes([c.declared]),c.member_count.to_bytes(8,'big'),c.next_ordinal.to_bytes(8,'big'),c.root.digest)

def _indexes(store):
    required=('lazy_namespace_interval','lazy_order_interval')
    if any(i not in store._interval_indexes for i in required):raise StoreError('collection requires explicit interval indexes')
    _require_indexes(store.db,include_order=False,intervals=required)

def _state(store,g,ns):
    columns="CASE WHEN typeof(member_count)='integer' THEN member_count END,CASE WHEN typeof(next_ordinal)='integer' THEN next_ordinal END,CASE WHEN typeof(valid_from)='integer' THEN valid_from END,CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END"
    rows=store._interval_rows('lazy_namespace_state',columns,('namespace',),(ns,),g,'lazy_namespace_interval',limit=2)
    if not rows:return False,0,0
    if len(rows)!=1:raise StoreIntegrityError('overlapping collection state')
    count,next_id,start,end,end_type,checksum=rows[0]
    if (type(count) is not int or type(next_id) is not int or not 0<=count<=next_id<2**63 or type(start) is not int or not 0<=start<=g
        or end_type not in ('null','integer') or end_type=='integer' and (type(end) is not int or end<=g or end<=start)
        or checksum!=_namespace_checksum(ns,count,next_id,start,end)):raise StoreIntegrityError('collection state checksum/interval disagreement')
    return True,count,next_id

def _schema(db):
    require_persistent_sources(db)
    row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_ordered_seek_nodes' AND type='table'").fetchone()
    expected='CREATE TABLE ate_ordered_seek_nodes(domain BLOB NOT NULL,digest BLOB NOT NULL,raw BLOB NOT NULL,PRIMARY KEY(domain,digest)) WITHOUT ROWID'
    if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(expected.lower().split()):raise StoreError('collection proof schema requires explicit construction')

def _construct_collection(store,g,namespace):
    declared,count,next_id=_state(store,g,namespace)
    d=domain(store.store_identity,store.codec.version,namespace);m=OrderedSeekMap(store.db,d);m.create_schema();_schema(store.db)
    rows=store.db.execute('SELECT typed_key,ordinal FROM lazy_order_versions WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY ordinal,typed_key',(namespace,g,g))
    try:root=m.build((query_order_key(ordinal,key),member(d,key,ordinal)) for key,ordinal in rows)
    finally:rows.close()
    c=CollectionCertificate(store.store_identity,g,store.codec.version,namespace,declared,count,next_id,root);expected=certificate_commitment(c)
    from .persistence_proof_collection_publish import persist_bootstrap
    persist_bootstrap(store,c)
    return c,expected

def bootstrap_collection(store,pin,namespace,*,max_metadata_bytes=1048576):
    _require_closed_codec(store,allow_typed=True)
    if len(_namespace(namespace))>4096 or type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=MAX_BODY_BYTES:raise StoreIntegrityError('invalid collection construction budget')
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('collection construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        require_persistent_sources(store.db);_closed_snapshot_preflight(store,max_metadata_bytes);g=store._require_pin(pin)
        if g!=int(store._checked_head_row()[0]):raise StoreConflictError('collection construction requires current pin')
        _indexes(store);_guard_construction(store,g,MAX_BODY_BYTES,max_metadata_bytes)
        if store.db.execute("SELECT 1 FROM lazy_order_versions WHERE namespace=? AND (typeof(typed_key)!='blob' OR length(typed_key)>4096) LIMIT 1",(namespace,)).fetchone():raise StoreError('collection keys require separately budgeted path')
        store.verify_all()
        c,expected=_construct_collection(store,g,namespace)
        store.db.commit();return c,expected
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False

def read_collection_page(store,pin,certificate,expected,*,after=None,limit=128,max_metadata_bytes=1048576):
    c=certificate;actual=certificate_commitment(c)
    if type(expected) is not bytes or len(expected)!=32 or actual!=expected:raise StoreIntegrityError('collection expected authority disagreement')
    if (c.store_identity!=store.store_identity or c.store_identity!=pin.store_identity or c.codec_version!=store.codec.version or c.generation!=pin.captured_head):raise StoreConflictError('collection context disagreement')
    if type(limit) is not int or not 1<=limit<=128 or type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=MAX_BODY_BYTES:raise StoreIntegrityError('invalid collection page budget')
    _require_closed_codec(store,allow_typed=True);after=_cursor(after)
    if len(_namespace(c.namespace))>4096 or after and len(after[1])>4096:raise StoreError('collection field exceeds page path')
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):raise StoreError('collection cannot borrow arbitrary transaction')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as g:
        head=int(store._checked_head_row()[0])
        if g not in (head,head-1):raise StoreConflictError('collection pin outside retained generations')
        _schema(store.db);_indexes(store)
        if _state(store,g,c.namespace)!=(c.declared,c.member_count,c.next_ordinal):raise StoreIntegrityError('collection exact state disagreement')
        d=domain(c.store_identity,c.codec_version,c.namespace);m=OrderedSeekMap(store.db,d);positions=m.page(c.root,after=None if after is None else query_order_key(*after),limit=limit+1);result=[]
        for position,value in positions[:limit]:
            if len(position)<8 or len(position)>4104:raise StoreIntegrityError('invalid collection position')
            ordinal=int.from_bytes(position[:8],'big');key=position[8:];query_order_key(ordinal,key)
            if ordinal>=c.next_ordinal:raise StoreIntegrityError('collection position exceeds counter')
            columns="CASE WHEN typeof(ordinal)='integer' THEN ordinal END,CASE WHEN typeof(valid_from)='integer' THEN valid_from END,CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END"
            rows=store._interval_rows('lazy_order_versions',columns,('namespace','typed_key'),(c.namespace,key),g,'lazy_order_interval',limit=2)
            if len(rows)!=1:raise StoreIntegrityError('selected collection order missing/overlapping')
            actual_ordinal,start,end,end_type,checksum=rows[0]
            if (actual_ordinal!=ordinal or type(start) is not int or not 0<=start<=g or end_type not in ('null','integer')
                or end_type=='integer' and (type(end) is not int or end<=g or end<=start)
                or checksum!=_order_checksum(c.namespace,key,ordinal,start,end) or value!=member(d,key,ordinal)):raise StoreIntegrityError('selected collection source disagreement')
            result.append((key,ordinal))
        return QueryPage(tuple(result),(result[-1][1],result[-1][0]) if result and len(positions)>limit else None)
