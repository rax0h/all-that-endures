"""One raw owner's complete direct references and targets; no World admission."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_owner_target_fixtures import make_owner_target_store,PAGE
from ate_sim.persistence_proof_owner_targets import read_owner_targets

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_owner_target_fixtures.py').read_bytes()).hexdigest(),target_fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_target_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a=make_owner_target_store(output/f'join-{n}.sqlite',archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');counts={'unrelated_payload':0,'selected_metadata':0};steps=[0]
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'payload' in t and 'then 1 else 0 end' not in t:counts['unrelated_payload' if "namespace='archive'" in t or 'namespace=' not in t else 'selected_metadata']+=1
   def progress():steps[0]+=100;return 0
   s.reset_diagnostics();s.db.set_trace_callback(trace);s.db.set_progress_handler(progress,100);tracemalloc.start();start=time.perf_counter()
   try:r=read_owner_targets(s,p,PAGE,s.codec.encode((3,0)),*a);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert len(r.references)==2 and [v for _,v in r.references]==[2,2] and len(r.targets)==1 and r.targets[0].descriptor==('list',0,0)
   assert counts['unrelated_payload']==0 and counts['selected_metadata']<=32 and peak<2*1024*1024 and steps[0]+99<300000 and s._payload_reads==0
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,join_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps[0]+99,sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero archive bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
