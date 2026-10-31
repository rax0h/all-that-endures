"""Bounded existing-record value transitions; structural edits keep full audit."""
from dataclasses import replace
from .incremental_store import StoreIntegrityError,Membership,_record_checksum
from .persistence_proof_content import version_key,record_key,record_commitment
from .persistence_proof_nodes import _digest
from . import persistence_proof_world as world
from . import persistence_proof_publication as content
from . import persistence_proof_record as records
from . import persistence_proof_scope as scope
from . import persistence_lazy_identity_catalog as catalog

MAX_ROWS=512
MAX_BYTES=4*1048576


def _projection(store,request,namespace,key,old,new,ordinary=False):
    codec=store.codec;typed=codec.encode(key)
    if namespace in world.AUXILIARY_OWNER_FAMILIES:
        from .persistence_proof_world_backing_value import projection
        before=projection(store,namespace,old);after=projection(store,namespace,new)
    else:
        before=tuple(world._project(store,namespace,key,old,ordinary));after=tuple(world._project(store,namespace,key,new,ordinary))
    if len(before)!=len(after):return False
    mapping=world._map(store,b'owner-projections')
    for a,b in zip(before,after):
        path,inc,kind,fingerprint=a
        if a[:3]!=b[:3]:return False
        rows=store._interval_rows('lazy_identity_occurrence_versions','incarnation_id',('owner_namespace','owner_key','occurrence_path'),(namespace,typed,codec.encode(path)),request.pin.captured_head,'lazy_identity_occurrence_interval',limit=2)
        if len(rows)!=1 or inc is not None and rows[0][0]!=inc:raise StoreIntegrityError('value transition predecessor placement disagreement')
        actual=rows[0][0];wanted=_digest(b'ate-world-placement/1',actual.to_bytes(8,'big'),kind.encode())
        if mapping.get(request.facts[1],codec.encode((namespace,typed,codec.encode(path))))!=wanted:raise StoreIntegrityError('value transition placement lacks accepted World authority')
        if fingerprint!=b[3] and scope._resolve(store,request.pairs[1][0],scope.GroupScope(actual)).count!=1:return False
    return True


def validate_lease_updates(store,request,versions):
    """Publisher lease ownership is mandatory even on the full-audit fallback."""
    from .persistence_history_dependencies import NAMESPACE,dependency_value,_active_tokens
    codec=store.codec;ca=request.pairs[0][0];g=request.pin.captured_head
    for item in versions:
        if item['namespace']!=NAMESPACE:continue
        key=item['typed_key'];old=content._source_version(store,g,NAMESPACE,key)
        wanted=None if old is None else content._version_value(NAMESPACE,key,old,codec.version)
        if content._map(store).get(ca.versions,version_key(NAMESPACE,key))!=wanted:raise StoreIntegrityError('backing lease predecessor lacks accepted content')
        before=() if old is None else codec.decode(old.payload)[2]
        if item['change'].delete:after=()
        else:
            new=codec.decode(item['payload'])
            try:expected=dependency_value(new[1],new[2])
            except (ValueError,TypeError,IndexError) as exc:raise StoreIntegrityError('invalid backing lease transition') from exc
            if codec.encode(expected)!=item['payload'] or item['change'].record_schema!=1 or old is not None and codec.decode(old.payload)[:2]!=new[:2]:raise StoreIntegrityError('backing lease kind/schema disagreement')
            after=new[2]
        added=tuple(t for t in after if t not in before)
        removed=tuple(t for t in before if t not in after and t!=request.pin.token)
        if any(t!=request.pin.token for t in added) or _active_tokens(store,removed):raise StoreIntegrityError('transition changed a foreign publisher lease')
        if _active_tokens(store,added)!=added:raise StoreIntegrityError('transition added an inactive publisher lease')


