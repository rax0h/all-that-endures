"""Real published catalog fixtures for counted sequence/Event-ID raw extents."""
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,initial_scalar_changes
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence,PARENT_NAMESPACE
from ate_sim.persistence_event_id_reference import EventIdReference
from ate_sim.persistence_event_ids import RANGE_TAG,EXCEPTION_TAG
from ate_sim import persistence_lazy_identity_catalog as catalog
from ate_sim.persistence_proof_record import bootstrap_record_proofs
from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
from ate_sim.persistence_proof_publication import bootstrap_content_proofs
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from ate_sim.persistence_proof_inventory import bootstrap_inventory


def authorities(s,p,*,version=3):
 ra=bootstrap_record_proofs(s,p)
 opts=dict(include_children=version>=2)
 if version==3:opts['include_sequence']=True
 sa=bootstrap_scope_proofs(s,p,**opts);ca=bootstrap_content_proofs(s,p);bootstrap_collection_directory(s,p);ia=bootstrap_inventory(s,p)
 return (ca,sa,ia),ra


def make_store(path,*,kind='sequence',values=(1,1,2),native=False,end=5,removed=(),added=(),archive=0,version=3,extra=(),slot_fault=None):
 s=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='sequence-event-extents');p=s.capture_pin();changes=[]
 if kind=='sequence':
  ref=HistoryReference('sequence',2);seq=LazyOrderedSequence(s,p,2,initial_values=values,value_mode='native' if native else 'integer_ids',checked_types=True,recursive=True);changes.extend(seq.pending_changes());allocator=3
 else:
  ref=EventIdReference(2);allocator=3
  if kind=='range':descriptor=(RANGE_TAG,end)
  else:
   seq=LazyOrderedSequence(s,p,3,initial_values=removed,value_mode='native',checked_types=True,recursive=True);changes.extend(seq.pending_changes());changes.extend(initial_scalar_changes(4,'set',added,s.codec,checked_types=True));allocator=5
   descriptor=(EXCEPTION_TAG,end,HistoryReference('sequence',3),HistoryReference('set',4),end-len(removed)+len(set(added)))
  changes.append(VersionChange('world.event_ids',0,descriptor))
 owners=[VersionChange('world.people',1,{'pointer':ref})]
 if kind!='sequence':owners.append(changes[-1])
 placements=[IdentityOccurrenceChange('world.people',1,(),1),IdentityOccurrenceChange('world.people',1,(('key','pointer'),),2)]
 if kind!='sequence':placements.append(IdentityOccurrenceChange('world.event_ids',0,(),2))
 if kind=='exceptions':
  placements.extend((IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','removed')),3),IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','added')),4)))
  if slot_fault=='missing':placements.pop()
  elif slot_fault=='swapped':placements[-2:]=[IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','removed')),4),IdentityOccurrenceChange('world.event_ids',0,(('field','_exact'),('field','added')),3)]
 delta=catalog.initial_catalog_delta(s.codec,owners,placements,next_incarnation_id=allocator,generation=1)
 def rows():
  yield owners[0];yield from changes;yield from delta.decode(s.codec)[0];yield from extra
  for i in range(archive):yield VersionChange(PARENT_NAMESPACE,(i+100,1),(None,0))
 p=s.commit(p,commit_token='seed',version_changes=rows(),identity_changes=placements,next_incarnation_id=allocator,changes=(),new_segments=(),metadata=dict(simulation_position=1,seed=7,next_ids={},namespaces=('world.people','world.event_ids',catalog.LINK_NAMESPACE))).pin
 a,ra=authorities(s,p,version=version);return s,p,ref,a,ra


def mutate(s,p,changes):
 p=s.commit(p,commit_token='mutate',version_changes=changes,changes=(),new_segments=(),metadata=s.head_metadata()).pin
 a,ra=authorities(s,p);return p,a,ra
