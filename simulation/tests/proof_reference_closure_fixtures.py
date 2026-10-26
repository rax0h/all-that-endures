"""Real catalog/content/scope roots for directed raw reference graphs."""
from ate_sim.incremental_store import Membership
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE,PAGE_NAMESPACE,ENTRY_NAMESPACE
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence,NODE_NAMESPACE,PARENT_NAMESPACE
from ate_sim.persistence_record_headers import RecordReference,NAMESPACE as RECORDS
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference,NAMESPACE as NAN,TAG as NAN_TAG,storage_equality_key
from ate_sim.persistence_history_types import initial_type_change
from ate_sim.persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES as AUX
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_sequence_event_fixtures import authorities


def ref(kind,inc):return RecordReference(inc) if kind=='record' else NonreflexiveKeyReference(inc) if kind=='nan-key' else HistoryReference(kind,inc)


def make_graph(path,nodes=None,*,root=2,archive=0,version=3):
 if nodes is None:nodes={2:('list',(HistoryReference('list',3),HistoryReference('list',3))),3:('list',(7,))}
 s=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='reference-closure');p=s.capture_pin();changes=[]
 for inc,spec in sorted(nodes.items()):
  kind,values=spec[:2]
  if kind=='sequence':changes.extend(LazyOrderedSequence(s,p,inc,initial_values=values,value_mode='native',recursive=True,checked_types=True).pending_changes())
  elif kind=='record':changes.append(VersionChange(RECORDS,(inc,0),('recursive-record/v1','core.LocalState/v1',tuple(values),None)))
  elif kind=='nan-key':changes.append(VersionChange(NAN,(inc,0),(NAN_TAG,values)))
  else:
   base=kind.removeprefix('frozen-');values=tuple(values)
   changes.extend((VersionChange(DESCRIPTOR_NAMESPACE,inc,(kind,len(values),len(values))+((spec[2],) if kind.startswith('frozen-') else ())),initial_type_change(inc,base,[k for k,v in values] if base=='map' else values)))
   if base=='list':changes.extend(VersionChange(PAGE_NAMESPACE,(inc,i//128),values[i:i+128]) for i in range(0,len(values),128))
   else:
    entries=values if base=='map' else [(k,None) for k in values]
    changes.extend(VersionChange(ENTRY_NAMESPACE,(inc,storage_equality_key(k)),(i,k,v),memberships=(Membership('incarnation',inc,i),)) for i,(k,v) in enumerate(entries))
 reference=ref(nodes[root][0],root);world=VersionChange('world.people',1,{'pointer':reference});owners=[world];placements=[IdentityOccurrenceChange('world.people',1,(),1),IdentityOccurrenceChange('world.people',1,(('key','pointer'),),root)]
 for c in changes:
  if c.namespace not in AUX or c.namespace==NODE_NAMESPACE and c.value[0]=='branch':continue
  owners.append(c)
  for path,inc in AUX[c.namespace].reference_placements(c.value):
   placements.append(IdentityOccurrenceChange(c.namespace,c.key,path,inc))
 allocator=max(nodes)+1
 delta=catalog.initial_catalog_delta(s.codec,owners,placements,next_incarnation_id=allocator,generation=1)
 def rows():
  yield world;yield from changes;yield from delta.decode(s.codec)[0]
  for i in range(archive):yield VersionChange(PARENT_NAMESPACE,(i+100,1),(None,0))
 p=s.commit(p,commit_token='graph',version_changes=rows(),identity_changes=placements,next_incarnation_id=allocator,changes=(),new_segments=(),metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=('world.people',catalog.LINK_NAMESPACE))).pin
 a,ra=authorities(s,p,version=version);return s,p,reference,a,ra
