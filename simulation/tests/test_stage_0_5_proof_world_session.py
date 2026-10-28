"""Real native sessions, canonical identity and exact manifest receipts."""
import importlib
import pytest
from ate_sim.incremental_store import StoreError
from simulation.tests.test_stage_0_5_proof_world import _proof_store

def api():return importlib.import_module('ate_sim.persistence_proof_world_session')
def fixture(tmp_path,**kw):
 s,p,pair=_proof_store(tmp_path,**kw);path=s.path;s.release_pin(p);s.close();return path,pair

def opened(path,pair):return api().open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=pair[1])

def test_native_proof_session_saves_and_reopens_canonical_shared_history(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  s.skills[1,'craft'].level=.75
  assert s.save()==1
  child=s.proof_manifest
  assert child[0].generation==1 and child[0].parent_commitment==pair[1]
 with opened(path,child) as s:
  assert s.skills[1,'craft'].level==.75
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  s.skills[1,'craft'].provenance.append(99);assert s.save()==2;child=s.proof_manifest
 with opened(path,child) as s:assert s.skills[2,'craft'].provenance[-1]==99

@pytest.mark.parametrize('phase',['before_head','before_commit','after_commit'])
def test_native_manifest_fault_resolves_original_parent_once(tmp_path,phase):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].level=.5
  def fault(at):
   if at==phase:raise RuntimeError('interrupted')
  s.store._phase_hook=fault
  with pytest.raises(RuntimeError):s.save()
  s.store._phase_hook=lambda _:None
  generation=s.resolve_save()
  assert generation==(1 if phase=='after_commit' else 0)
  assert s.proof_manifest[0].generation==generation
  assert s.skills[1,'craft'].level==.5
  assert s.save()==1
  child=s.proof_manifest
 with opened(path,child) as s:assert s.skills[1,'craft'].level==.5

def test_native_noop_preserves_manifest_and_generation(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  assert s.save()==0 and s.proof_manifest==pair

@pytest.mark.parametrize('wrong',['digest','old-generation','other-store'])
def test_native_admission_rejects_wrong_external_authority(tmp_path,wrong):
 path,pair=fixture(tmp_path)
 if wrong=='digest':bad=(pair[0],b'\0'*32)
 elif wrong=='other-store':_,bad=fixture(tmp_path/'other')
 else:
  with opened(path,pair) as s:s.skills[1,'craft'].level=.25;s.save()
  bad=pair
 with pytest.raises(StoreError):opened(path,bad)

@pytest.mark.parametrize('external',[False,True])
def test_native_epoch_rejects_untracked_sql_before_fetch_or_save(tmp_path,external):
 import sqlite3
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  db=sqlite3.connect(path) if external else s.store.db
  db.execute("UPDATE records SET payload_checksum='corrupt' WHERE namespace='world.year'");db.commit()
  if external:db.close()
  with pytest.raises(StoreError):s.save()
  with pytest.raises(StoreError):s.skills[1,'craft']
 with pytest.raises(StoreError):opened(path,pair)


def test_native_partial_participant_acknowledgement_recovers_original_manifest(tmp_path,monkeypatch):
 from ate_sim.persistence_lazy_participants import FamilySaveParticipant
 original=FamilySaveParticipant.accept_delta;failed=[]
 def partial(self,delta,pin):
  original(self,delta,pin)
  if not failed:failed.append(True);raise RuntimeError('partial native acceptance')
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].level=.375
  monkeypatch.setattr(FamilySaveParticipant,'accept_delta',partial)
  with pytest.raises(RuntimeError):s.save()
  assert s.store.generation==1
  monkeypatch.setattr(FamilySaveParticipant,'accept_delta',original)
  assert s.resolve_save()==1 and s.save()==1
  child=s.proof_manifest
 with opened(path,child) as s:assert s.skills[1,'craft'].level==.375


def test_native_recovery_authenticates_unrelated_bodies_before_runtime_ack(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].level=.5
  def fault(at):
   if at=='after_commit':raise RuntimeError('lost acknowledgement')
  s.store._phase_hook=fault
  with pytest.raises(RuntimeError):s.save()
  s.store._phase_hook=lambda _:None
  checksum=s.store.db.execute("SELECT payload_checksum FROM records WHERE namespace='world.settlements'").fetchone()[0]
  s.store.db.execute("UPDATE records SET payload_checksum='corrupt' WHERE namespace='world.settlements'");s.store.db.commit()
  with pytest.raises(StoreError):s.resolve_save()
  assert s._pending_save is not None and s._state=='recovery-required'
  s.store.db.execute("UPDATE records SET payload_checksum=? WHERE namespace='world.settlements'",(checksum,));s.store.db.commit()
  assert s.resolve_save()==1


