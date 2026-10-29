"""Complete generated-world years through the explicit native proof bridge."""
import copy
import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ate_sim.engine import Simulation
from ate_sim.persistence_lazy import convert_cold_to_lazy
from ate_sim.persistence_proof_world_copy import copy_world_with_proofs
from ate_sim.persistence_proof_world_session import open_audited_proof_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.worldgen import generate_world


@pytest.mark.parametrize('proof', [False, True])
def test_native_new_relationships_keep_insertion_and_query_order(tmp_path, proof):
    from ate_sim.persistence_lazy import open_lazy_world_session
    from simulation.tests.test_stage_0_5_proof_world_session import fixture

    path, pair = fixture(tmp_path)
    if not proof:
        path = tmp_path / 'source' / 'complete.sqlite'

    def opened():
        if proof:
            return open_audited_proof_world_session(
                path, rules_id='private-catalog-copy', expected_commitment=pair[1])
        return open_lazy_world_session(path, rules_id='private-catalog-copy')

    keys = ((5, 9), (1, 9), (3, 9))
    with opened() as session:
        for a, b in keys:
            session.world.social.get(a, b)
            session.world.social.partner(a, b, 1)
        session.save()
        if proof:
            pair = session.proof_manifest
        assert tuple(session.world.social.edges) == keys
        assert session.world.social.edges.ids_for_person(9) == keys
        assert tuple(session.world.social.partnerships) == keys
        assert tuple(session.world.social.adjacency) == (5, 9, 1, 3)
    with opened() as session:
        assert tuple(session.world.social.edges) == keys
        assert session.world.social.edges.ids_for_person(9) == keys
        assert tuple(session.world.social.partnerships) == keys
        assert tuple(session.world.social.adjacency) == (5, 9, 1, 3)
        # Reinsertion and a discarded new key must not leave ordinal gaps.
        edge = session.world.social.edges.pop(keys[0])
        session.world.social.edges[keys[0]] = edge
        session.world.social.get(4, 9)
        del session.world.social.edges[4, 9]
        session.world.social.get(2, 9)
        del session.world.social.partnerships[keys[0]]
        session.world.social.partner(*keys[0], 2)
        session.save()
        if proof:
            pair = session.proof_manifest
    with opened() as session:
        expected = keys[1:] + (keys[0], (2, 9))
        assert tuple(session.world.social.edges) == expected
        assert session.world.social.edges.ids_for_person(9) == expected
        assert tuple(session.world.social.partnerships) == keys[1:] + (keys[0],)


def test_proof_record_hints_resolve_all_persisted_fields():
    from ate_sim.advancement import AbilityProgress
    from ate_sim.mastery_training import ResponseModel
    from ate_sim.persistence_proof_world import _record_hints
    from ate_sim.persistence_schema import RECORD_FIELDS

    for cls, fields in RECORD_FIELDS.items():
        assert set(fields) <= _record_hints(cls).keys()
    assert _record_hints(AbilityProgress)['response_model'] == ResponseModel | None


@pytest.mark.parametrize('kind', ['list', 'sequence', 'frozen-list', 'map', 'set'])
def test_bare_list_annotation_checks_reference_container_kind(kind):
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim.mastery_training import ResponseModel
    from ate_sim.persistence_lazy_nested_history import HistoryReference
    from ate_sim.persistence_proof_world import _check_field_values

    values = (HistoryReference(kind, 1), [], 0, 0)
    if kind in ('list', 'sequence', 'frozen-list'):
        _check_field_values(None, None, ResponseModel, values)
    else:
        with pytest.raises(StoreIntegrityError, match='ResponseModel.samples'):
            _check_field_values(None, None, ResponseModel, values)


@pytest.mark.parametrize('pair', [(11, 12), (11, 11)])
@pytest.mark.parametrize('damage', [None, 'missing', 'wrong-person', 'wrong-order'])
def test_partnership_query_projection_uses_key_and_rejects_corruption(pair, damage):
    from ate_sim.incremental_store import Membership, StoreIntegrityError
    from ate_sim.persistence_adapters import WorldCodec
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_proof_world import _check_queries

    memberships = tuple(Membership('person', person, 7) for person in dict.fromkeys(pair))
    if damage == 'missing':
        memberships = memberships[:-1]
    elif damage == 'wrong-person':
        memberships = (Membership('person', 99, 7),) + memberships[1:]
    elif damage == 'wrong-order':
        memberships = (Membership('person', pair[0], 8),) + memberships[1:]
    store = SimpleNamespace(codec=WorldCodec(identity_links_recorded=True),
                            _visible_order=lambda *args: (7,))
    change = VersionChange('world.social.partnerships', pair, 42,
                           memberships=memberships)
    if damage:
        with pytest.raises(StoreIntegrityError, match='query projection'):
            _check_queries(store, SimpleNamespace(captured_head=0), change)
    else:
        _check_queries(store, SimpleNamespace(captured_head=0), change)


def test_generated_world_continues_through_two_proof_saves(tmp_path):
    rules = 'stage-0-6-proof-real-years'
    world = generate_world(843000, width=8, height=6, settlements=1, mature=True)
    Simulation(world).run(2)
    control = copy.deepcopy(world)
    expected = {}
    for year in (3, 4):
        Simulation(control).run(1)
        expected[year] = control.digest()
    cold, source, target = (tmp_path / name for name in
                            ('cold.sqlite', 'lazy.sqlite', 'proof.sqlite'))
    write_cold_snapshot(world, cold, rules_id=rules)
    convert_cold_to_lazy(cold, source, rules_id=rules, native_graph_buckets=True)
    source_digest = hashlib.sha256(source.read_bytes()).digest()
    result = copy_world_with_proofs(source, target, rules_id=rules)
    assert hashlib.sha256(source.read_bytes()).digest() == source_digest
    commitment = result.commitment
    for year in (3, 4):
        with open_audited_proof_world_session(
                target, rules_id=rules, expected_commitment=commitment) as session:
            before = session.pin.captured_head
            assert not session.store.db.in_transaction
            Simulation(session.world).run(1)
            assert not session.store.db.in_transaction
            assert session.world.year == year
            assert session.save() == before + 1
            assert session.proof_manifest[0].parent_commitment == commitment
            commitment = session.proof_manifest[1]
        # A fresh interpreter must restore using only the externally held
        # commitment, not any canonical objects or verification caches here.
        restored = subprocess.run([
            sys.executable, '-c',
            'import json,sys; '
            'from ate_sim.persistence_proof_world_session import open_audited_proof_world_session; '
            's=open_audited_proof_world_session(sys.argv[1],rules_id=sys.argv[2],expected_commitment=bytes.fromhex(sys.argv[3])); '
            'print(json.dumps([s.world.year,s.world.digest()])); s.close()',
            str(target), rules, commitment.hex(),
        ], check=True, capture_output=True, text=True, timeout=60)
        assert json.loads(restored.stdout) == [year, expected[year]]
