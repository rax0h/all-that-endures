"""Frozen/fixed raw extents amid unrelated physical child parents."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3,re
from pathlib import Path
from simulation.tests.proof_frozen_extent_fixtures import make_frozen_store
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
from ate_sim.persistence_record_headers import RecordReference,NAMESPACE as RECORDS
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference,NAMESPACE as NAN,TAG
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
 files={'driver_sha256':Path(__file__),'fixture_sha256':Path('simulation/tests/proof_frozen_extent_fixtures.py'),'target_fixture_sha256':Path('simulation/tests/proof_target_fixtures.py'),'child_fixture_sha256':Path('simulation/tests/proof_child_extent_fixtures.py')}
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),sqlite=sqlite3.sqlite_version,**{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()})
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 record,nan=RecordReference(3),NonreflexiveKeyReference(4)
 record_header=('recursive-record/v1','core.LocalState/v1',(1,2,3,4),None);nan_header=(TAG,bytes.fromhex('7ff8000000000042'))
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,ref,a,ra=make_frozen_store(output/f'extent-{n}.sqlite',values=(record,nan,nan),certified=False,dependencies=((record,record_header),(nan,nan_header)),archive=n)
  try:
   construction=time.perf_counter()-start;s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048');selected=s.codec.encode((2,0)).hex();operations={}
   for label,reference,want,locators in (
    ('frozen-list',ref,(record,nan,nan),((PAGE_NAMESPACE,(2,0)),)),
    ('record',record,(('rain',1),('drought',2),('flood',3),('scarcity',4)),((RECORDS,(3,0)),)),
    ('nan-key',nan,(),((NAN,(4,0)),)),
   ):
    counts={'unrelated_child_payload':0,'selected_metadata':0}
    def trace(sql):
     t=sql.lower()
     if t.startswith('select') and 'from lazy_record_versions' in t and 'then payload end' in t:
      match=re.search("typed_key=x'([0-9a-f]+)'",t)
      unrelated='namespace=' not in t or "namespace='archive'" in t or (f"namespace='{PAGE_NAMESPACE}'" in t and (match is None or match[1]!=selected))
      counts['unrelated_child_payload' if unrelated else 'selected_metadata']+=1
    s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
    try:r=read_target_members(s,p,reference,*a);seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop();s.db.set_trace_callback(None)
    assert r.members==want and r.child_locators==locators
    assert (len(r.certification_targets)==1 and r.certification_targets[0].incarnation==4) if label=='frozen-list' else not r.certification_targets
    vm=_VMWorkBudget(1000000);s.db.set_progress_handler(vm,1)
    try:checked=read_target_members(s,p,reference,*a)
    finally:s.db.set_progress_handler(None,0)
    assert checked==r and vm.steps<=vm.limit
    assert counts['unrelated_child_payload']==0 and counts['selected_metadata']<=96 and peak<2*1024*1024 and s._payload_reads==0
    operations[label]=dict(extent_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_steps=vm.steps,sql=counts)
   assert len(a[1][0].roots)==5 and a[1][0].roots[4].count==n+3
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,operations=operations,vm_measurement='untimed interval-one guarded replay')
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,{k:round(v['extent_ms'],2) for k,v in operations.items()},'ms; zero unrelated child bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
