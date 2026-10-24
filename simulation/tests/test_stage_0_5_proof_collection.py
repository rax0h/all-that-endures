import importlib
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.proof_query_fixtures import make_store,metadata

def module():return importlib.import_module('ate_sim.persistence_proof_collection')
def setup(tmp_path):
 s,p=make_store(tmp_path/'c.sqlite');m=module();return m,s,p,m.bootstrap_collection(s,p,'people')

def test_construct_complete_pages_and_opaque_positions(tmp_path):
 m,s,p,a=setup(tmp_path);assert a[0].root.count==a[0].member_count==8 and a[0].next_ordinal==8
 s.reset_diagnostics();first=m.read_collection_page(s,p,*a,limit=3)
 assert first.positions==tuple((s.codec.encode(i),i) for i in range(3)) and first.next_after==(2,s.codec.encode(2))
 second=m.read_collection_page(s,p,*a,after=first.next_after,limit=128)
 assert second.positions==tuple((s.codec.encode(i),i) for i in range(3,8)) and second.next_after is None
 assert s._payload_reads==s._payload_check_reads==0;s.close()

def test_absent_and_declared_empty_state_are_distinct(tmp_path):
 m,s,p,a=setup(tmp_path);absent=m.bootstrap_collection(s,p,'missing');assert not absent[0].declared
 out=s.commit(p,commit_token='delete',version_changes=tuple(VersionChange('people',i,delete=True) for i in range(8)),changes=(),new_segments=(),metadata=metadata(2))
 empty=m.bootstrap_collection(s,out.pin,'people');assert empty[0].declared and empty[0].member_count==0 and empty[0].next_ordinal==8
 assert m.read_collection_page(s,out.pin,*empty).positions==();s.close()

def test_retained_root_selects_exact_old_order_after_reinsertion(tmp_path):
 m,s,p,a=setup(tmp_path);old=s.capture_pin()
 out=s.commit(p,commit_token='move',version_changes=(VersionChange('people',0,{'wealth':9},reinsertion=True),),changes=(),new_segments=(),metadata=metadata(2))
 new=m.bootstrap_collection(s,out.pin,'people')
 assert m.read_collection_page(s,old,*a).positions[0]==(s.codec.encode(0),0)
 assert m.read_collection_page(s,out.pin,*new).positions[-1]==(s.codec.encode(0),8);s.close()

@pytest.mark.parametrize('fault',['expected','checksum','missing','node','state','shadow','transaction','hook','budget','index','generation','counter-bool'])
def test_rejects_corrupt_or_unbounded_source(tmp_path,fault):
 m,s,p,a=setup(tmp_path);kw={}
 if fault=='expected':a=(a[0],b'x'*32)
 elif fault=='checksum':s.db.execute('UPDATE lazy_order_versions SET row_checksum=?',('a\0'+'x'*1048577,))
 elif fault=='missing':s.db.execute('DELETE FROM lazy_order_versions WHERE ordinal=0')
 elif fault=='node':s.db.execute('DELETE FROM ate_ordered_seek_nodes')
 elif fault=='state':s.db.execute('UPDATE lazy_namespace_state SET next_ordinal=next_ordinal+1')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE lazy_order_versions AS SELECT * FROM main.lazy_order_versions')
 elif fault=='hook':s.codec.decode=lambda _:pytest.fail('caller hook')
 elif fault=='budget':kw['max_metadata_bytes']=1
 elif fault=='index':s.db.execute('DROP INDEX lazy_order_interval')
 elif fault=='generation':a=(replace(a[0],generation=0),b'x'*32)
 elif fault=='counter-bool':a=(replace(a[0],member_count=True),b'x'*32)
 s.db.commit()
 if fault=='transaction':s.db.execute('BEGIN')
 with pytest.raises(StoreError):m.read_collection_page(s,p,*a,**kw)
 if s.db.in_transaction:s.db.rollback()
 s.close()

@pytest.mark.parametrize('value',[None,'8','comparison-hook'])
def test_counter_type_checked_before_comparison(tmp_path,value):
 m,s,p,a=setup(tmp_path);calls=[]
 class Counter:
  def __ge__(self,other):calls.append(other);return True
 if value=='comparison-hook':value=Counter()
 with pytest.raises(StoreError):m.certificate_commitment(replace(a[0],next_ordinal=value))
 assert not calls;s.close()

@pytest.mark.parametrize('helper',['_enter','_node_sort_key'])
def test_constructor_rejects_overridden_codec_helpers(tmp_path,helper):
 from ate_sim.incremental_store import Membership
 s,p=make_store(tmp_path/'helpers.sqlite');value=('tuple',1) if helper=='_enter' else frozenset({1,2})
 out=s.commit(p,commit_token='membership',version_changes=(VersionChange('people',0,{'wealth':0},memberships=(Membership('index',value,0),)),),changes=(),new_segments=(),metadata=metadata(2))
 original=getattr(s.codec,helper);calls=[]
 def hook(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
 setattr(s.codec,helper,hook)
 with pytest.raises(StoreError):module().bootstrap_collection(s,out.pin,'people')
 assert not calls;s.close()
