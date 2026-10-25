"""Bounded backing and complete incoming group metadata; no native admission."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_owner_target_fixtures import make_owner_target_store,PAGE
from ate_sim.persistence_proof_target_group import read_target_group

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):
  self.steps+=1
  return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_owner_target_fixtures.py').read_bytes()).hexdigest(),target_fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_target_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a=make_owner_target_store(output/f'group-{n}.sqlite',archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');counts={'unrelated_payload':0,'selected_metadata':0}
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'payload' in t and 'then 1 else 0 end' not in t:counts['unrelated_payload' if "namespace='archive'" in t or 'namespace=' not in t else 'selected_metadata']+=1
   s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
   try:r=read_target_group(s,p,ref,*a,max_members=3);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert r.target.kind=='list' and r.target.descriptor==('list',0,0) and r.group.incarnation_id==2 and not r.group.retired
   rows=[(x.namespace,s.codec.decode(x.typed_key),s.codec.decode(x.path),x.incarnation_id) for x in r.group.occurrences]
   assert rows==[(PAGE,(3,0),(('index',0),),2),(PAGE,(3,0),(('index',1),),2),('world.people',1,(('key','pointer'),),2)]
   anchor=(('field','people'),('key',1),('key','pointer'))
   assert s.codec.decode(r.group.anchor)==anchor and [(s.codec.decode(x),s.codec.decode(y)) for x,y in r.group.links]==[((('key',PAGE),('key',(3,0)),('index',0)),anchor),((('key',PAGE),('key',(3,0)),('index',1)),anchor)]
   # Exact interval-one VM guard is a separate untimed diagnostic. Latency
   # above includes SQL tracing/allocation tracking, but not per-opcode callbacks.
   vm=_VMWorkBudget(1000000);s.db.set_progress_handler(vm,1)
   try:checked=read_target_group(s,p,ref,*a,max_members=3)
   finally:s.db.set_progress_handler(None,0)
   assert checked==r and vm.steps<=vm.limit
   assert counts['unrelated_payload']==0 and counts['selected_metadata']<=64 and peak<2*1024*1024 and s._payload_reads==0
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,join_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,vm_measurement='untimed interval-one guarded replay',sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero archive bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
