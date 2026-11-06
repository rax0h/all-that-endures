"""Accepted native collection state, point order and bounded key windows.

The World manifest binds the component envelope. Native shapes and the existing
publisher remain unchanged; query/identity admission is deliberately separate.
"""
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _namespace_checksum,_order_checksum
from .persistence_proof_content import version_key
from .persistence_proof_nodes import Root
from .persistence_proof_order import query_order_key
from .persistence_proof_seek import OrderedSeekMap,MAX_KEY_BYTES as SEEK_KEY_BYTES
from .persistence_sqlite_guard import require_persistent_sources
from .persistence_proof_native_window import scalar_fields as _order_fields,physical_window
from . import persistence_proof_native_sources as sources
from . import persistence_proof_collection_directory as directory
from . import persistence_proof_collection as collection
from . import persistence_proof_publication as content

MAX_KEY_BYTES=SEEK_KEY_BYTES-8
MAX_METADATA_BYTES=1048576


def _collection(store,authority,namespace):
    require_persistent_sources(store.db)
    components=authority.read_components
    if components is None:
        raise StoreIntegrityError('native collection lacks accepted component context')
    pair=components[4];certificate=pair[0]
    if (certificate.store_identity,certificate.generation,certificate.codec_version)!=(
            store.store_identity,authority.read_pin.captured_head,store.codec.version):
        raise StoreConflictError('native collection component context differs')
    key=(pair[1],directory._key(namespace))
    scope=getattr(store,'_validation_scope',None)
    cached=None if scope is None else scope.lookup('native-collection',key)
    if cached is not None:
        child=None if not cached[0] else collection.CollectionCertificate(store.store_identity,certificate.generation,store.codec.version,
            namespace,True,cached[1],cached[2],Root(cached[3],cached[4]))
    else:
        value=OrderedSeekMap(store.db,directory.domain(certificate.store_identity,certificate.codec_version)).get(certificate.root,key[1])
        selected=None if value is None else directory._descriptor(store,certificate,key[1],value)
        child=None if selected is None else selected[0]
        if scope is not None:
            summary=(False,) if child is None else (True,child.member_count,child.next_ordinal,child.root.digest,child.root.count)
            scope.remember('native-collection',key,summary)
    state=_state(store,certificate.generation,namespace,child)
    if child is None:
        # At the current head even a future-only orphan is impossible. Once
        # introduced, a namespace remains declared throughout its history.
        for table,kind in (('lazy_order_versions','order'),('lazy_record_versions','record')):
            if store.db.execute('SELECT 1 FROM '+table+' INDEXED BY ate_directory_'+kind+'_namespace_start WHERE namespace=? LIMIT 1',(namespace,)).fetchone():
                raise StoreIntegrityError('native namespace absence has orphan source')
    return child,state


def state_row(store,authority,generation,namespace):
    with sources._snapshot(store,authority,generation):
        _child,row=_collection(store,authority,namespace)
        return row


def _state(store,generation,namespace,child):
    if store.db.execute('SELECT 1 FROM lazy_namespace_state INDEXED BY lazy_namespace_interval WHERE namespace=? AND valid_to>? LIMIT 1',(namespace,generation)).fetchone():
        raise StoreIntegrityError('native current namespace has future closure')
    rows=store.db.execute('SELECT '+
        "CASE WHEN typeof(member_count)='integer' THEN member_count END,"
        "CASE WHEN typeof(next_ordinal)='integer' THEN next_ordinal END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END"+
        ' FROM lazy_namespace_state INDEXED BY lazy_namespace_interval WHERE namespace=? AND valid_to IS NULL LIMIT 2',(namespace,)).fetchall()
    store._metadata_rows+=len(rows)
    if child is None:
        if rows:raise StoreIntegrityError('native state differs from accepted namespace absence')
        return None
    if len(rows)!=1:raise StoreIntegrityError('native state missing or overlapping accepted namespace')
    count,next_id,start,end,end_type,checksum=rows[0]
    if (count!=child.member_count or next_id!=child.next_ordinal or type(start) is not int
            or not 0<=start<=generation or end_type!='null' or end is not None
            or checksum!=_namespace_checksum(namespace,count,next_id,start,end)):
        raise StoreIntegrityError('native state differs from accepted collection')
    return count,next_id,start,end

def _check_order(namespace,typed,row,generation,child):
    ordinal,start,end,end_type,checksum=row
    if (child is None or type(ordinal) is not int or not 0<=ordinal<child.next_ordinal
            or type(start) is not int or not 0<=start<=generation or end_type!='null' or end is not None
            or checksum!=_order_checksum(namespace,typed,ordinal,start,end)):
        raise StoreIntegrityError('native order metadata differs from accepted collection')
    return ordinal,start,end


