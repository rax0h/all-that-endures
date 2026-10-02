from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Property:
    id:int; kind:str; settlement:int; owner_kind:str; owner_id:int; value:float; created:int; provenance:list[int]=field(default_factory=list); ownership:list[tuple[int,str,int,int|None]]=field(default_factory=list)

@dataclass
class Economy:
    property:dict[int,Property]=field(default_factory=dict); next_property:int=1

    def _ensure_owner_index(self):
        if not hasattr(self,'_owner_index') or getattr(self,'_property_index_count',-1)!=len(self.property):
            index={}
            for pid,p in self.property.items():index.setdefault((p.owner_kind,p.owner_id),set()).add(pid)
            self._owner_index=index;self._property_index_count=len(self.property)

    def create(self,kind,settlement,owner_kind,owner_id,value,year,event_id=None):
        i=self.next_property; self.next_property+=1
        p=Property(i,kind,settlement,owner_kind,owner_id,value,year,[] if event_id is None else [event_id],[(year,owner_kind,owner_id,event_id)])
        self.property[i]=p
        if hasattr(self,'_owner_index'):
            self._owner_index.setdefault((owner_kind,owner_id),set()).add(i);self._property_index_count=len(self.property)
        return p

    def properties_for_owner(self,owner_kind,owner_id):
        self._ensure_owner_index();return [self.property[i] for i in self._owner_index.get((owner_kind,owner_id),())]

    def transfer(self,pid,owner_kind,owner_id,event_id,year=None):
        p=self.property[pid]
        if hasattr(self,'_owner_index'):
            self._owner_index.get((p.owner_kind,p.owner_id),set()).discard(pid)
            self._owner_index.setdefault((owner_kind,owner_id),set()).add(pid)
        p.owner_kind=owner_kind;p.owner_id=owner_id;p.provenance.append(event_id);p.ownership.append((p.created if year is None else year,owner_kind,owner_id,event_id))
