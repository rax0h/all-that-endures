import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import ate_sim.persistence_proof_parent_inputs as module
from ate_sim.persistence_proof_verify_batch import verify_sorted
from ate_sim.persistence_lazy_budget import resident_bytes
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_proof_map import MemoryNodes, proof_map, locator

def make(): return module.ParentInputs(SimpleNamespace(db=sqlite3.connect(':memory:')))
def gone(p): assert not p.store.db.execute("SELECT 1 FROM sqlite_temp_master WHERE name='ate_content_predecessors'").fetchone()
row=(0,locator(b'a'),b'a',None); charge=resident_bytes([])+resident_bytes(row)+128
p=make()
with patch.object(module,'BUFFER_BYTES',charge):
 p.add(*row); assert not p.spilled and p.bytes==charge
 p.add(1,locator(b'b'),b'b',None); assert p.spilled and not p.rows
 assert list(p.members(0))==[(b'a',None)] and list(p.members(1))==[(b'b',None)]
p.close();gone(p);p.close();gone(p)
print('PASS exact admission threshold, mixed-kind spill order, idempotent cleanup')
# Same locator across different kinds is legal; same-kind duplicate rejects in either path.
for limit in [0,1024*1024]:
 p=make();m=proof_map(MemoryNodes())
 with patch.object(module,'BUFFER_BYTES',limit):
  try:
   p.add(*row);p.add(*row)
   verify_sorted(m,m.empty,p.members(0))
  except StoreIntegrityError: pass
  else: raise AssertionError('duplicate accepted')
  finally:p.close()
 gone(p)
print('PASS duplicate locator rejection in memory and spill')
# Buffered duplicates fail during first spill; cleanup still owns the created table.
p=make();p.add(*row);p.add(*row)
with patch.object(module,'BUFFER_BYTES',0):
 try:p.add(1,locator(b'b'),b'b',None)
 except StoreIntegrityError:pass
 else:raise AssertionError('buffered collision accepted')
assert p.spilled
p.close();gone(p)
print('PASS partial spill collision cleanup')
# Inject fail after an inserted first buffered row.
p=make();p.add(*row);p.add(0,locator(b'b'),b'b',None);original=p._insert;calls=[]
def fault(r):
 calls.append(r)
 if len(calls)==2:raise RuntimeError('partial insert fault')
 return original(r)
with patch.object(module,'BUFFER_BYTES',0),patch.object(p,'_insert',fault):
 try:p.add(1,locator(b'c'),b'c',None)
 except RuntimeError:pass
 else:raise AssertionError('fault swallowed')
assert p.spilled and p.store.db.execute('SELECT count(*) FROM ate_content_predecessors').fetchone()==(1,)
p.close();gone(p)
print('PASS partial insert callback failure cleanup')
# Retained charge bounds actual Python row/list residency on representative largest nonspill inventory.
p=make();i=0
while not p.spilled:
 prior_bytes=p.bytes; prior_resident=resident_bytes(p.rows);prior_count=len(p.rows)
 p.add(i%2,locator(str(i).encode()),str(i).encode(),None);i+=1
assert prior_resident<=prior_bytes<=module.BUFFER_BYTES
p.close();gone(p)
print('PASS retained accounting bound',prior_count,'rows',prior_resident,'resident',prior_bytes,'charged')
print('ALL HELPER PROBES PASSED')
