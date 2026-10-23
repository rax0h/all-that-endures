"""Inactive root-selected raw query pages; external accepted authority required."""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,CodecError
from .persistence_lazy_store import _query_checksum
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_query import QueryScope,QueryPage,query_domain,member_commitment,_cursor,MAX_QUERY_KEY_BYTES
from .persistence_proof_order import query_order_key
from .persistence_proof_occurrence import _require_indexes
from .persistence_proof_content import _namespace
from .persistence_proof_version import VersionProofBudgetError
from .persistence_proof_projection import _require_closed_codec,_closed_snapshot_preflight,ProjectionProofBudgetError


class QuerySeekBudgetError(StoreError):
    """A larger certificate-checked source path is required."""


@dataclass(frozen=True)
class SeekQueryCertificate:
    store_identity: str
    generation: int
    codec_version: int
    scope: QueryScope
    root: Root


def seek_domain(store_identity,codec_version,scope):
    return _digest(b'ate-query-seek-domain/1',query_domain(store_identity,codec_version,scope))


def certificate_commitment(certificate):
    if (type(certificate) is not SeekQueryCertificate or type(certificate.generation) is not int
            or not 0<=certificate.generation<2**63):raise StoreIntegrityError('invalid seek query certificate')
    domain=seek_domain(certificate.store_identity,certificate.codec_version,certificate.scope)
    OrderedSeekMap(None,domain)._reference(certificate.root)
    return _digest(b'ate-query-seek-certificate/1',domain,certificate.generation.to_bytes(8,'big'),
        certificate.root.digest,certificate.root.count.to_bytes(8,'big'))


def _read(store,pin,certificate,expected,*,after,limit,max_metadata_bytes):
    actual=certificate_commitment(certificate)
    if type(expected) is not bytes or len(expected)!=32 or actual!=expected:raise StoreIntegrityError('seek query authority disagreement')
    if (certificate.store_identity!=store.store_identity or certificate.store_identity!=pin.store_identity
            or certificate.generation!=pin.captured_head or certificate.codec_version!=store.codec.version):
        raise StoreConflictError('seek query store/codec/pin disagreement')
    if (type(limit) is not int or not 1<=limit<=128 or type(max_metadata_bytes) is not int
            or not 1<=max_metadata_bytes<=64*1024*1024):raise StoreIntegrityError('invalid seek query budget')
    _require_closed_codec(store,allow_typed=True);scope=certificate.scope;after=_cursor(after)
    if max(len(_namespace(scope.namespace)),len(_namespace(scope.index_name)),len(scope.index_value),
            len(after[1]) if after else 0)>MAX_QUERY_KEY_BYTES:raise QuerySeekBudgetError('query fields exceed metadata budget')
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('seek query cannot borrow arbitrary transaction')
    with store.read_snapshot(pin,_preflight=lambda:_closed_snapshot_preflight(store,max_metadata_bytes)) as generation:
        head=int(store._checked_head_row()[0])
        if generation not in (head,head-1):raise StoreConflictError('query pin outside retained generations')
        if 'lazy_query_interval' not in store._interval_indexes:raise StoreError('query cannot use legacy interval fallback')
        _require_indexes(store.db,include_order=False,intervals=('lazy_query_interval',))
        m=OrderedSeekMap(store.db,seek_domain(certificate.store_identity,certificate.codec_version,scope))
        positions=m.page(certificate.root,after=None if after is None else query_order_key(*after),limit=limit+1)
        parsed=[]
        for position,value in positions:
            if len(position)<8:raise StoreIntegrityError('invalid seek query position')
            ordinal=int.from_bytes(position[:8],'big');key=position[8:];query_order_key(ordinal,key)
            if len(key)>MAX_QUERY_KEY_BYTES:raise QuerySeekBudgetError('selected query key exceeds budget')
            parsed.append((key,ordinal,value))
        domain=query_domain(certificate.store_identity,certificate.codec_version,scope);result=[]
        columns=("CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
            "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
            "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
        for key,ordinal,value in parsed[:limit]:
            rows=store._interval_rows('lazy_query_versions',columns,
                ('namespace','index_name','index_value','record_key','ordinal'),
                (scope.namespace,scope.index_name,scope.index_value,key,ordinal),generation,'lazy_query_interval',limit=2)
            store._metadata_rows+=len(rows)
            if len(rows)!=1:raise StoreIntegrityError('selected query missing or overlapping')
            start,end,end_type,checksum=rows[0]
            if (type(start) is not int or not 0<=start<=generation or end_type not in ('null','integer')
                    or end_type=='integer' and (type(end) is not int or end<=generation or end<=start)
                    or checksum!=_query_checksum(scope.namespace,scope.index_name,scope.index_value,key,ordinal,start,end)
                    or member_commitment(domain,key,ordinal)!=value):
                raise StoreIntegrityError('selected query interval/checksum/root disagreement')
            result.append((key,ordinal))
        return QueryPage(tuple(result),(result[-1][1],result[-1][0]) if result and len(parsed)>limit else None)


def read_query_seek_page(store,pin,certificate,expected,*,after=None,limit=128,max_metadata_bytes=1048576):
    try:return _read(store,pin,certificate,expected,after=after,limit=limit,max_metadata_bytes=max_metadata_bytes)
    except (VersionProofBudgetError,ProjectionProofBudgetError) as exc:raise QuerySeekBudgetError(str(exc)) from exc
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError) as exc:raise StoreIntegrityError('invalid query source metadata') from exc
