import hashlib, json, platform, sqlite3, sys, tempfile
from pathlib import Path
from unittest.mock import patch
import ate_sim.persistence_proof_verify_batch as batch
import ate_sim.persistence_proof_map as pm
from ate_sim.persistence_proof_nodes import Leaf, Branch
from ate_sim.incremental_store import StoreIntegrityError, StoreConflictError, NewSegment
from simulation.tests.test_stage_0_5_proof_map import MemoryNodes, proof_map, value
from simulation.tests.proof_publication_fixtures import make_publication_store, commit_publication, publication_module, read_version

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
  after={n:store.db.execute('SELECT * FROM "'+n+'"').fetchall() for (n,) in before}
  changed=[n for n in snapshot if snapshot[n]!=after[n]]
  print('Changed tables after rejected commit:',changed,flush=True)
  assert changed==['pin_attempts']
  attempt=after['pin_attempts'][0]
  assert attempt[3]=='pending' and attempt[4] is None
  assert store.resolve_commit(pin,'retry').outcome=='not_committed'
  result=commit_publication(store,pin,authority,token='retry-new'); assert result.commit.outcome=='committed'
  assert not store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
  store.close()
  check=sqlite3.connect(Path(tmp)/'db.sqlite'); assert check.execute('pragma integrity_check').fetchone()==('ok',);check.close()
 print('PASS persisted fault rollback / no source writes / TEMP cleanup / new-token retry after resolve kind',failing_kind,flush=True)
print('ALL PROBES PASSED',flush=True)
