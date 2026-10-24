"""Complete audited lazy namespace source and bounded raw directory reads.

Inactive authority: successor directory publication, save-head inventory,
allocators, topology and World admission require separate integration.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_content import _namespace,_integer
from . import persistence_proof_collection as collection
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight
from .persistence_proof_publication import _guard_construction,MAX_BODY_BYTES
from .persistence_sqlite_guard import require_persistent_sources
from .persistence_lazy_store import P1_DDL,P4_DDL

_SCHEMA='CREATE TABLE ate_collection_directory_bodies(domain BLOB NOT NULL,digest BLOB NOT NULL,raw BLOB NOT NULL,PRIMARY KEY(domain,digest)) WITHOUT ROWID'
_SOURCE_TABLES=tuple(sql.strip() for sql in (P1_DDL+P4_DDL).split(';') if sql.strip().startswith('CREATE TABLE '))
_SOURCE_INDEXES=tuple('CREATE INDEX ate_directory_'+kind+'_namespace_start ON '+table+'(namespace,valid_from)' for kind,table in (('order','lazy_order_versions'),('record','lazy_record_versions')))

def _source_schemas(db):
    # Must precede inherited metadata reads, including the snapshot preflight.
    # A view or virtual/generated replacement can invoke SQL functions on SELECT.
    require_persistent_sources(db)
    for sql in _SOURCE_TABLES:
        name=sql.split('(')[0].split()[2]
        row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=8192 THEN sql END FROM main.sqlite_schema WHERE name=? AND type='table'",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('directory source table schema disagreement')

def _source_indexes(db,*,create=False):
    for sql in _SOURCE_INDEXES:
        if create:db.execute(sql.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))
        name=sql.split()[2]
        row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name=? AND type='index'",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('directory source indexes require verified construction')

def _read_preflight(store,budget):
    _source_schemas(store.db);_source_indexes(store.db);_closed_snapshot_preflight(store,budget)

@dataclass(frozen=True)
class CollectionDirectoryCertificate:
    store_identity:str
    generation:int
    codec_version:int
    root:Root

@dataclass(frozen=True)
class CollectionNamespacePage:
    entries:tuple
    next_after:bytes|None

def domain(identity,codec):return _digest(b'ate-collection-directory-domain/1',_namespace(identity),_integer(codec,1))

def certificate_commitment(c):
    if type(c) is not CollectionDirectoryCertificate or type(c.generation) is not int or not 0<=c.generation<2**63:raise StoreIntegrityError('invalid collection directory certificate')
    d=domain(c.store_identity,c.codec_version);OrderedSeekMap(None,d)._reference(c.root)
    return _digest(b'ate-collection-directory-certificate/1',d,c.generation.to_bytes(8,'big'),c.root.count.to_bytes(8,'big'),c.root.digest)

def _budget(value):
    if type(value) is not int or not 1<=value<=MAX_BODY_BYTES:raise StoreIntegrityError('invalid directory metadata budget')

def _key(namespace):
    raw=_namespace(namespace)
    if len(raw)>4096:raise StoreError('directory namespace requires separately budgeted path')
    return raw

def _schemas(db):
    collection._schema(db)
    row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_collection_directory_bodies' AND type='table'").fetchone()
    if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(_SCHEMA.lower().split()):raise StoreError('directory requires verified construction')

def _raw(c):
    collection.certificate_commitment(c)
    if not c.declared:raise StoreIntegrityError('directory descriptor must be declared')
    return b'ATED\x01'+c.member_count.to_bytes(8,'big')+c.next_ordinal.to_bytes(8,'big')+c.root.count.to_bytes(8,'big')+c.root.digest

def _body_hash(d,key,raw):return _digest(b'ate-collection-directory-body/1',d,key,raw)

def _persist(store,d,key,c):
    raw=_raw(c);h=_body_hash(d,key,raw)
    store.db.execute('INSERT OR IGNORE INTO ate_collection_directory_bodies VALUES(?,?,?)',(d,h,raw))
    row=store.db.execute("SELECT CASE WHEN typeof(raw)='blob' AND length(raw)=61 THEN raw END FROM ate_collection_directory_bodies WHERE domain=? AND digest=?",(d,h)).fetchone()
    if row is None or row[0]!=raw:raise StoreIntegrityError('cannot repair divergent directory descriptor')
    return h

def bootstrap_collection_directory(store,pin,*,max_metadata_bytes=1048576):
    _budget(max_metadata_bytes);_require_closed_codec(store,allow_typed=True)
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('directory construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        _source_schemas(store.db);_closed_snapshot_preflight(store,max_metadata_bytes);g=store._require_pin(pin)
        if g!=int(store._checked_head_row()[0]):raise StoreConflictError('directory construction requires current pin')
        collection._indexes(store);_source_indexes(store.db,create=True);_guard_construction(store,g,MAX_BODY_BYTES,max_metadata_bytes)
        for table in ('lazy_namespace_state','lazy_order_versions','lazy_record_versions'):
            if store.db.execute('SELECT 1 FROM '+table+' WHERE length(CAST(namespace AS BLOB))>4096 LIMIT 1').fetchone():raise StoreError('directory namespace exceeds field path')
        if store.db.execute("SELECT 1 FROM lazy_order_versions WHERE typeof(typed_key)!='blob' OR length(typed_key)>4096 LIMIT 1").fetchone():raise StoreError('directory collection key exceeds field path')
        # The inherited audit iterates declared states. Explicitly reject source
        # rows outside that inventory, including coherent orphan namespaces.
        for table in ('lazy_order_versions','lazy_record_versions'):
            if store.db.execute('SELECT 1 FROM '+table+' AS source WHERE source.valid_from<=? AND (source.valid_to IS NULL OR ?<source.valid_to) AND NOT EXISTS(SELECT 1 FROM lazy_namespace_state AS state WHERE state.namespace=source.namespace AND state.valid_from<=? AND (state.valid_to IS NULL OR ?<state.valid_to)) LIMIT 1',(g,g,g,g)).fetchone():raise StoreIntegrityError('source namespace outside declared collection inventory')
        store.verify_all()
        d=domain(store.store_identity,store.codec.version);m=OrderedSeekMap(store.db,d);m.create_schema()
        store.db.execute(_SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1));_schemas(store.db)
        rows=store.db.execute('SELECT namespace FROM lazy_namespace_state WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY CAST(namespace AS BLOB)',(g,g))
        def values():
            for (ns,) in rows:
                c,e=collection._construct_collection(store,g,ns)
                yield _key(ns),_persist(store,d,_key(ns),c)
        try:root=m.build(values())
        finally:rows.close()
        c=CollectionDirectoryCertificate(store.store_identity,g,store.codec.version,root);expected=certificate_commitment(c)
        store.db.commit();return c,expected
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False

def _preflight(store,pin,c,expected,budget):
    _budget(budget)
    if type(expected) is not bytes or len(expected)!=32 or certificate_commitment(c)!=expected:raise StoreIntegrityError('directory expected authority disagreement')
    if (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version) or pin.store_identity!=store.store_identity:raise StoreConflictError('directory source context disagreement')
    _require_closed_codec(store,allow_typed=True)
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):raise StoreError('directory cannot borrow arbitrary transaction')

def _snapshot(store,g):
    head=int(store._checked_head_row()[0])
    if g not in (head,head-1):raise StoreConflictError('directory outside retained generations')
    _schemas(store.db);collection._indexes(store)

def _selected(store,c,key,value):
    if type(key) is not bytes or len(key)>4096:raise StoreIntegrityError('invalid selected namespace bytes')
    try:ns=key.decode('utf-8')
    except UnicodeError as exc:raise StoreIntegrityError('invalid namespace encoding') from exc
    if _key(ns)!=key:raise StoreIntegrityError('noncanonical namespace key')
    d=domain(c.store_identity,c.codec_version)
    row=store.db.execute("SELECT CASE WHEN typeof(raw)='blob' AND length(raw)=61 THEN raw END FROM ate_collection_directory_bodies WHERE domain=? AND digest=?",(d,value)).fetchone()
    if row is None or type(row[0]) is not bytes:raise StoreIntegrityError('missing or oversized directory descriptor')
    raw=row[0]
    if raw[:5]!=b'ATED\x01' or _body_hash(d,key,raw)!=value:raise StoreIntegrityError('directory descriptor disagreement')
    count,next_id,root_count=(int.from_bytes(raw[i:i+8],'big') for i in (5,13,21))
    child=collection.CollectionCertificate(c.store_identity,c.generation,c.codec_version,ns,True,count,next_id,Root(raw[29:],root_count))
    expected=collection.certificate_commitment(child)
    if collection._state(store,c.generation,ns)!=(True,count,next_id):raise StoreIntegrityError('directory selected namespace state disagreement')
    return child,expected

def read_collection_namespace(store,pin,certificate,expected,namespace,*,max_metadata_bytes=1048576):
    c=certificate;_preflight(store,pin,c,expected,max_metadata_bytes);key=_key(namespace)
    with store.read_snapshot(pin,_preflight=lambda:_read_preflight(store,max_metadata_bytes)) as g:
        _snapshot(store,g);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version));value=m.get(c.root,key)
        if value is None:
            if collection._state(store,g,namespace)!=(False,0,0):raise StoreIntegrityError('directory absence/source disagreement')
            # A namespace stays declared once introduced. Thus an accepted
            # absence cannot have any predecessor source, even an expired
            # orphan. Future-only rows remain valid for a retained old pin.
            for table,kind in (('lazy_order_versions','order'),('lazy_record_versions','record')):
                if store.db.execute('SELECT 1 FROM '+table+' INDEXED BY ate_directory_'+kind+'_namespace_start WHERE namespace=? AND valid_from<=? LIMIT 1',(namespace,g)).fetchone():raise StoreIntegrityError('directory absence has orphan predecessor source')
            return None
        return _selected(store,c,key,value)

def read_collection_namespaces(store,pin,certificate,expected,*,after=None,limit=128,max_metadata_bytes=1048576):
    c=certificate;_preflight(store,pin,c,expected,max_metadata_bytes)
    if type(limit) is not int or not 1<=limit<=128 or after is not None and (type(after) is not bytes or len(after)>4096):raise StoreIntegrityError('invalid directory page/cursor')
    with store.read_snapshot(pin,_preflight=lambda:_read_preflight(store,max_metadata_bytes)) as g:
        _snapshot(store,g);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version));positions=m.page(c.root,after=after,limit=limit+1)
        return CollectionNamespacePage(tuple(_selected(store,c,k,v) for k,v in positions[:limit]),positions[limit-1][0] if len(positions)>limit else None)
