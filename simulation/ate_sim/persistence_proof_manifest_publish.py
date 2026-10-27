"""Audited seven-root World manifests; ordinary World admission stays gated."""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import GenerationPin
from .persistence_proof_generation import GenerationManifest,ManifestReceipt,manifest_commitment,encode_manifest,read_generation_manifest,validate_successor
from .persistence_proof_nodes import Root
from . import persistence_proof_world as world
from . import persistence_proof_reference as reference
from . import persistence_proof_inventory as inventory
from . import persistence_proof_scope as scope
from . import persistence_proof_publication as content
from . import persistence_proof_record as records
from . import persistence_proof_directory_publish as directory

_SCHEMA='CREATE TABLE ate_generation_manifests(generation INTEGER PRIMARY KEY,commitment BLOB NOT NULL,manifest BLOB NOT NULL)'
_CONTEXT='CREATE TABLE ate_world_proof_contexts(generation INTEGER PRIMARY KEY,facts BLOB NOT NULL)'


def _schemas(store):
    reference.target._preflight(store,1048576)
    for sql in (_SCHEMA,_CONTEXT):
        name=sql.split('(')[0].split()[2];row=store.db.execute("SELECT CASE WHEN typeof(sql)='text' AND length(CAST(sql AS BLOB))<=4096 THEN sql END FROM main.sqlite_schema WHERE type='table' AND name=?",(name,)).fetchone()
        if row is None or type(row[0]) is not str or ''.join(row[0].lower().split())!=''.join(sql.lower().split()):raise StoreError('World manifest schemas require verified construction')


def _pairs(store,g):
    return content._load_root(store,g)[0],scope._load_root(store,g)[0],inventory._load(store,g)[0],records._load_root(store,g)[0],directory._load(store,g)[0]


def _manifest(store,g,roots,parent=None,writer=None,token=None):
    meta=dict(store.db.execute("SELECT key,value FROM store_metadata WHERE key IN ('format_version','simulation_schema','rules_id')"))
    head=inventory._physical_head(store,g)
    receipt=None
    if g:
        row=store.db.execute('SELECT commit_token,generation,parent_generation,outcome,row_checksum FROM pin_receipts WHERE pin_token=?',(writer,)).fetchone()
        if row is None or row[:4]!=(token,g,g-1,'committed'):raise StoreIntegrityError('World manifest lost exact writer receipt')
        receipt=ManifestReceipt(writer,token,row[4])
    return GenerationManifest(store.store_identity,g,parent,meta['format_version'],store.codec.version,meta['simulation_schema'],meta['rules_id'],head,roots,receipt)


def _write(store,value,facts):
    expected=manifest_commitment(value)
    store.db.execute('INSERT INTO ate_generation_manifests VALUES(?,?,?)',(value.generation,expected,encode_manifest(value)))
    store.db.execute('INSERT INTO ate_world_proof_contexts VALUES(?,?)',(value.generation,store.codec.encode(tuple((r.digest,r.count) for r in facts))))
    return value,expected


def _load(store,pin,pair):
    value=read_generation_manifest(store,pin,pair[1])
    if value!=pair[0]:raise StoreIntegrityError('World manifest accepted value disagreement')
    ca,sa,ia,ra,da=_pairs(store,pin.captured_head)
    reference._checked_components(store,ca,sa,ia,ra)
    row=store.db.execute("SELECT CASE WHEN typeof(facts)='blob' AND length(facts)<=4096 THEN facts END FROM ate_world_proof_contexts WHERE generation=?",(pin.captured_head,)).fetchone()
    if row is None or type(row[0]) is not bytes:raise StoreIntegrityError('missing World proof context')
    raw=reference._ProjectionCodec(metadata=True).decode(row[0])
    if type(raw) is not tuple or len(raw)!=5 or any(type(p) is not tuple or len(p)!=2 for p in raw):raise StoreIntegrityError('invalid World proof context')
    facts=tuple(Root(*p) for p in raw)
    topo=world._composite(store,b'topology',(*sa[0].roots[:2],*sa[0].roots[4:],*facts[:2]),persist=False);query=world._composite(store,b'queries',(*sa[0].roots[2:4],facts[2]),persist=False)
    orders=world._composite(store,b'orders',(da[0].root,facts[3],facts[4],sa[0].roots[2]),persist=False)
    actual=(ca[0].versions,ra[0].root,topo,query,orders,ca[0].events,ia[0].root)
    if actual!=value.roots:raise StoreIntegrityError('World manifest mixed component/fact authority')
    return (ca,sa,ia,ra,da),facts


