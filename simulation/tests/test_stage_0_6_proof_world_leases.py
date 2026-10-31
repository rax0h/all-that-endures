"""Existing publisher leases compose without consuming semantic row budgets."""
import pytest
import shutil

from simulation.tests.test_stage_0_5_proof_world_session import fixture, opened


@pytest.fixture(scope='module')
def lease_source(tmp_path_factory):
    count=520
    def configure(world):
        world.settlements[1].memory = {str(n): [] for n in range(count)}
    return fixture(tmp_path_factory.mktemp('lease-source'), configure=configure)


@pytest.mark.parametrize('edit', ['scalar', 'tail', 'fresh'])
def test_many_borrowed_backings_keep_supported_proof_path(tmp_path, monkeypatch, lease_source, edit):
    from ate_sim import persistence_proof_world as world
    from ate_sim import persistence_proof_manifest_publish as manifests
    from ate_sim.persistence_history_dependencies import NAMESPACE

    from ate_sim.skills import SkillHistory
    from ate_sim import persistence_proof_publication as content
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE, ENTRY_NAMESPACE
    source, pair = lease_source
    path = tmp_path/'world.sqlite'
    shutil.copyfile(source, path)
    with opened(path, pair) as session:
        borrowed = list(session.world.settlements[1].memory.values())
        assert len(borrowed) == 520
        parent_allocator = session.store.read_identity_state(session.pin)
        selected_tail = None
        session.skills[1, 'craft'].level = .75
        if edit == 'tail':
            history = session.skills[1, 'craft'].provenance
            selected_tail = history._incarnation, 0
            history.append(42)
        elif edit == 'fresh':
            session.world.skills.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=[7, 8])
        original, observed = manifests.commit_world_manifest, []
        source_read = content._source_version

        def checked_source(store, generation, namespace, key, **kwargs):
            row = source_read(store, generation, namespace, key, **kwargs)
            if row is not None and namespace in (PAGE_NAMESPACE, ENTRY_NAMESPACE):
                native_key = store.codec.decode(key)
                fresh = edit == 'fresh' and native_key[0] >= parent_allocator
                selected = namespace == PAGE_NAMESPACE and native_key == selected_tail
                assert fresh or selected, 'unrelated history body read'
            return row

        def capture(*args, **kwargs):
            observed.append(sum(c.namespace == NAMESPACE for c in kwargs['version_changes']))
            return original(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(manifests, 'commit_world_manifest', capture)
            patch.setattr(content, '_source_version', checked_source)
            patch.setattr(world, '_audit_world', lambda *a, **k: pytest.fail('lease-heavy save scanned World'))
            assert session.save() == 1
            pair = session.proof_manifest
        assert observed[0] > 512
        expected = session.world.digest()
        assert all(len(value) == 0 for value in borrowed)
        assert all(session.pin.token in session.store.read_version(
            session.pin, NAMESPACE, value._incarnation, expected_record_schema=1).value[2] for value in borrowed)
    with opened(path, pair) as restored:
        assert restored.world.digest() == expected
        assert restored.skills[1, 'craft'].level == .75
        assert restored.skills[1, 'craft'].provenance is restored.skills[2, 'craft'].provenance
        assert len(restored.world.settlements[1].memory) == 520
        if edit == 'tail':
            assert list(restored.skills[1, 'craft'].provenance) == list(range(32))+[42]
        elif edit == 'fresh':
            assert list(restored.skills[3, 'craft'].provenance) == [7, 8]


@pytest.mark.parametrize('limit', ['rows', 'bytes'])
def test_exemption_budget_is_all_or_nothing_and_still_rejects_foreign_tokens(tmp_path, monkeypatch, limit):
    from dataclasses import replace
    from types import SimpleNamespace
    from ate_sim import persistence_proof_world_value as values
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
    from ate_sim.incremental_store import StoreError
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api

    store, pin, pair = _proof_store(tmp_path)
    try:
        changes = tuple(VersionChange(NAMESPACE, key,
            dependency_value(store.read_version(pin, NAMESPACE, key, expected_record_schema=1).value[1], (pin.token,)))
            for key in (5, 6))
        prepared = tuple(store._prepare_version_changes(changes))
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        with store.read_snapshot(pin):
            accepted = values.validate_lease_updates(store, request, prepared)
            assert accepted == frozenset((NAMESPACE, store.codec.encode(key)) for key in (5, 6))
            monkeypatch.setattr(values, 'MAX_LEASE_ROWS' if limit == 'rows' else 'MAX_LEASE_BYTES', 1)
            assert values.validate_lease_updates(store, request, prepared) == frozenset()
            bad = replace(changes[1], value=dependency_value(changes[1].value[1], ('foreign',)))
            corrupt = tuple(store._prepare_version_changes((changes[0], bad)))
            with pytest.raises(StoreError, match='foreign publisher lease'):
                values.validate_lease_updates(store, request, corrupt)
        assert store.generation == 0
        assert store.read_version(pin, NAMESPACE, 5, expected_record_schema=1).value[2] == ()
    finally:
        store.close()


@pytest.mark.parametrize('kind', ['fresh', 'deleted', 'membership', 'reinsertion'])
def test_structural_leases_are_not_exempted(tmp_path, kind):
    from types import SimpleNamespace
    from ate_sim import persistence_proof_world_value as values
    from ate_sim.persistence_lazy_store import VersionChange
    from ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
    from ate_sim.incremental_store import Membership
    from simulation.tests.test_stage_0_5_proof_world import _proof_store, manifest_api

    store, pin, pair = _proof_store(tmp_path)
    try:
        key = 5 if kind != 'fresh' else 10000
        change = VersionChange(NAMESPACE, key, dependency_value('list', (pin.token,)),
            delete=kind == 'deleted', reinsertion=kind == 'reinsertion',
            memberships=(Membership('extra', 1, 0),) if kind == 'membership' else ())
        prepared = tuple(store._prepare_version_changes((change,)))
        request = SimpleNamespace(pin=pin, pairs=manifest_api()._pairs(store, pin.captured_head))
        with store.read_snapshot(pin):
            assert values.validate_lease_updates(store, request, prepared) == frozenset()
        assert store.generation == 0
    finally:
        store.close()
