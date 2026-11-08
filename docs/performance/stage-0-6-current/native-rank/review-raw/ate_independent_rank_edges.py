from pathlib import Path
import tempfile,tracemalloc
from simulation.tests.test_stage_0_6_proof_native_rank import rank_fixture,opened,bucket,NS
from ate_sim.persistence_lazy_minimum import rank_neighbor
from ate_sim.incremental_store import StoreError
from dataclasses import replace
with tempfile.TemporaryDirectory() as t:
 path,pair=rank_fixture(Path(t))
 with opened(path,pair) as session:
  store=session.store;db=store.db;auth=store._world_proof_authority
  scope=bucket(store);pin=session.pin
  def shadow():
   db.execute('CREATE TEMP TABLE lazy_query_versions AS SELECT * FROM main.lazy_query_versions')
   db.execute('CREATE INDEX temp.lazy_query_current ON lazy_query_versions(namespace,index_name,index_value,ordinal,record_key) WHERE valid_to IS NULL')
   db.execute('CREATE INDEX temp.ate_rank_query_closed ON lazy_query_versions(namespace,index_name,valid_to,index_value,ordinal,record_key) WHERE valid_to IS NOT NULL')
   try:
    print('shadow served',rank_neighbor(store,pin,NS,scope))
   except Exception as exc:print('shadow rejected',type(exc),exc)
   finally:db.execute('DROP TABLE temp.lazy_query_versions')
  auth.execute(session,shadow)
  for test,kw in [('rank',dict(rank='A'*(8*1024*1024),ordinal=0)),('key',dict(exclude=(b'A'*(8*1024*1024),)))]:
   tracemalloc.start()
   try:rank_neighbor(store,pin,NS,scope,**kw)
   except StoreError as e:print(test,str(e),tracemalloc.get_traced_memory()[1])
   finally:tracemalloc.stop()
  seen=[]
  f=store.codec.encode
  def encode(value):
   if value=='RANK' or value=='KEY':seen.append(value)
   return f(value)
  store.codec.encode=encode
  try:rank_neighbor(store,replace(pin,token='released!'),NS,scope,rank='RANK',ordinal=1,exclude=('KEY',))
  except Exception as e:print('stale pin',type(e),seen)
  finally:del store.codec.encode