def test_native_proof_save_matches_old_checked_world_digest_with_events(tmp_path):
 from ate_sim.persistence_lazy import open_lazy_world_session
 from ate_sim.core import Event,Layer,_digest_world_unchecked
 path,pair=fixture(tmp_path)
 with opened(path,pair) as candidate,open_lazy_world_session(tmp_path/'source'/'complete.sqlite',rules_id='private-catalog-copy') as control:
  for s in (candidate,control):
   s.skills[1,'craft'].provenance.append(99)
   s.skills[2,'craft'].level=.5
   s.world.year=1
   s.world.events.append(Event(1,1,'proof',Layer.SOCIETY,data={'remember':3}))
   s.world.event_ids.add(1);s.world.next_event=2;s.save()
  assert _digest_world_unchecked(candidate.world)==_digest_world_unchecked(control.world)
  child=candidate.proof_manifest
 with opened(path,child) as s:
  assert s.world.year==1 and s.world.next_event==2 and len(s.world.events)==1
  assert s.world.events[0].data['remember']==3


@pytest.mark.parametrize('bad',[None,False,1,b'bad','a'*64])
def test_native_open_requires_exact_external_commitment(tmp_path,bad):
 path,pair=fixture(tmp_path)
 with pytest.raises(StoreError):api().open_audited_proof_world_session(path,rules_id='private-catalog-copy',expected_commitment=bad)


def test_native_frozen_commit_descriptor_cannot_be_silently_replaced(tmp_path,monkeypatch):
 from dataclasses import replace
 from ate_sim.persistence_lazy_families import ParticipantDelta
 from ate_sim.persistence_session import EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].level=.5
  plan=s._prepare_hybrid_save();pub=plan.publication
  records=pub.ordinary_delta.decode(s.store.codec)[1]
  records=tuple(replace(c,value=(1,plan.target_generation,'f'*32)) if (c.namespace,c.key)==(EVENT_STORAGE,COMMIT_DESCRIPTOR_KEY) else c for c in records)
  delta=ParticipantDelta.freeze(s.store.codec,pub.ordinary_delta.participant,ordinary_changes=records)
  corrupted=replace(plan,publication=replace(pub,ordinary_delta=delta))
  monkeypatch.setattr(s,'_prepare_hybrid_save',lambda:corrupted)
  with pytest.raises(StoreError,match='descriptor'):s.save()
  assert s.store.generation==0


def test_closed_native_session_does_not_expose_manifest(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:pass
 with pytest.raises(StoreError):s.proof_manifest


def test_native_manifest_is_not_exposed_during_uncertain_publication(tmp_path):
 path,pair=fixture(tmp_path);seen=[]
 with opened(path,pair) as s:
  s.skills[1,'craft'].level=.5
  def inspect(phase):
   if phase=='before_commit':
    try:s.proof_manifest
    except StoreError:seen.append('blocked')
    else:seen.append('exposed')
  s.store._phase_hook=inspect;s.save()
  assert seen==['blocked']


@pytest.mark.parametrize('ddl',["CREATE TRIGGER untracked AFTER UPDATE ON records BEGIN SELECT 1; END", "CREATE TEMP VIEW untracked AS SELECT 1"])
def test_native_epoch_rejects_untracked_schema_changes(tmp_path,ddl):
 path,pair=fixture(tmp_path);s=opened(path,pair)
 try:
  s.store.db.execute(ddl);s.store.db.commit()
  with pytest.raises(StoreError):s.proof_manifest
 finally:s.store.close()


@pytest.mark.parametrize('mismatch',['token','generation'])
def test_frozen_token_disagreement_cannot_commit_an_unrecoverable_attempt(tmp_path,monkeypatch,mismatch):
 from dataclasses import replace
 path,pair=fixture(tmp_path);s=opened(path,pair)
 try:
  s.skills[1,'craft'].level=.5;plan=s._prepare_hybrid_save()
  changes=dict(commit_token_bytes=s.store.codec.encode('f'*32)) if mismatch=='token' else dict(target_generation=plan.target_generation+1)
  altered=replace(plan,publication=replace(plan.publication,**changes))
  monkeypatch.setattr(s,'_prepare_hybrid_save',lambda:altered)
  with pytest.raises(StoreError):s.save()
  assert s.store.generation==0
 finally:s.store.close()


def test_noop_does_not_accept_a_new_epoch_without_audit(tmp_path,monkeypatch):
 import sqlite3
 path,pair=fixture(tmp_path);s=opened(path,pair)
 try:
  authority=s.store._world_proof_authority;original=authority._epoch;calls=[]
  def race():
   captured=original();calls.append(True)
   if len(calls)==2:
    with sqlite3.connect(path) as db:db.execute("UPDATE records SET payload_checksum='corrupt' WHERE namespace='world.year'")
   return captured
  monkeypatch.setattr(authority,'_epoch',race)
  assert s.save()==0
  with pytest.raises(StoreError):s.proof_manifest
 finally:s.store.close()

@pytest.mark.parametrize('operation',['save','resolve_save'])
def test_closed_proof_session_uses_store_error_without_publication(tmp_path,operation):
 path,pair=fixture(tmp_path);s=opened(path,pair);s.close()
 with pytest.raises(StoreError,match='closed'):getattr(s,operation)()
 with opened(path,pair) as fresh:assert fresh.store.generation==0
