"""Real accepted roots for frozen and fixed-body extent tests."""
from ate_sim.incremental_store import Membership
from ate_sim.persistence_lazy_store import VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,ENTRY_NAMESPACE
from ate_sim.persistence_nonreflexive_keys import storage_equality_key,NAMESPACE as NAN
from ate_sim.persistence_record_headers import NAMESPACE as RECORDS
from ate_sim.persistence_history_types import initial_type_change
from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_target_fixtures import make_target_store
from simulation.tests.proof_child_extent_fixtures import authorities


def frozen_changes(s,kind,values,*,inc=2,certified=True):
 values=tuple(values);base=kind.removeprefix('frozen-')
 changes=[VersionChange(DESCRIPTOR_NAMESPACE,inc,(kind,len(values),len(values),certified)),initial_type_change(inc,base,[k for k,v in values] if base=='map' else values)]
 if base=='list':changes.extend(VersionChange(PAGE_NAMESPACE,(inc,i//128),values[i:i+128]) for i in range(0,len(values),128))
 else:
  changes.extend(VersionChange(ENTRY_NAMESPACE,(inc,storage_equality_key(k)),(i,k,v),memberships=(Membership('incarnation',inc,i),)) for i,(k,v) in enumerate(values))
 return tuple(changes)


def make_frozen_store(path,kind='frozen-list',values=(1,2,3),*,certified=True,dependencies=(),archive=0):
 s,p,r,_=make_target_store(path,kind=kind)
 changes=frozen_changes(s,kind,values,certified=certified);placements=[]
 for c in changes:
  if c.namespace in AUXILIARY_OWNER_FAMILIES:
   for member,inc in AUXILIARY_OWNER_FAMILIES[c.namespace].reference_placements(c.value):placements.append(IdentityOccurrenceChange(c.namespace,c.key,member,inc))
 depchanges=[]
 for ref,descriptor in dependencies:
  ns=RECORDS if ref.__class__.__name__=='RecordReference' else NAN if ref.__class__.__name__=='NonreflexiveKeyReference' else DESCRIPTOR_NAMESPACE
  depchanges.append(VersionChange(ns,(ref.incarnation,0) if ns in (RECORDS,NAN) else ref.incarnation,descriptor))
 allocator=max([3]+[ref.incarnation+1 for ref,_ in dependencies])
 delta=catalog.IdentityCatalog(s).prepare_delta(p,tuple(c for c in changes if c.namespace in AUXILIARY_OWNER_FAMILIES),tuple(placements),next_incarnation_id=allocator)
 def rows():
  yield from changes;yield from depchanges;yield from delta.decode(s.codec)[0]
  for i in range(archive):yield VersionChange(PAGE_NAMESPACE,(i+10,0),(i,))
 p=s.commit(p,commit_token='frozen',version_changes=rows(),identity_changes=tuple(placements),next_incarnation_id=allocator,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p);return s,p,r,a,ra


def make_fixed_store(path,kind='record',*,descriptor=None,archive=0):
 s,p,r,_=make_target_store(path,kind=kind,descriptor=descriptor)
 def rows():
  for i in range(archive):yield VersionChange(PAGE_NAMESPACE,(i+10,0),(i,))
 meta=s.head_metadata();meta['simulation_position']=2
 p=s.commit(p,commit_token='fixed',version_changes=rows(),changes=(),new_segments=(),metadata=meta).pin
 a,ra=authorities(s,p);return s,p,r,a,ra


def replace(s,p,changes,*,token='corrupt'):
 p=s.commit(p,commit_token=token,version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p);return p,a,ra
