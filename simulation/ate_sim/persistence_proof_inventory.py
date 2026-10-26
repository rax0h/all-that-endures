"""Inactive exact raw head/namespace-count/identity-allocator authority.

Counts preserve save-head semantics (auxiliary lazy versions are excluded),
not target existence/kind or complete World reference topology. Metadata has an explicit aggregate bound; archive bodies
are audited only during explicit construction.
"""
from dataclasses import dataclass
import json
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,_namespace_counts,_bump_count
from .persistence_proof_generation import ManifestHead
from .persistence_proof_collection import _schema as _node_schema
from .persistence_lazy_store import _auxiliary_namespace
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_content import _namespace,_integer
from .persistence_proof_projection import _require_closed_codec,_ProjectionCodec
from .persistence_proof_occurrence import _check_allocator,_require_indexes
from .persistence_proof_publication import _guard_construction,MAX_BODY_BYTES
from . import persistence_proof_collection_directory as source
from . import persistence_proof_directory_publish as directory
from . import persistence_proof_collection_publish as collection

MAX_METADATA_BYTES=1048576
MAX_CERTIFICATE_BYTES=3*MAX_METADATA_BYTES
_SCHEMA='CREATE TABLE ate_inventory_generations(generation INTEGER NOT NULL PRIMARY KEY,certificate BLOB NOT NULL,commitment BLOB NOT NULL,parent BLOB,writer TEXT NOT NULL,token BLOB NOT NULL,checksum BLOB NOT NULL) WITHOUT ROWID'

@dataclass(frozen=True)
class InventoryCertificate:
    store_identity:str
    generation:int
    codec_version:int
    head:ManifestHead
    root:Root

@dataclass(frozen=True)
class InventoryPage:
    entries:tuple
    next_after:bytes|None

@dataclass
class _Request:
    parent:tuple
    counts:object=None
    successor:object=None
    reference:object=None

@dataclass(frozen=True)
class InventoryCommit:
    content:object
    directory:tuple
    inventory:tuple

def domain(identity,codec):return _digest(b'ate-head-inventory-domain/1',_namespace(identity),_integer(codec,1))
def _key(ns):
    key=_namespace(ns)
    if len(key)>4096:raise StoreError('inventory namespace exceeds explicit key path')
    return key

def _head(h):
    if type(h) is not ManifestHead or type(h.seed) is not int or not -2**63<=h.seed<2**63 or type(h.next_incarnation_id) is not int or not 1<=h.next_incarnation_id<2**63:raise StoreIntegrityError('invalid inventory head')
    blobs=h.simulation_position,h.next_ids,h.namespace_inventory,h.namespace_counts
    if any(type(b) is not bytes for b in blobs):raise StoreIntegrityError('invalid head bytes')
    if sum(map(len,blobs))>MAX_METADATA_BYTES:raise StoreError('head inventory metadata exceeds explicit budget')
    codec=_ProjectionCodec(metadata=True)
    for b in blobs[:2]:codec.decode(b)
    names=codec.decode(h.namespace_inventory);counts=_namespace_counts(codec,h.namespace_counts)
    if type(names) is not tuple or any(type(n) is not str for n in names):raise StoreIntegrityError('invalid head namespace inventory')
    for n in names:_key(n)
    if names!=tuple(sorted(set(names))) or not set(counts)<=set(names):raise StoreIntegrityError('noncanonical or incomplete head inventory')
    return names,counts

def _encode(c):
    if type(c) is not InventoryCertificate or type(c.generation) is not int or not 0<=c.generation<2**63:raise StoreIntegrityError('invalid inventory certificate')
    names,counts=_head(c.head);m=OrderedSeekMap(None,domain(c.store_identity,c.codec_version));m._reference(c.root)
    if c.root.count!=len(names):raise StoreIntegrityError('head namespace/root count disagreement')
    h=c.head
    return json.dumps([c.store_identity,c.generation,c.codec_version,[h.simulation_position.hex(),h.next_ids.hex(),h.namespace_inventory.hex(),h.namespace_counts.hex(),h.seed,h.next_incarnation_id],c.root.digest.hex(),c.root.count],separators=(',',':'),ensure_ascii=False).encode()

