"""Inactive bounded directed raw backing closure, never native admission."""
from dataclasses import dataclass
from collections import deque
from .incremental_store import StoreError,StoreIntegrityError,CodecError,Membership
from .persistence_lazy_store import VersionChange
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_lazy_sequence import NODE_NAMESPACE
from .persistence_proof_occurrence import OwnerScope
from .persistence_proof_occurrence_seek import read_occurrence_seek_page
from .persistence_proof_extent_inventory import ExtentWork
from .persistence_frozen_snapshots import immutable_snapshot_value
from . import persistence_proof_target as target
from . import persistence_proof_target_incoming as incoming
from . import persistence_proof_child_extents as extents


@dataclass(frozen=True)
class RawReferenceEdge:
    source_incarnation:int
    namespace:str
    typed_key:bytes
    path:bytes
    target_incarnation:int
    target_kind:str


@dataclass(frozen=True)
class RawReferenceClosure:
    root:object
    targets:tuple
    edges:tuple
    immutable_targets:tuple


def _owner_edges(s,scope_pair,body,remaining):
    result=[]
    if body.target.kind=='event-ids':
        # The backing resolver has already authenticated the complete root and
        # both fixed component slots. The facade's root placement is not an edge.
        from .persistence_event_ids import EXCEPTION_TAG
        d=body.target.descriptor
        if d[0]==EXCEPTION_TAG:
            for name,ref in zip(('removed','added'),d[2:4]):
                path=s.codec.encode((('field','_exact'),('field',name)))
                result.append((body.target.namespace,body.target.typed_key,path,ref))
                s.charge(len(path)+8)
        if len(result)>remaining:raise StoreError('outgoing closure exceeds edge budget')
        return result
    for ns,key in body.child_locators:
        adapter=AUXILIARY_OWNER_FAMILIES.get(ns)
        if adapter is None:continue
        data,members,raw,typed=s.value(ns,key)
        branch=ns==NODE_NAMESPACE and data[0]=='branch'
        if branch:placements=()
        else:
            adapter.validate_source(VersionChange(ns,key,data,record_schema=raw.record_schema,memberships=tuple(Membership(*m) for m in members)),'lazy',s.codec)
            placements=adapter.reference_placements(data)
        expected=[]
        for path,inc in placements:
            if len(result)>=remaining:raise StoreError('outgoing closure exceeds edge budget')
            adapter.validate_path(path);encoded=s.codec.encode(path)
            if len(encoded)>4096:raise StoreError('closure path exceeds field budget')
            ref=adapter.resolve_path(data,path);kind,actual=target._reference(ref)
            if actual!=inc:raise StoreIntegrityError('outgoing path incarnation disagreement')
            s.charge(len(encoded)+8);expected.append((encoded,inc));result.append((ns,typed,encoded,ref))
        expected.sort()
        if len({p for p,i in expected})!=len(expected):raise StoreIntegrityError('duplicate outgoing projection path')
        cert,wanted=target.scope.read_scope_certificate(s.store,s.pin,*scope_pair,OwnerScope(ns,typed),max_metadata_bytes=s.metadata_limit)
        if cert.root.count!=len(expected):raise StoreIntegrityError('outgoing projection count disagrees with complete owner scope')
        after=None;offset=0
        while True:
            page=read_occurrence_seek_page(s.store,s.pin,cert,wanted,after=after,limit=128,max_metadata_bytes=s.metadata_limit)
            for row in page.rows:
                if offset>=len(expected) or (row.path,row.incarnation_id)!=expected[offset]:raise StoreIntegrityError('outgoing projection disagrees with committed owner scope')
                s.charge(len(row.namespace.encode())+len(row.typed_key)+len(row.path)+8);offset+=1
            if page.next_after is None:break
            after=page.next_after
        if offset!=len(expected):raise StoreIntegrityError('outgoing projection traversal incomplete')
    return result


def _immutable_targets(nodes):
    actual={inc:True for inc,n in nodes.items() if n.incoming.target.kind=='nan-key'}
    pending={inc:n for inc,n in nodes.items() if n.incoming.target.kind.startswith('frozen-')}
    while pending:
        progress=False
        for inc,n in tuple(pending.items()):
            deps={t.incarnation for t in n.certification_targets}
            if not deps<=actual.keys():continue
            values=(v for k,v in n.members) if n.incoming.target.kind=='frozen-map' else n.members
            valid=True
            for value in values:valid=immutable_snapshot_value(value,lambda ref:actual[ref.incarnation]) and valid
            if valid!=n.incoming.target.descriptor[3]:raise StoreIntegrityError('recursive frozen certification disagrees with complete descendants')
            actual[inc]=valid;del pending[inc];progress=True
        if not progress:raise StoreError('cyclic frozen certification requires a separate checked path')
    return tuple(sorted(actual.items()))


