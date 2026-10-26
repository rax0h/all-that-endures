"""Fixed reachable graph against growing unrelated physical internal parents."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_reference_closure_fixtures import make_graph
from ate_sim.persistence_lazy_sequence import PARENT_NAMESPACE
from ate_sim.persistence_proof_reference_closure import read_reference_closure

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):
  self.steps+=1
  return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 files={'driver_sha256':Path(__file__),'fixture_sha256':Path('simulation/tests/proof_reference_closure_fixtures.py'),'authority_fixture_sha256':Path('simulation/tests/proof_sequence_event_fixtures.py')}
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),sqlite=sqlite3.sqlite_version,**{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()})
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a,ra=make_graph(output/f'closure-{n}.sqlite',archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');counts={'unrelated_internal_payload':0,'selected_metadata':0}
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'then payload end' in t:
     unrelated='namespace=' not in t or f"namespace='{PARENT_NAMESPACE}'" in t
     counts['unrelated_internal_payload' if unrelated else 'selected_metadata']+=1
   s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
   try:r=read_reference_closure(s,p,ref,*a);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None)
   assert tuple(node.incoming.target.incarnation for node in r.targets)==(2,3) and len(r.edges)==2 and r.targets[1].members==(7,) and r.immutable_targets==()
   vm=_VMWorkBudget(1000000);s.db.set_progress_handler(vm,1)
   try:checked=read_reference_closure(s,p,ref,*a)
   finally:s.db.set_progress_handler(None,0)
   assert checked==r and vm.steps<=vm.limit
   assert counts['unrelated_internal_payload']==0 and counts['selected_metadata']<=128 and peak<2*1024*1024 and s._payload_reads==0
   assert len(a[1][0].roots)==6 and a[1][0].roots[5].count==n
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,closure_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,sql=counts,vm_measurement='untimed interval-one guarded replay')
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero unrelated internal bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
