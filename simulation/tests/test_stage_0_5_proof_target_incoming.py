import importlib
import pytest
from ate_sim.incremental_store import StoreError
from ate_sim.persistence_lazy_nested_history import HistoryReference
from ate_sim.persistence_proof_target_group import read_target_group
from simulation.tests.proof_target_fixtures import make_target_store,authorities,KINDS
from simulation.tests.proof_target_incoming_fixtures import make_incoming_store,make_ordinary_incoming,replace_world_body,record_authority
from simulation.tests.proof_owner_target_fixtures import PAGE


def read(s,p,r,a,**kw):return importlib.import_module('ate_sim.persistence_proof_target_incoming').read_target_incoming(s,p,r,*a,**kw)


def test_all_incoming_payloads_and_paths(tmp_path):
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite');v=read(s,p,r,a)
 assert v.target.kind=='list' and len(v.group.occurrences)==3 and len(v.owners)==2
 assert [(o.namespace,s.codec.decode(o.typed_key),tuple(s.codec.decode(x) for x in o.paths)) for o in v.owners]==[(PAGE,(3,0),((('index',0),),(('index',1),))),('world.people',1,((('key','pointer'),),))]
 assert v.owners[0].source.payload==s.codec.encode((r,r));s.close()


@pytest.mark.parametrize('kind',KINDS)
def test_all_target_kinds_in_actual_owner_body(tmp_path,kind):
 s,p,r,a=make_target_store(tmp_path/'i.sqlite',kind=kind);v=read(s,p,r,a)
 assert v.target.kind==kind and len(v.owners)==(2 if kind=='event-ids' else 1);s.close()


@pytest.mark.parametrize('fault',['kind','id','missing','extra','aux-kind'])
def test_valid_group_metadata_cannot_substitute_for_owner_payload(tmp_path,fault):
 ref=HistoryReference('list',2);body={'pointer':ref,'owner':HistoryReference('list',3)}
 if fault=='kind':body['pointer']=HistoryReference('map',2)
 elif fault=='id':body['pointer']=HistoryReference('list',3)
 elif fault=='missing':body['pointer']=123
 elif fault=='extra':body['unrecorded']=ref
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite',body=body if fault!='aux-kind' else None,wrong_aux_kind=fault=='aux-kind')
 assert len(read_target_group(s,p,r,*a).group.occurrences)==3
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_ordinary_body_requires_its_accepted_root(tmp_path):
 s,p,r,a,ra=make_ordinary_incoming(tmp_path/'i.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a)
 v=read(s,p,r,a,record_authority=ra)
 assert v.owners[0].storage_kind=='ordinary' and v.owners[0].source.payload==s.codec.encode({'pointer':r})
 with pytest.raises(StoreError):read(s,p,r,a,record_authority=(ra[0],b'x'*32))
 s.close()


def test_retained_ordinary_payload_survives_current_overwrite(tmp_path):
 from ate_sim.incremental_store import RecordChange
 from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
 from ate_sim import persistence_lazy_identity_catalog as catalog
 s,p,r,a,ra=make_ordinary_incoming(tmp_path/'i.sqlite');old=s.capture_pin()
 changes=(RecordChange('world.local',1,{'moved':r}),);placements=(IdentityOccurrenceChange('world.local',1,(('key','pointer'),),delete=True),IdentityOccurrenceChange('world.local',1,(('key','moved'),),2))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,(),placements,ordinary_changes=changes,next_incarnation_id=3)
 p=s.commit(p,commit_token='move',changes=changes,version_changes=delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=3,new_segments=(),metadata=s.head_metadata()).pin
 anew=authorities(s,p);ranew=record_authority(s,p)
 assert read(s,old,r,a,record_authority=ra).owners[0].paths==(s.codec.encode((('key','pointer'),)),)
 assert read(s,p,r,anew,record_authority=ranew).owners[0].paths==(s.codec.encode((('key','moved'),)),)
 with pytest.raises(StoreError):read(s,p,r,anew,record_authority=ra)
 s.close()


@pytest.mark.parametrize('kw',[{'max_members':2},{'max_members':True},{'max_bytes':1},{'max_source_bytes':1},{'max_metadata_bytes':1}])
def test_incoming_budgets(tmp_path,kw):
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite')
 with pytest.raises(StoreError):read(s,p,r,a,**kw)
 s.close()