def bootstrap_world_manifest(store,pin,content_authority,scope_authority,inventory_authority,record_authority,directory_authority):
    reference._components(store,pin,content_authority,scope_authority,inventory_authority,record_authority)
    if pin.captured_head!=0:raise StoreError('World proof genesis requires explicit new-identity generation0 copy')
    if store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()!=('7',):raise StoreError('World genesis requires fenced proof format')
    if store.db.in_transaction:raise StoreError('World manifest construction requires owned operation')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        for sql in (_SCHEMA,_CONTEXT):store.db.execute(sql.replace('CREATE TABLE','CREATE TABLE IF NOT EXISTS',1))
        _schemas(store)
        with store.read_snapshot(pin,_preflight=lambda:reference.target._preflight(store,1048576)):
            proof=world._audit_world(store,pin,content_authority,scope_authority,inventory_authority,record_authority,directory_authority)
            result=_write(store,_manifest(store,0,proof.roots),proof.facts)
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False


@dataclass
class _Request:
    store:object
    pin:object
    parent:tuple
    pairs:tuple
    facts:tuple
    token:bytes
    epoch:int
    guarded:bool=False
    may_reuse:bool=False
    value_only:bool=False
    successor:object=None
    reaudited:bool=False

@dataclass(frozen=True)
class WorldManifestCommit:
    commit:object
    manifest:tuple
    reaudited:bool=False


def _guard(store,r,versions,ordinary,segments):
    if type(r) is not _Request or r.store is not store or not store.db.in_transaction:raise StoreIntegrityError('invalid private World manifest request')
    if store.db.execute('PRAGMA data_version').fetchone()[0]!=r.epoch:raise StoreConflictError('external write invalidated World manifest parent')
    from .persistence_schema import ROOT_FIELDS
    from .persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
    scalars={root+'.'+field for root,fields in ROOT_FIELDS.items() for field,kind in fields.items() if kind=='int'}
    allowed={(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY)}
    r.may_reuse=not versions and not segments and all(not i['change'].delete and (i['namespace'],i['change'].key) in allowed for i in ordinary)
    # Immutable snapshots/atoms retain their content at a stable incarnation.
    from .persistence_proof_world import HISTORY,PAGE_NAMESPACE,ENTRY_NAMESPACE,RECORDS,NAN
    from .persistence_history_types import NAMESPACE as TYPES
    from .persistence_proof_content import version_key
    ca=r.pairs[0];codec=store.codec
    for item in versions:
        ns,key=item['namespace'],item['change'].key
        if ns not in (HISTORY,PAGE_NAMESPACE,ENTRY_NAMESPACE,RECORDS,NAN,TYPES) or item['change'].delete:continue
        old=content._source_version(store,r.pin.captured_head,ns,item['typed_key'])
        frozen=ns==NAN and old is not None
        if ns==RECORDS and old is not None:
            from .persistence_record_headers import checked_record_header
            state=checked_record_header(codec.decode(old.payload))[2];frozen=state is not None and state[0]
        if ns in (HISTORY,PAGE_NAMESPACE,ENTRY_NAMESPACE,TYPES):
            inc=key[0] if ns in (PAGE_NAMESPACE,ENTRY_NAMESPACE) else key
            parent=content._source_version(store,r.pin.captured_head,HISTORY,codec.encode(inc))
            if parent is not None:
                d=codec.decode(parent.payload);frozen=type(d) is tuple and type(d[0]) is str and d[0].startswith('frozen-')
        if frozen and (old is None or old.payload!=item['payload'] or old.memberships!=item['memberships_blob']):raise StoreIntegrityError('manifest transition cannot edit an immutable backing')
    from .persistence_proof_world_value import validate_value_transition,validate_lease_updates
    validate_lease_updates(store,r,versions)
    r.value_only=validate_value_transition(store,r,versions,ordinary,segments)
    r.guarded=True


