"""Full-verified root selection construction for tests/diagnostics only."""
import importlib

from ate_sim.persistence_proof_seek import OrderedSeekMap
from ate_sim.persistence_proof_occurrence import OwnerScope, RawOccurrence, occurrence_domain, member_commitment, group_order_key


def seek_module():return importlib.import_module('ate_sim.persistence_proof_occurrence_seek')


def construct_seek_certificates(store,pin,scopes):
    s=seek_module();store.db.execute('BEGIN IMMEDIATE')
    try:
        store._require_pin(pin);store.verify_all();allocator=store._identity_state_at(pin.captured_head)[0]
        result=[]
        for scope in scopes:
            base=occurrence_domain(store.store_identity,store.codec.version,scope)
            m=OrderedSeekMap(store.db,s.seek_domain(store.store_identity,store.codec.version,scope));m.create_schema()
            if type(scope) is OwnerScope:
                where,args,order='owner_namespace=? AND owner_key=?',(scope.namespace,scope.typed_key),'occurrence_path'
            else:where,args,order='incarnation_id=?',(scope.incarnation_id,),'owner_namespace,owner_key,occurrence_path'
            cursor=store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
                'FROM lazy_identity_occurrence_versions WHERE '+where+
                ' AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY '+order,
                args+(pin.captured_head,pin.captured_head))
            def rows():
                for ns,key,path,inc in cursor:
                    row=RawOccurrence(ns,key,path,inc)
                    yield path if type(scope) is OwnerScope else group_order_key(ns,key,path),member_commitment(base,row)
            try:root=m.build(rows())
            finally:cursor.close()
            m.verify(root)
            cert=s.SeekOccurrenceCertificate(store.store_identity,pin.captured_head,store.codec.version,scope,allocator,root)
            result.append((cert,s.certificate_commitment(cert)))
        store.db.commit();return tuple(result)
    except BaseException:store.db.rollback();raise
