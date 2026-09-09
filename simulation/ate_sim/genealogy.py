from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Genealogy:
    parents:dict[int,tuple[int,...]]=field(default_factory=dict); children:dict[int,list[int]]=field(default_factory=dict)
    def birth(self,child:int,parents:tuple[int,...]):
        self.parents[child]=parents
        for p in parents:self.children.setdefault(p,[]).append(child)
    def ancestors(self,pid:int,depth=8):
        out=set(); frontier={pid}
        for _ in range(depth):
            nxt=set()
            for x in frontier:
                for p in self.parents.get(x,()):
                    if p not in out:out.add(p); nxt.add(p)
            frontier=nxt
            if not frontier:break
        return out
