"""Durable bounded selected-graph facts; no native or complete World authority.

Descriptors bind exact positive/absent content paths and complete scoped
relations. Reuse carries a validated fact, never an unchecked payload.
"""
from dataclasses import dataclass
import json
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,CodecError
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_map import ProofMap
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_content import _namespace,_integer,version_key,record_key
from .persistence_proof_occurrence import OwnerScope,GroupScope
from .persistence_proof_query import QueryScope
from .persistence_proof_projection import _ProjectionCodec
from . import persistence_proof_reference_closure as closure
from . import persistence_proof_target as target
from . import persistence_proof_record as records

MAX_ROOTS=128
MAX_DEPENDENCIES=8192
MAX_DESCRIPTOR_BYTES=1048576
MAX_DESCRIPTOR_TOTAL=4*1048576
_SCHEMA='CREATE TABLE ate_reference_generations(generation INTEGER NOT NULL PRIMARY KEY,certificate BLOB NOT NULL,commitment BLOB NOT NULL,parent BLOB,writer TEXT NOT NULL,token BLOB NOT NULL,checksum BLOB NOT NULL) WITHOUT ROWID'
_DESCRIPTOR='CREATE TABLE ate_reference_descriptors(commitment BLOB PRIMARY KEY,raw BLOB NOT NULL) WITHOUT ROWID'
_KINDS=('list','map','set','sequence','frozen-list','frozen-map','record','nan-key','event-ids')

@dataclass(frozen=True)
class ReferenceCertificate:
    store_identity:str
    generation:int
    codec_version:int
    root:Root
    references:tuple
    components:tuple

@dataclass(frozen=True)
class ReferenceFact:
    kind:str
    incarnation:int
    targets:int
    edges:int
    immutable_targets:tuple
    graph_digest:bytes


def domain(identity,codec):return _digest(b'ate-reference-facts-domain/1',_namespace(identity),_integer(codec,1))
def _map(store):
    d=domain(store.store_identity,store.codec.version);nodes=ProofNodeStore(store.db)
    return ProofMap(d,lambda h:nodes.read(d,h),lambda h,b:nodes.write(d,h,b))

def _reference(pair):
    from .persistence_lazy_nested_history import HistoryReference
    from .persistence_record_headers import RecordReference
    from .persistence_nonreflexive_keys import NonreflexiveKeyReference
    from .persistence_event_id_reference import EventIdReference
    if type(pair) is not tuple or len(pair)!=2 or type(pair[0]) is not str or pair[0] not in _KINDS or type(pair[1]) is not int or not 1<=pair[1]<2**63:raise StoreIntegrityError('invalid reference proof root')
    k,i=pair
    return {'record':RecordReference,'nan-key':NonreflexiveKeyReference,'event-ids':EventIdReference}[k](i) if k in ('record','nan-key','event-ids') else HistoryReference(k,i)

def _key(pair):_reference(pair);return _ProjectionCodec().encode(pair)

def _encode(c):
    if type(c) is not ReferenceCertificate or type(c.generation) is not int or not 0<=c.generation<2**63:raise StoreIntegrityError('invalid reference certificate')
    ProofMap(domain(c.store_identity,c.codec_version),None,None)._reference(c.root)
    refs=c.references
    if type(refs) is not tuple or not 1<=len(refs)<=MAX_ROOTS or tuple(sorted(set(refs)))!=refs or c.root.count!=len(refs):raise StoreIntegrityError('invalid selected reference inventory')
    for r in refs:_reference(r)
    if type(c.components) is not tuple or len(c.components)!=4 or any(type(h) is not bytes or len(h)!=32 for h in c.components):raise StoreIntegrityError('invalid reference component authorities')
    return json.dumps([c.store_identity,c.generation,c.codec_version,c.root.digest.hex(),c.root.count,refs,[h.hex() for h in c.components]],ensure_ascii=False,separators=(',',':')).encode()

