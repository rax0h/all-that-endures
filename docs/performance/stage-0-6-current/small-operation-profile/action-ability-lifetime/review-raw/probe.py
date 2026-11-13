import gc, hashlib, json, platform, sqlite3, sys, weakref
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import random
from ate_sim.agency import _practice_path
from ate_sim.advancement import PracticeBatch
from ate_sim.incremental_store import StoreError
from ate_sim import persistence_history_runtime as records
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture, fast_open

out=Path('/workspace/scratch/72797495b7a4/action-review')
expected=json.loads(Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
import _sqlite3
runtime={'executable':sys.executable,'resolved_executable':str(Path(sys.executable).resolve()),'executable_sha256':sha(Path(sys.executable).resolve()),'system_python_sha256':sha('/usr/bin/python3'),'python':sys.version,'compiler':platform.python_compiler(),'sqlite':sqlite3.sqlite_version,'sqlite_source_id':sqlite3.connect(':memory:').execute('select sqlite_source_id()').fetchone()[0],'sqlite_compile_options':[r[0] for r in sqlite3.connect(':memory:').execute('pragma compile_options')],'sqlite_extension_path':_sqlite3.__file__,'sqlite_extension_sha256':sha(_sqlite3.__file__),'loaded_sqlite_libraries':[{'path':r['path'],'sha256':sha(r['path'])} for r in expected['loaded_sqlite_libraries']]}
for key,value in runtime.items():assert value==expected[key],(key,value,expected[key])
(out/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
report={'fingerprint_matches':True}
with TemporaryDirectory(prefix='action-lifetime-review-') as d:
 def ceiling(world):
  configure(world)
  for ability in world.advancement.path(1).abilities:ability.rank=5
  world.people[1].rank=5
 path,pair=ranked_fixture(Path(d),size=4,configure=ceiling)
 refs=[];during=[];original=PracticeBatch.__init__
 def observe(self,*a,**kw):
  original(self,*a,**kw)
  refs.extend(weakref.ref(ability) for ability in self.path.abilities)
  during.append(sum(ref() is not None for ref in refs))
 with fast_open(path,pair) as session:
  with patch.object(PracticeBatch,'__init__',observe):
   _practice_path(session.world,session.world.people[1],random.Random(32),'work',.5)
  gc.collect()
  report['clean_references_during_action']=during
  report['clean_bodies_after_return']=sum(ref() is not None for ref in refs)
  assert during==[20] and report['clean_bodies_after_return']==0
  held=session.world.advancement.path(1).abilities[0]
 try:held.rank=4
 except StoreError as e:report['held_body_mutation_after_close_refused']=str(e)
 else:raise AssertionError('closed native body mutation accepted')
 with fast_open(path,pair) as session:
  session.store.db.execute("UPDATE records SET payload_checksum='action-review-source-corruption' WHERE namespace='world.year'")
  session.store.db.commit()
  try:_practice_path(session.world,session.world.people[1],random.Random(32),'work',.5)
  except StoreError as e:report['actual_source_corruption_before_action_refused']=str(e)
  else:raise AssertionError('source corruption accepted')
(out/'probe-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
