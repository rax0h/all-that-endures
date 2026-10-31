"""Fresh backing forests must compose with the existing native publisher."""
import pytest
from ate_sim.skills import SkillHistory
from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


@pytest.mark.parametrize('length', [0, 3, 129])
def test_new_skill_owner_and_its_lists_avoid_full_audit(tmp_path, monkeypatch, length):
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('fresh backing scanned World'))
            session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', teachers=[7], provenance=list(range(length)))
            session.skills[1, 'craft'].level = .75
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.skills[3, 'craft'].teachers) == [7]
        assert list(restored.skills[3, 'craft'].provenance) == list(range(length))
        assert restored.skills[1, 'craft'].level == .75


def test_new_owner_can_reference_existing_shared_history_without_scanning_it(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world as world, persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    path, pair = fixture(tmp_path, size=10000)
    with opened(path, pair) as session:
        old_allocator = session.store.read_identity_state(session.pin)
        read, source = session.store.read_version, content._source_version
        def checked_read(pin, ns, key, *a, **kw):
            if ns in (PAGE_NAMESPACE, ENTRY_NAMESPACE):
                assert key[0] >= old_allocator, 'unrelated old history body read'
            return read(pin, ns, key, *a, **kw)
        def checked_source(store, generation, ns, key, *a, **kw):
            if ns in (PAGE_NAMESPACE, ENTRY_NAMESPACE):
                assert store.codec.decode(key)[0] >= old_allocator, 'unrelated old proof body read'
            return source(store, generation, ns, key, *a, **kw)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('shared target scanned World'))
            patch.setattr(session.store, 'read_version', checked_read)
            patch.setattr(content, '_source_version', checked_source)
            session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft',
                provenance=session.skills[1, 'craft'].provenance)
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert restored.skills[3, 'craft'].provenance is restored.skills[1, 'craft'].provenance
        assert len(restored.skills[3, 'craft'].provenance) == 10000


def test_new_nested_map_set_and_shared_record_forest_restores_exact_identity(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys
    from ate_sim import persistence_proof_world as world
    from ate_sim.culture import Practice
    path, pair = fixture(tmp_path)
    record = SkillHistory(9, 'nested', teachers=[7], provenance=[3, 4])
    with opened(path, pair) as session:
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('nested forest scanned World'))
            session.world.culture.practices[3] = Practice(3, 'craft', 'nested', 0, 1,
                traits={'a': record, 'b': record, 'nested': [{'values': {1, 2, 3}}]})
            assert session.save() == 1
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        traits = restored.world.culture.practices[3].traits
        assert traits['a'] is traits['b']
        assert list(traits['a'].provenance) == [3, 4]
        assert set(traits['nested'][0]['values']) == {1, 2, 3}
    result = subprocess.run([sys.executable, '-c',
        "import json,sys; from ate_sim.persistence_proof_world_session import open_audited_proof_world_session; "
        "s=open_audited_proof_world_session(sys.argv[1],rules_id='private-catalog-copy',expected_commitment=bytes.fromhex(sys.argv[2])); "
        "t=s.world.culture.practices[3].traits; print(json.dumps([t['a'] is t['b'],list(t['a'].teachers),sorted(t['nested'][0]['values'])]));s.close()",
        str(path), pair[1].hex()], capture_output=True, text=True, check=True, timeout=60)
    assert json.loads(result.stdout) == [True, [7], [1, 2, 3]]


def test_cyclic_fresh_backing_graph_is_rejected(tmp_path, monkeypatch):
    from dataclasses import replace
    from ate_sim.culture import Practice
    from ate_sim.incremental_store import StoreError
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_nested_history import ENTRY_NAMESPACE, HistoryReference
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original = manifests.commit_world_manifest
        shared = []
        session.world.culture.practices[3] = Practice(3, 'craft', 'cycle', 0, 1,
            traits={'self': {'link': shared}, 'keep': shared})

        def corrupt(store, pin, *args, **kw):
            versions = list(kw['version_changes'])
            owner = next(c for c in versions if c.namespace == 'world.culture.practices')
            target = owner.value.traits.incarnation
            entry = next(c for c in versions if c.namespace == ENTRY_NAMESPACE and c.key[1] == 'link')
            versions = [replace(c, value=(c.value[0], c.value[1], HistoryReference('map', target)))
                        if c is entry else c for c in versions]
            identities = tuple(replace(c, incarnation_id=target) if c.owner_namespace == ENTRY_NAMESPACE
                               and c.owner_key == entry.key and c.occurrence_path == (('index', 2),)
                               else c for c in kw['identity_changes'])
            allocator = next(c.value[2] for c in versions if c.namespace == catalog.CATALOG_NAMESPACE)
            sources = tuple(c for c in versions if c.namespace in catalog.IDENTITY_OWNER_FAMILIES)
            delta = catalog.IdentityCatalog(store).prepare_delta(pin, sources, identities,
                next_incarnation_id=allocator)
            kw['version_changes'] = tuple(c for c in versions if c.namespace not in catalog.CATALOG_NAMESPACES) + delta.decode(store.codec)[0]
            kw['identity_changes'] = identities
            return original(store, pin, *args, **kw)

        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError, match='cyclic fresh backing'):
                session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1


