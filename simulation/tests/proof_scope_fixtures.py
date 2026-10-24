"""Real scoped relations; production construction is explicitly budgeted."""
import importlib
from ate_sim.incremental_store import Membership,RecordChange,TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore,VersionChange,IdentityOccurrenceChange


def scope_module():return importlib.import_module('ate_sim.persistence_proof_scope')
def metadata(n=1):return dict(simulation_position=n,seed=7,next_ids={},namespaces=('people','archive','ordinary'))


def make_scope_store(path,archive=0,*,bootstrap=True):
    store=LazyRecordStore.create(path,codec=TypedCodec(),simulation_schema='8',rules_id='scope-proof-test')
    def versions():
        yield VersionChange('people',0,{'wealth':1},memberships=(Membership('cohort','active',0),))
        for i in range(archive):yield VersionChange('archive',i,{'old':i},memberships=(Membership('cohort',i,0),))
    def placements():
        yield IdentityOccurrenceChange('people',0,(),1)
        for i in range(archive):yield IdentityOccurrenceChange('archive',i,(),i+3)
    pin=store.commit(store.capture_pin(),commit_token='seed',version_changes=versions(),identity_changes=placements(),
        changes=(RecordChange('ordinary',1,{'ordinary':1}),),next_incarnation_id=archive+3,new_segments=(),metadata=metadata()).pin
    pair=scope_module().bootstrap_scope_proofs(store,pin) if bootstrap else None
    return store,pin,pair


def scopes(store):
    from ate_sim.persistence_proof_occurrence import OwnerScope,GroupScope
    from ate_sim.persistence_proof_query import QueryScope
    return OwnerScope('people',store.codec.encode(0)),GroupScope(1),QueryScope('people','cohort',store.codec.encode('active'))


def read_scope(store,pin,pair,scope,**kwargs):return scope_module().read_scope_certificate(store,pin,*pair,scope,**kwargs)


def commit_scope(store,pin,pair,*,token='next',**kwargs):
    arguments=dict(version_changes=(VersionChange('people',0,{'wealth':2},memberships=(Membership('cohort','new',7),)),),
        identity_changes=(IdentityOccurrenceChange('people',0,(),2),),changes=(),new_segments=(),metadata=metadata(pin.captured_head+1))
    arguments.update(kwargs)
    return scope_module().commit_scope_proof(store,pin,*pair,commit_token=token,**arguments)
