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
