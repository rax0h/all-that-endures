import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE
from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_nonreflexive_keys import NAMESPACE as NAN,nonreflexive_key_header
from simulation.tests.proof_target_fixtures import make_target_store,KINDS,authorities

def m():return importlib.import_module('ate_sim.persistence_proof_target')
def read(s,p,ref,a,**kw):return m().read_reference_target(s,p,ref,*a,**kw)

@pytest.mark.parametrize('kind',KINDS)
def test_each_closed_reference_has_one_checked_target(tmp_path,kind):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite',kind);r=read(s,p,ref,a)
 assert r.incarnation==2 and r.kind==kind and r.generation==1 and r.payload and r.namespace
 assert not hasattr(r,'native');s.close()

def test_mismatched_kind_and_missing_target_rejected(tmp_path):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite')
 with pytest.raises(StoreError):read(s,p,HistoryReference('map',2),a)
 with pytest.raises(StoreError):read(s,p,HistoryReference('list',3),a)
 s.close()

def test_competing_backing_kinds_rejected(tmp_path):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite',extra=(VersionChange(NAN,(2,0),nonreflexive_key_header(float('nan'))),))
 with pytest.raises(StoreError):read(s,p,ref,a)
 s.close()

@pytest.mark.parametrize('value',[('list',1,0),('map',0,0),('list',False,0)])
def test_malformed_or_wrong_descriptor_rejected(tmp_path,value):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite',descriptor=value)
 with pytest.raises(StoreError):read(s,p,ref,a)
 s.close()

@pytest.mark.parametrize('kw',[{'max_bytes':1},{'max_source_bytes':1},{'max_metadata_bytes':1},{'max_bytes':True}])
def test_explicit_byte_budgets(tmp_path,kw):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite')
 with pytest.raises(StoreError):read(s,p,ref,a,**kw)
 s.close()

@pytest.mark.parametrize('fault',['missing','empty-group','retired','wrong-root-placement','expected','context','codec-hook','temp-shadow','node-view','inventory-row','content-row','borrowed'])
def test_target_liveness_context_and_closed_sources(tmp_path,fault):
 from ate_sim import persistence_lazy_identity_catalog as catalog
 from ate_sim.persistence_lazy_identity_retired import RetiredIdentityRanges
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite','event-ids' if fault=='wrong-root-placement' else 'list')
 if fault in ('missing','empty-group','retired','wrong-root-placement'):
  changes=[];placements=()
  if fault=='missing':changes.append(VersionChange(DESCRIPTOR_NAMESPACE,2,delete=True))
  elif fault=='empty-group':
   h=list(s.read_version(p,catalog.GROUP_NAMESPACE,2,expected_record_schema=1).value);h[2]=0;h[4]=0;changes.append(VersionChange(catalog.GROUP_NAMESPACE,2,tuple(h)))
  elif fault=='retired':
   r=RetiredIdentityRanges(s,p);r.add(2);changes.extend(r.pending_changes())
   h=list(s.read_version(p,catalog.CATALOG_NAMESPACE,0,expected_record_schema=1).value);h[3]-=1;h[4]=r.header;changes.append(VersionChange(catalog.CATALOG_NAMESPACE,0,tuple(h)))
  else:placements=(IdentityOccurrenceChange('world.event_ids',0,(),delete=True),IdentityOccurrenceChange('world.event_ids',0,(('key','bad'),),2))
  p=s.commit(p,commit_token='bad',version_changes=changes,identity_changes=placements,next_incarnation_id=3,changes=(),new_segments=(),metadata=s.head_metadata()).pin;a=authorities(s,p)
 elif fault=='expected':a=((a[0][0],b'x'*32),*a[1:])
 elif fault=='context':
  from dataclasses import replace
  from ate_sim.persistence_proof_scope import certificate_commitment
  c=replace(a[1][0],next_incarnation_id=4);a=(a[0],(c,certificate_commitment(c)),a[2])
 elif fault=='codec-hook':s.codec.decode=lambda _:pytest.fail('store decoder hook invoked')
 elif fault=='temp-shadow':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head');s.db.commit()
 elif fault=='node-view':
  s.db.execute('ALTER TABLE ate_ordered_seek_nodes RENAME TO saved_nodes');s.db.execute('CREATE VIEW ate_ordered_seek_nodes AS SELECT * FROM saved_nodes');s.db.commit()
 elif fault=='inventory-row':s.db.execute('DELETE FROM ate_inventory_generations');s.db.commit()
 elif fault=='content-row':s.db.execute('DELETE FROM ate_content_generations');s.db.commit()
 elif fault=='borrowed':s.db.execute('BEGIN')
 with pytest.raises(StoreError):read(s,p,ref,a)
 if s.db.in_transaction:s.db.rollback()
 s.close()

