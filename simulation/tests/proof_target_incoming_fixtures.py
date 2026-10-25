from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.incremental_store import RecordChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE
from ate_sim import persistence_lazy_identity_catalog as catalog
from ate_sim import persistence_proof_record as records
from simulation.tests.proof_target_fixtures import authorities
from simulation.tests.proof_owner_target_fixtures import make_owner_target_store


def record_authority(s,p):return records._load_root(s,p.captured_head)[0]


def replace_world_body(s,p,body,*,token='body'):
 owners=(VersionChange('world.people',1,body),)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,(),next_incarnation_id=4)
 return s.commit(p,commit_token=token,version_changes=owners+delta.decode(s.codec)[0],identity_changes=(),next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin


def make_incoming_store(path,archive=0,*,body=None,wrong_aux_kind=False):
 s,p,ref,a=make_owner_target_store(path,archive=archive,wrong_kind=wrong_aux_kind)
 if body is not None:p=replace_world_body(s,p,body);a=authorities(s,p)
 return s,p,ref,a


def make_ordinary_incoming(path,body=None):
 s=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='ordinary-incoming');p=s.capture_pin();ref=HistoryReference('list',2)
 ordinary=(RecordChange('world.local',1,{'pointer':ref} if body is None else body),)
 placements=(IdentityOccurrenceChange('world.local',1,(),1),IdentityOccurrenceChange('world.local',1,(('key','pointer'),),2))
 delta=catalog.initial_catalog_delta(s.codec,(),placements,next_incarnation_id=3,generation=1,ordinary_changes=ordinary)
 p=s.commit(p,commit_token='seed',changes=ordinary,version_changes=delta.decode(s.codec)[0]+(VersionChange(DESCRIPTOR_NAMESPACE,2,('list',0,0)),),identity_changes=placements,next_incarnation_id=3,new_segments=(),metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=('world.local',catalog.LINK_NAMESPACE))).pin
 a=authorities(s,p);return s,p,ref,a,record_authority(s,p)


def rewrite_world_paths(s,p,body,paths):
 owners=(VersionChange('world.people',1,body),)
 placements=(IdentityOccurrenceChange('world.people',1,(('key','pointer'),),delete=True),)+tuple(IdentityOccurrenceChange('world.people',1,path,2) for path in paths)
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=4)
 p=s.commit(p,commit_token='paths',version_changes=owners+delta.decode(s.codec)[0],identity_changes=placements,next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 return p,authorities(s,p)
