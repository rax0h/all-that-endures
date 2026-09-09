from __future__ import annotations
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
import hashlib, json, random
from typing import Any
from .genealogy import Genealogy
from .social import SocialGraph
from .economy import Economy
from .knowledge import KnowledgeState
from .culture import CulturalState
from .lineage import LineageState
from .communities import CommunityState
from .transmission import TransmissionState
from .skills import SkillState
from .infrastructure import InfrastructureState
from .agency import AgencyState
from .advancement import AdvancementState
class Layer(str,Enum): REALITY='reality'; SOCIETY='society'; KNOWLEDGE='knowledge'; NARRATIVE='narrative'
@dataclass(frozen=True)
class Ref: kind:str; id:int
@dataclass
class Event: id:int; year:int; kind:str; layer:Layer; actors:tuple[Ref,...]=(); location:Ref|None=None; causes:tuple[int,...]=(); data:dict[str,Any]=field(default_factory=dict)
@dataclass
class Person:
 id:int; born:int; settlement:int; household:int; alive:bool=True; age:int=0; wealth:float=0.; health:float=1.; temperament:float=.5; attachment:float=.5; curiosity:float=.5; inhibition:float=.5; grief:float=0.; fear:float=0.; rank:int=0; species:str='human'; occupation:str='labor'; parents:tuple[int,...]=()
@dataclass
class Household: id:int; settlement:int; members:list[int]=field(default_factory=list); wealth:float=0.; food:float=10.; preparedness:float=.2; lineage:str=''; alive:bool=True
@dataclass
class Settlement: id:int; x:int; y:int; households:list[int]=field(default_factory=list); food_stock:float=100.; defense:float=.1; irrigation:float=.1; roads:float=.1; prosperity:float=.3; memory:dict[str,float]=field(default_factory=dict)
@dataclass
class Cell: x:int; y:int; elevation:float; moisture:float; fertility:float; forest:float; hazard:float
@dataclass
class LocalState: rain:float=.5; drought:float=0.; flood:float=0.; scarcity:float=0.
@dataclass
class TradeRoute: a:int; b:int; strength:float=.05; exchanges:int=0; last_used:int=0
def _canonical(value):
 if is_dataclass(value): return _canonical(asdict(value))
 if isinstance(value,Enum): return value.value
 if isinstance(value,dict): return {repr(k):_canonical(v) for k,v in sorted(value.items(),key=lambda kv:repr(kv[0]))}
 if isinstance(value,(list,tuple)): return [_canonical(v) for v in value]
 if isinstance(value,set): return sorted((_canonical(v) for v in value),key=repr)
 return value
@dataclass
class World:
 seed:int; year:int=0; cells:dict[tuple[int,int],Cell]=field(default_factory=dict); people:dict[int,Person]=field(default_factory=dict); households:dict[int,Household]=field(default_factory=dict); settlements:dict[int,Settlement]=field(default_factory=dict); local:dict[int,LocalState]=field(default_factory=dict); trade_routes:dict[tuple[int,int],TradeRoute]=field(default_factory=dict); events:list[Event]=field(default_factory=list); event_ids:set[int]=field(default_factory=set); genealogy:Genealogy=field(default_factory=Genealogy); social:SocialGraph=field(default_factory=SocialGraph); economy:Economy=field(default_factory=Economy); knowledge:KnowledgeState=field(default_factory=KnowledgeState); culture:CulturalState=field(default_factory=CulturalState); lineage:LineageState=field(default_factory=LineageState); communities:CommunityState=field(default_factory=CommunityState); transmission:TransmissionState=field(default_factory=TransmissionState); skills:SkillState=field(default_factory=SkillState); infrastructure:InfrastructureState=field(default_factory=InfrastructureState); agency:AgencyState=field(default_factory=AgencyState); advancement:AdvancementState=field(default_factory=AdvancementState); next_person:int=1; next_household:int=1; next_settlement:int=1; next_event:int=1
 def emit(self,kind,layer,actors=(),location=None,causes=(),**data):
  if layer is None:raise ValueError('events require an explicit layer')
  if any(c not in self.event_ids for c in causes):raise ValueError('event cause does not exist')
  e=Event(self.next_event,self.year,kind,layer,tuple(actors),location,tuple(causes),data);self.next_event+=1;self.events.append(e);self.event_ids.add(e.id);return e
 def living(self):return [p for p in self.people.values() if p.alive]
 def living_by_settlement(self):
  out={sid:[] for sid in self.settlements}
  for p in self.people.values():
   if p.alive:out[p.settlement].append(p)
  return out
 def digest(self):return hashlib.sha256(json.dumps(_canonical(self),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
class RNG:
 def __init__(self,seed):self.seed=seed
 def stream(self,namespace,year=0,entity=0):
  h=hashlib.blake2b(f'{self.seed}|{namespace}|{year}|{entity}'.encode(),digest_size=8).digest();return random.Random(int.from_bytes(h,'big'))
