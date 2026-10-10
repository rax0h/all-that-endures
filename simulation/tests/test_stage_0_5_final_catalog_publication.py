"""Checked identity joins the central immutable publisher, with no second commit."""
from dataclasses import dataclass, make_dataclass, replace

import pytest

from simulation.ate_sim.incremental_store import RecordChange, StoreConflictError, StoreIntegrityError
from simulation.ate_sim.persistence_lazy_store import VersionChange
from simulation.ate_sim.persistence_lazy_participants import (
    VERSION_FIELDS, IDENTITY_FIELDS, freeze_hybrid_publication)
from simulation.tests.test_persistence_lazy_store import make_store, metadata
from simulation.tests.test_stage_0_5_final_owner_replacement import setup, NS, LEFT, Child


@dataclass(frozen=True)
class ColdPlan:
    token: str
    changes: tuple
    new_segments: tuple
    metadata: dict
    layout_value: object = None


Plan = make_dataclass('CatalogHybridPlan', [(name, object) for name in
    (*VERSION_FIELDS, *IDENTITY_FIELDS, 'scalar_record_plans', 'layout_value',
     'cold_plan', 'token', 'target_generation', 'publication')], frozen=True)


def prepare(coord, owners, *, token='hybrid', identities=None, ordinary=()):
    values = {name: () for name in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
    values['version_changes'] = (VersionChange(NS, 1, owners[NS, 1]),)
    values['identity_changes'] = tuple(coord.placement_overlay.values()) if identities is None else identities
    return Plan(**values, scalar_record_plans=(), layout_value=None,
        cold_plan=ColdPlan(token, ordinary, (), metadata(2, (NS, 'world_identity_links'))),
        token=token, target_generation=2, publication=None)


def freeze(coord, plan):
    return freeze_hybrid_publication(coord.store, coord.pin, plan,
        next_incarnation=coord.registry.next_incarnation, required_format_version=3,
        identity_coordinator=coord)


def acknowledge(publication, plan, result):
    for unit in publication.participants:
        unit.validate_publication(unit.delta, result.pin)
    head = publication.participants[0].store.checked_head()
    for unit in publication.participants:
        unit.confirm_cold_publication(unit.delta, result.pin, plan.cold_plan, head)
    for unit in publication.participants:
        unit.accept_delta(unit.delta, result.pin)


def test_catalog_and_family_commit_together_with_exact_old_pin(tmp_path):
    with make_store(tmp_path / 'join.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        old = store.capture_pin()
        replacement = Child(10)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, replacement),))
        plan = prepare(coord, owners)
        publication = freeze(coord, plan)
        assert {unit.namespace for unit in publication.participants} == {NS, 'identity-coordinator'}
        arguments = publication.commit_arguments(plan)
        assert len(arguments['identity_changes']) == 1  # not duplicated by the catalog
        assert len(arguments['version_changes']) > 1
        with pytest.raises(StoreConflictError):
            coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(11)),))
        result = store.commit(coord.pin, **arguments)
        acknowledge(publication, plan, result)
        acknowledge(publication, plan, result)  # exact acknowledgement is idempotent
        assert all(unit.accepted for unit in publication.participants)
        assert coord.pin == result.pin and not coord.dirty_owners
        assert store.read_identity_group(old, 2).occurrences == ((NS, 1, LEFT), (NS, 2, LEFT))
        assert store.read_identity_group(result.pin, 2).occurrences == ((NS, 2, LEFT),)
        assert registry.object_for_incarnation(registry.incarnation_for_object(replacement)) is replacement


