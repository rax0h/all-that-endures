from __future__ import annotations
from dataclasses import dataclass,field
from .magic_progression import practice_ability,record_body_transition
from .rank_ecology import rank_ecology_step

ORDINARY_WORK_INCOME=.50
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

@dataclass(slots=True)
class MotiveState:
 hunger:float=0.;safety:float=0.;belonging:float=0.;wealth:float=0.;curiosity:float=0.;legacy:float=0.;obligation:float=0.;status:float=0.
@dataclass(slots=True)
class ActionRecord:
 year:int;person:int;action:str;motive:str;strength:float;event_id:int|None=None
@dataclass
class AgencyState:
 motives:dict[int,MotiveState]=field(default_factory=dict)
 actions:list[ActionRecord]=field(default_factory=list)
 def assess(self,world,p,attachment=None,dependents=None,hazard=None):
  q=world.local[p.settlement];h=world.households[p.household]
  if attachment is None:attachment=world.social.max_attachment(p.id)
  if dependents is None:dependents=sum(1 for x in world.genealogy.children.get(p.id,()) if world.people.get(x) and world.people[x].alive and world.people[x].age<18)
  m=self.motives.get(p.id)
  if m is None:m=MotiveState();self.motives[p.id]=m
  m.hunger=max(0.,min(1.,q.scarcity+max(0.,(5-h.food)/10)))
  if hazard is None:
   settlement=world.settlements[p.settlement];hazard=world.cells[(settlement.x,settlement.y)].hazard
  m.safety=max(0.,min(1.,hazard*(1-h.preparedness)+p.fear))
  m.belonging=max(0.,1-attachment);m.wealth=max(0.,min(1.,1-p.wealth/120.));m.curiosity=p.curiosity
  m.legacy=max(0.,min(1.,p.age/80))*p.attachment;m.obligation=min(1.,dependents*.18+p.grief*.2)
  m.status=max(0.,min(1.,.65-p.wealth/250.))*(.5+.5*(1-p.inhibition))
  return m
 def choose(self,world,p,rng,attachment=None,dependents=None,hazard=None):
  m=self.assess(world,p,attachment,dependents,hazard)
  secure=m.hunger*1.35;prepare=m.safety;work=m.wealth+.35*m.obligation
  socialize=m.belonging*.8;learn=m.curiosity*(1-.55*m.hunger);teach=m.legacy
  build=(.55*m.safety+.35*m.status)*(1-.5*m.hunger)
  scored=(('secure_food',secure),('prepare',prepare),('work',work),('socialize',socialize),('learn',learn),('teach',teach),('build',build))
  best=max(v for _,v in scored);eligible=[x for x in scored if x[1]>=best-.08]
  action,strength=eligible[int(rng.random()*len(eligible))%len(eligible)]
  motive='hunger';mv=m.hunger
  for name,value in (('safety',m.safety),('belonging',m.belonging),('wealth',m.wealth),('curiosity',m.curiosity),('legacy',m.legacy),('obligation',m.obligation),('status',m.status)):
   if value>mv:motive=name;mv=value
  return action,motive,strength


def _practice_path(world,p,rr,action,strength):
 if p.rank<=0:return
 path=world.advancement.path(p.id)
 if path is None or not path.abilities:return
 body_rank=p.rank;ceiling=min(5,max(1,body_rank)+1)
 trainable=[(i,a) for i,a in enumerate(path.abilities) if a.rank<ceiling]
 if not trainable:return
 relevant=AGENCY_ACTION_FUNCTIONS.get(action,set());candidates=[x for x in trainable if x[1].function in relevant] or trainable
 rr.shuffle(candidates);uses=max(1,min(len(candidates),2+int(3*strength)));changed=False
 for i,a in candidates[:uses]:
  before=a.rank;meaningful=(.10+.22*strength)*(.75+.5*p.curiosity)
  reflection=(.25+.75*p.curiosity) if action in ('learn','teach','socialize') else .08*p.curiosity
  practice_ability(world,p,i,meaningful,reflection,context=action,body_rank=body_rank,path=path)
  changed=changed or a.rank!=before
 if changed:record_body_transition(world,p,body_rank,context=action)


def agency_step(world,rng):
 view=world.runtime_view();people=view.living;current_actions={};year=world.year
 max_attachment=world.social.max_attachment;stream=rng.stream;choose=world.agency.choose
 skills_practice=world.skills.practice;households=world.households;append_action=world.agency.actions.append
 hazards={sid:world.cells[(s.x,s.y)].hazard for sid,s in world.settlements.items()}
 for p in people:
  if p.age<16:continue
  attachment=max_attachment(p.id);rr=stream('agency',year,p.id)
  action,motive,strength=choose(world,p,rr,attachment,view.dependents.get(p.id,0),hazards[p.settlement]);domain=ACTION_DOMAIN.get(action)
  if domain:skills_practice(p.id,domain,.12+.38*strength)
  if p.rank>0:_practice_path(world,p,rr,action,strength)
  if action=='secure_food':households[p.household].food+=.08+.2*strength
  elif action=='prepare':households[p.household].preparedness=min(1.,households[p.household].preparedness+.002*strength)
  elif action=='work':p.wealth+=ORDINARY_WORK_INCOME*strength
  rec=ActionRecord(year,p.id,action,motive,strength,None);append_action(rec)
  if p.rank>0:current_actions[p.id]=rec
 if len(world.agency.actions)>6000:world.agency.actions=world.agency.actions[-3000:]
 rank_ecology_step(world,rng,current_actions)
