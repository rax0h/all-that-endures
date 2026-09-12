from __future__ import annotations
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
import hashlib, json, math
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
from .magic_resources import MagicResourceState
from .institutions import InstitutionState
from .metaphysics import MetaphysicalState
from .divinity import DivineState
from .materials import MaterialEconomy
from .ambient_magic import AmbientMagicState
from .warfare import WarfareState
from .society_accountability import SocietyAccountabilityState
from .currency import RankedCurrencyState
from .threat_ecology import ThreatEcologyState
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
 seed:int; year:int=0; cells:dict[tuple[int,int],Cell]=field(default_factory=dict); people:dict[int,Person]=field(default_factory=dict); households:dict[int,Household]=field(default_factory=dict); settlements:dict[int,Settlement]=field(default_factory=dict); local:dict[int,LocalState]=field(default_factory=dict); trade_routes:dict[tuple[int,int],TradeRoute]=field(default_factory=dict); events:list[Event]=field(default_factory=list); event_ids:set[int]=field(default_factory=set); genealogy:Genealogy=field(default_factory=Genealogy); social:SocialGraph=field(default_factory=SocialGraph); economy:Economy=field(default_factory=Economy); knowledge:KnowledgeState=field(default_factory=KnowledgeState); culture:CulturalState=field(default_factory=CulturalState); lineage:LineageState=field(default_factory=LineageState); communities:CommunityState=field(default_factory=CommunityState); transmission:TransmissionState=field(default_factory=TransmissionState); skills:SkillState=field(default_factory=SkillState); infrastructure:InfrastructureState=field(default_factory=InfrastructureState); agency:AgencyState=field(default_factory=AgencyState); advancement:AdvancementState=field(default_factory=AdvancementState); magic_resources:MagicResourceState=field(default_factory=MagicResourceState); institutions:InstitutionState=field(default_factory=InstitutionState); metaphysics:MetaphysicalState=field(default_factory=MetaphysicalState); divinity:DivineState=field(default_factory=DivineState); materials:MaterialEconomy=field(default_factory=MaterialEconomy); ambient_magic:AmbientMagicState=field(default_factory=AmbientMagicState); warfare:WarfareState=field(default_factory=WarfareState); society_accountability:SocietyAccountabilityState=field(default_factory=SocietyAccountabilityState); currency:RankedCurrencyState=field(default_factory=RankedCurrencyState); threat_ecology:ThreatEcologyState=field(default_factory=ThreatEcologyState); next_person:int=1; next_household:int=1; next_settlement:int=1; next_event:int=1
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

_MASK=(1<<64)-1
class _FastRandom:
 __slots__=('state','_gauss')
 def __init__(self,seed):self.state=seed&_MASK or 0x9E3779B97F4A7C15;self._gauss=None
 def _next(self):
  self.state=(self.state+0x9E3779B97F4A7C15)&_MASK;z=self.state;z=((z^(z>>30))*0xBF58476D1CE4E5B9)&_MASK;z=((z^(z>>27))*0x94D049BB133111EB)&_MASK;return (z^(z>>31))&_MASK
 def random(self):return (self._next()>>11)*(1.0/(1<<53))
 def uniform(self,a,b):return a+(b-a)*self.random()
 def getrandbits(self,k):
  if k<=0:return 0
  out=0;shift=0
  while shift<k:
   out|=self._next()<<shift;shift+=64
  return out&((1<<k)-1)
 def randrange(self,start,stop=None,step=1):
  if stop is None:start,stop=0,start
  if step==0:raise ValueError('zero step for randrange()')
  n=(stop-start+step-(1 if step>0 else -1))//step if step>0 else (start-stop-step-1)//(-step)
  if n<=0:raise ValueError('empty range for randrange()')
  return start+(int(self.random()*n)%n)*step
 def randint(self,a,b):return self.randrange(a,b+1)
 def choice(self,seq):
  if not seq:raise IndexError('cannot choose from an empty sequence')
  return seq[int(self.random()*len(seq))%len(seq)]
 def shuffle(self,x):
  for i in range(len(x)-1,0,-1):
   j=int(self.random()*(i+1))%(i+1);x[i],x[j]=x[j],x[i]
 def gauss(self,mu=0.0,sigma=1.0):
  if self._gauss is not None:z=self._gauss;self._gauss=None;return mu+z*sigma
  u1=max(1e-15,self.random());u2=self.random();r=math.sqrt(-2.0*math.log(u1));theta=2.0*math.pi*u2;z0=r*math.cos(theta);self._gauss=r*math.sin(theta);return mu+z0*sigma
 def sample(self,population,k):
  if k<0 or k>len(population):raise ValueError('sample larger than population')
  pool=list(population);out=[]
  for _ in range(k):
   i=int(self.random()*len(pool))%len(pool);out.append(pool.pop(i))
  return out
 def choices(self,population,weights=None,cum_weights=None,k=1):
  if not population:raise IndexError('cannot choose from an empty sequence')
  if weights is None and cum_weights is None:return [self.choice(population) for _ in range(k)]
  if cum_weights is None:
   total=0.;cum_weights=[]
   for w in weights:total+=w;cum_weights.append(total)
  total=cum_weights[-1];out=[]
  for _ in range(k):
   x=self.random()*total;i=0
   while i<len(cum_weights)-1 and x>=cum_weights[i]:i+=1
   out.append(population[i])
  return out

class RNG:
 def __init__(self,seed):self.seed=seed&_MASK;self._names={}
 def _name_key(self,namespace):
  key=self._names.get(namespace)
  if key is not None:return key
  h=0xCBF29CE484222325
  for b in namespace.encode():h=((h^b)*0x100000001B3)&_MASK
  self._names[namespace]=h;return h
 def stream(self,namespace,year=0,entity=0):
  x=(self.seed^self._name_key(namespace)^((year*0xD6E8FEB86659FD93)&_MASK)^((entity*0xA5A3564E27F8862D)&_MASK))&_MASK
  x=(x^(x>>30))*0xBF58476D1CE4E5B9&_MASK;x=(x^(x>>27))*0x94D049BB133111EB&_MASK;x^=x>>31
  return _FastRandom(x)