def _check_head(store,pin,record_pair):
    from .persistence_proof_record import read_record_proof_bytes
    h=inventory._physical_head(store,pin.captured_head);codec=store.codec
    def value(ns):
        raw=read_record_proof_bytes(store,pin,*record_pair,ns,codec.encode(0),expected_record_schema=1,max_bytes=1048576)
        if raw is None:raise StoreIntegrityError('World manifest lacks head scalar source')
        v=codec.decode(raw.payload)
        if type(v) is not tuple or len(v)!=2 or type(v[0]) is not int or v[0]!=0 or type(v[1]) is not int:raise StoreIntegrityError('World head scalar must have exact ordinal/integer envelope')
        return v[1]
    if h.seed!=value('world.seed') or h.simulation_position!=codec.encode(value('world.year')) or codec.decode(h.next_ids)!={name:value('world.'+name) for name in ('next_person','next_household','next_settlement','next_event')}:raise StoreIntegrityError('World manifest head disagrees with authoritative scalar sources')


def _stage(store,r,g,writer,token,inventory_pair):
    if type(r) is not _Request or not r.guarded or r.store is not store or writer!=r.pin.token or token!=r.token or g!=r.pin.captured_head+1:raise StoreIntegrityError('World manifest successor context disagreement')
    parent,expected=r.parent
    row=store.db.execute('SELECT commitment,manifest FROM ate_generation_manifests WHERE generation=?',(parent.generation,)).fetchone()
    if row!=(expected,encode_manifest(parent)):raise StoreIntegrityError('World manifest parent changed during writer')
    pin=GenerationPin(writer,store.store_identity,g);ca,sa,ia,ra,da=_pairs(store,g)
    active=store._active_read_transaction;store._active_read_transaction=True
    try:
        with store.read_snapshot(pin,_preflight=lambda:_schemas(store)):
            oldca,oldsa,oldia,oldra,oldda=r.pairs
            reuse=r.may_reuse and ca[0].versions==oldca[0].versions and ca[0].events==oldca[0].events and sa[0].roots==oldsa[0].roots and sa[0].next_incarnation_id==oldsa[0].next_incarnation_id and da[0].root==oldda[0].root
            structural=(sa[0].roots[:2]==oldsa[0].roots[:2] and sa[0].roots[4:]==oldsa[0].roots[4:]
                and sa[0].next_incarnation_id==oldsa[0].next_incarnation_id and da[0].root==oldda[0].root
                and ca[0].versions.count==oldca[0].versions.count and ca[0].events==oldca[0].events
                and ia[0].head.namespace_inventory==oldia[0].head.namespace_inventory and ia[0].head.namespace_counts==oldia[0].head.namespace_counts)
            reuse=reuse or r.value_only and structural
            oldh=parent.head;newh=ia[0].head
            if not reuse or r.value_only and not r.may_reuse or (newh.seed,newh.simulation_position,newh.next_ids)!=(oldh.seed,oldh.simulation_position,oldh.next_ids):_check_head(store,pin,ra)
            if reuse:
                facts=r.facts;topo=world._composite(store,b'topology',(*sa[0].roots[:2],*sa[0].roots[4:],*facts[:2]));query=world._composite(store,b'queries',(*sa[0].roots[2:4],facts[2]))
                orders=world._composite(store,b'orders',(da[0].root,facts[3],facts[4],sa[0].roots[2]))
                roots=(ca[0].versions,ra[0].root,topo,query,orders,ca[0].events,ia[0].root)
            else:
                proof=world._audit_world(store,pin,ca,sa,ia,ra,da);roots,facts=proof.roots,proof.facts;r.reaudited=True
            child=_manifest(store,g,roots,expected,writer,token);e=manifest_commitment(child);validate_successor(parent,expected,child,e,token)
            r.successor=_write(store,child,facts)
    finally:store._active_read_transaction=active


