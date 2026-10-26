"""Inactive bounded selected history/fixed-body extent validator; raw values only.

Full selected-target reference/audit work, not ordinary open/save admission.
Recursive graph semantics and World admission remain gated.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,CodecError,Membership
from .persistence_lazy_store import VersionChange
from .persistence_lazy_nested_history import PAGE_NAMESPACE,ENTRY_NAMESPACE
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_history_types import NAMESPACE as TYPES,TAG,member_counts,incoming_owner_policy
from .persistence_lazy_graph_buckets import BUCKET_SPECS
from . import persistence_proof_target_incoming as incoming


@dataclass(frozen=True)
class RawTargetMembers:
    incoming: incoming.RawTargetIncoming
    members: tuple
    member_counts: tuple
    child_locators: tuple
    certification_targets: tuple = ()
    components: tuple = ()


@dataclass(frozen=True)
class RawBackingExtent:
    target: object
    members: tuple
    member_counts: tuple
    child_locators: tuple
    certification_targets: tuple = ()
    components: tuple = ()


def _finish(value,s,scope_pair,max_children,max_values,max_certification_targets):
    from .persistence_proof_extent_inventory import ExtentWork
    body=_physical(value.target,s,scope_pair,ExtentWork(max_children,max_values),max_certification_targets)
    _check_policies(value,s,value.target.kind,body.member_counts)
    return RawTargetMembers(value,body.members,body.member_counts,body.child_locators,body.certification_targets,body.components)


def _physical(backing,s,scope_pair,budget,max_certification_targets):
    if budget.extents is not None and backing.incarnation in budget.extents:
        result=budget.extents[backing.incarnation];old=result.target
        if (old.store_identity,old.generation,old.kind,old.namespace,old.typed_key,old.payload)!=(backing.store_identity,backing.generation,backing.kind,backing.namespace,backing.typed_key,backing.payload):raise StoreIntegrityError('cached extent authority disagreement')
        return result
    result=_physical_uncached(backing,s,scope_pair,budget,max_certification_targets)
    if budget.extents is not None:budget.extents[backing.incarnation]=result
    return result


def _physical_uncached(backing,s,scope_pair,budget,max_certification_targets):
    from .persistence_proof_extent_inventory import physical_locators
    kind=backing.kind;inc=backing.incarnation
    if kind=='sequence':
        from .persistence_proof_sequence_extents import read_sequence_extent
        return read_sequence_extent(backing,s,scope_pair,budget)
    if kind=='event-ids':
        from .persistence_proof_event_extents import read_event_extent
        return read_event_extent(backing,s,scope_pair,budget,max_certification_targets)
    base=kind.removeprefix('frozen-');fixed=kind in ('record','nan-key')
    if base not in ('list','map','set') and not fixed:raise StoreError('extent kind requires a separate checked path')
    if kind=='record':
        from .persistence_record_headers import checked_record_header
        from .persistence_schema import RECORD_FIELDS
        cls,fields,_state=checked_record_header(backing.descriptor);count=len(fields)
    elif kind=='nan-key':count=0
    else:count=backing.descriptor[1]
    budget.take_values(count)
    locators=physical_locators(s,scope_pair,inc,budget)
    expected=1 if fixed else (count+127)//128 if base=='list' else count
    expected_ns=backing.namespace if fixed else PAGE_NAMESPACE if base=='list' else ENTRY_NAMESPACE
    if len(locators)!=expected or any(ns!=expected_ns for ns,key in locators):raise StoreIntegrityError('complete physical children disagree with target extent/family')
    if fixed:
        if tuple(locators)!=((backing.namespace,(inc,0)),):raise StoreIntegrityError('fixed target has a competing child locator')
        items=tuple(zip(RECORD_FIELDS[cls],fields)) if kind=='record' else ()
        actual=member_counts(fields) if kind=='record' else (0,0,0)
        return RawBackingExtent(backing,items,actual,tuple(locators))
    items=[];ordered=[]
    for ns,key in locators:
        data,members,raw,typed=s.value(ns,key)
        change=VersionChange(ns,key,data,record_schema=raw.record_schema,memberships=tuple(Membership(*r) for r in members))
        AUXILIARY_OWNER_FAMILIES[ns].validate_source(change,'lazy',s.codec)
        if base=='list':
            number=key[1]
            if not 0<=number<expected or len(data)!=min(128,count-128*number):raise StoreIntegrityError('list page number/shape disagrees with exact extent')
            ordered.append((number,data))
        else:
            ordinal,member,payload=data
            if ordinal>=backing.descriptor[2] or base=='set' and payload is not None:raise StoreIntegrityError('scalar child ordinal/value disagrees with descriptor')
            ordered.append((ordinal,(member,payload)))
    ordered.sort(key=lambda x:x[0])
    if len({i for i,_ in ordered})!=len(ordered):raise StoreIntegrityError('duplicate history child ordinal')
    if base=='list':
        if tuple(i for i,_ in ordered)!=tuple(range(expected)):raise StoreIntegrityError('list extent has missing interior pages')
        for _,page in ordered:items.extend(page)
    else:items=[entry[0] if base=='set' else entry for _,entry in ordered]
    if len(items)!=count:raise StoreIntegrityError('history members disagree with extent count')
    actual=member_counts([entry[0] for entry in items] if base=='map' else items)
    _check_witness(s,inc,base,actual)
    dependencies=()
    if kind.startswith('frozen-'):
        from .persistence_proof_frozen_extents import check_frozen_members
        dependencies=check_frozen_members(s,scope_pair,backing,items,max_certification_targets)
    return RawBackingExtent(backing,tuple(items),actual,tuple(locators),dependencies)


def _check_witness(s,inc,base,actual):
    witness=s.metadata(TYPES,inc)
    if (type(witness) is not tuple or len(witness)!=3 or witness[:2]!=(TAG,base)
            or type(witness[2]) is not tuple or len(witness[2])!=3 or any(type(n) is not int or n<0 for n in witness[2]) or witness[2]!=actual):
        raise StoreIntegrityError('member witness disagrees with actual complete values')


def _check_policies(value,s,kind,actual):
    for row in value.group.occurrences:
        path=s.codec.decode(row.path);policy=incoming_owner_policy(row.namespace,path)
        if policy is None:continue
        if kind in ('record','nan-key','event-ids'):raise StoreIntegrityError('incoming history owner requires a history target')
        if not path and row.namespace in BUCKET_SPECS and kind!=BUCKET_SPECS[row.namespace][0]:raise StoreIntegrityError('incoming bucket has wrong history kind')
        allowed=0 if policy=='int' else 1
        if actual[allowed]!=sum(actual):raise StoreIntegrityError('actual history values violate incoming member policy')


def read_target_members(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,
                        max_children=4096,max_values=65536,max_certification_targets=128,max_members=4096,max_bytes=8388608,max_source_bytes=1048576,max_metadata_bytes=1048576):
    for n,limit in ((max_children,4096),(max_values,65536),(max_certification_targets,4096)):
        if type(n) is not int or not 1<=n<=limit:raise StoreIntegrityError('invalid extent budget')
    try:return incoming._read(store,pin,reference,content_authority,scope_authority,inventory_authority,record_authority=record_authority,
        max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes,
        _after=lambda value,s:_finish(value,s,scope_authority,max_children,max_values,max_certification_targets))
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError) as exc:raise StoreIntegrityError('invalid child extent source') from exc
