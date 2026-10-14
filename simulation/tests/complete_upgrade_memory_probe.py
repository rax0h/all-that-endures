import gc,json,resource,tempfile,time,sys,importlib
from pathlib import Path
from ate_sim.core import World,Person,Event,Layer
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy,open_lazy_world_session
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
n=int(sys.argv[1]);started=time.perf_counter()
def stats(phase):
 p={line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
 print(json.dumps({'phase':phase,'rss':p['VmRSS'],'vms':p['VmSize'],'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'seconds':time.perf_counter()-started}),flush=True)
for modname,names in [('persistence_catalog_copy',['_owner_sources','initial_catalog_delta','_verify_catalog']),('persistence_event_copy_normalization',['capture_bodies','normalize_events'])]:
 mod=importlib.import_module('ate_sim.'+modname)
 for name in names:
  orig=getattr(mod,name)
  def wrapped(*a,_orig=orig,_name=name,**kw):
   stats(_name+'_start');result=_orig(*a,**kw);stats(_name+'_end');return result
  setattr(mod,name,wrapped)
mod=importlib.import_module('ate_sim.persistence_catalog_copy');mod._copy_phase=lambda phase,path:stats(phase)
with tempfile.TemporaryDirectory() as d:
 p=Path(d);world=World(843000)
 for i in range(1,n+1):
  world.people[i]=Person(i,0,1,1)
  world.events.append(Event(i,0,'probe',Layer.SOCIETY,data={'a':[i,i+1],'b':{'v':i}}))
 world.next_person=n+1;world.next_event=n+1;world.event_ids.update(range(1,n+1))
 expected=world.digest();write_cold_snapshot(world,p/'cold.sqlite',rules_id='probe')
 del world;gc.collect()
 convert_cold_to_lazy(p/'cold.sqlite',p/'lazy.sqlite',rules_id='probe',native_graph_buckets=True)
 gc.collect();stats('ready')
 upgrade_lazy_snapshot(p/'lazy.sqlite',p/'complete.sqlite',rules_id='probe')
 stats('published')
 with open_lazy_world_session(p/'complete.sqlite',rules_id='probe') as s:assert s.detach(materialize_history=True).digest()==expected
 stats('digest_verified')
