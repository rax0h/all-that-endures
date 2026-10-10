"""World dependency wiring borrows the publisher pin and freezes with its save."""
import gc
import weakref

import pytest

from ate_sim.incremental_store import StoreError, StoreIntegrityError, StoreConflictError
from ate_sim.skills import SkillHistory
from ate_sim.persistence_history_dependencies import NAMESPACE, active_backing_dependencies, dependency_value
from ate_sim.persistence_lazy_nested_history import LazyHistoryList
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


@pytest.mark.parametrize('size', [1000, 10000])
def test_world_retained_orphan_survives_unrelated_saves_on_one_publisher_pin(tmp_path, size):
    target = converted_catalog(tmp_path, size)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc = child._incarnation
        child.append(size)
        session.save()
        pool = session._backing_dependencies
        assert active_backing_dependencies(session.store, session.pin, inc) == (session.pin.token,)
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        child.append(-1)  # Private after the final current placement disappears.
        session.save()
        for number in range(12):
            session.world.year += 1
            session.save()
            assert pool.pin == child._pin == session.pin
            assert session.store.db.execute('SELECT COUNT(*) FROM generation_pins').fetchone()[0] == 1
            assert child[-1] == -1 and child[-2] == size
            assert active_backing_dependencies(session.store, session.pin, inc) == (session.pin.token,)
        persisted = LazyHistoryList(session.store, session.pin, inc)
        assert persisted[-1] == size  # Unowned private edit was not written.
        session.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=child)
        session.save()
        assert session.skills[3, 'craft'].provenance is child and child[-1] == -1
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[3, 'craft'].provenance[-2:] == [size, -1]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_world_dependency_fault_retains_the_exact_joint_plan(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        def fail(at):
            if at == phase:
                raise OSError('joint dependency fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='joint dependency fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            assert session._backing_dependencies._prepared is None
            child.append(100)
            session.save()
        assert session._backing_dependencies.pin == session.pin
        assert active_backing_dependencies(session.store, session.pin, child._incarnation) == (session.pin.token,)


def test_world_missing_mandatory_dependency_rejects_save_without_dropping_edit(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        key = session.store.codec.encode(child._incarnation)
        session.store.db.execute('DELETE FROM lazy_record_versions WHERE namespace=? AND typed_key=?', (NAMESPACE, key))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.save()
        assert child[-1] == 99 and session._backing_dependencies._prepared is None


def test_world_read_only_acquisition_does_not_create_a_generation(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        generation = session.pin.captured_head
        assert session._backing_dependencies.diagnostics()['dependencies'] >= 1
        assert session.save() == generation
        assert session.store.read_version(session.pin, NAMESPACE, child._incarnation,
            expected_record_schema=1).value == dependency_value('list')
        assert session._backing_dependencies._prepared is None


def test_world_weak_alias_collection_defers_dependency_release_to_real_save(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        inc, ref = child._incarnation, weakref.ref(child)
        del session.skills[1, 'craft']
        del session.skills[2, 'craft']
        session.save()
        assert active_backing_dependencies(session.store, session.pin, inc) == (session.pin.token,)
        del child
        before = session.store.diagnostics()
        gc.collect()
        assert ref() is None and inc not in session._backing_dependencies._aliases
        assert session.store.diagnostics().payload_reads == before.payload_reads
        assert session.store.diagnostics().payload_writes == before.payload_writes
        generation = session.pin.captured_head
        assert session.save() == generation
        assert active_backing_dependencies(session.store, session.pin, inc) == (session.pin.token,)
        session.world.year += 1
        session.save()
        assert active_backing_dependencies(session.store, session.pin, inc) == ()


def test_world_new_history_creates_dependency_authority_in_same_save(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[3, 'craft'] = SkillHistory(3, 'craft', provenance=[5, 6])
        child = session.skills[3, 'craft'].provenance
        assert child._new
        session.save()
        assert not child._new
        assert active_backing_dependencies(session.store, session.pin, child._incarnation) == (session.pin.token,)


def test_world_losing_writer_can_close_without_thawing_stale_plan(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session, open_bridge(target, rules_id=RULES) as peer:
        activate(session)
        activate(peer)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        commit = session.store.commit
        def lose_race(*args, **kwargs):
            peer.world.year += 1
            peer.save()
            return commit(*args, **kwargs)
        session.store.commit = lose_race
        with pytest.raises(StoreConflictError):
            session.save()
        assert session._state == 'stale' and session._backing_dependencies._prepared is not None
        frozen = session._backing_dependencies._prepared
        def fail_release(phase):
            if phase == 'before_pin_release_commit':
                raise OSError('stale release fault')
        session.store._phase_hook = fail_release
        with pytest.raises(OSError, match='stale release fault'):
            session.close()
        assert session._active and session._backing_dependencies._prepared is frozen
        session.store._phase_hook = lambda _: None
        session.close()
        assert session._backing_dependencies.closed
        assert session.pin.token not in [row[0] for row in peer.store.db.execute('SELECT token FROM generation_pins')]


@pytest.mark.parametrize('operation', ['close', 'detach'])
def test_world_failed_publisher_release_preserves_dependency_and_usable_session(tmp_path, operation):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        session.save()
        pool = session._backing_dependencies
        def fail(at):
            if at == 'before_pin_release_commit':
                raise OSError('dependency release fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='dependency release fault'):
            session.close() if operation == 'close' else session.detach(materialize_history=True)
        session.store._phase_hook = lambda _: None
        assert session._active and not pool.closed and session._lifecycle_operation is None
        child.append(100)
        session.save()
        assert active_backing_dependencies(session.store, session.pin, child._incarnation) == (session.pin.token,)
        if operation == 'detach':
            world = session.detach(materialize_history=True)
            assert world.skills.skills[1, 'craft'].provenance is world.skills.skills[2, 'craft'].provenance
        else:
            session.close()
        assert pool.closed and not pool._aliases
        with pytest.raises(StoreError):
            child.append(101)
