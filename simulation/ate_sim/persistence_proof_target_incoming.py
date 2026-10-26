"""Inactive selected target plus all of its incoming typed owner references.

Raw bodies only. No native admission, child extents, namespace field-domain
policies, recursive closure, unindexed-owner discovery or World activation.
"""
from dataclasses import dataclass
from .incremental_store import StoreError, StoreIntegrityError, CodecError, Membership, _framed_sha, _record_checksum
from .persistence_lazy_store import VersionChange
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_lazy_families import FAMILIES
from .persistence_proof_projection import _ProjectionCodec
from .persistence_proof_owner_payload import world_target_paths
from .persistence_event_id_reference import check_compact_authority
from . import persistence_proof_target_group as groups
from . import persistence_proof_target as target
from . import persistence_proof_record as records


@dataclass(frozen=True)
class RawIncomingOwner:
    namespace: str
    typed_key: bytes
    storage_kind: str
    source: object
    paths: tuple


@dataclass(frozen=True)
class RawTargetIncoming:
    target: target.RawReferenceTarget
    group: object
    owners: tuple


def _body(s,namespace,typed,key,header,record_pair):
    s.charge(len(namespace.encode())+len(typed))
    if s.dependencies is not None:s.dependencies.add((0 if header[2]=='lazy' else 1,namespace,typed))
    if s.remaining<1:raise target.TargetProofBudgetError('incoming body exceeds aggregate budget')
    if header[2]=='lazy':
        raw=target.content.read_version_content_bytes(s.store,s.pin,*s.pair,namespace,typed,
            expected_record_schema=header[4],max_bytes=min(s.per_source,s.remaining),max_metadata_bytes=s.metadata_limit)
        if raw is None:raise StoreIntegrityError('incoming lazy owner body is absent')
        s.charge(len(raw.payload)+len(raw.memberships));revision=raw.valid_from
    else:
        if record_pair is None:raise StoreError('ordinary incoming owner requires accepted record authority')
        raw=records.read_record_proof_bytes(s.store,s.pin,*record_pair,namespace,typed,
            expected_record_schema=header[4],max_bytes=min(s.per_source,s.remaining),max_metadata_bytes=s.metadata_limit)
        if raw is None:raise StoreIntegrityError('incoming ordinary body is absent')
        s.charge(len(raw.payload));revision=raw.last_changed_generation
    checksum=(_framed_sha(b'lazy-payload-v1',raw.payload) if header[2]=='lazy' else
              _record_checksum(namespace,typed,raw.record_schema,s.store.codec.version,revision,raw.payload))
    if revision!=header[3] or checksum!=header[5]:
        raise StoreIntegrityError('incoming owner body/header disagreement')
    return raw


def _paths(s,namespace,key,raw,backing,max_members):
    codec=_ProjectionCodec();adapter=AUXILIARY_OWNER_FAMILIES.get(namespace)
    if adapter is not None:
        value=codec.decode(raw.payload);members=codec.decode(raw.memberships)
        change=VersionChange(namespace,key,value,record_schema=raw.record_schema,memberships=tuple(Membership(*m) for m in members))
        adapter.validate_source(change,'lazy',codec);paths=[]
        for path,inc in adapter.reference_placements(value):
            if inc!=backing.incarnation:continue
            kind,actual=target._reference(adapter.resolve_path(value,path))
            if actual!=inc or kind!=backing.kind:raise StoreIntegrityError('incoming auxiliary pointer kind/ID disagreement')
            encoded=codec.encode(path)
            if len(encoded)>4096:raise StoreError('incoming auxiliary path exceeds bounded field')
            s.charge(len(encoded)+8);paths.append(encoded)
            if len(paths)>max_members:raise StoreError('incoming auxiliary references exceed member budget')
        return tuple(sorted(paths))
    if namespace not in FAMILIES:raise StoreIntegrityError('incoming owner family is unregistered')
    if raw.record_schema!=FAMILIES[namespace].record_schema:raise StoreIntegrityError('incoming World owner schema disagreement')
    if namespace=='world.event_ids':
        from .persistence_event_ids import EXCEPTION_TAG
        if key!=0 or type(key) is not int:raise StoreIntegrityError('incoming Event-ID owner is not owner zero')
        value=codec.decode(raw.payload);check_compact_authority(value)
        if backing.kind=='event-ids':
            if raw.payload!=backing.payload:raise StoreIntegrityError('incoming Event-ID owner/target bytes disagree')
            path=()
        elif value[0]==EXCEPTION_TAG:
            matches=[(('field','_exact'),('field',name)) for name,ref in zip(('removed','added'),value[2:4]) if ref.incarnation==backing.incarnation and ref.kind==backing.kind]
            if len(matches)!=1:raise StoreIntegrityError('incoming Event-ID backing slot kind/ID disagreement')
            path=matches[0]
        else:raise StoreIntegrityError('range Event-ID owner has no history slots')
        encoded=codec.encode(path);s.charge(len(encoded)+8);return (encoded,)
    return world_target_paths(raw.payload,backing.kind,backing.incarnation,max_members=max_members,charge=s.charge)


def _read(store,pin,reference,content_pair,scope_pair,inventory_pair,*,record_authority,
          max_members,max_bytes,max_source_bytes,max_metadata_bytes,_after=None):
    options=dict(max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
    groups._check(store,pin,reference,content_pair,scope_pair,inventory_pair,**options)
    if record_authority is not None:
        if type(record_authority) is not tuple or len(record_authority)!=2:raise StoreIntegrityError('invalid incoming record authority pair')
        records._authority(store,pin,*record_authority)
    with store.read_snapshot(pin,_preflight=lambda:target._preflight(store,max_metadata_bytes)):
        if record_authority is not None:
            records._schemas(store.db)
            if records._load_root(store,pin.captured_head)[0]!=record_authority:raise StoreIntegrityError('incoming accepted record source root disagreement')
        value,s=_read_checked(store,pin,reference,content_pair,scope_pair,inventory_pair,record_authority=record_authority,**options)
        return value if _after is None else _after(value,s)


def _read_checked(store,pin,reference,content_pair,scope_pair,inventory_pair,*,record_authority,
                  max_members,max_bytes,max_source_bytes,max_metadata_bytes,_sources=None):
    if not getattr(store,'_checked_snapshot_depth',0):raise StoreError('incoming composition requires checked snapshot')
    options=dict(max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
    result,s=groups._read_checked(store,pin,reference,content_pair,scope_pair,inventory_pair,**options,_sources=_sources)
    s.read_limit+=max_members
    owners={}
    for row in result.group.occurrences:owners.setdefault((row.namespace,row.typed_key),[]).append(row.path)
    checked=[]
    for (namespace,typed),expected in sorted(owners.items()):
        key=s.codec.decode(typed);header=s.metadata(target.catalog.OWNER_NAMESPACE,(namespace,key))
        raw=_body(s,namespace,typed,key,header,record_authority)
        paths=_paths(s,namespace,key,raw,result.target,max_members)
        if paths!=tuple(sorted(expected)):raise StoreIntegrityError('incoming body references disagree with complete target group')
        checked.append(RawIncomingOwner(namespace,typed,header[2],raw,paths))
    value=RawTargetIncoming(result.target,result.group,tuple(checked))
    return value,s

def read_target_incoming(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,
                         max_members=4096,max_bytes=8388608,max_source_bytes=1048576,max_metadata_bytes=1048576):
    try:return _read(store,pin,reference,content_authority,scope_authority,inventory_authority,record_authority=record_authority,
        max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError) as exc:
        raise StoreIntegrityError('invalid incoming owner payload metadata') from exc