def certificate_commitment(c):return _digest(b'ate-head-inventory-certificate/1',_encode(c))
def _member(d,ns,pair):
    return _digest(b'ate-head-inventory-member/1',d,_key(ns),_integer(pair[0]),_integer(pair[1]))

def _preflight(store):
    _node_schema(store.db)
    source._read_preflight(store,MAX_METADATA_BYTES)
    if 'lazy_identity_state_interval' not in store._interval_indexes:raise StoreError('inventory requires allocator interval index')
    _require_indexes(store.db,include_order=False,intervals=('lazy_identity_state_interval',))

def _schemas(store):
    _preflight(store)
    row=store.db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_inventory_generations' AND type='table'").fetchone()
    if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(_SCHEMA.lower().split()):raise StoreError('inventory requires verified construction')

def _physical_head(store,g):
    row=store._checked_head_row()
    if row[0]!=g:raise StoreConflictError('inventory requires current head')
    allocator=store._identity_state_at(g)[0];_check_allocator(store,g,allocator)
    h=ManifestHead(row[2],row[4],row[5],row[6],row[3],allocator);_head(h);return h

def _row_hash(c,parent,writer,token):return _digest(b'ate-head-inventory-row/1',certificate_commitment(c),parent or b'',writer.encode('ascii'),token)
def _write(store,c,*,parent=None,writer='',token=b''):
    e=certificate_commitment(c);store.db.execute('INSERT INTO ate_inventory_generations VALUES(?,?,?,?,?,?,?)',(c.generation,_encode(c),e,parent,writer,token,_row_hash(c,parent,writer,token)));return c,e

def _load(store,g):
    _schemas(store)
    row=store.db.execute("SELECT CASE WHEN typeof(certificate)='blob' AND length(certificate)<=? THEN certificate END,CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,CASE WHEN typeof(parent)='blob' AND length(parent)=32 THEN parent END,typeof(parent),CASE WHEN typeof(writer)='text' AND length(CAST(writer AS BLOB))<=4096 THEN writer END,CASE WHEN typeof(token)='blob' AND length(token)<=65536 THEN token END,CASE WHEN typeof(checksum)='blob' AND length(checksum)=32 THEN checksum END FROM ate_inventory_generations WHERE generation=?",(MAX_CERTIFICATE_BYTES,g)).fetchone()
    if row is None:raise StoreIntegrityError('missing inventory generation')
    raw,e,parent,pt,writer,token,checksum=row
    try:
        if type(raw) is not bytes or pt not in ('null','blob') or pt=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid inventory row')
        v=json.loads(raw);hv=v[3];h=ManifestHead(*(bytes.fromhex(b) for b in hv[:4]),*hv[4:]);c=InventoryCertificate(*v[:3],h,Root(bytes.fromhex(v[4]),v[5]))
        if len(v)!=6 or len(hv)!=6 or _encode(c)!=raw or (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,g,store.codec.version) or certificate_commitment(c)!=e or _row_hash(c,parent,writer,token)!=checksum:raise StoreIntegrityError('inventory row authority disagreement')
    except (ValueError,TypeError,IndexError,UnicodeError,AttributeError,RecursionError,OverflowError) as exc:raise StoreIntegrityError('invalid inventory encoding') from exc
    return (c,e),parent,writer,token

def bootstrap_inventory(store,pin):
    _require_closed_codec(store,allow_typed=True)
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('inventory construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        _preflight(store);g=store._require_pin(pin);h=_physical_head(store,g);_guard_construction(store,g,MAX_BODY_BYTES,MAX_METADATA_BYTES);source._audit_namespace_inventory(store,g);store.verify_all()
        names,counts=_head(h);m=OrderedSeekMap(store.db,domain(store.store_identity,store.codec.version));m.create_schema()
        root=m.build((_key(ns),_member(m.domain,ns,counts.get(ns,(0,0)))) for ns in names)
        c=InventoryCertificate(store.store_identity,g,store.codec.version,h,root);e=certificate_commitment(c)
        store.db.execute(_SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1));_schemas(store)
        if store.db.execute('SELECT 1 FROM ate_inventory_generations WHERE generation=?',(g,)).fetchone():
            if _load(store,g)[0]!=(c,e):raise StoreIntegrityError('cannot repair divergent inventory')
        else:_write(store,c)
        store.db.commit();return c,e
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False

