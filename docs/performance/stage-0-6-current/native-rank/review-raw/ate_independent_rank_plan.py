import sqlite3
from ate_sim import persistence_proof_native_rank as rank
from ate_sim.persistence_lazy_store import _query_checksum
from types import SimpleNamespace
s=SimpleNamespace(db=sqlite3.connect(':memory:'),_metadata_rows=0,_query_rows=0)
s.db.execute('CREATE TABLE lazy_query_versions(namespace,index_name,index_value,record_key,ordinal,valid_from,valid_to,row_checksum)')
s.db.execute('CREATE INDEX lazy_query_current ON lazy_query_versions(namespace,index_name,index_value,ordinal,record_key) WHERE valid_to IS NULL')
s.db.execute(rank.ranks._INDEX)
scope=rank.ranks.RankScope('x','minimum/v1/a')
def rows(a,b):
 for i in range(a,b):
  r=i.to_bytes(2,'big');yield ('x',scope.index_name,r,b'k',i,0,None,_query_checksum('x',scope.index_name,r,b'k',i,0,None))
a=0
for b in (100,1000,10000):
 s.db.executemany('insert into lazy_query_versions values(?,?,?,?,?,?,?,?)',rows(a,b));a=b
 captured=[];s.db.set_trace_callback(captured.append)
 ticks=[];s.db.set_progress_handler(lambda:ticks.append(1) or 0,100)
 rank._physical(s,0,scope,[(i.to_bytes(2,'big'),i,b'k') for i in (0,1)],bound=None,before=False,continuation=None)
 s.db.set_progress_handler(None,0);s.db.set_trace_callback(None)
 print(b,len(ticks)*100)
 for x in s.db.execute('EXPLAIN QUERY PLAN '+captured[-1]):print(x)
