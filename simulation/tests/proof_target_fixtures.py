"""Real published catalog roots and small closed backing descriptors."""
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference,DESCRIPTOR_NAMESPACE as HISTORY
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence
from ate_sim.persistence_record_headers import RecordReference,NAMESPACE as RECORDS
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference,nonreflexive_key_header,NAMESPACE as NAN
from ate_sim.persistence_event_id_reference import EventIdReference
from ate_sim.persistence_event_ids import RANGE_TAG
from ate_sim import persistence_lazy_identity_catalog as catalog
from ate_sim.persistence_proof_record import bootstrap_record_proofs
from ate_sim.persistence_proof_scope import bootstrap_scope_proofs
from ate_sim.persistence_proof_publication import bootstrap_content_proofs
from ate_sim.persistence_proof_collection_directory import bootstrap_collection_directory
from ate_sim.persistence_proof_inventory import bootstrap_inventory

KINDS=('list','map','set','sequence','frozen-list','frozen-map','record','nan-key','event-ids')

def authorities(s,p):
 bootstrap_record_proofs(s,p);scope=bootstrap_scope_proofs(s,p);content=bootstrap_content_proofs(s,p);bootstrap_collection_directory(s,p);inventory=bootstrap_inventory(s,p)
 return content,scope,inventory

def make_target_store(path,kind='list',archive=0,*,extra=(),descriptor=None):
 s=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='target-proof-test');p=s.capture_pin();backings=[]
 if kind in ('list','map','set','frozen-list','frozen-map'):
  ref=HistoryReference(kind,2);value=(kind,0,0)+( (True,) if kind.startswith('frozen-') else ())
  backings=[VersionChange(HISTORY,2,value if descriptor is None else descriptor)]
 elif kind=='sequence':
  ref=HistoryReference(kind,2);sequence=LazyOrderedSequence(s,p,2,initial_values=(),checked_types=False);backings=list(sequence.pending_changes())
 elif kind=='record':
  ref=RecordReference(2);backings=[VersionChange(RECORDS,(2,0),('recursive-record/v1','core.LocalState/v1',(0,0,0,0),None) if descriptor is None else descriptor)]
 elif kind=='nan-key':ref=NonreflexiveKeyReference(2);backings=[VersionChange(NAN,(2,0),nonreflexive_key_header(float('nan')) if descriptor is None else descriptor)]
 elif kind=='event-ids':ref=EventIdReference(2)
 else:raise ValueError(kind)
 owners=[VersionChange('world.people',1,{'pointer':ref})];placements=[IdentityOccurrenceChange('world.people',1,(),1),IdentityOccurrenceChange('world.people',1,(('key','pointer'),),2)]
 if kind=='event-ids':
  owners.append(VersionChange('world.event_ids',0,(RANGE_TAG,3) if descriptor is None else descriptor));placements.append(IdentityOccurrenceChange('world.event_ids',0,(),2))
 delta=catalog.initial_catalog_delta(s.codec,owners,placements,next_incarnation_id=3,generation=1);witnesses=delta.decode(s.codec)[0]
 def versions():
  yield from owners;yield from backings;yield from witnesses;yield from extra
  for j in range(archive):yield VersionChange('archive',j,{'old':j})
 meta=dict(simulation_position=1,seed=7,next_ids={},namespaces=('world.people','world.event_ids','archive',catalog.LINK_NAMESPACE))
 p=s.commit(p,commit_token='seed',version_changes=versions(),identity_changes=placements,next_incarnation_id=3,changes=(),new_segments=(),metadata=meta).pin
 return s,p,ref,authorities(s,p)
