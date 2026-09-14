from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
from heapq import heappush, heappop, heapify
from .core_types import layer_ref
from .magic_progression import record_body_transition
from .currency import can_pay_tier
from math import ceil
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES

RESOURCE_DISCOVERY_RATE=.45

@dataclass
class MagicAspiration:
 drive:float;desired_base_essences:int;desired_abilities:int;reason:str;formed_year:int;preparation:float=0.;search_years:int=0;completion_goal:bool=False;urgency:float=.0;compromise_tolerance:float=.5;stone_selectiveness:float=.5;risk_tolerance:float=.5;adventurer_aspiration:bool=False
@dataclass
class MagicResource:
 id:int;kind:str;key:str;rarity:str;location:int|None;owner_kind:str|None=None;owner_id:int|None=None;created_year:int=0;origin_event:int|None=None;consumed_year:int|None=None;consumed_by:int|None=None;consumed_event:int|None=None;transfers:list[int]=field(default_factory=list)
@dataclass
class MagicResourceState:
 resources:dict[int,MagicResource]=field(default_factory=dict);owner_index:dict[tuple[str,int],set[int]]=field(default_factory=dict);aspirations:dict[int,MagicAspiration]=field(default_factory=dict);next_id:int=1
 def _index_add(self,r):
  if r.owner_kind is not None and r.owner_id is not None:self.owner_index.setdefault((r.owner_kind,r.owner_id),set()).add(r.id)
 def _index_remove(self,r):
  if r.owner_kind is None or r.owner_id is None:return
  key=(r.owner_kind,r.owner_id);bucket=self.owner_index.get(key)
  if bucket is not None:
   bucket.discard(r.id)
   if not bucket:self.owner_index.pop(key,None)
 def create(self,kind,key,rarity,year,location=None,owner_kind=None,owner_id=None,origin_event=None):
  rid=self.next_id;self.next_id+=1;r=MagicResource(rid,kind,key,rarity,location,owner_kind,owner_id,year,origin_event);self.resources[rid]=r;self._index_add(r);return r
 def available(self,rid):
  r=self.resources.get(rid);return r is not None and r.consumed_year is None
 def inventory(self,owner_kind,owner_id,kind=None):
  ids=sorted(self.owner_index.get((owner_kind,owner_id),()));return [self.resources[rid] for rid in ids if self.resources[rid].consumed_year is None and (kind is None or self.resources[rid].kind==kind)]
 def transfer(self,rid,owner_kind,owner_id,event_id,location=None):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('consumed magical resource cannot be transferred')
  self._index_remove(r);r.owner_kind=owner_kind;r.owner_id=owner_id;self._index_add(r)
  if location is not None:r.location=location
  r.transfers.append(event_id);return r
 def consume(self,rid,pid,year,event_id):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('magical resource already consumed')
  if r.owner_kind not in (None,'person') or (r.owner_kind=='person' and r.owner_id!=pid):raise ValueError('person does not possess magical resource')
  self._index_remove(r);r.consumed_year=year;r.consumed_by=pid;r.consumed_event=event_id;return r

def person_context(p,sid):return (p.species,p.occupation,round(p.curiosity,2),round(p.temperament,2),round(p.attachment,2),round(p.inhibition,2),round(p.grief,2),round(p.fear,2),sid)
def _commit_to_full_path(a):
 if a is None or a.completion_goal:return
 a.completion_goal=True;a.desired_base_essences=3;a.desired_abilities=20;a.urgency=max(a.urgency,.55)
def _validate_absorption_owner(resource,pid):
 if resource.consumed_year is not None:raise ValueError('magical resource already consumed')
 if resource.owner_kind!='person' or resource.owner_id!=pid:raise ValueError('person must own resource before absorption')
