"""Explicit full World reference/topology audit and seven-root composition.

This construction may read history. It is not ordinary World admission or an
incremental native save path. Same-input reuse belongs to manifest publication.
"""
from dataclasses import dataclass,is_dataclass
from functools import lru_cache
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,RecordChange
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_store import ProofNodeStore
from .persistence_proof_map import ProofMap
from .persistence_proof_content import _namespace,_integer,version_key,record_key,record_commitment,segment_key
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_projection import _require_closed_codec
from .persistence_lazy_families import AUXILIARY_OWNER_FAMILIES,FAMILIES
from .persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as HISTORY,PAGE_NAMESPACE,ENTRY_NAMESPACE,HistoryReference
from .persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE,NAMESPACES as SEQUENCES,NODE_NAMESPACE
from .persistence_record_headers import NAMESPACE as RECORDS,RecordReference
from .persistence_nonreflexive_keys import NAMESPACE as NAN,NonreflexiveKeyReference
from .persistence_event_id_reference import EventIdReference
from .persistence_schema import RECORD_FIELDS
from .event_log import FrozenList,FrozenDict
from . import persistence_catalog_copy as checked_copy
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_reference as selected
from . import persistence_proof_target as target
from . import persistence_proof_scope as scope
from . import persistence_proof_collection_directory as directory
from . import persistence_proof_collection as collection
from . import persistence_proof_directory_publish as directory_publish

@dataclass(frozen=True)
class WorldRoots:
    roots:tuple
    owners:int
    backings:int
    projections:int
    facts:tuple


def _map(store,label):
    d=_digest(b'ate-audited-world-domain/1',_namespace(store.store_identity),_integer(store.codec.version,1),label);nodes=ProofNodeStore(store.db)
    return ProofMap(d,lambda h:nodes.read(d,h),lambda h,b:nodes.write(d,h,b))

def _composite(store,label,roots,*,persist=True):
    m=_map(store,label)
    if not persist:
        nodes={};m=ProofMap(m.map_domain,lambda h:nodes[h],lambda h,b:nodes.__setitem__(h,b))
    r=m.empty
    for i,v in enumerate(roots):
        if type(v) is not Root or type(v.digest) is not bytes or len(v.digest)!=32 or type(v.count) is not int or not 0<=v.count<2**63:raise StoreIntegrityError('invalid World component root')
        r=m.set(r,i.to_bytes(2,'big'),_digest(b'ate-audited-world-root/1',v.digest,v.count.to_bytes(8,'big')))
    return r


