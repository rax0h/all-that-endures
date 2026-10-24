"""Audited complete collection directory; bounded reads amid growing archive.

Two declared lazy namespaces, N archive members. This measures archive growth,
not large namespace fanout or World open/save/year.
"""
import argparse,json,time,tracemalloc,subprocess,hashlib,sqlite3
from pathlib import Path
from simulation.tests.proof_scope_fixtures import make_scope_store
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory,read_collection_namespaces,read_collection_namespace

def git(*a):return subprocess.check_output(['git',*a],text=True).strip()
def run(output):
 output.mkdir(parents=True,exist_ok=False)
 if git('status','--porcelain','--untracked-files=no'):raise ValueError('dirty tracked source')
 source=dict(head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(Path('simulation/tests/proof_scope_fixtures.py').read_bytes()).hexdigest(),sqlite=sqlite3.sqlite_version)
 (output/'source.json').write_text(json.dumps(dict(source=source)))
 results=[]
 for n in (1000,10000,100000):
  start=time.perf_counter();s,p,_=make_scope_store(output/f'd-{n}.sqlite',n,bootstrap=False)
  try:
   a=bootstrap_collection_directory(s,p);construction=time.perf_counter()-start;assert a[0].root.count==2
   s.db.execute('PRAGMA cache_size=-2048');s.db.execute('PRAGMA temp_store=FILE');s.db.execute('PRAGMA temp.cache_size=-2048')
   counts={'payload':0,'namespace':0};steps=[0]
   def trace(sql):
    t=sql.lower()
    if t.startswith('select') and 'payload' in t and 'sqlite_schema' not in t:counts['payload']+=1
    if t.startswith('select') and 'from lazy_namespace_state' in t:counts['namespace']+=1
   def progress():steps[0]+=100;return 0
   s.reset_diagnostics();s.db.set_trace_callback(trace);s.db.set_progress_handler(progress,100);tracemalloc.start();start=time.perf_counter()
   try:
    page=read_collection_namespaces(s,p,*a,limit=1);selected=read_collection_namespace(s,p,*a,'people');absent=read_collection_namespace(s,p,*a,'missing')
    seconds=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory()
   finally:tracemalloc.stop();s.db.set_trace_callback(None);s.db.set_progress_handler(None,0)
   assert page.entries[0][0].namespace=='archive' and page.entries[0][0].member_count==n and page.next_after==b'archive'
   assert selected[0].namespace=='people' and selected[0].member_count==1 and absent is None
   assert counts=={'payload':0,'namespace':3} and steps[0]+99<50000 and peak<2*1024*1024 and s._payload_reads==s._payload_check_reads==0
   row=dict(size=n,source=source,exact=True,status='complete',namespace_count=2,construction_seconds=construction,page_and_two_lookups_ms=seconds*1000,python_peak_bytes=peak,sqlite_vm_step_upper_bound=steps[0]+99,sql=counts)
   results.append(row);(output/f'size-{n}.json').write_text(json.dumps(row,indent=2));print(n,round(seconds*1000,2),'ms; zero body reads',flush=True)
  finally:s.close()
 (output/'summary.json').write_text(json.dumps(dict(status='complete',source=source,results=results),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
