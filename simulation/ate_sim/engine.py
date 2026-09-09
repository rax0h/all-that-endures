from .core import *

class Simulation:
    def __init__(self,world): self.w=world; self.rng=RNG(world.seed)
    def run(self,years):
        for _ in range(years): self.step()
        return self.w
    def step(self): self.w.year+=1; self._weather(); self._production(); self._people(); self._demography(); self._pressure(); self._memory()
    def _weather(self):
        for sid,s in self.w.settlements.items():
            c=self.w.cells[(s.x,s.y)]; r=self.rng.stream("weather",self.w.year,sid); rain=max(0,min(1,c.moisture+r.uniform(-.38,.38))); drought=max(0,.35-rain); flood=max(0,rain-.82)
            if drought>.12: self.w.emit("drought",Layer.REALITY,location=Ref("settlement",sid),severity=drought)
            if flood>.05: self.w.emit("flood",Layer.REALITY,location=Ref("settlement",sid),severity=flood)
            s._rain=rain; s._drought=drought; s._flood=flood
    def _production(self):
        for sid,s in self.w.settlements.items():
            c=self.w.cells[(s.x,s.y)]; pop=sum(self.w.people[p].alive for h in s.households for p in self.w.households[h].members); crop=(12+2*pop)*c.fertility*(.45+.75*s._rain)*(1+.5*s.irrigation); s.food_stock+=crop-pop*1.05
            if s._flood: s.food_stock-=20*s._flood; s.roads=max(0,s.roads-.08*s._flood)
            s._scarcity=max(0,min(1,(pop*10-s.food_stock)/max(1,pop*10)))
            if s._scarcity>.25: self.w.emit("food_scarcity",Layer.SOCIETY,location=Ref("settlement",sid),severity=s._scarcity)
    def _people(self):
        for pid,p in list(self.w.people.items()):
            if not p.alive: continue
            p.age+=1; s=self.w.settlements[p.settlement]; r=self.rng.stream("life",self.w.year,pid); mortality=.003+max(0,p.age-65)*.0018+.025*s._scarcity
            if r.random()<mortality:
                p.alive=False; e=self.w.emit("death",Layer.REALITY,(Ref("person",pid),),Ref("settlement",p.settlement),age=p.age); h=self.w.households[p.household]
                for opid in h.members:
                    if opid!=pid and self.w.people[opid].alive:
                        q=self.w.people[opid]; q.grief=min(1,q.grief+.2+.5*q.attachment); self.w.emit("bereavement",Layer.SOCIETY,(Ref("person",opid),Ref("person",pid)),Ref("settlement",p.settlement),(e.id,),grief=q.grief)
            else: p.grief*=.94; p.fear*=.9
    def _demography(self):
        for hid,h in list(self.w.households.items()):
            if not h.alive: continue
            living=[self.w.people[i] for i in h.members if self.w.people[i].alive]; adults=[p for p in living if 18<=p.age<=42]; s=self.w.settlements[h.settlement]; r=self.rng.stream("birth",self.w.year,hid); chance=.055*min(1,len(adults)/2)*(1-.75*s._scarcity)
            if len(living)<8 and r.random()<chance and living:
                pid=self.w.next_person; self.w.next_person+=1; base=adults or living
                def inh(a): return max(0,min(1,sum(getattr(p,a) for p in base)/len(base)+r.gauss(0,.12)))
                p=Person(pid,self.w.year,h.settlement,hid,age=0,temperament=inh("temperament"),attachment=inh("attachment"),curiosity=inh("curiosity"),inhibition=inh("inhibition")); self.w.people[pid]=p; h.members.append(pid); self.w.emit("birth",Layer.REALITY,(Ref("person",pid),),Ref("settlement",h.settlement),household=hid)
            if not living: h.alive=False
    def _pressure(self):
        for sid,s in self.w.settlements.items():
            c=self.w.cells[(s.x,s.y)]; r=self.rng.stream("hazard",self.w.year,sid)
            if r.random()<.012*c.hazard:
                exposure=.5+.5*r.random(); hp=sum(self.w.households[h].preparedness for h in s.households)/max(1,len(s.households)); preparedness=min(.95,.55*s.defense+.2*s.roads+.25*hp); severity=max(0,exposure*(1-preparedness)*c.hazard); attack=self.w.emit("monster_surge",Layer.REALITY,location=Ref("settlement",sid),severity=severity,preparedness=preparedness); casualties=0
                for p in [p for p in self.w.people.values() if p.alive and p.settlement==sid]:
                    if self.rng.stream("surge_person",self.w.year,p.id).random()<severity*.12: p.alive=False; casualties+=1; self.w.emit("death",Layer.REALITY,(Ref("person",p.id),),Ref("settlement",sid),(attack.id,),cause="monster_surge")
                s.memory["monster_surge"]=min(1,s.memory.get("monster_surge",0)+severity); s.defense=min(1,s.defense+.08*severity); s.prosperity=max(0,s.prosperity-.08*severity); self.w.emit("surge_aftermath",Layer.SOCIETY,location=Ref("settlement",sid),causes=(attack.id,),casualties=casualties)
    def _memory(self):
        for s in self.w.settlements.values():
            for k in list(s.memory): s.memory[k]*=.992
