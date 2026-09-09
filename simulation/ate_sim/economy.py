from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Property:
    id:int; kind:str; settlement:int; owner_kind:str; owner_id:int; value:float; created:int; provenance:list[int]=field(default_factory=list); ownership:list[tuple[int,str,int,int|None]]=field(default_factory=list)

@dataclass
class Economy:
    property:dict[int,Property]=field(default_factory=dict); next_property:int=1
    def create(self,kind,settlement,owner_kind,owner_id,value,year,event_id=None):
        i=self.next_property; self.next_property+=1; p=Property(i,kind,settlement,owner_kind,owner_id,value,year,[] if event_id is None else [event_id],[(year,owner_kind,owner_id,event_id)]); self.property[i]=p; return p
    def transfer(self,pid,owner_kind,owner_id,event_id,year=None):
        p=self.property[pid]; p.owner_kind=owner_kind; p.owner_id=owner_id; p.provenance.append(event_id); p.ownership.append((p.created if year is None else year,owner_kind,owner_id,event_id))
