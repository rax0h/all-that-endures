from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Property:
    id:int; kind:str; settlement:int; owner_kind:str; owner_id:int; value:float; created:int; provenance:list[int]=field(default_factory=list); ownership:list[tuple[int,str,int,int|None]]=field(default_factory=list)

@dataclass
class Economy:
    property:dict[int,Property]=field(default_factory=dict); next_property:int=1
    def _ensure_owner_index(self):
        # Derived hot-state only: it is deliberately not a dataclass field, so
        # canonical history/digests remain unchanged and old checkpoints rebuild.
        if not hasattr(self,'_owner_index'):
            self._owner_index={}
            for p in self.property.values():
                self._owner_index.setdefault((p.owner_kind,p.owner_id),set()).add(p.id)
        return self._owner_index
    def owned_ids(self,owner_kind,owner_id):
        return self._ensure_owner_index().get((owner_kind,owner_id),())
    def owner_buckets(self,owner_kind):
        idx=self._ensure_owner_index()
        return ((oid,ids) for (kind,oid),ids in idx.items() if kind==owner_kind and ids)
    def create(self,kind,settlement,owner_kind,owner_id,value,year,event_id=None):
        i=self.next_property; self.next_property+=1; p=Property(i,kind,settlement,owner_kind,owner_id,value,year,[] if event_id is None else [event_id],[(year,owner_kind,owner_id,event_id)]); self.property[i]=p
        if hasattr(self,'_owner_index'):self._owner_index.setdefault((owner_kind,owner_id),set()).add(i)
        return p
    def transfer(self,pid,owner_kind,owner_id,event_id,year=None):
        p=self.property[pid];old=(p.owner_kind,p.owner_id)
        if hasattr(self,'_owner_index'):
            ids=self._owner_index.get(old)
            if ids is not None:
                ids.discard(pid)
                if not ids:self._owner_index.pop(old,None)
            self._owner_index.setdefault((owner_kind,owner_id),set()).add(pid)
        p.owner_kind=owner_kind; p.owner_id=owner_id; p.provenance.append(event_id); p.ownership.append((p.created if year is None else year,owner_kind,owner_id,event_id))
