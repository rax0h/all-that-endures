from __future__ import annotations
from dataclasses import dataclass, field
from .core_types import layer_ref
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES

@dataclass
class MagicAspiration:
 drive:float;desired_base_essences:int;desired_abilities:int;reason:str;formed_year:int;preparation:float=0.;search_years:int=0
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
def absorb_essence_resource(world,pid,rid):
 r=world.magic_resources.resources[rid]
 if r.kind!='essence':raise ValueError('resource is not an essence')
 p=world.people[pid];path=world.advancement.path(pid)
 if path is not None and (r.key in path.base_essences or len(path.base_essences)>=3):return path,[]
 Layer,Ref=layer_ref();e=world.emit('essence_absorbed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,essence=r.key);world.magic_resources.consume(rid,pid,world.year,e.id);path,created=world.advancement.absorb_essence(pid,r.key,world.year,person_context(p,p.settlement),e.id);p.rank=max(1,world.advancement.rank(pid))
 for a in created:world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura)
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

def _discover(world,rng,sid,people):
 if not people:return None
 finder=people[int(rng.random()*len(people))%len(people)];Layer,Ref=layer_ref();kind='essence' if rng.random()<.6 else 'awakening_stone'
 if kind=='essence':key=ESSENCE_IDS[int(rng.random()*len(ESSENCE_IDS))%len(ESSENCE_IDS)];rarity=ESSENCES[key]['rarity']
 else:key=STONE_IDS[int(rng.random()*len(STONE_IDS))%len(STONE_IDS)];rarity=AWAKENING_STONES[key]['rarity']
 e=world.emit('magic_resource_discovered',Layer.REALITY,(Ref('person',finder.id),),Ref('settlement',sid),resource_kind=kind,key=key,rarity=rarity);return world.magic_resources.create(kind,key,rarity,world.year,sid,'person',finder.id,e.id)
