"""Exact-source local diagnostic controls; not performance acceptance."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/scratch/d88f8db353e8')
out=Path.cwd()/'docs/performance/stage-0-6-current/bounded-genesis'
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
code='''from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
import sys
copy_world_with_proofs(sys.argv[1],sys.argv[2],rules_id='stage-0-6-real-year-probe',rank_proofs=True)
'''
rows=[]
for source_name in ('bounded-genesis-year','baseline-generated-year'):
 source=root/source_name/'lazy.sqlite'
 for name,checkout in (('candidate',Path.cwd()),('baseline',root/'ate-baseline-7df')):
  label=name+'-'+source_name
  before=h(source);start=time.monotonic()
  destination=root/('failure-matrix-'+label+'.sqlite')
  cmd=[sys.executable,'-c',code,str(source),str(destination)]
  env=dict(os.environ,PYTHONPATH='.:simulation')
  p=subprocess.run(cmd,cwd=checkout,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
  (out/(label+'.log')).write_text(p.stdout)
  git=lambda *a:subprocess.check_output(['git',*a],cwd=checkout,text=True).strip()
  row=dict(label=label,command=cmd,cwd=str(checkout),environment=dict(PYTHONPATH='.:simulation'),
    head=git('rev-parse','HEAD'),runtime_tree=git('rev-parse','HEAD:simulation/ate_sim'),
    tracked_clean=not git('status','--porcelain','--untracked-files=no'),
    driver_sha256=h(checkout/'.github/tests/run_proof_real_year_probe.py'),
    source=dict(path=str(source),bytes=source.stat().st_size,before_sha256=before,after_sha256=h(source)),
    returncode=p.returncode,wall_seconds=time.monotonic()-start,log=label+'.log')
  assert row['source']['before_sha256']==row['source']['after_sha256']
  rows.append(row);print(json.dumps(row),flush=True)
(out/'local-failure-matrix.json').write_text(json.dumps(rows,indent=2)+'\n')
