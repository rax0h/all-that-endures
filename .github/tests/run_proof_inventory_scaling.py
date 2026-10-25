"""Unified mixed inventory save at fixed namespace count, growing archive.

Construction/audit outside timer. No World or namespace-fanout timing claim.
"""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_publication_fixtures import make_publication_store,metadata
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from ate_sim.persistence_proof_inventory import bootstrap_inventory,commit_inventory,read_inventory_namespace
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.incremental_store import RecordChange,NewSegment
from ate_sim.persistence_proof_publication import read_version_content_bytes

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_publication_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)));results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,a=make_publication_store(output/f'i-{n}.sqlite',n)
  try:
   d=bootstrap_collection_directory(s,p);i=bootstrap_inventory(s,p);old=s.capture_pin();construction=time.perf_counter()-start
   s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048')
   counts={'unrelated_payload':0,'selected_payload':0};steps=[0];literal="typed_key=x'"+s.codec.encode(n).hex()+"'"
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'payload' in t and 'then 1 else 0 end' not in t:
     counts['selected_payload' if "namespace='archive'" in t and literal in t else 'unrelated_payload']+=1
   def progress():steps[0]+=100;return 0
   s.reset_diagnostics();s.db.set_trace_callback(trace);s.db.set_progress_handler(progress,100);tracemalloc.start();start=time.perf_counter()
   try:
    r=commit_inventory(s,p,*i,d,a.content,namespaces=('archive',),scope_authority=a.scope,record_authority=a.record,commit_token='inventory',version_changes=(VersionChange('archive',n,{'old':n}),),identity_changes=(),changes=(RecordChange('ordinary',1,{'new':1}),),new_segments=(NewSegment('events',n+1,[n+1],element_count=1,first_id=n+1,last_id=n+1),),metadata=metadata(2),preparation_budget=(1,1))
    seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert counts['unrelated_payload']==0 and counts['selected_payload']<=8 and steps[0]+99<250000 and peak<2*1024*1024 and s._payload_reads==0
   assert r.content.commit.outcome=='committed'
   assert read_inventory_namespace(s,old,*i,'archive')==('archive',n,0)
   for ns,pair in [('archive',(n+1,0)),('ordinary',(2,0)),('events',(0,n+2))]:assert read_inventory_namespace(s,r.content.commit.pin,*r.inventory,ns)==(ns,*pair)
   raw=read_version_content_bytes(s,r.content.commit.pin,r.content.certificate,r.content.commitment,'archive',s.codec.encode(n),expected_record_schema=1);assert raw.payload==s.codec.encode({'old':n})
   row=dict(size=n,source=source,exact=True,status='complete',namespace_count=4,construction_seconds=construction,save_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps[0]+99,sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero unrelated bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