@pytest.mark.parametrize('old', [False, True])
def test_backed_record_cannot_bypass_class_incoming_policy(tmp_path, old):
    from ate_sim.core import Settlement
    from ate_sim.culture import Practice
    from ate_sim.materials import MaterialLot
    from ate_sim.incremental_store import StoreError

    def lot():
        return MaterialLot(9, 'wood', 1., 1., 1, 1, 0, 0, 'person', 1, transfers=[True])

    def configure(w):
        if old:
            value = lot()
            w.settlements[1] = Settlement(1, 0, 0, memory={'a': value, 'b': value})

    path, pair = fixture(tmp_path, configure=configure)
    with opened(path, pair) as session:
        value = session.world.settlements[1].memory['a'] if old else lot()
        session.world.culture.practices[3] = Practice(3, 'craft', 'policy', 0, 1, traits={'record': value})
        with pytest.raises(StoreError, match='incoming member policy'):
            session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0


@pytest.mark.parametrize('phase', ['before_head', 'before_commit', 'after_commit'])
def test_fresh_forest_recovers_original_frozen_attempt(tmp_path, phase):
    from ate_sim.culture import Practice
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        shared = SkillHistory(9, 'nested', provenance=[1, 2])
        session.world.culture.practices[3] = Practice(3, 'craft', 'recovery', 0, 1, traits={'a': shared, 'b': shared})

        def fault(at):
            if at == phase:
                raise RuntimeError('interrupted fresh forest')

        session.store._phase_hook = fault
        with pytest.raises(RuntimeError, match='interrupted fresh forest'):
            session.save()
        session.store._phase_hook = lambda _: None
        assert session.resolve_save() == (1 if phase == 'after_commit' else 0)
        assert session.save() == 1
        pair = session.proof_manifest
    with opened(path, pair) as restored:
        traits = restored.world.culture.practices[3].traits
        assert traits['a'] is traits['b']
        assert list(traits['a'].provenance) == [1, 2]


@pytest.mark.parametrize('damage', ['missing-page', 'extra-page', 'bool-count', 'dependency-kind', 'missing-identity', 'extra-identity', 'missing-header'])
def test_fresh_forest_rejects_inconsistent_frozen_authority(tmp_path, monkeypatch, damage):
    from dataclasses import replace
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    from ate_sim.persistence_history_types import NAMESPACE as TYPES
    from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
    from ate_sim.persistence_lazy_store import VersionChange, IdentityOccurrenceChange
    from ate_sim.incremental_store import StoreError
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original = manifests.commit_world_manifest

        def corrupt(*args, **kw):
            versions = list(kw['version_changes'])
            owner = next(c for c in versions if c.namespace == 'world.skills.skills')
            inc = owner.value.provenance.incarnation
            result = []
            for c in versions:
                if damage == 'missing-page' and c.namespace == PAGE_NAMESPACE and c.key == (inc, 1): continue
                if damage == 'missing-header' and c.namespace == catalog.OWNER_NAMESPACE and c.key == (PAGE_NAMESPACE, (inc, 1)): continue
                if damage == 'bool-count' and c.namespace == TYPES and c.value[2] == (1, 0, 0):
                    c = replace(c, value=(c.value[0], c.value[1], (True, 0, 0)))
                if damage == 'dependency-kind' and c.namespace == DEPENDENCIES and c.key == inc:
                    c = replace(c, value=(c.value[0], 'map', c.value[2]))
                result.append(c)
            if damage == 'extra-page': result.append(VersionChange(PAGE_NAMESPACE, (inc, 99), (1,)))
            if damage == 'missing-identity': kw['identity_changes'] = ()
            if damage == 'extra-identity': kw['identity_changes'] += (IdentityOccurrenceChange('world.skills.skills', (3, 'craft'), (('field', 'missing'),), incarnation_id=inc),)
            kw['version_changes'] = tuple(result)
            return original(*args, **kw)

        session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', teachers=[7], provenance=list(range(129)))
        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', corrupt)
            with pytest.raises(StoreError): session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1


