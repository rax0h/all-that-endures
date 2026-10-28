import pytest
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

@pytest.mark.parametrize('length,target',[(129,128),(129,32),(129,0),(257,129),(257,128),(257,0),(128,0)])
def test_integer_page_shrink_preserves_prefix_and_aliases_without_full_audit(tmp_path,monkeypatch,length,target):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  shared=list(range(length))
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  v=s.skills[1,'craft'].provenance
  for _ in range(length-target):v.pop()
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('shrink invoked full audit'))
   assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert list(s.skills[1,'craft'].provenance)==list(range(target))
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  s.skills[1,'craft'].provenance.extend(range(129));assert s.save()==2;child=s.proof_manifest
 with opened(path,child) as s:assert list(s.skills[2,'craft'].provenance)==list(range(target))+list(range(129))

@pytest.mark.parametrize('fault',['before_head','before_commit','after_commit'])
def test_page_shrink_resolves_original_attempt_once(tmp_path,fault):
 path,pair=fixture(tmp_path)
 with opened(path,pair) as s:
  v=s.skills[1,'craft'].provenance;v.extend(range(97));assert s.save()==1
  v.pop()
  def stop(at):
   if at==fault:raise RuntimeError('interrupted shrink')
  s.store._phase_hook=stop
  with pytest.raises(RuntimeError):s.save()
  s.store._phase_hook=lambda _:None
  assert s.resolve_save()==(2 if fault=='after_commit' else 1)
  assert s.save()==2;child=s.proof_manifest
 with opened(path,child) as s:assert len(s.skills[2,'craft'].provenance)==128

@pytest.mark.parametrize('bad',['missing-page','extra-page','missing-header','wrong-header','wrong-types','bool-tail'])
def test_shrink_rejects_inconsistent_frozen_sources(tmp_path,bad):
 from dataclasses import replace
 from ate_sim.skills import SkillHistory
 from ate_sim.persistence_lazy_store import VersionChange
 from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as D,PAGE_NAMESPACE as P
 from ate_sim.persistence_history_types import NAMESPACE as T,TAG
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.incremental_store import StoreError
 from simulation.tests.test_stage_0_5_final_catalog_copy import opened as raw_opened
 from simulation.tests.test_stage_0_5_proof_world import manifest_api
 def configure(w):
  shared=list(range(257))
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with raw_opened(path) as s:
  p=s.capture_pin();inc=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value.provenance.incarnation
  tail=(True,)+tuple(range(1,32)) if bad=='bool-tail' else tuple(range(32))
  pages=(VersionChange(P,(inc,0),tail),VersionChange(P,(inc,1),delete=True),VersionChange(P,(inc,2),delete=True))
  if bad=='extra-page':pages=(VersionChange(P,(inc,0),delete=True),)+pages[1:]
  delta=cat.IdentityCatalog(s).prepare_delta(p,pages,(),next_incarnation_id=s.read_identity_state(p))
  versions=(VersionChange(D,inc,('list',32,32)),VersionChange(T,inc,(TAG,'list',(33 if bad=='wrong-types' else 32,0,0))))+pages+delta.decode(s.codec)[0]
  if bad=='missing-page':versions=tuple(c for c in versions if not(c.namespace==P and c.key==(inc,2)))
  if bad=='missing-header':versions=tuple(c for c in versions if not(c.namespace==cat.OWNER_NAMESPACE and c.key==(P,(inc,2))))
  if bad=='wrong-header':versions=tuple(replace(c,value=c.value[:1]+(True,)+c.value[2:]) if c.namespace==cat.OWNER_NAMESPACE and c.key==(P,(inc,2)) else c for c in versions)
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='d'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==0


def test_growth_and_shrink_compose_across_distinct_backings(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 from ate_sim.skills import SkillHistory
 def configure(w):
  first=list(range(257));second=[]
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=first)
  for i in (3,4):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=second)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  for _ in range(225):s.skills[1,'craft'].provenance.pop()
  s.skills[3,'craft'].provenance.extend(range(129))
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('mixed growth/shrink invoked audit'))
   assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert list(s.skills[1,'craft'].provenance)==list(range(32))
  assert list(s.skills[3,'craft'].provenance)==list(range(129))
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  assert s.skills[3,'craft'].provenance is s.skills[4,'craft'].provenance


def test_shrink_old_page_inspection_respects_aggregate_byte_budget(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world_tail_shrink as shrink
 from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
 from ate_sim.skills import SkillHistory
 def configure(w):
  shared=[10**4000]*1152
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  v=s.skills[1,'craft'].provenance
  for _ in range(1152):v.pop()
  inspected=[];original=shrink._parent
  def read(store,request,namespace,key):
   result=original(store,request,namespace,key)
   if namespace==PAGE_NAMESPACE:inspected.append(len(store.codec.encode(result)))
   return result
  with monkeypatch.context() as m:
   m.setattr(shrink,'_parent',read);assert s.save()==1;child=s.proof_manifest
  assert sum(inspected)<=4*1048576
 with opened(path,child) as s:assert len(s.skills[2,'craft'].provenance)==0
