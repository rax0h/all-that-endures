"""Actual native counted-sequence appends compose with World proof publication."""
import pytest
import shutil
import subprocess
import sys
import json

from ate_sim.core import Household
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def sequence_fixture(tmp_path, count=3, *, history=32):
    def configure(world):
        members = list(range(1, count+1))
        world.households[1] = Household(1, 1, members=members)
        world.households[2] = Household(2, 1, members=members)
    return fixture(tmp_path, size=history, configure=configure)


@pytest.fixture(scope='module')
def sequences(tmp_path_factory):
    cached = {}
    def create(tmp_path, count=3, history=32):
        marker = count, history
        if marker not in cached:
            cached[marker] = sequence_fixture(tmp_path_factory.mktemp('sequence-source'), count, history=history)
        source, pair = cached[marker]
        path = tmp_path/'world.sqlite'
        shutil.copyfile(source, path)
        return path, pair
    return create


@pytest.mark.parametrize('count', [3, 128, 4096])
def test_existing_native_sequence_append_avoids_world_audit(tmp_path, monkeypatch, sequences, count):
    from ate_sim import persistence_proof_world as world
    path, pair = sequences(tmp_path, count)
    with opened(path, pair) as session:
        members = session.world.households[1].members
        assert members._kind == 'sequence'
        assert members is session.world.households[2].members
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('sequence append scanned World'))
            members.append(7)
            members.extend([7, 9999])
            assert session.save() == 1
            pair = session.proof_manifest
        expected = session.world.digest()
    with opened(path, pair) as restored:
        members = restored.world.households[1].members
        assert list(members) == list(range(1, count+1))+[7, 7, 9999]
        assert members.occurrences(7) == ((6,) if count >= 7 else ())+(count, count+1)
        assert restored.world.households[1].members is restored.world.households[2].members
        assert restored.world.digest() == expected
    if count == 4096:
        fresh = subprocess.run([sys.executable, '-c',
            "import json,sys;from ate_sim.persistence_proof_world_session import open_audited_proof_world_session;"
            "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2]));"
            "print(json.dumps([s.world.digest(),len(s.world.households[1].members),s.world.households[1].members is s.world.households[2].members]));s.close()",
            str(path), pair[1].hex()], capture_output=True, text=True, check=True, timeout=90)
        assert json.loads(fresh.stdout) == [expected, 4099, True]


def test_sequence_append_composes_with_fresh_owner_and_integer_tail(tmp_path, monkeypatch, sequences):
    from ate_sim.core import Person
    from ate_sim import persistence_proof_world as world
    path, pair = sequences(tmp_path, 128)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('mixed sequence save scanned World'))
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.next_person = 100
            session.world.households[1].members.append(99)
            session.skills[1, 'craft'].provenance.append(42)
            session.skills[1, 'craft'].level = .75
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.people[99].id == 99
        assert list(restored.world.households[2].members) == list(range(1, 129))+[99]
        assert list(restored.skills[2, 'craft'].provenance) == list(range(32))+[42]
        assert restored.skills[1, 'craft'].level == .75


@pytest.mark.parametrize('damage', ['missing-locator', 'wrong-locator', 'wrong-types', 'missing-owner', 'bad-owner', 'bad-descriptor', 'malformed-leaf', 'malformed-occurrence'])
def test_sequence_append_rejects_inconsistent_frozen_rows(tmp_path, monkeypatch, sequences, damage):
    from dataclasses import replace
    from ate_sim.incremental_store import StoreError
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_sequence as sequence
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_history_types import NAMESPACE as TYPES
    path, pair = sequences(tmp_path, 128)
    with opened(path, pair) as session:
        members = session.world.households[1].members
        incarnation = members._incarnation
        members.append(7)
        original = manifests.commit_world_manifest
        def corrupt(*args, **kwargs):
            changed, altered = [], False
            for c in kwargs['version_changes']:
                if not altered:
                    if c.namespace == sequence.LOCATOR_NAMESPACE and c.key[0] == incarnation:
                        if damage == 'missing-locator':
                            altered = True;continue
                        if damage == 'wrong-locator':
                            c = replace(c, value=(999999, 0));altered = True
                    if c.namespace == TYPES and c.key == incarnation and damage == 'wrong-types':
                        c = replace(c, value=(c.value[0], c.value[1], (0, 0, 129)));altered = True
                    if c.namespace == catalog.OWNER_NAMESPACE and c.key[0] == sequence.NODE_NAMESPACE and c.key[1][0] == incarnation:
                        if damage == 'missing-owner':
                            altered = True;continue
                        if damage == 'bad-owner':
                            c = replace(c, value=c.value[:5]+('0'*64,)+c.value[6:]);altered = True
                    if c.namespace == sequence.DESCRIPTOR_NAMESPACE and c.key == incarnation and damage == 'bad-descriptor':
                        c = replace(c, value=c.value[:3]+(9999,)+c.value[4:]);altered = True
                    if c.namespace == sequence.NODE_NAMESPACE and c.key[0] == incarnation:
                        if damage == 'malformed-leaf':
                            c = replace(c, value=('leaf', (None,)));altered = True
                        if damage == 'malformed-occurrence':
                            c = replace(c, value=('leaf', (('bad', 7),)));altered = True
                changed.append(c)
            assert altered
            kwargs['version_changes'] = tuple(changed)
            return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError):
                session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.world.households[1].members) == list(range(1,129))+[7]


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_sequence_append_recovers_original_frozen_attempt(tmp_path, sequences, phase):
    path, pair = sequences(tmp_path, 128)
    with opened(path, pair) as session:
        session.world.households[1].members.append(7)
        def fault(at):
            if at == phase:raise RuntimeError('interrupted sequence publication')
        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted sequence'):
            session.save()
        session.store._phase_hook = lambda _: None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.world.households[1].members) == list(range(1,129))+[7]


