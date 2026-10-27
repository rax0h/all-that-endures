import pytest
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

@pytest.mark.parametrize('count',[97,225])
def test_native_tail_growth_adds_authenticated_pages_without_full_audit(tmp_path,monkeypatch,count):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path);s=opened(path,pair)
 try:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('page growth invoked full World audit'))
   s.skills[1,'craft'].provenance.extend(range(count));assert s.save()==1;child=s.proof_manifest
 finally:
  if s._state=='recovery-required':s.resolve_save()
  s.close()
 with opened(path,child) as s:
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  assert len(s.skills[2,'craft'].provenance)==32+count
  assert s.skills[2,'craft'].provenance[-1]==count-1

@pytest.mark.parametrize('bad',['missing-page','missing-types','wrong-header','extra-page','bool-member','wrong-length'])
def test_new_page_growth_rejects_inconsistent_frozen_authority(tmp_path,bad):
 from dataclasses import replace
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_store import VersionChange
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as D,PAGE_NAMESPACE as P
 from ate_sim.persistence_history_types import NAMESPACE as T,TAG
 from ate_sim.incremental_store import StoreError
 from simulation.tests.test_stage_0_5_proof_world import _proof_store,manifest_api
 s,p,pair=_proof_store(tmp_path)
 try:
  inc=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value.provenance.incarnation
  pages=(VersionChange(P,(inc,0),tuple(range(128))),VersionChange(P,(inc,1),(True if bad=='bool-member' else 128,)))
  if bad=='extra-page':pages+= (VersionChange(P,(inc,99),(1,)),)
  delta=cat.IdentityCatalog(s).prepare_delta(p,pages,(),next_incarnation_id=s.read_identity_state(p))
  versions=(VersionChange(D,inc,('list',257 if bad=='wrong-length' else 129,257 if bad=='wrong-length' else 129)),VersionChange(T,inc,(TAG,'list',(129,0,0))))+pages+delta.decode(s.codec)[0]
  if bad=='missing-page':versions=tuple(c for c in versions if not(c.namespace==P and c.key==(inc,1)))
  if bad=='missing-types':versions=tuple(c for c in versions if c.namespace!=T)
  if bad=='wrong-header':
   versions=tuple(replace(c,value=c.value[:5]+('0'*64,)+c.value[6:]) if c.namespace==cat.OWNER_NAMESPACE and c.key==(P,(inc,1)) else c for c in versions)
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==0
 finally:s.close()

@pytest.mark.parametrize('fault',['before_head','before_commit','after_commit'])
def test_new_tail_page_recovers_original_attempt_once(tmp_path,fault):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].provenance.extend(range(97))
  def stop(at):
   if at==fault:raise RuntimeError('interrupted page growth')
  s.store._phase_hook=stop
  with pytest.raises(RuntimeError):s.save()
  s.store._phase_hook=lambda _:None
  assert s.resolve_save()==(1 if fault=='after_commit' else 0)
  assert len(s.skills[2,'craft'].provenance)==129
  assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert len(s.skills[1,'craft'].provenance)==129
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance


def test_removing_last_page_retains_checked_structural_fallback(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  s.skills[1,'craft'].provenance.extend(range(97));assert s.save()==1
  calls=[];original=world._audit_world
  def audit(*a,**kw):calls.append(True);return original(*a,**kw)
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',audit)
   assert s.skills[1,'craft'].provenance.pop()==96
   assert s.save()==2 and calls
  child=s.proof_manifest
 with opened(path,child) as s:assert len(s.skills[2,'craft'].provenance)==128


def test_regrowing_a_previously_removed_page_keeps_checked_fallback(tmp_path):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  values=s.skills[1,'craft'].provenance
  values.extend(range(97));assert s.save()==1
  assert values.pop()==96;assert s.save()==2
  values.append(97);assert s.save()==3;child=s.proof_manifest
 with opened(path,child) as s:
  assert len(s.skills[2,'craft'].provenance)==129
  assert s.skills[2,'craft'].provenance[-1]==97


def test_growth_after_an_exact_full_page_preserves_audit_equivalence(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  shared=list(range(128))
  w.skills.skills[1,'craft']=SkillHistory(1,'craft',provenance=shared)
  w.skills.skills[2,'craft']=SkillHistory(2,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('full-page boundary invoked full audit'))
   s.skills[1,'craft'].provenance.append(999);assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert len(s.skills[2,'craft'].provenance)==129
  assert s.skills[2,'craft'].provenance[-1]==999
