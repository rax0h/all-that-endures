"""Frozen agency step from 216c2660 for differential stabilization tests."""
from simulation.ate_sim.agency import ActionRecord, _practice_path
from simulation.ate_sim.rank_ecology import rank_ecology_step

def legacy_agency_step(world,rng):
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
