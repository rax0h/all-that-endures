from __future__ import annotations
from dataclasses import dataclass,field

@dataclass
class MotiveState:
    hunger:float=0.; safety:float=0.; belonging:float=0.; wealth:float=0.; curiosity:float=0.; legacy:float=0.; obligation:float=0.; status:float=0.

@dataclass
class ActionRecord:
    year:int; person:int; action:str; motive:str; strength:float; event_id:int|None=None

@dataclass
class AgencyState:
    motives:dict[int,MotiveState]=field(default_factory=dict)
    actions:list[ActionRecord]=field(default_factory=list)

    def assess(self,world,p):
        q=world.local[p.settlement];h=world.households[p.household]
        rel=[r for (a,b),r in world.social.edges.items() if p.id in (a,b)]
        attachment=max([r.attachment for r in rel] or [0.])
        dependents=sum(1 for x in world.genealogy.children.get(p.id,[]) if world.people.get(x) and world.people[x].alive and world.people[x].age<18)
        m=MotiveState(
            hunger=max(0.,min(1.,q.scarcity+(5-h.food)/10)),
            safety=max(0.,min(1.,world.cells[(world.settlements[p.settlement].x,world.settlements[p.settlement].y)].hazard*(1-h.preparedness)+p.fear)),
            belonging=max(0.,1-attachment),
            wealth=max(0.,min(1.,1-p.wealth/120.)),
            curiosity=p.curiosity,
            legacy=max(0.,min(1.,p.age/80))*p.attachment,
            obligation=min(1.,dependents*.18+p.grief*.2),
            status=max(0.,min(1.,.65-p.wealth/250.))*(.5+.5*(1-p.inhibition)),
        );self.motives[p.id]=m;return m

    def choose(self,world,p,rng):
        m=self.assess(world,p);choices={
            'secure_food':m.hunger*1.35,
            'prepare':m.safety,
            'work':m.wealth+.35*m.obligation,
            'socialize':m.belonging*.8,
            'learn':m.curiosity*(1-.55*m.hunger),
            'teach':m.legacy,
            'build':(.55*m.safety+.35*m.status)*(1-.5*m.hunger),
        }
        best=max(choices.values());near=[(a,v) for a,v in choices.items() if v>=best-.08]
        action,strength=near[int(rng.random()*len(near))%len(near)];motive=max(m.__dict__,key=m.__dict__.get)
        return action,motive,strength

def agency_step(world,rng):
    adults=[p for p in world.people.values() if p.alive and p.age>=16]
    for p in sorted(adults,key=lambda x:x.id):
        rr=rng.stream('agency',world.year,p.id);action,motive,strength=world.agency.choose(world,p,rr)
        domain={'secure_food':'agriculture','prepare':'defense','work':'craft','learn':'knowledge','teach':'knowledge','build':'construction'}.get(action)
        event=None
        if domain:
            amount=.12+.38*strength;world.skills.practice(p.id,domain,amount)
            if strength>.72 and rr.random()<.035:
                event=world.emit('purposeful_work',world.Layer.SOCIETY if hasattr(world,'Layer') else __import__('ate_sim.core',fromlist=['Layer']).Layer.SOCIETY,actors=(__import__('ate_sim.core',fromlist=['Ref']).Ref('person',p.id),),location=__import__('ate_sim.core',fromlist=['Ref']).Ref('settlement',p.settlement),action=action,motive=motive,domain=domain,strength=strength)
        if action=='secure_food':world.households[p.household].food+=.08+.2*strength
        elif action=='prepare':world.households[p.household].preparedness=min(1.,world.households[p.household].preparedness+.002*strength)
        elif action=='work':p.wealth+=.03*strength
        world.agency.actions.append(ActionRecord(world.year,p.id,action,motive,strength,None if event is None else event.id))
