"""Shared mutable backing edits must preserve accepted semantic authority."""
import pytest
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened

@pytest.mark.parametrize('kind',['list','map','eager-record'])
def test_native_fixed_shape_shared_backing_save_keeps_full_history_cold(tmp_path,monkeypatch,kind):
 from ate_sim import persistence_proof_world as world
 from ate_sim.core import Settlement
 def configure(w):w.settlements[1]=Settlement(1,0,0,memory={'war':.25})
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  def full(*a,**k):raise AssertionError('fixed-shape backing save walked full World history')
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',full)
   if kind=='list':s.skills[1,'craft'].provenance[0]=99
   elif kind=='map':s.world.settlements[1].memory['war']=.5
   else:s.world.settlements[1].food_stock=75.
   assert s.save()==1
   child=s.proof_manifest
 with opened(path,child) as s:
  assert s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance
  if kind=='list':assert s.skills[2,'craft'].provenance[0]==99
  elif kind=='map':assert s.world.settlements[1].memory['war']==.5
  else:assert s.world.settlements[1].food_stock==75.


def test_native_shared_backed_record_value_save_preserves_one_canonical_object(tmp_path,monkeypatch):
 from ate_sim import persistence_proof_world as world
 from ate_sim.core import Settlement
 from ate_sim.skills import SkillHistory
 def configure(w):
  record=SkillHistory(9,'nested',level=.25)
  w.settlements[1]=Settlement(1,0,0,memory={'a':record,'b':record})
 path,pair=fixture(tmp_path,configure=configure)
 with opened(path,pair) as s:
  with monkeypatch.context() as m:
   m.setattr(world,'_audit_world',lambda *a,**k:pytest.fail('backed record save invoked full audit'))
   s.world.settlements[1].memory['a'].level=.75
   assert s.world.settlements[1].memory['b'].level==.75
   assert s.save()==1;child=s.proof_manifest
 with opened(path,child) as s:
  assert s.world.settlements[1].memory['a'] is s.world.settlements[1].memory['b']
  assert s.world.settlements[1].memory['a'].level==.75


def raw_page_delta(store,pin,*,value):
 from ate_sim import persistence_lazy_identity_catalog as cat
 from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
 from ate_sim.persistence_lazy_store import VersionChange
 key=next(k for k in store.iter_keys(pin,PAGE_NAMESPACE) if len(store.read_version(pin,PAGE_NAMESPACE,k,expected_record_schema=1).value)==32)
 old=store.read_version(pin,PAGE_NAMESPACE,key,expected_record_schema=1).value
 changed=VersionChange(PAGE_NAMESPACE,key,value(old))
 delta=cat.IdentityCatalog(store).prepare_delta(pin,(changed,),(),next_incarnation_id=store.read_identity_state(pin))
 return (changed,)+delta.decode(store.codec)[0]

@pytest.mark.parametrize('edit',[lambda old:(True,)+old[1:],lambda old:old[:-1]])
def test_backing_value_reuse_cannot_bypass_member_witness_or_exact_length(tmp_path,edit):
 from simulation.tests.test_stage_0_5_proof_world import _proof_store,manifest_api
 from ate_sim.incremental_store import StoreError
 s,p,pair=_proof_store(tmp_path)
 try:
  versions=raw_page_delta(s,p,value=edit)
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==0
 finally:s.close()


def test_backing_page_with_forged_owner_witness_cannot_reuse_facts(tmp_path):
 from simulation.tests.test_stage_0_5_proof_world import _proof_store,manifest_api
 from ate_sim import persistence_lazy_identity_catalog as cat
 from dataclasses import replace
 from ate_sim.incremental_store import StoreError
 s,p,pair=_proof_store(tmp_path)
 try:
  versions=raw_page_delta(s,p,value=lambda old:(99,)+old[1:]);forged=[]
  for row in versions:
   if row.namespace==cat.OWNER_NAMESPACE:
    v=list(row.value);v[5]='0'*64;row=replace(row,value=tuple(v))
   forged.append(row)
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='a'*32,version_changes=tuple(forged),changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==0
 finally:s.close()
