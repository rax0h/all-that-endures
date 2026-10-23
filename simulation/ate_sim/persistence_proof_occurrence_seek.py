"""Root-selected occurrence pages with exact checked physical admission.

The accepted root defines logical membership. Unselected physical surplus or
corruption requires full audit; it never enters a page. No World capability,
production authority constructor, or alternate publisher is enabled here.
"""
from dataclasses import dataclass

from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError
from .persistence_lazy_store import _identity_occurrence_checksum
from .persistence_proof_nodes import Root,_digest
from .persistence_proof_content import _namespace
from .persistence_proof_seek import OrderedSeekMap
from .persistence_proof_occurrence import (
    OwnerScope,GroupScope,RawOccurrence,OccurrencePage,OccurrenceProofBudgetError,
    occurrence_domain,member_commitment,group_order_key,_cursor,_id,_check_allocator,
    _require_indexes,REQUIRED_INTERVALS,MAX_FIELD_BYTES,
)
from .persistence_proof_version import _guard_operational_metadata,VersionProofBudgetError


@dataclass(frozen=True)
class SeekOccurrenceCertificate:
    store_identity: str
    generation: int
    codec_version: int
    scope: OwnerScope | GroupScope
    next_incarnation_id: int
    root: Root


def seek_domain(store_identity,codec_version,scope):
    return _digest(b'ate-occurrence-seek-domain/1',occurrence_domain(store_identity,codec_version,scope))


def certificate_commitment(certificate):
    if (type(certificate) is not SeekOccurrenceCertificate or type(certificate.generation) is not int
            or not 0<=certificate.generation<2**63):raise StoreIntegrityError('invalid seek occurrence certificate')
    domain=seek_domain(certificate.store_identity,certificate.codec_version,certificate.scope)
    allocator=_id(certificate.next_incarnation_id)
    if type(certificate.scope) is GroupScope and certificate.scope.incarnation_id>=certificate.next_incarnation_id:
        raise StoreIntegrityError('seek occurrence exceeds allocator')
    OrderedSeekMap(None,domain)._reference(certificate.root)
    return _digest(b'ate-occurrence-seek-certificate/1',domain,certificate.generation.to_bytes(8,'big'),
                   allocator,certificate.root.digest,certificate.root.count.to_bytes(8,'big'))


def _fields(namespace,key,path):
    encoded=_namespace(namespace)
    if type(key) is not bytes or type(path) is not bytes:raise StoreIntegrityError('invalid seek occurrence field')
    if max(len(encoded),len(key),len(path))>MAX_FIELD_BYTES:
        raise OccurrenceProofBudgetError('seek occurrence field exceeds declared page path')
    return namespace,key,path


def _decode_group_position(position):
    parts=[];part=bytearray();offset=0
    while offset<len(position):
        value=position[offset];offset+=1
        if value:
            part.append(value);continue
        if offset==len(position):raise StoreIntegrityError('truncated seek occurrence escape')
        following=position[offset];offset+=1
        if following==255:part.append(0)
        elif following==0:
            parts.append(bytes(part));part.clear()
            if len(parts)>3:raise StoreIntegrityError('surplus seek occurrence position fields')
        else:raise StoreIntegrityError('invalid seek occurrence escape')
    if part or len(parts)!=3:raise StoreIntegrityError('incomplete seek occurrence position')
    try:namespace=parts[0].decode('utf-8')
    except UnicodeDecodeError as exc:raise StoreIntegrityError('invalid seek occurrence namespace') from exc
    result=_fields(namespace,parts[1],parts[2])
    if group_order_key(*result)!=position:raise StoreIntegrityError('noncanonical seek occurrence position')
    return result


