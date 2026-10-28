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

@pytest.mark.parametrize('count',[1,128,129,257])
def test_empty_list_growth_uses_authenticated_empty_child_inventory(tmp_path,monkeypatch,count):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  shared=[]
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('empty growth invoked full audit'))
   s.skills[1,'craft'].provenance.extend(range(count));assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert list(s.skills[1,'craft'].provenance)==list(range(count))
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance

@pytest.mark.parametrize('fault',[None,'before_head','before_commit','after_commit'])
def test_regrowth_reuses_only_authenticated_inactive_empty_owner(tmp_path,monkeypatch,fault):
 from ate_sim import persistence_proof_world as world
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  v=s.skills[1,'craft'].provenance;v.extend(range(97));assert s.save()==1
  assert v.pop()==96;assert s.save()==2;parent=s.proof_manifest
 with opened(path,parent) as s:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('regrowth invoked full audit'))
   s.skills[1,'craft'].provenance.append(777)
   if fault:
    def stop(at):
     if at==fault:raise RuntimeError('interrupted regrowth')
    s.store._phase_hook=stop
    with pytest.raises(RuntimeError):s.save()
    s.store._phase_hook=lambda _:None
   else:assert s.save()==3
  if fault:assert s.resolve_save()==(3 if fault=='after_commit' else 2)
  assert s.save()==3;child=s.proof_manifest
 with opened(path,child) as s:
  assert len(s.skills[2,'craft'].provenance)==129 and s.skills[2,'craft'].provenance[-1]==777
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance

@pytest.mark.parametrize('empty',[False,True])
@pytest.mark.parametrize('bad',['bool','float','reference'])
def test_empty_and_reused_growth_preserves_checked_noninteger_fallback(tmp_path,monkeypatch,empty,bad):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  shared=[] if empty else list(range(128))
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  v=s.skills[1,'craft'].provenance
  if not empty:v.append(1);s.save();v.pop();s.save()
  value={'bool':True,'float':.5,'reference':[]}[bad]
  calls=[];original=world._audit_world
  def audit(*a,**k):calls.append(True);return original(*a,**k)
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',audit);v.append(value);s.save();assert calls
  child=s.proof_manifest
 with opened(path,child) as s:
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  actual=s.skills[1,'craft'].provenance[-1]
  if bad=='reference':assert list(actual)==[]
  else:assert actual==value and type(actual) is type(value)


def test_empty_and_reused_pages_compose_across_distinct_backings(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  first=[];second=list(range(129))
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=first)
  for i in (3,4):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=second)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  values=s.skills[3,'craft'].provenance
  for _ in range(129):values.pop()
  assert s.save()==1;parent=s.proof_manifest
 with opened(path,parent) as s:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('combined empty/reused growth invoked full audit'))
   s.skills[1,'craft'].provenance.extend(range(129))
   s.skills[3,'craft'].provenance.extend(range(257))
   assert s.save()==2;child=s.proof_manifest
 with opened(path,child) as s:
  assert list(s.skills[1,'craft'].provenance)==list(range(129))
  assert list(s.skills[3,'craft'].provenance)==list(range(257))
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  assert s.skills[3,'craft'].provenance is s.skills[4,'craft'].provenance
  assert s.skills[1,'craft'].provenance is not s.skills[3,'craft'].provenance