def _authority(store,pin,c,e):
    _require_closed_codec(store,allow_typed=True)
    if type(e) is not bytes or len(e)!=32 or certificate_commitment(c)!=e:raise StoreIntegrityError('inventory expected authority disagreement')
    if (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version) or pin.store_identity!=store.store_identity:raise StoreConflictError('inventory context disagreement')

def _snapshot_checks(store,c,e):
    _schemas(store);head=int(store._checked_head_row()[0])
    if c.generation not in (head,head-1):raise StoreConflictError('inventory outside retained window')
    if _load(store,c.generation)[0]!=(c,e):raise StoreIntegrityError('inventory persisted authority disagreement')
    _check_allocator(store,c.generation,c.head.next_incarnation_id)
    if c.generation==head and _physical_head(store,head)!=c.head:raise StoreIntegrityError('inventory actual head disagreement')

def _entry(c,key,value):
    try:ns=key.decode('utf-8')
    except UnicodeError as exc:raise StoreIntegrityError('invalid inventory namespace encoding') from exc
    names,counts=_head(c.head);pair=counts.get(ns,(0,0))
    if ns not in names or _key(ns)!=key or value!=_member(domain(c.store_identity,c.codec_version),ns,pair):raise StoreIntegrityError('inventory selected descriptor disagreement')
    return ns,*pair

def read_inventory_namespace(store,pin,certificate,expected,namespace):
    c=certificate;_authority(store,pin,c,expected);key=_key(namespace)
    if store.db.in_transaction:raise StoreError('inventory read requires owned snapshot')
    with store.read_snapshot(pin,_preflight=lambda:_preflight(store)):
        _snapshot_checks(store,c,expected);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version));value=m.get(c.root,key)
        if value is None:
            if namespace in _head(c.head)[0]:raise StoreIntegrityError('inventory declared namespace missing')
            return None
        return _entry(c,key,value)

def read_inventory_namespaces(store,pin,certificate,expected,*,after=None,limit=128):
    c=certificate;_authority(store,pin,c,expected)
    if type(limit) is not int or not 1<=limit<=128 or after is not None and (type(after) is not bytes or len(after)>4096):raise StoreIntegrityError('invalid inventory page')
    if store.db.in_transaction:raise StoreError('inventory read requires owned snapshot')
    with store.read_snapshot(pin,_preflight=lambda:_preflight(store)):
        _snapshot_checks(store,c,expected);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version));rows=m.page(c.root,after=after,limit=limit+1)
        return InventoryPage(tuple(_entry(c,k,v) for k,v in rows[:limit]),rows[limit-1][0] if len(rows)>limit else None)

def _guard(store,request,versions,ordinary,segments):
    if type(request) is not _Request:raise StoreIntegrityError('invalid private inventory request')
    c,e=request.parent;_schemas(store)
    if _load(store,c.generation)[0]!=(c,e) or _physical_head(store,c.generation)!=c.head:raise StoreIntegrityError('inventory accepted head changed')
    counts=dict(_head(c.head)[1])
    for item in versions:
        if _auxiliary_namespace(item['namespace']):continue
        ns,key=item['namespace'],item['typed_key'];old=collection._order(store,c.generation,ns,key) is not None
        delta=-int(old) if item['change'].delete else int(not old)
        _bump_count(counts,ns,records=delta)
    for item in ordinary:
        ns,key=item['namespace'],item['typed_key'];old=store.db.execute('SELECT 1 FROM records WHERE namespace=? AND typed_key=?',(ns,key)).fetchone() is not None
        _bump_count(counts,ns,records=-int(old) if item['change'].delete else int(not old))
    for item in segments:_bump_count(counts,item['namespace'],segments=1)
    request.counts=counts
    if request.reference is not None:
        from .persistence_proof_reference_publish import _guard as guard_reference
        guard_reference(store,request.reference)

