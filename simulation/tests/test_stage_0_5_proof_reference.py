"""Durable semantic facts and transitions through the real unified writer."""
import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import HistoryReference as H,PAGE_NAMESPACE,DESCRIPTOR_NAMESPACE
from simulation.tests.proof_reference_closure_fixtures import make_graph


def api():return importlib.import_module('ate_sim.persistence_proof_reference')
def publish():return importlib.import_module('ate_sim.persistence_proof_reference_publish')
def setup(tmp_path,**kw):
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',**kw)
 pair=api().bootstrap_reference_proofs(s,p,(r,),*a,record_authority=ra)
 return s,p,r,a,ra,pair

def test_durable_summary_and_selected_absence_without_payload_reads(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path);s.reset_diagnostics()
 fact=api().read_reference_certificate(s,p,*pair,r)
 assert (fact.kind,fact.incarnation,fact.targets,fact.edges,fact.immutable_targets)==('list',2,2,2,())
 assert len(fact.graph_digest)==32
 assert api().read_reference_certificate(s,p,*pair,H('list',999)) is None
 assert s._payload_reads==s._payload_check_reads==0;s.close()

@pytest.mark.parametrize('nodes',[
 {2:('list',(H('list',2),))},
 {2:('frozen-list',(H('frozen-list',3),),True),3:('frozen-list',(),True)},
 {2:('sequence',tuple(range(257)))},
 {2:('map',((1,'x'),))},
 {2:('set',(1,2))},
 {2:('record',(0,0,0,0))},
 {2:('nan-key',bytes.fromhex('fff8000000000042'))},
])
def test_checked_graph_kinds_and_mutable_cycles(tmp_path,nodes):
 s,p,r,a,ra,pair=setup(tmp_path,nodes=nodes)
 fact=api().read_reference_certificate(s,p,*pair,r)
 assert fact.targets==len(nodes) and fact.kind==nodes[2][0];s.close()

@pytest.mark.parametrize('fault',['expected','row','descriptor','node','transaction','temp','roots','duplicate','empty'])
def test_malformed_authority_sources_and_root_inventory(tmp_path,fault):
 s,p,r,a,ra,pair=setup(tmp_path)
 if fault=='expected':pair=(pair[0],b'x'*32)
 elif fault=='row':s.db.execute('UPDATE ate_reference_generations SET certificate=?',(b'[]',));s.db.commit()
 elif fault=='descriptor':s.db.execute('UPDATE ate_reference_descriptors SET raw=?',(b'[]',));s.db.commit()
 elif fault=='node':s.db.execute('DELETE FROM ate_proof_nodes');s.db.commit()
 elif fault=='transaction':s.db.execute('BEGIN')
 elif fault=='temp':s.db.execute('CREATE TEMP TABLE ate_reference_descriptors AS SELECT * FROM main.ate_reference_descriptors');s.db.commit()
 with pytest.raises(StoreError):
  if fault in ('roots','duplicate','empty'):
   roots=(r,)*({'roots':129,'duplicate':2,'empty':0}[fault]);api().bootstrap_reference_proofs(s,p,roots,*a,record_authority=ra)
  else:api().read_reference_certificate(s,p,*pair,r)
 if s.db.in_transaction:s.db.rollback()
 s.close()


