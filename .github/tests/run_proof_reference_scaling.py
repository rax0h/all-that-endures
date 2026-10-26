"""Durable selected-graph reuse during real atomic publication, fixed graph."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_reference_closure_fixtures import make_graph
from ate_sim.persistence_lazy_sequence import PARENT_NAMESPACE
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_proof_reference import bootstrap_reference_proofs,read_reference_certificate
from ate_sim.persistence_proof_reference_publish import commit_reference_proofs
from ate_sim.persistence_proof_directory_publish import _load as directory_root

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
  start=time.perf_counter();s,p,ref,a,ra=make_graph(output/f'reference-{n}.sqlite',archive=n)
  try:
   pair=bootstrap_reference_proofs(s,p,(ref,),*a,record_authority=ra);d=directory_root(s,p.captured_head)[0];construction=time.perf_counter()-start
   s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048')
   counts={'graph_payload':0,'unrelated_archive_payload':0,'changed_payload':0,'proof_nodes':0}
   key=s.codec.encode((n+99,1)).hex()
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and ('from ate_proof_nodes' in t or 'from main.ate_proof_nodes' in t):counts['proof_nodes']+=1
    if t.startswith('select') and 'from lazy_record_versions' in t and 'then payload end' in t:
     if f"namespace='{PARENT_NAMESPACE}'" in t:
      counts['changed_payload' if f"typed_key=x'{key}'" in t else 'unrelated_archive_payload']+=1
     else:counts['graph_payload']+=1
   s.reset_diagnostics();s.db.set_trace_callback(trace);tracemalloc.start();start=time.perf_counter()
   try:
    result=commit_reference_proofs(s,p,*pair,d,a[0],a[2],scope_authority=a[1],record_authority=ra,commit_token='reuse-edit',namespaces=(PARENT_NAMESPACE,),version_changes=(VersionChange(PARENT_NAMESPACE,(n+99,1),(None,1)),),changes=(),new_segments=(),metadata=s.head_metadata())
    elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None)
   assert result.inventory.content.commit.outcome=='committed' and result.rebuilt==() and result.reused==(('list',2),) and result.reference[0].root==pair[0].root
   assert counts['graph_payload']==counts['unrelated_archive_payload']==0 and 1<=counts['changed_payload']<=8 and peak<4*1024*1024
   v=result.inventory.content;pin=v.commit.pin;ra2=(v.scope.record.certificate,v.scope.record.commitment);ca2=(v.certificate,v.commitment);sa2=(v.scope.certificate,v.scope.commitment)
   vm=_VMWorkBudget(2000000);s.db.set_progress_handler(vm,1);before=s._payload_check_reads;start=time.perf_counter()
   try:
    meta=commit_reference_proofs(s,pin,*result.reference,result.inventory.directory,ca2,result.inventory.inventory,scope_authority=sa2,record_authority=ra2,commit_token='metadata-reuse',namespaces=(),version_changes=(),changes=(),new_segments=(),metadata=dict(s.head_metadata(),simulation_position=3))
   finally:s.db.set_progress_handler(None,0)
   assert s._payload_check_reads==before and meta.rebuilt==() and meta.reference[0].root==pair[0].root and vm.steps<=vm.limit
   fact=read_reference_certificate(s,meta.inventory.content.commit.pin,*meta.reference,ref)
   assert (fact.targets,fact.edges)==(2,2)
   row=dict(size=n,source=source,status='complete',exact=True,construction_seconds=construction,point_edit_ms=elapsed*1000,python_peak_bytes=peak,sql=counts,metadata_reuse_vm_steps=vm.steps,rebuilt=0,reused=1,vm_measurement='interval-one guarded metadata-only successor')
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(elapsed*1000,2),'ms; graph reused, zero graph/unrelated bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
