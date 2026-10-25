"""Bounded sequence/Event-ID reads amid unrelated physical internal parents."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3,re
from pathlib import Path
from simulation.tests.proof_sequence_event_fixtures import make_store
from ate_sim.persistence_lazy_sequence import PARENT_NAMESPACE
from ate_sim.persistence_lazy_nested_history import HistoryReference
from ate_sim.persistence_proof_child_extents import read_target_members

class _VMWorkBudget:
 def __init__(self,limit):self.limit,self.steps=limit,0
 def __call__(self):
  self.steps+=1
  return int(self.steps>self.limit)

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 files={'driver_sha256':Path(__file__),'fixture_sha256':Path('simulation/tests/proof_sequence_event_fixtures.py')}
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),sqlite=sqlite3.sqlite_version,**{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()})
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a,ra=make_store(output/f'extent-{n}.sqlite',kind='exceptions',removed=(1,4),added=(True,9.0,'x'),archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');selected=s.codec.encode((3,1)).hex();operations={}
   for label,reference,want in (('event-ids',ref,(2,3,5,True,9.0,'x')),('sequence',HistoryReference('sequence',3),(1,4))):
    counts={'unrelated_internal_payload':0,'selected_metadata':0}
    def trace(sql):
     t=sql.lower()
     if t.startswith('select') and 'from lazy_record_versions' in t and 'then payload end' in t:
      match=re.search("typed_key=x'([0-9a-f]+)'",t)
      unrelated='namespace=' not in t or (f"namespace='{PARENT_NAMESPACE}'" in t and (match is None or match[1]!=selected))
      counts['unrelated_internal_payload' if unrelated else 'selected_metadata']+=1
    s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
    try:r=read_target_members(s,p,reference,*a);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();s.db.set_trace_callback(None)
    assert r.members==want and tuple(type(v) for v in r.members)==tuple(type(v) for v in want)
    assert tuple(c.target.kind for c in r.components)==(('sequence','set') if label=='event-ids' else ())
    vm=_VMWorkBudget(1000000);s.db.set_progress_handler(vm,1)
    try:checked=read_target_members(s,p,reference,*a)
    finally:s.db.set_progress_handler(None,0)
    assert checked==r and vm.steps<=vm.limit
    assert counts['unrelated_internal_payload']==0 and counts['selected_metadata']<=128 and peak<2*1024*1024 and s._payload_reads==0
    operations[label]=dict(extent_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,sql=counts)
   assert len(a[1][0].roots)==6 and a[1][0].roots[5].count==n+1
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,operations=operations,vm_measurement='untimed interval-one guarded replay')
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,{k:round(v['extent_ms'],2) for k,v in operations.items()},'ms; zero unrelated internal bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
