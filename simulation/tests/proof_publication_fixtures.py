"""Real content/ordinary/scope roots sharing one physical store."""
import importlib
from collections import namedtuple
from ate_sim.incremental_store import Membership,RecordChange,NewSegment,TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_proof_record import bootstrap_record_proofs
from ate_sim.persistence_proof_scope import bootstrap_scope_proofs

Authorities=namedtuple('Authorities','content record scope')
def publication_module():return importlib.import_module('ate_sim.persistence_proof_publication')
def metadata(n=1):return dict(simulation_position=n,seed=7,next_ids={},namespaces=('people','archive','ordinary','events'))


def make_publication_store(path,archive=0,*,bootstrap=True,empty_event=False):
    store=LazyRecordStore.create(path,codec=TypedCodec(),simulation_schema='8',rules_id='content-publication-test')
    def versions():
        yield VersionChange('people',0,{'wealth':1},memberships=(Membership('cohort','active',0),))
        for i in range(archive):yield VersionChange('archive',i,{'old':i},memberships=(Membership('cohort',i,0),))
    def placements():
        yield IdentityOccurrenceChange('people',0,(),1)
        for i in range(archive):yield IdentityOccurrenceChange('archive',i,(),i+3)
    def events():
        yield NewSegment('events',0,[] if empty_event else ['first'],element_count=0 if empty_event else 1,first_id=None if empty_event else 0,last_id=None if empty_event else 0)
        for i in range(archive):yield NewSegment('events',i+1,[i],element_count=1,first_id=i+1,last_id=i+1)
    pin=store.commit(store.capture_pin(),commit_token='seed',version_changes=versions(),identity_changes=placements(),
        changes=(RecordChange('ordinary',0,{'value':1}),),new_segments=events(),next_incarnation_id=archive+3,metadata=metadata()).pin
    if bootstrap:
        record=bootstrap_record_proofs(store,pin);scope=bootstrap_scope_proofs(store,pin)
        authorities=Authorities(publication_module().bootstrap_content_proofs(store,pin),record,scope)
    else:authorities=None
    return store,pin,authorities


def commit_publication(store,pin,authorities,*,token='next',**kwargs):
    arguments=dict(version_changes=(VersionChange('people',0,{'wealth':2},memberships=(Membership('cohort','new',7),)),),
        identity_changes=(IdentityOccurrenceChange('people',0,(),2),),changes=(RecordChange('ordinary',0,{'value':2}),),
        new_segments=(NewSegment('events',1000001,['second'],element_count=1,first_id=1000001,last_id=1000001),),metadata=metadata(pin.captured_head+1))
    arguments.update(kwargs)
    return publication_module().commit_content_proof(store,pin,*authorities.content,record_authority=authorities.record,
        scope_authority=authorities.scope,commit_token=token,**arguments)


def next_authorities(result):return Authorities((result.certificate,result.commitment),(result.scope.record.certificate,result.scope.record.commitment),(result.scope.certificate,result.scope.commitment))


def read_version(store,pin,authorities,**kwargs):return publication_module().read_version_content_bytes(store,pin,*authorities.content,'people',store.codec.encode(0),expected_record_schema=1,**kwargs)
def read_event(store,pin,authorities,ordinal=0,**kwargs):return publication_module().read_event_content_bytes(store,pin,*authorities.content,'events',ordinal,**kwargs)