def _read_checked(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,
        max_targets=128,max_edges=4096,max_members=4096,max_children=4096,max_values=65536,max_bytes=33554432,max_source_bytes=1048576,max_metadata_bytes=1048576):
    """Private producer seam, under one already checked owned snapshot."""
    if not getattr(store,'_checked_snapshot_depth',0):raise StoreError('closure producer requires checked snapshot')
    target._pairs(store,pin,(content_authority,scope_authority,inventory_authority))
    if len(scope_authority[0].roots)!=6:raise StoreError('reference closure requires explicit six-root authority')
    if record_authority is not None:
        incoming.records._authority(store,pin,*record_authority);incoming.records._schemas(store.db)
        if incoming.records._load_root(store,pin.captured_head)[0]!=record_authority:raise StoreIntegrityError('closure record root disagreement')
    s=target._Sources(store,pin,content_authority,max_bytes,max_source_bytes,max_metadata_bytes,memoize=True)
    budget=ExtentWork(max_children,max_values,memoize=True);queue=deque();kinds={};nodes={};edges=[];members_left=max_members
    def discover(ref):
        kind,inc=target._reference(ref)
        if inc in kinds:
            if kinds[inc]!=kind:raise StoreIntegrityError('closure has conflicting kinds for one incarnation')
            return
        if len(kinds)>=max_targets:raise StoreError('reference closure exceeds target budget')
        kinds[inc]=kind;queue.append(ref)
    discover(reference)
    while queue:
        ref=queue.popleft();kind,inc=target._reference(ref)
        if members_left<1:raise StoreError('closure exceeds aggregate incoming-member budget')
        value,s=incoming._read_checked(store,pin,ref,content_authority,scope_authority,inventory_authority,record_authority=record_authority,
            max_members=members_left,max_bytes=s.remaining,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes,_sources=s)
        members_left-=len(value.group.occurrences)
        body=extents._physical(value.target,s,scope_authority,budget,max_targets)
        extents._check_policies(value,s,kind,body.member_counts)
        node=extents.RawTargetMembers(value,body.members,body.member_counts,body.child_locators,body.certification_targets,body.components);nodes[inc]=node
        for ns,typed,path,child in _owner_edges(s,scope_authority,body,max_edges-len(edges)):
            child_kind,child_inc=target._reference(child);discover(child)
            edges.append(RawReferenceEdge(inc,ns,typed,path,child_inc,child_kind))
    frozen=_immutable_targets(nodes)
    return RawReferenceClosure(reference,tuple(nodes[i] for i in sorted(nodes)),tuple(sorted(edges,key=lambda e:(e.source_incarnation,e.namespace,e.typed_key,e.path))),frozen),s


def read_reference_closure(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,
        max_targets=128,max_edges=4096,max_members=4096,max_children=4096,max_values=65536,max_bytes=33554432,max_source_bytes=1048576,max_metadata_bytes=1048576):
    for n,maximum in ((max_targets,1024),(max_edges,4096),(max_children,4096),(max_values,65536)):
        if type(n) is not int or not 1<=n<=maximum:raise StoreIntegrityError('invalid reference closure budget')
    options=dict(max_members=max_members,max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)
    incoming.groups._check(store,pin,reference,content_authority,scope_authority,inventory_authority,**options)
    if len(scope_authority[0].roots)!=6:raise StoreError('reference closure requires explicit six-root authority')
    if record_authority is not None:
        if type(record_authority) is not tuple or len(record_authority)!=2:raise StoreIntegrityError('invalid closure record authority')
        incoming.records._authority(store,pin,*record_authority)
    try:
        with store.read_snapshot(pin,_preflight=lambda:target._preflight(store,max_metadata_bytes)):
            return _read_checked(store,pin,reference,content_authority,scope_authority,inventory_authority,record_authority=record_authority,
                max_targets=max_targets,max_edges=max_edges,max_members=max_members,max_children=max_children,max_values=max_values,
                max_bytes=max_bytes,max_source_bytes=max_source_bytes,max_metadata_bytes=max_metadata_bytes)[0]
    except (CodecError,ValueError,TypeError,UnicodeError,RecursionError,IndexError,AttributeError,KeyError) as exc:raise StoreIntegrityError('invalid raw reference closure source') from exc
