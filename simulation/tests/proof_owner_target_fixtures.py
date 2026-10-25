from simulation.tests.proof_target_fixtures import make_target_store,authorities
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE
from ate_sim import persistence_lazy_identity_catalog as catalog
PAGE='aux.lazy.nested.list_pages'

def make_owner_target_store(path,archive=0,*,wrong_kind=False):
 s,p,ref,_=make_target_store(path,archive=archive)
 stored=HistoryReference('map',2) if wrong_kind else ref
 owners=(VersionChange('world.people',1,{'pointer':ref,'owner':HistoryReference('list',3)}),VersionChange(PAGE,(3,0),(stored,stored)))
 placements=(IdentityOccurrenceChange('world.people',1,(('key','owner'),),3),IdentityOccurrenceChange(PAGE,(3,0),(('index',0),),2),IdentityOccurrenceChange(PAGE,(3,0),(('index',1),),2))
 delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=4)
 p=s.commit(p,commit_token='owner',version_changes=owners+delta.decode(s.codec)[0]+(VersionChange(DESCRIPTOR_NAMESPACE,3,('list',2,2)),),identity_changes=placements,next_incarnation_id=4,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 return s,p,ref,authorities(s,p)