def commit_world_manifest(store,pin,certificate,expected,*,commit_token,version_changes,changes,new_segments,metadata,identity_changes=(),checkpoint=False,**arguments):
    import re
    from .incremental_store import RecordChange
    from .persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
    if type(checkpoint) is not bool:raise StoreIntegrityError('invalid World checkpoint option')
    if any(k.startswith('_') for k in arguments):raise StoreError('private World manifest arguments forbidden')
    if type(commit_token) is not str or re.fullmatch('[0-9a-f]{32}',commit_token) is None:raise StoreIntegrityError('World manifest requires exact session publication token')
    if any(type(v) is not tuple for v in (version_changes,changes,new_segments,identity_changes)):raise StoreError('World manifest producer requires frozen finite input tuples')
    if store.db.in_transaction:raise StoreError('World manifest save requires owned operation')
    reference.target._require_closed_codec(store)
    with store.read_snapshot(pin,_preflight=lambda:_schemas(store)):
        pairs,facts=_load(store,pin,(certificate,expected));epoch=store.db.execute('PRAGMA data_version').fetchone()[0]
    r=_Request(store,pin,(certificate,expected),pairs,facts,store.codec.encode(commit_token),epoch)
    changed=bool(checkpoint or version_changes or changes or new_segments or identity_changes or metadata!=store.head_metadata())
    if changed:
        marker=(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY)
        if any((c.namespace,c.key)==marker for c in changes):raise StoreError('World manifest owns the exact session commit descriptor')
        changes=(*changes,RecordChange(*marker,(1,pin.captured_head+1,commit_token)))
    ca,sa,ia,ra,da=pairs
    touched=tuple(sorted({c.namespace for c in version_changes}))
    if 'namespaces' in arguments:raise StoreError('World manifest derives touched namespaces from frozen rows')
    result=inventory._commit_inventory(store,pin,*ia,da,ca,scope_authority=sa,record_authority=ra,commit_token=commit_token,manifest_request=r,
        namespaces=touched,version_changes=version_changes,changes=changes,new_segments=new_segments,identity_changes=identity_changes,metadata=metadata,**arguments)
    outcome=result.content.commit.outcome
    if outcome=='committed' and r.successor is None:raise StoreIntegrityError('missing World manifest successor')
    return WorldManifestCommit(result.content.commit,r.successor if outcome=='committed' else r.parent if outcome=='not_committed' else (),r.reaudited)


def resolve_world_manifest(store,pin,certificate,expected,*,commit_token):
    from .persistence_proof_generation import _accepted
    _accepted(certificate,expected)
    if (certificate.store_identity,certificate.generation,certificate.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version):raise StoreConflictError('World recovery context disagreement')
    if store.db.in_transaction:raise StoreError('World recovery requires owned operation')
    _schemas(store);ca,sa,ia,ra,da=_pairs(store,certificate.generation)
    result=inventory.resolve_inventory(store,pin,*ia,da,ca,scope_authority=sa,record_authority=ra,commit_token=commit_token)
    c=result.content.commit
    if c.outcome=='conflict':return WorldManifestCommit(c,())
    row=store.db.execute('SELECT commitment,manifest FROM ate_generation_manifests WHERE generation=?',(c.generation,)).fetchone()
    if row is None:raise StoreIntegrityError('missing recovered World manifest')
    from .persistence_proof_generation import decode_manifest
    child=decode_manifest(row[1],row[0]);pair=child,row[0]
    with store.read_snapshot(c.pin,_preflight=lambda:_schemas(store)):_load(store,c.pin,pair)
    if c.outcome=='not_committed':
        if pair!=(certificate,expected):raise StoreIntegrityError('World recovery parent disagreement')
    else:
        validate_successor(certificate,expected,child,row[0],store.codec.encode(commit_token))
        if child.receipt.pin_token!=pin.token:raise StoreIntegrityError('World recovery writer disagreement')
    return WorldManifestCommit(c,pair)