@pytest.mark.parametrize('operation', ['replace', 'replace-and-append', 'empty', 'budget'])
def test_unsupported_sequence_edits_keep_checked_fallback(tmp_path, monkeypatch, sequences, operation):
    from ate_sim import persistence_proof_world as world, persistence_proof_world_sequence as proof
    path, pair = sequences(tmp_path, 0 if operation == 'empty' else 3)
    with opened(path, pair) as session:
        members = session.world.households[1].members
        if operation in ('replace', 'replace-and-append'):
            members[0] = 7
            if operation == 'replace-and-append':members.append(7)
        else:members.append(7)
        original, calls = world._audit_world, []
        def audit(*args, **kwargs):
            calls.append(True);return original(*args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            if operation == 'budget':patch.setattr(proof, 'MAX_READS', 1)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert list(restored.world.households[1].members) == ([7,2,3] if operation == 'replace' else [7,2,3,7] if operation == 'replace-and-append' else [7] if operation == 'empty' else [1,2,3,7])


def test_append_reads_only_its_tree_frontier_beside_unrelated_history(tmp_path, monkeypatch, sequences):
    from ate_sim import persistence_proof_world as world, persistence_proof_publication as content
    from ate_sim.persistence_lazy_sequence import NODE_NAMESPACE
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    path, pair = sequences(tmp_path, 128, history=10000)
    with opened(path, pair) as session:
        generation = session.pin.captured_head
        original, nodes = content._source_version, set()
        def read(store, at, namespace, key, **kwargs):
            row = original(store, at, namespace, key, **kwargs)
            if at == generation and row is not None:
                assert namespace not in (PAGE_NAMESPACE, ENTRY_NAMESPACE), 'unrelated history body read'
                if namespace == NODE_NAMESPACE:nodes.add(key)
            return row
        with monkeypatch.context() as patch:
            patch.setattr(content, '_source_version', read)
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('append scanned World'))
            session.world.households[1].members.append(9999)
            assert session.save() == 1
            pair = session.proof_manifest
        assert 0 < len(nodes) < 8
    with opened(path, pair) as restored:
        assert list(restored.world.households[1].members) == list(range(1,129))+[9999]
        assert len(restored.skills[1, 'craft'].provenance) == 10000


def test_overlapping_predecessors_are_rejected_before_body_fetch(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from ate_sim.incremental_store import StoreIntegrityError
    from ate_sim import persistence_proof_world_sequence as proof
    from ate_sim import persistence_proof_publication as content
    from ate_sim.persistence_lazy_sequence import DESCRIPTOR_NAMESPACE
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api
    store, pin, pair = _proof_store(tmp_path,
        configure=lambda w: w.households.update({1: Household(1, 1, members=[1,2,3])}))
    try:
        result = manifest_api().commit_world_manifest(store, pin, *pair, commit_token='a'*32,
            version_changes=(), changes=(), new_segments=(), metadata=store.head_metadata(), checkpoint=True)
        pin = result.commit.pin
        incarnation = next(iter(store.iter_keys(pin, DESCRIPTOR_NAMESPACE)))
        typed = store.codec.encode(incarnation)
        store.db.execute('INSERT INTO lazy_record_versions SELECT namespace,typed_key,1,NULL,payload,payload_checksum,codec_version,record_schema,memberships,row_checksum FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
                         (DESCRIPTOR_NAMESPACE, typed))
        store.db.commit()
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        def forbidden(*args, **kwargs):raise RuntimeError('body fetch preceded overlap rejection')
        monkeypatch.setattr(content, '_source_version', forbidden)
        with store.read_snapshot(pin), pytest.raises(StoreIntegrityError, match='overlap'):
            proof._Sources(store, request, 0).source(DESCRIPTOR_NAMESPACE, typed)
    finally:
        store.close()
