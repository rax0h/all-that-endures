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
