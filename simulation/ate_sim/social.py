from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Relationship:
    a:int; b:int; familiarity:float=0.; trust:float=.5; attachment:float=0.; obligation:float=0.; resentment:float=0.; attraction:float=0.; shared_history:list[int]=field(default_factory=list)

@dataclass
class SocialGraph:
    edges:dict[tuple[int,int],Relationship]=field(default_factory=dict)
    partnerships:dict[tuple[int,int],int]=field(default_factory=dict)
    adjacency:dict[int,set[int]]=field(default_factory=dict)
    def key(self,a,b): return (min(a,b),max(a,b))
    def get(self,a,b):
        k=self.key(a,b)
        if k not in self.edges:
            self.edges[k]=Relationship(*k)
            self.adjacency.setdefault(k[0],set()).add(k[1])
            self.adjacency.setdefault(k[1],set()).add(k[0])
        return self.edges[k]
    def record(self,a,b,event_id,trust=0.,attachment=0.,obligation=0.,resentment=0.):
        r=self.get(a,b); r.familiarity=min(1.,r.familiarity+.03); r.trust=max(0.,min(1.,r.trust+trust)); r.attachment=max(0.,min(1.,r.attachment+attachment)); r.obligation=max(0.,min(1.,r.obligation+obligation)); r.resentment=max(0.,min(1.,r.resentment+resentment)); r.shared_history.append(event_id); return r
    def neighbors(self,pid): return self.adjacency.get(pid,())
    def relationships_for(self,pid): return (self.edges[self.key(pid,other)] for other in self.neighbors(pid))
    def partner(self,a,b,event_id): self.partnerships[self.key(a,b)]=event_id
    def is_partnered(self,a,b): return self.key(a,b) in self.partnerships
