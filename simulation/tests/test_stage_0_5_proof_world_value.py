"""Real native value changes, semantic reuse and explicit structural fallback."""
from dataclasses import replace
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_store import VersionChange
from simulation.tests.test_stage_0_5_proof_world import _proof_store,manifest_api
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened


def scalar_delta(s,p,**kw):
 from ate_sim import persistence_lazy_identity_catalog as cat
 old=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
 owners=(VersionChange('world.skills.skills',(1,'craft'),replace(old,**kw)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p))
 return owners+delta.decode(s.codec)[0]


def test_existing_world_scalar_transition_reuses_real_semantic_facts(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 s,p,pair=_proof_store(tmp_path);versions=scalar_delta(s,p,level=.5)
 def full(*a,**k):raise AssertionError('value-only transition walked full World history')
 monkeypatch.setattr(world,'_audit_world',full)
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
 assert result.commit.outcome=='committed' and not result.reaudited
 assert result.manifest[0].roots[2:]==pair[0].roots[2:]
 s.close()


def test_actual_native_scalar_save_does_not_call_full_audit(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  def full(*a,**k):raise AssertionError('native scalar save walked full history')
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',full)
   s.skills[1,'craft'].level=.5
   assert s.save()==1
   child=s.proof_manifest
 with opened(path,child) as s:
  assert s.skills[1,'craft'].level==.5
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance


def test_structural_reference_replacement_still_uses_full_audit(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_lazy_nested_history import HistoryReference
 s,p,pair=_proof_store(tmp_path)
 old=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
 owners=(VersionChange('world.skills.skills',(1,'craft'),replace(old,teachers=old.provenance)),)
 paths=(IdentityOccurrenceChange('world.skills.skills',(1,'craft'),(('field','teachers'),),old.provenance.incarnation),)
 d=cat.IdentityCatalog(s).prepare_delta(p,owners,paths,next_incarnation_id=s.read_identity_state(p))
 result=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=owners+d.decode(s.codec)[0],identity_changes=paths,changes=(),new_segments=(),metadata=s.head_metadata())
 assert result.reaudited;s.close()


def test_native_acknowledgement_cannot_write_unlisted_source_rows(tmp_path,monkeypatch):
 from ate_sim.persistence_lazy_participants import FamilySaveParticipant
 path,pair=fixture(tmp_path);s=opened(path,pair)
 original=FamilySaveParticipant.accept_delta
 def corrupt(self,delta,pin):
  self.store.db.execute("UPDATE records SET payload_checksum='corrupt' WHERE namespace='world.year'")
  return original(self,delta,pin)
 try:
  s.skills[1,'craft'].level=.5;monkeypatch.setattr(FamilySaveParticipant,'accept_delta',corrupt)
  with pytest.raises(StoreError):s.save()
  assert s.store.db.execute("SELECT payload_checksum FROM records WHERE namespace='world.year'").fetchone()[0]!='corrupt'
 finally:s.store.close()


def test_connection_write_guard_invalidates_cached_publisher_statements():
 import sqlite3,importlib
 from ate_sim.persistence_sqlite_guard import GuardedConnection
 db=sqlite3.connect(':memory:',factory=GuardedConnection);db.execute('CREATE TABLE source(x)');db.execute('INSERT INTO source VALUES(1)');db.commit()
 Guard=importlib.import_module('ate_sim.persistence_proof_native_guard').NativeWriteGuard
 with Guard(db) as guard:
  with guard.publisher():db.execute('UPDATE source SET x=2');db.commit()
  with pytest.raises(sqlite3.DatabaseError):db.execute('UPDATE source SET x=2')
 assert db.execute('SELECT x FROM source').fetchone()==(2,);db.close()


@pytest.mark.parametrize('fault',['query','missing-witness','wrong-witness','inactive-lease'])
def test_value_only_producer_rejects_false_semantic_witnesses(tmp_path,fault):
 from ate_sim.incremental_store import Membership
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_history_dependencies import NAMESPACE as DEPS
 s,p,pair=_proof_store(tmp_path);versions=list(scalar_delta(s,p,level=.5))
 if fault=='query':versions[0]=replace(versions[0],memberships=(Membership('invented',1,0),))
 elif fault=='missing-witness':versions=[c for c in versions if c.namespace!=cat.OWNER_NAMESPACE]
 elif fault=='wrong-witness':
  i=next(i for i,c in enumerate(versions) if c.namespace==cat.OWNER_NAMESPACE);v=list(versions[i].value);v[3]+=1;versions[i]=replace(versions[i],value=tuple(v))
 else:
  old=s.read_version(p,DEPS,5,expected_record_schema=1).value
  versions.append(VersionChange(DEPS,5,(old[0],old[1],('inactive',))))
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=tuple(versions),changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()


def test_shared_inline_native_records_keep_checked_alias_fallback(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 def configure(w):w.skills.skills[2,'craft']=w.skills.skills[1,'craft']
 path,pair=fixture(tmp_path,configure=configure);calls=[];original=world._audit_world
 with opened(path,pair) as s:
  assert s.skills[1,'craft'] is s.skills[2,'craft']
  def checked(*a,**k):calls.append(True);return original(*a,**k)
  monkeypatch.setattr(world,'_audit_world',checked)
  s.skills[1,'craft'].level=.5;assert s.save()==1 and calls;child=s.proof_manifest
 with opened(path,child) as s:assert s.skills[1,'craft'] is s.skills[2,'craft'] and s.skills[2,'craft'].level==.5


def test_native_sql_guard_preserves_caller_authorizer_and_blocks_replacement():
 import sqlite3
 from ate_sim.persistence_sqlite_guard import GuardedConnection
 from ate_sim.persistence_proof_native_guard import NativeWriteGuard
 db=sqlite3.connect(':memory:',factory=GuardedConnection);db.execute('CREATE TABLE source(x)')
 def caller(action,first,second,database,source):
  return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_INSERT and first=='source' else sqlite3.SQLITE_OK
 db.set_authorizer(caller)
 with NativeWriteGuard(db) as guard:
  with guard.publisher():
   with pytest.raises(sqlite3.DatabaseError):db.execute('INSERT INTO source VALUES(1)')
  with pytest.raises(StoreError):db.set_authorizer(None)
  with pytest.raises(StoreError):guard.check()
 assert db._known_authorizer is caller;db.close()


@pytest.mark.parametrize('namespace,value',[('world.year',(0,1)),('world.institutions.next_notice',1)])
def test_value_reuse_cannot_invent_head_or_counter_envelope(tmp_path,namespace,value):
 from ate_sim.incremental_store import RecordChange
 s,p,pair=_proof_store(tmp_path)
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(RecordChange(namespace,0,value),),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()


@pytest.mark.parametrize('query_value',[False,0])
def test_value_transition_checks_exact_derived_query_before_reuse(tmp_path,query_value):
 from ate_sim.core import Person
 from ate_sim.incremental_store import Membership
 from ate_sim import persistence_lazy_identity_catalog as cat
 def configure(w):w.people[1]=Person(1,0,1,1);w.next_person=2
 s,p,pair=_proof_store(tmp_path,configure=configure)
 old=s.read_version(p,'world.people',1,expected_record_schema=1).value
 ordinal=s._visible_order('world.people',s.codec.encode(1),p.captured_head)[0]
 owners=(VersionChange('world.people',1,replace(old,alive=False),memberships=(Membership('alive',query_value,ordinal),)),)
 delta=cat.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=s.read_identity_state(p));versions=owners+delta.decode(s.codec)[0]
 def save():return manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
 if type(query_value) is int:
  with pytest.raises(StoreError):save()
 else:
  result=save();assert not result.reaudited and result.manifest[0].roots[2]==pair[0].roots[2] and result.manifest[0].roots[3]!=pair[0].roots[3]
 s.close()


def test_native_scalar_keeps_sealed_event_archive_payloads_cold(tmp_path,monkeypatch):
 from ate_sim.core import Event,Layer
 from ate_sim import persistence_proof_world as world
 def configure(w):
  from ate_sim.event_log import EventLog
  w.events=EventLog(Event(i+1,0,'archived',Layer.SOCIETY) for i in range(2048))
  w.events.seal_before(1);w.year=1
  w.event_ids.update(range(1,2049));w.next_event=2049
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  reads=[]
  def trace(sql):
   t=sql.lower()
   import re
   if t.startswith('select') and (re.search(r'(?:select|,|then)\s*payload\b',t) or re.match(r'select\s+\*',t)) and 'from segments' in t:reads.append(t)
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('native scalar reread full event archive'))
   s.store.db.set_trace_callback(trace)
   try:s.skills[1,'craft'].level=.5;assert s.save()==1
   finally:s.store.db.set_trace_callback(None)
  assert reads==[] and len(s.world.events)==2048


def test_value_transition_preserves_event_counter_authority_with_matching_head(tmp_path):
 from ate_sim.incremental_store import RecordChange
 s,p,pair=_proof_store(tmp_path);metadata=s.head_metadata();metadata['next_ids']['next_event']=999
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(),changes=(RecordChange('world.next_event',0,(0,999)),),new_segments=(),metadata=metadata)
 assert s.generation==0;s.close()


