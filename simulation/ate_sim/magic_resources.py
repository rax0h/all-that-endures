from __future__ import annotations
from dataclasses import dataclass, field
from .core_types import layer_ref
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES

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
def absorb_essence_resource(world,pid,rid):
 r=world.magic_resources.resources[rid]
 if r.kind!='essence':raise ValueError('resource is not an essence')
 p=world.people[pid];path=world.advancement.path(pid)
 if path is not None and (r.key in path.base_essences or len(path.base_essences)>=3):return path,[]
 Layer,Ref=layer_ref();e=world.emit('essence_absorbed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,essence=r.key);world.magic_resources.consume(rid,pid,world.year,e.id);path,created=world.advancement.absorb_essence(pid,r.key,world.year,person_context(p,p.settlement),e.id);p.rank=max(1,world.advancement.rank(pid))
 a=world.magic_resources.aspirations.get(pid)
 if a is not None and (a.adventurer_aspiration or a.drive>=.34):_commit_to_full_path(a)
 for ability in created:world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=ability.essence,source=ability.source,ability=ability.semantic_key,name=ability.name,special=ability.special,aura=ability.aura)
 return path,created
def use_awakening_stone(world,pid,rid,target_essence=None):
 r=world.magic_resources.resources[rid]
 if r.kind!='awakening_stone':raise ValueError('resource is not an awakening stone')
 p=world.people[pid];path=world.advancement.path(pid)
 if path is None:return None
 available=[e for e in path.essences if len(path.abilities_for(e))<5]
 if not available or (target_essence is not None and target_essence not in available):return None
 Layer,Ref=layer_ref();e=world.emit('awakening_stone_used',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,stone=r.key,target_essence=target_essence);a=world.advancement.awaken_skill(pid,r.key,world.year,person_context(p,p.settlement),e.id,target_essence)
 if a is None:return None
 world.magic_resources.consume(rid,pid,world.year,e.id);world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura);return a

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
def _environmental_essence(world,rng,sid):
 tags=_environment_tags(world,sid);weighted=[]
 for key in ESSENCE_IDS:
  text=(key+' '+str(ESSENCES[key])).lower();hits=sum(1 for tag in tags if tag in text)
  if hits:weighted.append((key,float(hits*hits)))
 if not weighted:
  return ESSENCE_IDS[int(rng.random()*len(ESSENCE_IDS))%len(ESSENCE_IDS)],tags
 total=sum(w for _,w in weighted);x=rng.random()*total
 for key,w in weighted:
  x-=w
  if x<=0:return key,tags
 return weighted[-1][0],tags

def _make_resource(world,rng,sid,finder,kind=None,cause=None,method='chance discovery'):
 Layer,Ref=layer_ref();kind=kind or ('essence' if rng.random()<.6 else 'awakening_stone');tags=()
 if kind=='essence':key,tags=_environmental_essence(world,rng,sid);rarity=ESSENCES[key]['rarity']
 else:key=STONE_IDS[int(rng.random()*len(STONE_IDS))%len(STONE_IDS)];rarity=AWAKENING_STONES[key]['rarity']
 causes=() if cause is None else (cause,);e=world.emit('magic_resource_discovered',Layer.REALITY,(Ref('person',finder.id),),Ref('settlement',sid),causes,resource_kind=kind,key=key,rarity=rarity,method=method,environment_tags=tags,manifestation_basis='local magical ecology' if kind=='essence' else 'awakening resonance');return world.magic_resources.create(kind,key,rarity,world.year,sid,'person',finder.id,e.id)
def _discover(world,rng,sid,people):
 if not people:return None
 finder=people[int(rng.random()*len(people))%len(people)];return _make_resource(world,rng,sid,finder)
