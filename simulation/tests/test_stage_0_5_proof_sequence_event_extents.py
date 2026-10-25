import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,PAGE_NAMESPACE,ENTRY_NAMESPACE
from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as DESC,NODE_NAMESPACE as NODE,PARENT_NAMESPACE as PARENT,LOCATOR_NAMESPACE as LOCATOR,MEMBER_NAMESPACE as MEMBER,DIRECTORY_NAMESPACE as DIRECTORY
from ate_sim.persistence_history_types import NAMESPACE as TYPES,TAG
from ate_sim.persistence_event_ids import RANGE_TAG,EXCEPTION_TAG
from ate_sim.persistence_proof_child_extents import read_target_members
from simulation.tests.proof_sequence_event_fixtures import make_store,mutate


def read(s,p,r,a,**kw):return read_target_members(s,p,r,*a,**kw)


@pytest.mark.parametrize('values,native,want',[((),False,()),((1,1,2),False,(1,1,2)),((True,1,1.0,'x',0,-1),True,(True,1,1.0,'x',0,-1))])
def test_complete_sequence_order_duplicates_and_native_equality(tmp_path,values,native,want):
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite',values=values,native=native);v=read(s,p,r,a)
 assert v.members==want and tuple(type(x) for x in v.members)==tuple(type(x) for x in want) and len(a[1][0].roots)==6;s.close()


def test_sequence_multiple_balanced_leaves(tmp_path):
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite',values=range(1,258));v=read(s,p,r,a)
 assert v.members==tuple(range(1,258)) and v.member_counts==(257,0,0) and sum(ns==NODE for ns,k in v.child_locators)==4;s.close()


@pytest.mark.parametrize('namespace,key,value',[(NODE,(2,999),('leaf',())),(PARENT,(2,999),(None,0)),(LOCATOR,(2,999),(1,0)),(MEMBER,(2,999),('member/v1',1,None,None)),(DIRECTORY,(2,b'orphan'),('directory-branch/v1',b'orphan',())),(PAGE_NAMESPACE,(2,99),(1,))])
def test_sequence_rejects_complete_inventory_surplus(tmp_path,namespace,key,value):
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite');p,a,ra=mutate(s,p,(VersionChange(namespace,key,value),))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('fault',['node','parent','locator','member','directory','types','no-directory','typed-parent','typed-locator'])
def test_sequence_rejects_bad_or_missing_reciprocal_sources(tmp_path,fault):
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite',values=(1,1,2));d=s.read_version(p,DESC,2,expected_record_schema=1).value
 if fault=='node':c=VersionChange(NODE,(2,d[2][0]),('leaf',((1,99),(2,1),(3,2))))
 elif fault=='parent':c=VersionChange(PARENT,(2,d[2][0]),delete=True)
 elif fault=='locator':c=VersionChange(LOCATOR,(2,1),(d[2][0],1))
 elif fault=='member':c=VersionChange(MEMBER,(2,1),delete=True)
 elif fault=='directory':c=VersionChange(DIRECTORY,(2,d[7][0]),delete=True)
 elif fault=='types':c=VersionChange(TYPES,2,(TAG,'sequence',(2,0,1)))
 elif fault=='no-directory':c=VersionChange(DESC,2,(*d[:7],None))
 elif fault=='typed-parent':c=VersionChange(PARENT,(2,d[2][0]),(None,False))
 else:c=VersionChange(LOCATOR,(2,1),(d[2][0],False))
 p,a,ra=mutate(s,p,(c,))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('version',[1,2])
def test_legacy_scope_cannot_certify_sequence_or_event_extents(tmp_path,version):
 for kind in ('sequence','range'):
  s,p,r,a,ra=make_store(tmp_path/f'{kind}.sqlite',kind=kind,version=version)
  with pytest.raises(StoreError):read(s,p,r,a)
  s.close()


@pytest.mark.parametrize('end,want',[(0,()),(3,(1,2,3))])
def test_compact_event_id_range(tmp_path,end,want):
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='range',end=end);v=read(s,p,r,a)
 assert v.members==want and v.child_locators==() and v.components==();s.close()


def test_exception_event_ids_preserve_exact_added_representatives(tmp_path):
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',end=5,removed=(1,4),added=(True,9.0,'x'));v=read(s,p,r,a)
 assert v.members==(2,3,5,True,9.0,'x') and tuple(type(x) for x in v.members)==(int,int,int,bool,float,str)
 assert tuple(c.target.kind for c in v.components)==('sequence','set') and v.components[0].members==(1,4) and v.components[1].members==(True,9.0,'x')
 assert read(s,p,HistoryReference('sequence',3),a).members==(1,4);s.close()


@pytest.mark.parametrize('fault',['unsorted','duplicate','outside','bool','overlap','missing-slot','swapped-slot','count','mode'])
def test_exception_event_ids_reject_bad_components_and_slots(tmp_path,fault):
 removed=(3,1) if fault=='unsorted' else (1,1) if fault=='duplicate' else (6,) if fault=='outside' else (True,) if fault=='bool' else (1,)
 added=(2.0,) if fault=='overlap' else (True,)
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',removed=removed,added=added,slot_fault='missing' if fault=='missing-slot' else 'swapped' if fault=='swapped-slot' else None)
 if fault=='count':
  d=s.read_version(p,'world.event_ids',0,expected_record_schema=1).value
  # A coherent content root binds this descriptor; owner/catalog commitment is
  # independently checked and must also reject disagreement.
  p,a,ra=mutate(s,p,(VersionChange('world.event_ids',0,(*d[:4],999)),))
 if fault=='mode':
  d=s.read_version(p,DESC,3,expected_record_schema=1).value;p,a,ra=mutate(s,p,(VersionChange(DESC,3,('ordered-sequence/v1',*d[1:8])),))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kw',[{'max_children':1},{'max_values':2},{'max_bytes':1},{'max_source_bytes':1}])
