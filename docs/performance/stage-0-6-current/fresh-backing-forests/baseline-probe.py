import json,platform,sqlite3,subprocess,time
from pathlib import Path
from ate_sim.core import Person
from ate_sim.skills import SkillHistory
from ate_sim.culture import Practice
from ate_sim import persistence_proof_world as world
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
out=Path('/tmp/ate-fresh-baseline-results');out.mkdir(exist_ok=False)
read=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
source=dict(head=read('rev-parse','HEAD'),runtime_tree=read('rev-parse','HEAD:simulation/ate_sim'),python=platform.python_version(),sqlite=sqlite3.sqlite_version,scenario='fresh')
def mutate(s,person,generation):
 s.world.people[person]=Person(person,0,1,1);s.world.next_person=person+1
 s.skills[1,'craft'].level=generation/10;s.world.settlements[1].food_stock=100.+generation;s.world.year=generation
 s.world.skills.skills[person,'new']=SkillHistory(person,'new',teachers=[7],provenance=s.skills[1,'craft'].provenance)
 record=SkillHistory(person,'nested',provenance=[generation])
 s.world.culture.practices[person]=Practice(person,'craft','fresh',generation,1,traits={'a':record,'b':record,'values':{1,2,3}})
rows=[]
for size in (1000,10000,100000):
 path,pair=fixture(out/str(size),size=size)
 with opened(path,pair) as s:mutate(s,99,1);s.save();pair=s.proof_manifest
 calls=[];original=world._audit_world
 def audit(*a,**kw):calls.append(True);return original(*a,**kw)
 with opened(path,pair) as s:
  world._audit_world=audit;start,cpu=time.perf_counter(),time.process_time()
  try:
   mutate(s,100,2);assert s.save()==2
   wall,used=time.perf_counter()-start,time.process_time()-cpu;pair=s.proof_manifest
  finally:world._audit_world=original
 with opened(path,pair) as s:
  assert tuple(s.world.people)==(99,100)
  assert s.skills[100,'new'].provenance is s.skills[1,'craft'].provenance
  assert len(s.skills[1,'craft'].provenance)==size
  t=s.world.culture.practices[100].traits;assert t['a'] is t['b'];assert list(t['a'].provenance)==[2]
 row=dict(size=size,source=source,archive_unit='retained history values',raw_save_seconds=wall,raw_save_cpu_seconds=used,full_world_audits_within_save=len(calls),status='complete')
 rows.append(row);(out/f'size-{size}.json').write_text(json.dumps(row,indent=2)+'\n');print(size,wall,used,len(calls),flush=True)
(out/'summary.json').write_text(json.dumps(dict(source=source,results=rows),indent=2)+'\n')
