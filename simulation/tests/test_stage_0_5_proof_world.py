import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.proof_world_fixtures import make_world

def m():return importlib.import_module('ate_sim.persistence_proof_world')


def coherent_edit(s,p,*,version_changes,identity_changes=(),changes=()):
 from ate_sim.incremental_store import RecordChange
 from ate_sim.persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
 token='d'*32
 return s.commit(p,commit_token=token,version_changes=version_changes,identity_changes=identity_changes,changes=(*changes,RecordChange(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY,(1,p.captured_head+1,token))),new_segments=(),metadata=s.head_metadata()).pin

def test_complete_world_audit_produces_real_topology_and_query_roots(tmp_path):
 s,p,a,ra,d=make_world(tmp_path/'world')
 proof=m().audit_world_roots(s,p,*a,ra,d)
 assert len(proof.roots)==7 and proof.owners==8 and proof.backings==6 and proof.projections==10
 assert proof.roots[0]==a[0][0].versions and proof.roots[1]==ra[0].root and proof.roots[4].count==4 and proof.roots[5]==a[0][0].events and proof.roots[6]==a[2][0].root
 s.close()

@pytest.mark.parametrize('kind',['missing','wrong','extra-child','unindexed-owner'])
def test_full_world_reference_and_parent_inventory_rejects_corruption(tmp_path,kind):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,HistoryReference
 from ate_sim.persistence_history_types import initial_type_change
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,a,ra,d=make_world(tmp_path/'world')
 if kind=='missing':changes=(VersionChange(DESCRIPTOR_NAMESPACE,5,delete=True),)
 elif kind=='wrong':changes=(VersionChange(DESCRIPTOR_NAMESPACE,5,('set',32,32)),)
 elif kind=='extra-child':changes=(VersionChange(PAGE_NAMESPACE,(5,9),(1,)),)
 else:
  from ate_sim.skills import SkillHistory
  change=VersionChange('world.skills.skills',(3,'craft'),SkillHistory(3,'craft',teachers=HistoryReference('list',6),provenance=HistoryReference('list',5)))
  changes=(change,)
 p=coherent_edit(s,p,version_changes=changes)
 a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 with pytest.raises(StoreError):m().audit_world_roots(s,p,*a,ra,d)
 s.close()


def copy_api():return importlib.import_module('ate_sim.persistence_proof_world_copy')
def manifest_api():return importlib.import_module('ate_sim.persistence_proof_manifest_publish')


