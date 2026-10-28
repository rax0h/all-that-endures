"""Frozen/fixed extent behavior using coherent accepted source roots."""
import pytest
from ate_sim.incremental_store import StoreError,Membership
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,ENTRY_NAMESPACE
from ate_sim.persistence_record_headers import RecordReference,NAMESPACE as RECORDS
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference,NAMESPACE as NAN,TAG as NAN_TAG
from ate_sim.persistence_history_types import NAMESPACE as TYPES,TAG
from ate_sim.persistence_proof_child_extents import read_target_members
from simulation.tests.proof_frozen_extent_fixtures import make_frozen_store,make_fixed_store,replace


def read(s,p,r,a,**kw):return read_target_members(s,p,r,*a,**kw)


@pytest.mark.parametrize('kind,values,want,counts',[
 ('frozen-list',(1,True,2.0),(1,True,2.0),(1,0,2)),
 ('frozen-map',(('a',1),('b',2)),(('a',1),('b',2)),(0,0,2)),
 ('frozen-list',(),(),(0,0,0)),('frozen-map',(),(),(0,0,0)),
])
def test_frozen_members_and_base_type_witness(tmp_path,kind,values,want,counts):
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',kind,values)
 v=read(s,p,r,a);assert v.members==want and v.member_counts==counts and v.certification_targets==();s.close()


def test_frozen_list_complete_multi_page_order(tmp_path):
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=range(257));v=read(s,p,r,a)
 assert len(v.members)==257 and v.members[127:130]==(127,128,129) and v.members[-1]==256 and len(v.child_locators)==3;s.close()


@pytest.mark.parametrize('kind,values',[('frozen-list',()),('frozen-list',(1,)),('frozen-map',(('a',1),))])
def test_false_frozen_certification_rejects_immutable_values(tmp_path,kind,values):
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',kind,values,certified=False)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kind,values,certified',[
 ('frozen-list',(HistoryReference('list',3),),False),
 ('frozen-map',(('a',HistoryReference('list',3)),),False),
 ('frozen-list',(HistoryReference('list',3),),True),
])
def test_frozen_certification_follows_values_not_map_keys(tmp_path,kind,values,certified):
 dep=HistoryReference('list',3)
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',kind,values,certified=certified,dependencies=((dep,('list',0,0)),))
 if certified:
  with pytest.raises(StoreError):read(s,p,r,a)
 else:assert read(s,p,r,a).members==values
 s.close()


@pytest.mark.parametrize('ref,descriptor',[
 (HistoryReference('frozen-list',3),('frozen-list',0,0,True)),
 (HistoryReference('frozen-map',3),('frozen-map',0,0,True)),
 (NonreflexiveKeyReference(3),(NAN_TAG,bytes.fromhex('7ff8000000000042'))),
])
def test_frozen_certification_targets_are_authenticated_and_deduplicated(tmp_path,ref,descriptor):
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=((ref,ref),ref),dependencies=((ref,descriptor),))
 v=read(s,p,r,a,max_certification_targets=1)
 assert v.members==((ref,ref),ref) and len(v.certification_targets)==1 and v.certification_targets[0].incarnation==3 and v.certification_targets[0].descriptor==descriptor;s.close()


def test_frozen_dependency_false_bit_is_preserved(tmp_path):
 ref=HistoryReference('frozen-list',3)
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=(ref,),certified=False,dependencies=((ref,('frozen-list',1,1,False)),))
 assert read(s,p,r,a).certification_targets[0].descriptor==('frozen-list',1,1,False);s.close()


@pytest.mark.parametrize('fault',['kind','missing','bit','late-missing','nested-late-missing'])
def test_referenced_certification_requires_accepted_typed_target_even_after_false(tmp_path,fault):
 ref=HistoryReference('frozen-list',3);values=((HistoryReference('list',2),ref),) if fault=='nested-late-missing' else (HistoryReference('list',2),ref) if fault=='late-missing' else (ref,)
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=values,certified=fault not in ('late-missing','nested-late-missing'),dependencies=((ref,('list',0,0) if fault=='kind' else ('frozen-list',0,0,False if fault=='bit' else True)),))
 if fault in ('missing','late-missing','nested-late-missing'):p,a,ra=replace(s,p,(VersionChange(DESCRIPTOR_NAMESPACE,3,delete=True),))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('fault',['far','hole','shape','family','types','ordinal','membership'])
