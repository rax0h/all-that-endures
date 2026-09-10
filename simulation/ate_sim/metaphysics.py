from __future__ import annotations
from dataclasses import dataclass,field

TRANSCENDENT_KINDS=('god','astral_king','great_astral_being')

@dataclass
class SoulState:
 person:int
 origin_world:str='local'
 outworlder:bool=False
 body_generation:int=1
 death_count:int=0
 resurrection_count:int=0
 ontology:str='mortal'
 authorities:set[str]=field(default_factory=set)
 marks:set[str]=field(default_factory=set)
 cosmic_links:dict[str,float]=field(default_factory=dict)
 transformations:list[int]=field(default_factory=list)

@dataclass
class ResurrectionToken:
 id:int
 person:int
 patron_kind:str
 patron_id:str
 granted_year:int
 grant_event:int
 consumed_year:int|None=None
 consumed_event:int|None=None

@dataclass
class MetaphysicalState:
 souls:dict[int,SoulState]=field(default_factory=dict)
 resurrection_tokens:dict[int,ResurrectionToken]=field(default_factory=dict)
 next_token:int=1

 def soul(self,pid,origin_world='local',outworlder=False):
  if pid not in self.souls:self.souls[pid]=SoulState(pid,origin_world,outworlder)
  return self.souls[pid]

 def mark(self,pid,mark,link=None,strength=0.):
  s=self.soul(pid);s.marks.add(mark)
  if link is not None:s.cosmic_links[link]=max(s.cosmic_links.get(link,0.),max(0.,min(1.,strength)))
  return s

 def grant_resurrection_token(self,person,patron_kind,patron_id,year,event_id):
  tid=self.next_token;self.next_token+=1
  t=ResurrectionToken(tid,person,patron_kind,str(patron_id),year,event_id);self.resurrection_tokens[tid]=t;return t

 def available_token(self,pid):
  return next((t for t in sorted(self.resurrection_tokens.values(),key=lambda x:x.id) if t.person==pid and t.consumed_year is None),None)

 def record_death(self,pid):
  s=self.soul(pid);s.death_count+=1;return s

 def consume_resurrection(self,pid,year,event_id):
  t=self.available_token(pid)
  if t is None:return None
  t.consumed_year=year;t.consumed_event=event_id;s=self.soul(pid);s.resurrection_count+=1;s.body_generation+=1;s.marks.add('resurrected');return t

 def transcendence_candidates(self,pid):
  s=self.soul(pid);out=[]
  # Transcendence is an ontological transformation, not a post-Diamond XP rank.
  # Multiple causal routes can satisfy these broad gates; no random ascension roll exists.
  if 'divine_domain_bound' in s.marks and any(k.startswith('divine:') for k in s.authorities):out.append('god')
  if 'astral_throne_claimed' in s.marks and any(k.startswith('astral:') for k in s.authorities):out.append('astral_king')
  if 'cosmic_role_embodied' in s.marks and any(k.startswith('cosmic:') for k in s.authorities):out.append('great_astral_being')
  return tuple(out)

 def transform(self,pid,kind,event_id,authorities=()):
  if kind not in TRANSCENDENT_KINDS:raise ValueError('unknown transcendent ontology')
  s=self.soul(pid)
  if kind not in self.transcendence_candidates(pid):raise ValueError(f'causal prerequisites for {kind} are not satisfied')
  s.ontology=kind;s.authorities.update(authorities);s.transformations.append(event_id);s.marks.add('transcendent');return s


def register_outworlder(world,pid,origin_world,arrival_causes=()):
 from .core import Layer,Ref
 p=world.people[pid];s=world.metaphysics.soul(pid,origin_world,True)
 s.origin_world=origin_world;s.outworlder=True;s.marks.add('cross_world_arrival')
 e=world.emit('outworlder_arrived',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),arrival_causes,origin_world=origin_world)
 s.transformations.append(e.id);return e


def grant_resurrection_token(world,pid,patron_kind,patron_id,causes=()):
 from .core import Layer,Ref
 p=world.people[pid];e=world.emit('resurrection_token_granted',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),causes,patron_kind=patron_kind,patron_id=str(patron_id))
 return world.metaphysics.grant_resurrection_token(pid,patron_kind,patron_id,world.year,e.id)


def try_resurrection(world,pid,death_event):
 from .core import Layer,Ref
 token=world.metaphysics.available_token(pid)
 if token is None:return None
 p=world.people[pid]
 e=world.emit('resurrection',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),(death_event.id,token.grant_event),token=token.id,patron_kind=token.patron_kind,patron_id=token.patron_id)
 world.metaphysics.consume_resurrection(pid,world.year,e.id);p.alive=True;p.health=max(.5,p.health);return e


def attempt_transcendence(world,pid,kind,authorities=(),causes=()):
 from .core import Layer,Ref
 p=world.people[pid]
 if kind not in world.metaphysics.transcendence_candidates(pid):return None
 e=world.emit('ontological_transcendence',Layer.REALITY,(Ref('person',pid),),Ref('settlement',p.settlement),causes,kind=kind,authorities=tuple(authorities))
 return world.metaphysics.transform(pid,kind,e.id,authorities)
