from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from .rank import profile,biological_age

@dataclass(slots=True)
class HealthCondition:
 id:int;person:int;kind:str;started_year:int;severity:float;origin_event:int;last_year:int
@dataclass
class HealthState:
 active:dict[int,HealthCondition]=field(default_factory=dict)
 next_condition:int=1
 def start(self,person,kind,year,severity,event_id):
  condition=HealthCondition(self.next_condition,person,kind,year,severity,event_id,year)
  self.next_condition+=1;self.active[person]=condition;return condition
 def clear(self,person):return self.active.pop(person,None)


def _illness_kind(world,sid,rr):
 q=world.local[sid];s=world.settlements[sid];c=world.cells[(s.x,s.y)]
 if q.flood>.05 or q.rain>.82:return 'waterborne illness'
 if q.scarcity>.22:return 'scarcity fever'
 if c.hazard>.68:return 'environmental illness'
 return ('respiratory illness','seasonal fever','gastrointestinal illness')[int(rr.random()*3)%3]


def health_step(world,rng):
 """Ordinary disease/recovery using embodied and environmental state."""
 Layer,Ref=layer_ref();living=world.living_by_settlement();alive_ids=world.runtime_view().alive_ids
 # Clear conditions whose person no longer has a living body.
 for pid in tuple(world.health.active):
  if pid not in alive_ids:world.health.active.pop(pid,None)

 for sid,people in sorted(living.items()):
  if not people:continue
  q=world.local[sid];s=world.settlements[sid];cell=world.cells[(s.x,s.y)]
  crowd=min(2.,len(people)/max(30.,90.+150.*cell.fertility))
  environment=.0010+.0045*q.scarcity+.0025*q.flood+.0012*q.drought+.0010*crowd+.0008*cell.hazard
  for p in people:
   rp=profile(p.rank);condition=world.health.active.get(p.id)
   if condition is None:
    # Healthy bodies recover toward baseline even without an explicit illness.
    p.health=min(1.,p.health+.025*rp.healing)
    age_pressure=max(0.,biological_age(p.age,p.rank)-55.)/120.
    chance=environment*(1+.8*age_pressure)/max(1.,rp.disease_resistance)
    rr=rng.stream('ordinary_disease',world.year,p.id)
    if rr.random()<chance:
     severity=min(.85,.10+.28*rr.random()+.22*q.scarcity+.15*q.flood)
     kind=_illness_kind(world,sid,rr)
     e=world.emit('illness_started',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),
         illness=kind,severity=round(severity,4),scarcity=round(q.scarcity,4),
         flood=round(q.flood,4),drought=round(q.drought,4))
     condition=world.health.start(p.id,kind,world.year,severity,e.id)
   if condition is None:continue

   rr=rng.stream('ordinary_recovery',world.year,p.id)
   age_pressure=max(0.,biological_age(p.age,p.rank)-60.)/100.
   burden=condition.severity*(1+.35*q.scarcity+.20*age_pressure)
   p.health=max(.05,p.health-.12*burden/max(1.,rp.disease_resistance))
   recovery=min(.92,.18+.18*rp.healing+.20*p.health-.12*q.scarcity)
   condition.last_year=world.year
   if rr.random()<recovery:
    e=world.emit('illness_recovered',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',sid),
        (condition.origin_event,),illness=condition.kind,duration=world.year-condition.started_year+1,
        ending_severity=round(condition.severity,4))
    world.health.clear(p.id);p.health=min(1.,p.health+.08*rp.healing)
   else:
    condition.severity=max(.03,min(.95,condition.severity*(.92+.12*rr.random())+.04*q.scarcity))