def test_frozen_extent_rejects_coherent_bad_physical_sources(tmp_path,fault):
 kind='frozen-map' if fault in ('ordinal','membership') else 'frozen-list';values=(('a',1),) if kind=='frozen-map' else range(129)
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',kind,values)
 change={
 'far':VersionChange(PAGE_NAMESPACE,(2,999),(1,)),
 'hole':VersionChange(PAGE_NAMESPACE,(2,1),delete=True),
 'shape':VersionChange(PAGE_NAMESPACE,(2,1),()),
 'family':VersionChange(ENTRY_NAMESPACE,(2,'z'),(0,'z',1),memberships=(Membership('incarnation',2,0),)),
 'types':VersionChange(TYPES,2,(TAG,'list',(0,0,129))),
 'ordinal':VersionChange(ENTRY_NAMESPACE,(2,'a'),(1,'a',1),memberships=(Membership('incarnation',2,1),)),
 'membership':VersionChange(ENTRY_NAMESPACE,(2,'a'),(0,'a',1),memberships=(Membership('incarnation',2.0,0),)),
 }[fault]
 p,a,ra=replace(s,p,(change,))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kw',[{'max_children':1},{'max_values':128},{'max_bytes':1},{'max_source_bytes':1},{'max_certification_targets':True},{'max_certification_targets':0}])
def test_frozen_extent_budgets(tmp_path,kw):
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=range(129))
 with pytest.raises(StoreError):read(s,p,r,a,**kw)
 s.close()


def test_distinct_certification_targets_share_explicit_limit(tmp_path):
 a3,a4=HistoryReference('frozen-list',3),HistoryReference('frozen-map',4)
 s,p,r,a,ra=make_frozen_store(tmp_path/'f.sqlite',values=(a3,a4),dependencies=((a3,('frozen-list',0,0,True)),(a4,('frozen-map',0,0,True))))
 with pytest.raises(StoreError):read(s,p,r,a,max_certification_targets=1)
 assert len(read(s,p,r,a,max_certification_targets=2).certification_targets)==2;s.close()


def test_record_members_preserve_schema_order_and_raw_event_state(tmp_path):
 s,p,r,a,ra=make_fixed_store(tmp_path/'r.sqlite',descriptor=('recursive-record/v1','core.LocalState/v1',(1,2,3,4),None));v=read(s,p,r,a)
 assert v.members==( ('rain',1),('drought',2),('flood',3),('scarcity',4)) and v.member_counts==(4,0,0) and v.child_locators==((RECORDS,(2,0)),)
 with pytest.raises(StoreError):read(s,p,r,a,max_values=3)
 s.close()
 header=('recursive-record/v1','core.Event/v1',(7,12,'test','surface',(),None,(),None),(True,True))
 s,p,r,a,ra=make_fixed_store(tmp_path/'e.sqlite',descriptor=header);v=read(s,p,r,a)
 assert tuple(k for k,_ in v.members)==('id','year','kind','layer','actors','location','causes','data') and v.incoming.target.descriptor==header;s.close()


def test_nan_body_preserves_exact_payload_and_has_no_members(tmp_path):
 header=(NAN_TAG,bytes.fromhex('fff8000000000042'))
 s,p,r,a,ra=make_fixed_store(tmp_path/'n.sqlite','nan-key',descriptor=header);v=read(s,p,r,a)
 assert v.members==() and v.member_counts==(0,0,0) and v.incoming.target.descriptor==header and v.child_locators==((NAN,(2,0)),);s.close()


@pytest.mark.parametrize('kind',['record','nan-key'])
def test_fixed_body_rejects_competing_children_and_legacy_authority(tmp_path,kind):
 from simulation.tests.proof_target_fixtures import make_target_store
 s,p,r,a=make_target_store(tmp_path/'legacy.sqlite',kind=kind)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()
 s,p,r,a,ra=make_fixed_store(tmp_path/'bad.sqlite',kind)
 p,a,ra=replace(s,p,(VersionChange(PAGE_NAMESPACE,(2,0),(1,)),))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kind',['frozen-list','frozen-map','record','nan-key'])
