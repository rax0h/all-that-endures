"""Native minimum neighbors authenticated against a distinct rank-ordered root."""
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _query_checksum
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_query import QueryScope
from .persistence_proof_native_query import _selected_key
from .persistence_proof_native_window import scalar_fields,MAX_METADATA_BYTES
from .persistence_sqlite_guard import require_persistent_sources
from . import persistence_proof_rank as ranks
from . import persistence_proof_scope as scopes
from . import persistence_proof_native_sources as sources


def available(authority):
    if authority.read_components is None:raise StoreIntegrityError('native rank lacks accepted component context')
    count=len(authority.read_components[1][0].roots)
    if count not in (6,7):raise StoreIntegrityError('native rank has unsupported component context')
    return count==7


def _root(store,authority,pin,scope):
    require_persistent_sources(store.db)
    if not available(authority):raise StoreError('native rank requires accepted rank-index authority')
    certificate=authority.read_components[1][0]
    if (certificate.store_identity,certificate.generation,certificate.codec_version)!=(store.store_identity,pin.captured_head,store.codec.version):
        raise StoreConflictError('native rank component context differs')
    ranks.index(store)
    return scopes._resolve(store,certificate,scope)


def _physical(store,generation,scope,positions,*,bound,before,continuation):
    """Compare an indexed physical window without transferring unknown rank/key bytes."""
    if store.db.execute('SELECT 1 FROM lazy_query_versions INDEXED BY ate_rank_query_closed '
            'WHERE namespace=? AND index_name=? AND valid_to>? LIMIT 1',
            (scope.namespace,scope.index_name,generation)).fetchone():
        raise StoreIntegrityError('native rank has future closure')
    where='namespace=? AND index_name=? AND valid_to IS NULL';args=[scope.namespace,scope.index_name]
    op='<' if before else '>'
    if continuation is not None:
        where+=' AND (index_value,ordinal,record_key)'+op+'(?,?,?)';args.extend(continuation)
    elif bound is not None:
        where+=' AND (index_value,ordinal)'+op+'(?,?)';args.extend(bound)
    direction=' DESC' if before else ' ASC'
    ordering=','.join(c+direction for c in ('index_value','ordinal','record_key'))
    physical_ordering=','.join('lazy_query_versions.'+c+direction for c in ('index_value','ordinal','record_key'))
    suffix=' FROM lazy_query_versions INDEXED BY lazy_query_current WHERE '+where+' ORDER BY '+physical_ordering+' LIMIT 2'
    sizes=store.db.execute("SELECT CASE WHEN typeof(index_value)='blob' THEN length(index_value) END,"
        "CASE WHEN typeof(record_key)='blob' THEN length(record_key) END,"+scalar_fields()+suffix,args).fetchall()
    store._metadata_rows+=len(sizes)
    for rsize,ksize,ordinal,start,end,end_type,checksum in sizes:
        if (type(rsize) is not int or type(ksize) is not int or not 0<=rsize<=ranks.MAX_FIELD_BYTES
                or not 0<=ksize<=ranks.MAX_FIELD_BYTES or type(ordinal) is not int or not 0<=ordinal<2**63
                or type(start) is not int or not 0<=start<=generation or end_type!='null' or end is not None
                or type(checksum) is not str):raise StoreIntegrityError('invalid rank physical window metadata')
    charged=len(scopes._scope_key(scope))+sum(r+k+128 for r,k,*_ in sizes)+sum(len(r)+len(k)+128 for r,o,k in positions)
    if charged>MAX_METADATA_BYTES:raise StoreError('rank window exceeds metadata budget')
    wanted='VALUES '+','.join('(?,?,?,?)' for _ in positions) if positions else 'SELECT 0,NULL,NULL,NULL WHERE 0'
    wanted_args=[v for i,(rank,ordinal,key) in enumerate(positions,1) for v in (i,rank,ordinal,key)]
    columns=("CASE WHEN typeof(index_value)='blob' AND length(index_value)<=4096 THEN index_value END AS index_value,"
        "CASE WHEN typeof(record_key)='blob' AND length(record_key)<=4096 THEN record_key END AS record_key,"
        "CASE WHEN typeof(ordinal)='integer' THEN ordinal END AS ordinal,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END AS valid_from,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END AS valid_to,"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END AS row_checksum")
    sql=('WITH physical AS MATERIALIZED (SELECT '+columns+suffix+'),'
        'ranked AS (SELECT row_number() OVER (ORDER BY '+ordering+') AS slot,* FROM physical),'
        'wanted(slot,rank,position,typed) AS ('+wanted+') '
        'SELECT CASE WHEN r.index_value=w.rank AND r.ordinal=w.position AND r.record_key=w.typed THEN 1 ELSE 0 END,'
        +scalar_fields('r.')+' FROM ranked r LEFT JOIN wanted w ON r.slot=w.slot ORDER BY r.slot')
    rows=store.db.execute(sql,(*args,*wanted_args)).fetchall()
    if len(rows)!=len(positions):raise StoreIntegrityError('native rank window misses accepted position')
    for (rank,ordinal,key),(matches,actual,start,end,end_type,checksum) in zip(positions,rows):
        if (matches!=1 or actual!=ordinal or end_type!='null' or end is not None
                or checksum!=_query_checksum(scope.namespace,scope.index_name,rank,key,ordinal,start,end)):
            raise StoreIntegrityError('native rank window differs from accepted positions')
    store._query_rows+=len(rows)


def _bounded_encode(store,value):
    """Bound source shape before allocating the codec's JSON/base64 representation."""
    from dataclasses import fields
    from .persistence_lazy_nested_history import HistoryReference
    from .persistence_record_headers import RecordReference
    from .persistence_event_id_reference import EventIdReference
    from .persistence_nonreflexive_keys import NonreflexiveKeyReference
    pending=[(value,0)];remaining=ranks.MAX_FIELD_BYTES
    references=(HistoryReference,RecordReference,EventIdReference,NonreflexiveKeyReference)
    while pending:
        item,depth=pending.pop();kind=type(item);remaining-=1
        if depth>64 or remaining<0:raise StoreError('rank input exceeds metadata shape budget')
        if kind in (str,bytes):remaining-=len(item)
        elif kind is int:remaining-=(item.bit_length()*30103)//100000+1
        elif item is None or kind in (bool,float):pass
        elif kind in (tuple,frozenset):
            if len(item)>remaining:raise StoreError('rank key exceeds metadata budget')
            pending.extend((v,depth+1) for v in item)
        elif kind in store.codec._enum_by_type:
            remaining-=len(item.name)+len(store.codec._enum_by_type[kind])
        elif kind in references or kind in store.codec._record_by_type:
            pending.extend((getattr(item,f.name),depth+1) for f in fields(item))
        else:raise StoreIntegrityError('unsupported native rank key shape')
        if remaining<0:raise StoreError('rank field exceeds metadata budget')
    encoded=store.codec.encode(value)
    if len(encoded)>ranks.MAX_FIELD_BYTES:raise StoreError('rank encoded field exceeds metadata budget')
    return encoded


def _keep_snapshot(store,authority,pin,epoch):
    require_persistent_sources(store.db)
    if authority.epoch!=epoch or not store.db.in_transaction:
        raise StoreConflictError('native rank lost original accepted snapshot')
    if sources.active(store) is not authority:raise StoreConflictError('native rank entered publisher context')
    sources.before_snapshot(store,authority,pin)


def neighbor(store,authority,pin,namespace,index_name,*,rank=None,ordinal=None,before=False,exclude=()):
    require_persistent_sources(store.db)
    if any(type(v) is not str or not 0<len(v)<=ranks.MAX_FIELD_BYTES for v in (namespace,index_name)):
        raise StoreError('rank scope exceeds field budget')
    scope=ranks.RankScope(namespace,index_name);scopes._scope_key(scope)
    if not ranks.ranked(namespace,index_name) or type(before) is not bool:raise StoreError('unsupported ranked query')
    if rank is not None and (type(rank) is not str or type(ordinal) is not int or not 0<=ordinal<2**63):
        raise StoreIntegrityError('invalid native rank boundary')
    epoch=authority.epoch
    with sources._snapshot(store,authority,pin.captured_head,pin=pin):
        root=_root(store,authority,pin,scope);domain=scopes._seek_domain(store,scope)
        encoded=None if rank is None else _bounded_encode(store,rank)
        excluded=set();charged=len(scopes._scope_key(scope))
        for key in exclude:
            typed=_bounded_encode(store,key);charged+=len(typed)+128
            if charged>MAX_METADATA_BYTES:raise StoreError('rank exclusions exceed metadata budget')
            excluded.add(typed)
        _keep_snapshot(store,authority,pin,epoch)
        m=OrderedSeekMap(store.db,domain);bound=None if rank is None else (encoded,ordinal)
        cursor=None if bound is None else ranks.position(encoded,ordinal,b'' if before else b'\xff'*ranks.MAX_FIELD_BYTES)
        continuation=None
        while True:
            page=m.reverse_page(root,before=cursor,limit=2) if before else m.page(root,after=cursor,limit=2)
            positions=[]
            for raw,value in page:
                position=ranks.parse_position(raw)
                if value!=ranks.member(domain,*position):raise StoreIntegrityError('invalid accepted rank member')
                positions.append(position)
            _physical(store,pin.captured_head,scope,positions,bound=bound,before=before,continuation=continuation)
            if not positions:
                _keep_snapshot(store,authority,pin,epoch)
                return None
            encoded_rank,actual_ordinal,typed=positions[0]
            key=_selected_key(store,pin.captured_head,QueryScope(namespace,index_name,encoded_rank),typed,actual_ordinal)
            _keep_snapshot(store,authority,pin,epoch)
            rank_value=store.codec.decode(encoded_rank)
            if type(rank_value) is not str or store.codec.encode(rank_value)!=encoded_rank:raise StoreIntegrityError('noncanonical native rank value')
            _keep_snapshot(store,authority,pin,epoch)
            if typed not in excluded:return rank_value,actual_ordinal,key
            cursor=page[0][0];continuation=positions[0]
