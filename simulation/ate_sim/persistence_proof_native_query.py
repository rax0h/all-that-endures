"""Native query membership selection bound to the accepted scoped roots."""
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _query_checksum
from .persistence_proof_nodes import Root
from .persistence_proof_query import QueryScope,query_domain,member_commitment,MAX_QUERY_KEY_BYTES
from .persistence_proof_order import query_order_key
from .persistence_proof_seek import OrderedSeekMap
from .persistence_sqlite_guard import require_persistent_sources
from .persistence_proof_native_window import physical_window,MAX_METADATA_BYTES
from . import persistence_proof_native_sources as sources
from . import persistence_proof_scope as scopes


def _root(store,authority,scope):
    require_persistent_sources(store.db)
    components=authority.read_components
    if components is None:raise StoreIntegrityError('native query lacks accepted component context')
    pair=components[1];certificate=pair[0]
    if (certificate.store_identity,certificate.generation,certificate.codec_version)!=(
            store.store_identity,authority.read_pin.captured_head,store.codec.version):
        raise StoreConflictError('native query component context differs')
    key=(pair[1],scopes._scope_key(scope));cache=getattr(store,'_validation_scope',None)
    summary=None if cache is None else cache.lookup('native-query',key)
    if summary is not None:return Root(*summary)
    root=scopes._resolve(store,certificate,scope)
    if cache is not None:cache.remember('native-query',key,(root.digest,root.count))
    return root


def _positions(store,scope,root,after):
    m=OrderedSeekMap(store.db,scopes._seek_domain(store,scope));positions=[]
    consumed=len(scope.namespace.encode())+len(scope.index_name.encode())+len(scope.index_value)
    domain=query_domain(store.store_identity,store.codec.version,scope)
    cursor=None if after is None else query_order_key(*after)
    for _ in range(129):
        page=m.page(root,after=cursor,limit=1)
        if not page:return tuple(positions),True
        position,value=page[0]
        if not 8<=len(position)<=MAX_QUERY_KEY_BYTES+8:raise StoreIntegrityError('invalid native query proof position')
        ordinal,typed=int.from_bytes(position[:8],'big'),position[8:]
        if ordinal>=2**63 or value!=member_commitment(domain,typed,ordinal):raise StoreIntegrityError('invalid accepted native query member')
        cost=2*len(typed)+256
        if consumed+cost>MAX_METADATA_BYTES:
            if len(positions)<2:raise StoreError('native query window exceeds metadata budget')
            return tuple(positions),False
        positions.append((typed,ordinal));consumed+=cost;cursor=position
    return tuple(positions),False


def _window(store,generation,scope,after,positions,exhausted):
    if store.db.execute('SELECT 1 FROM lazy_query_versions INDEXED BY lazy_query_closed_generation WHERE namespace=? AND index_name=? AND index_value=? AND valid_to>? LIMIT 1',
            (scope.namespace,scope.index_name,scope.index_value,generation)).fetchone():
        raise StoreIntegrityError('native current query has future closure')
    rows=physical_window(store,generation,scope.namespace,after,len(positions)+int(exhausted),positions,
        query=(scope.index_name,scope.index_value),max_key_bytes=MAX_QUERY_KEY_BYTES)
    if len(rows)!=len(positions):raise StoreIntegrityError('native query window misses accepted position')
    for (wanted,ordinal),(typed,actual,start,end,end_type,checksum) in zip(positions,rows):
        if (typed!=wanted or actual!=ordinal or end_type!='null' or end is not None
                or checksum!=_query_checksum(scope.namespace,scope.index_name,scope.index_value,typed,ordinal,start,end)):
            raise StoreIntegrityError('native query differs from accepted membership')


def _selected_key(store,generation,scope,typed,ordinal):
    row=store._visible_record_row(generation,scope.namespace,typed)
    if row is None:raise StoreIntegrityError('accepted query membership lacks owner source')
    memberships=store._check_record_row(scope.namespace,typed,row,decode=False)[4]
    if not any(name==scope.index_name and position==ordinal and store.codec.encode(value)==scope.index_value
            for name,value,position in memberships):
        raise StoreIntegrityError('accepted query membership differs from owner metadata')
    key=store.codec.decode(typed)
    if store.codec.encode(key)!=typed:raise StoreIntegrityError('noncanonical native query key')
    return key


def iter_memberships(store,authority,pin,namespace,index_name,value,*,limit=None,exclude_keys=()):
    def iterator():
        scope=QueryScope(namespace,index_name,store.codec.encode(value));scopes._scope_key(scope)
        excluded=set();charged=len(scopes._scope_key(scope))
        for key in exclude_keys:
            typed=store.codec.encode(key);charged+=len(typed)+128
            if charged>MAX_METADATA_BYTES:raise StoreError('native query exclusions exceed metadata budget')
            excluded.add(typed)
        after=None;visited=0;yielded=0;accepted_epoch=authority.epoch
        while True:
            with sources._snapshot(store,authority,pin.captured_head,pin=pin):
                root=_root(store,authority,scope)
                if limit==0:return
                positions,exhausted=_positions(store,scope,root,after)
                _window(store,pin.captured_head,scope,after,positions,exhausted)
                selected=positions if exhausted else positions[:-1]
                visited+=len(selected)
                if visited>root.count or exhausted and visited!=root.count:raise StoreIntegrityError('native query ended outside accepted count')
                decoded=[]
                for typed,ordinal in selected:
                    if typed in excluded:continue
                    if limit is not None and yielded+len(decoded)>=limit:break
                    decoded.append((_selected_key(store,pin.captured_head,scope,typed,ordinal),ordinal))
                if selected:typed,ordinal=selected[-1];after=(ordinal,typed)
            for key,ordinal in decoded:
                yielded+=1
                yield key,ordinal
                if sources.active(store) is not authority:raise StoreConflictError('native query iterator cannot resume in publisher context')
                if authority.epoch!=accepted_epoch:raise StoreConflictError('native query iterator accepted epoch changed')
                sources.before_snapshot(store,authority,pin)
            if exhausted or limit is not None and yielded>=limit:return
    return iterator()


def memberships(store,authority,pin,namespace,index_name,value,*,limit=None,exclude_keys=()):
    return tuple(iter_memberships(store,authority,pin,namespace,index_name,value,limit=limit,exclude_keys=exclude_keys))
