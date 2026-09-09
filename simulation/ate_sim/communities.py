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
