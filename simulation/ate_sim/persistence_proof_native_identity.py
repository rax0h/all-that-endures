"""Accepted native allocator and bidirectional identity occurrence reads."""
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _identity_state_checksum,_identity_occurrence_checksum
from .persistence_proof_occurrence import OwnerScope,GroupScope,RawOccurrence,occurrence_domain,member_commitment,group_order_key
from .persistence_proof_occurrence_seek import _decode_group_position
from .persistence_proof_nodes import Root
from .persistence_proof_seek import OrderedSeekMap
from .persistence_sqlite_guard import require_persistent_sources
from . import persistence_proof_scope as scopes
from . import persistence_proof_native_sources as sources

MAX_FIELD_BYTES=4096
MAX_METADATA_BYTES=1048576


def _context(store,authority):
    require_persistent_sources(store.db)
    pairs=authority.read_components
    if pairs is None:raise StoreIntegrityError('native identity lacks accepted component context')
    cert=pairs[1][0];manifest=authority.pair[0]
    if (cert.store_identity,cert.generation,cert.codec_version)!=(store.store_identity,manifest.generation,store.codec.version):
        raise StoreConflictError('native identity component context differs')
    if cert.next_incarnation_id!=manifest.head.next_incarnation_id:raise StoreIntegrityError('accepted identity allocators disagree')
    return cert,pairs[1][1]


def _root(store,authority,scope,context):
    cert,expected=context
    if type(scope) is GroupScope and scope.incarnation_id>=cert.next_incarnation_id:
        return OrderedSeekMap(None,scopes._seek_domain(store,scope)).empty
    encoded=scopes._scope_key(scope);key=(expected,encoded);cache=getattr(store,'_validation_scope',None)
    cached=None if cache is None else cache.lookup('native-identity',key)
    if cached is not None:return Root(*cached)
    root=scopes._resolve(store,cert,scope)
    if cache is not None:cache.remember('native-identity',key,(root.digest,root.count))
    return root


def _state(store,generation,expected):
    if store.db.execute('SELECT 1 FROM lazy_identity_state INDEXED BY lazy_identity_state_interval WHERE valid_to>? LIMIT 1',(generation,)).fetchone():
        raise StoreIntegrityError('native current allocator has future closure')
    rows=store.db.execute("SELECT CASE WHEN typeof(next_incarnation_id)='integer' THEN next_incarnation_id END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END "
        'FROM lazy_identity_state INDEXED BY lazy_identity_state_interval WHERE valid_to IS NULL LIMIT 2').fetchall()
    store._metadata_rows+=len(rows)
    if len(rows)!=1:raise StoreIntegrityError('native allocator missing or overlapping')
    number,start,checksum=rows[0]
    if (number!=expected or type(start) is not int or not 0<=start<=generation
            or checksum!=_identity_state_checksum(number,start,None)):
        raise StoreIntegrityError('native allocator differs from accepted manifest')
    return number,start,None


def state_row(store,authority,generation):
    with sources._snapshot(store,authority,generation):
        context=_context(store,authority)
        return _state(store,generation,context[0].next_incarnation_id)


def _fields(namespace,key,path):
    if (type(namespace) is not str or not namespace or '\x00' in namespace or type(key) is not bytes or type(path) is not bytes
            or max(len(namespace.encode()),len(key),len(path))>MAX_FIELD_BYTES):
        raise StoreError('native identity locator exceeds field path or is invalid')


def _columns():
    return ("CASE WHEN typeof(incarnation_id)='integer' THEN incarnation_id END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")