def certificate_commitment(c):return _digest(b'ate-reference-certificate/1',_encode(c))
def _row_hash(c,parent,writer,token):return _digest(b'ate-reference-generation-row/1',certificate_commitment(c),parent or b'',writer.encode('ascii'),token)
def _write(store,c,*,parent=None,writer='',token=b''):
    e=certificate_commitment(c);store.db.execute('INSERT INTO ate_reference_generations VALUES(?,?,?,?,?,?,?)',(c.generation,_encode(c),e,parent,writer,token,_row_hash(c,parent,writer,token)));return c,e

def _schemas(store):
    target._preflight(store,1048576)
    for sql in (_SCHEMA,_DESCRIPTOR):
        name=sql.split('(')[0].split()[2]
        row=store.db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name=? AND type='table'",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('reference schemas require verified construction')

def _load(store,g):
    _schemas(store)
    row=store.db.execute("SELECT CASE WHEN typeof(certificate)='blob' AND length(certificate)<=65536 THEN certificate END,CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,CASE WHEN typeof(parent)='blob' AND length(parent)=32 THEN parent END,typeof(parent),CASE WHEN typeof(writer)='text' AND length(CAST(writer AS BLOB))<=4096 THEN writer END,CASE WHEN typeof(token)='blob' AND length(token)<=65536 THEN token END,CASE WHEN typeof(checksum)='blob' AND length(checksum)=32 THEN checksum END FROM main.ate_reference_generations WHERE generation=?",(g,)).fetchone()
    if row is None:raise StoreIntegrityError('missing reference generation')
    raw,e,parent,pt,writer,token,checksum=row
    try:
        if type(raw) is not bytes or pt not in ('null','blob') or pt=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid reference generation row')
        v=json.loads(raw);c=ReferenceCertificate(*v[:3],Root(bytes.fromhex(v[3]),v[4]),tuple(tuple(p) for p in v[5]),tuple(bytes.fromhex(h) for h in v[6]))
        if len(v)!=7 or _encode(c)!=raw or (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,g,store.codec.version) or certificate_commitment(c)!=e or _row_hash(c,parent,writer,token)!=checksum:raise StoreIntegrityError('reference generation authority disagreement')
        return (c,e),parent,writer,token
    except (ValueError,TypeError,IndexError,AttributeError,UnicodeError,OverflowError,RecursionError) as exc:raise StoreIntegrityError('invalid reference certificate encoding') from exc

def _authority(store,pin,c,e):
    target._require_closed_codec(store)
    if type(e) is not bytes or len(e)!=32 or certificate_commitment(c)!=e:raise StoreIntegrityError('reference expected authority disagreement')
    if (c.store_identity,c.generation,c.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version) or pin.store_identity!=store.store_identity:raise StoreConflictError('reference context disagreement')

def _components(store,pin,ca,sa,ia,ra):
    target._pairs(store,pin,(ca,sa,ia));records._authority(store,pin,*ra)
    if len(sa[0].roots)!=6:raise StoreError('durable references require six-root scope authority')
    return tuple(pair[1] for pair in (ca,sa,ia,ra))

def _checked_components(store,ca,sa,ia,ra):
    for pair,load in ((ca,target.content._load_root),(sa,target.scope._load_root),(ia,target.inventory._load),(ra,records._load_root)):
        if load(store,pair[0].generation)[0]!=pair:raise StoreIntegrityError('reference component persisted authority disagreement')
    target.inventory._snapshot_checks(store,*ia)

def _dependency(store,ca,sa,ra,kind,ns,key):
    if kind==0:return target.content._map(store).get(ca[0].versions,version_key(ns,key))
    if kind==1:return records._map(store).get(ra[0].root,record_key(ns,key))
    if kind==2:return target.scope._map(store,key[0]).get(sa[0].roots[key[0]],key)
    raise StoreIntegrityError('invalid reference dependency kind')

