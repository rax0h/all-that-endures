"""Unpublished append backing can become counted without replacing its alias."""
import pytest

from ate_sim.core import Household, Settlement
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, DESCRIPTOR_NAMESPACE
from ate_sim.persistence_lazy_sequence import LazyOrderedSequence, DESCRIPTOR_NAMESPACE as COUNTED
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def counted_catalog(tmp_path, size=32):
    def configure(world, history):
        world.households[1] = Household(1, 1, members=[1])
        world.settlements[1] = Settlement(1, 0, 0, households=[1])
    return converted_catalog(tmp_path, size=size, owners=1, counted_households=True, configure_world=configure)


@pytest.mark.parametrize('owner', ['household', 'settlement'])
def test_new_shared_append_list_promotes_same_object_and_incarnation(tmp_path, owner):
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.skills[1, 'craft'].provenance = [1, 2, 1]
        child = session.skills[1, 'craft'].provenance
        assert type(child) is LazyHistoryList and child._new
        incarnation = session._registry.incarnation_for_object(child)
        if owner == 'household':
            session.world.households[1].members = child
            assert session.world.households[1].members is child
        else:
            session.world.settlements[1].households = child
            assert session.world.settlements[1].households is child
        assert type(child) is LazyOrderedSequence
        assert session.skills[1, 'craft'].provenance is child
        assert session._registry.incarnation_for_object(child) == incarnation
        child.remove(1.0)
        assert list(child) == [2, 1]
        session.save()
        assert session._backing_dependencies._persisted[incarnation.value] == 'sequence'
        assert not coord.placement_overlay
        with session.store.read_snapshot(session.pin):
            with pytest.raises(KeyError):
                session.store.read_version(session.pin, DESCRIPTOR_NAMESPACE, incarnation.value, expected_record_schema=1)
            session.store.read_version(session.pin, COUNTED, incarnation.value, expected_record_schema=1)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        peer = (session.world.households[1].members if owner == 'household'
                else session.world.settlements[1].households)
        assert peer is child and list(child) == [2, 1]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_new_backing_promotion_is_one_recoverable_publication(tmp_path, phase):
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.skills[1, 'craft'].provenance = [1, 2, 1]
        child = session.skills[1, 'craft'].provenance
        session.world.households[1].members = child
        def fault(at):
            if at == phase:
                raise OSError('promotion fault')
        session.store._phase_hook = fault
        with pytest.raises(OSError, match='promotion fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert session.skills[1, 'craft'].provenance is child
        assert session.world.households[1].members is child
        assert coord.pin == session.pin and not coord.dirty_owners


def test_retained_method_and_weak_alias_survive_unpublished_promotion(tmp_path):
    import weakref
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [1, 2, 1]
        child = session.skills[1, 'craft'].provenance
        weak, append, remove = weakref.ref(child), child.append, child.remove
        session.world.households[1].members = child
        assert weak() is child
        append(3)
        from unittest.mock import patch
        with patch.object(LazyOrderedSequence, 'index', side_effect=AssertionError('old removal scanned history')):
            remove(1.0)
        assert list(child) == [2, 1, 3]
        assert child + [4] == [2, 1, 3, 4]
        assert [0] + child == [0, 2, 1, 3]
        assert 2 * child == [2, 1, 3, 2, 1, 3]
        assert child < [3]
        session.save()


def test_published_append_backing_is_not_scanned_or_replaced_on_admission(tmp_path):
    from ate_sim.incremental_store import StoreError
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = session.skills[1, 'craft'].provenance
        original = session.world.households[1].members
        child._read_page = lambda *_: pytest.fail('admission silently scanned persisted history')
        with pytest.raises(StoreError):
            session.world.households[1].members = child
        assert session.world.households[1].members is original
        assert session.skills[1, 'craft'].provenance is child


def test_unpublished_promotion_work_does_not_visit_replaced_archive(tmp_path):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = counted_catalog(directory, size=size)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            retained_old = session.skills[1, 'craft'].provenance
            # Keep the same explicit U in both fixtures. Otherwise collection
            # timing of the replaced counted proxy changes lease maintenance.
            retained_members = session.world.households[1].members
            retained_old._read_page = lambda *_: pytest.fail('promotion read replaced historical pages')
            session.skills[1, 'craft'].provenance = [1, 2, 1]
            child = session.skills[1, 'craft'].provenance
            session.store.reset_diagnostics()
            session.world.households[1].members = child
            child.remove(1.0)
            session.save()
            assert len(retained_old) == size
            assert list(retained_members) == [1]
            metrics.append(session.store.diagnostics())
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].metadata_rows == metrics[1].metadata_rows
    assert metrics[0].payload_writes == metrics[1].payload_writes