def test_new_extent_kinds_preserve_atomic_retained_and_exact_recovery(tmp_path,kind):
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 if kind.startswith('frozen-'):s,p,r,a,ra=make_frozen_store(tmp_path/'s.sqlite',kind,(1,) if kind=='frozen-list' else (('a',1),))
 else:s,p,r,a,ra=make_fixed_store(tmp_path/'s.sqlite',kind)
 old=s.capture_pin();before=read(s,old,r,a)
 if kind=='frozen-list':change=VersionChange(PAGE_NAMESPACE,(2,0),(2,))
 elif kind=='frozen-map':change=VersionChange(ENTRY_NAMESPACE,(2,'a'),(0,'a',2),memberships=(Membership('incarnation',2,0),))
 elif kind=='record':change=VersionChange(RECORDS,(2,0),('recursive-record/v1','core.LocalState/v1',(1,2,3,4),None))
 else:change=VersionChange(NAN,(2,0),(NAN_TAG,bytes.fromhex('7ff8000000000042')))
 result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='extent-edit',version_changes=(change,),changes=(),new_segments=(),metadata=s.head_metadata())
 newa=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
 assert read(s,old,r,a)==before and read(s,result.commit.pin,r,newa)!=before
 recovered=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='extent-edit')
 assert recovered.scope.commitment==result.scope.commitment;s.close()


@pytest.mark.parametrize('kind',['record','nan-key'])
def test_fixed_target_cannot_satisfy_history_bucket_kind(tmp_path,kind):
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from simulation.tests.proof_child_extent_fixtures import authorities
 s,p,r,a,ra=make_fixed_store(tmp_path/'s.sqlite',kind)
 owners=(VersionChange('world.genealogy.children',1,r),);placements=(IdentityOccurrenceChange('world.genealogy.children',1,(),2),)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=3)
 meta=s.head_metadata();meta['namespaces']=tuple(sorted(set(meta['namespaces'])|{'world.genealogy.children'}))
 p=s.commit(p,commit_token='bad-bucket',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,changes=(),new_segments=(),metadata=meta).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_certification_dependencies_share_aggregate_source_budget(tmp_path):
 refs=(HistoryReference('frozen-list',3),HistoryReference('frozen-map',4))
 for n in (1,2):
  s,p,r,a,ra=make_frozen_store(tmp_path/f'{n}.sqlite',values=refs[:n],dependencies=tuple((ref,(ref.kind,0,0,True)) for ref in refs[:n]))
  if n==1:assert len(read(s,p,r,a,max_bytes=7000).certification_targets)==1
  else:
   with pytest.raises(StoreError):read(s,p,r,a,max_bytes=7000)
   assert len(read(s,p,r,a).certification_targets)==2
  s.close()


def test_parent_and_child_certification_changes_preserve_retained_and_recovery(tmp_path):
 from simulation.tests.proof_reference_closure_fixtures import make_graph
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_history_types import initial_type_change
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 child=HistoryReference('frozen-list',3);mutable=HistoryReference('list',4)
 s,p,r,a,ra=make_graph(tmp_path/'bits.sqlite',{2:('frozen-list',(child,),True),3:('frozen-list',(),True),4:('list',())})
 old=s.capture_pin();before=read(s,old,r,a)
 owner=VersionChange(PAGE_NAMESPACE,(3,0),(mutable,));placements=(IdentityOccurrenceChange(PAGE_NAMESPACE,(3,0),(('index',0),),4),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,(owner,),placements,next_incarnation_id=5)
 changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,('frozen-list',1,1,False)),VersionChange(DESCRIPTOR_NAMESPACE,3,('frozen-list',1,1,False)),initial_type_change(3,'list',(mutable,)),owner)+delta.decode(s.codec)[0]
 result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='both-bits',version_changes=changes,identity_changes=placements,next_incarnation_id=5,changes=(),new_segments=(),metadata=s.head_metadata())
 newa=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
 assert read(s,old,r,a)==before
 after=read(s,result.commit.pin,r,newa);assert after.certification_targets[0].descriptor==('frozen-list',1,1,False)
 assert read(s,result.commit.pin,child,newa).members==(mutable,)
 recovered=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='both-bits')
 assert recovered.commit.pin.captured_head==result.commit.pin.captured_head and recovered.scope.commitment==result.scope.commitment
 assert read(s,old,r,a)==before;s.close()
