from __future__ import annotations
from dataclasses import dataclass,field
@dataclass
class Practice: id:int; domain:str; name:str; origin_year:int; origin_settlement:int; traits:dict[str,float]=field(default_factory=dict); parent:int|None=None
@dataclass
class Institution: id:int; settlement:int; kind:str; founded:int; practices:set[int]=field(default_factory=set); authority:float=.2; assets:float=0.; legitimacy:float=.5
@dataclass
class Law: id:int; settlement:int; domain:str; strictness:float; enforcement:float; origin_event:int|None=None
@dataclass
class CulturalState:
 practices:dict[int,Practice]=field(default_factory=dict); institutions:dict[int,Institution]=field(default_factory=dict); laws:dict[int,Law]=field(default_factory=dict); adoption:dict[tuple[int,int],float]=field(default_factory=dict); next_practice:int=1; next_institution:int=1; next_law:int=1
def pressures(world,sid):
 s=world.settlements[sid]; c=world.cells[(s.x,s.y)]; local=world.local.get(sid); return {"wet":c.moisture,"forest":c.forest,"hazard":c.hazard,"fertility":c.fertility,"scarcity":local.scarcity if local else 0.,"flood":local.flood if local else 0.,"defense_need":max(0.,c.hazard-s.defense)}
def seed_practices(world,state):
 for sid in world.settlements:
  p=pressures(world,sid)
  for domain,name,fit in [("construction","drainage",p["wet"]),("construction","timber_joinery",p["forest"]),("food","preservation",.35+p["scarcity"]*.5),("defense","fortification",p["hazard"]),("agriculture","water_management",p["fertility"]*.6+p["wet"]*.2)]:
   pid=state.next_practice; state.next_practice+=1; state.practices[pid]=Practice(pid,domain,name,world.year,sid,{"fitness":min(1.,fit),"refinement":.1}); state.adoption[(sid,pid)]=max(.05,min(.8,fit*.55))
def cultural_step(world,state,rng):
 from .core import Layer,Ref
 for sid in world.settlements:
  p=pressures(world,sid)
  for (place,pid),adopt in list(state.adoption.items()):
   if place!=sid:continue
   pr=state.practices[pid]; rr=rng.stream("culture",world.year,sid*100000+pid); pressure={"construction":max(p["wet"],p["forest"]),"food":p["scarcity"],"defense":p["defense_need"],"agriculture":p["fertility"]}.get(pr.domain,.2); pr.traits["refinement"]=min(1.,pr.traits.get("refinement",.1)+.002*adopt*(.5+pressure)); state.adoption[(sid,pid)]=max(0.,min(1.,adopt+.01*(pressure-.25)+rr.uniform(-.008,.008)))
   if adopt>.35 and rr.random()<.0015*(1+pressure):
    nid=state.next_practice; state.next_practice+=1; state.practices[nid]=Practice(nid,pr.domain,pr.name+" variant",world.year,sid,dict(pr.traits),pid); state.practices[nid].traits["refinement"]=min(1.,pr.traits.get("refinement",.1)+rr.uniform(-.05,.12)); state.adoption[(sid,nid)]=.08; world.emit("practice_innovated",Layer.SOCIETY,location=Ref("settlement",sid),parent=pid,practice=nid,domain=pr.domain)
def accommodation(world,sid):
 from .species import accommodation_requirements
 return accommodation_requirements([p.species for p in world.people.values() if p.alive and p.settlement==sid])
