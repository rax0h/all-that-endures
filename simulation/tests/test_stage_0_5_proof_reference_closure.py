import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference as H,PAGE_NAMESPACE,DESCRIPTOR_NAMESPACE
from ate_sim.persistence_record_headers import RecordReference as R
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference as N
from simulation.tests.proof_reference_closure_fixtures import make_graph


def read(s,p,r,a,**kw):return importlib.import_module('ate_sim.persistence_proof_reference_closure').read_reference_closure(s,p,r,*a,**kw)


def ids(v):return tuple(n.incoming.target.incarnation for n in v.targets)


def test_repeated_aliases_keep_distinct_paths_and_one_target_extent(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite');v=read(s,p,r,a,max_targets=2,max_edges=2,max_children=2,max_values=3,max_members=3)
 assert ids(v)==(2,3) and len(v.edges)==2 and tuple(e.target_incarnation for e in v.edges)==(3,3)
 assert tuple(s.codec.decode(e.path) for e in v.edges)==((('index',0),),(('index',1),)) and v.targets[1].members==(7,);s.close()


@pytest.mark.parametrize('nodes',[
 {2:('list',(H('list',2),))},
 {2:('list',(R(3),)),3:('record',(H('list',2),0,0,0))},
])
def test_mutable_cycles_terminate_and_preserve_edges(tmp_path,nodes):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',nodes);v=read(s,p,r,a)
 assert ids(v)==tuple(nodes) and len(v.edges)==len(nodes);s.close()


def test_nested_immutable_reference_paths_are_complete(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('list',((H('list',3),H('list',3)),)),3:('list',())});v=read(s,p,r,a)
 assert ids(v)==(2,3) and tuple(s.codec.decode(e.path) for e in v.edges)==((('index',0),('index',0)),(('index',0),('index',1)));s.close()


def test_map_key_nan_target_is_reached_and_exact_body_retained(tmp_path):
 bits=bytes.fromhex('fff8000000000042');s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('map',((N(3),1),)),3:('nan-key',bits)});v=read(s,p,r,a)
 assert ids(v)==(2,3) and v.targets[1].incoming.target.descriptor[1]==bits and v.immutable_targets==((3,True),);s.close()


def test_sequence_leaves_follow_stored_references(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('sequence',(H('list',3),H('list',3))),3:('list',(7,))});v=read(s,p,r,a)
 assert ids(v)==(2,3) and tuple(s.codec.decode(e.path) for e in v.edges)==((('key',1),),(('key',2),));s.close()


def test_sequence_branch_is_not_a_native_reference_owner(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('sequence',tuple(range(257)))});v=read(s,p,r,a)
 assert ids(v)==(2,) and v.edges==() and len(v.targets[0].members)==257;s.close()


@pytest.mark.parametrize('omitted',[True,False])
def test_complete_owner_projection_disagrees_with_changed_physical_body(tmp_path,omitted):
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_history_types import initial_type_change
 values=(1,) if omitted else (H('list',3),)
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('list',values),3:('list',())})
 changed=(H('list',3),) if omitted else (1,)
 # Bind changed physical bytes into accepted content while retaining the old
 # complete catalog relation. A full semantic producer would reject this;
 # raw construction intentionally does not certify that whole-World invariant.
 p=s.commit(p,commit_token='projection-mismatch',version_changes=(VersionChange(PAGE_NAMESPACE,(2,0),changed),initial_type_change(2,'list',changed)),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p)
 with pytest.raises(StoreError,match='projection'):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kind',['missing','wrong-kind','conflict'])
def test_all_reachable_targets_must_exist_with_one_typed_kind(tmp_path,kind):
 values=(H('map',3),) if kind=='wrong-kind' else (H('list',3),H('map',3)) if kind=='conflict' else (H('list',3),)
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('list',values),3:('list',())})
 if kind=='missing':
  from simulation.tests.proof_sequence_event_fixtures import authorities
  p=s.commit(p,commit_token='delete',version_changes=(VersionChange(DESCRIPTOR_NAMESPACE,3,delete=True),),changes=(),new_segments=(),metadata=s.head_metadata()).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('certified,values,child',[(True,(H('frozen-list',3),),('frozen-list',(),True)),(False,(R(3),),('record',(0,0,0,0)))])
def test_frozen_certification_is_checked_through_reached_descendants(tmp_path,certified,values,child):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('frozen-list',values,certified),3:child});v=read(s,p,r,a)
 assert ids(v)==(2,3) and (2,certified) in v.immutable_targets;s.close()


def test_false_descendant_bit_cannot_hide_an_immutable_leaf(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('frozen-list',(H('frozen-list',3),),False),3:('frozen-list',(),False)})
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('flag',[True,False])
def test_cyclic_frozen_certification_has_explicit_unsupported_path(tmp_path,flag):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('frozen-list',(H('frozen-list',2),),flag)})
 with pytest.raises(StoreError,match='cyclic frozen certification'):read(s,p,r,a)
 s.close()