@pytest.mark.parametrize('direction',['add','remove'])
def test_value_transition_cannot_change_another_active_publishers_lease(tmp_path,direction):
 from ate_sim.persistence_history_dependencies import NAMESPACE as DEPS,dependency_value
 s,p,pair=_proof_store(tmp_path)
 if direction=='remove':
  r=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(VersionChange(DEPS,5,dependency_value('list',(p.token,))),),changes=(),new_segments=(),metadata=s.head_metadata());p=r.commit.pin;pair=r.manifest
 q=s.capture_pin();tokens=(p.token,) if direction=='add' else ()
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,q,*pair,commit_token='b'*32,version_changes=(VersionChange(DEPS,5,dependency_value('list',tokens)),),changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==p.captured_head;s.close()


@pytest.mark.parametrize('release',['own','expired'])
def test_value_transition_allows_own_release_and_inactive_lease_pruning(tmp_path,release):
 from ate_sim.persistence_history_dependencies import NAMESPACE as DEPS,dependency_value
 s,p,pair=_proof_store(tmp_path)
 r=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(VersionChange(DEPS,5,dependency_value('list',(p.token,))),),changes=(),new_segments=(),metadata=s.head_metadata());p=r.commit.pin;pair=r.manifest
 if release=='expired':s.release_pin(p);p=s.capture_pin()
 r=manifest_api().commit_world_manifest(s,p,*pair,commit_token='b'*32,version_changes=(VersionChange(DEPS,5,dependency_value('list')),),changes=(),new_segments=(),metadata=s.head_metadata())
 assert r.commit.outcome=='committed' and not r.reaudited;s.close()


