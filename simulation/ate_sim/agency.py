from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from .magic_progression import practice_ability,record_body_transition
from .rank_ecology import rank_ecology_step

# Ordinary wealth is the civilian market scale. The old .03 work payout made a
# seven-unit common essence cost centuries of labor for descendants born at zero.
# Half a unit per full-strength work year keeps ordinary goods and wages on the
# same scale without granting magic, resources, or rank directly.
ORDINARY_WORK_INCOME = .50
AGENCY_ACTION_FUNCTIONS={
 'secure_food':{'creation','control','support','detection','recovery'},
 'prepare':{'enhancement','control','movement','detection','recovery'},
 'work':{'creation','enhancement','control','support','exchange'},
 'socialize':{'influence','support','detection','exchange'},
 'learn':{'detection','control','transformation','support'},
 'teach':{'influence','support','control','exchange'},
 'build':{'creation','enhancement','control','transformation'},
}
ACTION_DOMAIN={'secure_food':'agriculture','prepare':'defense','work':'craft',
               'learn':'knowledge','teach':'knowledge','build':'construction'}
@dataclass
class MotiveState:hunger:float=0.;safety:float=0.;belonging:float=0.;wealth:float=0.;curiosity:float=0.;legacy:float=0.;obligation:float=0.;status:float=0.
@dataclass
class ActionRecord:year:int;person:int;action:str;motive:str;strength:float;event_id:int|None=None
@dataclass
class AgencyState:
 motives:dict[int,MotiveState]=field(default_factory=dict);actions:list[ActionRecord]=field(default_factory=list)
 def assess(self,world,p,attachment=None,dependents=None):
  q=world.local[p.settlement];h=world.households[p.household]
  if attachment is None:attachment=max((r.attachment for r in world.social.relationships_for(p.id)),default=0.)
  if dependents is None:dependents=sum(1 for x in world.genealogy.children.get(p.id,[]) if world.people.get(x) and world.people[x].alive and world.people[x].age<18)
  m=MotiveState(max(0.,min(1.,q.scarcity+max(0.,(5-h.food)/10))),max(0.,min(1.,world.cells[(world.settlements[p.settlement].x,world.settlements[p.settlement].y)].hazard*(1-h.preparedness)+p.fear)),max(0.,1-attachment),max(0.,min(1.,1-p.wealth/120.)),p.curiosity,max(0.,min(1.,p.age/80))*p.attachment,min(1.,dependents*.18+p.grief*.2),max(0.,min(1.,.65-p.wealth/250.))*(.5+.5*(1-p.inhibition)));self.motives[p.id]=m;return m
 def choose(self,world,p,rng,attachment=None,dependents=None):
  m=self.assess(world,p,attachment,dependents);choices={'secure_food':m.hunger*1.35,'prepare':m.safety,'work':m.wealth+.35*m.obligation,'socialize':m.belonging*.8,'learn':m.curiosity*(1-.55*m.hunger),'teach':m.legacy,'build':(.55*m.safety+.35*m.status)*(1-.5*m.hunger)};best=max(choices.values());near=[(a,v) for a,v in choices.items() if v>=best-.08];action,strength=near[int(rng.random()*len(near))%len(near)];return action,max(m.__dict__,key=m.__dict__.get),strength


def _practice_path(world,p,rr,action,strength):
 # An incomplete rank-0 path's awakened abilities already begin at Iron.
 # Advancement's body ceiling makes every practice call a no-op until 20/20
 # completes the body, so avoid rebuilding candidate lists for those users.
 if p.rank<=0:return
 path=world.advancement.path(p.id)
 if path is None or not path.abilities:return
 body_rank=p.rank;ceiling=min(5,max(1,body_rank)+1)
 # Advancement.practice cannot move an ability at or above this body's current
 # training ceiling. Do not rebuild/shuffle candidate lists or call into
 # progression for hundreds of mature partial users whose abilities are capped.
 trainable=[(i,a) for i,a in enumerate(path.abilities) if a.rank<ceiling]
 if not trainable:return
 relevant=AGENCY_ACTION_FUNCTIONS.get(action,set())
 candidates=[(i,a) for i,a in trainable if a.function in relevant] or trainable;rr.shuffle(candidates);uses=max(1,min(len(candidates),2+int(3*strength)));before=body_rank
 for i,a in candidates[:uses]:
  meaningful=(.10+.22*strength)*(.75+.5*p.curiosity);reflection=(.25+.75*p.curiosity) if action in ('learn','teach','socialize') else .08*p.curiosity;practice_ability(world,p,i,meaningful,reflection,context=action,body_rank=body_rank)
 record_body_transition(world,p,before,context=action)

def agency_step(world,rng):
 dependents={}
 for p in world.current_people():
  if p.alive and p.age<18:
   for parent in p.parents:dependents[parent]=dependents.get(parent,0)+1
 for p in (x for x in world.current_people() if x.alive and x.age>=16):
  attachment=max((r.attachment for r in world.social.relationships_for(p.id)),default=0.)
  rr=rng.stream('agency',world.year,p.id);action,motive,strength=world.agency.choose(world,p,rr,attachment,dependents.get(p.id,0));domain=ACTION_DOMAIN.get(action);event=None
  if domain:world.skills.practice(p.id,domain,.12+.38*strength)
  _practice_path(world,p,rr,action,strength)
  if action=='secure_food':world.households[p.household].food+=.08+.2*strength
  elif action=='prepare':world.households[p.household].preparedness=min(1.,world.households[p.household].preparedness+.002*strength)
  elif action=='work':p.wealth+=ORDINARY_WORK_INCOME*strength
  world.agency.actions.append(ActionRecord(world.year,p.id,action,motive,strength,None if event is None else event.id))
 # Actions are a bounded recent decision cache; durable history lives in
 # events and the post-run archive. A few recent years are ample for consumers
 # such as rank ecology and avoid copying a 50k-entry list every mature year.
 if len(world.agency.actions)>6000:world.agency.actions=world.agency.actions[-3000:]
 rank_ecology_step(world,rng)
