"""Bounded raw canonical20 action comparison, separate from annual acceptance."""
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path('/workspace/scratch/d88f8db353e8/ate')
OUT=ROOT/'docs/performance/stage-0-6-current/small-operation-profile/action-ability-lifetime/complete20-pairs'
SCRATCH=Path('/workspace/scratch/72797495b7a4/complete20-source')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
if len(sys.argv)>1:
 root=Path.cwd();sys.path[:0]=[str(root),str(root/'simulation')]
 from ate_sim.agency import _practice_path
 from ate_sim.persistence_proof_world_session import open_proof_world_session
 import random
 source,trial,commit=map(str,sys.argv[1:]);trial=Path(trial);trial.mkdir()
 original=sha(source);working=trial/'working.sqlite';shutil.copyfile(source,working)
 try:
  with open_proof_world_session(working,rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(commit)) as session:
   person=session.world.people[1]
   assert len(session.world.advancement.path(1).abilities)==20
   start=time.perf_counter();cpu=time.process_time()
   _practice_path(session.world,person,random.Random(32),'work',.5)
   timing=dict(wall=time.perf_counter()-start,cpu=time.process_time()-cpu)
   saved_digest=session.world.digest();before=session.pin.captured_head
   assert session.save()==before+1
   child=session.proof_manifest
  with open_proof_world_session(working,rules_id='private-catalog-copy',expected_commitment=child[1]) as restored:
   assert restored.world.digest()==saved_digest
  result=dict(status='complete',timing=timing,saved_digest=saved_digest,source_sha256=original,
   runtime_tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],text=True).strip(),
   agency_source_sha256=sha(root/'simulation/ate_sim/agency.py'))
  assert sha(source)==original
  record(trial/'report.json',result)
 finally:working.unlink(missing_ok=True)
 sys.exit()
sys.path[:0]=[str(ROOT),str(ROOT/'simulation')]
from simulation.tests.test_stage_0_6_proof_open import ranked_fixture
from simulation.tests.test_stage_0_6_action_ability_lifetime import configure
path=ROOT/'docs/performance/stage-0-6-current/small-operation-profile/read-view-epoch/repeat-comparison/repeat.py'
spec=importlib.util.spec_from_file_location('reviewed_runner',path);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
OUT.mkdir(exist_ok=False)
source,pair=ranked_fixture(SCRATCH,size=4,configure=configure)
manifest=dict(kind='raw-complete20-action-only',source_sha256=sha(source),commitment=pair[1].hex(),
 context=runner.machine(),trials=[],limit_seconds=90,
 limitation='Generated canonical20 proof fixture; action only, not a complete generated year or mature acceptance.')
record(OUT/'manifest.json',manifest)
saved=None
for name,label in [('pair1-baseline','baseline'),('pair1-candidate','candidate'),('pair2-candidate','candidate'),('pair2-baseline','baseline')]:
 root=ROOT if label=='candidate' else ROOT.parent/'action-retention-baseline'
 fence=runner.pinned_runtime_files(root)
 tree=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],cwd=root,text=True).strip()
 assert tree=={'candidate':'8cc642b2a95d47b6d874dfe5260dacbe18f52d43','baseline':'7347092a500a666710598fe4dcd31ae08d63848f'}[label]
 proc=None
 try:
  with (OUT/(name+'.log')).open('w') as log:
   proc=subprocess.Popen([sys.executable,__file__,str(source),str(OUT/name),pair[1].hex()],cwd=root,env=dict(os.environ,PYTHONPATH='.:simulation'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   assert proc.wait(timeout=90)==0, name
  report=json.loads((OUT/name/'report.json').read_text())
  assert report['source_sha256']==manifest['source_sha256'] and sha(source)==manifest['source_sha256']
  assert report['runtime_tree']==tree and runner.pinned_runtime_files(root)==fence
  if saved is None:saved=report['saved_digest']
  assert report['saved_digest']==saved
  manifest['trials'].append(dict(name=name,**report));record(OUT/'manifest.json',manifest)
  print(name,report['timing'],flush=True)
 except BaseException:
  runner.stop_group(proc);raise
manifest['status']='complete';record(OUT/'manifest.json',manifest)
