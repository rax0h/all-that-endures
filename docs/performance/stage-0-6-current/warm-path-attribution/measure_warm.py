"""Profile the second parent-process annual step; unchanged state-checked driver."""
import cProfile,json,pstats,runpy,sys
from pathlib import Path
root=Path.cwd().resolve();sys.path[:0]=[str(root),str(root/'simulation')]
from ate_sim.engine import Simulation
output=Path(sys.argv[2]).resolve();original=Simulation.run;calls=0

def measured(self,*args,**kwargs):
    global calls
    calls+=1
    if calls!=2:return original(self,*args,**kwargs)
    profile=cProfile.Profile();profile.enable()
    try:return original(self,*args,**kwargs)
    finally:
        profile.disable()
        rows=[dict(file=f,line=line,function=name,calls=v[1],primitive_calls=v[0],own_seconds=v[2],cumulative_seconds=v[3],callers=[dict(caller=list(k),data=list(c) if isinstance(c,tuple) else c) for k,c in v[4].items()]) for (f,line,name),v in pstats.Stats(profile).stats.items()]
        (output/'warm-calls.json').write_text(json.dumps(rows,indent=2)+'\n')
Simulation.run=measured
try:
    driver=root/'docs/performance/stage-0-6-current/small-operation-profile/factorization/compare.py';sys.argv[0]=str(driver);runpy.run_path(str(driver),run_name='__main__')
finally:
    Simulation.run=original
    if (output/'report.json').exists():
        report=json.loads((output/'report.json').read_text());report.update(kind='instrumented-current-warm-path-attribution',limitation='Second Simulation.run wrapped for profiling only; not raw latency acceptance');(output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
