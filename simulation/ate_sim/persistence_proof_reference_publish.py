"""Verified selected-graph transitions inside the existing inventory writer."""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import GenerationPin
from . import persistence_proof_reference as reference
from . import persistence_proof_inventory as inventory
from . import persistence_proof_publication as content
from . import persistence_proof_scope as scope
from . import persistence_proof_record as records

@dataclass
class _Request:
    store:object
    pin:object
    parent:tuple
    authorities:tuple
    token:bytes
    epoch:int
    successor:object=None
    rebuilt:tuple=()
    reused:tuple=()
    guarded:bool=False

@dataclass(frozen=True)
class ReferenceCommit:
    inventory:object
    reference:tuple
    rebuilt:tuple=()
    reused:tuple=()


def _check(store,r):
    if type(r) is not _Request or r.store is not store:raise StoreIntegrityError('invalid private reference request')
    reference._authority(store,r.pin,*r.parent)
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=r.epoch:raise StoreConflictError('external write invalidated reference parent')
    if type(r.token) is not bytes or len(r.token)>65536:raise StoreError('reference commit token exceeds budget')
    if reference._components(store,r.pin,*r.authorities)!=r.parent[0].components:raise StoreIntegrityError('reference parent component binding disagreement')


def _guard(store,r):
    _check(store,r)
    if not store.db.in_transaction:raise StoreError('reference guard requires existing writer')
    if reference._load(store,r.pin.captured_head)[0]!=r.parent:raise StoreIntegrityError('reference accepted parent changed')
    reference._checked_components(store,*r.authorities);r.guarded=True


def _stage(store,r,g,writer,token,inventory_pair):
    _check(store,r)
    if not r.guarded or not store.db.in_transaction or g!=r.pin.captured_head+1 or writer!=r.pin.token or token!=r.token:raise StoreIntegrityError('reference successor writer context disagreement')
    if reference._load(store,r.pin.captured_head)[0]!=r.parent:raise StoreIntegrityError('reference parent changed during publication')
    pin=GenerationPin(writer,store.store_identity,g)
    ca=content._load_root(store,g)[0];sa=scope._load_root(store,g)[0];ra=records._load_root(store,g)[0];ia=inventory_pair
    components=reference._components(store,pin,ca,sa,ia,ra)
    m=reference._map(store);root=r.parent[0].root;remaining=reference.MAX_DESCRIPTOR_TOTAL;rebuilt=[];reused=[];cache={}
    # The existing writer owns this transaction. Checked nested readers borrow
    # it without BEGIN, rollback, native restoration or an independent publisher.
    active=store._active_read_transaction;store._active_read_transaction=True
    try:
        with store.read_snapshot(pin,_preflight=lambda:reference._schemas(store)):
            reference._checked_components(store,ca,sa,ia,ra)
            for pair in r.parent[0].references:
                key=reference._key(pair);old=m.get(root,key)
                value,size=reference._descriptor(store,old,remaining);remaining-=size
                if value[-1]!=pair:raise StoreIntegrityError('reference selected dependency descriptor mismatch')
                changed=value[7]!=ia[0].head.next_incarnation_id
                for kind,ns,dep,wanted in value[8]:
                    marker=kind,ns,dep
                    if marker not in cache:cache[marker]=reference._dependency(store,ca,sa,ra,*marker)
                    changed=(cache[marker]!=wanted) or changed
                if changed:
                    successor,size=reference._produce(store,pin,reference._reference(pair),ca,sa,ia,ra)
                    # Charge both parent and replacement descriptors to bound
                    # temporary data, even when their immutable hashes coincide.
                    remaining-=size
                    if remaining<0:raise StoreError('reference aggregate descriptor budget exceeded')
                    if successor!=old:root=m.set(root,key,successor)
                    rebuilt.append(pair)
                else:reused.append(pair)
            child=reference.ReferenceCertificate(store.store_identity,g,store.codec.version,root,r.parent[0].references,components)
            r.successor=reference._write(store,child,parent=r.parent[1],writer=writer,token=token)
            r.rebuilt,r.reused=tuple(rebuilt),tuple(reused)
    finally:store._active_read_transaction=active


def commit_reference_proofs(store,pin,certificate,expected,directory_authority,content_authority,inventory_authority,*,scope_authority,record_authority,commit_token,**arguments):
    if any(k.startswith('_') for k in arguments):raise StoreError('private reference arguments forbidden')
    reference._authority(store,pin,certificate,expected)
    authorities=content_authority,scope_authority,inventory_authority,record_authority
    if reference._components(store,pin,*authorities)!=certificate.components:raise StoreIntegrityError('reference component arguments disagree')
    if store.db.in_transaction:raise StoreError('reference save requires owned operation')
    with store.read_snapshot(pin,_preflight=lambda:reference._schemas(store)):
        if reference._load(store,pin.captured_head)[0]!=(certificate,expected):raise StoreIntegrityError('reference parent disagreement')
        reference._checked_components(store,*authorities);epoch=store.db.execute('PRAGMA data_version').fetchone()[0]
    request=_Request(store,pin,(certificate,expected),authorities,store.codec.encode(commit_token),epoch)
    result=inventory._commit_inventory(store,pin,*inventory_authority,directory_authority,content_authority,reference_request=request,
        scope_authority=scope_authority,record_authority=record_authority,commit_token=commit_token,**arguments)
    outcome=result.content.commit.outcome
    if outcome=='committed' and request.successor is None:raise StoreIntegrityError('missing reference successor')
    return ReferenceCommit(result,request.successor if outcome=='committed' else request.parent if outcome=='not_committed' else (),request.rebuilt,request.reused)


def resolve_reference_commit(store,pin,certificate,expected,directory_authority,content_authority,inventory_authority,*,scope_authority,record_authority,commit_token):
    reference._authority(store,pin,certificate,expected)
    if reference._components(store,pin,content_authority,scope_authority,inventory_authority,record_authority)!=certificate.components:raise StoreIntegrityError('reference recovery parent bindings disagree')
    if store.db.in_transaction:raise StoreError('reference recovery requires owned operation')
    reference._schemas(store)
    result=inventory.resolve_inventory(store,pin,*inventory_authority,directory_authority,content_authority,scope_authority=scope_authority,record_authority=record_authority,commit_token=commit_token)
    commit=result.content.commit
    if commit.outcome=='conflict':return ReferenceCommit(result,())
    with store.read_snapshot(commit.pin,_preflight=lambda:reference._schemas(store)):
        pair,parent,writer,token=reference._load(store,commit.generation)
        if commit.outcome=='not_committed':
            if pair!=(certificate,expected):raise StoreIntegrityError('reference recovery parent disagreement')
        elif parent!=expected or writer!=pin.token or token!=store.codec.encode(commit_token) or commit.generation!=certificate.generation+1:raise StoreIntegrityError('reference recovery exact receipt disagreement')
        v=result.content
        ca=(v.certificate,v.commitment);sa=(v.scope.certificate,v.scope.commitment);ra=(v.scope.record.certificate,v.scope.record.commitment)
        if reference._components(store,commit.pin,ca,sa,result.inventory,ra)!=pair[0].components:raise StoreIntegrityError('reference recovered component bindings disagree')
        reference._checked_components(store,ca,sa,result.inventory,ra)
        return ReferenceCommit(result,pair)
