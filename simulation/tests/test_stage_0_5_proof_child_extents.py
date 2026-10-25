import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE,ENTRY_NAMESPACE,DESCRIPTOR_NAMESPACE
from ate_sim.persistence_history_types import NAMESPACE as TYPES,TAG
from simulation.tests.proof_child_extent_fixtures import make_child_store,authorities
from simulation.tests.proof_target_fixtures import make_target_store


def read(s,p,r,a,**kw):return importlib.import_module('ate_sim.persistence_proof_child_extents').read_target_members(s,p,r,*a,**kw)


@pytest.mark.parametrize('kind,values,want',[('list',(1,2,3),(1,2,3)),('map',(('a',1),('b',2)),(('a',1),('b',2))),('set',(4,2),(4,2))])
def test_exact_mutable_child_members(tmp_path,kind,values,want):
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite',kind,values);v=read(s,p,r,a)
 assert v.members==want and v.member_counts==((3,0,0) if kind=='list' else (2,0,0) if kind=='set' else (0,0,2));s.close()


@pytest.mark.parametrize('fault',['far','hole','family','length','counter'])
def test_valid_roots_reject_bad_list_extent(tmp_path,fault):
 extra=[];values=tuple(range(257)) if fault=='hole' else (1,2,3)
 if fault=='far':extra=[VersionChange(PAGE_NAMESPACE,(2,999),(7,))]
 elif fault=='hole':extra=[VersionChange(PAGE_NAMESPACE,(2,1),delete=True)]
 elif fault=='family':extra=[VersionChange(ENTRY_NAMESPACE,(2,1),(0,1,None))]
 elif fault=='length':extra=[VersionChange(PAGE_NAMESPACE,(2,0),(1,2))]
 else:extra=[VersionChange(TYPES,2,(TAG,'list',(0,0,3)))]
 # Duplicate source changes are prepared in a successor, then audited explicitly.
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite',values=values)
 p=s.commit(p,commit_token='bad',version_changes=tuple(extra),changes=(),new_segments=(),metadata=s.head_metadata()).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('values,valid',[((1,2),True),((True,2),False),((1.0,2),False)])
def test_actual_integer_owner_policy(tmp_path,values,valid):
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite',values=values,policy='int')
 if valid:assert read(s,p,r,a).member_counts==(2,0,0)
 else:
  with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_legacy_scope_does_not_gain_child_authority(tmp_path):
 s,p,r,a=make_target_store(tmp_path/'c.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kw',[{'max_children':0},{'max_children':True},{'max_values':2},{'max_bytes':1},{'max_source_bytes':1}])
def test_extent_budgets(tmp_path,kw):
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a,**kw)
 s.close()


def test_child_successor_published_atomically_and_retained(tmp_path):
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite');old=s.capture_pin()
 changes=(VersionChange(PAGE_NAMESPACE,(2,0),(4,5)),VersionChange(DESCRIPTOR_NAMESPACE,2,('list',2,2)),VersionChange(TYPES,2,(TAG,'list',(2,0,0))))
 result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='edit',version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata())
 anew=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
 assert read(s,old,r,a).members==(1,2,3) and read(s,result.commit.pin,r,anew).members==(4,5)
 recovered=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='edit')
 assert recovered.scope.commitment==result.scope.commitment and len(recovered.scope.certificate.roots)==5;s.close()


@pytest.mark.parametrize('values,valid',[((('person',1),('person',2)),True),((('person',True),),False)])
def test_actual_lineage_pair_policy(tmp_path,values,valid):
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite','set',values,policy='lineage_pair')
 if valid:assert read(s,p,r,a).member_counts==(0,2,0)
 else:
  with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('fault',['ordinal','duplicate','key','membership','count'])
