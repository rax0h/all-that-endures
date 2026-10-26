"""Explicit World genesis construction versus bounded checkpoint publication.

History values are retained in a real complete-format shared history. This is
checkpoint reuse evidence, not an interactive point-edit or mature timing claim.
"""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_world_fixtures import make_world
from simulation.tests.test_stage_0_5_final_catalog_copy import opened,RULES
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_proof_manifest_publish import commit_world_manifest,resolve_world_manifest
from ate_sim.persistence_proof_generation import read_generation_manifest

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):
  self.steps+=1
  return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 files={'driver_sha256':Path(__file__),'fixture_sha256':Path('simulation/tests/proof_world_fixtures.py'),'complete_fixture_sha256':Path('simulation/tests/test_stage_0_5_final_complete_format.py'),'authority_fixture_sha256':Path('simulation/tests/test_stage_0_5_final_catalog_copy.py')}
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),sqlite=sqlite3.sqlite_version,**{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()})
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,a,ra,d=make_world(output/f'source-{n}',size=n);path=s.path;s.release_pin(p);s.close()
  candidate=output/f'world-{n}.sqlite';genesis=copy_world_with_proofs(path,candidate,rules_id=RULES);construction=time.perf_counter()-start
  s=opened(candidate);p=s.capture_pin();counts={'history_body':0,'commit_descriptor_body':0};vm=_VMWorkBudget(2000000)
  try:
   s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048')
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and ('from records' in t or 'from lazy_record_versions' in t) and ('then payload end' in t or 'select payload' in t):
     counts['commit_descriptor_body' if "namespace='world_event_storage'" in t else 'history_body']+=1
   s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
   try:r=commit_world_manifest(s,p,genesis.manifest,genesis.commitment,commit_token='a'*32,checkpoint=True,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata());elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None)
   assert r.commit.outcome=='committed' and not r.reaudited and counts['history_body']==0 and peak<4*1048576
   assert r.manifest[0].roots[2:]==genesis.manifest.roots[2:]
   s.db.set_progress_handler(vm,1)
   try:
    again=commit_world_manifest(s,r.commit.pin,*r.manifest,commit_token='b'*32,checkpoint=True,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
   finally:s.db.set_progress_handler(None,0)
   assert not again.reaudited and vm.steps<=vm.limit
   assert read_generation_manifest(s,again.commit.pin,again.manifest[1])==again.manifest[0]
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,checkpoint_ms=elapsed*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,sql=counts,reaudited=False,archive_unit='retained history values',vm_measurement='separate interval-one guarded checkpoint')
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(elapsed*1000,2),'ms checkpoint; zero history bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
