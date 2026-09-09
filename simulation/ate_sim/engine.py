from .core import *
from .rank import annual_mortality,profile,military_value
from .species import compose_biology,species
from .culture import cultural_step
class Simulation:
 def __init__(self,world): self.w=world; self.rng=RNG(world.seed)
 def run(self,years):
  for _ in range(years):self.step()
  return self.w
 def step(self): self.w.year+=1; self._weather(); self._production(); self._people(); self._demography(); self._pressure(); cultural_step(self.w,self.w.culture,self.rng); self._memory()
 def _weather(self):
  for sid,s in self.w.settlements.items():
   c=self.w.cells[(s.x,s.y)]; r=self.rng.stream("weather",self.w.year,sid); q=self.w.local[sid]; q.rain=max(0,min(1,c.moisture+r.uniform(-.38,.38))); q.drought=max(0,.35-q.rain); q.flood=max(0,q.rain-.82)
   if q.drought>.12:self.w.emit("drought",Layer.REALITY,location=Ref("settlement",sid),severity=q.drought)
   if q.flood>.05:self.w.emit("flood",Layer.REALITY,location=Ref("settlement",sid),severity=q.flood)
 def _production(self):
  for sid,s in self.w.settlements.items():
   people=[p for p in self.w.people.values() if p.alive and p.settlement==sid]; c=self.w.cells[(s.x,s.y)]; q=self.w.local[sid]; labor=sum(compose_biology(p.species,profile(p.rank))["endurance"]*p.health for p in people); food=sum(compose_biology(p.species,profile(p.rank))["food_need"] for p in people); crop=(12+2*labor)*c.fertility*(.45+.75*q.rain)*(1+.5*s.irrigation); s.food_stock+=crop-food
   if q.flood:s.food_stock-=20*q.flood;s.roads=max(0,s.roads-.08*q.flood)
   q.scarcity=max(0,min(1,(food*10-s.food_stock)/max(1,food*10)))
   if q.scarcity>.25:self.w.emit("food_scarcity",Layer.SOCIETY,location=Ref("settlement",sid),severity=q.scarcity)
 def _people(self):
  for pid,p in list(self.w.people.items()):
   if not p.alive:continue
   p.age+=1; q=self.w.local[p.settlement]; r=self.rng.stream("life",self.w.year,pid); risk=annual_mortality(p.age,p.rank,q.scarcity)/max(.4,species(p.species).baseline_longevity)
   if r.random()<risk:self._die(p,"natural")
   else:p.grief*=.94;p.fear*=.9
 def _die(self,p,cause,causes=()):
  if not p.alive:return
  p.alive=False; e=self.w.emit("death",Layer.REALITY,(Ref("person",p.id),),Ref("settlement",p.settlement),causes,age=p.age,rank=p.rank,species=p.species,cause=cause); h=self.w.households[p.household]
  survivors=[i for i in h.members if i!=p.id and self.w.people[i].alive]
  for oid in survivors:
   q=self.w.people[oid]; rel=self.w.social.get(p.id,oid); q.grief=min(1,q.grief+.12+.55*rel.attachment); self.w.social.record(p.id,oid,e.id,attachment=.01); self.w.emit("bereavement",Layer.SOCIETY,(Ref("person",oid),Ref("person",p.id)),Ref("settlement",p.settlement),(e.id,),grief=q.grief)
  if survivors:
   heir=min(survivors); inherited=p.wealth; self.w.people[heir].wealth+=inherited; p.wealth=0.; self.w.emit("inheritance",Layer.SOCIETY,(Ref("person",heir),Ref("person",p.id)),Ref("settlement",p.settlement),(e.id,),wealth=inherited)
 def _demography(self):
  for hid,h in list(self.w.households.items()):
   if not h.alive:continue
   living=[self.w.people[i] for i in h.members if self.w.people[i].alive]; adults=[p for p in living if 18<=p.age<=42]; q=self.w.local[h.settlement]; r=self.rng.stream("birth",self.w.year,hid); fertility=sum(species(p.species).fertility for p in adults)/max(1,len(adults)); chance=.055*min(1,len(adults)/2)*(1-.75*q.scarcity)*fertility
   if len(living)<8 and adults and r.random()<chance:
    parents=tuple(p.id for p in sorted(adults,key=lambda x:x.id)[:2]); base=[self.w.people[i] for i in parents]; pid=self.w.next_person;self.w.next_person+=1
    def inh(a):return max(0,min(1,sum(getattr(p,a) for p in base)/len(base)+r.gauss(0,.12)))
    sp=base[0].species if len({p.species for p in base})==1 or r.random()<.5 else base[-1].species; p=Person(pid,self.w.year,h.settlement,hid,age=0,temperament=inh("temperament"),attachment=inh("attachment"),curiosity=inh("curiosity"),inhibition=inh("inhibition"),species=sp,parents=parents); self.w.people[pid]=p;h.members.append(pid);self.w.genealogy.birth(pid,parents); e=self.w.emit("birth",Layer.REALITY,(Ref("person",pid),)+tuple(Ref("person",x) for x in parents),Ref("settlement",h.settlement),household=hid,species=sp)
    for x in parents:self.w.social.record(x,pid,e.id,trust=.15,attachment=.3,obligation=.25)
   if not living:h.alive=False
 def _pressure(self):
  for sid,s in self.w.settlements.items():
   c=self.w.cells[(s.x,s.y)];r=self.rng.stream("hazard",self.w.year,sid)
   if r.random()<.012*c.hazard:
    residents=[p for p in self.w.people.values() if p.alive and p.settlement==sid]; exposure=.5+.5*r.random(); hp=sum(self.w.households[h].preparedness for h in s.households)/max(1,len(s.households)); defenders=sum(military_value(p.rank,health=p.health)*species(p.species).strength for p in residents); rank_defense=min(.35,defenders/max(1,len(residents))*.025); preparedness=min(.95,.55*s.defense+.2*s.roads+.25*hp+rank_defense); severity=max(0,exposure*(1-preparedness)*c.hazard); attack=self.w.emit("monster_surge",Layer.REALITY,location=Ref("settlement",sid),severity=severity,preparedness=preparedness)
    for p in residents:
     resilience=profile(p.rank).injury_resilience*species(p.species).endurance
     if self.rng.stream("surge_person",self.w.year,p.id).random()<severity*.12/resilience:self._die(p,"monster_surge",(attack.id,))
    s.memory["monster_surge"]=min(1,s.memory.get("monster_surge",0)+severity);s.defense=min(1,s.defense+.08*severity)
 def _memory(self):
  for s in self.w.settlements.values():
   for k in list(s.memory):s.memory[k]*=.992