def _point(store,authority,generation,namespace,key,path,context):
    _fields(namespace,key,path);args=(namespace,key,path)
    if store.db.execute('SELECT 1 FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_occurrence_interval WHERE owner_namespace=? AND owner_key=? AND occurrence_path=? AND valid_to>? LIMIT 1',(*args,generation)).fetchone():
        raise StoreIntegrityError('native current occurrence has future closure')
    rows=store.db.execute('SELECT '+_columns()+' FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_occurrence_interval WHERE owner_namespace=? AND owner_key=? AND occurrence_path=? AND valid_to IS NULL LIMIT 2',args).fetchall()
    store._metadata_rows+=len(rows)
    scope=OwnerScope(namespace,key);root=_root(store,authority,scope,context)
    domain=occurrence_domain(store.store_identity,store.codec.version,scope)
    wanted=OrderedSeekMap(store.db,scopes._seek_domain(store,scope)).get(root,path)
    if not rows:
        if wanted is not None:raise StoreIntegrityError('native occurrence missing from accepted owner')
        return None
    if len(rows)!=1:raise StoreIntegrityError('native occurrence overlaps current owner placement')
    inc,start,end,end_type,checksum=rows[0]
    if (type(inc) is not int or not 0<inc<context[0].next_incarnation_id or type(start) is not int or not 0<=start<=generation
            or end is not None or end_type!='null' or checksum!=_identity_occurrence_checksum(namespace,key,path,inc,start,end)):
        raise StoreIntegrityError('invalid native occurrence interval or checksum')
    raw=RawOccurrence(namespace,key,path,inc)
    if member_commitment(domain,raw)!=wanted:raise StoreIntegrityError('native occurrence differs from accepted owner root')
    group=GroupScope(inc);group_root=_root(store,authority,group,context)
    actual=OrderedSeekMap(store.db,scopes._seek_domain(store,group)).get(group_root,group_order_key(namespace,key,path))
    if actual!=member_commitment(occurrence_domain(store.store_identity,store.codec.version,group),raw):
        raise StoreIntegrityError('native occurrence differs from accepted group root')
    return inc,start,end,checksum


def point_row(store,authority,generation,namespace,key,path):
    with sources._snapshot(store,authority,generation):
        context=_context(store,authority);_state(store,generation,context[0].next_incarnation_id)
        return _point(store,authority,generation,namespace,key,path,context)


def _next(store,generation,scope,after,fields,incarnation):
    if type(scope) is not OwnerScope:raise StoreIntegrityError('physical next requires owner scope')
    index='lazy_identity_occurrence_current';where='owner_namespace=? AND owner_key=? AND valid_to IS NULL'
    args=[scope.namespace,scope.typed_key]
    if after is not None:where+=' AND (occurrence_path,incarnation_id)>(?,?)';args.extend((after[2],after[3]))
    ordering='occurrence_path,incarnation_id'
    if fields is None:match='0';wanted=[]
    else:
        match='owner_namespace=? AND owner_key=? AND occurrence_path=? AND incarnation_id=?'
        wanted=[*fields,incarnation]
    row=store.db.execute('SELECT CASE WHEN '+match+' THEN 1 ELSE 0 END,'+_columns()+
        ' FROM lazy_identity_occurrence_versions INDEXED BY '+index+' WHERE '+where+' ORDER BY '+ordering+' LIMIT 1',(*wanted,*args)).fetchone()
    store._metadata_rows+=int(row is not None)
    if row is None:
        if fields is not None:raise StoreIntegrityError('native identity window misses accepted locator')
    elif fields is None or row[0]!=1:raise StoreIntegrityError('native identity window has extra or changed locator')
    elif (type(row[1]) is not int or row[1]!=incarnation or type(row[2]) is not int or not 0<=row[2]<=generation
            or row[3] is not None or row[4]!='null'
            or row[5]!=_identity_occurrence_checksum(*fields,row[1],row[2],row[3])):
        raise StoreIntegrityError('native identity window scalar metadata differs')


def _positions(store,scope,root,after):
    m=OrderedSeekMap(store.db,scopes._seek_domain(store,scope));rows=[];charged=len(scopes._scope_key(scope))
    for _ in range(129):
        page=m.page(root,after=after,limit=1)
        if not page:return tuple(rows),True
        position,value=page[0]
        fields=(scope.namespace,scope.typed_key,position) if type(scope) is OwnerScope else _decode_group_position(position)
        _fields(*fields);cost=2*sum(len(x.encode()) if type(x) is str else len(x) for x in fields)+256
        if charged+cost>MAX_METADATA_BYTES:
            if len(rows)<2:raise StoreError('native identity window exceeds metadata budget')
            return tuple(rows),False
        rows.append((position,value,fields));charged+=cost;after=position
    return tuple(rows),False


