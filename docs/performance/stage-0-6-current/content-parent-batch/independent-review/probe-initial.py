import hashlib, json, platform, sqlite3, sys, tempfile
from pathlib import Path
from unittest.mock import patch
import ate_sim.persistence_proof_verify_batch as batch
import ate_sim.persistence_proof_map as pm
from ate_sim.persistence_proof_nodes import Leaf, Branch
from ate_sim.incremental_store import StoreIntegrityError, StoreConflictError, NewSegment
from simulation.tests.test_stage_0_5_proof_map import MemoryNodes, proof_map, value
from simulation.tests.proof_publication_fixtures import make_publication_store, commit_publication, publication_module, read_version

receipt=json.loads(Path('docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json').read_text())
assert sys.version==receipt['python'] and platform.python_compiler()==receipt['compiler'] and sqlite3.sqlite_version==receipt['sqlite']
for p,k in [(receipt['resolved_executable'],'executable_sha256'),(receipt['sqlite_extension_path'],'sqlite_extension_sha256')]:
 assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==receipt[k]
for lib in receipt['loaded_sqlite_libraries']: assert hashlib.sha256(Path(lib['path']).read_bytes()).hexdigest()==lib['sha256']
db=sqlite3.connect(':memory:')
assert db.execute('select sqlite_source_id()').fetchone()[0]==receipt['sqlite_source_id']
assert sorted(r[0] for r in db.execute('pragma compile_options'))==sorted(receipt['sqlite_compile_options'])
print('PASS full qualified runtime fingerprint', flush=True)
# Synthetic locators deliberately cover compressed gaps and last-nibble splits.
def loc(domain,key): return key
keys=[bytes.fromhex(s.ljust(64,'0')) for s in ['1230','1231','123f','124','12f','2','f0','ff']]
queries=sorted(set(keys+[bytes.fromhex(s.ljust(64,'0')) for s in ['0','1','122f','1232','123e','123ff','1241','12e','13','e','f1','fff']]))
checks=0
with patch.object(batch,'key_locator',loc),patch.object(pm,'key_locator',loc):
 for mask in range(256):
  storage=MemoryNodes(); m=proof_map(storage); root=m.empty
  expected={k:value(str(i)) for i,k in enumerate(keys) if mask>>i&1}
  for k,v in expected.items(): root=m.set(root,k,v)
  members=[(k,expected.get(k)) for k in queries]
  for k,v in members: assert m.get(root,k)==v
  storage.reads.clear(); storage.writes.clear()
  batch.verify_sorted(m,root,members)
  assert len(storage.reads)==len(set(storage.reads)) and not storage.writes
  checks+=len(members)
  for malformed in [members+[(b'late',b'bad')],members+[members[-1]]]:
   try: batch.verify_sorted(m,root,malformed)
   except StoreIntegrityError: pass
   else: raise AssertionError('late invalid input accepted')
 print('PASS exhaustive sparse compressed-prefix models',checks,'members; late invalid/duplicate checks 512',flush=True)
 # Longest possible checked path: 64 branches then leaf.
 storage=MemoryNodes(); m=proof_map(storage); zero=bytes(32); root=storage.store(Leaf(zero,value('zero')))
 for depth in reversed(range(64)):
  nibbles=[0]*64; nibbles[depth]=1
  other=bytes((nibbles[i]<<4)|nibbles[i+1] for i in range(0,64,2))
  sibling=storage.store(Leaf(other,value(str(depth))))
  root=storage.store(Branch((0,)*depth,((0,root),(1,sibling))))
 storage.reads.clear(); batch.verify_sorted(m,root,[(zero,value('zero'))]); assert len(storage.reads)==65
 print('PASS maximum depth 64 branches / 65 checked nodes',flush=True)
# Reader failure must propagate; no write callback.
storage=MemoryNodes();m=proof_map(storage);root=m.set(m.empty,b'a',value('a'));storage.writes.clear()
with patch.object(m,'read_node',side_effect=RuntimeError('reader fault')):
 try: batch.verify_sorted(m,root,[(b'a',value('a'))])
 except RuntimeError as e: assert str(e)=='reader fault'
 else: raise AssertionError('reader exception swallowed')
assert not storage.writes
print('PASS reader callback failure',flush=True)
# Real sqlite transactions: fail each of the two parent checks, then retry same token.
for failing_kind in (0,1):
 with tempfile.TemporaryDirectory() as tmp:
  store,pin,authority=make_publication_store(Path(tmp)/'db.sqlite',2)
  p=publication_module(); original=batch.verify_sorted; calls=[]; writes=[]
  def faulty(m,root,members):
   idx=len(calls); calls.append(idx)
   if idx==failing_kind:
    next(iter(members),None)
    raise RuntimeError('injected parent fault')
   return original(m,root,members)
  before=store.db.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name').fetchall()
  snapshot={n:store.db.execute('SELECT * FROM "'+n+'"').fetchall() for (n,) in before}
  with patch.object(batch,'verify_sorted',faulty),patch.object(store,'_write_lazy_changes',side_effect=lambda *a,**kw:writes.append(True)):
   try: commit_publication(store,pin,authority,token='retry')
   except RuntimeError as e: assert str(e)=='injected parent fault'
   else: raise AssertionError('fault swallowed')
  assert not writes and not store.db.in_transaction
  assert not store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
  assert snapshot=={n:store.db.execute('SELECT * FROM "'+n+'"').fetchall() for (n,) in before}
  result=commit_publication(store,pin,authority,token='retry'); assert result.commit.outcome=='committed'
  assert not store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
  store.close()
  check=sqlite3.connect(Path(tmp)/'db.sqlite'); assert check.execute('pragma integrity_check').fetchone()==('ok',);check.close()
 print('PASS persisted fault rollback / no source writes / TEMP cleanup / same-token retry kind',failing_kind,flush=True)
print('ALL PROBES PASSED',flush=True)
