from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class MagicResource:
 id:int
 kind:str
 key:str
 rarity:str
 location:int|None
 owner_kind:str|None=None
 owner_id:int|None=None
 created_year:int=0
 origin_event:int|None=None
 consumed_year:int|None=None
 consumed_by:int|None=None
 consumed_event:int|None=None
 transfers:list[int]=field(default_factory=list)

@dataclass
class MagicResourceState:
 resources:dict[int,MagicResource]=field(default_factory=dict)
 next_id:int=1

 def create(self,kind,key,rarity,year,location=None,owner_kind=None,owner_id=None,origin_event=None):
  rid=self.next_id;self.next_id+=1
  r=MagicResource(rid,kind,key,rarity,location,owner_kind,owner_id,year,origin_event)
  self.resources[rid]=r
  return r

 def available(self,rid):
  r=self.resources.get(rid)
  return r is not None and r.consumed_year is None

 def inventory(self,owner_kind,owner_id,kind=None):
  return [r for r in self.resources.values() if r.consumed_year is None and r.owner_kind==owner_kind and r.owner_id==owner_id and (kind is None or r.kind==kind)]

 def transfer(self,rid,owner_kind,owner_id,event_id,location=None):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('consumed magical resource cannot be transferred')
  r.owner_kind=owner_kind;r.owner_id=owner_id
  if location is not None:r.location=location
  r.transfers.append(event_id)
  return r

 def consume(self,rid,pid,year,event_id):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('magical resource already consumed')
  if r.owner_kind not in (None,'person') or (r.owner_kind=='person' and r.owner_id!=pid):raise ValueError('person does not possess magical resource')
  r.consumed_year=year;r.consumed_by=pid;r.consumed_event=event_id
  return r