def validate_value_transition(store,request,versions,ordinary,segments):
    """Return False for unsupported shapes, never infer permission from dirt."""
    from .persistence_schema import ROOT_FIELDS
    from .persistence_history_dependencies import NAMESPACE as DEPENDENCIES
    from .persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
    from .core import Event
    from .persistence_proof_world_tail import metadata_allowed
    if segments or len(versions)>MAX_ROWS:return False
    codec=store.codec;g=request.pin.captured_head;ca=request.pairs[0][0];ra=request.pairs[3][0]
    rows=[];owners={};source_only=set();total=0
    for item in versions:
        if item['change'].reinsertion:return False
        ns,key=item['namespace'],item['typed_key']
        total+=len(ns.encode())+len(key)
        sizes=store._interval_rows('lazy_record_versions','length(payload)+length(memberships)',('namespace','typed_key'),(ns,key),g,'lazy_record_interval',limit=2)
        if len(sizes)==1 and type(sizes[0][0]) is int and sizes[0][0]+len(item['payload'] or b'')+len(item['memberships_blob'])+total>MAX_BYTES:return False
        old=content._source_version(store,g,ns,key,max_bytes=MAX_BYTES)
        if item['change'].delete:
            approved=(request.tail_removed or {}).get((ns,key))
            if approved is None:return False
            if old is None or old.payload!=approved or old.record_schema!=1 or old.memberships!=codec.encode(()) or item['change'].record_schema!=1 or item['memberships_blob']!=codec.encode(()):raise StoreIntegrityError('removed page differs from frozen authority')
            if content._map(store).get(ca.versions,version_key(ns,key))!=content._version_value(ns,key,old,codec.version):raise StoreIntegrityError('removed page lacks accepted content')
            total+=len(old.payload)+len(old.memberships)
            if total>MAX_BYTES:return False
            continue
        if old is None:
            expected=(request.tail_new or {}).get((ns,key))
            if expected is None:return False
            if item['payload']!=expected or item['change'].record_schema!=1 or item['memberships_blob']!=codec.encode(()):raise StoreIntegrityError('new tail source differs from frozen authority')
            if content._map(store).get(ca.versions,version_key(ns,key)) is not None:raise StoreIntegrityError('new tail source lacks accepted content absence')
        if old is not None and content._map(store).get(ca.versions,version_key(ns,key))!=content._version_value(ns,key,old,codec.version):raise StoreIntegrityError('value transition old bytes lack accepted content')
        total+=len(item['payload'] or b'')+len(item['memberships_blob'])+(len(old.payload)+len(old.memberships) if old is not None else 0)
        if total>MAX_BYTES or old is not None and old.record_schema!=item['change'].record_schema:return False
        frozen=replace(item['change'],key=codec.decode(key),value=codec.decode(item['payload']),memberships=tuple(Membership(*m) for m in codec.decode(item['memberships_blob'])))
        item=dict(item,change=frozen)
        value=codec.decode(old.payload) if old is not None else ();rows.append((item,old,value))
        if ns in world.AUXILIARY_OWNER_FAMILIES:
            from .persistence_proof_world_backing_value import eligible
            if eligible(store,request,frozen,value):owners[(ns,key)]=frozen
        if ns in world.FAMILIES and world._record_class(ns) not in (None,Event):owners[(ns,key)]=frozen
        if ((ns,key) not in owners and ns in catalog.IDENTITY_OWNER_FAMILIES and old is not None
                and item['payload']==old.payload and item['memberships_blob']==old.memberships):
            from .persistence_lazy_sequence import NODE_NAMESPACE
            # Branch nodes are structural metadata, not catalog owner sources.
            # An unchanged registered body still acquires a new source revision;
            # require its witness even when its native projection needs no edit.
            if ns!=NODE_NAMESPACE or type(value) is not tuple or not value or value[0]!='branch':
                owners[(ns,key)]=frozen;source_only.add((ns,key))
    headers=[];ordinary_owners=set()
    for item,old,value in rows:
        ns,key=item['namespace'],item['typed_key'];change=item['change'];new=change.value
        if (ns,key) in owners:
            if (ns,key) not in source_only and not _projection(store,request,ns,change.key,value,new):return False
            if ns not in world.AUXILIARY_OWNER_FAMILIES:world._check_queries(store,request.pin,change)
        elif ns==catalog.OWNER_NAMESPACE:
            headers.append((item,old,value))
        elif metadata_allowed(request,ns,change.key):
            pass
        elif ns==DEPENDENCIES:
            if old.memberships!=item['memberships_blob']:return False
        elif item['payload']!=old.payload or item['memberships_blob']!=old.memberships:return False
    scalars={r+'.'+f for r,fields in ROOT_FIELDS.items() for f,k in fields.items() if k=='int'}
    count=0
    for item in ordinary:
        count+=1;ns,key=item['namespace'],item['typed_key'];total+=len(ns.encode())+len(key)
        change=replace(item['change'],key=codec.decode(key),value=None if item['change'].delete else codec.decode(item['payload']))
        if count+len(versions)>MAX_ROWS or change.delete or change.memberships:return False
        row=store.db.execute("SELECT CASE WHEN typeof(payload)='blob' AND length(payload)<=? THEN payload END,payload_checksum,codec_version,record_schema,last_changed_generation FROM records WHERE namespace=? AND typed_key=?",(MAX_BYTES,ns,key)).fetchone()
        if row is None:return False
        payload,checksum,version,schema,revision=row
        if type(payload) is not bytes:return False
        total+=len(payload)+len(item['payload'] or b'')
        if total>MAX_BYTES or schema!=change.record_schema:return False
        if checksum!=_record_checksum(ns,key,schema,version,revision,payload) or records._map(store).get(ra.root,record_key(ns,key))!=record_commitment(ns,key,last_changed_generation=revision,codec_version=version,record_schema=schema,payload=payload):raise StoreIntegrityError('value transition ordinary predecessor lacks accepted content')
        if ns==EVENT_STORAGE and change.key==COMMIT_DESCRIPTOR_KEY:
            if schema!=1 or codec.encode((1,g+1,codec.decode(request.token)))!=item['payload']:raise StoreIntegrityError('value transition session receipt disagreement')
        elif ns in scalars:
            if ns=='world.next_event' and item['payload']!=payload:return False
            v=change.value;before=codec.decode(payload)
            if change.key!=0 or type(v) is not tuple or len(v)!=2 or v[0]!=0 or type(v[0]) is not int or type(v[1]) is not int or type(before) is not tuple or before[0]!=0:return False
        elif ns in world.FAMILIES and ns not in ('world.events','world.event_ids'):
            before=codec.decode(payload);after=change.value
            if (type(before) is not tuple or type(after) is not tuple or len(before)!=2 or len(after)!=2
                    or type(before[0]) is not int or type(after[0]) is not int or before[0]!=after[0]):return False
            if not _projection(store,request,ns,change.key,before,after,ordinary=True):return False
            owners[(ns,key)]=change;ordinary_owners.add((ns,key))
        elif ns in catalog.IDENTITY_OWNER_FAMILIES:
            if item['payload']!=payload:return False
            owners[(ns,key)]=change;ordinary_owners.add((ns,key))
        elif item['payload']!=payload:return False
    witnessed=set()
    for item,old,value in headers:
        change=item['change'];owner_ns,owner_key=change.key;marker=owner_ns,codec.encode(owner_key);source=owners.get(marker)
        if source is None:
            approved=(request.tail_new or {}).get((item['namespace'],item['typed_key']))
            if marker in (request.tail_removed or {}) and approved is not None:
                if item['payload']!=approved:raise StoreIntegrityError('inactive owner differs from frozen authority')
                continue
            if item['payload']!=old.payload or item['memberships_blob']!=old.memberships:return False
            continue
        kind='ordinary' if marker in ordinary_owners else 'lazy'
        approved=(request.tail_new or {}).get((item['namespace'],item['typed_key']))
        if approved is not None:
            if item['payload']!=approved:raise StoreIntegrityError('revived owner differs from frozen authority')
            witnessed.add(marker);continue
        if old is None:raise StoreIntegrityError('unproved new owner witness')
        expected=list(value)
        if len(expected)!=9 or expected[0]!='identity-owner/v1' or expected[1] is not True or expected[2]!=kind:return False
        expected[3]=g+1;expected[4]=source.record_schema;expected[5]=catalog._source_commitment(codec,source,kind,g+1)
        if codec.encode(tuple(expected))!=item['payload'] or item['memberships_blob']!=old.memberships:raise StoreIntegrityError('value transition source witness differs from changed owner')
        witnessed.add(marker)
    if witnessed!=set(owners):raise StoreIntegrityError('value transition lacks changed owner source witness')
    return True