def _recover_dead_owner_resources(world):
 Layer,Ref=layer_ref();owners=[key for key in world.magic_resources.owner_index if key[0]=='person']
 for _,pid in sorted(owners,key=lambda x:x[1]):
  owner=world.people.get(pid)
  if owner is not None and owner.alive:continue
  for rid in sorted(tuple(world.magic_resources.owner_index.get(('person',pid),()))):
   r=world.magic_resources.resources[rid]
   if r.consumed_year is not None:continue
   household=None if owner is None else world.households.get(owner.household);heirs=[] if household is None else [world.people[x] for x in household.members if world.people.get(x) and world.people[x].alive]
   if heirs:
    heir=min(heirs,key=lambda p:p.id);e=world.emit('magic_resource_inherited',Layer.SOCIETY,(Ref('person',heir.id),Ref('person',pid)),Ref('settlement',heir.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key);world.magic_resources.transfer(r.id,'person',heir.id,e.id,heir.settlement)
   else:
    e=world.emit('magic_resource_recovered',Layer.REALITY,location=Ref('settlement',r.location) if r.location in world.settlements else None,causes=((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key);world.magic_resources.transfer(r.id,'settlement',r.location,e.id,r.location)
def _aspiration(world,p):
 a=world.magic_resources.aspirations.get(p.id)
 if a:return a
 family=sum(1 for x in p.parents if world.advancement.essence_user(x));contacts=sum(1 for x in world.social.neighbors(p.id) if world.advancement.essence_user(x));m=world.agency.motives.get(p.id);status=0 if m is None else m.status
 drive=max(0.,min(1.,.46*p.curiosity+.18*(1-p.inhibition)+.12*status+.10*min(2,family)+.05*min(3,contacts)))
 adventurer=(p.occupation in ('adventurer','guard','hunter','soldier')) or (drive>.68 and (p.curiosity>.58 or status>.42))
 interested=drive>=.34 or family>0 or contacts>=2
 serious=interested and (adventurer or drive>=.40 or family>0 or contacts>=2)
 completion=serious
 if not interested:desired=0
 elif completion:desired=3
 else:desired=1
 urgency=max(0.,min(1.,.18+.55*drive+(.22 if adventurer else 0.)+.08*min(2,family))) if interested else 0.
 compromise=max(.05,min(.95,.70-.38*p.inhibition+.18*drive+(.12 if adventurer else 0.)))
 selectivity=max(.05,min(.95,.66+.22*p.inhibition-.25*urgency))
 risk=max(.05,min(.95,.25+.42*drive+.20*(1-p.inhibition)+(.15 if adventurer else 0.)))
 reason='adventure' if adventurer else ('family tradition' if family else ('curiosity' if p.curiosity>.7 else ('ambition' if status>.45 else 'capability')))
 a=MagicAspiration(drive,desired,0 if desired==0 else (20 if completion else 5),reason,world.year,completion_goal=completion,urgency=urgency,compromise_tolerance=compromise,stone_selectiveness=selectivity,risk_tolerance=risk,adventurer_aspiration=adventurer);world.magic_resources.aspirations[p.id]=a;return a
def _wants(world,p,r):
 a=_aspiration(world,p);path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences);abilities=0 if path is None else len(path.abilities)
 if r.kind=='essence':return base<a.desired_base_essences and (path is None or r.key not in path.base_essences)
 return path is not None and abilities<a.desired_abilities and abilities<path.capacity
def _demand_key(resource):
 # Stone identity/rarity does not enter _wants; essence identity does.
 return (resource.kind, resource.key if resource.kind=='essence' else None)

def _market_contenders(world,people,resource):
 # During the settlement market only wealth changes. Preserve all ties in the
 # fixed urgency/drive/preparation prefix; wealth and ID are compared at purchase.
 contenders=[];best=None
 for person in people:
  if not _wants(world,person,resource):continue
  a=_aspiration(world,person);priority=(a.urgency,a.drive,a.preparation)
  if best is None or priority>best:best=priority;contenders=[person]
  elif priority==best:contenders.append(person)
 return contenders

def _wanted_resources(world,person,resources,wanted=True):
 # This query has no intervening advancement or aspiration mutation.
 decisions={};result=[]
 for resource in resources:
  key=_demand_key(resource)
  if key not in decisions:decisions[key]=_wants(world,person,resource)
  if decisions[key]==wanted:result.append(resource)
 return result

def _transfer_to_seeker(world,r,holder,local,rng):
 Layer,Ref=layer_ref();candidates=[q for q in local if q.id!=holder.id and _wants(world,q,r)]
 if not candidates:return False
 q=max(candidates,key=lambda p:(_aspiration(world,p).urgency,_aspiration(world,p).drive,_aspiration(world,p).preparation,p.wealth,-p.id));a=_aspiration(world,q);price=(8 if r.kind=='essence' else 4)*(1+.35*('Rare' in r.rarity or 'Epic' in r.rarity)+.8*('Legendary' in r.rarity));gift=world.social.get(holder.id,q.id).attachment>.7
 if not gift and q.wealth<price:return False
 if not gift:q.wealth-=price;holder.wealth+=price
 e=world.emit('magic_resource_transferred',Layer.SOCIETY,(Ref('person',holder.id),Ref('person',q.id)),Ref('settlement',holder.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key,reason='relationship gift' if gift else 'aspirant purchase',price=0 if gift else price);world.magic_resources.transfer(r.id,'person',q.id,e.id,holder.settlement);a.preparation=min(1.,a.preparation+.08);return True

def magic_ecology_step(world,rng):
 Layer,Ref=layer_ref();_recover_dead_owner_resources(world);adults_by_settlement={sid:[] for sid in world.settlements}
 for p in world.people.values():
  if p.alive and p.age>=16:adults_by_settlement[p.settlement].append(p)
 for sid in adults_by_settlement:adults_by_settlement[sid].sort(key=lambda p:p.id)
 for sid,people in sorted(adults_by_settlement.items()):
  c=world.cells[(world.settlements[sid].x,world.settlements[sid].y)];rr=rng.stream('magic_discovery',world.year,sid);ambient=world.ambient_magic.field(sid).level
  chance=min(.16,.010+.00004*len(people)+.025*c.hazard+.008*c.forest+.04*max(0.,ambient-.5))
  if rr.random()<chance:_discover(world,rr,sid,people)
  market={}
  for r in world.magic_resources.inventory('settlement',sid):
   key=_demand_key(r)
   if key not in market:market[key]=_market_contenders(world,people,r)
   seekers=market[key]
   if seekers:
    q=max(seekers,key=lambda p:(p.wealth,-p.id));price=(7 if r.kind=='essence' else 3)
    if q.wealth>=price:
     q.wealth-=price;e=world.emit('magic_resource_purchased',Layer.SOCIETY,(Ref('person',q.id),),Ref('settlement',sid),((r.origin_event,) if r.origin_event else ()),resource=r.id,key=r.key,price=price);world.magic_resources.transfer(r.id,'person',q.id,e.id,sid)
 adults=[p for sid in sorted(adults_by_settlement) for p in adults_by_settlement[sid]]
 for p in adults:
  rr=rng.stream('magic_use',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
  if path is not None and not a.completion_goal and (a.adventurer_aspiration or a.drive>=.34):_commit_to_full_path(a)
  if a.desired_base_essences>base:
   a.search_years+=1;a.preparation=min(1.,a.preparation+.0025*(.5+a.drive+.5*a.urgency));sought=None
   if rr.random()<.015*(.4+a.drive+.4*a.urgency):sought=world.emit('magic_resource_sought',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),reason=a.reason,drive=round(a.drive,3),urgency=round(a.urgency,3),preparation=round(a.preparation,3),search_years=a.search_years,completion_goal=a.completion_goal)
   search_chance=min(.012,.00035+.0018*a.drive+.0020*a.preparation+.0018*a.urgency+.00008*min(30,a.search_years))
   if rr.random()<search_chance:_make_resource(world,rr,p.settlement,p,'essence',None if sought is None else sought.id,'aspirant search')
  essences=world.magic_resources.inventory('person',p.id,'essence')
  if essences and base<a.desired_base_essences and rr.random()<.15+.34*a.drive+.18*a.urgency:
   candidates=[r for r in essences if path is None or r.key not in path.base_essences]
   if candidates:
    take=a.compromise_tolerance if base>0 else max(.35,a.compromise_tolerance)
    if rr.random()<take:absorb_essence_resource(world,p.id,candidates[int(rr.random()*len(candidates))%len(candidates)].id);path=world.advancement.path(p.id);base=len(path.base_essences)
  stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
  if path is not None and stones and len(path.abilities)<min(a.desired_abilities,path.capacity) and rr.random()<.15+.34*a.drive+.18*a.urgency:
   if rr.random()<max(.12,1-a.stone_selectiveness):use_awakening_stone(world,p.id,stones[int(rr.random()*len(stones))%len(stones)].id)
  held=world.magic_resources.inventory('person',p.id)
  if held:
   surplus=_wanted_resources(world,p,held,wanted=False)
   if surplus and rr.random()<.20:
    local=adults_by_settlement[p.settlement];pressure=0.
    demand_types={}
    for r in surplus:demand_types.setdefault(_demand_key(r),r)
    for r in demand_types.values():
     seekers=[q for q in local if q.id!=p.id and _wants(world,q,r)]
     if seekers:pressure=max(pressure,max((_aspiration(world,q).drive+.5*_aspiration(world,q).urgency)*(.35+.65*_aspiration(world,q).preparation) for q in seekers))
    conditional=(.04+.16*min(1.,pressure))/.20
    if rr.random()<conditional:_transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],p,local,rr)
