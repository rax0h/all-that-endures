from pathlib import Path
import tempfile
from simulation.tests.test_stage_0_6_proof_native_rank import rank_fixture,opened,bucket,NS
from ate_sim.persistence_lazy_minimum import rank_neighbor
with tempfile.TemporaryDirectory() as t:
 path,pair=rank_fixture(Path(t))
 session=opened(path,pair);store=session.store;auth=store._world_proof_authority
 try:
  scope=bucket(store);pin=session.pin
  first=rank_neighbor(store,pin,NS,scope)
  expected=store.codec.encode(first[0]);done=[];decode=store.codec.decode
  def changed(raw):
   if not done and raw==expected:
    done.append(1)
    store.db.execute('DELETE FROM lazy_query_versions WHERE namespace=? AND index_name=? AND record_key=?',(NS,scope,store.codec.encode(first[2])))
    store.db.commit()
   return decode(raw)
  store.codec.decode=changed
  try:print('changed-epoch read result',rank_neighbor(store,pin,NS,scope))
  finally:del store.codec.decode
  print('changed',done,'valid epoch?',auth.epoch==auth._epoch());print('current rows from sqlite',store.db.execute('select ordinal from lazy_query_versions where namespace=? and index_name=? order by ordinal',(NS,scope)).fetchall())
 finally:store.close()
