from __future__ import annotations
from dataclasses import dataclass,field

# Canon-facing names are objective divine actors. Mortal doctrine remains separate.
GOD_DEFINITIONS={
 'knowledge':('Knowledge',('knowledge','truth','learning')),
 'healer':('Healer',('healing','mercy','health')),
 'hero':('Hero',('courage','service','protection')),
 'dominion':('Dominion',('rule','authority','order')),
 'liberty':('Liberty',('freedom','resistance','choice')),
 'justice':('Justice',('law','judgment','fairness')),
 'purity':('Purity',('purity','discipline','cleansing')),
 'fertility':('Fertility',('fertility','family','growth')),
 'merchant':('Merchant',('trade','bargain','prosperity')),
 'ocean':('Ocean',('sea','depth','water')),
 'journey':('Journey',('travel','discovery','passage')),
 'roads':('Roads',('roads','connection','travel')),
 'war':('War',('war','conflict','valor')),
 'storm':('Storm',('storm','weather','power')),
 'truth':('Truth',('truth','revelation','honesty')),
 'hearth':('Hearth',('home','family','hospitality')),
 'refuge':('Refuge',('shelter','safety','protection')),
}

@dataclass
class God:
 id:str
 name:str
 domains:tuple[str,...]
 ontology:str='god'
 transcendent:bool=True
 manifestations:list[int]=field(default_factory=list)
 relationships:dict[int,float]=field(default_factory=dict)

@dataclass
class Church:
 id:int
 god:str
 settlement:int
 founded_year:int
 origin_event:int
 clergy:set[int]=field(default_factory=set)
 followers:set[int]=field(default_factory=set)
 authority:float=.25
 wealth:float=0.
 doctrine_claims:set[int]=field(default_factory=set)

@dataclass
class DivineState:
 gods:dict[str,God]=field(default_factory=dict)
 churches:dict[int,Church]=field(default_factory=dict)
 next_church:int=1

 def seed_pantheon(self):
  if self.gods:return
  for gid,(name,domains) in GOD_DEFINITIONS.items():self.gods[gid]=God(gid,name,domains)

 def churches_for(self,god=None,settlement=None):
  out=list(self.churches.values())
  if god is not None:out=[c for c in out if c.god==god]
  if settlement is not None:out=[c for c in out if c.settlement==settlement]
  return out

 def create_church(self,god,settlement,year,event_id,authority=.25):
  existing=self.churches_for(god,settlement)
  if existing:return existing[0]
  cid=self.next_church;self.next_church+=1;c=Church(cid,god,settlement,year,event_id,authority=authority);self.churches[cid]=c;return c


def seed_gods(world):
 # Gods are part of objective world reality before mortal history; no fake founding event is emitted.
 world.divinity.seed_pantheon()


def _need_score(world,sid,gid):
 q=world.local[sid];s=world.settlements[sid]
 if gid=='healer':return min(1.,q.scarcity*.7+world.cells[(s.x,s.y)].hazard*.35)
 if gid in ('storm','ocean'):return min(1.,q.flood+q.drought*.5)
 if gid in ('merchant','roads','journey'):return min(1.,s.roads*.5+s.prosperity*.5)
 if gid in ('hero','refuge'):return min(1.,world.cells[(s.x,s.y)].hazard*.7+s.memory.get('monster_surge',0.))
 if gid in ('knowledge','truth'):return min(1.,.2+len(world.knowledge.claims)/200)
 if gid in ('fertility','hearth'):return .35
 if gid in ('justice','dominion','liberty'):return min(1.,.15+len(world.culture.laws)/30)
 return .2


def _eligible_clergy(world,sid):return [p for p in world.people.values() if p.alive and p.age>=18 and p.settlement==sid]


def divine_step(world,rng):
 from .core import Layer,Ref
 world.divinity.seed_pantheon()
 for sid in sorted(world.settlements):
  residents=_eligible_clergy(world,sid)
  if not residents:continue
  for gid,god in sorted(world.divinity.gods.items()):
   if world.divinity.churches_for(gid,sid):continue
   need=_need_score(world,sid,gid);rr=rng.stream('church_emergence',world.year,sid*1000+sum(map(ord,gid)))
   if world.year<12 or rr.random()>=.0012*(.25+need):continue
   founder=max(residents,key=lambda p:(p.attachment+p.curiosity-.4*p.inhibition,-p.id))
   e=world.emit('church_founded',Layer.SOCIETY,(Ref('person',founder.id),),Ref('settlement',sid),god=gid,need=round(need,4))
   c=world.divinity.create_church(gid,sid,world.year,e.id,authority=.2+.3*need);c.clergy.add(founder.id);c.followers.add(founder.id);god.relationships[founder.id]=max(god.relationships.get(founder.id,0.),.25)
   world.lineage.register('church',c.id,origin_event=e.id,origin_year=world.year)
  for c in world.divinity.churches_for(settlement=sid):
   god=world.divinity.gods[c.god];rr=rng.stream('church_life',world.year,c.id)
   candidates=[p for p in residents if p.id not in c.followers]
   if candidates and rr.random()<.08:
    p=candidates[int(rr.random()*len(candidates))];c.followers.add(p.id);god.relationships[p.id]=min(1.,god.relationships.get(p.id,0.)+.08)
   for pid in list(c.followers):
    p=world.people.get(pid)
    if p is None or not p.alive:continue
    devotion=god.relationships.get(pid,.1);god.relationships[pid]=min(1.,devotion+.002*(.4+p.attachment))
    path=world.advancement.path(pid)
    if devotion>.55 and rr.random()<.00055:
     from .semantic_dictionary import ESSENCE_IDS,ESSENCES
     available=[x for x in ESSENCE_IDS if path is None or x not in path.base_essences]
     if available:
      key=available[int(rr.random()*len(available))];e=world.emit('divine_essence_granted',Layer.REALITY,(Ref('person',pid),),Ref('settlement',sid),(c.origin_event,),god=c.god,essence=key)
      world.magic_resources.create('essence',key,ESSENCES[key]['rarity'],world.year,sid,'person',pid,e.id)
    pressure=max(world.local[sid].scarcity,world.local[sid].flood,world.settlements[sid].memory.get('monster_surge',0.))
    if pressure>.7 and c.authority>.35 and rr.random()<.00015:
     e=world.emit('god_manifested',Layer.REALITY,(),Ref('settlement',sid),(c.origin_event,),god=c.god,pressure=round(pressure,4));god.manifestations.append(e.id)