def absorb_essence_resource(world,pid,rid):
 r=world.magic_resources.resources[rid]
 if r.kind!='essence':raise ValueError('resource is not an essence')
 _validate_absorption_owner(r,pid)
 if r.key not in ESSENCES:raise ValueError('unknown essence')
 p=world.people[pid];path=world.advancement.path(pid);before=world.advancement.rank(pid)
 if path is not None and (r.key in path.base_essences or len(path.base_essences)>=3):return path,[]
 Layer,Ref=layer_ref();e=world.emit('essence_absorbed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,essence=r.key);world.magic_resources.consume(rid,pid,world.year,e.id);path,created=world.advancement.absorb_essence(pid,r.key,world.year,person_context(p,p.settlement),e.id);p.rank=world.advancement.rank(pid)
 a=world.magic_resources.aspirations.get(pid)
 if a is not None and (a.adventurer_aspiration or a.drive>=.34):_commit_to_full_path(a)
 if any(a.source=='confluence' for a in created):
  formation=world.emit('confluence_formed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),base_essences=tuple(path.base_essences),confluence=path.confluence)
  world.emit('confluence_absorbed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(formation.id,),confluence=path.confluence,mechanism='touch',automatic_acceptance=True)
 for ability in created:world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=ability.essence,source=ability.source,ability=ability.semantic_key,name=ability.name,special=ability.special,aura=ability.aura)
 record_body_transition(world,p,before,context="essence_absorption",causes=(e.id,))
 return path,created
def use_awakening_stone(world,pid,rid,target_essence=None):
 r=world.magic_resources.resources[rid]
 if r.kind!='awakening_stone':raise ValueError('resource is not an awakening stone')
 _validate_absorption_owner(r,pid)
 world.advancement._stone(r.key)
 p=world.people[pid];path=world.advancement.path(pid)
 if path is None:return None
 available=[e for e in path.essences if len(path.abilities_for(e))<5]
 if not available or (target_essence is not None and target_essence not in available):return None
 before=world.advancement.rank(pid)
 Layer,Ref=layer_ref();e=world.emit('awakening_stone_used',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,stone=r.key,target_essence=target_essence);a=world.advancement.awaken_skill(pid,r.key,world.year,person_context(p,p.settlement),e.id,target_essence)
 if a is None:return None
 world.magic_resources.consume(rid,pid,world.year,e.id);awakened=world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura)
 record_body_transition(world,p,before,context='awakening_stone',causes=(awakened.id,))
 return a

def _environment_tags(world,sid):
 s=world.settlements[sid];c=world.cells[(s.x,s.y)];q=world.local[sid];tags=[]
 if c.forest>=.55:tags+=['wood','plant','growth','nature','leaf','forest','beast']
 elif c.forest>=.25:tags+=['plant','nature','beast']
 if c.fertility>=.58:tags+=['growth','life','plant','earth']
 if c.elevation>=.58:tags+=['stone','earth','iron','metal','crystal','mountain']
 elif c.elevation<=.25:tags+=['plain','wind']
 if c.moisture>=.62 or q.rain>=.68:tags+=['water','rain','river','storm']
 if q.flood>.04:tags+=['water','flood','river']
 if c.moisture<=.28 or q.drought>.10:tags+=['sun','fire','dust','dry','wind']
 if c.hazard>=.62:tags+=['danger','death','poison','blood','shadow']
 if s.memory.get('monster_surge',0)>.12:tags+=['monster','fear','death']
 if s.prosperity>=.55:tags+=['craft','trade','wealth','knowledge','order']
 return tuple(dict.fromkeys(tags))
@lru_cache(maxsize=512)
def _environment_weights(tags):
 weighted=[]
 for key in ESSENCE_IDS:
  text=(key+' '+str(ESSENCES[key])).lower();hits=sum(1 for tag in tags if tag in text)
  if hits:weighted.append((key,float(hits*hits)))
 return tuple(weighted)

def _environmental_essence(world,rng,sid):
 tags=_environment_tags(world,sid);weighted=_environment_weights(tags)
 if not weighted:return ESSENCE_IDS[int(rng.random()*len(ESSENCE_IDS))%len(ESSENCE_IDS)],tags
 total=sum(w for _,w in weighted);x=rng.random()*total
 for key,w in weighted:
  x-=w
  if x<=0:return key,tags
 return weighted[-1][0],tags

# Remaining resource ecology, market, aspiration, and simulation functions are unchanged below this point.