def _point(store,generation,certificate,namespace,key,path):
    columns=("CASE WHEN typeof(incarnation_id)='integer' THEN incarnation_id END,"
        "CASE WHEN typeof(valid_from)='integer' THEN valid_from END,"
        "CASE WHEN typeof(valid_to)='integer' THEN valid_to END,typeof(valid_to),"
        "CASE WHEN typeof(row_checksum)='text' AND length(CAST(row_checksum AS BLOB))=64 THEN row_checksum END")
    rows=store._interval_rows('lazy_identity_occurrence_versions',columns,
        ('owner_namespace','owner_key','occurrence_path'),(namespace,key,path),generation,
        'lazy_identity_occurrence_interval',limit=2)
    store._metadata_rows+=len(rows)
    if len(rows)!=1:raise StoreIntegrityError('selected occurrence missing or overlapping')
    inc,start,end,end_type,checksum=rows[0]
    if (type(inc) is not int or not 0<inc<certificate.next_incarnation_id
            or type(start) is not int or not 0<=start<=generation
            or end_type not in ('null','integer') or end_type=='integer' and (end<=generation or end<=start)
            or checksum!=_identity_occurrence_checksum(namespace,key,path,inc,start,end)):
        raise StoreIntegrityError('selected occurrence physical checksum/interval disagreement')
    if type(certificate.scope) is GroupScope and inc!=certificate.scope.incarnation_id:
        raise StoreIntegrityError('selected occurrence belongs to a different group')
    return RawOccurrence(namespace,key,path,inc)


def read_occurrence_seek_page(store,pin,certificate,expected_commitment,*,after=None,limit=128,max_metadata_bytes=1048576):
    actual=certificate_commitment(certificate)
    if type(expected_commitment) is not bytes or len(expected_commitment)!=32 or expected_commitment!=actual:
        raise StoreIntegrityError('seek occurrence certificate commitment disagreement')
    if (certificate.store_identity!=store.store_identity or certificate.store_identity!=pin.store_identity
            or certificate.generation!=pin.captured_head or certificate.codec_version!=store.codec.version):
        raise StoreConflictError('seek occurrence store/codec/pin disagreement')
    if (type(limit) is not int or not 1<=limit<=128 or type(max_metadata_bytes) is not int
            or not 1<=max_metadata_bytes<=64*1024*1024):raise StoreIntegrityError('invalid seek occurrence page budget')
    scope=certificate.scope;after=_cursor(scope,after)
    if type(scope) is OwnerScope:_fields(scope.namespace,scope.typed_key,b'')
    if after is not None:_fields(*after)
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('seek occurrence cannot borrow arbitrary transaction')
    def preflight():
        try:_guard_operational_metadata(store,max_metadata_bytes)
        except VersionProofBudgetError as exc:raise OccurrenceProofBudgetError(str(exc)) from exc
    with store.read_snapshot(pin,_preflight=preflight) as generation:
        head=int(store._checked_head_row()[0])
        if generation not in (head,head-1):raise StoreConflictError('seek occurrence pin outside retained generations')
        if any(name not in store._interval_indexes for name in REQUIRED_INTERVALS):
            raise StoreError('seek occurrence cannot use legacy interval fallback')
        _require_indexes(store.db,include_order=False);_check_allocator(store,generation,certificate.next_incarnation_id)
        m=OrderedSeekMap(store.db,seek_domain(certificate.store_identity,certificate.codec_version,scope))
        cursor=None if after is None else after[2] if type(scope) is OwnerScope else group_order_key(*after)
        positions=m.page(certificate.root,after=cursor,limit=limit+1)
        domain=occurrence_domain(certificate.store_identity,certificate.codec_version,scope)
        result=[]
        for position,commitment in positions[:limit]:
            fields=_fields(scope.namespace,scope.typed_key,position) if type(scope) is OwnerScope else _decode_group_position(position)
            row=_point(store,generation,certificate,*fields)
            if member_commitment(domain,row)!=commitment:raise StoreIntegrityError('selected occurrence content-root disagreement')
            result.append(row)
        next_after=(result[-1].namespace,result[-1].typed_key,result[-1].path) if result and len(positions)>limit else None
        return OccurrencePage(tuple(result),next_after)