def test_scalar_extents_and_payload_projection(tmp_path,fault):
 from ate_sim.incremental_store import Membership
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite','set',(1,2,3))
 change=VersionChange(ENTRY_NAMESPACE,(2,1),(99 if fault=='ordinal' else 1 if fault=='duplicate' else 0,99 if fault=='key' else 1,None),memberships=() if fault=='membership' else (Membership('incarnation',2,99 if fault=='ordinal' else 1 if fault=='duplicate' else 0),))
 if fault=='count':change=VersionChange(DESCRIPTOR_NAMESPACE,2,('set',2,3))
 p=s.commit(p,commit_token='bad',version_changes=(change,),changes=(),new_segments=(),metadata=s.head_metadata()).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_child_add_delete_and_metadata_only_share_correct_roots(tmp_path):
 from ate_sim.persistence_proof_publication import commit_content_proof
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite',values=())
 def commit(p,a,ra,token,changes):
  result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token=token,version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata())
  return result,result.commit.pin,((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin)),(result.scope.record.certificate,result.scope.record.commitment)
 oldroot=a[1][0].roots[4]
 result,p,a,ra=commit(p,a,ra,'add',(VersionChange(PAGE_NAMESPACE,(2,0),(7,)),VersionChange(DESCRIPTOR_NAMESPACE,2,('list',1,1)),VersionChange(TYPES,2,(TAG,'list',(1,0,0)))))
 assert read(s,p,r,a).members==(7,) and a[1][0].roots[4]!=oldroot
 addedroot=a[1][0].roots[4];result,p,a,ra=commit(p,a,ra,'meta',())
 assert a[1][0].roots[4]==addedroot
 result,p,a,ra=commit(p,a,ra,'delete',(VersionChange(PAGE_NAMESPACE,(2,0),delete=True),VersionChange(DESCRIPTOR_NAMESPACE,2,('list',0,0)),VersionChange(TYPES,2,(TAG,'list',(0,0,0)))))
 assert read(s,p,r,a).members==() and a[1][0].roots[4]==oldroot;s.close()


@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_child_root_failure_and_exact_recovery(tmp_path,phase):
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite',values=())
 def fault(p):
  if p==phase:raise RuntimeError('injected')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='failure',version_changes=(VersionChange(PAGE_NAMESPACE,(2,0),(7,)),VersionChange(DESCRIPTOR_NAMESPACE,2,('list',1,1)),VersionChange(TYPES,2,(TAG,'list',(1,0,0)))),changes=(),new_segments=(),metadata=s.head_metadata())
 s._phase_hook=lambda _:None
 result=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='failure')
 assert result.commit.outcome==('committed' if phase=='after_commit' else 'not_committed')
 anew=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin) if phase=='after_commit' else a[2])
 assert read(s,result.commit.pin,r,anew).members==((7,) if phase=='after_commit' else ())
 s.close()


def test_deleted_selected_child_descriptor_fails_closed(tmp_path):
 from ate_sim import persistence_proof_scope as scope
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite');selected=scope.ChildScope(2)
 wanted=scope._map(s,4).get(a[1][0].roots[4],scope._scope_key(selected));s.db.execute('DELETE FROM ate_scope_descriptors WHERE commitment=?',(wanted,));s.db.commit()
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_child_constructor_rejects_unrepresentable_parent_id(tmp_path):
 from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite')
 p=s.commit(p,commit_token='oversize-parent',version_changes=(VersionChange(PAGE_NAMESPACE,(2**63,0),(7,)),),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 with pytest.raises(StoreError):bootstrap_scope_proofs(s,p,include_children=True)
 assert s.db.execute('SELECT 1 FROM ate_scope_generations WHERE generation=?',(p.captured_head,)).fetchone() is None;s.close()


@pytest.mark.parametrize('parent,other',[(2,2.0),(1,True)])
def test_scalar_adapter_requires_exact_typed_parent_membership(parent,other):
 from ate_sim.incremental_store import Membership
 from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
 from ate_sim.persistence_proof_projection import _ProjectionCodec
 adapter=AUXILIARY_OWNER_FAMILIES[ENTRY_NAMESPACE];codec=_ProjectionCodec()
 good=VersionChange(ENTRY_NAMESPACE,(parent,7),(0,7,None),memberships=(Membership('incarnation',parent,0),))
 adapter.validate_source(good,'lazy',codec)
 bad=VersionChange(ENTRY_NAMESPACE,(parent,7),(0,7,None),memberships=(Membership('incarnation',other,0),))
 with pytest.raises(StoreError):adapter.validate_source(bad,'lazy',codec)


def test_extent_rejects_float_parent_query_projection(tmp_path):
 from ate_sim.incremental_store import Membership
 s,p,r,a,ra=make_child_store(tmp_path/'c.sqlite','set',(1,2,3))
 p=s.commit(p,commit_token='float-parent',version_changes=(VersionChange(ENTRY_NAMESPACE,(2,1),(0,1,None),memberships=(Membership('incarnation',2.0,0),)),),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p)
 assert s.query_keys(p,ENTRY_NAMESPACE,'incarnation',2)==((2,2),(2,3))
 assert s.query_keys(p,ENTRY_NAMESPACE,'incarnation',2.0)==((2,1),)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()