def _decode(store,fields,inc,owner):
    namespace,key,path=fields;decoded_key=store.codec.decode(key);decoded_path=store.codec.decode(path)
    if type(decoded_path) is not tuple or store.codec.encode(decoded_key)!=key or store.codec.encode(decoded_path)!=path:
        raise StoreIntegrityError('noncanonical native identity locator')
    if any(type(c) is not tuple or len(c)!=2 or c[0] not in ('field','key','index')
            or c[0]=='field' and (type(c[1]) is not str or not c[1])
            or c[0]=='index' and (type(c[1]) is not int or c[1]<0) for c in decoded_path):
        raise StoreIntegrityError('invalid native identity path component')
    return (decoded_path,inc) if owner else (namespace,decoded_key,decoded_path)


def iter_occurrences(store,authority,pin,scope):
    def iterator():
        accepted_epoch=authority.epoch;cursor=None;physical_after=None;visited=0;physical_count=None
        while True:
            with sources._snapshot(store,authority,pin.captured_head,pin=pin):
                context=_context(store,authority);_state(store,pin.captured_head,context[0].next_incarnation_id)
                root=_root(store,authority,scope,context)
                if type(scope) is OwnerScope:
                    closed='lazy_identity_owner_interval';where='owner_namespace=? AND owner_key=?';args=(scope.namespace,scope.typed_key)
                else:closed='lazy_identity_incarnation_interval';where='incarnation_id=?';args=(scope.incarnation_id,)
                if store.db.execute('SELECT 1 FROM lazy_identity_occurrence_versions INDEXED BY '+closed+' WHERE '+where+' AND valid_to>? LIMIT 1',(*args,pin.captured_head)).fetchone():
                    raise StoreIntegrityError('native identity scope has future closure')
                if type(scope) is GroupScope and physical_count is None:
                    physical_count=store.db.execute('SELECT count(*) FROM lazy_identity_occurrence_versions INDEXED BY lazy_identity_incarnation_interval WHERE incarnation_id=? AND valid_to IS NULL',(scope.incarnation_id,)).fetchone()[0]
                    if physical_count!=root.count:raise StoreIntegrityError('native group physical count differs from accepted scope')
                positions,exhausted=_positions(store,scope,root,cursor);checked=[];scan_after=physical_after
                for position,wanted,fields in positions:
                    row=_point(store,authority,pin.captured_head,*fields,context)
                    if row is None:raise StoreIntegrityError('accepted identity position lacks physical source')
                    inc=row[0];raw=RawOccurrence(*fields,inc)
                    if wanted!=member_commitment(occurrence_domain(store.store_identity,store.codec.version,scope),raw):
                        raise StoreIntegrityError('native occurrence differs from accepted selected scope')
                    if type(scope) is OwnerScope:_next(store,pin.captured_head,scope,scan_after,fields,inc)
                    scan_after=(*fields,inc)
                    checked.append((position,fields,inc))
                if exhausted and type(scope) is OwnerScope:_next(store,pin.captured_head,scope,scan_after,None,None)
                selected=checked if exhausted else checked[:-1];visited+=len(selected)
                if visited>root.count or exhausted and visited!=root.count:raise StoreIntegrityError('native identity window count differs')
                decoded=[_decode(store,fields,inc,type(scope) is OwnerScope) for _pos,fields,inc in selected]
                if selected:cursor,fields,inc=selected[-1];physical_after=(*fields,inc)
            for value in decoded:
                yield value
                if sources.active(store) is not authority or authority.epoch!=accepted_epoch:
                    raise StoreConflictError('native identity iterator authority or accepted epoch changed')
                sources.before_snapshot(store,authority,pin)
            if exhausted:return
    return iterator()