def save(s,p,a,ra,pair,**kw):
 from ate_sim import persistence_proof_directory_publish as directory
 d=directory._load(s,p.captured_head)[0]
 args=dict(namespaces=(),scope_authority=a[1],record_authority=ra,commit_token='next',version_changes=(),identity_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
 args.update(kw)
 return publish().commit_reference_proofs(s,p,*pair,d,a[0],a[2],**args)


def next_authorities(result):
 v=result.inventory.content
 return ((v.certificate,v.commitment),(v.scope.certificate,v.scope.commitment),result.inventory.inventory),(v.scope.record.certificate,v.scope.record.commitment)


def test_unrelated_edit_reuses_graph_without_graph_body_reads(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path);s.reset_diagnostics();trace=[];s.db.set_trace_callback(trace.append)
 result=save(s,p,a,ra,pair,namespaces=('archive',),version_changes=(VersionChange('archive',0,{'x':1}),),metadata=dict(s.head_metadata(),namespaces=(*s.head_metadata()['namespaces'],'archive')))
 s.db.set_trace_callback(None)
 assert result.inventory.content.commit.outcome=='committed' and result.rebuilt==() and result.reused==(('list',2),)
 assert result.reference[0].root==pair[0].root
 queries=[t.lower() for t in trace if t.lower().startswith('select') and 'then payload end' in t.lower() and 'from lazy_record_versions' in t.lower()]
 assert queries and all("namespace='archive'" in t for t in queries)
 assert api().read_reference_certificate(s,result.inventory.content.commit.pin,*result.reference,r).targets==2;s.close()


def test_metadata_only_reuses_and_noop_has_no_payload_io(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path);s.reset_diagnostics()
 result=save(s,p,a,ra,pair)
 assert result.inventory.content.commit.outcome=='not_committed' and result.reference==pair
 assert s._payload_reads==s._payload_check_reads==0
 result=save(s,p,a,ra,pair,metadata=dict(s.head_metadata(),simulation_position=2))
 assert result.inventory.content.commit.outcome=='committed' and result.rebuilt==() and result.reference[0].root==pair[0].root
 assert s._payload_reads==s._payload_check_reads==0;s.close()


def test_changed_descendant_rebuilds_and_retained_pin_keeps_old_fact(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path);old=s.capture_pin();before=api().read_reference_certificate(s,p,*pair,r)
 result=save(s,p,a,ra,pair,namespaces=(PAGE_NAMESPACE,),version_changes=(VersionChange(PAGE_NAMESPACE,(3,0),(8,)),))
 pin=result.inventory.content.commit.pin;after=api().read_reference_certificate(s,pin,*result.reference,r)
 assert result.rebuilt==(('list',2),) and result.reused==() and after.graph_digest!=before.graph_digest
 assert api().read_reference_certificate(s,old,*pair,r)==before
 a2,ra2=next_authorities(result)
 s.release_pin(old)
 again=save(s,pin,a2,ra2,result.reference,commit_token='third',metadata=dict(s.head_metadata(),simulation_position=3))
 assert again.rebuilt==() and api().read_reference_certificate(s,again.inventory.content.commit.pin,*again.reference,r)==after;s.close()


@pytest.mark.parametrize('fault',['competitor','child','projection','deleted','frozen-bit'])
def test_invalid_changed_graph_aborts_all_roots(tmp_path,fault):
 from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE as SEQUENCE
 from ate_sim.persistence_history_types import initial_type_change
 nodes={2:('frozen-list',(),True)} if fault=='frozen-bit' else None
 s,p,r,a,ra,pair=setup(tmp_path,nodes=nodes)
 if fault=='competitor':change=VersionChange(SEQUENCE,3,('nonsense',))
 elif fault=='child':change=VersionChange(PAGE_NAMESPACE,(3,1),(9,))
 elif fault=='projection':change=VersionChange(PAGE_NAMESPACE,(3,0),(H('list',2),))
 elif fault=='deleted':change=VersionChange(DESCRIPTOR_NAMESPACE,3,delete=True)
 else:change=VersionChange(DESCRIPTOR_NAMESPACE,2,('frozen-list',0,0,False))
 with pytest.raises(StoreError):save(s,p,a,ra,pair,namespaces=(change.namespace,),version_changes=(change,))
 assert s.generation==1 and not s.db.in_transaction
 assert api().read_reference_certificate(s,p,*pair,r).targets==(1 if fault=='frozen-bit' else 2)
 assert s.db.execute('SELECT COUNT(*) FROM ate_reference_generations').fetchone()==(1,);s.close()


@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_atomic_failure_and_exact_recovery(tmp_path,phase):
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,r,a,ra,pair=setup(tmp_path);d=_load(s,p.captured_head)[0]
 def fault(at):
  if at==phase:raise RuntimeError('interrupted')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):save(s,p,a,ra,pair,namespaces=(PAGE_NAMESPACE,),version_changes=(VersionChange(PAGE_NAMESPACE,(3,0),(8,)),))
 s._phase_hook=lambda _:None
 recovered=publish().resolve_reference_commit(s,p,*pair,d,a[0],a[2],scope_authority=a[1],record_authority=ra,commit_token='next')
 assert recovered.inventory.content.commit.outcome==('committed' if phase=='after_commit' else 'not_committed')
 assert recovered.reference[0].generation==(2 if phase=='after_commit' else 1)
 assert api().read_reference_certificate(s,recovered.inventory.content.commit.pin,*recovered.reference,r).targets==2;s.close()


def test_reopen_exact_recovery_and_wrong_token(tmp_path):
 from ate_sim.persistence_lazy_store import LazyRecordStore
 from ate_sim.persistence_adapters import WorldCodec
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,r,a,ra,pair=setup(tmp_path);d=_load(s,p.captured_head)[0]
 result=save(s,p,a,ra,pair,namespaces=(PAGE_NAMESPACE,),version_changes=(VersionChange(PAGE_NAMESPACE,(3,0),(8,)),));s.close()
 s=LazyRecordStore.open(tmp_path/'g.sqlite',codec=WorldCodec(),expected_simulation_schema='8',expected_rules_id='reference-closure')
 out=publish().resolve_reference_commit(s,p,*pair,d,a[0],a[2],scope_authority=a[1],record_authority=ra,commit_token='next')
 assert out.reference==result.reference
 with pytest.raises(StoreError):publish().resolve_reference_commit(s,p,*pair,d,a[0],a[2],scope_authority=a[1],record_authority=ra,commit_token='wrong')
 s.close()


