from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class LineageNode:
    kind:str
    id:int
    parents:tuple[tuple[str,int],...]=()
    origin_event:int|None=None
    origin_year:int=0

@dataclass
class LineageState:
    nodes:dict[tuple[str,int],LineageNode]=field(default_factory=dict)
    children:dict[tuple[str,int],set[tuple[str,int]]]=field(default_factory=dict)

    def register(self,kind:str,entity_id:int,parents=(),origin_event=None,origin_year=0):
        key=(kind,entity_id)
        node=LineageNode(kind,entity_id,tuple(parents),origin_event,origin_year)
        self.nodes[key]=node
        for parent in node.parents:self.children.setdefault(parent,set()).add(key)
        return node

    def ancestors(self,kind:str,entity_id:int,depth=16):
        out=set(); frontier={(kind,entity_id)}
        for _ in range(depth):
            nxt=set()
            for key in frontier:
                node=self.nodes.get(key)
                if not node:continue
                for parent in node.parents:
                    if parent not in out:out.add(parent);nxt.add(parent)
            frontier=nxt
            if not frontier:break
        return out
