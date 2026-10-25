"""Inactive complete collection-directory successor in the existing save transaction.

This does not supply save-head namespace inventory, target topology or World
manifest authority. Callers name at most 128 touched lazy namespaces.
"""
from dataclasses import dataclass
import json
from .incremental_store import StoreError,StoreIntegrityError
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_proof_collection_directory as directory
from . import persistence_proof_collection as collection
from . import persistence_proof_collection_publish as publication
from .persistence_proof_publication import resolve_content_commit

_SCHEMA='CREATE TABLE ate_directory_generations(generation INTEGER NOT NULL PRIMARY KEY,certificate BLOB NOT NULL,commitment BLOB NOT NULL,parent BLOB,writer TEXT NOT NULL,token BLOB NOT NULL,checksum BLOB NOT NULL) WITHOUT ROWID'

def _schema(db):
    directory._source_schemas(db);directory._source_indexes(db);directory._schemas(db)
    row=db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE name='ate_directory_generations' AND type='table'").fetchone()
    if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(_SCHEMA.lower().split()):raise StoreError('directory publication requires verified construction')

def _encode(c):return json.dumps([c.store_identity,c.generation,c.codec_version,c.root.digest.hex(),c.root.count],separators=(',',':'),ensure_ascii=False).encode()
def _hash(c,parent,writer,token):return _digest(b'ate-directory-row/1',directory.certificate_commitment(c),parent or b'',writer.encode('ascii'),token)
def _write(store,c,*,parent=None,writer='',token=b''):
    e=directory.certificate_commitment(c)
    store.db.execute('INSERT INTO ate_directory_generations VALUES(?,?,?,?,?,?,?)',(c.generation,_encode(c),e,parent,writer,token,_hash(c,parent,writer,token)))
    return c,e

def _load(store,g):
    _schema(store.db)
    row=store.db.execute("SELECT CASE WHEN typeof(certificate)='blob' AND length(certificate)<=16384 THEN certificate END,CASE WHEN typeof(commitment)='blob' AND length(commitment)=32 THEN commitment END,CASE WHEN typeof(parent)='blob' AND length(parent)=32 THEN parent END,typeof(parent),CASE WHEN typeof(writer)='text' AND length(CAST(writer AS BLOB))<=4096 THEN writer END,CASE WHEN typeof(token)='blob' AND length(token)<=65536 THEN token END,CASE WHEN typeof(checksum)='blob' AND length(checksum)=32 THEN checksum END FROM ate_directory_generations WHERE generation=?",(g,)).fetchone()
    if row is None:raise StoreIntegrityError('missing directory generation')
    raw,e,parent,pt,writer,token,checksum=row
    try:
        if type(raw) is not bytes or pt not in ('null','blob') or pt=='blob' and parent is None or type(writer) is not str or type(token) is not bytes:raise StoreIntegrityError('invalid directory row')
        v=json.loads(raw);c=directory.CollectionDirectoryCertificate(*v[:3],Root(bytes.fromhex(v[3]),v[4]))
        if len(v)!=5 or _encode(c)!=raw or c.generation!=g or c.store_identity!=store.store_identity or c.codec_version!=store.codec.version or directory.certificate_commitment(c)!=e or _hash(c,parent,writer,token)!=checksum:raise StoreIntegrityError('directory row authority disagreement')
    except (ValueError,TypeError,IndexError,UnicodeError,AttributeError,RecursionError,OverflowError) as exc:raise StoreIntegrityError('invalid directory encoding') from exc
    return (c,e),parent,writer,token

def persist_bootstrap(store,c):
    store.db.execute(_SCHEMA.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1));_schema(store.db)
    if store.db.execute('SELECT 1 FROM ate_directory_generations WHERE generation=?',(c.generation,)).fetchone():
        if _load(store,c.generation)[0]!=(c,directory.certificate_commitment(c)):raise StoreIntegrityError('cannot repair divergent directory generation')
    else:_write(store,c)

@dataclass
class _DirectoryRequest:
    parent:tuple
    inventory:object=None
    successor:object=None

@dataclass(frozen=True)
class DirectoryCommit:
    content:object
    directory:tuple

