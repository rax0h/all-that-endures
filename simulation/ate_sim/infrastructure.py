from __future__ import annotations
from dataclasses import dataclass,field

@dataclass
class Infrastructure:
    id:int
    kind:str
    settlements:tuple[int,...]
    condition:float
    capacity:float
    built:int
    origin_event:int|None=None
    provenance:list[int]=field(default_factory=list)

@dataclass
class InfrastructureState:
    assets:dict[int,Infrastructure]=field(default_factory=dict)
    next_id:int=1

    def create(self,kind,settlements,condition,capacity,year,event_id=None):
        i=self.next_id;self.next_id+=1
        a=Infrastructure(i,kind,tuple(settlements),max(0.,min(1.,condition)),max(0.,capacity),year,event_id,[] if event_id is None else [event_id]);self.assets[i]=a;return a

    def maintain(self,i,effort,event_id=None):
        a=self.assets[i];a.condition=min(1.,a.condition+max(0.,effort)*(1-a.condition))
        if event_id is not None:a.provenance.append(event_id)
        return a.condition

    def decay(self,rate=.001):
        for a in self.assets.values():a.condition=max(0.,a.condition-rate)

    def route_condition(self,a,b):
        vals=[x.condition for x in self.assets.values() if x.kind=='road' and set((a,b)).issubset(set(x.settlements))]
        return max(vals) if vals else 0.
