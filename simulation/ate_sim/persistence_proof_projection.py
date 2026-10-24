"""Inactive content-to-placement checks for existing physical history owners.

Storage references only: no target lookup, World object admission, production
root construction, alternate registry or publisher. Full topology stays gated.
"""
from dataclasses import dataclass
import json

from .incremental_store import TypedCodec,CodecError,Membership,StoreError,StoreIntegrityError
from .persistence_adapters import WorldCodec
from .persistence_lazy_store import VersionChange
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_proof_occurrence import OwnerScope,REQUIRED_INTERVALS,_require_indexes,MAX_FIELD_BYTES,OccurrenceProofBudgetError
from .persistence_proof_occurrence_seek import (
    certificate_commitment as occurrence_commitment,read_occurrence_seek_page)
from .persistence_proof_version import (
    RawVersion,VersionProofBudgetError,certificate_commitment as version_commitment,read_version_bytes,_guard_operational_metadata)


class ProjectionProofBudgetError(StoreError):
    """The declared changed-owner path needs a separately budgeted check."""


@dataclass(frozen=True)
class RawOwnerProjection:
    source: RawVersion | None
    reference_count: int


class _ProjectionCodec(WorldCodec):
    """Borrow existing encoding/tags, register no mutable World classes."""
    def __init__(self,*,metadata=False):
        from .core import Ref,Layer
        TypedCodec.__init__(self)
        self.identity_links_recorded=False
        self._metadata=metadata
        self.register_enum('core.Layer/v1',Layer)
        self.register_record('core.Ref/v1',Ref)

    def decode(self,payload):
        try:node=json.loads(payload.decode('utf-8'))
        except (ValueError,UnicodeError,RecursionError) as exc:
            raise StoreIntegrityError('invalid projection typed bytes') from exc
        pending=[(node,0)];count=0
        while pending:
            item,depth=pending.pop();count+=1
            if count>32768 or depth>64:raise ProjectionProofBudgetError('projection parsed inventory exceeds node/depth budget')
            if type(item) is list:pending.extend((child,depth+1) for child in item)
            elif type(item) is dict:raise StoreIntegrityError('invalid projection typed JSON object')
        try:return self._decode_value(node)
        except (CodecError,ValueError,TypeError,RecursionError) as exc:
            raise StoreIntegrityError('invalid closed projection value') from exc

    def _decode_value(self,node):
        containers=('list','dict','set') if self._metadata else ()
        if (type(node) is not list or not node or type(node[0]) is not str or node[0] not in containers+(
                'none','bool','int','float64','str','bytes','tuple','frozenset','enum','record',
                'typed-history/v1','typed-record/v1','typed-event-id-authority/v1','typed-nan-key/v1')):
            raise CodecError('mutable or unsupported projection tag')
        # TypedCodec resolves records only through this instance's Ref registry.
        return super()._decode_value(node)


def _authority(certificate,expected,commitment):
    actual=commitment(certificate)
    if type(expected) is not bytes or len(expected)!=32 or expected!=actual:
        raise StoreIntegrityError('owner projection authority commitment disagreement')


def _require_closed_codec(store,*,allow_typed=False):
    world=type(store.codec) is WorldCodec
    plain=allow_typed and type(store.codec) is TypedCodec
    if not (world or plain) or any(
            getattr(getattr(store.codec,name,None),'__func__',None) is not method for name,method in (
                ('encode',TypedCodec.encode),('decode',TypedCodec.decode),
                ('_encode_value',WorldCodec._encode_value if world else TypedCodec._encode_value),
                ('_decode_value',WorldCodec._decode_value if world else TypedCodec._decode_value))):
        raise StoreError('proof source requires a closed codec without caller hooks')
    if any(getattr(store.codec,name,None) is not getattr(TypedCodec,name) for name in ('_enter','_node_sort_key')):
        raise StoreError('proof source requires closed codec helper functions')
    if plain and (store.codec._record_by_name or store.codec._enum_by_name):
        raise StoreError('generic proof source cannot use caller codec registries')
    if world:
        from .core import Ref,Layer
        if (store.codec._record_by_name.get('core.Ref/v1') is not Ref
                or store.codec._enum_by_name.get('core.Layer/v1') is not Layer):
            raise StoreError('proof source requires built-in immutable metadata types')


def _closed_snapshot_preflight(store,max_metadata_bytes):
    _guard_operational_metadata(store,max_metadata_bytes)
    blobs=store.db.execute('SELECT simulation_position,next_ids,namespace_inventory,namespace_counts '
        'FROM save_head WHERE singleton=1').fetchone()
    closed=_ProjectionCodec(metadata=True)
    for blob in blobs:closed.decode(blob)