def _check_sources(store,g,ca,sa,ia,ra,da):
    selected._checked_components(store,ca,sa,ia,ra)
    directory._preflight(store,type('PinContext',(),{'captured_head':g,'store_identity':store.store_identity})(),*da,1048576)
    if directory_publish._load(store,g)[0]!=da:raise StoreIntegrityError('World directory authority disagreement')
    scope._guard_construction(store.db);scope._guard_child_keys(store);scope._guard_sequence_keys(store)
    if scope._construct_roots(store,g,sa[0].next_incarnation_id,include_children=True,include_sequence=True)!=sa[0].roots:raise StoreIntegrityError('World physical scoped relations disagree with accepted roots')
    counts=[0,0,0]
    for ns,key in store.db.execute('SELECT namespace,typed_key FROM lazy_record_versions WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(g,g)):
        row=target.content._source_version(store,g,ns,key);actual=target.content._version_value(ns,key,row,store.codec.version)
        if target.content._map(store).get(ca[0].versions,version_key(ns,key))!=actual:raise StoreIntegrityError('World version source disagrees with accepted content')
        counts[0]+=1
    from . import persistence_proof_record as records
    for ns,key,payload,codec,schema,revision in store.db.execute('SELECT namespace,typed_key,payload,codec_version,record_schema,last_changed_generation FROM records'):
        actual=record_commitment(ns,key,last_changed_generation=revision,codec_version=codec,record_schema=schema,payload=payload)
        if records._map(store).get(ra[0].root,record_key(ns,key))!=actual:raise StoreIntegrityError('World ordinary source disagrees with accepted content')
        counts[1]+=1
    for ns,ordinal in store.db.execute('SELECT namespace,ordinal FROM segments'):
        row=target.content._source_event(store,g,ns,ordinal,64*1048576,1048576)
        if target.content._map(store,True).get(ca[0].events,segment_key(ns,ordinal))!=target.content._event_value(ns,ordinal,row,store.codec.version):raise StoreIntegrityError('World event source disagrees with accepted content')
        counts[2]+=1
    if tuple(counts)!=(ca[0].versions.count,ra[0].root.count,ca[0].events.count):raise StoreIntegrityError('World source inventory disagrees with content root counts')
    m=OrderedSeekMap(store.db,directory.domain(store.store_identity,store.codec.version))
    def collections():
        for (ns,) in store.db.execute('SELECT namespace FROM lazy_namespace_state WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY CAST(namespace AS BLOB)',(g,g)):
            c,e=collection._construct_collection(store,g,ns)
            yield directory._key(ns),directory._persist(store,m.domain,directory._key(ns),c)
    if m.build(collections())!=da[0].root:raise StoreIntegrityError('World complete collection directory disagreement')



@lru_cache(maxsize=128)
def _family_value_hint(namespace):
    from typing import get_type_hints,get_args
    from .persistence_schema import ROOT_TYPES
    root,field=namespace.rsplit('.',1)
    value=get_args(get_type_hints(ROOT_TYPES[root])[field])
    return value[-1] if value else None


def _record_class(namespace):
    cls=_family_value_hint(namespace)
    return cls if isinstance(cls,type) and cls in RECORD_FIELDS else None


def _check_record_class(store,namespace,value,record_header=None):
    expected=_record_class(namespace)
    if expected is None:return
    if type(value) is RecordReference:
        from .persistence_record_headers import checked_record_header
        row=store.db.execute('SELECT payload FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',(RECORDS,store.codec.encode((value.incarnation,0)))).fetchone() if record_header is None else None
        header=record_header(value.incarnation) if record_header is not None else None if row is None else store.codec.decode(row[0])
        if header is None or checked_record_header(header)[0] is not expected:raise StoreIntegrityError('World owner record class disagrees with namespace')
    elif type(value) is not expected:raise StoreIntegrityError('World owner record class disagrees with namespace')


def _check_family_value(store,namespace,key,value,record_header=None):
    """The consuming family, rather than the reference tag, declares its type."""
    from typing import get_origin
    from .persistence_lazy import BUCKET_SPECS,SCALAR_MAP_SPECS,_valid_scalar_map_key
    _check_record_class(store,namespace,value,record_header)
    if _record_class(namespace) is not None:return
    hint=_family_value_hint(namespace);origin=get_origin(hint)
    if namespace in SCALAR_MAP_SPECS:
        valid=_valid_scalar_map_key(namespace,key) and type(value) in SCALAR_MAP_SPECS[namespace][1]
    elif type(value) is HistoryReference:
        expected=BUCKET_SPECS[namespace][0] if namespace in BUCKET_SPECS else {dict:'map',list:'list',set:'set'}.get(origin)
        valid=expected is not None and value.kind==expected
    else:
        expected=origin or hint
        valid=type(value) is expected or expected is float and type(value) is int
    if not valid:raise StoreIntegrityError('World family value has wrong declared kind')


@lru_cache(maxsize=256)
def _record_hints(cls):
    from typing import get_type_hints
    from .advancement import AbilityProgress
    from .mastery_training import ResponseModel
    # Advancement imports this type only for static checking to avoid a cycle.
    # Supply the exact persisted class without changing the module's globals.
    if cls is AbilityProgress:return get_type_hints(cls,localns={'ResponseModel':ResponseModel})
    return get_type_hints(cls)


def _check_field_values(store,namespace,cls,values,record_header=None):
    from typing import get_type_hints,get_origin,get_args,Any,Union
    from types import UnionType
    from .persistence_lazy import NESTED_FIELD_KINDS
    from .persistence_record_headers import checked_record_header
    hints=_record_hints(cls)
    def allowed(annotation,ref):
        if annotation in (Any,object):return True
        origin=get_origin(annotation) or annotation
        if origin in (Union,UnionType):return any(allowed(a,ref) for a in get_args(annotation))
        if type(ref) is NonreflexiveKeyReference:return annotation is float
        if type(ref) is EventIdReference:return origin in (set,frozenset)
        if type(ref) is HistoryReference:
            return ref.kind in ({list:('list','sequence','frozen-list'),dict:('map','frozen-map'),set:('set',),tuple:('list','frozen-list'),frozenset:('set',)}.get(origin,()))
        if type(ref) is RecordReference:
            if not isinstance(annotation,type) or annotation not in RECORD_FIELDS:return False
            row=store.db.execute('SELECT payload FROM lazy_record_versions WHERE namespace=? AND typed_key=? AND valid_to IS NULL',(RECORDS,store.codec.encode((ref.incarnation,0)))).fetchone() if record_header is None else None
            header=record_header(ref.incarnation) if record_header is not None else None if row is None else store.codec.decode(row[0])
            return header is not None and checked_record_header(header)[0] is annotation
        return False
    for field,ref in zip(RECORD_FIELDS[cls],values):
        if type(ref) not in (HistoryReference,RecordReference,NonreflexiveKeyReference,EventIdReference):continue
        expected=NESTED_FIELD_KINDS.get((namespace,field))
        if not allowed(hints[field],ref) or expected is not None and (type(ref) is not HistoryReference or ref.kind!=expected):raise StoreIntegrityError(f'World field reference has wrong member kind: {cls.__name__}.{field}')


def _check_field_references(store,namespace,value,record_header=None):
    cls=type(value)
    _check_field_values(store,namespace,cls,tuple(getattr(value,f) for f in RECORD_FIELDS[cls]),record_header)


def _check_queries(store,pin,change):
    if isinstance(change,RecordChange):return
    from . import persistence_lazy as runtime
    from .persistence_lazy_adoption import memberships as adoption_memberships
    ns=change.namespace
    order=store._visible_order(ns,store.codec.encode(change.key),pin.captured_head)
    if order is None:raise StoreIntegrityError('World owner has no collection order')
    ordinal=order[0];v=change.value
    institutional=set(runtime.SCALAR_RECORD_SPECS)|{runtime.SOCIAL_EDGE_NAMESPACE,runtime.SOCIAL_PARTNERSHIP_NAMESPACE,runtime.TRANSMISSION_NAMESPACE,runtime.MOTIVE_NAMESPACE,runtime.INSTITUTION_MAGIC_RECORD_NAMESPACE,runtime.INSTITUTION_NOTICE_NAMESPACE,runtime.INSTITUTION_APPLICATION_NAMESPACE}
    # Partnership bodies store only the event ID; the pair belongs to the key.
    # The shared projection validator consumes the logical (pair, event) entry.
    if ns==runtime.SOCIAL_PARTNERSHIP_NAMESPACE:expected=runtime._institution_memberships(ns,(change.key,v),ordinal)
    elif ns in institutional:expected=runtime._institution_memberships(ns,v,ordinal)
    elif ns=='world.people':expected=(('alive',bool(v.alive),ordinal),)
    elif ns=='world.magic_resources.resources':expected=runtime._resource_memberships(v,ordinal)
    elif ns=='world.materials.lots':expected=runtime._material_lot_memberships(v,ordinal)
    elif ns=='world.communities.memberships':expected=(('person',change.key[0],ordinal),)
    elif ns=='world.culture.adoption':expected=tuple((m.index_name,m.value,m.ordinal) for m in adoption_memberships(change.key,v,ordinal))
    else:expected=()
    actual=tuple((m.index_name,m.value,m.ordinal) for m in change.memberships)
    if store.codec.encode(tuple(sorted(actual,key=store.codec.encode)))!=store.codec.encode(tuple(sorted(expected,key=store.codec.encode))):raise StoreIntegrityError(f'World query projection disagrees with owner values: {ns} {change.key!r}')


def _check_events(store,pin,manifest):
    from .persistence_session import _read_event_descriptors,_read_suffix,COLD_EVENT_KIND,CHUNK_SIZE
    from .persistence_events import SealedEventPrefix
    prefix,tail,commit=_read_event_descriptors(store)
    if commit.captured_generation!=pin.captured_head or manifest['collections']['world.events']!=(COLD_EVENT_KIND,tail.total_events,tail.sealed_events//CHUNK_SIZE):raise StoreIntegrityError('World event/commit descriptor disagreement')
    if store.read_record('world.next_event',0,expected_record_schema=1)[1]!=tail.total_events+1:raise StoreIntegrityError('World next event disagrees with event authority')
    reader=SealedEventPrefix.from_active_read_transaction(store)
    try:reader.verify_full()
    finally:reader.close()
    _read_suffix(store,tail,prefix,captured_generation=pin.captured_head)

def _project(store,namespace,key,value,ordinary,*,record_header=None):
    """Existing World paths, including ordinary ordinal envelopes, no restoration."""
    from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE,PACKED_LIST_KEY,PACKED_LIST_PAYLOAD
    if ordinary:
        if type(value) is not tuple or len(value)!=2 or type(value[0]) is not int or value[0]<0:raise StoreIntegrityError('World ordinary owner lacks exact ordinal envelope')
        value=value[1]
    if namespace=='world.event_ids':
        if type(key) is not int or key!=0:raise StoreIntegrityError('World Event-ID facade is not owner zero')
        from .persistence_event_id_reference import check_compact_authority
        from .persistence_event_ids import EXCEPTION_TAG
        check_compact_authority(value)
        # Owner-zero's facade incarnation comes from its exact checked root slot.
        slots=store.db.execute('SELECT incarnation_id FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=? AND valid_to IS NULL',(namespace,store.codec.encode(key),store.codec.encode(()))).fetchall()
        if len(slots)!=1:raise StoreIntegrityError('World Event-ID facade lacks one root slot')
        yield (),slots[0][0],'event-ids',None
        if value[0]==EXCEPTION_TAG:
            for name,ref in zip(('removed','added'),value[2:4]):yield (('field','_exact'),('field',name)),ref.incarnation,ref.kind,None
        return
    if namespace==AGENCY_ACTIONS_NAMESPACE and key==PACKED_LIST_KEY:
        if type(value) is not tuple or len(value)!=2 or value[0]!=PACKED_LIST_PAYLOAD or type(value[1]) is not tuple:raise StoreIntegrityError('invalid packed World action owner')
        for item in value[1]:_check_record_class(store,namespace,item,record_header)
        roots=[(v,(('index',i),)) for i,v in enumerate(value[1])]
    else:
        _check_family_value(store,namespace,key,value,record_header)
        roots=[(value,())]
    pending=list(reversed(roots));seen=0
    while pending:
        v,path=pending.pop();seen+=1
        if seen>1048576:raise StoreError('World owner projection requires larger explicit construction budget')
        if type(v) in (HistoryReference,RecordReference,NonreflexiveKeyReference,EventIdReference):
            kind,inc=target._reference(v);yield path,inc,kind,None;continue
        cls=type(v);record=is_dataclass(v)
        from .core import Event
        mutable=cls in (dict,list,set) or record and cls in RECORD_FIELDS and not cls.__dataclass_params__.frozen
        if cls is Event and getattr(v,'_sealed',False):mutable=False
        if mutable:
            kind='record:'+cls.__module__.split('.')[-1]+'.'+cls.__name__ if record else cls.__name__
            yield path,None,kind,_digest(b'ate-inline-identity-value/1',store.codec.encode(v))
        if record:
            if cls not in RECORD_FIELDS:raise StoreIntegrityError('undeclared World record projection')
            _check_field_references(store,namespace,v,record_header)
            pending.extend((getattr(v,n),path+(('field',n),)) for n in reversed(RECORD_FIELDS[cls]))
        elif cls in (dict,FrozenDict):
            for k,child in reversed(tuple(v.items())):
                from .persistence_nonreflexive_keys import stored_reference_placements
                if stored_reference_placements(k):raise StoreError('inline World key reference needs separate canonical admission')
                pending.append((child,path+(('key',k),)))
        elif cls in (list,tuple,FrozenList):pending.extend((child,path+(('index',i),)) for i,child in reversed(tuple(enumerate(v))))
        elif cls in (set,frozenset):
            from .persistence_nonreflexive_keys import stored_reference_placements
            if any(stored_reference_placements(c) for c in v):raise StoreError('inline World set reference needs separate canonical admission')




def _acyclic_backings(store):
    db=store.db
    db.execute('CREATE TEMP TABLE ate_world_degree(inc INTEGER PRIMARY KEY,degree INTEGER NOT NULL) WITHOUT ROWID')
    db.execute('CREATE INDEX ate_world_degree_zero ON ate_world_degree(degree,inc)')
    try:
        db.execute('INSERT INTO ate_world_degree SELECT parent,0 FROM ate_world_edges UNION SELECT child,0 FROM ate_world_edges')
        db.execute('CREATE INDEX ate_world_edges_child ON ate_world_edges(child,parent)')
        db.execute('UPDATE ate_world_degree SET degree=(SELECT COUNT(*) FROM ate_world_edges WHERE child=inc)')
        while True:
            ready=db.execute('SELECT inc FROM ate_world_degree WHERE degree=0 LIMIT 128').fetchall()
            if not ready:break
            for (inc,) in ready:
                for (child,) in db.execute('SELECT child FROM ate_world_edges WHERE parent=?',(inc,)):
                    db.execute('UPDATE ate_world_degree SET degree=degree-1 WHERE inc=?',(child,))
                db.execute('DELETE FROM ate_world_degree WHERE inc=?',(inc,))
        if db.execute('SELECT 1 FROM ate_world_degree LIMIT 1').fetchone():raise StoreError('cyclic World backing graph requires a separate checked path')
    finally:db.execute('DROP TABLE ate_world_degree')


def _build_map(store,label,rows):
    from .persistence_proof_nodes import key_locator
    from .persistence_proof_batch import update_sorted
    m=_map(store,label);db=store.db
    db.execute('CREATE TEMP TABLE ate_world_map_delta(locator BLOB PRIMARY KEY,key BLOB,value BLOB) WITHOUT ROWID')
    try:
        for key,value in rows:db.execute('INSERT INTO ate_world_map_delta VALUES(?,?,?)',(key_locator(m.map_domain,key),key,value))
        return update_sorted(m,m.empty,db.execute('SELECT key,value FROM ate_world_map_delta ORDER BY locator'))
    finally:db.execute('DROP TABLE ate_world_map_delta')


def _structural_descriptor(codec,kind,raw):
    d=codec.decode(raw)
    if kind=='record':return codec.encode((d[0],d[1]))
    if kind=='nan-key':return b''
    if kind=='sequence':return codec.encode((d[0],d[1],d[3],d[4],d[5],d[8:] if len(d)>8 else ()))
    if kind=='event-ids':return codec.encode(d)
    return codec.encode(d)

def _fixed_world_sources(store,pin,manifest):
    from .persistence_schema import ROOT_FIELDS
    from .persistence_session import _expected_collection_namespaces,_validate_head_inventory,_read_event_descriptors,EVENT_STORAGE,SEALED_EVENTS
    from .persistence_adapters import META,IDENTITY_LINKS,AGENCY_ACTIONS_NAMESPACE,PACKED_LIST_KEY,PACKED_LIST_PAYLOAD
    from .persistence_complete_format import _check_fixed_contract
    from .persistence_lazy import _base_kind
    for root,fields in ROOT_FIELDS.items():
        for name,expected in fields.items():
            if expected=='state':continue
            description=manifest['collections'][root+'.'+name]
            if type(description) is not tuple or len(description)!=3:raise StoreIntegrityError('invalid World collection layout')
            kind,size,chunks=description
            allowed={'int':('int',),'dict':('dict','RecordTable'),'list':('list','list-packed/v1'),'set':('set','event-ids-range/v1','event-ids-exceptions/v1'),'events':('EventLog',)}[expected]
            if type(kind) is not str or _base_kind(kind) not in allowed or type(size) is not int or size<0 or type(chunks) is not int or chunks<0 or expected!='events' and chunks!=0:raise StoreIntegrityError('invalid World collection layout kind/count')
    head=store.checked_head();identity_count=_check_fixed_contract(store,pin,head,manifest)
    prefix,tail,_commit=_read_event_descriptors(store)
    _validate_head_inventory(head,manifest,(),dict(metadata_rows=store.read_records(META,expected_record_schema=1),prefix=prefix,tail=tail),checked_identity_count=identity_count)
    if set(head.metadata['namespaces'])!=_expected_collection_namespaces()|{META,IDENTITY_LINKS,EVENT_STORAGE,SEALED_EVENTS}:raise StoreIntegrityError('World namespace inventory disagrees with closed schema')
    for root,fields in ROOT_FIELDS.items():
        for name,kind in fields.items():
            if kind!='int':continue
            ns=root+'.'+name
            if store._namespace_state_at(ns,pin.captured_head) is not None:raise StoreIntegrityError('World scalar has competing lazy authority')
            rows=store.db.execute('SELECT typed_key,payload FROM records WHERE namespace=? LIMIT 2',(ns,)).fetchall()
            if len(rows)!=1 or rows[0][0]!=store.codec.encode(0):raise StoreIntegrityError('missing or surplus World scalar source')
            v=store.codec.decode(rows[0][1])
            if type(v) is not tuple or len(v)!=2 or type(v[0]) is not int or v[0]!=0 or type(v[1]) is not int:raise StoreIntegrityError('invalid World scalar source envelope')
    for ns,key in (('world.event_ids',0),(AGENCY_ACTIONS_NAMESPACE,PACKED_LIST_KEY)):
        state=store._namespace_state_at(ns,pin.captured_head)
        if state is None:rows=store.db.execute('SELECT typed_key FROM records WHERE namespace=? LIMIT 2',(ns,)).fetchall()
        else:rows=store.db.execute('SELECT typed_key FROM lazy_record_versions WHERE namespace=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) LIMIT 2',(ns,pin.captured_head,pin.captured_head)).fetchall()
        if rows!=[(store.codec.encode(key),)]:raise StoreIntegrityError('World singleton owner has missing, extra or wrong key')
        value=store.read_version(pin,ns,key,expected_record_schema=1).value if state is not None else store.read_record(ns,key,expected_record_schema=1)[1]
        kind,size,chunks=manifest['collections'][ns]
        if type(chunks) is not int or chunks!=0:raise StoreIntegrityError('World singleton layout has invalid chunks')
        if ns=='world.event_ids':
            from .persistence_event_id_reference import check_compact_authority
            from .persistence_event_ids import RANGE_TAG
            check_compact_authority(value)
            if kind!=value[0]:raise StoreIntegrityError('World Event-ID layout kind disagrees with descriptor')
            actual=value[1] if kind==RANGE_TAG else value[4]
            if size!=actual:raise StoreIntegrityError('World Event-ID layout count disagrees with descriptor')
        elif type(value) is not tuple or len(value)!=2 or value[0]!=PACKED_LIST_PAYLOAD or type(value[1]) is not tuple or len(value[1])!=size:raise StoreIntegrityError('World packed action layout count disagrees with payload')

def _audit_world(store,pin,ca,sa,ia,ra,da):
    from .persistence_adapters import META,_read_cold_manifest
    from .persistence_complete_format import selected as complete_selected
    from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES,_checked_value
    from .persistence_history_types import NAMESPACE as TYPES
    from .persistence_event_ids import EXCEPTION_TAG
    if not getattr(store,'_checked_snapshot_depth',0):raise StoreError('World audit requires checked owned snapshot')
    if pin.captured_head!=store.generation:raise StoreConflictError('World full audit requires current pinned head')
    _check_sources(store,pin.captured_head,ca,sa,ia,ra,da)
    manifest=_read_cold_manifest(store)
    floor=int(store.db.execute("SELECT value FROM store_metadata WHERE key='format_version'").fetchone()[0])
    if not complete_selected(manifest,floor):raise StoreError('World proof construction requires explicit complete source format')
    from .persistence_proof_manifest_publish import _check_head
    from .persistence_history_retirement import NAMESPACE as RETIREMENT
    if next(iter(store.iter_keys(pin,RETIREMENT)),None) is not None:raise StoreError('partial retirement requires a separately checked World proof path')
    _fixed_world_sources(store,pin,manifest)
    _check_head(store,pin,ra);_check_events(store,pin,manifest)
    if store.db.execute('SELECT 1 FROM query_membership LIMIT 1').fetchone():raise StoreError('ordinary World query projection has no declared source contract')
    store.verify_all();checked_copy._verify_catalog(store,pin)
    store.db.execute('CREATE TEMP TABLE ate_world_backings(inc INTEGER PRIMARY KEY,kind TEXT,namespace TEXT,key BLOB,descriptor BLOB) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_world_projection(namespace TEXT,key BLOB,path BLOB,inc INTEGER,kind TEXT,fingerprint BLOB,PRIMARY KEY(namespace,key,path)) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_world_orders(namespace TEXT,ordinal INTEGER,typed_key BLOB,PRIMARY KEY(namespace,ordinal),UNIQUE(namespace,typed_key)) WITHOUT ROWID')
    store.db.execute('CREATE TEMP TABLE ate_world_edges(parent INTEGER,child INTEGER,PRIMARY KEY(parent,child)) WITHOUT ROWID')
    owners=0;codec=store.codec
    try:
        for ns in (HISTORY,SEQUENCE,RECORDS,NAN):
            for key in store.iter_keys(pin,ns):
                value=store.read_version(pin,ns,key,expected_record_schema=1).value
                inc=key[0] if ns in (RECORDS,NAN) else key;kind='record' if ns==RECORDS else 'nan-key' if ns==NAN else 'sequence' if ns==SEQUENCE else value[0]
                target._validate_descriptor(kind,inc,value)
                if type(inc) is not int or not 1<=inc<ia[0].head.next_incarnation_id:raise StoreIntegrityError('World backing outside allocator')
                if _checked_value(store,pin,inc)[1]!=kind:raise StoreIntegrityError('World backing dependency kind disagreement')
                try:store.db.execute('INSERT INTO ate_world_backings VALUES(?,?,?,?,?)',(inc,kind,ns,codec.encode(key),codec.encode(value)))
                except Exception as exc:
                    if store.db.execute('SELECT 1 FROM ate_world_backings WHERE inc=?',(inc,)).fetchone():raise StoreIntegrityError('competing World backing families') from exc
                    raise
        for c in checked_copy._iter_owner_sources(store,pin):
            owners+=1;adapter=AUXILIARY_OWNER_FAMILIES.get(c.namespace);typed=codec.encode(c.key)
            if isinstance(c,RecordChange):
                if type(c.value) is not tuple or len(c.value)!=2 or type(c.value[0]) is not int or c.value[0]<0:raise StoreIntegrityError('World ordinary order lacks exact envelope')
                store.db.execute('INSERT INTO ate_world_orders VALUES(?,?,?)',(c.namespace,c.value[0],typed))
            if adapter:
                if c.namespace==NODE_NAMESPACE and c.value[0]=='branch':continue
                adapter.validate_source(c,'lazy',codec)
                if c.namespace==RECORDS:
                    from .persistence_record_headers import checked_record_header
                    cls,values,_state=checked_record_header(c.value)
                    _check_field_values(store,None,cls,values)
                projections=((path,inc,*target._reference(adapter.resolve_path(c.value,path))[:1],None) for path,inc in adapter.reference_placements(c.value))
            else:
                _check_queries(store,pin,c)
                projections=_project(store,c.namespace,c.key,c.value,isinstance(c,RecordChange))
            facade=None
            for path,inc,kind,fingerprint in projections:
                encoded=codec.encode(path)
                actual=store.db.execute('SELECT incarnation_id FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND owner_key=? AND occurrence_path=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',(c.namespace,typed,encoded,pin.captured_head,pin.captured_head)).fetchall()
                if len(actual)!=1 or inc is not None and actual[0][0]!=inc:raise StoreIntegrityError('World body projection missing or wrong complete owner placement')
                inc=actual[0][0]
                if adapter is not None and fingerprint is None:store.db.execute('INSERT OR IGNORE INTO ate_world_edges VALUES(?,?)',(c.key[0],inc))
                if c.namespace=='world.event_ids':
                    if not path:facade=inc
                    else:store.db.execute('INSERT OR IGNORE INTO ate_world_edges VALUES(?,?)',(facade,inc))
                if fingerprint is None:
                    if kind=='event-ids' and c.namespace=='world.event_ids' and not path:
                        if store.db.execute('SELECT 1 FROM ate_world_backings WHERE inc=?',(inc,)).fetchone():raise StoreIntegrityError('competing Event-ID backing')
                        store.db.execute('INSERT INTO ate_world_backings VALUES(?,?,?,?,?)',(inc,kind,c.namespace,typed,codec.encode(c.value)))
                    row=store.db.execute('SELECT kind FROM ate_world_backings WHERE inc=?',(inc,)).fetchone()
                    if row!=(kind,):raise StoreIntegrityError('World reference has missing or wrong-kind target backing')
                elif store.db.execute('SELECT 1 FROM ate_world_backings WHERE inc=?',(inc,)).fetchone():raise StoreError('mixed inline/backed identity requires a separate checked path')
                from .persistence_history_types import incoming_owner_policy
                policy=incoming_owner_policy(c.namespace,path)
                if policy is not None:
                    if kind not in ('list','map','set','sequence','frozen-list','frozen-map'):raise StoreIntegrityError('World incoming policy requires history backing')
                    counts=store.read_version(pin,TYPES,inc,expected_record_schema=1).value[2]
                    if counts[0 if policy=='int' else 1]!=sum(counts):raise StoreIntegrityError('World incoming member policy disagrees with backing values')
                store.db.execute('INSERT INTO ate_world_projection VALUES(?,?,?,?,?,?)',(c.namespace,typed,encoded,inc,kind,fingerprint))
        g=pin.captured_head
        expected='SELECT namespace,key,path,inc FROM ate_world_projection'
        actual='SELECT owner_namespace,owner_key,occurrence_path,incarnation_id FROM lazy_identity_occurrence_versions WHERE valid_from<='+str(g)+' AND (valid_to IS NULL OR '+str(g)+'<valid_to)'
        for a,b in ((expected,actual),(actual,expected)):
            if store.db.execute(a+' EXCEPT '+b+' LIMIT 1').fetchone():raise StoreIntegrityError('World full owner projection inventory disagrees')
        if store.db.execute('SELECT inc FROM ate_world_projection GROUP BY inc HAVING COUNT(DISTINCT kind)>1 OR COUNT(DISTINCT fingerprint)>1 LIMIT 1').fetchone():raise StoreIntegrityError('World aliases disagree on kind or native value')
        # Every physical child belongs to the correct backing family, including
        # otherwise unindexed surplus pages/entries and sequence sidecars.
        families={PAGE_NAMESPACE:('list','frozen-list'),ENTRY_NAMESPACE:('map','set','frozen-map'),RECORDS:('record',),NAN:('nan-key',)}
        families.update((ns,('sequence',)) for ns in SEQUENCES if ns!=SEQUENCE)
        for ns,kinds in families.items():
            for key in store.iter_keys(pin,ns):
                if type(key) is not tuple or len(key)!=2 or type(key[0]) is not int:raise StoreIntegrityError('invalid global physical child parent')
                row=store.db.execute('SELECT kind,descriptor FROM ate_world_backings WHERE inc=?',(key[0],)).fetchone()
                if row is None or row[0] not in kinds:raise StoreIntegrityError('orphan or wrong-kind physical child parent')
                if ns in (PAGE_NAMESPACE,ENTRY_NAMESPACE):
                    descriptor=codec.decode(row[1]);value=store.read_version(pin,ns,key,expected_record_schema=1).value
                    if ns==PAGE_NAMESPACE:
                        if type(key[1]) is not int or not 0<=key[1]<(descriptor[1]+127)//128 or len(value)!=min(128,descriptor[1]-128*key[1]):raise StoreIntegrityError('surplus or malformed physical list page')
                    elif type(value[0]) is not int or not 0<=value[0]<descriptor[2] or row[0]=='set' and value[2] is not None:raise StoreIntegrityError('invalid scalar child ordinal/value')
        # Existence checks above are complemented by complete native extent,
        # type/certification and sequence audits in the established copy audit.
        _acyclic_backings(store)
        def backing_rows():
            for inc,kind,ns,key,descriptor in store.db.execute('SELECT * FROM ate_world_backings ORDER BY inc'):
                frame=_structural_descriptor(codec,kind,descriptor)
                yield inc.to_bytes(8,'big'),_digest(b'ate-world-backing/1',kind.encode(),ns.encode(),key,frame)
        br=_build_map(store,b'backing-inventory',backing_rows())
        def projection_rows():
            for ns,key,path,inc,kind,f in store.db.execute('SELECT * FROM ate_world_projection ORDER BY namespace,key,path'):
                yield codec.encode((ns,key,path)),_digest(b'ate-world-placement/1',inc.to_bytes(8,'big'),kind.encode())
        orr=_build_map(store,b'owner-projections',projection_rows())
        qr=_map(store,b'ordinary-query').empty
        def history_orders():
            for inc,kind,ns,key,descriptor in store.db.execute("SELECT * FROM ate_world_backings WHERE kind NOT IN ('record','nan-key') ORDER BY inc"):
                yield inc.to_bytes(8,'big'),_digest(b'ate-world-history-order/1',kind.encode(),descriptor)
        hr=_build_map(store,b'backing-orders',history_orders())
        od=_digest(b'ate-world-ordinary-order-domain/1',store.store_identity.encode(),_integer(store.codec.version,1));om=OrderedSeekMap(store.db,od)
        def ordered():
            for ns,ordinal,key in store.db.execute('SELECT * FROM ate_world_orders ORDER BY length(CAST(namespace AS BLOB)),CAST(namespace AS BLOB),ordinal,typed_key'):
                raw=ns.encode();position=len(raw).to_bytes(4,'big')+raw+ordinal.to_bytes(8,'big')+key
                yield position,_digest(b'ate-world-ordinary-order-member/1',position)
        order=om.build(ordered());orders=_composite(store,b'orders',(da[0].root,order,hr,sa[0].roots[2]))
        topo=_composite(store,b'topology',(*sa[0].roots[:2],*sa[0].roots[4:],br,orr))
        query=_composite(store,b'queries',(*sa[0].roots[2:4],qr))
        return WorldRoots((ca[0].versions,ra[0].root,topo,query,orders,ca[0].events,ia[0].root),owners,br.count,orr.count,(br,orr,qr,order,hr))
    finally:
        store.db.execute('DROP TABLE ate_world_edges');store.db.execute('DROP TABLE ate_world_orders');store.db.execute('DROP TABLE ate_world_projection');store.db.execute('DROP TABLE ate_world_backings')


def audit_world_roots(store,pin,content_authority,scope_authority,inventory_authority,record_authority,directory_authority):
    selected._components(store,pin,content_authority,scope_authority,inventory_authority,record_authority)
    if store.db.in_transaction:raise StoreError('World audit requires owned operation')
    store.db.execute('BEGIN IMMEDIATE');store._active_read_transaction=True
    try:
        with store.read_snapshot(pin,_preflight=lambda:target._preflight(store,1048576)):
            result=_audit_world(store,pin,content_authority,scope_authority,inventory_authority,record_authority,directory_authority)
        store.db.commit();return result
    except BaseException:
        if store.db.in_transaction:store.db.rollback()
        raise
    finally:store._active_read_transaction=False
