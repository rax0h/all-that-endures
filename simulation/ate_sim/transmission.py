from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Transmission:
    id:int
    year:int
    kind:str
    item_kind:str
    item_id:int
    source_kind:str
    source_id:int
    target_kind:str
    target_id:int
    event_id:int|None=None
    reliability:float=1.0
    mutation:float=0.0

@dataclass
class TransmissionState:
    records:dict[int,Transmission]=field(default_factory=dict)
    next_id:int=1

    def record(self,year,kind,item_kind,item_id,source_kind,source_id,target_kind,target_id,event_id=None,reliability=1.0,mutation=0.0):
        tid=self.next_id; self.next_id+=1
        t=Transmission(tid,year,kind,item_kind,item_id,source_kind,source_id,target_kind,target_id,event_id,max(0.,min(1.,reliability)),max(0.,mutation))
        self.records[tid]=t
        return t

    def history(self,item_kind,item_id):
        return [t for t in self.records.values() if t.item_kind==item_kind and t.item_id==item_id]
