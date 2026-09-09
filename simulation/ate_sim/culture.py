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
 s=world.settlements[sid];c=world.cells[(s.x,s.y)];local=world.local.get(sid);return {"wet":c.moisture,"forest":c.forest,"hazard":c.hazard,"fertility":c.fertility,"scarcity":local.scarcity if local else 0.,"flood":local.flood if local else 0.,"defense_need":max(0.,c.hazard-s.defense)}
def _signature(p):return {"req_wet":p["wet"],"req_forest":p["forest"],"req_hazard":p["hazard"],"req_fertility":p["fertility"]}
def _local_fit(pr,p):
 t=pr.traits
 if pr.domain=="construction":d=.55*abs(p["wet"]-t.get("req_wet",p["wet"]))+.45*abs(p["forest"]-t.get("req_forest",p["forest"]))
 elif pr.domain=="agriculture":d=.55*abs(p["fertility"]-t.get("req_fertility",p["fertility"]))+.45*abs(p["wet"]-t.get("req_wet",p["wet"]))
 elif pr.domain=="defense":d=abs(p["hazard"]-t.get("req_hazard",p["hazard"]))
 else:d=.25*abs(p["wet"]-t.get("req_wet",p["wet"]))
 return max(.08,min(1.,1-d))
def seed_practices(world,state):
 for sid in world.settlements:
  p=pressures(world,sid);sig=_signature(p)
  for domain,name,fit in [("construction","drainage",p["wet"]),("construction","timber_joinery",p["forest"]),("food","preservation",.35+p["scarcity"]*.5),("defense","fortification",p["hazard"]),("agriculture","water_management",p["fertility"]*.6+p["wet"]*.2)]:
   pid=state.next_practice;state.next_practice+=1;traits={"fitness":min(1.,fit),"refinement":.1,**sig};state.practices[pid]=Practice(pid,domain,name,world.year,sid,traits);state.adoption[(sid,pid)]=max(.05,min(.8,fit*.55))
def cultural_step(world,state,rng):
 from .core import Layer,Ref
 institution_support={(inst.settlement,pid):max(.15,inst.legitimacy) for inst in state.institutions.values() for pid in inst.practices}
 for sid in world.settlements:
  p=pressures(world,sid);local_items=[(pid,a) for (place,pid),a in state.adoption.items() if place==sid and a>.01];active_count=len(local_items)
  for pid,adopt in list(local_items):
   pr=state.practices[pid];rr=rng.stream("culture",world.year,sid*100000+pid);pressure={"construction":max(p["wet"],p["forest"]),"food":max(.12,p["scarcity"]),"defense":max(.12,p["defense_need"]),"agriculture":p["fertility"]}.get(pr.domain,.2);support=institution_support.get((sid,pid),0.);fit=_local_fit(pr,p)
   retention=.0015*support+.0008*fit;decay=.0032*max(0.,.38-pressure)*(1-support*.6)+.0022*max(0.,.58-fit)
   if pr.origin_settlement!=sid:decay+=.0009*(1-fit)
   noise=rr.uniform(-.0035,.0035);new=max(0.,min(1.,adopt+.0052*(pressure-.28)*(.35+.65*fit)+retention-decay+noise));state.adoption[(sid,pid)]=new
   if new<=.008:
    del state.adoption[(sid,pid)];world.emit("practice_lost",Layer.KNOWLEDGE,location=Ref("settlement",sid),practice=pid,domain=pr.domain);continue
   pr.traits["refinement"]=min(1.,pr.traits.get("refinement",.1)+.0012*new*(.35+pressure)*fit)
   saturation=max(.10,1/(1+active_count/16));novelty=max(.04,pressure-.15)
   if new>.44 and rr.random()<.00075*(1+novelty)*saturation:
    nid=state.next_practice;state.next_practice+=1;traits=dict(pr.traits);traits["refinement"]=max(0.,min(1.,pr.traits.get("refinement",.1)+rr.uniform(-.06,.09)));state.practices[nid]=Practice(nid,pr.domain,pr.name+" variant",world.year,sid,traits,pid);state.adoption[(sid,nid)]=.055;world.emit("practice_innovated",Layer.SOCIETY,location=Ref("settlement",sid),parent=pid,practice=nid,domain=pr.domain)
  # A community has finite teaching/attention capacity inside each domain. Practices compete rather than all converging to 1.0.
  domains={}
  for (place,pid),a in list(state.adoption.items()):
   if place==sid and a>.008:domains.setdefault(state.practices[pid].domain,[]).append((pid,a))
  for domain,items in domains.items():
   total=sum(a for _,a in items);cap=1.55+sum(institution_support.get((sid,pid),0.)*.12 for pid,_ in items)
   if total>cap:
    scale=cap/total
    for pid,a in items:state.adoption[(sid,pid)]=a*scale
def accommodation(world,sid):
 from .species import accommodation_requirements
 return accommodation_requirements([p.species for p in world.people.values() if p.alive and p.settlement==sid])
