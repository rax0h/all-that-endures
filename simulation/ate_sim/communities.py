from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Community:
    id:int
    kind:str
    founded:int
    origin_settlement:int
    origin_event:int|None=None
    parent:int|None=None
    active:bool=True

@dataclass
class CommunityState:
    communities:dict[int,Community]=field(default_factory=dict)
    memberships:dict[tuple[int,int],float]=field(default_factory=dict)
    next_community:int=1

    def create(self,kind,year,origin_settlement,origin_event=None,parent=None):
        cid=self.next_community; self.next_community+=1
        c=Community(cid,kind,year,origin_settlement,origin_event,parent)
        self.communities[cid]=c
        if hasattr(self,'_kind_index'):self._kind_index.setdefault(kind,[]).append(cid);self._community_index_count=len(self.communities)
        if kind=='founder_network' and hasattr(self,'_root_index'):self._root_index.setdefault(origin_settlement,cid)
        if kind=='diaspora' and parent is not None and hasattr(self,'_diaspora_index'):self._diaspora_index.setdefault((parent,origin_settlement),cid)
        return c

    def join(self,person_id,community_id,strength=1.0):
        self.memberships[(person_id,community_id)]=max(0.,min(1.,strength))
        if hasattr(self,'_membership_index'):
            self._membership_index.setdefault(person_id,{})[community_id]=None

    def rebuild_membership_index(self):
        self._membership_index={}
        for pid,cid in self.memberships:
            self._membership_index.setdefault(pid,{})[cid]=None

    def memberships_for(self,person_id,minimum=.01):
        # IDs retain archive insertion order; strengths remain authoritative there.
        if not hasattr(self,'_membership_index'):self.rebuild_membership_index()
        return {cid:v for cid in self._membership_index.get(person_id,()) if (v:=self.memberships[(person_id,cid)])>=minimum}

    def inherit(self,child_id,parent_ids,weight=.72):
        inherited={}
        for pid in parent_ids:
            for cid,v in self.memberships_for(pid).items():inherited[cid]=max(inherited.get(cid,0.),v*weight)
        for cid,v in inherited.items():self.join(child_id,cid,v)
        return inherited

    def _ensure_community_indexes(self):
        if not hasattr(self,'_kind_index') or getattr(self,'_community_index_count',-1)!=len(self.communities):
            kinds={};roots={};diaspora={}
            for cid,c in self.communities.items():
                kinds.setdefault(c.kind,[]).append(cid)
                if c.kind=='founder_network':roots.setdefault(c.origin_settlement,cid)
                if c.kind=='diaspora' and c.parent is not None:diaspora.setdefault((c.parent,c.origin_settlement),cid)
            self._kind_index=kinds;self._root_index=roots;self._diaspora_index=diaspora;self._community_index_count=len(self.communities)
    def communities_of_kind(self,kind,active_only=False):
        self._ensure_community_indexes()
        values=[self.communities[cid] for cid in self._kind_index.get(kind,())]
        return [c for c in values if c.active] if active_only else values
    def local_root(self,settlement):
        self._ensure_community_indexes();return self._root_index.get(settlement)

    def diaspora(self,parent_id,destination,year,event_id):
        self._ensure_community_indexes();existing=self._diaspora_index.get((parent_id,destination))
        if existing is not None:return self.communities[existing]
        return self.create("diaspora",year,destination,event_id,parent_id)

def community_step(world):
    for p in world.current_people():
        if not p.alive:continue
        local=world.communities.local_root(p.settlement)
        if local is not None:
            key=(p.id,local);current=world.communities.memberships.get(key,0.);world.communities.join(p.id,local,min(1.,current+.012*(1-current)))
        for cid,v in list(world.communities.memberships_for(p.id).items()):
            c=world.communities.communities[cid]
            if c.origin_settlement!=p.settlement and c.kind!="diaspora":world.communities.join(p.id,cid,max(.01,v*.9995))