def _read_owner_projection(store,pin,version_certificate,expected_version,occurrence_certificate,expected_occurrence,
                          *,max_bytes=1048576,max_references=4096,max_metadata_bytes=1048576):
    _authority(version_certificate,expected_version,version_commitment)
    _authority(occurrence_certificate,expected_occurrence,occurrence_commitment)
    if (type(max_bytes) is not int or not 1<=max_bytes<=64*1024*1024
            or type(max_references) is not int or not 1<=max_references<=4096
            or type(max_metadata_bytes) is not int or not 1<=max_metadata_bytes<=64*1024*1024):
        raise StoreIntegrityError('invalid projection budget')
    scope=occurrence_certificate.scope
    if type(scope) is not OwnerScope or scope.namespace not in AUXILIARY_OWNER_FAMILIES:
        raise StoreError('projection requires a registered physical owner scope')
    _require_closed_codec(store)
    if len(scope.typed_key)>MAX_FIELD_BYTES:raise ProjectionProofBudgetError('projection owner key exceeds field budget')
    if occurrence_certificate.root.count>max_references:raise ProjectionProofBudgetError('projection references exceed budget')
    if store.db.in_transaction and not store._active_read_transaction and not getattr(store,'_checked_snapshot_depth',0):
        raise StoreError('projection cannot borrow arbitrary transaction')
    adapter=AUXILIARY_OWNER_FAMILIES[scope.namespace]
    codec=_ProjectionCodec()
    if codec.version!=store.codec.version:raise StoreError('unsupported projection codec version')
    def preflight():
        _closed_snapshot_preflight(store,max_metadata_bytes)
    with store.read_snapshot(pin,_preflight=preflight):
        required=REQUIRED_INTERVALS+('lazy_record_interval',)
        if any(name not in store._interval_indexes for name in required):
            raise StoreError('projection cannot use legacy interval fallback')
        _require_indexes(store.db,include_order=False,intervals=required)
        # Each component checks store, codec, generation, exact live pin and
        # fetched physical bytes. Nested snapshots share the outer snapshot.
        source=read_version_bytes(store,pin,version_certificate,expected_version,scope.namespace,scope.typed_key,
            expected_record_schema=adapter.record_schema,max_bytes=max_bytes,max_metadata_bytes=max_metadata_bytes)
        key=codec.decode(scope.typed_key);adapter.validate_key(key)
        allocator=occurrence_certificate.next_incarnation_id
        if key[0]>=allocator:raise StoreIntegrityError('projection owner exceeds allocator')
        expected=[]
        if source is not None:
            value=codec.decode(source.payload);memberships=codec.decode(source.memberships)
            if (type(memberships) is not tuple or any(type(row) is not tuple or len(row)!=3 for row in memberships)):
                raise StoreIntegrityError('invalid projection memberships')
            change=VersionChange(scope.namespace,key,value,record_schema=source.record_schema,
                memberships=tuple(Membership(*row) for row in memberships))
            adapter.validate_source(change,'lazy',codec)
            placements=adapter.reference_placements(value)
            if len(placements)>max_references:raise ProjectionProofBudgetError('projection references exceed budget')
            for path,inc in placements:
                adapter.validate_path(path)
                if type(inc) is not int or not 0<inc<allocator:raise StoreIntegrityError('projected reference exceeds allocator')
                encoded=codec.encode(path)
                if len(encoded)>MAX_FIELD_BYTES:raise ProjectionProofBudgetError('projection path exceeds field budget')
                expected.append((encoded,inc))
            expected.sort()
            if any(a[0]==b[0] for a,b in zip(expected,expected[1:])):
                raise StoreIntegrityError('duplicate projected reference path')
        if len(expected)!=occurrence_certificate.root.count:
            raise StoreIntegrityError('payload reference count disagrees with committed owner root')
        offset=0;after=None
        while True:
            page=read_occurrence_seek_page(store,pin,occurrence_certificate,expected_occurrence,
                after=after,limit=128,max_metadata_bytes=max_metadata_bytes)
            for row in page.rows:
                if offset>=len(expected) or (row.path,row.incarnation_id)!=expected[offset]:
                    raise StoreIntegrityError('payload references disagree with committed owner placements')
                offset+=1
            if page.next_after is None:break
            after=page.next_after
        if offset!=len(expected):raise StoreIntegrityError('owner reference projection incomplete')
        return RawOwnerProjection(source,offset)


def read_owner_projection(store,pin,version_certificate,expected_version,occurrence_certificate,expected_occurrence,
                          *,max_bytes=1048576,max_references=4096,max_metadata_bytes=1048576):
    """Check one raw physical source and its full committed reference relation."""
    try:
        return _read_owner_projection(store,pin,version_certificate,expected_version,occurrence_certificate,expected_occurrence,
            max_bytes=max_bytes,max_references=max_references,max_metadata_bytes=max_metadata_bytes)
    except (VersionProofBudgetError,OccurrenceProofBudgetError) as exc:
        raise ProjectionProofBudgetError(str(exc)) from exc
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError) as exc:
        raise StoreIntegrityError('invalid owner projection codec/schema') from exc
