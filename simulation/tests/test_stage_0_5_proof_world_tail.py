import pytest
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

@pytest.mark.parametrize('edit',['append','pop'])
def test_native_integer_tail_resize_does_not_audit_unrelated_history(tmp_path,monkeypatch,edit):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path);s=opened(path,pair)
 try:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('tail resize invoked full World audit'))
   values=s.skills[1,'craft'].provenance
   if edit=='append':values.append(99)
   else:assert values.pop()==31
   assert s.save()==1;child=s.proof_manifest
 finally:
  if s._state=='recovery-required':s.resolve_save()
  s.close()
 with opened(path,child) as s:
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  assert len(s.skills[2,'craft'].provenance)==(33 if edit=='append' else 31)
  assert s.skills[2,'craft'].provenance[-1]==(99 if edit=='append' else 30)


def test_new_history_backing_retains_checked_structural_fallback(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.world.settlements[1].memory['new']=[1,2,3]
  assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:assert list(s.world.settlements[1].memory['new'])==[1,2,3]

@pytest.mark.parametrize('fault',['before_head','before_commit','after_commit'])
def test_native_tail_resize_recovers_exact_frozen_attempt(tmp_path,fault):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].provenance.append(99)
  def stop(at):
   if at==fault:raise RuntimeError('lost tail acknowledgement')
  s.store._phase_hook=stop
  with pytest.raises(RuntimeError):s.save()
  s.store._phase_hook=lambda _:None
  expected=1 if fault=='after_commit' else 0
  assert s.resolve_save()==expected
  assert len(s.skills[2,'craft'].provenance)==33
  assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert len(s.skills[2,'craft'].provenance)==33
  assert s.skills[2,'craft'].provenance[-1]==99

@pytest.mark.parametrize('bad',['no-page','no-types','bad-count','bad-length','bool-member'])
def test_tail_resize_cannot_certify_inconsistent_frozen_rows(tmp_path,bad):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import VersionChange
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as D,PAGE_NAMESPACE as P
 from ate_sim.persistence_history_types import NAMESPACE as T,TAG
 from ate_sim.incremental_store import StoreError
 from simulation.tests.test_stage_0_5_proof_world import _proof_store,manifest_api
 s,p,pair=_proof_store(tmp_path)
 try:
  owner=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value;inc=owner.provenance.incarnation
  before=s.read_version(p,P,(inc,0),expected_record_schema=1).value
  tail=before+((True if bad=='bool-member' else 99),)+( (100,) if bad=='bad-length' else ())
  page=VersionChange(P,(inc,0),tail)
  pages=() if bad=='no-page' else (page,)
  witnesses=() if bad=='no-types' else (VersionChange(T,inc,(TAG,'list',((32 if bad=='bad-count' else 33),0,0))),)
  delta=cat.IdentityCatalog(s).prepare_delta(p,pages,(),next_incarnation_id=s.read_identity_state(p))
  versions=(VersionChange(D,inc,('list',33,33)),)+witnesses+pages+delta.decode(s.codec)[0]
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==0
 finally:s.close()


def test_native_cross_page_growth_keeps_full_audit_fallback(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path);calls=[];original=world._audit_world
 with opened(path,pair) as s:
  def audit(*args,**kw):calls.append(True);return original(*args,**kw)
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',audit)
   s.skills[1,'craft'].provenance.extend(range(97));assert s.save()==1
   assert calls;child=s.proof_manifest
 with opened(path,child) as s:assert len(s.skills[2,'craft'].provenance)==129