def test_semantic_validation_uses_frozen_payload_not_mutable_caller_value(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 s,p,pair=_proof_store(tmp_path);ns='world.skills.skills';key=(1,'craft')
 old=s.read_version(p,ns,key,expected_record_schema=1).value
 altered=replace(old,teachers=old.provenance)
 header=list(s.read_version(p,cat.OWNER_NAMESPACE,(ns,key),expected_record_schema=1).value);header[3]=p.captured_head+1
 versions=(VersionChange(ns,key,altered),VersionChange(cat.OWNER_NAMESPACE,(ns,key),tuple(header)))
 def mutate(phase):
  if phase=='before_transaction':altered.teachers=old.teachers
 s._phase_hook=mutate
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==0;s.close()


def test_foreign_lease_release_cannot_hide_in_structural_fallback(tmp_path):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim.persistence_history_dependencies import NAMESPACE as DEPS,dependency_value
 s,p,pair=_proof_store(tmp_path)
 r=manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=(VersionChange(DEPS,5,dependency_value('list',(p.token,))),),changes=(),new_segments=(),metadata=s.head_metadata());p=r.commit.pin;pair=r.manifest;q=s.capture_pin()
 old=s.read_version(q,'world.skills.skills',(1,'craft'),expected_record_schema=1).value
 owners=(VersionChange('world.skills.skills',(1,'craft'),replace(old,teachers=old.provenance)),)
 paths=(IdentityOccurrenceChange('world.skills.skills',(1,'craft'),(('field','teachers'),),old.provenance.incarnation),)
 delta=cat.IdentityCatalog(s).prepare_delta(q,owners,paths,next_incarnation_id=s.read_identity_state(q))
 versions=owners+delta.decode(s.codec)[0]+(VersionChange(DEPS,5,dependency_value('list')),)
 with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,q,*pair,commit_token='b'*32,version_changes=versions,identity_changes=paths,changes=(),new_segments=(),metadata=s.head_metadata())
 assert s.generation==1;s.close()