@pytest.mark.parametrize('fault', ['missing', 'extra', 'duplicate', 'legacy_links'])
def test_inconsistent_sources_reject_before_freezing_coordinator(tmp_path, fault):
    with make_store(tmp_path / 'bad-plan.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        changes = tuple(coord.placement_overlay.values())
        identities = () if fault == 'missing' else changes + changes if fault == 'duplicate' else changes
        plan = prepare(coord, owners, identities=identities,
                       ordinary=(RecordChange('world_identity_links', 0, ()),) if fault == 'legacy_links' else ())
        if fault == 'extra':
            plan = replace(plan, nested_history_identity_changes=changes)
        with pytest.raises(StoreIntegrityError):
            freeze(coord, plan)
        assert coord._prepared is None and coord.placement_overlay
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(11)),))


def test_failed_joint_publication_thaws_only_checked_attempt_and_retries(tmp_path):
    with make_store(tmp_path / 'retry.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        plan = prepare(coord, owners, token='failed')
        publication = freeze(coord, plan)
        def fail(phase):
            if phase == 'before_head':
                raise OSError('before head')
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(coord.pin, **publication.commit_arguments(plan))
        publication.abort_uncommitted()
        assert coord._prepared is None and coord.placement_overlay and coord.dirty_owners
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(11)),))
        store._phase_hook = lambda phase: None
        retry = prepare(coord, owners, token='retry')
        frozen = freeze(coord, retry)
        result = store.commit(coord.pin, **frozen.commit_arguments(retry))
        acknowledge(frozen, retry, result)
        assert store.read_version(result.pin, NS, 1, expected_record_schema=1).value.left.value == 11


