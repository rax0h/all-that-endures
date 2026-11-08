import sqlite3,random,tempfile
from pathlib import Path
from ate_sim.persistence_proof_seek import OrderedSeekMap
from ate_sim.persistence_proof_rank import position,parse_position
from simulation.tests import proof_sequence_event_fixtures as fix
from simulation.tests.test_stage_0_5_proof_reference_closure import make_graph,read,ids
from ate_sim.persistence_lazy_nested_history import HistoryReference as H
rng=random.Random(9204)
values=sorted({(bytes(rng.choices([0,1,255],k=rng.randrange(6))),rng.randrange(3),bytes(rng.choices([0,1,255],k=rng.randrange(4)))) for i in range(160)})
db=sqlite3.connect(':memory:');db.execute('BEGIN');m=OrderedSeekMap(db,b'test');m.create_schema()
rr=m.build((position(*v),bytes([n%256])*32) for n,v in enumerate(values));db.commit()
tests=0
for rank in {r for r,_,_ in values}|{b'\0\xff\0\xff\1',b'z',b'\xff'*8}:
 for o in range(4):
  for before in (True,False):
   w=sorted([v for v in values if ((v[:2]<(rank,o)) if before else (v[:2]>(rank,o)))],reverse=before)[:2]
   k=position(rank,o,b'' if before else b'\xff'*4096)
   page=m.reverse_page(rr,before=k,limit=2) if before else m.page(rr,after=k,limit=2)
   assert [parse_position(p) for p,_ in page]==w
   tests+=1
print('rank/key/strict boundary comparisons:',tests)
with tempfile.TemporaryDirectory() as tmp:
 orig=fix.bootstrap_scope_proofs
 fix.bootstrap_scope_proofs=lambda s,p,**kw:orig(s,p,include_rank=True,**kw)
 s,p,r,a,ra=make_graph(Path(tmp)/'closure.sqlite',{2:('list',(H('sequence',3),H('sequence',3))),3:('sequence',(7,8))})
 try:
  assert len(a[1][0].roots)==7
  closure=read(s,p,r,a)
  print('seven-root closure:',ids(closure),[e.target_incarnation for e in closure.edges],closure.targets[1].members)
 finally:s.close()