def _parents(store,pin,authority,namespaces):
    c,e=authority;directory._preflight(store,pin,c,e,1048576)
    if type(namespaces) is not tuple or len(namespaces)>128 or any(type(ns) is not str for ns in namespaces) or len(set(namespaces))!=len(namespaces):raise StoreError('invalid bounded touched namespace inventory')
    with store.read_snapshot(pin,_preflight=lambda:directory._read_preflight(store,1048576)):
        if _load(store,c.generation)[0]!=authority:raise StoreIntegrityError('directory parent row changed')
        pairs=[]
        for ns in namespaces:
            pair=directory.read_collection_namespace(store,pin,*authority,ns)
            if pair is None:
                root=OrderedSeekMap(None,collection.domain(c.store_identity,c.codec_version,ns)).empty
                child=collection.CollectionCertificate(c.store_identity,c.generation,c.codec_version,ns,False,0,0,root)
                pair=child,collection.certificate_commitment(child)
            pairs.append(pair)
        return tuple(pairs)

def _guard(store,r,versions,ordinary,segments):
    if type(r.directory) is not _DirectoryRequest:raise StoreIntegrityError('invalid private directory request')
    c,e=r.directory.parent
    directory._read_preflight(store,1048576)
    if _load(store,c.generation)[0]!=(c,e):raise StoreIntegrityError('directory parent row changed')
    for parent,expected in r.pairs:
        actual=directory._lookup(store,c,parent.namespace)
        if actual is None:
            empty=OrderedSeekMap(None,collection.domain(c.store_identity,c.codec_version,parent.namespace)).empty
            if parent.declared or parent.root!=empty:raise StoreIntegrityError('directory absence certificate disagreement')
        elif actual!=(parent,expected):raise StoreIntegrityError('directory selected parent disagreement')
    if r.directory.inventory is not None:
        from .persistence_proof_inventory import _guard as guard_inventory
        guard_inventory(store,r.directory.inventory,versions,ordinary,segments)

def _stage(store,r,g,token):
    c,e=r.directory.parent
    if _load(store,c.generation)[0]!=(c,e):raise StoreIntegrityError('directory parent changed during publication')
    m=OrderedSeekMap(store.db,directory.domain(c.store_identity,c.codec_version));root=c.root
    for child,expected in r.successor:
        key=directory._key(child.namespace)
        if child.declared:root=m.set(root,key,directory._persist(store,m.domain,key,child))
        elif m.get(root,key) is not None:raise StoreIntegrityError('declared namespace cannot disappear')
    child=directory.CollectionDirectoryCertificate(c.store_identity,g,c.codec_version,root)
    r.directory.successor=_write(store,child,parent=e,writer=r.pin.token,token=token)
    if r.directory.inventory is not None:
        from .persistence_proof_inventory import _stage as stage_inventory
        stage_inventory(store,r.directory.inventory,g,r.pin.token,token)

def commit_directory(store,pin,certificate,expected,content_certificate,content_expected,*,namespaces,commit_token,_inventory=None,**arguments):
    if any(k.startswith('_') for k in arguments):raise StoreError('private directory arguments forbidden')
    if store.db.in_transaction:raise StoreError('directory save requires owned operation')
    authority=certificate,expected;pairs=_parents(store,pin,authority,namespaces);request=_DirectoryRequest(authority,inventory=_inventory)
    result=publication.commit_collections(store,pin,pairs,content_certificate,content_expected,commit_token=commit_token,_directory=request,**arguments)
    outcome=result.content.commit.outcome
    if outcome=='committed' and request.successor is None:raise StoreIntegrityError('missing directory successor')
    return DirectoryCommit(result.content,request.successor if outcome=='committed' else authority if outcome=='not_committed' else ())

def resolve_directory(store,pin,certificate,expected,content_certificate,content_expected,*,commit_token,**arguments):
    if any(k.startswith('_') for k in arguments):raise StoreError('private directory recovery arguments forbidden')
    if store.db.in_transaction:raise StoreError('directory recovery requires owned operation')
    directory._preflight(store,pin,certificate,expected,1048576)
    directory._read_preflight(store,1048576);_schema(store.db)
    content=resolve_content_commit(store,pin,content_certificate,content_expected,commit_token=commit_token,**arguments);result=content.commit
    if result.outcome=='conflict':return DirectoryCommit(content,())
    with store.read_snapshot(result.pin,_preflight=lambda:directory._read_preflight(store,1048576)):
        pair,parent,writer,token=_load(store,result.generation)
        if result.outcome=='not_committed':
            if pair!=(certificate,expected):raise StoreIntegrityError('directory recovery parent disagreement')
        elif parent!=expected or writer!=pin.token or token!=store.codec.encode(commit_token) or result.generation!=certificate.generation+1:raise StoreIntegrityError('directory recovery receipt disagreement')
        return DirectoryCommit(content,pair)
