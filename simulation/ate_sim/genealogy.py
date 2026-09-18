from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Genealogy:
    parents:dict[int,tuple[int,...]]=field(default_factory=dict); children:dict[int,list[int]]=field(default_factory=dict)
    def birth(self,child:int,parents:tuple[int,...]):
        self.parents[child]=parents
        for p in parents:self.children.setdefault(p,[]).append(child)
    def ancestors(self,pid:int,depth=8):
        # Parentage is immutable after birth, so ancestry is a derived value
        # that can be cached without becoming canonical simulation state.
        cache=self.__dict__.setdefault('_ancestor_cache',{})
        key=(pid,depth);cached=cache.get(key)
        if cached is not None:return set(cached)
        out=set(); frontier={pid}
        for _ in range(depth):
            nxt=set()
            for x in frontier:
                for p in self.parents.get(x,()):
                    if p not in out:out.add(p); nxt.add(p)
            frontier=nxt
            if not frontier:break
        cache[key]=frozenset(out)
        return set(out)
