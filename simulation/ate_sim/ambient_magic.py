from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref

@dataclass
class AmbientField:
 level:float=.12;peak:float=.12;critical_years:int=0;quintessence:float=0.;surges:int=0
@dataclass
class AmbientMagicState:
 fields:dict[int,AmbientField]=field(default_factory=dict)
 def field(self,sid):return self.fields.setdefault(sid,AmbientField())

def ambient_magic_step(world,rng):
 Layer,Ref=layer_ref()
 for sid,s in sorted(world.settlements.items()):
  f=world.ambient_magic.field(sid);local=world.local[sid];rr=rng.stream('ambient_magic',world.year,sid)
  users=sum(1 for p in world.living_by_settlement()[sid] if world.advancement.essence_user(p.id))
  pressure=.0025+.004*world.cells[(s.x,s.y)].hazard+.002*local.flood+.00012*users
  dissipation=.0035+.002*max(0.,.5-local.scarcity)
  f.level=max(0.,min(1.5,f.level+pressure-dissipation+rr.uniform(-.006,.006)))
  f.peak=max(f.peak,f.level)
  if f.level>=.72:
   f.critical_years+=1
   if rr.random()<min(.18,.015+.08*(f.level-.72)):
    amount=round(.1+.7*(f.level-.72)+rr.random()*.15,3);f.quintessence+=amount;f.surges+=1
    world.emit('quintessence_condensed',Layer.REALITY,location=Ref('settlement',sid),amount=amount,ambient=round(f.level,3))
  else:f.critical_years=max(0,f.critical_years-1)
