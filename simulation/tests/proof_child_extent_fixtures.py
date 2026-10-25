from ate_sim.persistence_lazy_store import VersionChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,initial_scalar_changes
from ate_sim.persistence_history_types import initial_type_change
from ate_sim.persistence_proof_record import bootstrap_record_proofs
from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
from ate_sim.persistence_proof_publication import bootstrap_content_proofs
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from ate_sim.persistence_proof_inventory import bootstrap_inventory
from simulation.tests.proof_target_fixtures import make_target_store


def authorities(s,p,*,children=True):
 ra=bootstrap_record_proofs(s,p);sa=bootstrap_scope_proofs(s,p,include_children=children);ca=bootstrap_content_proofs(s,p);bootstrap_collection_directory(s,p);ia=bootstrap_inventory(s,p)
 return (ca,sa,ia),ra


def make_child_store(path,kind='list',values=(1,2,3),*,extra=(),archive=0,policy=None):
 s,p,r,_=make_target_store(path,kind=kind)
 values=tuple(values)
 if kind=='list':changes=(VersionChange(DESCRIPTOR_NAMESPACE,2,('list',len(values),len(values))),initial_type_change(2,kind,values))+tuple(VersionChange(PAGE_NAMESPACE,(2,i//128),values[i:i+128]) for i in range(0,len(values),128))
 else:changes=initial_scalar_changes(2,kind,dict(values) if kind=='map' else values,s.codec,checked_types=True)
 if policy is not None:
  from ate_sim import persistence_lazy_identity_catalog as catalog
  from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
  ns='world.genealogy.children' if policy=='int' else 'world.lineage.children'
  owners=(VersionChange(ns,1,r),);placements=(IdentityOccurrenceChange(ns,1,(),2),)
  delta=catalog.IdentityCatalog(s).prepare_delta(p,owners,placements,next_incarnation_id=3)
  changes+=owners+delta.decode(s.codec)[0]
 else:placements=()
 def rows():
  yield from changes;yield from extra
  for i in range(archive):yield VersionChange(PAGE_NAMESPACE,(i+10,0),(i,))
 meta=s.head_metadata()
 if policy is not None:meta['namespaces']=tuple(sorted(set(meta['namespaces'])|{ns}))
 p=s.commit(p,commit_token='children',version_changes=rows(),identity_changes=placements,changes=(),new_segments=(),metadata=meta).pin
 a,ra=authorities(s,p);return s,p,r,a,ra
