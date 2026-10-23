"""Full-verified ordered query roots for tests/diagnostics only."""
import importlib
from ate_sim.persistence_proof_seek import OrderedSeekMap
from ate_sim.persistence_proof_query import QueryScope,query_domain,member_commitment
from ate_sim.persistence_proof_order import query_order_key


def query_seek_module():return importlib.import_module('ate_sim.persistence_proof_query_seek')


def construct_query_seek(store,pin,scope):
    q=query_seek_module();store.db.execute('BEGIN IMMEDIATE')
    try:
        store._require_pin(pin);store.verify_all()
        m=OrderedSeekMap(store.db,q.seek_domain(store.store_identity,store.codec.version,scope));m.create_schema()
        domain=query_domain(store.store_identity,store.codec.version,scope)
        cursor=store.db.execute('SELECT record_key,ordinal FROM lazy_query_versions WHERE namespace=? AND index_name=? '
            'AND index_value=? AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY ordinal,record_key',
            (scope.namespace,scope.index_name,scope.index_value,pin.captured_head,pin.captured_head))
        try:root=m.build((query_order_key(ordinal,key),member_commitment(domain,key,ordinal)) for key,ordinal in cursor)
        finally:cursor.close()
        m.verify(root);cert=q.SeekQueryCertificate(store.store_identity,pin.captured_head,store.codec.version,scope,root)
        store.db.commit();return cert,q.certificate_commitment(cert)
    except BaseException:store.db.rollback();raise
