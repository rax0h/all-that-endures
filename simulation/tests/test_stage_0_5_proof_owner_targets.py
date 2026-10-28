import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE
from simulation.tests.proof_owner_target_fixtures import make_owner_target_store,PAGE
from simulation.tests.proof_target_fixtures import authorities

def m():return importlib.import_module('ate_sim.persistence_proof_owner_targets')
def read(s,p,a,**kw):return m().read_owner_targets(s,p,PAGE,s.codec.encode((3,0)),*a,**kw)

def test_all_paths_and_one_distinct_target(tmp_path):
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite');r=read(s,p,a)
 assert len(r.references)==2 and [inc for path,inc in r.references]==[2,2]
 assert len(r.targets)==1 and r.targets[0].kind=='list' and r.source.payload==s.codec.encode((ref,ref));s.close()

def test_wrong_kind_same_identity_rejected(tmp_path):
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite',wrong_kind=True)
 with pytest.raises(StoreError):read(s,p,a)
 s.close()

@pytest.mark.parametrize('fault',['target','placement','limit','bytes','source','metadata','transaction'])
def test_join_fail_closed(tmp_path,fault):
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite');kw={}
 if fault=='target':
  p=s.commit(p,commit_token='delete',version_changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,delete=True),),changes=(),new_segments=(),metadata=s.head_metadata()).pin;a=authorities(s,p)
 elif fault=='placement':s.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?',(PAGE,));s.db.commit()
 elif fault=='limit':kw['max_references']=1
 elif fault=='bytes':kw['max_bytes']=1
 elif fault=='source':kw['max_source_bytes']=1
 elif fault=='metadata':kw['max_metadata_bytes']=1
 elif fault=='transaction':s.db.execute('BEGIN')
 with pytest.raises(StoreError):read(s,p,a,**kw)
 if s.db.in_transaction:s.db.rollback()
 s.close()

@pytest.mark.parametrize('deleted',[False,True])
def test_empty_or_absent_owner_has_no_targets(tmp_path,deleted):
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite')
 owners=(VersionChange(PAGE,(3,0),(11,22),delete=deleted),)
 placements=tuple(IdentityOccurrenceChange(PAGE,(3,0),(('index',n),),delete=True) for n in (0,1))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=4)
 p=s.commit(p,commit_token='empty',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 r=read(s,p,authorities(s,p));assert r.references==r.targets==() and (r.source is None)==deleted;s.close()

def test_retained_owner_and_same_snapshot(tmp_path):
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite');old=s.capture_pin()
 p2=s.commit(p,commit_token='grow',version_changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,('list',1,1)),VersionChange(PAGE,(2,0),(11,))),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a2=authorities(s,p2)
 assert read(s,old,a).targets[0].descriptor==('list',0,0)
 assert read(s,p2,a2).targets[0].descriptor==('list',1,1)
 with pytest.raises(StoreError):read(s,p2,a)
 s.close()

@pytest.mark.parametrize('fault',['codec','shadow','view','expected','limit-type'])
def test_join_source_guards(tmp_path,fault):
 s,p,ref,a=make_owner_target_store(tmp_path/'o.sqlite');kw={}
 if fault=='codec':s.codec.decode=lambda _:pytest.fail('codec hook invoked')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head');s.db.commit()
 elif fault=='view':s.db.execute('ALTER TABLE save_head RENAME TO old_head');s.db.execute('CREATE VIEW save_head AS SELECT * FROM old_head');s.db.commit()
 elif fault=='expected':a=((a[0][0],b'x'*32),*a[1:])
 elif fault=='limit-type':kw['max_references']=True
 with pytest.raises(StoreError):read(s,p,a,**kw)
 s.close()


def test_duplicate_owner_references_resolve_target_once(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_target as target
 s,p,ref,a=make_owner_target_store(tmp_path/'once.sqlite');original=target._resolve_target;calls=[]
 def resolve(*args,**kw):calls.append(args[2].incarnation);return original(*args,**kw)
 with monkeypatch.context() as patch:
  patch.setattr(target,'_resolve_target',resolve);result=read(s,p,a)
 assert len(result.references)==2 and [t.incarnation for t in result.targets]==[2] and calls==[2];s.close()


def distinct_owner_targets(tmp_path,late_conflict=False):
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_lazy_nested_history import HistoryReference
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,ref,a=make_owner_target_store(tmp_path/'distinct.sqlite');other=HistoryReference('list',4)
 values=(ref,other,HistoryReference('map',2)) if late_conflict else (ref,other)
 owner=VersionChange(PAGE,(3,0),values)
 placements=(IdentityOccurrenceChange(PAGE,(3,0),(('index',1),),4),)+((IdentityOccurrenceChange(PAGE,(3,0),(('index',2),),2),) if late_conflict else ())
 delta=cat.IdentityCatalog(s).prepare_delta(p,(owner,),placements,next_incarnation_id=5)
 p=s.commit(p,commit_token='distinct',version_changes=(owner,VersionChange(DESCRIPTOR_NAMESPACE,3,('list',len(values),len(values))),VersionChange(DESCRIPTOR_NAMESPACE,4,('list',0,0)))+delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=5,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 return s,p,authorities(s,p)


def test_distinct_targets_share_aggregate_source_budget(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_target as target
 s,p,a=distinct_owner_targets(tmp_path);original=target._Sources.charge;charged=[]
 def charge(self,n):charged.append(n);return original(self,n)
 with monkeypatch.context() as patch:
  patch.setattr(target._Sources,'charge',charge);result=read(s,p,a)
 assert [t.incarnation for t in result.targets]==[2,4]
 with pytest.raises(StoreError):read(s,p,a,max_bytes=sum(charged)-1)
 assert read(s,p,a).targets==result.targets;s.close()


def test_late_conflicting_kind_is_rejected_after_distinct_targets(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_target as target
 s,p,a=distinct_owner_targets(tmp_path,True);original=target._resolve_target;calls=[]
 def resolve(*args,**kw):calls.append(args[2].incarnation);return original(*args,**kw)
 with monkeypatch.context() as patch:
  patch.setattr(target,'_resolve_target',resolve)
  with pytest.raises(StoreError,match='competing target kinds'):read(s,p,a)
 assert calls==[2,4];s.close()
