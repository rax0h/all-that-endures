from .core import *
from .biology import state as biology_state,mortality_risk,reproductive_window,pair_reproductive_opportunity,child_species,combat_value,injury_resilience
from .culture import cultural_step
from .households import household_step
from .civilization import civilization_step
from .development import development_step
from .agency import agency_step
from .institutions import institution_step
from .magic_resources import magic_ecology_step
from .materials import material_economy_step
from .ambient_magic import ambient_magic_step
from .divinity import divine_step
from .metaphysics import try_resurrection
class Simulation:
 def __init__(self,world): self.w=world; self.rng=RNG(world.seed)
 def run(self,years):
  for _ in range(years):self.step()
  return self.w
 def step(self):
  self.w.year+=1; self._weather(); self._production(); self._people(); household_step(self.w,self.rng); self._demography(); self._pressure(); ambient_magic_step(self.w,self.rng); divine_step(self.w,self.rng); magic_ecology_step(self.w,self.rng); agency_step(self.w,self.rng); material_economy_step(self.w,self.rng); cultural_step(self.w,self.w.culture,self.rng); civilization_step(self.w,self.rng); development_step(self.w,self.rng); institution_step(self.w,self.rng); self._memory()
 def _weather(self):
  for sid,s in self.w.settlements.items():
   c=self.w.cells[(s.x,s.y)];r=self.rng.stream("weather",self.w.year,sid);q=self.w.local[sid];q.rain=max(0,min(1,c.moisture+r.uniform(-.38,.38)));q.drought=max(0,.35-q.rain);q.flood=max(0,q.rain-.82)
   if q.drought>.12:self.w.emit("drought",Layer.REALITY,location=Ref("settlement",sid),severity=q.drought)
   if q.flood>.05:self.w.emit("flood",Layer.REALITY,location=Ref("settlement",sid),severity=q.flood)
 def _production(self):
  by_settlement={sid:[] for sid in self.w.settlements}
  for p in self.w.people.values():
   if p.alive:by_settlement[p.settlement].append(p)
  for sid,s in self.w.settlements.items():
   people=by_settlement[sid];c=self.w.cells[(s.x,s.y)];q=self.w.local[sid];bios=[biology_state(p) for p in people];labor=sum(b.endurance*p.health for b,p in zip(bios,people));food=sum(b.food_need for b in bios);adults=[p for p in people if p.age>=18];agri=sum(self.w.skills.get(p.id,"agriculture").level for p in adults)/max(1,len(adults));crop=(12+2*labor)*c.fertility*(.45+.75*q.rain)*(1+.5*s.irrigation)*(1+.22*agri);s.food_stock+=crop-food
   if q.flood:s.food_stock-=20*q.flood;s.roads=max(0,s.roads-.08*q.flood)
   q.scarcity=max(0,min(1,(food*10-s.food_stock)/max(1,food*10)))
   if q.scarcity>.25:self.w.emit("food_scarcity",Layer.SOCIETY,location=Ref("settlement",sid),severity=q.scarcity)
 def _people(self):
  for pid,p in list(self.w.people.items()):
   if not p.alive:continue
   p.age=self.w.year-p.born; b=biology_state(p); p.health=max(0,min(1,p.health+b.recovery*(1-p.health)))
   q=self.w.local[p.settlement];r=self.rng.stream("person",self.w.year,pid);death=mortality_risk(p)*(1+q.scarcity*.8)*(1-injury_resilience(p)*.15)
   if r.random()<death:self._die(p)
 def _die(self,p):
  p.alive=False;e=self.w.emit("death",Layer.REALITY,(Ref("person",p.id),),Ref("settlement",p.settlement));self.w.metaphysics.record_death(p.id)
  if try_resurrection(self.w,p.id,(e.id,)):return
  for q in self.w.living():
   rel=self.w.social.get(p.id,q.id)
   if rel.attachment>.25:q.grief=min(1,q.grief+.2*rel.attachment)
  self.w.economy.inherit_person(self.w,p.id,e.id)
 def _demography(self):
  by={sid:[] for sid in self.w.settlements}
  for p in self.w.living():by[p.settlement].append(p)
  for sid,people in by.items():
   adults=[p for p in people if p.age>=16]
   for p in adults:
    r=self.rng.stream("birth",self.w.year,p.id)
    if not reproductive_window(p):continue
    partners=[q for q in adults if q.id!=p.id and pair_reproductive_opportunity(p,q) and self.w.genealogy.relatedness(p.id,q.id)<.25]
    if partners and r.random()<.008:
     q=partners[int(r.random()*len(partners))%len(partners)];hid=p.household if p.household in self.w.households else q.household;pid=self.w.next_person;self.w.next_person+=1;species=child_species(p,q,r);child=Person(pid,self.w.year,sid,hid,species=species,parents=(p.id,q.id));self.w.people[pid]=child;self.w.households[hid].members.append(pid);self.w.genealogy.add(pid,(p.id,q.id));self.w.metaphysics.soul(pid);self.w.emit("birth",Layer.REALITY,(Ref("person",p.id),Ref("person",q.id)),Ref("settlement",sid),child=pid,species=species)
 def _pressure(self):
  for sid,q in self.w.local.items():
   s=self.w.settlements[sid];s.prosperity=max(0,min(1,s.prosperity+.003-.01*q.scarcity));s.defense=max(.05,min(1,s.defense+.0005))
 def _memory(self):
  for p in self.w.living():p.grief*=.985;p.fear*=.99