def _descriptor(store,expected,budget):
    row=store.db.execute("SELECT CASE WHEN typeof(raw)='blob' THEN length(raw) END,CASE WHEN typeof(raw)='blob' AND length(raw)<=? THEN raw END FROM main.ate_reference_descriptors WHERE commitment=?",(min(MAX_DESCRIPTOR_BYTES,budget),expected)).fetchone()
    if row is None or type(row[0]) is not int or row[0]>min(MAX_DESCRIPTOR_BYTES,budget) or type(row[1]) is not bytes:raise StoreError('missing or oversized reference descriptor')
    raw=row[1]
    if _digest(b'ate-reference-descriptor/1',raw)!=expected:raise StoreIntegrityError('reference descriptor checksum disagreement')
    try:
        value=_ProjectionCodec(metadata=True).decode(raw)
        if type(value) is not tuple or len(value)!=10 or value[0]!='reference-facts/v1':raise StoreIntegrityError('invalid reference descriptor')
        _,kind,inc,targets,edges,frozen,digest,allocator,deps,root_pair=value
        _reference((kind,inc))
        if root_pair!=(kind,inc) or type(targets) is not int or not 1<=targets<=128 or type(edges) is not int or not 0<=edges<=4096 or type(digest) is not bytes or len(digest)!=32 or type(allocator) is not int or not inc<allocator<2**63:raise StoreIntegrityError('invalid reference fact summary')
        if type(frozen) is not tuple or any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not int or not 1<=p[0]<allocator or type(p[1]) is not bool for p in frozen) or tuple(sorted(set(frozen)))!=frozen:raise StoreIntegrityError('invalid immutable target summary')
        if type(deps) is not tuple or not 1<=len(deps)<=MAX_DEPENDENCIES:raise StoreError('reference dependency budget exceeded')
        keys=[]
        for d in deps:
            if type(d) is not tuple or len(d)!=4:raise StoreIntegrityError('invalid reference dependency')
            k,ns,key,h=d
            if type(k) is not int or k not in (0,1,2) or type(ns) is not str or type(key) is not bytes or len(key)>8192 or h is not None and (type(h) is not bytes or len(h)!=32):raise StoreIntegrityError('invalid reference dependency fields')
            if k==2:
                if ns!='':raise StoreIntegrityError('invalid scope dependency namespace')
                target.scope._parse_scope(key)
            else:_namespace(ns)
            keys.append(d[:3])
        if keys!=sorted(set(keys)) or _ProjectionCodec(metadata=True).encode(value)!=raw:raise StoreIntegrityError('noncanonical reference descriptor')
        return value,len(raw)
    except (CodecError,ValueError,TypeError,UnicodeError,IndexError,AttributeError,RecursionError) as exc:raise StoreIntegrityError('invalid reference descriptor encoding') from exc

def _produce(store,pin,reference,ca,sa,ia,ra):
    graph,s=closure._read_checked(store,pin,reference,ca,sa,ia,record_authority=ra)
    keys=set(s.dependencies);scopes={OwnerScope('world.event_ids',s.codec.encode(0))};nodes=[]
    for n in graph.targets:
        t=n.incoming.target;inc=t.incarnation
        scopes.update((GroupScope(inc),target.scope.ChildScope(inc),target.scope.SequenceScope(inc),QueryScope(target.catalog.LINK_NAMESPACE,'incarnation',s.codec.encode(inc))))
        scopes.update(OwnerScope(o.namespace,o.typed_key) for o in n.incoming.owners)
        scopes.update(OwnerScope(ns,s.codec.encode(key)) for ns,key in n.child_locators if ns in closure.AUXILIARY_OWNER_FAMILIES)
        owners=tuple((o.namespace,o.typed_key,o.storage_kind,o.source.payload,getattr(o.source,'memberships',None)) for o in n.incoming.owners)
        occurrences=tuple((o.namespace,o.typed_key,o.path,o.incarnation_id) for o in n.incoming.group.occurrences)
        nodes.append((inc,t.kind,t.namespace,t.typed_key,t.payload,n.members,n.member_counts,owners,occurrences,n.incoming.group.links,n.incoming.group.anchor))
    keys.update((2,'',target.scope._scope_key(sc)) for sc in scopes)
    if len(keys)>MAX_DEPENDENCIES:raise StoreError('reference dependency budget exceeded')
    deps=tuple((*k,_dependency(store,ca,sa,ra,*k)) for k in sorted(keys))
    edges=tuple((e.source_incarnation,e.namespace,e.typed_key,e.path,e.target_incarnation,e.target_kind) for e in graph.edges)
    digest=_digest(b'ate-reference-graph/1',s.codec.encode((tuple(nodes),edges,graph.immutable_targets)))
    kind,inc=target._reference(reference)
    value=('reference-facts/v1',kind,inc,len(nodes),len(edges),graph.immutable_targets,digest,ia[0].head.next_incarnation_id,deps,(kind,inc))
    raw=s.codec.encode(value)
    if len(raw)>MAX_DESCRIPTOR_BYTES:raise StoreError('reference descriptor exceeds byte budget')
    h=_digest(b'ate-reference-descriptor/1',raw)
    store.db.execute('INSERT OR IGNORE INTO main.ate_reference_descriptors VALUES(?,?)',(h,raw))
    checked,size=_descriptor(store,h,MAX_DESCRIPTOR_BYTES)
    if checked!=value:raise StoreIntegrityError('conflicting reference descriptor')
    return h,size

