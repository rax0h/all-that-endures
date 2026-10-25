"""Selected target incoming body semantics; no native admission."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_target_incoming_fixtures import make_incoming_store
from simulation.tests.proof_owner_target_fixtures import PAGE
from ate_sim.persistence_proof_target_incoming import read_target_incoming

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):
  self.steps+=1
  return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_target_incoming_fixtures.py').read_bytes()).hexdigest(),owner_fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_owner_target_fixtures.py').read_bytes()).hexdigest(),target_fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_target_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a=make_incoming_store(output/f'group-{n}.sqlite',archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');counts={'unrelated_payload':0,'selected_metadata':0}
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'payload' in t and 'then 1 else 0 end' not in t:counts['unrelated_payload' if "namespace='archive'" in t or 'namespace=' not in t else 'selected_metadata']+=1
   s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
   try:r=read_target_incoming(s,p,ref,*a,max_members=3);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert r.target.kind=='list' and r.target.descriptor==('list',0,0) and len(r.group.occurrences)==3 and len(r.group.links)==2
   paths=[(o.namespace,s.codec.decode(o.typed_key),tuple(s.codec.decode(v) for v in o.paths)) for o in r.owners]
   assert paths==[(PAGE,(3,0),((('index',0),),(('index',1),))),('world.people',1,((('key','pointer'),),))]
   assert r.owners[0].source.payload==s.codec.encode((ref,ref))
   # Exact interval-one VM guard is a separate untimed diagnostic. Latency
   # above includes SQL tracing/allocation tracking, but not per-opcode callbacks.
   vm=_VMWorkBudget(1000000);s.db.set_progress_handler(vm,1)
   try:checked=read_target_incoming(s,p,ref,*a,max_members=3)
   finally:s.db.set_progress_handler(None,0)
   assert checked==r and vm.steps<=vm.limit
   assert counts['unrelated_payload']==0 and counts['selected_metadata']<=96 and peak<2*1024*1024 and s._payload_reads==0
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,join_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,vm_measurement='untimed interval-one guarded replay',sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero archive bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
