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

    def _ensure_indexes(self):
        if not hasattr(self,'_kind_index') or getattr(self,'_asset_index_count',-1)!=len(self.assets):
            kinds={};local={};routes={}
            for aid,a in self.assets.items():
                kinds.setdefault(a.kind,[]).append(aid)
                for sid in a.settlements:local.setdefault((a.kind,sid),[]).append(aid)
                if a.kind=='road' and len(a.settlements)>=2:
                    ss=tuple(sorted(a.settlements))
                    for i,x in enumerate(ss):
                        for y in ss[i+1:]:routes.setdefault((x,y),[]).append(aid)
            self._kind_index=kinds;self._local_index=local;self._route_index=routes;self._asset_index_count=len(self.assets)

    def create(self,kind,settlements,condition,capacity,year,event_id=None):
        i=self.next_id;self.next_id+=1
        a=Infrastructure(i,kind,tuple(settlements),max(0.,min(1.,condition)),max(0.,capacity),year,event_id,[] if event_id is None else [event_id]);self.assets[i]=a
        if hasattr(self,'_kind_index'):
            self._kind_index.setdefault(kind,[]).append(i)
            for sid in a.settlements:self._local_index.setdefault((kind,sid),[]).append(i)
            if kind=='road' and len(a.settlements)>=2:
                ss=tuple(sorted(a.settlements))
                for n,x in enumerate(ss):
                    for y in ss[n+1:]:self._route_index.setdefault((x,y),[]).append(i)
            self._asset_index_count=len(self.assets)
        return a

    def assets_of_kind(self,kind):
        self._ensure_indexes();return [self.assets[i] for i in self._kind_index.get(kind,())]

    def at_settlement(self,kind,sid):
        self._ensure_indexes();return [self.assets[i] for i in self._local_index.get((kind,sid),())]

    def maintain(self,i,effort,event_id=None):
        a=self.assets[i];a.condition=min(1.,a.condition+max(0.,effort)*(1-a.condition))
        if event_id is not None:a.provenance.append(event_id)
        return a.condition

    def decay(self,rate=.001):
        for a in self.assets.values():a.condition=max(0.,a.condition-rate)

    def route_condition(self,a,b):
        self._ensure_indexes();ids=self._route_index.get(tuple(sorted((a,b))),())
        return max((self.assets[i].condition for i in ids),default=0.)