@pytest.mark.parametrize('fault',['codec','transaction','shadow','view','authority'])
def test_incoming_guards(tmp_path,fault):
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite')
 if fault=='codec':s.codec.decode=lambda _:pytest.fail('caller codec hook invoked')
 elif fault=='transaction':s.db.execute('BEGIN')
 elif fault=='shadow':s.db.execute('CREATE TEMP TABLE save_head AS SELECT * FROM main.save_head');s.db.commit()
 elif fault=='view':s.db.execute('ALTER TABLE save_head RENAME TO old_head');s.db.execute('CREATE VIEW save_head AS SELECT * FROM old_head');s.db.commit()
 elif fault=='authority':a=(a[0],(a[1][0],b'x'*32),a[2])
 with pytest.raises(StoreError):read(s,p,r,a)
 if s.db.in_transaction:s.db.rollback()
 s.close()


def test_declared_record_fields_are_inert_and_preserve_nested_paths(tmp_path):
 from ate_sim.core import LocalState,Ref
 from simulation.tests.proof_target_incoming_fixtures import rewrite_world_paths
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite')
 body={'node':LocalState((Ref('person',1),r),0,0,0),'owner':HistoryReference('list',3)}
 path=(('key','node'),('field','rain'),('index',1));p,a=rewrite_world_paths(s,p,body,(path,))
 class Poison:
  @property
  def rain(self):return None
  @rain.setter
  def rain(self,value):pytest.fail('caller mutable record restored')
 s.codec._record_by_name['core.LocalState/v1']=Poison
 v=read(s,p,r,a);assert v.owners[1].paths==(s.codec.encode(path),);s.close()


def test_event_envelope_and_field_reference(tmp_path):
 from ate_sim.core import Event,Layer
 from simulation.tests.proof_target_incoming_fixtures import rewrite_world_paths
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite')
 body=Event(1,1,'test',Layer.NARRATIVE,(),None,(),r)
 path=(('field','data'),);p,a=rewrite_world_paths(s,p,body,(path,))
 assert read(s,p,r,a).owners[1].paths==(s.codec.encode(path),);s.close()


@pytest.mark.parametrize('payload',[
 b'["record","unregistered.Bad/v1",[]]',
 b'["record","core.LocalState/v1",[["rain",["none"]]]]',
 b'["ate_event/v1",false,true,["record","core.Event/v1",[]]]',
 b'["typed-history/v1","list",true]',
 b'["dict",[[["str","x"],["none"]],[["str","x"],["none"]]]]',
])
def test_closed_owner_payload_rejects_malformed_schema(payload):
 module=importlib.import_module('ate_sim.persistence_proof_owner_payload')
 with pytest.raises(StoreError):module.world_target_paths(payload,'list',2)


def test_inline_record_counterpart_is_not_a_typed_backing_pointer(tmp_path):
 from ate_sim.core import LocalState
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite',body={'pointer':LocalState(0,0,0,0),'owner':HistoryReference('list',3)})
 assert read_target_group(s,p,r,*a).target.kind=='list'
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()


def test_group_and_owner_bodies_share_one_byte_budget(tmp_path):
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite')
 assert len(read_target_group(s,p,r,*a,max_bytes=8000).group.occurrences)==3
 with pytest.raises(StoreError):read(s,p,r,a,max_bytes=8000)
 assert len(read(s,p,r,a,max_bytes=9000).owners)==2;s.close()


def test_repeated_paths_fetch_each_owner_body_once_in_one_snapshot(tmp_path):
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite');sql=[];s.db.set_trace_callback(sql.append)
 v=read(s,p,r,a);s.db.set_trace_callback(None)
 for namespace in (PAGE,'world.people'):
  bodies=[q for q in sql if 'then payload end' in q.lower() and 'from lazy_record_versions' in q.lower() and f"namespace='{namespace}'" in q]
  assert len(bodies)==1
 assert sum(q=='BEGIN' for q in sql)==1 and sum(q in ('ROLLBACK','COMMIT') for q in sql)==1
 assert len(v.owners[0].paths)==2;s.close()


def test_deleted_retained_ordinary_body_rejects_even_with_valid_catalog(tmp_path):
 s,p,r,a,ra=make_ordinary_incoming(tmp_path/'i.sqlite')
 s.db.execute('DELETE FROM ate_retained_records');s.db.commit()
 assert len(read_target_group(s,p,r,*a).group.occurrences)==1
 with pytest.raises(StoreError):read(s,p,r,a,record_authority=ra)
 s.close()


@pytest.mark.parametrize('container',['key','set'])
def test_unroutable_inline_key_and_set_references_fail_closed(tmp_path,container):
 r=HistoryReference('list',2);body={'pointer':r,'owner':HistoryReference('list',3)}
 body['unsupported']={r:1} if container=='key' else frozenset((r,))
 s,p,r,a=make_incoming_store(tmp_path/'i.sqlite',body=body)
 assert len(read_target_group(s,p,r,*a).group.occurrences)==3
 with pytest.raises(StoreError):read(s,p,r,a)
 s.close()