def test_lost_ack_keeps_exact_frozen_joint_plan_until_resolution(tmp_path):
    with make_store(tmp_path / 'lost.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        plan = prepare(coord, owners)
        publication = freeze(coord, plan)
        def fail(phase):
            if phase == 'after_commit':
                raise OSError('lost acknowledgement')
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(coord.pin, **publication.commit_arguments(plan))
        plan.version_changes[0].value.left.value = 999
        plan.cold_plan.metadata['seed'] = -1
        altered = replace(plan, token='wrong-token', target_generation=999)
        assert publication.commit_arguments(altered)['commit_token'] == 'hybrid'
        assert publication.commit_arguments(altered)['version_changes'][0].value.left.value == 10
        with pytest.raises(StoreConflictError):
            publication.abort_uncommitted()
        assert coord._prepared is not None and coord.placement_overlay
        store._phase_hook = lambda phase: None
        result = store.resolve_commit(coord.pin, 'hybrid')
        acknowledge(publication, publication.replay_plan(altered), result)
        assert not coord.placement_overlay and all(unit.accepted for unit in publication.participants)


def test_joint_publication_rejects_allocator_and_parent_mismatch(tmp_path):
    with make_store(tmp_path / 'parent.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        plan = prepare(coord, owners)
        with pytest.raises(StoreIntegrityError):
            freeze_hybrid_publication(store, coord.pin, plan,
                next_incarnation=registry.next_incarnation + 1, required_format_version=3,
                identity_coordinator=coord)
        with pytest.raises(StoreIntegrityError):
            freeze(coord, replace(plan, target_generation=99))
        assert coord._prepared is None


def test_unrelated_auxiliary_write_advances_clean_coordinator_without_catalog_writes(tmp_path):
    with make_store(tmp_path / 'unrelated.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        plan = replace(prepare(coord, owners),
                       version_changes=(VersionChange('aux.test', 0, ('bounded',)),))
        plan = replace(plan, cold_plan=replace(plan.cold_plan,
            metadata=metadata(2, (NS, 'world_identity_links', 'aux.test'))))
        before = store.diagnostics()
        publication = freeze(coord, plan)
        assert publication.coordinator_participant.delta.decode(store.codec) == ((), (), ())
        assert store.diagnostics() == before  # no owner/group traversal
        with pytest.raises(StoreConflictError):
            coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        result = store.commit(coord.pin, **publication.commit_arguments(plan))
        acknowledge(publication, plan, result)
        assert coord.pin == result.pin and coord._prepared is None


def test_missing_dirty_owner_payload_rejects_before_freeze(tmp_path):
    with make_store(tmp_path / 'missing-owner.sqlite') as store:
        coord, registry, owners, *_ = setup(store)
        coord.replace_subtree((NS, 1), LEFT, ((LEFT, Child(10)),))
        plan = replace(prepare(coord, owners), version_changes=())
        with pytest.raises(StoreIntegrityError, match='owner'):
            freeze(coord, plan)
        assert coord._prepared is None and coord.placement_overlay


def backing_plan(coord, child, *, changes=None):
    values = {name: () for name in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
    values['nested_history_version_changes'] = child.pending_changes() if changes is None else changes
    return Plan(**values, scalar_record_plans=(), layout_value=None,
        cold_plan=ColdPlan('backing-hybrid', (), (), metadata(2, ('world.skills.skills',
            'world.settlements', 'world_identity_links', 'aux.test'))),
        token='backing-hybrid', target_generation=2, publication=None)


@pytest.mark.parametrize('mixed', [False, True])
def test_frozen_backing_writes_force_and_publish_all_physical_owner_headers(tmp_path, mixed):
    from simulation.tests.test_stage_0_5_final_coordinator_header_witnesses import fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
    with store_at(tmp_path / 'backing-join.sqlite') as store:
        coord, child, calls = fixture(store, mixed=mixed)
        child.append(8)
        plan = backing_plan(coord, child)
        publication = freeze(coord, plan)
        arguments = publication.commit_arguments(plan)
        assert len(calls) == 2
        assert sum(c.namespace == 'world.skills.skills' for c in arguments['version_changes']) == (1 if mixed else 2)
        assert sum(c.namespace == 'world.settlements' for c in arguments['changes']) == int(mixed)
        # Neither caller-held source bodies nor private decoded replays can
        # change the forced physical header captured with the catalog.
        if mixed:
            arguments['changes'][0].value.memory.clear()
            assert publication.commit_arguments(plan)['changes'][0].value.memory
        result = store.commit(coord.pin, **publication.commit_arguments(plan))
        acknowledge(publication, plan, result)
        acknowledge(publication, plan, result)
        child.accept_save(result.pin)
        assert LazyHistoryList(store, result.pin, 1) == [7, 8]
        assert all(unit.accepted for unit in publication.participants)
        assert store.read_version(result.pin, 'world.skills.skills', (1, 'craft'), expected_record_schema=1).valid_from == 2


def test_guarded_noop_with_unrelated_commit_does_not_force_owner_headers(tmp_path):
    from simulation.tests.test_stage_0_5_final_coordinator_header_witnesses import fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    with store_at(tmp_path / 'backing-noop.sqlite') as store:
        coord, child, calls = fixture(store)
        coord.routes_for_mutation(child)
        plan = backing_plan(coord, child, changes=(VersionChange('aux.test', 0, ('bounded',)),))
        before = store.diagnostics()
        publication = freeze(coord, plan)
        assert calls == []
        assert publication.coordinator_participant.delta.decode(store.codec) == ((), (), ())
        assert store.diagnostics() == before
        result = store.commit(coord.pin, **publication.commit_arguments(plan))
        acknowledge(publication, plan, result)


def test_unrouted_backing_write_rejects_before_coordinator_freeze(tmp_path):
    from simulation.tests.test_stage_0_5_final_coordinator_header_witnesses import fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    from simulation.ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    with store_at(tmp_path / 'backing-unrouted.sqlite') as store:
        coord, child, calls = fixture(store)
        plan = backing_plan(coord, child, changes=(VersionChange(PAGE_NAMESPACE, (1, 0), (7, 8)),))
        with pytest.raises(StoreIntegrityError, match='routed identity group'):
            freeze(coord, plan)
        assert coord._prepared is None and calls == []


@pytest.mark.parametrize('phase', ['before_head', 'after_commit'])
def test_backing_dependencies_share_central_commit_and_checked_failed_release(tmp_path, phase):
    from simulation.ate_sim.persistence_history_dependencies import BackingDependencyPool, NAMESPACE
    from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
    with make_store(tmp_path / 'dependencies-join.sqlite') as store:
        pin = store.capture_pin()
        pool = BackingDependencyPool(store, pin)
        child = LazyHistoryList(store, pin, 1, initial_values=[7])
        pool.acquire(child)
        values = {name: () for name in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
        values['nested_history_version_changes'] = child.pending_changes()
        plan = Plan(**values, scalar_record_plans=(), layout_value=None,
            cold_plan=ColdPlan('dependency-joint', (), (), metadata(1, ())),
            token='dependency-joint', target_generation=1, publication=None)
        publication = freeze_hybrid_publication(store, pin, plan, next_incarnation=2,
            required_format_version=3, backing_dependencies=pool)
        assert pool.prepare_delta() is publication.dependency_participant.delta
        assert len([c for c in publication.commit_arguments(plan)['version_changes'] if c.namespace == NAMESPACE]) == 1
        def fail(at):
            if at == phase:
                raise OSError('joint backing failure')
        store._phase_hook = fail
        with pytest.raises(OSError):
            store.commit(pin, **publication.commit_arguments(plan))
        store._phase_hook = lambda at: None
        if phase == 'before_head':
            publication.abort_uncommitted()
            assert pool._prepared is None and child[-1] == 7
            plan = replace(plan, token='dependency-retry', cold_plan=replace(plan.cold_plan, token='dependency-retry'))
            publication = freeze_hybrid_publication(store, pin, plan, next_incarnation=2,
                required_format_version=3, backing_dependencies=pool)
            result = store.commit(pin, **publication.commit_arguments(plan))
        else:
            with pytest.raises(StoreConflictError):
                publication.abort_uncommitted()
            assert pool.prepare_delta() is publication.dependency_participant.delta
            result = store.resolve_commit(pin, plan.token)
        acknowledge(publication, plan, result)
        acknowledge(publication, plan, result)
        assert pool.pin == result.pin and pool._prepared is None
        assert store.read_version(result.pin, NAMESPACE, 1, expected_record_schema=1).value[2] == (pin.token,)
        assert store.db.execute('SELECT COUNT(*) FROM generation_pins').fetchone()[0] == 1


def test_failed_catalog_preparation_releases_only_new_dependency_freeze(tmp_path):
    from simulation.ate_sim.persistence_history_dependencies import BackingDependencyPool
    from simulation.tests.test_stage_0_5_final_coordinator_header_witnesses import fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    with store_at(tmp_path / 'preparation-join.sqlite') as store:
        coord, child, calls = fixture(store, callback=False)
        # Initial checked dependency authority is mandatory for this existing backing.
        from simulation.ate_sim.persistence_history_dependencies import NAMESPACE, dependency_value
        pin = store.commit(coord.pin, commit_token='dependency-initial', changes=(), new_segments=(),
            version_changes=(VersionChange(NAMESPACE, 1, dependency_value('list')),),
            metadata=metadata(2, ('world.skills.skills', 'world_identity_links'))).pin
        coord.pin = child._pin = pin
        pool = BackingDependencyPool(store, pin)
        pool.acquire(child)
        child.append(8)
        plan = replace(backing_plan(coord, child), target_generation=3)
        plan = replace(plan, cold_plan=replace(plan.cold_plan, metadata=metadata(3, ())))
        with pytest.raises(StoreIntegrityError, match='physical owner header'):
            freeze_hybrid_publication(store, pin, plan, next_incarnation=2,
                required_format_version=3, identity_coordinator=coord, backing_dependencies=pool)
        assert coord._prepared is None and pool._prepared is None
        assert child[-1] == 8 and pool.protected_incarnations() == (1,)


def test_bounded_retirement_batch_joins_frozen_publication_without_routing_deleted_backing(tmp_path):
    from simulation.tests.test_stage_0_5_final_history_retirement import fixture as retirement_fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    from simulation.ate_sim.persistence_history_retirement import prepare_retirement_delta
    from simulation.ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    with store_at(tmp_path / 'retirement-join.sqlite') as store:
        pin, pool, alias, old = retirement_fixture(store, 1000)
        store.release_pin(old)
        pool.close()
        pin = store.capture_pin()
        retirement = prepare_retirement_delta(store, pin, row_budget=4)
        values = {name: () for name in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
        plan = Plan(**values, scalar_record_plans=(), layout_value=None,
            cold_plan=ColdPlan('retirement-joint', (), (), metadata(3, ('world.currency.wallets', 'world_identity_links'))),
            token='retirement-joint', target_generation=3, publication=None)
        publication = freeze_hybrid_publication(store, pin, plan, next_incarnation=2,
            required_format_version=3, retirement_delta=retirement)
        arguments = publication.commit_arguments(plan)
        assert len(arguments['version_changes']) == 4
        assert sum(c.namespace == PAGE_NAMESPACE for c in arguments['version_changes']) == 3
        result = store.commit(pin, **arguments)
        acknowledge(publication, plan, result)
        acknowledge(publication, plan, result)
        assert all(unit.accepted for unit in publication.participants)
        assert store.namespace_size(result.pin, PAGE_NAMESPACE) == 5


def test_duplicate_backing_authorities_reject_before_freezing_dependency_pool(tmp_path):
    from simulation.ate_sim.persistence_history_dependencies import BackingDependencyPool, NAMESPACE, dependency_value
    from simulation.ate_sim.persistence_lazy_nested_history import LazyHistoryList
    with make_store(tmp_path / 'duplicate-backings.sqlite') as store:
        pin = store.capture_pin()
        pool = BackingDependencyPool(store, pin)
        child = LazyHistoryList(store, pin, 1, initial_values=[])
        pool.acquire(child)
        values = {name: () for name in (*VERSION_FIELDS, *IDENTITY_FIELDS)}
        values['nested_history_version_changes'] = child.pending_changes() + (VersionChange(NAMESPACE, 1, dependency_value('list')),)
        plan = Plan(**values, scalar_record_plans=(), layout_value=None,
            cold_plan=ColdPlan('duplicate-joint', (), (), metadata(1, ())),
            token='duplicate-joint', target_generation=1, publication=None)
        with pytest.raises(StoreIntegrityError, match='duplicate.*authority'):
            freeze_hybrid_publication(store, pin, plan, next_incarnation=2,
                required_format_version=3, backing_dependencies=pool)
        assert pool._prepared is None and pool.protected_incarnations() == (1,)


@pytest.mark.parametrize('size', [1000, 10000])
def test_frozen_changed_backing_discovery_is_independent_of_history_extent(tmp_path, size, record_property):
    from simulation.tests.test_stage_0_5_final_coordinator_header_witnesses import fixture
    from simulation.tests.test_stage_0_5_final_sequence_compat import store_at
    from simulation.ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    with store_at(tmp_path / 'bounded-join.sqlite') as store:
        coord, child, calls = fixture(store, history_size=size)
        child[0] = -1
        plan = backing_plan(coord, child)
        before = store.diagnostics()
        publication = freeze(coord, plan)
        after = store.diagnostics()
        assert len(calls) == 2
        assert sum(c.namespace == PAGE_NAMESPACE for c in publication.commit_arguments(plan)['version_changes']) == 1
        assert after.payload_reads - before.payload_reads <= 8
        assert after.payload_read_bytes - before.payload_read_bytes <= 8192
        assert publication.frozen_bytes <= 16384
        for name, value in {'history': size, 'payload_reads': after.payload_reads - before.payload_reads,
                'payload_bytes': after.payload_read_bytes - before.payload_read_bytes,
                'metadata_rows': after.metadata_rows - before.metadata_rows,
                'frozen_bytes': publication.frozen_bytes}.items():
            record_property(name, value)
