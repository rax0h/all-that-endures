"""Compose accepted existing-value/tail proofs with fresh native owner proofs."""
import pytest

from ate_sim.core import Person
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


def test_new_owner_existing_values_and_ordinary_owner_compose(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        session.world.people[98] = Person(98, 0, 1, 1)
        session.world.next_person = 99
        session.save()
        pair = session.proof_manifest
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('mixed save scanned World'))
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.people[98].alive = False
            session.skills[1, 'craft'].level = .75
            session.world.settlements[1].food_stock = 123.5
            session.world.social.partner(98, 99, 2)
            session.world.year = 2
            session.world.next_person = 100
            assert session.save() == 2
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.people[99].id == 99
        assert not restored.world.people[98].alive
        assert [p.id for p in restored.world.current_people()] == [99]
        assert restored.skills[1, 'craft'].level == .75
        assert restored.skills[1, 'craft'].provenance is restored.skills[2, 'craft'].provenance
        assert restored.world.settlements[1].food_stock == 123.5
        assert tuple(restored.world.social.partnerships) == ((98, 99),)
        assert restored.world.year == 2
    import json
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-c',
        "import json,sys; from ate_sim.persistence_proof_world_session import open_audited_proof_world_session; "
        "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2])); "
        "print(json.dumps([s.world.year,[p.id for p in s.world.current_people()],s.skills[1,'craft'].level,s.world.settlements[1].food_stock,"
        "s.skills[1,'craft'].provenance is s.skills[2,'craft'].provenance])); s.close()",
        str(path), pair[1].hex()], capture_output=True, text=True, check=True, timeout=60)
    assert json.loads(result.stdout) == [2, [99], .75, 123.5, True]


@pytest.mark.parametrize('size,operation', [(127, 'append'), (128, 'append'), (129, 'pop')])
def test_new_owner_and_supported_history_tail_compose(tmp_path, monkeypatch, size, operation):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path, size=size)
    expected = size + (1 if operation == 'append' else -1)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('mixed tail save scanned World'))
            session.world.people[99] = Person(99, 0, 1, 1)
            history = session.skills[1, 'craft'].provenance
            if operation == 'append':
                history.append(42)
            else:
                history.pop()
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.people[99].id == 99
        assert len(restored.skills[1, 'craft'].provenance) == expected
        assert restored.skills[1, 'craft'].provenance is restored.skills[2, 'craft'].provenance


def test_new_owner_and_shared_backed_record_compose(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    from ate_sim.core import Settlement
    from ate_sim.skills import SkillHistory

    def configure(w):
        record = SkillHistory(9, 'nested', level=.25)
        w.settlements[1] = Settlement(1, 0, 0, memory={'a': record, 'b': record})

    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('mixed record save scanned World'))
            session.world.people[99] = Person(99, 0, 1, 1)
            session.world.settlements[1].memory['a'].level = .75
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        memory = restored.world.settlements[1].memory
        assert memory['a'] is memory['b']
        assert memory['a'].level == .75
        assert restored.world.people[99].id == 99


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_mixed_page_growth_recovers_frozen_attempt_once(tmp_path, phase):
    path, pair = fixture(tmp_path, size=128)
    with opened(path, pair) as session:
        session.world.people[99] = Person(99, 0, 1, 1)
        session.skills[1, 'craft'].level = .75
        session.skills[1, 'craft'].provenance.append(42)

        def fault(at):
            if at == phase:
                raise RuntimeError('interrupted mixed save')

        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted mixed save'):
            session.save()
        session.store._phase_hook = lambda _: None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.people[99].id == 99
        assert restored.skills[1, 'craft'].level == .75
        assert list(restored.skills[1, 'craft'].provenance) == list(range(128)) + [42]


@pytest.mark.parametrize('damage', ['existing-header', 'new-header', 'missing-page', 'wrong-types', 'extra-identity'])
def test_mixed_save_rejects_incomplete_or_inconsistent_authority(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.incremental_store import StoreError
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    from ate_sim.persistence_history_types import NAMESPACE as TYPES
    from ate_sim.persistence_lazy_store import IdentityOccurrenceChange
    path, pair = fixture(tmp_path, size=128)
    with opened(path, pair) as session:
        original = manifests.commit_world_manifest

        def corrupt(*args, **kw):
            result = []
            for c in kw['version_changes']:
                if damage == 'existing-header' and c.namespace == catalog.OWNER_NAMESPACE and c.key == ('world.skills.skills', (1, 'craft')):
                    continue
                if damage == 'new-header' and c.namespace == catalog.OWNER_NAMESPACE and c.key == ('world.people', 99):
                    c = replace(c, value=c.value[:5] + ('0'*64,) + c.value[6:])
                if damage == 'missing-page' and c.namespace == PAGE_NAMESPACE and c.key[1] == 1:
                    continue
                if damage == 'wrong-types' and c.namespace == TYPES:
                    c = replace(c, value=(c.value[0], c.value[1], (0, 0, 129)))
                result.append(c)
            kw['version_changes'] = tuple(result)
            if damage == 'extra-identity':
                kw['identity_changes'] += (IdentityOccurrenceChange('world.people', 99,
                    (('field', 'parents'),), incarnation_id=kw['identity_changes'][0].incarnation_id),)
            return original(*args, **kw)

        session.world.people[99] = Person(99, 0, 1, 1)
        session.skills[1, 'craft'].level = .75
        session.skills[1, 'craft'].provenance.append(42)
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError):
                session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1


