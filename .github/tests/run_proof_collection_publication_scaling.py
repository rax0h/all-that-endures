"""Actual unified order successor saves, full construction outside timer."""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_publication_fixtures import make_publication_store,metadata
from ate_sim.persistence_proof_collection import bootstrap_collection,read_collection_page
from ate_sim.persistence_proof_collection_publish import commit_collections
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_proof_publication import read_version_content_bytes

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_publication_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)))
 results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,a=make_publication_store(output/f'o-{n}.sqlite',n)
  try:
   c=bootstrap_collection(s,p,'archive');old=s.capture_pin();construction=time.perf_counter()-start
   s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048')
   counts={'unrelated_payload':0,'selected_payload':0};steps=[0];literal="typed_key=x'"+s.codec.encode(0).hex()+"'"
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'from lazy_record_versions' in t and 'payload' in t and 'then 1 else 0 end' not in t:
     counts['selected_payload' if "namespace='archive'" in t and literal in t else 'unrelated_payload']+=1
   def progress():steps[0]+=100;return 0
   s.reset_diagnostics();s.db.set_trace_callback(trace);s.db.set_progress_handler(progress,100);tracemalloc.start();start=time.perf_counter()
   try:
    r=commit_collections(s,p,(c,),*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='order',version_changes=(VersionChange('archive',0,{'old':0},reinsertion=True),),identity_changes=(),changes=(),new_segments=(),metadata=metadata(2),preparation_budget=(1,1))
    seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert counts['unrelated_payload']==0 and 1<=counts['selected_payload']<=8 and peak<2*1024*1024 and steps[0]+99<150000 and s._payload_reads==0
   assert r.content.commit.outcome=='committed' and r.collections[0][0].member_count==n and r.collections[0][0].next_ordinal==n+1
   assert read_collection_page(s,old,*c,limit=3).positions==tuple((s.codec.encode(i),i) for i in range(3))
   assert read_collection_page(s,r.content.commit.pin,*r.collections[0],after=(n-1,s.codec.encode(n-1))).positions==((s.codec.encode(0),n),)
   raw=read_version_content_bytes(s,r.content.commit.pin,r.content.certificate,r.content.commitment,'archive',s.codec.encode(0),expected_record_schema=1)
   assert raw.payload==s.codec.encode({'old':0})
   row=dict(size=n,source=source,exact=True,status='complete',construction_seconds=construction,save_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps[0]+99,sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero unrelated bodies',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