def test_sql_trace_callback_cannot_inject_unlisted_publisher_writes(tmp_path):
 path,pair=fixture(tmp_path);s=opened(path,pair);attempts=[]
 def trace(sql):
  if sql.startswith('UPDATE save_head SET') and not attempts:
   attempts.append(True)
   s.store.db.execute("UPDATE records SET payload_checksum='trace-corrupt' WHERE namespace='world.settlements'")
 try:
  s.store.db.set_trace_callback(trace);s.skills[1,'craft'].level=.5
  try:s.save()
  except StoreError:pass
  finally:s.store.db.set_trace_callback(None)
  assert attempts and s.store.db.execute("SELECT payload_checksum FROM records WHERE namespace='world.settlements'").fetchone()[0]!='trace-corrupt'
 finally:s.store.close()


def test_sql_trace_callback_cannot_write_during_entry_epoch_check(tmp_path):
 path,pair=fixture(tmp_path);s=opened(path,pair);attempts=[]
 def trace(sql):
  if sql=='PRAGMA main.schema_version' and not attempts:
   attempts.append(True)
   s.store.db.execute("UPDATE records SET payload_checksum='entry-corrupt' WHERE namespace='world.settlements'")
 try:
  s.store.db.set_trace_callback(trace)
  try:s.save()
  except StoreError:pass
  finally:s.store.db.set_trace_callback(None)
  assert attempts and s.store.db.execute("SELECT payload_checksum FROM records WHERE namespace='world.settlements'").fetchone()[0]!='entry-corrupt'
 finally:s.store.close()


@pytest.mark.parametrize('during',['trace','progress'])
def test_sql_callback_cannot_reuse_a_preexisting_cursor_write(during):
 import sqlite3
 from ate_sim.persistence_sqlite_guard import GuardedConnection
 from ate_sim.persistence_proof_native_guard import NativeWriteGuard
 db=sqlite3.connect(':memory:',factory=GuardedConnection);db.execute('CREATE TABLE source(x)');cursor=db.execute('INSERT INTO source VALUES(1)');db.commit();attempts=[]
 def callback(*args):
  if not attempts:
   attempts.append(True)
   try:cursor.execute('UPDATE source SET x=999')
   except (StoreError,sqlite3.DatabaseError):pass
  return 0
 with NativeWriteGuard(db) as guard:
  if during=='trace':db.set_trace_callback(callback)
  else:db.set_progress_handler(callback,1)
  with guard.publisher():db.execute('SELECT 1').fetchone()
  db.set_trace_callback(None);db.set_progress_handler(None,0)
  assert attempts and db.execute('SELECT x FROM source').fetchone()==(1,)
  with pytest.raises(StoreError):guard.check()
 db.close()