def test_shared_sequence_event_work_budgets(tmp_path,kw):
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',removed=(1,4),added=(True,9.0,'x'))
 with pytest.raises(StoreError):read(s,p,r,a,**kw)
 s.close()


def test_event_prefix_work_is_bounded_even_with_empty_result(tmp_path):
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',end=5,removed=(1,2,3,4,5))
 with pytest.raises(StoreError):read(s,p,r,a,max_values=5)
 assert read(s,p,r,a,max_values=10).members==();s.close()


@pytest.mark.parametrize('point',['before_head','before_commit','after_commit'])
def test_sixth_root_atomic_publication_retained_and_exact_recovery(tmp_path,point):
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite',values=(1,2));old=s.capture_pin();oldv=read(s,old,r,a);before=a[1][0].roots
 changes=(VersionChange(PARENT,(999,1),(None,0)),)
 def fail(name):
  if name==point:raise RuntimeError('interrupt')
 s._phase_hook=fail
 with pytest.raises(RuntimeError):commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='sixth',version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata())
 s._phase_hook=lambda _:None
 result=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='sixth')
 assert read(s,old,r,a)==oldv
 if point=='after_commit':
  aa=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
  assert result.scope.certificate.roots[:5]==before[:5] and result.scope.certificate.roots[5]!=before[5] and read(s,result.commit.pin,r,aa).members==(1,2)
 else:assert result.commit.outcome=='not_committed' and result.scope.certificate.roots==before
 s.close()


def test_sixth_root_add_delete_and_unchanged_sharing(tmp_path):
 from ate_sim.persistence_proof_publication import commit_content_proof
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite');original=a[1][0].roots[5]
 for token,changes in [('add',(VersionChange(PARENT,(999,1),(None,0)),)),('meta',()),('delete',(VersionChange(PARENT,(999,1),delete=True),))]:
  result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token=token,version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata())
  previous=a[1][0].roots[5];p=result.commit.pin
  a=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,p));ra=(result.scope.record.certificate,result.scope.record.commitment)
  assert read(s,p,r,a).members==(1,1,2)
  if token=='add':assert a[1][0].roots[5]!=original
  elif token=='meta':assert a[1][0].roots[5]==previous
  else:assert a[1][0].roots[5]==original
 s.close()


def test_native_missing_membership_directory_cannot_hide_existing_rows(tmp_path):
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite',values=(True,1.0),native=True);d=s.read_version(p,DESC,2,expected_record_schema=1).value
 p,a,ra=mutate(s,p,(VersionChange(DESC,2,(*d[:7],None,d[8])),))
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('namespace,key',[(PARENT,(2**63,1)),(LOCATOR,(2,True)),(DIRECTORY,(2,b'x'*33))])
def test_sequence_inventory_constructor_rejects_invalid_key_before_publication(tmp_path,namespace,key):
 from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
 s,p,r,a,ra=make_store(tmp_path/'s.sqlite')
 p=s.commit(p,commit_token='bad-key',version_changes=(VersionChange(namespace,key,(1,0)),),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 with pytest.raises(StoreError):bootstrap_scope_proofs(s,p,include_children=True,include_sequence=True)
 assert s.db.execute('SELECT 1 FROM ate_scope_generations WHERE generation=?',(p.captured_head,)).fetchone() is None;s.close()


def test_event_slot_mutation_is_atomically_bound_and_retained(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='range',end=3);old=s.capture_pin()
 # Add a third backing as the facade's live exception slots in the existing
 # writer; the descriptor body and exact owner/group projections move together.
 from ate_sim.persistence_lazy_sequence import LazyOrderedSequence
 from ate_sim.persistence_lazy_nested_history import initial_scalar_changes
 seq=LazyOrderedSequence(s,p,3,initial_values=(1,),value_mode='native',checked_types=True,recursive=True)
 d=(EXCEPTION_TAG,3,HistoryReference('sequence',3),HistoryReference('set',4),3)
 owner=(VersionChange('world.event_ids',0,d),)
 placements=(IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','removed')),3),IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','added')),4))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owner,placements,next_incarnation_id=5)
 changes=owner+tuple(seq.pending_changes())+initial_scalar_changes(4,'set',(True,),s.codec,checked_types=True)+delta.decode(s.codec)[0]
 result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='exceptions',version_changes=changes,identity_changes=placements,next_incarnation_id=5,changes=(),new_segments=(),metadata=s.head_metadata())
 aa=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
 assert read(s,old,r,a).members==(1,2,3)
 new=read(s,result.commit.pin,r,aa);assert new.members==(2,3,True) and type(new.members[-1]) is bool
 recovered=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='exceptions');assert recovered.scope.commitment==result.scope.commitment;s.close()