def _stage(store,request,g,writer,token):
    c,e=request.parent
    if _load(store,c.generation)[0]!=(c,e) or g!=c.generation+1 or not store.db.in_transaction:raise StoreIntegrityError('inventory successor context disagreement')
    h=_physical_head(store,g);names,counts=_head(h)
    if counts!=request.counts or h.next_incarnation_id<c.head.next_incarnation_id:raise StoreIntegrityError('inventory successor count/allocator transition disagreement')
    old_names,old_counts=_head(c.head);m=OrderedSeekMap(store.db,domain(c.store_identity,c.codec_version));root=c.root
    for ns in sorted(set(old_names)|set(names)):
        old=_member(m.domain,ns,old_counts.get(ns,(0,0))) if ns in old_names else None
        new=_member(m.domain,ns,counts.get(ns,(0,0))) if ns in names else None
        if old!=new:
            if m.get(root,_key(ns))!=old:raise StoreIntegrityError('inventory parent namespace path disagreement')
            root=m.set(root,_key(ns),new)
    child=InventoryCertificate(c.store_identity,g,c.codec_version,h,root);request.successor=_write(store,child,parent=e,writer=writer,token=token)
    if request.reference is not None:
        from .persistence_proof_reference_publish import _stage as stage_reference
        stage_reference(store,request.reference,g,writer,token,request.successor)

def _commit_inventory(store,pin,certificate,expected,directory_authority,content_authority,*,reference_request=None,**arguments):
    if any(k.startswith('_') for k in arguments):raise StoreError('private inventory arguments forbidden')
    _authority(store,pin,certificate,expected)
    if store.db.in_transaction:raise StoreError('inventory save requires owned operation')
    with store.read_snapshot(pin,_preflight=lambda:_preflight(store)):_snapshot_checks(store,certificate,expected)
    request=_Request((certificate,expected),reference=reference_request);result=directory.commit_directory(store,pin,*directory_authority,*content_authority,_inventory=request,**arguments);outcome=result.content.commit.outcome
    if outcome=='committed' and request.successor is None:raise StoreIntegrityError('missing inventory successor')
    return InventoryCommit(result.content,result.directory,request.successor if outcome=='committed' else request.parent if outcome=='not_committed' else ())

def commit_inventory(store,pin,certificate,expected,directory_authority,content_authority,**arguments):
    if any(k.startswith('_') or k=='reference_request' for k in arguments):raise StoreError('private inventory arguments forbidden')
    return _commit_inventory(store,pin,certificate,expected,directory_authority,content_authority,**arguments)


def resolve_inventory(store,pin,certificate,expected,directory_authority,content_authority,**arguments):
    if any(k.startswith('_') for k in arguments):raise StoreError('private inventory recovery arguments forbidden')
    _authority(store,pin,certificate,expected)
    if store.db.in_transaction:raise StoreError('inventory recovery requires owned operation')
    _schemas(store);result=directory.resolve_directory(store,pin,*directory_authority,*content_authority,**arguments);commit=result.content.commit
    if commit.outcome=='conflict':return InventoryCommit(result.content,result.directory,())
    with store.read_snapshot(commit.pin,_preflight=lambda:_preflight(store)):
        pair,parent,writer,token=_load(store,commit.generation)
        if commit.outcome=='not_committed':
            if pair!=(certificate,expected):raise StoreIntegrityError('inventory recovery parent disagreement')
        elif parent!=expected or writer!=pin.token or token!=store.codec.encode(arguments['commit_token']) or commit.generation!=certificate.generation+1:raise StoreIntegrityError('inventory recovery receipt disagreement')
        _snapshot_checks(store,*pair)
        return InventoryCommit(result.content,result.directory,pair)
