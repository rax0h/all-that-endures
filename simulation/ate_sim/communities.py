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
        return c

    def join(self,person_id,community_id,strength=1.0):
        self.memberships[(person_id,community_id)]=max(0.,min(1.,strength))

    def memberships_for(self,person_id,minimum=.01):
        return {cid:v for (pid,cid),v in self.memberships.items() if pid==person_id and v>=minimum}

    def inherit(self,child_id,parent_ids,weight=.72):
        inherited={}
        for pid in parent_ids:
            for cid,v in self.memberships_for(pid).items():inherited[cid]=max(inherited.get(cid,0.),v*weight)
        for cid,v in inherited.items():self.join(child_id,cid,v)
        return inherited

    def local_root(self,settlement):
        roots=[c.id for c in self.communities.values() if c.kind=="founder_network" and c.origin_settlement==settlement]
        return min(roots) if roots else None

    def diaspora(self,parent_id,destination,year,event_id):
        existing=[c for c in self.communities.values() if c.kind=="diaspora" and c.parent==parent_id and c.origin_settlement==destination]
        if existing:return min(existing,key=lambda c:c.id)
        return self.create("diaspora",year,destination,event_id,parent_id)

def community_step(world):
    for p in world.people.values():
        if not p.alive:continue
        local=world.communities.local_root(p.settlement)
        if local is not None:
            key=(p.id,local);current=world.communities.memberships.get(key,0.);world.communities.memberships[key]=min(1.,current+.012*(1-current))
        for cid,v in list(world.communities.memberships_for(p.id).items()):
            c=world.communities.communities[cid]
            if c.origin_settlement!=p.settlement and c.kind!="diaspora":world.communities.memberships[(p.id,cid)]=max(.01,v*.9995)
