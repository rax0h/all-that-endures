from dataclasses import replace
import pytest
from simulation.tests.test_stage_0_5_proof_world_session import fixture,opened
from simulation.tests.test_stage_0_5_final_catalog_copy import opened as raw_opened
from simulation.tests.test_stage_0_5_proof_world import manifest_api
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE as D,PAGE_NAMESPACE as P
from ate_sim.persistence_history_types import NAMESPACE as T,TAG
from ate_sim import persistence_lazy_identity_catalog as cat
from ate_sim.incremental_store import StoreError

@pytest.mark.parametrize('reused',[False,True])
@pytest.mark.parametrize('bad',['types-bool','types-count','live-false','reference-count','extra-child'])
def test_hostile_payload(tmp_path,reused,bad):
 def configure(w):
  shared=list(range(128)) if reused else []
  for i in (1,2):w.skills.skills[i,'craft']=SkillHistory(i,'craft',provenance=shared)
 path,pair=fixture(tmp_path,configure=configure)
 if reused:
  with opened(path,pair) as session:
   v=session.skills[1,'craft'].provenance;v.append(1);session.save();v.pop();session.save();pair=session.proof_manifest
 with raw_opened(path) as s:
  p=s.capture_pin();inc=s.read_version(p,'world.skills.skills',(1,'craft'),expected_record_schema=1).value.provenance.incarnation
  number=1 if reused else 0;n=129 if reused else 1
  pages=(VersionChange(P,(inc,number),(17,)),)
  if bad=='extra-child':pages+=(VersionChange(P,(inc,99),(31,)),)
  delta=cat.IdentityCatalog(s).prepare_delta(p,pages,(),next_incarnation_id=s.read_identity_state(p))
  witness=(TAG,'list',(n,0,0))
  if bad=='types-bool':witness=(TAG,'list',(True,0,0))
  elif bad=='types-count':witness=(TAG,'list',(n+1,0,0))
  versions=(VersionChange(D,inc,('list',n,n)),VersionChange(T,inc,witness))+pages+delta.decode(s.codec)[0]
  if bad in ('live-false','reference-count'):
   def altered(c):
    if c.namespace!=cat.OWNER_NAMESPACE or c.key!=(P,(inc,number)):return c
    h=list(c.value)
    if bad=='live-false':h[1]=False
    else:h[6]=b'fake';h[7]=1
    return replace(c,value=tuple(h))
   versions=tuple(altered(c) for c in versions)
  g=s.generation
  with pytest.raises(StoreError):manifest_api().commit_world_manifest(s,p,*pair,commit_token='c'*32,version_changes=versions,changes=(),new_segments=(),metadata=s.head_metadata())
  assert s.generation==g

@pytest.mark.parametrize('bad',['live','references','kind','schema'])
def test_classifier_retained_header_gate(tmp_path,monkeypatch,bad):
 from ate_sim import persistence_proof_world_tail_pages as classifier,persistence_proof_world as world
 path,pair=fixture(tmp_path)
 with opened(path,pair) as session:
  v=session.skills[1,'craft'].provenance;v.extend(range(97));session.save();v.pop();session.save()
  original_parent=classifier._parent;original_audit=world._audit_world;calls=[]
  def fake_parent(s,r,ns,key):
   value=original_parent(s,r,ns,key)
   if ns==cat.OWNER_NAMESPACE:
    value=list(value)
    if bad=='live':value[1]=True
    elif bad=='references':value[6]=b'fake';value[7]=1
    elif bad=='kind':value[2]='ordinary'
    else:value[4]=2
    return tuple(value)
   return value
  def audit(*a,**k):calls.append(True);return original_audit(*a,**k)
  monkeypatch.setattr(classifier,'_parent',fake_parent);monkeypatch.setattr(world,'_audit_world',audit)
  v.append(100);session.save();assert calls
