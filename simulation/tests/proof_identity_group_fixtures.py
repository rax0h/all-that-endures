"""Real catalog publication plus test-only full-verified proof construction."""
import importlib
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange
from ate_sim.persistence_record_headers import RecordReference
from ate_sim.persistence_proof_occurrence import GroupScope,OwnerScope
from ate_sim.persistence_proof_query import QueryScope
from ate_sim import persistence_lazy_identity_catalog as catalog
from simulation.tests.proof_version_fixtures import construct_version_certificate
from simulation.tests.proof_occurrence_seek_fixtures import construct_seek_certificates
from simulation.tests.proof_query_seek_fixtures import construct_query_seek

NS='world.people'
PAGE='aux.lazy.nested.list_pages'


def group_module():return importlib.import_module('ate_sim.persistence_proof_identity_group')


def metadata(generation=1):
    return dict(simulation_position=generation,seed=7,next_ids={},namespaces=(NS,PAGE,'archive',catalog.LINK_NAMESPACE))


def group_authorities(store,pin,inc=1):
    version=construct_version_certificate(store,pin)
    owners=store.db.execute('SELECT DISTINCT owner_namespace,owner_key FROM lazy_identity_occurrence_versions '
        'WHERE incarnation_id=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY owner_namespace,owner_key',
        (inc,pin.captured_head,pin.captured_head)).fetchall()
    scopes=(GroupScope(inc),)+tuple(OwnerScope(ns,key) for ns,key in owners)
    occurrences=construct_seek_certificates(store,pin,scopes)
    query=construct_query_seek(store,pin,QueryScope(catalog.LINK_NAMESPACE,'incarnation',store.codec.encode(inc)))
    return version,occurrences[0],query,tuple(occurrences[1:])


def make_group_store(path,archive=0,*,catalog_mutator=None,wide_owner=0,aux_peer=False,inc=1):
    store=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='group-source-test');pin=store.capture_pin()
    versions=[VersionChange(NS,1,{'value':'shared'}),VersionChange(NS,2,{'value':'shared'}),VersionChange(NS,3,{'value':'other'})]
    placements=[IdentityOccurrenceChange(NS,1,(),1),IdentityOccurrenceChange(NS,2,(),1),IdentityOccurrenceChange(NS,3,(),2)]
    placements.extend(IdentityOccurrenceChange(NS,1,(('key',i),),2) for i in range(wide_owner))
    allocator=4
    if aux_peer:
        versions.append(VersionChange(PAGE,(4,0),(RecordReference(1),)));placements.append(IdentityOccurrenceChange(PAGE,(4,0),(('index',0),),1));allocator=5
    delta=catalog.initial_catalog_delta(store.codec,versions,placements,next_incarnation_id=allocator,generation=1)
    witnesses=delta.decode(store.codec)[0]
    if catalog_mutator is not None:witnesses=tuple(catalog_mutator(witnesses,store.codec))
    def changes():
        yield from versions;yield from witnesses
        for i in range(archive):yield VersionChange('archive',i,b'unrelated historical body'+b'x'*100)
    pin=store.commit(pin,commit_token='seed',version_changes=changes(),identity_changes=placements,next_incarnation_id=allocator,
        changes=(),new_segments=(),metadata=metadata()).pin
    if catalog_mutator is None:catalog.IdentityCatalog(store).validate_publication(delta,pin)
    return store,pin,group_authorities(store,pin,inc)


def reanchor(store,pin):
    versions=(VersionChange(NS,1,{'value':'replacement'}),);placements=(IdentityOccurrenceChange(NS,1,(),4),)
    delta=catalog.IdentityCatalog(store).prepare_delta(pin,versions,placements,next_incarnation_id=5)
    successor=store.commit(pin,commit_token='reanchor',version_changes=versions+delta.decode(store.codec)[0],
        identity_changes=placements,next_incarnation_id=5,changes=(),new_segments=(),metadata=metadata(2)).pin
    catalog.IdentityCatalog(store).validate_publication(delta,successor);return successor


def retire_empty(store,pin):
    delta=catalog.IdentityCatalog(store).prepare_retirement_delta(pin,row_budget=256)
    successor=store.commit(pin,commit_token='retire',version_changes=delta.decode(store.codec)[0],identity_changes=(),
        next_incarnation_id=4,changes=(),new_segments=(),metadata=metadata(2)).pin
    catalog.IdentityCatalog(store).validate_publication(delta,successor);return successor


def read_group(store,pin,pairs,**kwargs):
    return group_module().read_identity_group_proof(store,pin,*pairs[0],*pairs[1],*pairs[2],pairs[3],**kwargs)
