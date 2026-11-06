"""Bounded exact physical current-order/query windows for native proof reads."""
from .incremental_store import StoreError,StoreIntegrityError

MAX_METADATA_BYTES=1048576


def scalar_fields(prefix=''):
    ordinal,start,end,checksum=(prefix+n for n in ('ordinal','valid_from','valid_to','row_checksum'))
    return (f"CASE WHEN typeof({ordinal})='integer' THEN {ordinal} END,"
        f"CASE WHEN typeof({start})='integer' THEN {start} END,"
        f"CASE WHEN typeof({end})='integer' THEN {end} END,typeof({end}),"
        f"CASE WHEN typeof({checksum})='text' AND length(CAST({checksum} AS BLOB))=64 THEN {checksum} END")


def physical_window(store,generation,namespace,after,limit,positions,*,query=None,max_key_bytes=32760):
    if type(limit) is not int or not 1<=limit<=129:raise StoreError('invalid native window limit')
    if query is None:
        table,index,key='lazy_order_versions','lazy_order_current','typed_key'
        where='namespace=? AND valid_to IS NULL';args=[namespace];locator=len(namespace.encode())
    else:
        table,index,key='lazy_query_versions','lazy_query_current','record_key'
        name,value=query;where='namespace=? AND index_name=? AND index_value=? AND valid_to IS NULL'
        args=[namespace,name,value];locator=len(namespace.encode())+len(name.encode())+len(value)
    if after is not None:
        ordinal,typed=after;where+=f' AND (ordinal,{key})>(?,?)';args.extend((ordinal,typed))
    suffix=f' FROM {table} INDEXED BY {index} WHERE '+where+f' ORDER BY {table}.ordinal,{table}.{key} LIMIT ?'
    args.append(limit)
    sizes=store.db.execute(f"SELECT CASE WHEN typeof({key})='blob' THEN length({key}) END,"+scalar_fields()+suffix,args).fetchall()
    store._metadata_rows+=len(sizes)
    if any(type(row[0]) is not int or not 0<=row[0]<=max_key_bytes for row in sizes):
        raise StoreIntegrityError('invalid native window key metadata')
    for _size,ordinal,start,end,end_type,checksum in sizes:
        if (type(ordinal) is not int or ordinal<0 or type(start) is not int or not 0<=start<=generation
                or end is not None or end_type!='null' or type(checksum) is not str):
            raise StoreIntegrityError('invalid native scalar metadata before materialization')
    if locator+sum(row[0]+128 for row in sizes)+sum(len(k)+128 for k,_o in positions)>MAX_METADATA_BYTES:
        raise StoreError('native physical window exceeds metadata budget')
    expected_sql='VALUES '+','.join('(?,?,?)' for _ in positions) if positions else 'SELECT 0,NULL,NULL WHERE 0'
    expected_args=[v for i,(typed,ordinal) in enumerate(positions,1) for v in (i,typed,ordinal)]
    bounded=(f"CASE WHEN typeof({key})='blob' AND length({key})<={max_key_bytes} THEN {key} END AS typed_key,"
        "CASE WHEN typeof(ordinal)='integer' THEN ordinal END AS ordinal,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END AS valid_from,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END AS valid_to,"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END AS row_checksum")
    # Limit by the real indexed columns before ranking; guard every materialized
    # variable field as well as the first scalar-only preflight.
    sql=('WITH physical AS MATERIALIZED (SELECT '+bounded+suffix+'),'
        'ranked AS (SELECT row_number() OVER (ORDER BY ordinal,typed_key) AS slot,* FROM physical),'
        'wanted(slot,typed,wanted_ordinal) AS ('+expected_sql+') '
        'SELECT CASE WHEN r.typed_key=w.typed AND r.ordinal=w.wanted_ordinal THEN 1 ELSE 0 END,'+scalar_fields('r.')+
        ' FROM ranked AS r LEFT JOIN wanted AS w ON r.slot=w.slot ORDER BY r.slot')
    captured=store.db.execute(sql,(*args,*expected_args)).fetchall();rows=[]
    for i,(matches,*row) in enumerate(captured):
        if matches!=1 or i>=len(positions):raise StoreIntegrityError('native physical window differs from accepted positions')
        rows.append((positions[i][0],*row))
    store._query_rows+=len(rows)
    return rows
