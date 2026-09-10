from __future__ import annotations
from dataclasses import dataclass,field
from .core_types import layer_ref
from .rank_ecology import rank_ecology_step
@dataclass
class MotiveState:hunger:float=0.;safety:float=0.;belonging:float=0.;wealth:float=0.;curiosity:float=0.;legacy:float=0.;obligation:float=0.;status:float=0.
@dataclass
class ActionRecord:year:int;person:int;action:str;motive:str;strength:float;event_id:int|None=None
@dataclass
class AgencyState:
 motives:dict[int,MotiveState]=field(default_factory=dict);actions:list[ActionRecord]=field(default_factory=list)
 def assess(self,world,p,attachment=None,dependents=None):
  q=world.local[p.settlement];h=world.households[p.household]
  if attachment is None:attachment=max((r.attachment for r in world.social.edges.values() if p.id in (r.a,r.b)),default=0.)
  if dependents is None:dependents=sum(1 for x in world.genealogy.children.get(p.id,[]) if world.people.get(x) and world.people[x].alive and world.people[x].age<18)
  m=MotiveState(max(0.,min(1.,q.scarcity+max(0.,(5-h.food)/10))),max(0.,min(1.,world.cells[(world.settlements[p.settlement].x,world.settlements[p.settlement].y)].hazard*(1-h.preparedness)+p.fear)),max(0.,1-attachment),max(0.,min(1.,1-p.wealth/120.)),p.curiosity,max(0.,min(1.,p.age/80))*p.attachment,min(1.,dependents*.18+p.grief*.2),max(0.,min(1.,.65-p.wealth/250.))*(.5+.5*(1-p.inhibition)));self.motives[p.id]=m;return m
 def choose(self,world,p,rng,attachment=None,dependents=None):
  m=self.assess(world,p,attachment,dependents);choices={'secure_food':m.hunger*1.35,'prepare':m.safety,'work':m.wealth+.35*m.obligation,'socialize':m.belonging*.8,'learn':m.curiosity*(1-.55*m.hunger),'teach':m.legacy,'build':(.55*m.safety+.35*m.status)*(1-.5*m.hunger)};best=max(choices.values());near=[(a,v) for a,v in choices.items() if v>=best-.08];action,strength=near[int(rng.random()*len(near))%len(near)];return action,max(m.__dict__,key=m.__dict__.get),strength

def _practice_path(world,p,rr,action,strength):
 path=world.advancement.path(p.id)
 if path is None or not path.abilities:return
 relevant={'secure_food':{'creation','control','support','detection','recovery'},'prepare':{'enhancement','control','movement','detection','recovery'},'work':{'creation','enhancement','control','support','exchange'},'socialize':{'influence','support','detection','exchange'},'learn':{'detection','control','transformation','support'},'teach':{'influence','support','control','exchange'},'build':{'creation','enhancement','control','transformation'}}.get(action,set())
 candidates=[(i,a) for i,a in enumerate(path.abilities) if a.function in relevant] or list(enumerate(path.abilities));rr.shuffle(candidates);uses=max(1,min(len(candidates),2+int(3*strength)));before=world.advancement.rank(p.id)
 for i,a in candidates[:uses]:
  meaningful=(.10+.22*strength)*(.75+.5*p.curiosity);reflection=(.25+.75*p.curiosity) if action in ('learn','teach','socialize') else .08*p.curiosity;world.advancement.practice(p.id,i,meaningful,reflection)
 after=world.advancement.rank(p.id)
 if after>before:p.rank=after;Layer,Ref=layer_ref();world.emit('rank_advanced',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),from_rank=before,to_rank=after,practice_context=action)

def agency_step(world,rng):
 attachments={}
 for r in world.social.edges.values():attachments[r.a]=max(attachments.get(r.a,0.),r.attachment);attachments[r.b]=max(attachments.get(r.b,0.),r.attachment)
 dependents={}
 for p in world.people.values():
  if p.alive and p.age<18:
   for parent in p.parents:dependents[parent]=dependents.get(parent,0)+1
 for p in sorted((x for x in world.people.values() if x.alive and x.age>=16),key=lambda x:x.id):
  rr=rng.stream('agency',world.year,p.id);action,motive,strength=world.agency.choose(world,p,rr,attachments.get(p.id,0.),dependents.get(p.id,0));domain={'secure_food':'agriculture','prepare':'defense','work':'craft','learn':'knowledge','teach':'knowledge','build':'construction'}.get(action);event=None
  if domain:world.skills.practice(p.id,domain,.12+.38*strength)
  _practice_path(world,p,rr,action,strength)
  if action=='secure_food':world.households[p.household].food+=.08+.2*strength
  elif action=='prepare':world.households[p.household].preparedness=min(1.,world.households[p.household].preparedness+.002*strength)
  elif action=='work':p.wealth+=.03*strength
  world.agency.actions.append(ActionRecord(world.year,p.id,action,motive,strength,None if event is None else event.id))
 if len(world.agency.actions)>50000:world.agency.actions=world.agency.actions[-50000:]
 rank_ecology_step(world,rng)
