"""Explicit verified test construction, never an ordinary World reader path."""
import importlib

from ate_sim.incremental_store import Membership, RecordChange, TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_order import query_order_key
from ate_sim.persistence_proof_order_edit import build_ordered
from ate_sim.persistence_proof_store import ProofNodeStore


def query_module():
    return importlib.import_module('ate_sim.persistence_proof_query')


def metadata(position=1):
    return dict(simulation_position=position,seed=7,next_ids={},namespaces=('people','archive'))


def make_store(path,archive_count=0):
    store=LazyRecordStore.create(path,codec=TypedCodec(),simulation_schema='8',rules_id='proof-source-test')
    pin=store.capture_pin()
    changes=[VersionChange('people',i,{'wealth':i},memberships=(Membership('cohort','active',2*i),
             Membership('cohort','active',2*i+1))) for i in range(8)]
    result=store.commit(pin,commit_token='seed',version_changes=changes,
        changes=(RecordChange('archive',i,b'historical'+b'x'*118) for i in range(archive_count)),
        new_segments=(),metadata=metadata())
    return store,result.pin


def construct_certificate(store,pin,value='active'):
    q=query_module();scope=q.QueryScope('people','cohort',store.codec.encode(value))
    nodes=ProofNodeStore(store.db);nodes.create_schema()
    domain=q.query_domain(store.store_identity,store.codec.version,scope)
    m=ProofMap(domain,lambda d:nodes.read(domain,d),lambda d,raw:nodes.write(domain,d,raw))
    store.db.execute('BEGIN IMMEDIATE')
    try:
        store.verify_all()  # full accepted test import, outside query timers
        cursor=store.db.execute('SELECT record_key,ordinal FROM lazy_query_versions '
            'WHERE namespace=? AND index_name=? AND index_value=? AND valid_from<=? '
            'AND (valid_to IS NULL OR ?<valid_to) ORDER BY ordinal,record_key',
            (scope.namespace,scope.index_name,scope.index_value,pin.captured_head,pin.captured_head))
        try:
            order=build_ordered(m,store.db,((query_order_key(ordinal,key),q.member_commitment(domain,key,ordinal))
                                          for key,ordinal in cursor))
        finally:cursor.close()
        certificate=q.QueryCertificate(store.store_identity,pin.captured_head,store.codec.version,scope,order)
        store.db.commit()
        return certificate,q.certificate_commitment(certificate)
    except BaseException:
        store.db.rollback();raise
