"""Actual World deletion queues bounded cleanup, without retiring live aliases."""
import gc

import pytest

from ate_sim.persistence_history_retirement import NAMESPACE, pending_retirement
from ate_sim.persistence_history_dependencies import NAMESPACE as DEPENDENCIES
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, PAGE_NAMESPACE, DESCRIPTOR_NAMESPACE
from ate_sim.persistence_lazy_store import GenerationPressureError
from ate_sim.skills import SkillHistory
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


@pytest.mark.parametrize('size', [1000, 10000])
def test_world_last_owner_queues_without_pages_and_retained_alias_blocks_cleanup(tmp_path, size):
    target = converted_catalog(tmp_path, size)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        read_page = child._read_page
        child._read_page = lambda *_: pytest.fail('last-owner retirement read a historical member page')
        commit, captured = session.store.commit, []
        def record(*args, **kwargs):
            captured.append(kwargs['version_changes'])
            return commit(*args, **kwargs)
        session.store.commit = record
        del session.skills[1, 'craft']
        session.save()
        assert not pending_retirement(session.store, session.pin, inc)
        del session.skills[2, 'craft']
        session.save()
        assert pending_retirement(session.store, session.pin, inc)
        assert not any(c.namespace == PAGE_NAMESPACE for c in captured[-1])
        for _ in range(4):
            session.world.year += 1
            session.save()
            assert not any(c.namespace == PAGE_NAMESPACE for c in captured[-1])
        assert session.store.contains_lazy_key(session.pin, DESCRIPTOR_NAMESPACE, inc)
        child._read_page = read_page
        child.append(-1)  # Still a usable private orphan, not published authority.
        assert child[-1] == -1


@pytest.mark.parametrize('size', [1000, 10000])
def test_world_old_reader_blocks_then_background_slices_finish_on_real_saves(tmp_path, size):
    target = converted_catalog(tmp_path, size)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        old = session.store.capture_pin()
        old_alias = LazyHistoryList(session.store, old, inc)
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        del child
        gc.collect()
        session.world.year += 1
        with pytest.raises(GenerationPressureError):
            session.save()
        assert session.store.contains_lazy_key(session.pin, DESCRIPTOR_NAMESPACE, inc)
        assert old_alias[-1] == size - 1
        session.store.release_pin(old)
        commit, batches = session.store.commit, []
        def record(*args, **kwargs):
            assert kwargs['cleanup_budget'] == 128
            batches.append(tuple(c for c in kwargs['version_changes'] if c.namespace in
                (NAMESPACE, DEPENDENCIES, PAGE_NAMESPACE, DESCRIPTOR_NAMESPACE)))
            return commit(*args, **kwargs)
        session.store.commit = record
        for _ in range(12):
            session.world.year += 1
            before = session.store.diagnostics().maintenance_removed_rows
            session.save()
            assert len(batches[-1]) <= 128
            assert len(batches[-1]) + session.store.diagnostics().maintenance_removed_rows - before <= 256
            if not pending_retirement(session.store, session.pin, inc):
                break
        else:
            pytest.fail('World retirement failed to make bounded progress')
        assert not session.store.contains_lazy_key(session.pin, DESCRIPTOR_NAMESPACE, inc)
        assert not session.store.contains_lazy_key(session.pin, DEPENDENCIES, inc)
        assert session.store.namespace_size(session.pin, PAGE_NAMESPACE) == 0


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_world_retirement_enqueue_joins_exact_rollback_and_lost_ack(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        def fail(at):
            if at == phase:
                raise OSError('retirement enqueue fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='retirement enqueue fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert pending_retirement(session.store, session.pin, inc)
        assert session._backing_dependencies.pin == session.pin


def test_world_revival_then_final_removal_requeues_before_background_cancellation(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        assert pending_retirement(session.store, session.pin, inc)
        session.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=child)
        session.save()
        del session.skills[3, 'craft']
        session.save()
        assert pending_retirement(session.store, session.pin, inc)
        child.append(-1)
        session.skills[4, 'craft'] = SkillHistory(4, 'craft', provenance=child)
        session.save()
        session.world.year += 1
        session.save()
        assert not pending_retirement(session.store, session.pin, inc)
        assert session.skills[4, 'craft'].provenance is child and child[-1] == -1


def test_world_many_foreground_removals_do_not_impose_background_budget_on_user_edits(tmp_path):
    target = converted_catalog(tmp_path, 1, owners=260)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        for key in range(1, 261):
            del session.skills[key, 'craft']
        session.save()
        assert len(session.skills) == 0
        assert session.store.namespace_size(session.pin, NAMESPACE) > 256


@pytest.mark.parametrize('namespace', [DEPENDENCIES, DESCRIPTOR_NAMESPACE])
def test_world_cold_last_owner_rejects_missing_backing_authority_before_freeze(tmp_path, namespace):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?',
            (namespace, session.store.codec.encode(inc)))
        session.store.db.commit()
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        head = session.pin.captured_head
        with pytest.raises(StoreIntegrityError):
            session.save()
        assert session.pin.captured_head == session.store.generation == head
        assert session._backing_dependencies._prepared is None
        assert session._identity_coordinator._prepared is None
