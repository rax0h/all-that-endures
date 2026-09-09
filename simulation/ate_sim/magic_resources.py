from __future__ import annotations
from dataclasses import dataclass, field
from .core_types import layer_ref
from .semantic_dictionary import ESSENCE_IDS,ESSENCES,STONE_IDS,AWAKENING_STONES

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
  r=MagicResource(rid,kind,key,rarity,location,owner_kind,owner_id,year,origin_event);self.resources[rid]=r;return r
 def available(self,rid):
  r=self.resources.get(rid);return r is not None and r.consumed_year is None
 def inventory(self,owner_kind,owner_id,kind=None):
  return [r for r in self.resources.values() if r.consumed_year is None and r.owner_kind==owner_kind and r.owner_id==owner_id and (kind is None or r.kind==kind)]
 def transfer(self,rid,owner_kind,owner_id,event_id,location=None):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('consumed magical resource cannot be transferred')
  r.owner_kind=owner_kind;r.owner_id=owner_id
  if location is not None:r.location=location
  r.transfers.append(event_id);return r
 def consume(self,rid,pid,year,event_id):
  r=self.resources[rid]
  if r.consumed_year is not None:raise ValueError('magical resource already consumed')
  if r.owner_kind not in (None,'person') or (r.owner_kind=='person' and r.owner_id!=pid):raise ValueError('person does not possess magical resource')
  r.consumed_year=year;r.consumed_by=pid;r.consumed_event=event_id;return r

def person_context(p,sid):
 return (p.species,p.occupation,round(p.curiosity,2),round(p.temperament,2),round(p.attachment,2),round(p.inhibition,2),round(p.grief,2),round(p.fear,2),sid)

def absorb_essence_resource(world,pid,rid):
 r=world.magic_resources.resources[rid]
 if r.kind!='essence':raise ValueError('resource is not an essence')
 p=world.people[pid];Layer,Ref=layer_ref();e=world.emit('essence_absorbed',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,essence=r.key)
 world.magic_resources.consume(rid,pid,world.year,e.id);path,created=world.advancement.absorb_essence(pid,r.key,world.year,person_context(p,p.settlement),e.id);p.rank=max(1,world.advancement.rank(pid))
 for a in created:world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura)
 return path,created

def use_awakening_stone(world,pid,rid,target_essence=None):
 r=world.magic_resources.resources[rid]
 if r.kind!='awakening_stone':raise ValueError('resource is not an awakening stone')
 p=world.people[pid];Layer,Ref=layer_ref();e=world.emit('awakening_stone_used',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=rid,stone=r.key,target_essence=target_essence)
 world.magic_resources.consume(rid,pid,world.year,e.id);a=world.advancement.awaken_skill(pid,r.key,world.year,person_context(p,p.settlement),e.id,target_essence)
 if a is None:return None
 world.emit('ability_awakened',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(e.id,),essence=a.essence,source=a.source,ability=a.semantic_key,name=a.name,special=a.special,aura=a.aura)
 return a

def _discover(world,rng,sid):
 people=[p for p in world.people.values() if p.alive and p.age>=16 and p.settlement==sid]
 if not people:return None
 finder=people[int(rng.random()*len(people))%len(people)];Layer,Ref=layer_ref();kind='essence' if rng.random()<.58 else 'awakening_stone'
 if kind=='essence':key=ESSENCE_IDS[int(rng.random()*len(ESSENCE_IDS))%len(ESSENCE_IDS)];rarity=ESSENCES[key]['rarity']
 else:key=STONE_IDS[int(rng.random()*len(STONE_IDS))%len(STONE_IDS)];rarity=AWAKENING_STONES[key]['rarity']
 e=world.emit('magic_resource_discovered',Layer.REALITY,(Ref('person',finder.id),),Ref('settlement',sid),resource_kind=kind,key=key,rarity=rarity)
 return world.magic_resources.create(kind,key,rarity,world.year,sid,'person',finder.id,e.id)

def magic_ecology_step(world,rng):
 # Discovery depends on people actually exploring hazardous, inhabited places. It is sparse by design.
 for sid in sorted(world.settlements):
  c=world.cells[(world.settlements[sid].x,world.settlements[sid].y)];rr=rng.stream('magic_discovery',world.year,sid);chance=.004+.012*c.hazard+.004*c.forest
  if rr.random()<chance:_discover(world,rr,sid)
 # Possession precedes use. Partial loadouts remain normal, and people may keep or trade resources instead.
 for p in sorted((x for x in world.people.values() if x.alive and x.age>=16),key=lambda x:x.id):
  rr=rng.stream('magic_use',world.year,p.id);path=world.advancement.path(p.id)
  essences=world.magic_resources.inventory('person',p.id,'essence')
  if essences and (path is None or len(path.base_essences)<3) and rr.random()<.08:
   candidates=[r for r in essences if path is None or r.key not in path.base_essences]
   if candidates:absorb_essence_resource(world,p.id,candidates[int(rr.random()*len(candidates))%len(candidates)].id);path=world.advancement.path(p.id)
  stones=world.magic_resources.inventory('person',p.id,'awakening_stone')
  if path is not None and stones and len(path.abilities)<path.capacity and rr.random()<.11:use_awakening_stone(world,p.id,stones[int(rr.random()*len(stones))%len(stones)].id)
  # Low-frequency peer transfer lets resources circulate without inventing a separate market shortcut.
  held=world.magic_resources.inventory('person',p.id)
  if held and rr.random()<.008:
   peers=[q for q in world.people.values() if q.alive and q.id!=p.id and q.settlement==p.settlement and q.age>=16]
   if peers:
    q=peers[int(rr.random()*len(peers))%len(peers)];r=held[int(rr.random()*len(held))%len(held)];Layer,Ref=layer_ref();e=world.emit('magic_resource_transferred',Layer.SOCIETY,(Ref('person',p.id),Ref('person',q.id)),Ref('settlement',p.settlement),((r.origin_event,) if r.origin_event else ()),resource=r.id,kind=r.kind,key=r.key);world.magic_resources.transfer(r.id,'person',q.id,e.id,p.settlement)