def order_row(store,authority,generation,namespace,typed):
    sources._locator(namespace,typed)
    with sources._snapshot(store,authority,generation) as manifest:
        child,_state_row=_collection(store,authority,namespace)
        if store.db.execute('SELECT 1 FROM lazy_order_versions INDEXED BY lazy_order_interval WHERE namespace=? AND typed_key=? AND valid_to>? LIMIT 1',
                (namespace,typed,generation)).fetchone():raise StoreIntegrityError('native current point order has future closure')
        rows=store.db.execute('SELECT '+_order_fields()+' FROM lazy_order_versions INDEXED BY lazy_order_interval WHERE namespace=? AND typed_key=? AND valid_to IS NULL LIMIT 2',
            (namespace,typed)).fetchall()
        store._metadata_rows+=len(rows)
        if len(rows)>1:raise StoreIntegrityError('overlapping native collection order')
        if not rows:
            # Accepted World construction/publication guarantees one order per
            # lazy version; this supplies authenticated negative key selection.
            if content._map(store).get(manifest.roots[0],version_key(namespace,typed)) is not None:
                raise StoreIntegrityError('native order missing for accepted source')
            return None
        ordinal,start,end=_check_order(namespace,typed,rows[0],generation,child)
        if len(typed)>MAX_KEY_BYTES:raise StoreIntegrityError('native order key exceeds accepted seek path')
        d=collection.domain(store.store_identity,store.codec.version,namespace)
        m=OrderedSeekMap(store.db,d)
        if m.get(child.root,query_order_key(ordinal,typed))!=collection.member(d,typed,ordinal):
            raise StoreIntegrityError('native order differs from accepted collection leaf')
        return ordinal,start,end


def _positions(store,child,after,limit):
    if child is None:return (),True
    d=collection.domain(store.store_identity,store.codec.version,child.namespace)
    m=OrderedSeekMap(store.db,d);positions=[];consumed=len(child.namespace.encode());cursor=after
    for _ in range(limit+1):
        page=m.page(child.root,after=cursor,limit=1)
        if not page:return tuple(positions),True
        position,value=page[0]
        if not 8<=len(position)<=MAX_KEY_BYTES+8:raise StoreIntegrityError('invalid native order proof position')
        ordinal,typed=int.from_bytes(position[:8],'big'),position[8:]
        if ordinal>=child.next_ordinal or value!=collection.member(d,typed,ordinal):
            raise StoreIntegrityError('invalid accepted native collection member')
        # Reserve both proof and physical fields, including fixed header fields.
        cost=2*len(typed)+256
        if consumed+cost>MAX_METADATA_BYTES:
            if len(positions)<2:raise StoreError('native order window exceeds metadata budget')
            return tuple(positions),False
        positions.append((typed,ordinal));consumed+=cost;cursor=position
    return tuple(positions),False


def _physical_window(store,generation,namespace,after,limit,positions):
    # At the accepted current head no order can close in a future generation.
    # The closed-generation prefix probes that contradiction without history scan.
    if store.db.execute('SELECT 1 FROM lazy_order_versions INDEXED BY lazy_order_closed_generation WHERE namespace=? AND valid_to>? LIMIT 1',
            (namespace,generation)).fetchone():
        raise StoreIntegrityError('native current order has future closure')
    return physical_window(store,generation,namespace,after,limit,positions,max_key_bytes=MAX_KEY_BYTES)


def _checked_key(store,generation,namespace,typed):
    record=store._visible_record_row(generation,namespace,typed)
    if record is None:raise StoreIntegrityError('accepted ordered key lacks its source')
    store._check_record_row(namespace,typed,record,decode=False)
    return store.codec.decode(typed)


def iter_keys(store,authority,pin,namespace,page_size):
    def iterator():
        after=None;yielded=0;accepted_epoch=authority.epoch
        while True:
            with sources._snapshot(store,authority,pin.captured_head,pin=pin):
                child,_state_row=_collection(store,authority,namespace)
                positions,exhausted=_positions(store,child,None if after is None else query_order_key(*after),page_size)
                # At the last window also probe one physical surplus slot.
                rows=_physical_window(store,pin.captured_head,namespace,after,len(positions)+int(exhausted),positions)
                actual=[]
                for typed,*row in rows:
                    ordinal,_start,_end=_check_order(namespace,typed,row,pin.captured_head,child)
                    actual.append((typed,ordinal))
                if tuple(actual)!=positions:
                    raise StoreIntegrityError('native physical order window differs from accepted collection')
                selected=positions if exhausted else positions[:-1]
                decoded=[]
                for typed,ordinal in selected:
                    decoded.append((ordinal,typed,_checked_key(store,pin.captured_head,namespace,typed)))
                store._temporary_keys_peak=max(store._temporary_keys_peak,len(decoded))
            for ordinal,typed,key in decoded:
                yielded+=1;after=(ordinal,typed)
                yield key
                # A caller may save or another connection may write while this
                # page is paused. Never expose the remaining old keys afterward.
                if sources.active(store) is not authority:
                    raise StoreConflictError('native key iterator cannot resume in publisher context')
                if authority.epoch!=accepted_epoch:
                    raise StoreConflictError('native key iterator accepted epoch changed')
                sources.before_snapshot(store,authority,pin)
            if exhausted:
                if yielded!=(0 if child is None else child.member_count):
                    raise StoreIntegrityError('native collection ended before accepted count')
                return
    return iterator()
