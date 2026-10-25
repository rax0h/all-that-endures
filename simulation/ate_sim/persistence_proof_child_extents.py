"""Inactive bounded mutable history extent/type validator; raw values only.

Full selected-target reference/audit work, not ordinary open/save admission.
Sequence/frozen/record/Event-ID extents and recursive semantics remain gated.
"""
from dataclasses import dataclass
from .incremental_store import StoreError,StoreIntegrityError,CodecError,Membership
from .persistence_lazy_store import VersionChange
from .persistence_lazy_nested_history import PAGE_NAMESPACE,ENTRY_NAMESPACE
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_history_types import NAMESPACE as TYPES,TAG,member_counts,incoming_owner_policy
from .persistence_lazy_graph_buckets import BUCKET_SPECS
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_proof_scope as scopes
from . import persistence_proof_target_incoming as incoming


@dataclass(frozen=True)
class RawTargetMembers:
    incoming: incoming.RawTargetIncoming
    members: tuple
    member_counts: tuple
    child_locators: tuple


def _finish(value,s,scope_pair,max_children,max_values):
    backing=value.target;kind=backing.kind;inc=backing.incarnation
    if kind not in ('list','map','set'):raise StoreError('extent kind requires a separate checked path')
    count=backing.descriptor[1]
    if count>max_values:raise StoreError('selected history exceeds value budget')
    scope=scopes.ChildScope(inc);root=scopes._resolve(s.store,scope_pair[0],scope)
    expected=(count+127)//128 if kind=='list' else count
    if root.count!=expected:raise StoreIntegrityError('complete physical child count disagrees with target extent')
    if root.count>max_children:raise StoreError('selected history exceeds child budget')
    m=OrderedSeekMap(s.store.db,scopes._seek_domain(s.store,scope));locators=[];after=None
    while True:
        rows=m.page(root,after=after,limit=128)
        for position,commitment in rows:
            if not position or position[0]>=len(scopes._CHILD_NAMES) or commitment!=scopes._child_member(m.domain,position):raise StoreIntegrityError('invalid child locator proof')
            ns=scopes._CHILD_NAMES[position[0]];typed=position[1:];key=s.codec.decode(typed)
            if scopes._child_locator(ns,typed)!=(scope,position):raise StoreIntegrityError('child locator parent disagreement')
            if ns!=(PAGE_NAMESPACE if kind=='list' else ENTRY_NAMESPACE):raise StoreIntegrityError('target has competing child backing family')
            s.charge(len(position)+32);locators.append((ns,key))
        if len(rows)<128:break
        after=rows[-1][0]
    if len(locators)!=expected:raise StoreIntegrityError('incomplete child inventory traversal')
    s.read_limit+=max_children+1;items=[];ordered=[]
    for ns,key in locators:
        data,members,raw,typed=s.value(ns,key)
        change=VersionChange(ns,key,data,record_schema=raw.record_schema,memberships=tuple(Membership(*r) for r in members))
        AUXILIARY_OWNER_FAMILIES[ns].validate_source(change,'lazy',s.codec)
        if kind=='list':
            number=key[1]
            if not 0<=number<expected or len(data)!=min(128,count-128*number):raise StoreIntegrityError('list page number/shape disagrees with exact extent')
            ordered.append((number,data))
        else:
            ordinal,member,payload=data
            if ordinal>=backing.descriptor[2] or kind=='set' and payload is not None:raise StoreIntegrityError('scalar child ordinal/value disagrees with descriptor')
            ordered.append((ordinal,(member,payload)))
    ordered.sort(key=lambda x:x[0])
    if len({i for i,_ in ordered})!=len(ordered):raise StoreIntegrityError('duplicate history child ordinal')
    if kind=='list':
        if tuple(i for i,_ in ordered)!=tuple(range(expected)):raise StoreIntegrityError('list extent has missing interior pages')
        for _,page in ordered:items.extend(page)
    else:items=[entry[0] if kind=='set' else entry for _,entry in ordered]
    if len(items)!=count:raise StoreIntegrityError('history members disagree with extent count')
    actual=member_counts([entry[0] for entry in items] if kind=='map' else items)
    witness=s.metadata(TYPES,inc)
    if (type(witness) is not tuple or len(witness)!=3 or witness[:2]!=(TAG,kind)
            or type(witness[2]) is not tuple or len(witness[2])!=3 or any(type(n) is not int or n<0 for n in witness[2]) or witness[2]!=actual):
        raise StoreIntegrityError('member witness disagrees with actual complete values')
    for row in value.group.occurrences:
        path=s.codec.decode(row.path);policy=incoming_owner_policy(row.namespace,path)
        if policy is None:continue
        if not path and row.namespace in BUCKET_SPECS and kind!=BUCKET_SPECS[row.namespace][0]:raise StoreIntegrityError('incoming bucket has wrong history kind')
        allowed=0 if policy=='int' else 1
        if actual[allowed]!=sum(actual):raise StoreIntegrityError('actual history values violate incoming member policy')
    return RawTargetMembers(value,tuple(items),actual,tuple(locators))


def read_target_members(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,
                        max_children=4096,max_values=65536,max_members=4096,max_bytes=8388608,max_source_bytes=1048576,max_metadata_bytes=1048576):
    for n,limit in ((max_children,4096),(max_values,65536)):
        if type(n) is not int or not 1<=n<=limit:raise StoreIntegrityError('invalid extent budget')
    try:return incoming._read(store,pin,reference,content_authority,scope_authority,inventory_authority,record_authority=record_authority,
        max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes,
        _after=lambda value,s:_finish(value,s,scope_authority,max_children,max_values))
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError) as exc:raise StoreIntegrityError('invalid child extent source') from exc