@pytest.mark.parametrize('size', [1000, 10000])
def test_mixed_save_reads_only_the_changed_history_page(tmp_path, monkeypatch, size):
    from ate_sim import persistence_proof_world as world, persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    path, pair = fixture(tmp_path, size=size)
    with opened(path, pair) as session:
        history = session.skills[1, 'craft'].provenance
        changed_page = history._incarnation, (size-1)//128
        original, source = session.store.read_version, content._source_version

        def checked_read(pin, namespace, key, *args, **kw):
            assert namespace != ENTRY_NAMESPACE, 'unrelated history entry read'
            if namespace == PAGE_NAMESPACE:
                assert key == changed_page, 'unrelated history page read'
            return original(pin, namespace, key, *args, **kw)

        def checked_source(store, generation, namespace, key, *args, **kw):
            assert namespace != ENTRY_NAMESPACE, 'unrelated proof entry read'
            if namespace == PAGE_NAMESPACE:
                assert store.codec.decode(key) == changed_page, 'unrelated proof page read'
            return source(store, generation, namespace, key, *args, **kw)

        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('mixed save scanned World'))
            patch.setattr(session.store, 'read_version', checked_read)
            patch.setattr(content, '_source_version', checked_source)
            session.world.people[99] = Person(99, 0, 1, 1)
            session.skills[1, 'craft'].level = .75
            history.append(42)
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.world.people[99].id == 99
        assert len(restored.skills[1, 'craft'].provenance) == size + 1
        assert restored.skills[1, 'craft'].provenance[-1] == 42


def test_mixed_new_backing_alias_keeps_checked_fallback(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world
    from ate_sim.skills import SkillHistory
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []

        def audit(*args, **kw):
            calls.append(True)
            return original(*args, **kw)

        session.world.people[99] = Person(99, 0, 1, 1)
        session.world.skills.skills[3, 'craft'] = SkillHistory(
            3, 'craft', provenance=session.skills[1, 'craft'].provenance)
        session.skills[1, 'craft'].level = .75
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            assert session.save() == 1
            pair = session.proof_manifest
        assert calls
    with opened(path, pair) as restored:
        assert restored.skills[3, 'craft'].provenance is restored.skills[1, 'craft'].provenance
        assert restored.skills[1, 'craft'].level == .75


@pytest.mark.parametrize('witness', [False, True])
def test_identical_scalar_owner_rewrite_requires_updated_source_witness(tmp_path, witness):
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.incremental_store import StoreError, Membership
    from ate_sim.persistence_lazy import SOCIAL_PARTNERSHIP_NAMESPACE
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api

    def configure(w):
        w.social.partner(5, 9, 1)

    store, pin, pair = _proof_store(tmp_path, configure=configure)
    try:
        row = store.read_version(pin, SOCIAL_PARTNERSHIP_NAMESPACE, (5, 9), expected_record_schema=1)
        change = VersionChange(SOCIAL_PARTNERSHIP_NAMESPACE, (5, 9), row.value,
                               memberships=(Membership('person', 5, 0), Membership('person', 9, 0)))
        versions = (change,)
        if witness:
            delta = catalog.IdentityCatalog(store).prepare_delta(pin, versions, (),
                next_incarnation_id=store.read_identity_state(pin))
            versions += delta.decode(store.codec)[0]
        arguments = dict(commit_token='a'*32, version_changes=versions, changes=(),
                         new_segments=(), metadata=store.head_metadata())
        if witness:
            result = manifest_api().commit_world_manifest(store, pin, *pair, **arguments)
            assert result.commit.outcome == 'committed'
            pin = result.commit.pin
            assert not result.reaudited
            pair = result.manifest
        else:
            with pytest.raises(StoreError):
                manifest_api().commit_world_manifest(store, pin, *pair, **arguments)
            assert store.generation == 0
            assert manifest_api().resolve_world_manifest(store, pin, *pair, commit_token='a'*32).commit.outcome == 'not_committed'
    finally:
        store.close()
    with opened(store.path, pair) as restored:
        assert tuple(restored.world.social.partnerships) == ((5, 9),)


@pytest.mark.parametrize('witness', [False, True])
def test_identical_ordinary_event_ids_require_updated_source_witness(tmp_path, witness):
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.incremental_store import StoreError, RecordChange
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api
    store, pin, pair = _proof_store(tmp_path)
    try:
        change = RecordChange('world.event_ids', 0, store.read_record('world.event_ids', 0, expected_record_schema=1))
        versions = ()
        if witness:
            delta = catalog.IdentityCatalog(store).prepare_delta(pin, (), (), ordinary_changes=(change,),
                next_incarnation_id=store.read_identity_state(pin))
            versions = delta.decode(store.codec)[0]
        arguments = dict(commit_token='a'*32, version_changes=versions, changes=(change,),
                         new_segments=(), metadata=store.head_metadata())
        if witness:
            result = manifest_api().commit_world_manifest(store, pin, *pair, **arguments)
            pin, pair = result.commit.pin, result.manifest
            assert result.commit.outcome == 'committed' and not result.reaudited
        else:
            with pytest.raises(StoreError):
                manifest_api().commit_world_manifest(store, pin, *pair, **arguments)
            assert store.generation == 0
            assert manifest_api().resolve_world_manifest(store, pin, *pair, commit_token='a'*32).commit.outcome == 'not_committed'
    finally:
        store.close()
    with opened(store.path, pair) as restored:
        assert len(restored.world.event_ids) == 0