@pytest.mark.parametrize('component',['ate_content_generations','ate_scope_generations','ate_inventory_generations','ate_record_roots'])
def test_read_binds_actual_persisted_component_authorities(tmp_path,component):
 s,p,r,a,ra,pair=setup(tmp_path)
 column='commitment' if component=='ate_inventory_generations' else 'certificate'
 s.db.execute('UPDATE '+component+' SET '+column+'=?',(b'x'*32,));s.db.commit()
 with pytest.raises(StoreError):api().read_reference_certificate(s,p,*pair,r)
 s.close()


def test_added_incoming_alias_rebuilds_complete_group(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 s,p,r,a,ra,pair=setup(tmp_path)
 owners=(VersionChange('world.people',2,{'pointer':H('list',3)}),)
 placements=(IdentityOccurrenceChange('world.people',2,(),4),IdentityOccurrenceChange('world.people',2,(('key','pointer'),),3))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=5)
 versions=owners+delta.decode(s.codec)[0]
 before=api().read_reference_certificate(s,p,*pair,r)
 result=save(s,p,a,ra,pair,namespaces=tuple(sorted({c.namespace for c in versions})),version_changes=versions,identity_changes=placements,next_incarnation_id=5)
 after=api().read_reference_certificate(s,result.inventory.content.commit.pin,*result.reference,r)
 assert result.rebuilt==(('list',2),) and after.graph_digest!=before.graph_digest and after.edges==2;s.close()


def test_ordinary_body_change_revalidates_fact(tmp_path):
 from ate_sim.incremental_store import RecordChange
 from ate_sim.persistence_history_types import initial_type_change
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from simulation.tests.proof_target_incoming_fixtures import make_ordinary_incoming
 from simulation.tests.proof_sequence_event_fixtures import authorities
 s,p,r,a,ra=make_ordinary_incoming(tmp_path/'g.sqlite')
 p=s.commit(p,commit_token='types',version_changes=(initial_type_change(2,'list',()),),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p);pair=api().bootstrap_reference_proofs(s,p,(r,),*a,record_authority=ra)
 before=api().read_reference_certificate(s,p,*pair,r)
 ordinary=(RecordChange('world.local',1,{'pointer':r,'value':9}),)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,(),(),ordinary_changes=ordinary,next_incarnation_id=3);versions=delta.decode(s.codec)[0]
 result=save(s,p,a,ra,pair,namespaces=tuple(sorted({v.namespace for v in versions})),version_changes=versions,changes=ordinary)
 after=api().read_reference_certificate(s,result.inventory.content.commit.pin,*result.reference,r)
 assert result.rebuilt==(('list',2),) and before.graph_digest!=after.graph_digest;s.close()


@pytest.mark.parametrize('kind',['range','exceptions'])
def test_event_facts_and_components(tmp_path,kind):
 from simulation.tests.proof_sequence_event_fixtures import make_store
 s,p,r,a,ra=make_store(tmp_path/'g.sqlite',kind=kind,removed=(1,4),added=(True,9.0,'x'))
 pair=api().bootstrap_reference_proofs(s,p,(r,),*a,record_authority=ra)
 fact=api().read_reference_certificate(s,p,*pair,r)
 assert fact.kind=='event-ids' and fact.targets==(1 if kind=='range' else 3)
 out=save(s,p,a,ra,pair,metadata=dict(s.head_metadata(),simulation_position=2))
 assert out.rebuilt==() and out.reference[0].root==pair[0].root;s.close()


def test_shared_owner_change_invalidates_both_selected_roots(tmp_path):
 nodes={2:('list',()),3:('list',(7,))}
 # Give the second root an incoming path so both are live.
 nodes[2]=('list',(H('list',3),))
 s,p,r,a,ra=make_graph(tmp_path/'g.sqlite',nodes)
 pair=api().bootstrap_reference_proofs(s,p,(r,H('list',3)),*a,record_authority=ra)
 from ate_sim import persistence_lazy_identity_catalog as catalog
 changes=(VersionChange(PAGE_NAMESPACE,(2,0),(H('list',3),)),)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,changes,(),next_incarnation_id=4);versions=changes+delta.decode(s.codec)[0]
 before=api().read_reference_certificate(s,p,*pair,r)
 out=save(s,p,a,ra,pair,namespaces=tuple(sorted({v.namespace for v in versions})),version_changes=versions)
 # Exact source revision dependencies change even if raw semantic bytes agree.
 assert out.rebuilt==(('list',2),('list',3))
 assert api().read_reference_certificate(s,out.inventory.content.commit.pin,*out.reference,r)==before;s.close()


def test_oversized_descriptor_rejected_without_materialization(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path)
 s.db.execute('UPDATE ate_reference_descriptors SET raw=zeroblob(?)',(1048577,));s.db.commit()
 with pytest.raises(StoreError):api().read_reference_certificate(s,p,*pair,r)
 s.close()


def test_private_writer_arguments_rejected(tmp_path):
 s,p,r,a,ra,pair=setup(tmp_path)
 with pytest.raises(StoreError):save(s,p,a,ra,pair,_scope_proof=object())
 assert s.generation==1;s.close()