@pytest.mark.parametrize('kind', ['occurrence', 'link'])
def test_surplus_physical_alias_roster_is_rejected_before_legacy_scan(tmp_path, monkeypatch, kind):
    from ate_sim import persistence_proof_world_new_backings as backing
    from ate_sim import persistence_lazy_identity_catalog as catalog
    from ate_sim.persistence_lazy_store import _identity_occurrence_checksum, _query_checksum
    from ate_sim.incremental_store import StoreError
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original = backing.Forest.guard_alias_work
        shared = session.skills[1, 'craft'].provenance
        inc = shared._incarnation
        session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=shared)
        with monkeypatch.context() as patch:
            def inject(forest, incarnations):
                original(forest, incarnations)
                store, g = forest.store, forest.request.pin.captured_head
                key, path = store.codec.encode(999), store.codec.encode(())
                if kind == 'occurrence':
                    checksum = _identity_occurrence_checksum('world.people', key, path, inc, g, None)
                    store.db.execute('INSERT INTO lazy_identity_occurrence_versions VALUES(?,?,?,?,?,?,?)',
                                     ('world.people', key, path, inc, g, None, checksum))
                    patch.setattr(store, 'iter_identity_occurrences_for_incarnation', lambda *a, **k: pytest.fail('unbounded occurrence scan'))
                else:
                    value = store.codec.encode(inc)
                    checksum = _query_checksum(catalog.LINK_NAMESPACE, 'incarnation', value, key, 999, g, None)
                    store.db.execute('INSERT INTO lazy_query_versions VALUES(?,?,?,?,?,?,?,?)',
                                     (catalog.LINK_NAMESPACE, 'incarnation', value, key, 999, g, None, checksum))
                    patch.setattr(store, 'iter_query_memberships', lambda *a, **k: pytest.fail('unbounded link scan'))
            patch.setattr(backing.Forest, 'guard_alias_work', inject)
            with pytest.raises(StoreError, match='physical alias roster'): session.save()
        assert session.store.generation == 0
        assert session.resolve_save() == 0
        assert session.save() == 1


def test_large_old_alias_scope_uses_checked_fallback(tmp_path, monkeypatch):
    from ate_sim import persistence_proof_world_new_backings as backing, persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []
        def audit(*a, **k):
            calls.append(True)
            return original(*a, **k)
        with monkeypatch.context() as patch:
            patch.setattr(backing, 'MAX_OLD_ALIASES', 1)
            patch.setattr(world, '_audit_world', audit)
            session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=session.skills[1, 'craft'].provenance)
            assert session.save() == 1
            assert calls


def test_new_sequence_backing_retains_checked_fallback(tmp_path, monkeypatch):
    from ate_sim.core import Household
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []
        def audit(*a, **k):
            calls.append(True)
            return original(*a, **k)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            session.world.households[99] = Household(99, 1, members=[1, 2])
            assert session.save() == 1
            assert calls
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.world.households[99].members) == [1, 2]


def test_generic_backed_record_representation_retains_checked_fallback(tmp_path, monkeypatch):
    from ate_sim.core import Household
    from ate_sim.culture import Practice
    from ate_sim import persistence_proof_world as world
    path, pair = fixture(tmp_path)
    with opened(path, pair) as session:
        original, calls = world._audit_world, []
        def audit(*a, **k):
            calls.append(True)
            return original(*a, **k)
        with monkeypatch.context() as patch:
            patch.setattr(world, '_audit_world', audit)
            session.world.culture.practices[3] = Practice(3, 'craft', 'generic', 0, 1,
                traits={'household': Household(99, 1, members=[1, 2])})
            assert session.save() == 1
            assert calls
            pair = session.proof_manifest
    with opened(path, pair) as restored:
        assert list(restored.world.culture.practices[3].traits['household'].members) == [1, 2]