def test_retained_exact_target_kind_after_successor(tmp_path):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite');old=s.capture_pin()
 p2=s.commit(p,commit_token='new',version_changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,('list',1,1)),VersionChange('aux.lazy.nested.list_pages',(2,0),(11,))),changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a2=authorities(s,p2)
 assert read(s,old,ref,a).descriptor==('list',0,0)
 assert read(s,p2,ref,a2).descriptor==('list',1,1)
 with pytest.raises(StoreError):read(s,p2,ref,a)
 s.close()

def test_ordinary_core_ref_is_not_a_backing_pointer(tmp_path):
 from ate_sim.core import Ref
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite')
 with pytest.raises(StoreError):read(s,p,Ref('person',2),a)
 with pytest.raises(StoreError):read(s,p,HistoryReference('list',1),a)
 s.close()

def test_live_group_requires_one_checked_physical_placement(tmp_path):
 s,p,ref,a=make_target_store(tmp_path/'target.sqlite')
 s.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE incarnation_id=2');s.db.commit()
 with pytest.raises(StoreError):read(s,p,ref,a)
 s.close()

@pytest.mark.parametrize('fault',['rechecksummed-descriptor','uncommitted-competing-kind','deleted-descriptor'])
def test_raw_target_rejects_physical_corruption_behind_accepted_roots(tmp_path,fault):
 from ate_sim.persistence_lazy_store import _version_checksum
 from ate_sim.incremental_store import _framed_sha
 from ate_sim import persistence_proof_publication as content
 s,p,ref,a=make_target_store(tmp_path/'physical.sqlite');typed=s.codec.encode(2)
 if fault=='rechecksummed-descriptor':
  schema,version,start,end,members=s.db.execute('SELECT record_schema,codec_version,valid_from,valid_to,memberships FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(DESCRIPTOR_NAMESPACE,typed)).fetchone()
  payload=s.codec.encode(('list',1,1));checksum=_version_checksum(DESCRIPTOR_NAMESPACE,typed,schema,version,start,end,members,payload)
  s.db.execute('UPDATE lazy_record_versions SET payload=?,payload_checksum=?,row_checksum=? WHERE namespace=? AND typed_key=?',(payload,_framed_sha(b'lazy-payload-v1',payload),checksum,DESCRIPTOR_NAMESPACE,typed));s.db.commit()
 elif fault=='deleted-descriptor':s.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',(DESCRIPTOR_NAMESPACE,typed));s.db.commit()
 else:
  key=s.codec.encode((2,0));payload=s.codec.encode(nonreflexive_key_header(float('nan')));members=s.codec.encode(())
  checksum=_version_checksum(NAN,key,1,s.codec.version,p.captured_head,None,members,payload)
  # A coherent physical competing source is absent from accepted content roots.
  s.db.execute('INSERT INTO lazy_record_versions(namespace,typed_key,valid_from,valid_to,record_schema,codec_version,payload,payload_checksum,memberships,row_checksum) VALUES(?,?,?,NULL,1,?,?,?,?,?)',(NAN,key,p.captured_head,s.codec.version,payload,_framed_sha(b'lazy-payload-v1',payload),members,checksum));s.db.commit()
 if fault!='deleted-descriptor':assert content._source_version(s,p.captured_head,NAN if fault=='uncommitted-competing-kind' else DESCRIPTOR_NAMESPACE,key if fault=='uncommitted-competing-kind' else typed).payload==payload
 with pytest.raises(StoreError):read(s,p,ref,a)
 s.close()