def _recover_dead_owner_resources(world):
 Layer,Ref=layer_ref()
 for r in sorted(world.magic_resources.resources.values(),key=lambda x:x.id):
  if r.consumed_year is not None or r.owner_kind!='person' or r.owner_id is None:continue
  owner=world.people.get(r.owner_id)
  if owner is None or owner.alive:continue
  household=world.households.get(owner.household);heirs=[] if household is None else [world.people[x] for x in household.members if world.people.get(x) and world.people[x].alive]
  if heirs:
   heir=min(heirs,key=lambda p:p.id);e=world.emit('magic_resource_inherited',Layer.SOCIETY,(Ref('person',heir.id),Ref('person',owner.id)),Ref('settlement',heir.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key);world.magic_resources.transfer(r.id,'person',heir.id,e.id,heir.settlement)
  else:
   e=world.emit('magic_resource_recovered',Layer.REALITY,location=Ref('settlement',r.location) if r.location in world.settlements else None,causes=((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key);world.magic_resources.transfer(r.id,'settlement',r.location,e.id,r.location)
def _aspiration(world,p):
 a=world.magic_resources.aspirations.get(p.id)
 if a:return a
 family=sum(1 for x in p.parents if world.advancement.essence_user(x));contacts=sum(1 for r in world.social.edges.values() if p.id in (r.a,r.b) and world.advancement.essence_user(r.b if r.a==p.id else r.a));m=world.agency.motives.get(p.id);status=0 if m is None else m.status;drive=max(0.,min(1.,.46*p.curiosity+.18*(1-p.inhibition)+.12*status+.10*min(2,family)+.05*min(3,contacts)))
 if drive<.36:desired=0
 elif drive<.54:desired=1
 elif drive<.68:desired=2
 else:desired=3
 reason='curiosity' if p.curiosity>.7 else ('family tradition' if family else ('ambition' if status>.45 else 'capability'))
 a=MagicAspiration(drive,desired,0 if desired==0 else (5 if desired==1 else (10 if desired==2 else 20)),reason,world.year);world.magic_resources.aspirations[p.id]=a;return a
def _wants(world,p,r):
 a=_aspiration(world,p);path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences);abilities=0 if path is None else len(path.abilities)
 if r.kind=='essence':return base<a.desired_base_essences and (path is None or r.key not in path.base_essences)
 return path is not None and abilities<a.desired_abilities and abilities<path.capacity
def _transfer_to_seeker(world,r,holder,local,rng):
 Layer,Ref=layer_ref();candidates=[q for q in local if q.id!=holder.id and _wants(world,q,r)]
 if not candidates:return False
 q=max(candidates,key=lambda p:(_aspiration(world,p).drive,_aspiration(world,p).preparation,p.wealth,-p.id));a=_aspiration(world,q);price=(8 if r.kind=='essence' else 4)*(1+.35*('Rare' in r.rarity or 'Epic' in r.rarity)+.8*('Legendary' in r.rarity));gift=world.social.get(holder.id,q.id).attachment>.7
 if not gift and q.wealth<price:return False
 if not gift:q.wealth-=price;holder.wealth+=price
 e=world.emit('magic_resource_transferred',Layer.SOCIETY,(Ref('person',holder.id),Ref('person',q.id)),Ref('settlement',holder.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,resource_kind=r.kind,key=r.key,reason='relationship gift' if gift else 'aspirant purchase',price=0 if gift else price);world.magic_resources.transfer(r.id,'person',q.id,e.id,holder.settlement);a.preparation=min(1.,a.preparation+.08);return True

def magic_ecology_step(world,rng):
 Layer,Ref=layer_ref();_recover_dead_owner_resources(world);adults_by_settlement={sid:[] for sid in world.settlements}
 for p in world.people.values():
  if p.alive and p.age>=16:adults_by_settlement[p.settlement].append(p)
 for sid in adults_by_settlement:adults_by_settlement[sid].sort(key=lambda p:p.id)
 for sid,people in sorted(adults_by_settlement.items()):
  c=world.cells[(world.settlements[sid].x,world.settlements[sid].y)];rr=rng.stream('magic_discovery',world.year,sid);chance=min(.06,.004+.000025*len(people)+.012*c.hazard+.004*c.forest)
  if rr.random()<chance:_discover(world,rr,sid,people)
  for r in list(world.magic_resources.inventory('settlement',sid)):
   seekers=[p for p in people if _wants(world,p,r)]
   if seekers:
    q=max(seekers,key=lambda p:(_aspiration(world,p).drive,_aspiration(world,p).preparation,p.wealth,-p.id));price=(7 if r.kind=='essence' else 3)
    if q.wealth>=price:
     q.wealth-=price;e=world.emit('magic_resource_purchased',Layer.SOCIETY,(Ref('person',q.id),),Ref('settlement',sid),((r.origin_event,) if r.origin_event else ()),resource=r.id,key=r.key,price=price);world.magic_resources.transfer(r.id,'person',q.id,e.id,sid)
 adults=[p for sid in sorted(adults_by_settlement) for p in adults_by_settlement[sid]]
 for p in adults:
  rr=rng.stream('magic_use',world.year,p.id);a=_aspiration(world,p);path=world.advancement.path(p.id);base=0 if path is None else len(path.base_essences)
  if a.desired_base_essences>base:
   a.search_years+=1;a.preparation=min(1.,a.preparation+.002*(.5+a.drive));
   if rr.random()<.012*a.drive:world.emit('magic_resource_sought',Layer.SOCIETY,(Ref('person',p.id),),Ref('settlement',p.settlement),reason=a.reason,drive=round(a.drive,3),preparation=round(a.preparation,3))
  essences=world.magic_resources.inventory('person',p.id,'essence')
  if essences and base<a.desired_base_essences and rr.random()<.12+.35*a.drive:
   candidates=[r for r in essences if path is None or r.key not in path.base_essences]
   if candidates:absorb_essence_resource(world,p.id,candidates[int(rr.random()*len(candidates))%len(candidates)].id);path=world.advancement.path(p.id)
  stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
  if path is not None and stones and len(path.abilities)<min(a.desired_abilities,path.capacity) and rr.random()<.12+.35*a.drive:use_awakening_stone(world,p.id,stones[int(rr.random()*len(stones))%len(stones)].id)
  held=world.magic_resources.inventory('person',p.id)
  if held and rr.random()<.035:
   surplus=[r for r in held if not _wants(world,p,r)]
   if surplus:_transfer_to_seeker(world,surplus[int(rr.random()*len(surplus))%len(surplus)],p,adults_by_settlement[p.settlement],rr)
