"""Publication acknowledgement may reuse only the exact validated successor."""
from unittest.mock import patch
import importlib
import sqlite3

import pytest

from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_packed_action_reconciliation_cost import fixture, RULES
from simulation.tests.test_persistence_lazy_store import make_store, metadata
from simulation.tests.test_stage_0_5_final_identity_catalog import groups, NS
from simulation.tests.test_stage_0_5_final_identity_coordinator import coordinator
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.ate_sim.incremental_store import StoreConflictError, StoreIntegrityError


def prepared(store, *, placement=False):
    pin = groups(store)
    coord, registry, owners, load = coordinator(store, pin, [], set())
    registry.allocator.next_value = 3
    obj = load((NS, 1))
    identity = importlib.import_module('simulation.ate_sim.persistence_lazy_identity')
    registry.bind(obj, identity.Occurrence(NS, 1, ()), incarnation=identity.IncarnationId(store.store_identity, 1))
    coord.routes_for_mutation(obj)
    obj.value = 10
    if placement:
        from simulation.ate_sim.persistence_lazy_store import IdentityOccurrenceChange
        coord.placement_overlay[coord._marker((NS, 1), ())] = IdentityOccurrenceChange(NS, 1, (), 1)
    payloads = tuple(VersionChange(*owner, {'value': 10}) for owner in ((NS, 1), (NS, 2)))
    delta = coord.prepare_delta(payloads)
    versions, records, identities = delta.decode(store.codec)
    successor = store.commit(pin, commit_token='proof', version_changes=payloads+versions,
        changes=records, new_segments=(), identity_changes=identities,
        next_incarnation_id=registry.next_incarnation,
        metadata=metadata(2, (NS, 'world_identity_links'))).pin
    return coord, delta, successor


@pytest.mark.parametrize('proof_used', [False, True])
@pytest.mark.parametrize('replacement', [
    {'owner_namespace': 'world.skills'}, {'owner_key': 2},
    {'occurrence_path': (('key', 'changed'),)}, {'incarnation_id': 2}, {'delete': True},
])
def test_same_key_overlay_edits_cannot_acknowledge_frozen_plan(tmp_path, proof_used, replacement):
    from dataclasses import replace
    with make_store(tmp_path/'overlay.sqlite') as store:
        coord, delta, pin = prepared(store, placement=True)
        proof = coord.validate_publication(delta, pin) if proof_used else None
        marker = next(iter(coord.placement_overlay))
        coord.placement_overlay[marker] = replace(coord.placement_overlay[marker], **replacement)
        with pytest.raises(StoreConflictError, match='overlay changed'):
            coord.accept_delta(delta, pin, proof=proof)
        assert coord._prepared is not None and coord.dirty_owners


def test_normal_save_does_not_validate_coordinator_twice(tmp_path):
    path = fixture(tmp_path, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        session.world.agency.actions[0].strength = .875
        coord = session._identity_coordinator
        with patch.object(coord, 'validate_publication', wraps=coord.validate_publication) as calls:
            session.save()
            assert calls.call_count == 1
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.world.agency.actions[0].strength == .875


def test_direct_accept_still_validates(tmp_path):
    with make_store(tmp_path/'direct.sqlite') as store:
        coord, delta, pin = prepared(store)
        with patch.object(coord, 'validate_publication', wraps=coord.validate_publication) as calls:
            coord.accept_delta(delta, pin)
            assert calls.call_count == 1
        with patch.object(coord, 'validate_publication', wraps=coord.validate_publication) as calls:
            coord.accept_delta(delta, pin)
            assert calls.call_count == 0
        store.release_pin(pin)
        with pytest.raises(StoreConflictError): coord.accept_delta(delta, pin)


def test_unchanged_proof_reuses_validation(tmp_path):
    with make_store(tmp_path/'reuse.sqlite') as store:
        coord, delta, pin = prepared(store)
        proof = coord.validate_publication(delta, pin)
        assert proof is not None
        with patch.object(coord, 'validate_publication', wraps=coord.validate_publication) as calls:
            coord.accept_delta(delta, pin, proof=proof)
            assert calls.call_count == 0
        assert coord.pin == pin and coord.diagnostics()['dirty_owners'] == 0


@pytest.mark.parametrize('change', ['row', 'rollback', 'external', 'schema', 'codec', 'overlay'])
def test_changed_authority_invalidates_proof(tmp_path, change):
    path = tmp_path/'epoch.sqlite'
    with make_store(path) as store:
        coord, delta, pin = prepared(store)
        proof = coord.validate_publication(delta, pin)
        assert proof is not None
        owner_namespace = importlib.import_module('simulation.ate_sim.persistence_lazy_identity_catalog').OWNER_NAMESPACE
        if change == 'row':
            store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?', (b'bad', owner_namespace))
            store.db.commit()
        elif change == 'rollback':
            store.db.execute('SAVEPOINT change')
            store.db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?', (b'bad', NS))
            store.db.execute('ROLLBACK TO change'); store.db.execute('RELEASE change')
        elif change == 'external':
                with sqlite3.connect(path) as db:
                    db.execute('UPDATE lazy_record_versions SET payload=? WHERE namespace=?', (b'bad', owner_namespace))
        elif change == 'schema': store.db.execute('CREATE TABLE proof_invalid(x)'); store.db.commit()
        elif change == 'codec': store.codec = type(store.codec)()
        else: coord.placement_revision += 1
        assert not proof.matches(coord, delta, pin)
        if change in ('row', 'external'):
            with pytest.raises(StoreIntegrityError): coord.accept_delta(delta, pin, proof=proof)
            assert coord._prepared is not None and coord.dirty_owners
        elif change in ('rollback', 'schema', 'overlay'):
            with patch.object(coord, 'validate_publication', wraps=coord.validate_publication) as calls:
                coord.accept_delta(delta, pin, proof=proof)
                assert calls.call_count == 1


def test_borrowed_transaction_cannot_mint_reusable_proof(tmp_path):
    with make_store(tmp_path/'borrowed.sqlite') as store:
        coord, delta, pin = prepared(store)
        with store.read_snapshot(pin):
            proof = coord.validate_publication(delta, pin)
        assert not proof.matches(coord, delta, pin)


def test_different_successor_or_connection_cannot_reuse_proof(tmp_path):
    from dataclasses import replace
    with make_store(tmp_path/'connection.sqlite') as store:
        coord, delta, pin = prepared(store)
        proof = coord.validate_publication(delta, pin)
        assert not proof.matches(coord, delta, replace(pin, captured_head=pin.captured_head+1))
        db = store.db
        store.db = sqlite3.connect(':memory:')
        try: assert not proof.matches(coord, delta, pin)
        finally: store.db.close(); store.db = db
