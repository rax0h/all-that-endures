"""Full verified test import into a content map; never a production constructor."""
import importlib

from ate_sim.persistence_proof_batch import update_sorted
from ate_sim.persistence_proof_content import version_key, version_commitment
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_nodes import key_locator
from ate_sim.persistence_proof_store import ProofNodeStore


def version_module():
    return importlib.import_module('ate_sim.persistence_proof_version')


def construct_version_certificate(store, pin):
    v = version_module()
    domain = v.version_domain(store.store_identity, store.codec.version)
    nodes = ProofNodeStore(store.db)
    nodes.create_schema()
    proof_map = ProofMap(domain, lambda d: nodes.read(domain, d),
                         lambda d, raw: nodes.write(domain, d, raw))
    store.db.execute('BEGIN IMMEDIATE')
    try:
        store._require_pin(pin)
        store.verify_all()
        store.db.execute('CREATE TEMP TABLE version_fixture_delta('
                         'locator BLOB PRIMARY KEY,key BLOB,value BLOB) WITHOUT ROWID')
        cursor = store.db.execute('SELECT namespace,typed_key,valid_from,codec_version,'
            'record_schema,memberships,payload FROM lazy_record_versions '
            'WHERE valid_from<=? AND (valid_to IS NULL OR ?<valid_to)',
            (pin.captured_head, pin.captured_head))
        try:
            for ns, key, start, codec, schema, memberships, payload in cursor:
                encoded = version_key(ns, key)
                value = version_commitment(ns, key, valid_from=start, codec_version=codec,
                    record_schema=schema, memberships=memberships, payload=payload)
                store.db.execute('INSERT INTO version_fixture_delta VALUES(?,?,?)',
                                 (key_locator(domain, encoded), encoded, value))
        finally:
            cursor.close()
        delta = store.db.execute('SELECT key,value FROM version_fixture_delta ORDER BY locator')
        try:
            root = update_sorted(proof_map, proof_map.empty, delta)
        finally:
            delta.close()
        store.db.execute('DROP TABLE version_fixture_delta')
        store.db.commit()
        certificate = v.VersionCertificate(store.store_identity, pin.captured_head,
                                           store.codec.version, root)
        return certificate, v.certificate_commitment(certificate)
    except BaseException:
        store.db.rollback()
        raise