@pytest.mark.parametrize('kw',[{'max_targets':1},{'max_edges':1},{'max_members':2},{'max_children':1},{'max_values':2},{'max_bytes':1},{'max_source_bytes':1},{'max_targets':True},{'max_edges':0}])
def test_closure_budgets_are_shared_across_targets(tmp_path,kw):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a,**kw)
 s.close()


def test_event_components_are_incoming_checked_and_extent_charged_once(tmp_path):
 from simulation.tests.proof_sequence_event_fixtures import make_store
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',removed=(1,4),added=(True,9.0,'x'))
 v=read(s,p,r,a,max_values=10,max_members=4);assert ids(v)==(2,3,4) and len(v.edges)==2 and v.targets[0].members==(2,3,5,True,9.0,'x')
 with pytest.raises(StoreError):read(s,p,r,a,max_values=9)
 with pytest.raises(StoreError):read(s,p,r,a,max_members=3)
 s.close()


def test_ordinary_incoming_authority_is_required_in_closure(tmp_path):
 from simulation.tests.proof_target_incoming_fixtures import make_ordinary_incoming
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_history_types import initial_type_change
 s,p,r,a,oldra=make_ordinary_incoming(tmp_path/'o.sqlite')
 p=s.commit(p,commit_token='types',version_changes=(initial_type_change(2,'list',()),),changes=(),new_segments=(),metadata=s.head_metadata()).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 assert ids(read(s,p,r,a,record_authority=ra))==(2,)
 with pytest.raises(StoreError):read(s,p,r,a,record_authority=oldra)
 s.close()


def test_missing_physical_child_cannot_reuse_old_content_hash(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite');s.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(PAGE_NAMESPACE,s.codec.encode((3,0))));s.db.commit()
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_owned_single_snapshot_and_legacy_rejection(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite');trace=[];s.db.set_trace_callback(trace.append)
 v=read(s,p,r,a);s.db.set_trace_callback(None);assert ids(v)==(2,3) and sum(t.upper().startswith('BEGIN') for t in trace)==1
 s.db.execute('BEGIN')
 with pytest.raises(StoreError):read(s,p,r,a)
 s.db.rollback();s.close()
 s,p,r,a,ra=make_graph(tmp_path/'legacy.sqlite',version=2)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_atomic_value_edit_keeps_old_and_new_closures_exact(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from ate_sim.persistence_proof_publication import commit_content_proof,resolve_content_commit
 from ate_sim.persistence_proof_inventory import bootstrap_inventory
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite');old=s.capture_pin();before=read(s,old,r,a)
 changes=(VersionChange(PAGE_NAMESPACE,(3,0),(9,)),);delta=catalog.IdentityCatalog(s).prepare_delta(p,changes,(),next_incarnation_id=4)
 result=commit_content_proof(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='closure-edit',version_changes=changes+delta.decode(s.codec)[0],changes=(),new_segments=(),metadata=s.head_metadata())
 aa=((result.certificate,result.commitment),(result.scope.certificate,result.scope.commitment),bootstrap_inventory(s,result.commit.pin))
 assert read(s,old,r,a)==before and read(s,result.commit.pin,r,aa).targets[1].members==(9,)
 recovered=resolve_content_commit(s,p,*a[0],scope_authority=a[1],record_authority=ra,commit_token='closure-edit');assert recovered.scope.commitment==result.scope.commitment;s.close()


def test_cached_event_component_still_requires_all_incoming_owner_bodies(tmp_path):
 from simulation.tests.proof_sequence_event_fixtures import make_store,authorities
 from ate_sim import persistence_lazy_identity_catalog as catalog
 s,p,r,a,ra=make_store(tmp_path/'e.sqlite',kind='exceptions',removed=(1,4),added=(True,9.0,'x'))
 owners=(VersionChange('world.people',1,{'pointer':r,'other':H('map',3)}),)
 placements=(IdentityOccurrenceChange('world.people',1,(('key','other'),),3),)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=5)
 p=s.commit(p,commit_token='bad-alias',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,changes=(),new_segments=(),metadata=s.head_metadata()).pin;a,ra=authorities(s,p)
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_source_byte_budget_is_not_reset_for_each_reached_target(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'one.sqlite',{2:('list',(7,))});assert ids(read(s,p,r,a,max_bytes=10000))==(2,);s.close()
 s,p,r,a,ra=make_graph(tmp_path/'two.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a,max_bytes=10000)
 assert ids(read(s,p,r,a))==(2,3);s.close()


def test_large_extent_cached_projection_does_not_spend_incoming_budget(tmp_path):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',{2:('list',tuple(range(40000)))})
 v=read(s,p,r,a,max_members=1,max_targets=1,max_children=313,max_values=40000,max_edges=1)
 assert ids(v)==(2,) and len(v.targets[0].members)==40000 and v.targets[0].members[128:131]==(128,129,130) and v.targets[0].members[-1]==39999 and v.edges==()
 s.close()
