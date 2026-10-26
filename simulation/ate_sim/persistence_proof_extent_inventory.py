"""Bounded complete physical locator inventories for selected raw extents."""
from .incremental_store import StoreError,StoreIntegrityError
from .persistence_proof_seek import OrderedSeekMap
from . import persistence_proof_scope as scopes


class ExtentWork:
    def __init__(self,children,values,*,memoize=False):
        self.children,self.values=children,values;self.extents={} if memoize else None
    def take_values(self,n):
        self.values-=n
        if self.values<0:raise StoreError('selected extents exceed value-work budget')
    def take_children(self,n):
        self.children-=n
        if self.children<0:raise StoreError('selected extents exceed child budget')


def physical_locators(s,pair,inc,budget,*,require_sequence=False):
    if require_sequence and len(pair[0].roots)!=6:raise StoreError('extent requires explicitly constructed sequence authority')
    scopes_to_read=[(scopes.ChildScope(inc),scopes._CHILD_NAMES,scopes._child_locator)]
    if len(pair[0].roots)==6:scopes_to_read.append((scopes.SequenceScope(inc),scopes._SEQUENCE_NAMES,scopes._sequence_locator))
    locators=[]
    for scope,names,locator in scopes_to_read:
        root=scopes._resolve(s.store,pair[0],scope);budget.take_children(root.count)
        m=OrderedSeekMap(s.store.db,scopes._seek_domain(s.store,scope));after=None;seen=0
        while True:
            rows=m.page(root,after=after,limit=128)
            for position,commitment in rows:
                if not position or position[0]>=len(names) or commitment!=scopes._child_member(m.domain,position):raise StoreIntegrityError('invalid extent locator proof')
                ns=names[position[0]];typed=position[1:];key=s.codec.decode(typed)
                if locator(ns,typed)!=(scope,position):raise StoreIntegrityError('extent locator parent disagreement')
                s.charge(len(position)+32);locators.append((ns,key));seen+=1
            if len(rows)<128:break
            after=rows[-1][0]
        if seen!=root.count:raise StoreIntegrityError('incomplete physical locator traversal')
    s.read_limit+=len(locators)+2
    return tuple(locators)
