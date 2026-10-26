"""Inactive raw target descriptor/kind/liveness join, using existing roots.

This point result does not admit native objects, certify target members or
outgoing references, prove complete alias links, or activate World loading.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,StoreConflictError,CodecError
from .persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE as HISTORY
from .persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE,_link,_directory_link
from .persistence_record_headers import RecordReference,NAMESPACE as RECORDS,checked_record_header
from .persistence_nonreflexive_keys import NonreflexiveKeyReference,NAMESPACE as NAN,checked_nonreflexive_key_header
from .persistence_event_id_reference import EventIdReference,check_compact_authority
from .persistence_frozen_snapshots import checked_frozen_descriptor
from .persistence_lazy_identity_retired import RetiredIdentityRanges,checked_header
from .persistence_proof_identity_group import _RetiredSource
from .persistence_proof_projection import _ProjectionCodec,_require_closed_codec,_closed_snapshot_preflight
from .persistence_proof_occurrence import OwnerScope,GroupScope
from .persistence_proof_occurrence_seek import read_occurrence_seek_page
from . import persistence_lazy_identity_catalog as catalog
from . import persistence_proof_publication as content
from . import persistence_proof_scope as scope
from . import persistence_proof_inventory as inventory
from . import persistence_proof_collection_directory as source

class TargetProofBudgetError(StoreError):pass

@dataclass(frozen=True)
class RawReferenceTarget:
    store_identity:str
    generation:int
    incarnation:int
    kind:str
    namespace:str
    typed_key:bytes
    payload:bytes
    descriptor:tuple


def _reference(value):
    if type(value) is HistoryReference:
        kind=value.kind
        if type(kind) is not str or kind not in ('list','map','set','sequence','frozen-list','frozen-map'):raise StoreIntegrityError('unsupported target history kind')
    elif type(value) is RecordReference:kind='record'
    elif type(value) is NonreflexiveKeyReference:kind='nan-key'
    elif type(value) is EventIdReference:kind='event-ids'
    else:raise StoreIntegrityError('unsupported closed target reference')
    inc=value.incarnation
    if type(inc) is not int or not 1<=inc<2**63:raise StoreIntegrityError('invalid target incarnation')
    return kind,inc

def _pairs(store,pin,pairs):
    if any(type(p) is not tuple or len(p)!=2 for p in pairs):raise StoreIntegrityError('target requires exact authority pairs')
    c,s,i=pairs
    content._authority(store,pin,*c);scope._authority(store,pin,*s);inventory._authority(store,pin,*i)
    if s[0].next_incarnation_id!=i[0].head.next_incarnation_id:raise StoreConflictError('target allocator authorities disagree')

def _preflight(store,budget):
    # Validate schemas before inherited metadata reads or any SQL callback can
    # hide behind a source view. The inventory path guards the node source too.
    source._source_schemas(store.db);inventory._node_schema(store.db);source._source_indexes(store.db)
    _closed_snapshot_preflight(store,budget);inventory._preflight(store)

class _Sources:
    def __init__(self,store,pin,pair,aggregate,per_source,metadata,*,read_limit=128,memoize=False):
        self.store,self.pin,self.pair=store,pin,pair;self.codec=_ProjectionCodec(metadata=True)
        self.remaining,self.per_source,self.metadata_limit=aggregate,per_source,metadata;self.reads=0;self.read_limit=read_limit;self._memo={} if memoize else None
    def charge(self,n):
        self.remaining-=n
        if self.remaining<0:raise TargetProofBudgetError('target sources exceed aggregate budget')
    def value(self,ns,key,*,absent=False):
        typed=self.codec.encode(key);marker=ns,typed
        if self._memo is not None and marker in self._memo:
            cached=self._memo[marker]
            if cached is None and not absent:raise StoreIntegrityError('missing required target source')
            return cached
        # Memo hits perform no source traversal; closure child/edge budgets
        # independently bound their logical visits. Legacy readers do not memoize.
        self.reads+=1
        if self.reads>self.read_limit:raise TargetProofBudgetError('target metadata traversal exceeds source budget')
        self.charge(len(ns.encode())+len(typed))
        if self.remaining<1:raise TargetProofBudgetError('target sources exceed aggregate budget')
        raw=content.read_version_content_bytes(self.store,self.pin,*self.pair,ns,typed,expected_record_schema=1,max_bytes=min(self.per_source,self.remaining),max_metadata_bytes=self.metadata_limit)
        if raw is None:
            if self._memo is not None:self._memo[marker]=None
            if absent:return None
            raise StoreIntegrityError('missing required target source')
        self.charge(len(raw.payload)+len(raw.memberships));value=self.codec.decode(raw.payload);members=self.codec.decode(raw.memberships)
        if type(members) is not tuple or any(type(row) is not tuple or len(row)!=3 or type(row[0]) is not str or type(row[2]) is not int or row[2]<0 for row in members):raise StoreIntegrityError('invalid target source memberships')
        result=value,members,raw,typed
        if self._memo is not None:self._memo[marker]=result
        return result
    def metadata(self,ns,key):
        value,members,*_=self.value(ns,key)
        if members:raise StoreIntegrityError('unexpected target metadata memberships')
        return value


def _live_group(sources,scope_pair,inc,allocator):
    s=sources;descriptor=s.metadata(catalog.CATALOG_NAMESPACE,0);retired=s.metadata(catalog.RETIRED_NAMESPACE,0);checked_header(retired)
    if (type(descriptor) is not tuple or len(descriptor)!=5 or descriptor[0]!=catalog.CATALOG_TAG or descriptor[1]!=catalog.FEATURES
        or type(descriptor[2]) is not int or descriptor[2]!=allocator or type(descriptor[3]) is not int or descriptor[3]<0
        or s.codec.encode(checked_header(descriptor[4]))!=s.codec.encode(retired)
        or descriptor[3]+(retired[2][6] if retired[2] else 0)!=allocator-1
        or retired[2] is not None and retired[2][5]>=allocator):raise StoreIntegrityError('target catalog allocator/retirement disagreement')
    if RetiredIdentityRanges(_RetiredSource(s),s.pin,header=retired).contains(inc):raise StoreIntegrityError('target incarnation is retired')
    header,members,*_=s.value(catalog.GROUP_NAMESPACE,inc)
    group,expected=scope.read_scope_certificate(s.store,s.pin,*scope_pair,GroupScope(inc),max_metadata_bytes=s.metadata_limit)
    if (type(header) is not tuple or len(header)!=7 or header[:2]!=('identity-group/v1','mutable')
        or type(header[2]) is not int or header[2]<1 or header[2]!=group.root.count
        or type(header[4]) is not int or header[4]!=header[2]-1 or members
        or any(type(header[n]) is not str or len(header[n])!=64 or any(c not in '0123456789abcdef' for c in header[n]) for n in (3,5))
        or type(header[6]) is not tuple):raise StoreIntegrityError('target lacks a live complete-count group header')
    witness=read_occurrence_seek_page(s.store,s.pin,group,expected,limit=1,max_metadata_bytes=s.metadata_limit)
    if not witness.rows or witness.rows[0].incarnation_id!=inc:raise StoreIntegrityError('target lacks a checked physical group placement')
    for row in witness.rows:s.charge(len(row.namespace.encode())+len(row.typed_key)+len(row.path)+8)


def _validate_descriptor(kind,inc,value):
    if kind in ('frozen-list','frozen-map'):checked_frozen_descriptor(value,kind=kind)
    elif kind in ('list','map','set'):
        if (type(value) is not tuple or len(value)!=3 or value[0]!=kind
            or type(value[1]) is not int or not 0<=value[1]<2**63 or type(value[2]) is not int or not value[1]<=value[2]<2**63
            or kind=='list' and value[1]!=value[2]):raise StoreIntegrityError('invalid target history descriptor')
    elif kind=='sequence':
        if (type(value) is not tuple or not (len(value)==8 and value[0]=='ordered-sequence/v1' or len(value)==9 and value[0]=='ordered-sequence/v2' and value[8]=='native')):raise StoreIntegrityError('invalid target sequence kind')
        native=len(value)==9
        if (type(value[1]) is not int or value[1]!=inc or not _link(value[2]) or type(value[3]) is not int or value[3]<0 or value[2][1]!=value[3]
            or type(value[4]) is not int or value[4]<1 or type(value[5]) is not int or value[5]<1 or value[2][0]>=value[5]
            or type(value[6]) is not int or value[6]<0 or value[7] is not None and not _directory_link(value[7])
            or value[3]==0 and value[7] is not None or not native and value[3]>0 and value[7] is None):raise StoreIntegrityError('invalid target sequence descriptor')
    elif kind=='record':checked_record_header(value)
    elif kind=='nan-key':checked_nonreflexive_key_header(value)
    else:check_compact_authority(value)


def _event_owner(s,scope_pair):
    from .persistence_event_ids import EXCEPTION_TAG
    owner,expected=scope.read_scope_certificate(s.store,s.pin,*scope_pair,OwnerScope('world.event_ids',s.codec.encode(0)),max_metadata_bytes=s.metadata_limit)
    if not owner.root.count:return None
    if owner.root.count not in (1,3):raise StoreIntegrityError('Event-ID owner-zero has wrong fixed slot count')
    page=read_occurrence_seek_page(s.store,s.pin,owner,expected,limit=4,max_metadata_bytes=s.metadata_limit)
    if len(page.rows)!=owner.root.count or page.next_after is not None:raise StoreIntegrityError('incomplete Event-ID owner slots')
    slots={row.path:row.incarnation_id for row in page.rows}
    for row in page.rows:s.charge(len(row.namespace.encode())+len(row.typed_key)+len(row.path)+8)
    root=slots.get(s.codec.encode(()))
    if root is None:raise StoreIntegrityError('Event-ID owner has no root slot')
    value,members,raw,typed=s.value('world.event_ids',0);check_compact_authority(value)
    if members:raise StoreIntegrityError('Event-ID descriptor has unexpected memberships')
    wanted={s.codec.encode(()):root}
    if value[0]==EXCEPTION_TAG:
        wanted.update({s.codec.encode((('field','_exact'),('field',name))):ref.incarnation for name,ref in zip(('removed','added'),value[2:4])})
    if slots!=wanted or len(slots)!=len(page.rows) or root in [v for k,v in wanted.items() if k!=s.codec.encode(())]:raise StoreIntegrityError('Event-ID descriptor and fixed owner slots disagree')
    return root,value,raw,typed


def _resolve_target(s,scope_pair,reference,allocator):
    store,pin=s.store,s.pin;max_metadata_bytes=s.metadata_limit
    kind,inc=_reference(reference)
    if inc>=allocator:raise StoreIntegrityError('target exceeds identity allocator')
    _live_group(s,scope_pair,inc,allocator)
    candidates=[]
    for ns,key,expected_kind in ((HISTORY,inc,'history'),(SEQUENCE,inc,'sequence'),(RECORDS,(inc,0),'record'),(NAN,(inc,0),'nan-key')):
        found=s.value(ns,key,absent=True)
        if found is not None:
            value,members,raw,typed=found
            if members:raise StoreIntegrityError('target descriptor has unexpected memberships')
            actual=value[0] if expected_kind=='history' and type(value) is tuple and value else expected_kind
            candidates.append((actual,ns,typed,raw.payload,value))
    event=_event_owner(s,scope_pair)
    if event is not None:
        event_inc,value,raw,typed=event
        if event_inc==inc:candidates.append(('event-ids','world.event_ids',typed,raw.payload,value))
    if len(candidates)!=1 or candidates[0][0]!=kind:raise StoreIntegrityError('missing, competing or wrong-kind target descriptor')
    actual,ns,typed,payload,value=candidates[0];_validate_descriptor(kind,inc,value)
    return RawReferenceTarget(store.store_identity,pin.captured_head,inc,kind,ns,typed,payload,value)

def _read(store,pin,reference,content_pair,scope_pair,inventory_pair,*,max_bytes,max_source_bytes,max_metadata_bytes):
    _require_closed_codec(store);kind,inc=_reference(reference)
    for n,maximum in ((max_bytes,64*1024*1024),(max_source_bytes,64*1024*1024),(max_metadata_bytes,1048576)):
        if type(n) is not int or not 1<=n<=maximum:raise StoreIntegrityError('invalid target byte budget')
    _pairs(store,pin,(content_pair,scope_pair,inventory_pair));allocator=inventory_pair[0].head.next_incarnation_id
    if inc>=allocator:raise StoreIntegrityError('target exceeds identity allocator')
    if store.db.in_transaction:raise StoreError('target reader requires owned snapshot')
    with store.read_snapshot(pin,_preflight=lambda:_preflight(store,max_metadata_bytes)):
        inventory._snapshot_checks(store,*inventory_pair);s=_Sources(store,pin,content_pair,max_bytes,max_source_bytes,max_metadata_bytes)
        return _resolve_target(s,scope_pair,reference,allocator)


def read_reference_target(store,pin,reference,content_authority,scope_authority,inventory_authority,*,max_bytes=2097152,max_source_bytes=1048576,max_metadata_bytes=1048576):
    try:return _read(store,pin,reference,content_authority,scope_authority,inventory_authority,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError) as exc:raise StoreIntegrityError('invalid closed target metadata') from exc
