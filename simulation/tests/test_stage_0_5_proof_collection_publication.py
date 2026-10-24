import importlib
import pytest
from ate_sim.incremental_store import StoreError,StoreIntegrityError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_proof_collection import bootstrap_collection,read_collection_page
from simulation.tests.proof_publication_fixtures import make_publication_store,metadata

def m():return importlib.import_module('ate_sim.persistence_proof_collection_publish')
def setup(tmp_path):
 s,p,a=make_publication_store(tmp_path/'publish.sqlite');c=bootstrap_collection(s,p,'people');return s,p,a,c

def save(s,p,a,c,changes,**kw):
 return m().commit_collections(s,p,(c,),*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next',version_changes=changes,identity_changes=(),changes=(),new_segments=(),metadata=metadata(p.captured_head+1),**kw)

def test_atomic_order_successor_and_retained_page(tmp_path):
 s,p,a,c=setup(tmp_path);old=s.capture_pin()
 r=save(s,p,a,c,(VersionChange('people',0,{'wealth':2},reinsertion=True),VersionChange('people',1,{'wealth':3})))
 assert r.content.commit.generation==2 and r.collections[0][0].member_count==2 and r.collections[0][0].next_ordinal==3
 assert read_collection_page(s,old,*c).positions==((s.codec.encode(0),0),)
 assert read_collection_page(s,r.content.commit.pin,*r.collections[0]).positions==((s.codec.encode(0),1),(s.codec.encode(1),2));s.close()

def test_value_only_reuses_root(tmp_path):
 s,p,a,c=setup(tmp_path);r=save(s,p,a,c,(VersionChange('people',0,{'wealth':2}),))
 assert r.collections[0][0].root==c[0].root;s.close()

@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_failure_and_exact_recovery(tmp_path,phase):
 s,p,a,c=setup(tmp_path)
 def fault(at):
  if at==phase:raise RuntimeError('injected')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):save(s,p,a,c,(VersionChange('people',0,{'wealth':2},reinsertion=True),))
 s._phase_hook=lambda _:None
 if phase=='after_commit':
  r=m().resolve_collections(s,p,(c,),*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='next')
  assert r.collections[0][0].next_ordinal==2
 else:assert s.generation==1
 s.close()

def test_missing_namespace_authority_rejects_before_writes(tmp_path):
 s,p,a,c=setup(tmp_path)
 with pytest.raises(StoreError):save(s,p,a,c,(VersionChange('archive',0,{'new':1}),))
 assert s.generation==1;s.close()

def test_coherent_old_order_tamper_rejected(tmp_path):
 from ate_sim.persistence_lazy_store import _order_checksum
 s,p,a,c=setup(tmp_path);key=s.codec.encode(0)
 s.db.execute("UPDATE lazy_order_versions SET ordinal=9,row_checksum=? WHERE namespace='people'",(_order_checksum('people',key,9,1,None),));s.db.commit()
 with pytest.raises(StoreIntegrityError):save(s,p,a,c,(VersionChange('people',0,{'wealth':2}),))
 assert s.generation==1;s.close()

def test_expected_type_rejected_without_comparison_hook(tmp_path):
 s,p,a,c=setup(tmp_path);calls=[]
 class Expected:
  def __eq__(self,other):calls.append(1);return True
 bad=(c[0],Expected())
 with pytest.raises(StoreError):save(s,p,a,bad,())
 assert not calls;s.close()

def test_nested_malformed_persistent_certificate_is_integrity_error(tmp_path):
 s,p,a,c=setup(tmp_path)
 s.db.execute('UPDATE ate_collection_generations SET certificate=?',(('['*1500+'0'+']'*1500).encode(),));s.db.commit()
 with pytest.raises(StoreError):save(s,p,a,c,())
 s.close()

def test_metadata_only_and_noop_share_all_collection_roots(tmp_path):
 s,p,a,c=setup(tmp_path)
 args=dict(scope_authority=a.scope,record_authority=a.record,commit_token='noop',version_changes=(),identity_changes=(),changes=(),new_segments=(),metadata=metadata(1))
 r=m().commit_collections(s,p,(c,),*a.content,**args)
 assert r.content.commit.outcome=='not_committed' and r.collections==(c,)
 args.update(commit_token='metadata',metadata=metadata(2));r=m().commit_collections(s,p,(c,),*a.content,**args)
 assert r.collections[0][0].root==c[0].root and r.collections[0][0].next_ordinal==c[0].next_ordinal;s.close()

def test_multiple_namespaces_spilled_and_absent_delete(tmp_path):
 s,p,a,c=setup(tmp_path);archive=bootstrap_collection(s,p,'archive')
 r=m().commit_collections(s,p,(c,archive),*a.content,scope_authority=a.scope,record_authority=a.record,commit_token='multiple',
  version_changes=(VersionChange('people',0,{'wealth':2},reinsertion=True),VersionChange('archive',999,delete=True),VersionChange('people',1,{'wealth':3})),identity_changes=(),changes=(),new_segments=(),metadata=metadata(2),preparation_budget=(1,1))
 assert r.collections[0][0].member_count==2 and r.collections[0][0].next_ordinal==3
 assert r.collections[1][0].declared and r.collections[1][0].member_count==r.collections[1][0].next_ordinal==0
 s.verify_all();s.close()

def test_actual_new_order_is_checked_outside_callbacks(tmp_path,monkeypatch):
 from ate_sim.persistence_lazy_store import LazyRecordStore,_order_checksum
 s,p,a,c=setup(tmp_path);original=LazyRecordStore._write_lazy_changes
 def corrupt(self,*args,**kwargs):
  original(self,*args,**kwargs);key=self.codec.encode(0)
  self.db.execute("UPDATE lazy_order_versions SET ordinal=7,row_checksum=? WHERE namespace='people' AND valid_to IS NULL",(_order_checksum('people',key,7,1,None),))
 monkeypatch.setattr(LazyRecordStore,'_write_lazy_changes',corrupt)
 with pytest.raises(StoreIntegrityError):save(s,p,a,c,(VersionChange('people',0,{'wealth':2}),))
 assert s.generation==1;s.close()
