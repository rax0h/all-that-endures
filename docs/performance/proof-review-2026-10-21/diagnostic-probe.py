"""Disposable current-runtime diagnostic; not a mature performance benchmark."""
import cProfile, json, pathlib, pstats, signal, time
from collections import Counter
from dataclasses import asdict
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy_store import LazyRecordStore
from simulation.profile_stage_0_5_performance import _runtime_identity
out=pathlib.Path('/workspace/scratch/7905b656a1e1/proof-review-probe')
result={'schema':'ate-architecture-diagnostic/1','runtime':_runtime_identity(),'fixture':{'seed':843000,'mature_initialization':True,'source_year':0},'phases':{},'profiled':True,'budget_seconds':180}
def flush(): (out/'result.json').write_text(json.dumps(result,indent=2))
def expired(*_): raise TimeoutError('diagnostic 180-second budget')
signal.signal(signal.SIGALRM,expired);signal.alarm(180)
ns=Counter(); read=LazyRecordStore.read_version
# Counts read_version requests, not all IO or distinct keys.
def traced(self,pin,namespace,key,**kw):
 ns[namespace]+=1
 return read(self,pin,namespace,key,**kw)
LazyRecordStore.read_version=traced
session=None
try:
 w=generate_world(843000,mature=True)
 result['fixture'].update(people=len(w.people),events=len(w.events),actions=len(w.agency.actions))
 t=time.perf_counter()
 write_cold_snapshot(w,out/'cold.sqlite',rules_id='proof-review-diagnostic')
 convert_cold_to_lazy(out/'cold.sqlite',out/'legacy.sqlite',rules_id='proof-review-diagnostic',native_graph_buckets=True)
 upgrade_lazy_snapshot(out/'legacy.sqlite',out/'complete.sqlite',rules_id='proof-review-diagnostic')
 result['fixture']['construction_seconds']=time.perf_counter()-t
 result['fixture']['database_bytes']=(out/'complete.sqlite').stat().st_size
 print('fixture ready',result['fixture'],flush=True)
 def measure(name,fn):
  global session
  ns.clear()
  if session: session.store.reset_diagnostics()
  p=cProfile.Profile();t=time.perf_counter();row={'status':'incomplete'};result['phases'][name]=row
  p.enable()
  try:
   value=fn()
   if name=='open':session=value
   row['status']='complete'
   return value
  finally:
   p.disable(); row['profiled_wall_seconds']=time.perf_counter()-t
   st=pstats.Stats(p)
   rows=[{'file':pathlib.Path(k[0]).name,'line':k[1],'function':k[2],'primitive_calls':v[0],'calls':v[1],'self_seconds':v[2],'inclusive_seconds':v[3]} for k,v in st.stats.items()]
   row['top_inclusive']=sorted(rows,key=lambda x:x['inclusive_seconds'],reverse=True)[:45]
   row['top_self']=sorted(rows,key=lambda x:x['self_seconds'],reverse=True)[:20]
   row['read_version_requests_by_namespace']=dict(ns.most_common())
   if session:row['io']=asdict(session.store.diagnostics())
   p.dump_stats(str(out/(name+'.prof')));flush();print(name,row['status'],row['profiled_wall_seconds'],flush=True)
 measure('open',lambda:open_lazy_world_session(out/'complete.sqlite',rules_id='proof-review-diagnostic'))
 measure('first_step',lambda:Simulation(session.world).step())
 measure('save',session.save)
 measure('warm_step',lambda:Simulation(session.world).step())
 result['status']='complete'
except Exception as e:
 result['status']='incomplete';result['error']=repr(e);print(repr(e),flush=True)
finally:
 signal.alarm(0)
 if session:session.close()
 flush()
