from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Practice:
    id:int; domain:str; name:str; origin_year:int; origin_settlement:int
    traits:dict[str,float]=field(default_factory=dict); parent:int|None=None

@dataclass
class Institution:
    id:int; settlement:int; kind:str; founded:int; practices:set[int]=field(default_factory=set)
    authority:float=.2; assets:float=0.; legitimacy:float=.5

@dataclass
class Law:
    id:int; settlement:int; domain:str; strictness:float; enforcement:float; origin_event:int|None=None

@dataclass
class CulturalState:
    practices:dict[int,Practice]=field(default_factory=dict); institutions:dict[int,Institution]=field(default_factory=dict)
    laws:dict[int,Law]=field(default_factory=dict); adoption:dict[tuple[int,int],float]=field(default_factory=dict)
    next_practice:int=1; next_institution:int=1; next_law:int=1

def pressures(world,sid:int)->dict[str,float]:
    s=world.settlements[sid]; c=world.cells[(s.x,s.y)]
    return {"wet":c.moisture,"forest":c.forest,"hazard":c.hazard,"fertility":c.fertility,
            "scarcity":getattr(s,"_scarcity",0.),"flood":getattr(s,"_flood",0.),"defense_need":max(0.,c.hazard-s.defense)}

def seed_practices(world,state:CulturalState):
    for sid in world.settlements:
        p=pressures(world,sid)
        specs=[("construction","drainage",p["wet"]), ("construction","timber_joinery",p["forest"]),
               ("food","preservation",.35+p["scarcity"]*.5), ("defense","fortification",p["hazard"]),
               ("agriculture","water_management",p["fertility"]*.6+p["wet"]*.2)]
        for domain,name,fit in specs:
            pid=state.next_practice; state.next_practice+=1
            state.practices[pid]=Practice(pid,domain,name,world.year,sid,{"fitness":min(1.,fit),"refinement":.1})
            state.adoption[(sid,pid)]=max(.05,min(.8,fit*.55))

def cultural_step(world,state:CulturalState,rng):
    for sid in world.settlements:
        p=pressures(world,sid)
        for (place,pid),adopt in list(state.adoption.items()):
            if place!=sid: continue
            practice=state.practices[pid]; rr=rng.stream("culture",world.year,sid*100000+pid)
            pressure={"construction":max(p["wet"],p["forest"]),"food":p["scarcity"],"defense":p["defense_need"],"agriculture":p["fertility"]}.get(practice.domain,.2)
            practice.traits["refinement"]=min(1.,practice.traits.get("refinement",.1)+.002*adopt*(.5+pressure))
            state.adoption[(sid,pid)]=max(0.,min(1.,adopt+.01*(pressure-.25)+rr.uniform(-.008,.008)))
            if adopt>.35 and rr.random()<.0015*(1+pressure):
                nid=state.next_practice; state.next_practice+=1
                state.practices[nid]=Practice(nid,practice.domain,practice.name+" variant",world.year,sid,dict(practice.traits),pid)
                state.practices[nid].traits["refinement"]=min(1.,practice.traits.get("refinement",.1)+rr.uniform(-.05,.12))
                state.adoption[(sid,nid)]=.08
                world.emit("practice_innovated",world.events[0].layer if world.events else None,location=None,parent=pid,practice=nid,domain=practice.domain)

def accommodation(world,sid:int)->dict[str,float]:
    from .species import accommodation_requirements
    residents=[p for p in world.people.values() if p.alive and p.settlement==sid]
    return accommodation_requirements([p.species for p in residents])