def _fact(value):return ReferenceFact(*value[1:7])

def bootstrap_reference_proofs(store,pin,references,content_authority,scope_authority,inventory_authority,*,record_authority):
    ca,sa,ia,ra=content_authority,scope_authority,inventory_authority,record_authority
    components=_components(store,pin,ca,sa,ia,ra)
    if type(references) is not tuple or not 1<=len(references)<=MAX_ROOTS:raise StoreError('selected reference inventory exceeds budget')
    refs=tuple(sorted(target._reference(r) for r in references))
    if len(set(refs))!=len(refs):raise StoreIntegrityError('duplicate selected root')
    if store.db.in_transaction or store._active_read_transaction:raise StoreError('reference construction requires owned transaction')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        for sql in (_SCHEMA,_DESCRIPTOR):store.db.execute(sql.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1))
        _schemas(store)
        with store.read_snapshot(pin,_preflight=lambda:target._preflight(store,1048576)):
            if store._checked_head_row()[0]!=pin.captured_head:raise StoreConflictError('reference construction requires current head')
            _checked_components(store,ca,sa,ia,ra);m=_map(store);root=m.empty;remaining=MAX_DESCRIPTOR_TOTAL
            for pair in refs:
                h,n=_produce(store,pin,_reference(pair),ca,sa,ia,ra);remaining-=n
                if remaining<0:raise StoreError('reference aggregate descriptor budget exceeded')
                root=m.set(root,_key(pair),h)
            c=ReferenceCertificate(store.store_identity,pin.captured_head,store.codec.version,root,refs,components)
            if store.db.execute('SELECT 1 FROM main.ate_reference_generations WHERE generation=?',(c.generation,)).fetchone():
                if _load(store,c.generation)[0]!=(c,certificate_commitment(c)):raise StoreIntegrityError('cannot repair divergent reference generation')
                result=c,certificate_commitment(c)
            else:result=_write(store,c)
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False

def read_reference_certificate(store,pin,certificate,expected,reference):
    c=certificate;_authority(store,pin,c,expected);pair=target._reference(reference)
    if store.db.in_transaction:raise StoreError('reference read requires owned snapshot')
    with store.read_snapshot(pin,_preflight=lambda:_schemas(store)):
        if _load(store,pin.captured_head)[0]!=(c,expected):raise StoreIntegrityError('reference persisted authority disagreement')
        ca=target.content._load_root(store,c.generation)[0];sa=target.scope._load_root(store,c.generation)[0]
        ia=target.inventory._load(store,c.generation)[0];ra=records._load_root(store,c.generation)[0]
        if _components(store,pin,ca,sa,ia,ra)!=c.components:raise StoreIntegrityError('reference stored component bindings disagree')
        _checked_components(store,ca,sa,ia,ra)
        h=_map(store).get(c.root,_key(pair))
        if h is None:
            if pair in c.references:raise StoreIntegrityError('selected reference missing')
            return None
        if pair not in c.references:raise StoreIntegrityError('unselected reference surplus')
        value,_=_descriptor(store,h,MAX_DESCRIPTOR_TOTAL)
        if value[-1]!=pair:raise StoreIntegrityError('selected reference descriptor mismatch')
        return _fact(value)
