"""Real ordinary rows; explicit full bootstrap is outside timed operations."""
import importlib
from ate_sim.persistence_adapters import WorldCodec
from ate_sim.persistence_lazy_store import LazyRecordStore
from ate_sim.incremental_store import RecordChange


def record_module():return importlib.import_module('ate_sim.persistence_proof_record')


def metadata(n=1):return dict(simulation_position=n,seed=7,next_ids={},namespaces=('people','archive'))


def make_record_store(path,archive=0,*,bootstrap=True):
    r=record_module();store=LazyRecordStore.create(path,codec=WorldCodec(),simulation_schema='8',rules_id='record-proof-test')
    pin=store.capture_pin()
    def changes():
        yield RecordChange('people',0,{'wealth':1})
        for i in range(archive):yield RecordChange('archive',i,b'history'+b'x'*121)
    pin=store.commit(pin,commit_token='seed',version_changes=(),changes=changes(),new_segments=(),metadata=metadata()).pin
    pair=r.bootstrap_record_proofs(store,pin) if bootstrap else None
    return store,pin,pair


def read_record(store,pin,pair,key=0,**kwargs):
    return record_module().read_record_proof_bytes(store,pin,*pair,'people',store.codec.encode(key),expected_record_schema=1,**kwargs)
