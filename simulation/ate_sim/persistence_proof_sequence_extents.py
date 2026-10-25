"""Read-only complete counted-sequence checks over accepted raw sources.

Borrow pure existing commitment rules; construct no mutable sequence facade.
"""
from collections import defaultdict
from .incremental_store import StoreIntegrityError,_framed_sha
from .persistence_lazy_nested_history import stored_value
from . import persistence_lazy_sequence as q
from .persistence_proof_extent_inventory import physical_locators


class _CheckedSequence:
    _node_commit=q.LazyOrderedSequence._node_commit
    _member_commit=q.LazyOrderedSequence._member_commit
    _directory_commit=q.LazyOrderedSequence._directory_commit
    _member_key=staticmethod(q.LazyOrderedSequence._member_key)

    def __init__(self,s,backing,locators):
        self.s=s;self._incarnation=backing.incarnation;d=backing.descriptor
        self._next_occurrence,self._next_node=d[4:6];self.native=len(d)==9
        self.inventory=set(locators);self.loaded={}
    def _valid_value(self,v):return stored_value(v) if self.native else type(v) is int and v>0
    def _digest(self,ns,key,value):return _framed_sha(b'counted-sequence-node/v1',self.s.codec.encode((ns,key,value)))
    def _member_hash(self,value):return bytes.fromhex(_framed_sha(b'sequence-member-key/v1',self.s.codec.encode(value)))
    def read(self,ns,key):
        marker=ns,key
        if marker not in self.inventory:raise StoreIntegrityError('sequence authority missing from complete inventory')
        if marker not in self.loaded:self.loaded[marker]=self.s.metadata(ns,key)
        return self.loaded[marker]
    def same(self,a,b):return self.s.codec.encode(a)==self.s.codec.encode(b)


def read_sequence_extent(backing,s,scope_pair,budget):
    from .persistence_proof_child_extents import RawBackingExtent,_check_witness
    d=backing.descriptor;budget.take_values(d[3])
    locators=physical_locators(s,scope_pair,backing.incarnation,budget,require_sequence=True)
    c=_CheckedSequence(s,backing,locators);inc=backing.incarnation;occurrences={};members=defaultdict(list);seen_nodes=set();values=[]
    def main(link,parent,root=False):
        if not q._link(link) or link[0]>=d[5]:raise StoreIntegrityError('invalid sequence main link')
        key=inc,link[0]
        if key in seen_nodes:raise StoreIntegrityError('cyclic/duplicate main sequence node')
        seen_nodes.add(key);node=c.read(q.NODE_NAMESPACE,key)
        if not c.same(c._node_commit(link[0],node),link):raise StoreIntegrityError('sequence main commitment disagrees')
        if not c.same(c.read(q.PARENT_NAMESPACE,key),parent):raise StoreIntegrityError('sequence reciprocal parent disagrees')
        kind,entries=node
        if not root and len(entries)<(q.LEAF_SIZE//2 if kind=='leaf' else q.FANOUT//2):raise StoreIntegrityError('underfull sequence node')
        if root and kind=='branch' and len(entries)<2:raise StoreIntegrityError('uncollapsed sequence root')
        if kind=='branch':
            for slot,child in enumerate(entries):main(child,(link[0],slot))
        else:
            for slot,(occurrence,value) in enumerate(entries):
                if occurrence in occurrences:raise StoreIntegrityError('duplicate sequence occurrence')
                occurrences[occurrence]=(len(values),value);values.append(value)
                member=c._member_key(value)
                if member is not None:members[member].append(occurrence)
                if not c.same(c.read(q.LOCATOR_NAMESPACE,(inc,occurrence)),(link[0],slot)):raise StoreIntegrityError('sequence locator disagrees')
    main(d[2],(None,0),True)
    if len(values)!=d[3]:raise StoreIntegrityError('sequence descriptor length disagrees')
    found={};seen_directory=set();seen_members=set()
    def directory(link):
        if not q._directory_link(link):raise StoreIntegrityError('invalid sequence directory link')
        key=inc,link[0]
        if key in seen_directory:raise StoreIntegrityError('duplicate/cyclic sequence directory')
        seen_directory.add(key);node=c.read(q.DIRECTORY_NAMESPACE,key)
        if not c.same(c._directory_commit(link[0],node),link):raise StoreIntegrityError('sequence directory commitment disagrees')
        if node[0]=='directory-branch/v1':
            for child in node[2]:directory(child[1:])
            return
        value,root=node[1:];order=[]
        def member(link,lower,upper):
            if link is None:return
            if not q._link(link) or not 0<link[0]<d[4]:raise StoreIntegrityError('invalid sequence membership link')
            key=inc,link[0]
            if key in seen_members:raise StoreIntegrityError('duplicate/cyclic sequence membership')
            seen_members.add(key);m=c.read(q.MEMBER_NAMESPACE,key)
            if not c.same(c._member_commit(link[0],m),link) or m[1]!=value:raise StoreIntegrityError('sequence membership commitment/value disagrees')
            rank,actual=occurrences.get(link[0],(-1,None))
            if actual!=value or not lower<rank<upper:raise StoreIntegrityError('sequence membership rank/value disagrees')
            member(m[2],lower,rank);order.append(link[0]);member(m[3],rank,upper)
        member(root,-1,len(values))
        if value in found:raise StoreIntegrityError('duplicate sequence member directory value')
        found[value]=order
    if d[7] is not None:directory(d[7])
    if dict(members)!=found:raise StoreIntegrityError('incomplete sequence memberships')
    if set(c.loaded)!=c.inventory:raise StoreIntegrityError('surplus physical sequence authority')
    from .persistence_history_types import member_counts
    counts=member_counts(values);_check_witness(s,inc,'sequence',counts)
    return RawBackingExtent(backing,tuple(values),counts,locators)
