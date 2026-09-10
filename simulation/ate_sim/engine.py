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
   p.age+=1;q=self.w.local[p.settlement];r=self.rng.stream("life",self.w.year,pid);risk=mortality_risk(p,q.scarcity)
   if r.random()<risk:self._die(p,"natural")
   else:p.grief*=.94;p.fear*=.9
 def _die(self,p,cause,causes=()):
  if not p.alive:return
  p.alive=False;e=self.w.emit("death",Layer.REALITY,(Ref("person",p.id),),Ref("settlement",p.settlement),causes,age=p.age,rank=p.rank,species=p.species,cause=cause);self.w.metaphysics.record_death(p.id)
  if try_resurrection(self.w,p.id,e) is not None:return
  h=self.w.households[p.household];survivors=[i for i in h.members if i!=p.id and self.w.people[i].alive]
  for oid in survivors:
   q=self.w.people[oid];rel=self.w.social.get(p.id,oid);q.grief=min(1,q.grief+.12+.55*rel.attachment);self.w.social.record(p.id,oid,e.id,attachment=.01);self.w.emit("bereavement",Layer.SOCIETY,(Ref("person",oid),Ref("person",p.id)),Ref("settlement",p.settlement),(e.id,),grief=q.grief)
  if survivors:
   children=[x for x in self.w.genealogy.children.get(p.id,[]) if self.w.people.get(x) and self.w.people[x].alive];heir=min(children) if children else min(survivors);inherited=p.wealth;self.w.people[heir].wealth+=inherited;p.wealth=0.;self.w.emit("inheritance",Layer.SOCIETY,(Ref("person",heir),Ref("person",p.id)),Ref("settlement",p.settlement),(e.id,),wealth=inherited)
 def _capacity(self,sid):
  s=self.w.settlements[sid];c=self.w.cells[(s.x,s.y)];return max(24.,90.+150.*c.fertility+55.*s.irrigation+35.*s.roads-45.*c.hazard)
 def _demography(self):
  alive_by_settlement={sid:[] for sid in self.w.settlements};dependent_count={}
  for p in self.w.people.values():
   if not p.alive:continue
   alive_by_settlement[p.settlement].append(p)
   if p.age<18 and len(p.parents)==2:dependent_count[tuple(sorted(p.parents))]=dependent_count.get(tuple(sorted(p.parents)),0)+1
  for pair,formed in sorted(self.w.social.partnerships.items()):
   a=self.w.people.get(pair[0]);b=self.w.people.get(pair[1])
   if not a or not b or not a.alive or not b.alive or a.settlement!=b.settlement:continue
   sid=a.settlement;q=self.w.local[sid];residents=alive_by_settlement[sid];cap=self._capacity(sid)
   if not reproductive_window(a) or not reproductive_window(b):continue
   density=len(residents)/cap;rr=self.rng.stream("birth",self.w.year,pair[0]*100000+pair[1]);bio_opportunity=pair_reproductive_opportunity(a,b);resource=max(.05,1-.72*q.scarcity);density_factor=max(.05,min(1.35,1.25-density*.85));chance=.22*bio_opportunity*resource*density_factor
   key=tuple(sorted(pair));child_count=dependent_count.get(key,0);chance*=1/(1+.30*child_count)
   if rr.random()>=chance:continue
   base=[a,b];hid=a.household if a.household==b.household else (a.household if len(self.w.households[a.household].members)<=len(self.w.households[b.household].members) else b.household);h=self.w.households[hid];pid=self.w.next_person;self.w.next_person+=1;r=rr
   def inh(attr):return max(0,min(1,sum(getattr(p,attr) for p in base)/2+r.gauss(0,.12)))
   sp=child_species(a,b,rr);p=Person(pid,self.w.year,sid,hid,age=0,temperament=inh("temperament"),attachment=inh("attachment"),curiosity=inh("curiosity"),inhibition=inh("inhibition"),species=sp,parents=pair);self.w.people[pid]=p;self.w.metaphysics.soul(pid);h.members.append(pid);self.w.genealogy.birth(pid,pair);alive_by_settlement[sid].append(p);dependent_count[key]=child_count+1;e=self.w.emit("birth",Layer.REALITY,(Ref("person",pid),Ref("person",a.id),Ref("person",b.id)),Ref("settlement",sid),(formed,),household=hid,species=sp,reproductive_opportunity=bio_opportunity);self.w.lineage.register("person",pid,tuple(("person",x) for x in pair),e.id,self.w.year);inherited=self.w.communities.inherit(pid,pair)
   for cid,strength in inherited.items():self.w.transmission.record(self.w.year,"parenting","community_membership",cid,"parents",min(pair),"person",pid,e.id,reliability=strength)
   for parent in pair:self.w.social.record(parent,pid,e.id,trust=.15,attachment=.3,obligation=.25)
  for h in self.w.households.values():
   if h.alive and not any(self.w.people[i].alive for i in h.members):h.alive=False
 def _pressure(self):
  by_settlement={sid:[] for sid in self.w.settlements}
  for p in self.w.people.values():
   if p.alive:by_settlement[p.settlement].append(p)
  for sid,s in self.w.settlements.items():
   c=self.w.cells[(s.x,s.y)];r=self.rng.stream("hazard",self.w.year,sid);ambient=self.w.ambient_magic.field(sid).level;surge_chance=.012*c.hazard*(1+max(0.,ambient-.55)*1.8)
   if r.random()<surge_chance:
    residents=by_settlement[sid];exposure=.5+.5*r.random();hp=sum(self.w.households[h].preparedness for h in s.households)/max(1,len(s.households));defenders=sum(combat_value(p) for p in residents);rank_defense=min(.35,defenders/max(1,len(residents))*.025);preparedness=min(.95,.55*s.defense+.2*s.roads+.25*hp+rank_defense);severity=max(0,exposure*(1-preparedness)*c.hazard*(1+max(0.,ambient-.72)*.8));attack=self.w.emit("monster_surge",Layer.REALITY,location=Ref("settlement",sid),severity=severity,preparedness=preparedness,ambient_magic=round(ambient,3))
    for p in residents:
     resilience=injury_resilience(p)
     if self.rng.stream("surge_person",self.w.year,p.id).random()<severity*.12/resilience:self._die(p,"monster_surge",(attack.id,))
    s.memory["monster_surge"]=min(1,s.memory.get("monster_surge",0)+severity);s.defense=min(1,s.defense+.08*severity)
 def _memory(self):
  for s in self.w.settlements.values():
   for k in list(s.memory):s.memory[k]*=.992