"""Verified construction for tests/diagnostics only, never World authority."""
import importlib

from ate_sim.incremental_store import TypedCodec
from ate_sim.persistence_lazy_store import LazyRecordStore, VersionChange, IdentityOccurrenceChange
from ate_sim.persistence_proof_map import ProofMap
from ate_sim.persistence_proof_order_edit import build_ordered
from ate_sim.persistence_proof_store import ProofNodeStore


def occurrence_module():
    return importlib.import_module('ate_sim.persistence_proof_occurrence')


def metadata(position=1):
    return dict(simulation_position=position, seed=7, next_ids={}, namespaces=('people', 'archive'))


def make_occurrence_store(path, archive=0):
    store = LazyRecordStore.create(path, codec=TypedCodec(), simulation_schema='8', rules_id='occurrence-source-test')
    pin = store.capture_pin()
    def versions():
        for i in range(4): yield VersionChange('people', i, {'shared': 'raw fixture', 'other': i})
        for i in range(archive): yield VersionChange('archive', i, {'old': i})
    def placements():
        for i in range(4):
            for field in ('other', 'shared'):
                yield IdentityOccurrenceChange('people', i, (('field', field),), 1)
        for i in range(archive): yield IdentityOccurrenceChange('archive', i, (), i+3)
    pin = store.commit(pin, commit_token='seed', version_changes=versions(), identity_changes=placements(),
        next_incarnation_id=archive+3, changes=(), new_segments=(), metadata=metadata()).pin
    return store, pin


def construct_occurrence_certificates(store, pin, scopes):
    o = occurrence_module()
    nodes = ProofNodeStore(store.db)
    store.db.execute('BEGIN IMMEDIATE')
    try:
        o.create_occurrence_indexes(store.db)
        nodes.create_schema()
        store.verify_all()
        allocator = store._identity_state_at(pin.captured_head)[0]
        result = []
        for scope in scopes:
            domain = o.occurrence_domain(store.store_identity, store.codec.version, scope)
            m = ProofMap(domain, lambda d: nodes.read(domain, d), lambda d, raw: nodes.write(domain, d, raw))
            if type(scope) is o.OwnerScope:
                where, args, order = 'owner_namespace=? AND owner_key=?', (scope.namespace, scope.typed_key), 'occurrence_path'
            else:
                where, args, order = 'incarnation_id=?', (scope.incarnation_id,), 'owner_namespace,owner_key,occurrence_path'
            cursor = store.db.execute('SELECT owner_namespace,owner_key,occurrence_path,incarnation_id '
                'FROM lazy_identity_occurrence_versions WHERE '+where+
                ' AND valid_from<=? AND (valid_to IS NULL OR ?<valid_to) ORDER BY '+order,
                args+(pin.captured_head, pin.captured_head))
            def rows():
                for ns, key, path, inc in cursor:
                    row = o.RawOccurrence(ns, key, path, inc)
                    position = path if type(scope) is o.OwnerScope else o.group_order_key(ns, key, path)
                    yield position, o.member_commitment(domain, row)
            try: root = build_ordered(m, store.db, rows())
            finally: cursor.close()
            cert = o.OccurrenceCertificate(store.store_identity, pin.captured_head, store.codec.version, scope, allocator, root)
            result.append((cert, o.certificate_commitment(cert)))
        store.db.commit()
        return tuple(result)
    except BaseException:
        store.db.rollback()
        raise
