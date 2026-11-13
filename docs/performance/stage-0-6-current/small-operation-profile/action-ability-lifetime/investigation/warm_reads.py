"""Small disposable diagnostic: quantify repeated physical proof work; no cache."""
import collections, hashlib, json, platform, sqlite3, _sqlite3, sys, subprocess, weakref
from pathlib import Path
ROOT=Path('/workspace/scratch/d88f8db353e8/ate')
sys.path[:0]=[str(ROOT), str(ROOT/'simulation')]
OUT=Path('/workspace/scratch/72797495b7a4/continuation-diagnostics')
expected=json.loads((ROOT/'docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
db=sqlite3.connect(':memory:')
observed=dict(python=sys.version, compiler=platform.python_compiler(), sqlite=sqlite3.sqlite_version,
 sqlite_source_id=db.execute('select sqlite_source_id()').fetchone()[0],
 sqlite_compile_options=sorted(x[0] for x in db.execute('pragma compile_options')),
 executable_sha256=sha(sys.executable),system_python_sha256=sha('/usr/bin/python3.13'),
 sqlite_extension_sha256=sha(_sqlite3.__file__),
 loaded_sqlite_libraries=[dict(path=p,sha256=sha(p)) for p in sorted({x.split()[-1] for x in Path('/proc/self/maps').read_text().splitlines() if 'libsqlite3.so' in x})])
db.close()
assert all(observed[k]==expected[k] for k in observed),observed
(OUT/'runtime.json').write_text(json.dumps(observed,indent=2)+'\n')
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_store import ProofNodeStore
from ate_sim.persistence_lazy_identity_catalog import IdentityCatalog
from ate_sim.persistence_proof_world_session import open_proof_world_session
from ate_sim.engine import Simulation
from simulation.stage_0_6_genesis_stages import Recorder
from simulation import stage_0_6_genesis_checkpoint as c
from dataclasses import asdict
import shutil
info=json.loads((ROOT/'docs/performance/stage-0-6-current/small-operation-profile/input.json').read_text())
source=ROOT.parent/'small-proof-profile/source.sqlite/candidate.sqlite'
c.verify_database(source,info['database'])
work=OUT/'working.sqlite'; shutil.copyfile(source,work)
phase='open';store=None;reads=collections.Counter();scope_reads=collections.Counter();gets=collections.Counter();owner=collections.Counter();scope_ids=weakref.WeakKeyDictionary()
original_read=ProofNodeStore._read_bound_bytes
original_get=ProofMap.get
original_owner=IdentityCatalog.read_owner_identity

def scope_tag():
 scope=getattr(store,'_validation_scope',None)
 if scope is None:return 'none'
 if scope not in scope_ids:scope_ids[scope]=len(scope_ids)+1+scope_tag.serial;scope_tag.serial+=1
 return str(scope_ids[scope])
scope_tag.serial=0

def read(self,domain,digest):
 tag=scope_tag();reads[(phase,domain,digest)]+=1;scope_reads[(phase,tag,domain,digest)]+=1
 return original_read(self,domain,digest)
def get(self,root,key):
 gets[(phase,self.map_domain)]+=1
 return original_get(self,root,key)
def own(self,pin,owner_key,**kwargs):
 before=(self._owner_cache_hits,self._owner_cache_misses)
 standalone=not self.store.db.in_transaction
 result=original_owner(self,pin,owner_key,**kwargs)
 owner[(phase,'standalone' if standalone else 'nested','hit' if self._owner_cache_hits>before[0] else 'miss',owner_key[0])]+=1
 return result
ProofNodeStore._read_bound_bytes=read;ProofMap.get=get;IdentityCatalog.read_owner_identity=own
rec=Recorder(OUT/'phases',dict(open=60,first_step=120,save=120,warm_step=120))
session=None;report={}
try:
 session=rec.measure('open',lambda:open_proof_world_session(work,rules_id=info['rules_id'],expected_commitment=bytes.fromhex(info['proof_commitment'])))
 store=session.store;rec.store=store
 for phase,operation in [('first_step',lambda:Simulation(session.world).run(1)),('save',session.save),('warm_step',lambda:Simulation(session.world).run(1))]:
  rec.measure(phase,operation)
  rows={k:v for k,v in reads.items() if k[0]==phase};scoped={k:v for k,v in scope_reads.items() if k[0]==phase and k[1]!='none'}
  report[phase]=dict(reads=sum(rows.values()),unique_nodes=len(rows),scoped_reads=sum(scoped.values()),unique_scope_nodes=len(scoped),
   outside_scope_reads=sum(v for k,v in scope_reads.items() if k[0]==phase and k[1]=='none'),
   top_domains=[dict(domain=k[0].hex(),reads=v) for k,v in collections.Counter({(d,):sum(v for (p,dom,_),v in rows.items() if dom==d) for _,d,_ in rows}).most_common(8)],
   owner_calls=[dict(kind=list(k[1:]),count=v) for k,v in owner.items() if k[0]==phase])
  print(phase,json.dumps(report[phase]),flush=True)
 assert session.world.year==3
 report['warm_digest']=session.world.digest();assert report['warm_digest']=='a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3'
 report['phases']=rec.phases
 report['runtime_tree']=subprocess.check_output(['git','rev-parse','HEAD:simulation/ate_sim'],cwd=ROOT,text=True).strip()
 report['source_preserved']=True
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 if session is not None:session.close()
 c.verify_database(source,info['database']);work.unlink(missing_ok=True)
