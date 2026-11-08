from pathlib import Path
import tempfile
from simulation.tests.test_stage_0_6_proof_native_rank import rank_fixture,opened,bucket,NS
from ate_sim.persistence_lazy_minimum import rank_neighbor
with tempfile.TemporaryDirectory() as t:
 path,pair=rank_fixture(Path(t));session=opened(path,pair);store=session.store;auth=store._world_proof_authority
 try:
  name=bucket(store);pin=session.pin;print('accepted',rank_neighbor(store,pin,NS,name))
  # Same physical fault model as the package's negative controls. Context disappearance alone enables the false result.
  store.db.execute('delete from lazy_query_versions where namespace=? and index_name=? and ordinal=0',(NS,name))
  store.db.commit();auth.epoch=auth._epoch()
  try:print('v4 normal',rank_neighbor(store,pin,NS,name))
  except Exception as e:print('v4 normal',type(e),e)
  auth.read_components=None
  print('missing v4 context',rank_neighbor(store,pin,NS,name))
 finally:store.close()
