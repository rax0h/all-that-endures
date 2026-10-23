"""Synthetic physical owners; full row verification, not World graph authority."""
import importlib
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_lazy_nested_history import HistoryReference
from ate_sim.persistence_record_headers import RecordReference
from ate_sim.persistence_event_id_reference import EventIdReference
from ate_sim.persistence_nonreflexive_keys import NonreflexiveKeyReference
from ate_sim.core import Ref
from ate_sim.persistence_proof_occurrence import OwnerScope
from simulation.tests.proof_version_fixtures import construct_version_certificate
from simulation.tests.proof_occurrence_seek_fixtures import construct_seek_certificates

PAGE='aux.lazy.nested.list_pages'
PAGE_VALUE=(HistoryReference('list',2),(RecordReference(3),EventIdReference(4)),Ref(NonreflexiveKeyReference(5),7))
PAGE_PLACEMENTS=(((('index',0),),2),((('index',1),('index',0)),3),
                 ((('index',1),('index',1)),4),((('index',2),('field','kind')),5))


def projection_module():return importlib.import_module('ate_sim.persistence_proof_projection')


def metadata(generation=1):return dict(simulation_position=generation,seed=7,next_ids={},namespaces=(PAGE,))


def authorities(store,pin,namespace=PAGE,key=(1,0)):
    version=construct_version_certificate(store,pin)
    occurrence=construct_seek_certificates(store,pin,(OwnerScope(namespace,store.codec.encode(key)),))[0]
    return version,occurrence


def make_projection_store(path,archive=0,*,namespace=PAGE,key=(1,0),value=PAGE_VALUE,placements=PAGE_PLACEMENTS,memberships=(),present=True):
    store=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='projection-source-test');pin=store.capture_pin()
    def versions():
        if present:yield VersionChange(namespace,key,value,memberships=memberships)
        for i in range(archive):yield VersionChange(PAGE,(i+10,0),(i,))
    pin=store.commit(pin,commit_token='seed',version_changes=versions(),
        identity_changes=(IdentityOccurrenceChange(namespace,key,path,inc) for path,inc in placements),
        next_incarnation_id=max(archive+10,10),changes=(),new_segments=(),metadata=metadata()).pin
    return store,pin,authorities(store,pin,namespace,key)


def read_projection(store,pin,pairs,**kwargs):
    return projection_module().read_owner_projection(store,pin,*pairs[0],*pairs[1],**kwargs)