def test_verified_copy_creates_real_genesis_and_preserves_source(tmp_path):
 import hashlib
 from ate_sim.persistence_lazy import open_lazy_world_session
 from ate_sim.persistence_proof_generation import read_generation_manifest
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened
 s,p,a,ra,d=make_world(tmp_path/'source');source=s.path;source_id=s.store_identity;s.release_pin(p);s.close()
 before=hashlib.sha256(source.read_bytes()).hexdigest();dest=tmp_path/'proof.sqlite'
 result=copy_api().copy_world_with_proofs(source,dest,rules_id='private-catalog-copy')
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 with opened(dest) as s:
  p=s.capture_pin();value=read_generation_manifest(s,p,result.commitment)
  assert value==result.manifest and value.generation==0 and value.parent_commitment is value.receipt is None
  assert value.store_identity!=source_id and value.head.simulation_position==s.codec.encode(0)
  assert value.format_version=='7' and len(value.roots)==7
  with pytest.raises(StoreError):s.commit(p,commit_token='unproved',version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
 with pytest.raises(StoreError):open_lazy_world_session(dest,rules_id='private-catalog-copy')


def test_existing_positive_generation_cannot_manufacture_manifest_parent(tmp_path):
 s,p,a,ra,d=make_world(tmp_path/'world')
 with pytest.raises(StoreError):manifest_api().bootstrap_world_manifest(s,p,*a,ra,d)
 assert not s.db.in_transaction;s.close()


def _proof_store(tmp_path,**kwargs):
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened
 s,p,a,ra,d=make_world(tmp_path/'source',**kwargs);source=s.path;s.release_pin(p);s.close()
 result=copy_api().copy_world_with_proofs(source,tmp_path/'proof.sqlite',rules_id='private-catalog-copy')
 s=opened(tmp_path/'proof.sqlite');p=s.capture_pin()
 return s,p,(result.manifest,result.commitment)


def test_manifest_checkpoint_and_noop_reuse_without_graph_body_reads(tmp_path):
 from ate_sim.persistence_proof_generation import read_generation_manifest,validate_successor
 s,p,pair=_proof_store(tmp_path);s.reset_diagnostics()
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata(),checkpoint=True)
 assert result.commit.outcome=='committed' and result.reaudited is False
 child,e=result.manifest
 validate_successor(*pair,child,e,s.codec.encode('a'*32))
 assert child.head.simulation_position==s.codec.encode(0) and child.roots[2:6]==pair[0].roots[2:6]
 assert read_generation_manifest(s,result.commit.pin,e)==child
 assert s._payload_reads==0
 noop=manifest_api().commit_world_manifest(s,result.commit.pin,*result.manifest,commit_token='b'*32,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
 assert noop.commit.outcome=='not_committed' and noop.manifest==result.manifest;s.close()


@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_manifest_atomic_recovery(tmp_path,phase):
 s,p,pair=_proof_store(tmp_path)
 def fault(at):
  if at==phase:raise RuntimeError('interrupted')
 s._phase_hook=fault
 with pytest.raises(RuntimeError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata(),checkpoint=True)
 s._phase_hook=lambda _:None
 result=manifest_api().resolve_world_manifest(s,p,*pair,commit_token='a'*32)
 assert result.commit.outcome==('committed' if phase=='after_commit' else 'not_committed')
 assert result.manifest[0].generation==(1 if phase=='after_commit' else 0);s.close()


def test_format_floor_cannot_be_raised_by_unproved_writer(tmp_path):
 s,p,a,ra,d=make_world(tmp_path/'world')
 with pytest.raises(StoreError):s.commit(p,commit_token='bad-floor',required_format_version=7,version_changes=(),changes=(),new_segments=(),metadata=dict(s.head_metadata(),simulation_position=1))
 assert s.generation==p.captured_head;s.close()


def test_context_integer_types_cannot_be_forged_without_changing_hash(tmp_path):
 s,p,pair=_proof_store(tmp_path)
 raw=s.db.execute('SELECT facts FROM ate_world_proof_contexts').fetchone()[0];facts=list(s.codec.decode(raw));assert facts[2][1]==0
 facts[2]=(facts[2][0],False);s.db.execute('UPDATE ate_world_proof_contexts SET facts=?',(s.codec.encode(tuple(facts)),));s.db.commit()
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
 s.close()


def test_namespace_native_record_schema_is_checked(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.agency import MotiveState
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,a,ra,d=make_world(tmp_path/'world')
 owners=(VersionChange('world.skills.skills',(1,'craft'),MotiveState()),)
 paths=(IdentityOccurrenceChange('world.skills.skills',(1,'craft'),(('field','teachers'),),delete=True),IdentityOccurrenceChange('world.skills.skills',(1,'craft'),(('field','provenance'),),delete=True))
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,paths,next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 p=coherent_edit(s,p,version_changes=versions,identity_changes=paths)
 a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 with pytest.raises(StoreError,match='record class'):m().audit_world_roots(s,p,*a,ra,d)
 s.close()


def test_world_field_reference_cannot_change_to_different_container_kind(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_lazy_nested_history import HistoryReference
 from ate_sim.skills import SkillHistory
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,a,ra,d=make_world(tmp_path/'world')
 owners=(VersionChange('world.skills.skills',(1,'craft'),SkillHistory(1,'craft',teachers=HistoryReference('map',3),provenance=HistoryReference('list',5))),)
 paths=(IdentityOccurrenceChange('world.skills.skills',(1,'craft'),(('field','teachers'),),3),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,paths,next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 p=coherent_edit(s,p,version_changes=versions,identity_changes=paths)
 a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 with pytest.raises(StoreError,match='member kind'):m().audit_world_roots(s,p,*a,ra,d)
 s.close()


def test_world_query_memberships_are_derived_from_actual_owner_values(tmp_path):
 from ate_sim.incremental_store import Membership
 from ate_sim import persistence_lazy_identity_catalog as cat
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,a,ra,d=make_world(tmp_path/'world')
 old=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1)
 owners=(VersionChange('world.skills.skills',(1,'craft'),old.value,memberships=(Membership('forged',9,0),)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 p=coherent_edit(s,p,version_changes=versions)
 a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 with pytest.raises(StoreError,match='query projection'):m().audit_world_roots(s,p,*a,ra,d)
 s.close()


def test_native_scalar_edit_keeps_topology_root_and_reaudits_changed_world(tmp_path):
 from dataclasses import replace
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,pair=_proof_store(tmp_path)
 old=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
 owners=(VersionChange('world.skills.skills',(1,'craft'),replace(old,level=.75)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
 assert result.commit.outcome=='committed' and result.reaudited
 assert result.manifest[0].roots[0]!=pair[0].roots[0] and result.manifest[0].roots[2]==pair[0].roots[2]
 s.close()


def test_world_metadata_cannot_diverge_from_actual_scalar_state(tmp_path):
 s,p,pair=_proof_store(tmp_path)
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(),new_segments=(),metadata=dict(s.head_metadata(),simulation_position=1))
 assert s.generation==0 and s.db.execute('SELECT COUNT(*) FROM ate_generation_manifests').fetchone()==(1,);s.close()


def test_reopen_recovery_and_retained_manifest(tmp_path):
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened
 from ate_sim.persistence_proof_generation import read_generation_manifest
 s,p,pair=_proof_store(tmp_path);old=s.capture_pin();path=s.path
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,checkpoint=True,version_changes=(),changes=(),new_segments=(),metadata=s.head_metadata())
 assert read_generation_manifest(s,old,pair[1])==pair[0];s.release_pin(old);s.close()
 with opened(path) as s:
  recovered=manifest_api().resolve_world_manifest(s,p,*pair,commit_token='a'*32)
  assert recovered.manifest==result.manifest
  try:
   wrong=manifest_api().resolve_world_manifest(s,p,*pair,commit_token='b'*32)
  except StoreError:pass
  else:assert wrong.commit.outcome=='conflict' and wrong.manifest==()


@pytest.mark.parametrize('fault',['constructor','racing-destination'])
def test_failed_copy_does_not_publish_partial_or_replace_racing_file(tmp_path,monkeypatch,fault):
 import hashlib
 import ate_sim.persistence_session as session
 s,p,a,ra,d=make_world(tmp_path/'source');source=s.path;s.release_pin(p);s.close();before=hashlib.sha256(source.read_bytes()).hexdigest();dest=tmp_path/'proof.sqlite'
 if fault=='constructor':
  def stop(*args,**kwargs):raise RuntimeError('manifest construction failed')
  monkeypatch.setattr(manifest_api(),'bootstrap_world_manifest',stop)
  with pytest.raises(RuntimeError):copy_api().copy_world_with_proofs(source,dest,rules_id='private-catalog-copy')
  assert not dest.exists()
 else:
  real=session._publish_private_cold_file
  def race(private,destination):
   if destination==dest:dest.write_bytes(b'racing file')
   return real(private,destination)
  monkeypatch.setattr(session,'_publish_private_cold_file',race)
  with pytest.raises(FileExistsError):copy_api().copy_world_with_proofs(source,dest,rules_id='private-catalog-copy')
  assert dest.read_bytes()==b'racing file'
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before


def test_missing_nonidentity_world_counter_cannot_be_certified(tmp_path):
 from ate_sim.incremental_store import RecordChange
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 s,p,a,ra,d=make_world(tmp_path/'world')
 p=coherent_edit(s,p,version_changes=(),changes=(RecordChange('world.institutions.next_notice',0,delete=True),));a,ra=authorities(s,p);d=_load(s,p.captured_head)[0]
 with pytest.raises(StoreError):m().audit_world_roots(s,p,*a,ra,d)
 s.close()


def test_existing_frozen_backing_cannot_be_mutated_by_manifest_transition(tmp_path):
 from ate_sim.core import Event,Layer
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE,ENTRY_NAMESPACE
 from ate_sim import persistence_lazy_identity_catalog as cat
 def configure(w):
  e=Event(1,0,'sealed',Layer.SOCIETY,data={'x':1});e.seal();w.events.append(e);w.event_ids.add(1);w.next_event=2
 s,p,pair=_proof_store(tmp_path,configure=configure)
 inc=next(i for i in s.iter_keys(p,DESCRIPTOR_NAMESPACE) if s.read_version(p,DESCRIPTOR_NAMESPACE,i,expected_record_schema=1).value[0]=='frozen-map')
 key=next(k for k in s.iter_keys(p,ENTRY_NAMESPACE) if k[0]==inc);old=s.read_version(p,ENTRY_NAMESPACE,key,expected_record_schema=1)
 from ate_sim.incremental_store import Membership
 owners=(VersionChange(ENTRY_NAMESPACE,key,(old.value[0],old.value[1],2),memberships=(Membership('incarnation',inc,old.value[0]),)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 with pytest.raises(StoreError,match='immutable'):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()


def test_ordinary_order_changes_are_bound_by_orders_root(tmp_path):
 from ate_sim.incremental_store import RecordChange
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,pair=_proof_store(tmp_path)
 ordinal,value=s.read_record('world.settlements',1,expected_record_schema=1)
 ordinary=(RecordChange('world.settlements',1,(ordinal+1,value)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,(),(),ordinary_changes=ordinary,next_incarnation_id=s.read_identity_state(p));versions=delta.decode(s.codec)[0]
 out=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=ordinary,new_segments=(),metadata=s.head_metadata())
 assert out.manifest[0].roots[4]!=pair[0].roots[4] and out.manifest[0].roots[2]==pair[0].roots[2];s.close()


def test_scalar_only_container_append_changes_structural_topology(tmp_path):
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE
 from ate_sim.persistence_history_types import initial_type_change
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,pair=_proof_store(tmp_path)
 old=s.read_version(p,PAGE_NAMESPACE,(5,0),expected_record_schema=1).value;values=(*old,33)
 owners=(VersionChange(PAGE_NAMESPACE,(5,0),values),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p))
 changes=(*owners,VersionChange(DESCRIPTOR_NAMESPACE,5,('list',33,33)),initial_type_change(5,'list',values),*delta.decode(s.codec)[0])
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata())
 assert result.manifest[0].roots[2]!=pair[0].roots[2];s.close()


def test_new_cyclic_backing_graph_cannot_gain_world_authority(tmp_path):
 from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE,HistoryReference
 from ate_sim.persistence_history_types import initial_type_change
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,pair=_proof_store(tmp_path)
 old=s.read_version(p,PAGE_NAMESPACE,(5,0),expected_record_schema=1).value;values=(HistoryReference('list',5),*old[1:])
 owner=(VersionChange(PAGE_NAMESPACE,(5,0),values),)
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 paths=(IdentityOccurrenceChange(PAGE_NAMESPACE,(5,0),(('index',0),),5),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owner,paths,next_incarnation_id=s.read_identity_state(p))
 changes=(*owner,initial_type_change(5,'list',values),*delta.decode(s.codec)[0])
 with pytest.raises(StoreError,match='cyclic'):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=changes,identity_changes=paths,changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()


def _audit_current(s,p):
 from simulation.tests.proof_sequence_event_fixtures import authorities
 from ate_sim.persistence_proof_directory_publish import _load
 a,ra=authorities(s,p)
 return m().audit_world_roots(s,p,*a,ra,_load(s,p.captured_head)[0])


def _catalog_edit(s,p,owners,paths=(),changes=()):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_families import FAMILIES
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,paths,ordinary_changes=tuple(c for c in changes if c.namespace in FAMILIES),next_incarnation_id=s.read_identity_state(p))
 return coherent_edit(s,p,version_changes=owners+delta.decode(s.codec)[0],identity_changes=paths,changes=changes)


@pytest.mark.parametrize('namespace',['world.currency.wallets','world.genealogy.children','world.knowledge.claim_index'])
def test_world_family_value_contract_rejects_coherent_wrong_kind(tmp_path,namespace):
 from ate_sim.persistence_lazy_nested_history import HistoryReference
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 def configure(w):
  w.currency.wallets[1]={}
  w.genealogy.children[1]=[2]
  w.knowledge.claim_index['a','b']=1
 s,p,a,ra,d=make_world(tmp_path/'world',configure=configure)
 key=('a','b') if namespace=='world.knowledge.claim_index' else 1
 skill=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
 # Existing complete backing, correct occurrences/catalog and all source roots;
 # only the consuming family's declared type is wrong.
 ref=skill.provenance if namespace!='world.genealogy.children' else s.read_version(p,'world.currency.wallets',1,expected_record_schema=1).value
 assert type(ref) is HistoryReference
 owners=(VersionChange(namespace,key,ref),)
 paths=(IdentityOccurrenceChange(namespace,key,(),ref.incarnation),)
 p=_catalog_edit(s,p,owners,paths)
 with pytest.raises(StoreError,match='family value'):_audit_current(s,p)
 s.close()


def test_backed_record_field_contract_rejects_coherent_wrong_kind(tmp_path):
 from ate_sim.persistence_lazy import open_lazy_world_session
 from ate_sim.persistence_record_headers import NAMESPACE,checked_record_header
 from ate_sim.persistence_schema import RECORD_FIELDS
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.skills import SkillHistory
 s,p,a,ra,d=make_world(tmp_path/'world',configure=lambda w:w.currency.wallets.update({1:{'iron':1}}));path=s.path;s.release_pin(p);s.close()
 with open_lazy_world_session(path,rules_id='private-catalog-copy') as runtime:
  runtime.world.settlements[1].memory['nested']=SkillHistory(9,'craft',teachers=[1])
  runtime.save()
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened
 s=opened(path);p=s.capture_pin()
 key=next(k for k in s.iter_keys(p,NAMESPACE) if checked_record_header(s.read_version(p,NAMESPACE,k,expected_record_schema=1).value)[0] is SkillHistory)
 header=list(s.read_version(p,NAMESPACE,key,expected_record_schema=1).value);values=list(header[2]);fields=RECORD_FIELDS[SkillHistory]
 map_ref=s.read_version(p,'world.currency.wallets',1,expected_record_schema=1).value
 values[fields.index('teachers')]=map_ref;header[2]=tuple(values)
 owners=(VersionChange(NAMESPACE,key,tuple(header)),)
 paths=(IdentityOccurrenceChange(NAMESPACE,key,(('field','teachers'),),map_ref.incarnation),)
 p=_catalog_edit(s,p,owners,paths)
 with pytest.raises(StoreError,match='member kind'):_audit_current(s,p)
 s.close()


def test_genesis_rebase_keeps_retired_group_query_and_membership_ordinals_equal(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_adapters import META,COLLECTION_LAYOUT,_read_cold_manifest
 from ate_sim.incremental_store import RecordChange
 s,p,a,ra,d=make_world(tmp_path/'source');owners=tuple(VersionChange('world.skills.skills',k,delete=True) for k in ((1,'craft'),(2,'craft')))
 paths=tuple(IdentityOccurrenceChange('world.skills.skills',k,path,delete=True) for k in ((1,'craft'),(2,'craft')) for path,_ in cat.IdentityCatalog(s).read_owner_identity(p,('world.skills.skills',k)).occurrences)
 layout=dict(_read_cold_manifest(s)['collections']);kind,_,chunks=layout['world.skills.skills'];layout['world.skills.skills']=(kind,0,chunks)
 p=_catalog_edit(s,p,owners,paths,(RecordChange(META,COLLECTION_LAYOUT,layout),))
 assert tuple(s.query_memberships(p,cat.GROUP_NAMESPACE,'retired',True))
 _audit_current(s,p)
 source=s.path;s.release_pin(p);s.close()
 result=copy_api().copy_world_with_proofs(source,tmp_path/'proof.sqlite',rules_id='private-catalog-copy')
 assert result.manifest.generation==0
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened
 with opened(tmp_path/'proof.sqlite') as s:
  s.verify_all();p=s.capture_pin()
  retired=tuple(s.query_memberships(p,cat.GROUP_NAMESPACE,'retired',True))
  assert retired and all(ordinal==0 for _,ordinal in retired)


@pytest.mark.parametrize('namespace',['world.skills.skills','world.settlements','world.agency.actions','world.event_ids'])
def test_manifest_rejects_invented_collection_layout_count(tmp_path,namespace):
 from ate_sim.incremental_store import RecordChange
 from ate_sim.persistence_adapters import META,COLLECTION_LAYOUT,_read_cold_manifest
 s,p,pair=_proof_store(tmp_path)
 layout=dict(_read_cold_manifest(s)['collections']);kind,size,chunks=layout[namespace];layout[namespace]=(kind,size+100,chunks)
 with pytest.raises(StoreError,match='count|layout'):
  manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(RecordChange(META,COLLECTION_LAYOUT,layout),),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()
