"""Recursive mutable descendants use physical owners and one World publisher."""
import pytest

from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.persistence_lazy_nested_history import LazyHistoryList, LazyHistoryMap, PAGE_NAMESPACE, ENTRY_NAMESPACE
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def test_recursive_list_map_and_tuple_preserve_shared_child_after_reopen(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [3]
        session.skills[1, 'craft'].provenance = [shared, {'notes': shared}, (shared,)]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        assert type(child) is LazyHistoryList
        assert type(root[1]) is LazyHistoryMap
        assert root[1]['notes'] is root[2][0] is child
        child.append(9)
        session.save()
        assert list(child) == [3, 9]
        assert session.save() == session.pin.captured_head
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['notes'] is root[2][0]
        root[0].append(11)
        session.save()
        assert list(root[2][0]) == [3, 9, 11]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_recursive_children_share_the_world_fault_recovery_plan(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [[4]]
        child = session.skills[1, 'craft'].provenance[0]
        def fault(at):
            if at == phase:
                raise OSError('recursive fault')
        session.store._phase_hook = fault
        with pytest.raises(OSError, match='recursive fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert session.skills[1, 'craft'].provenance[0] is child
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert list(session.skills[1, 'craft'].provenance[0]) == [4]


def test_pending_child_replacement_wins_over_retained_alias(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared, {'notes': shared}]
        root = session.skills[1, 'craft'].provenance
        old = root[0]
        session.save()
        root[0] = [2]
        old.append(8)
        assert list(root[0]) == [2]
        assert root[1]['notes'] is old
        session.save()
        group = coord.catalog.read_identity_group(session.pin, old._incarnation)
        assert len(group.occurrences) == 1 and group.occurrences[0][0] == ENTRY_NAMESPACE
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert list(root[0]) == [2] and list(root[1]['notes']) == [1, 8]


def test_missing_recursive_occurrence_rejects_before_value_edit(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared, (shared,)]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        session.save()
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND occurrence_path=?',
            (PAGE_NAMESPACE, session.store.codec.encode((('index', 1), ('index', 0)))))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            child.append(9)
        assert list(child) == [1]


def test_recursive_value_routing_is_independent_of_unrelated_history(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = converted_catalog(directory, size=size, owners=24)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            shared = [1]
            session.skills[1, 'craft'].provenance = [shared, {'notes': shared}]
            root = session.skills[1, 'craft'].provenance
            child = root[0]
            retained_other = session.skills[2, 'craft'].provenance
            session.save()
            retained_other._read_page = lambda *_: pytest.fail('recursive edit read unrelated history')
            session._registry.live_bindings = lambda: pytest.fail('recursive edit searched global registry')
            session.store.reset_diagnostics()
            child.append(8)
            session.save()
            assert root[1]['notes'] is child
            before_noop = session.store.diagnostics()
            session.save()
            assert session.store.diagnostics().payload_writes == before_noop.payload_writes
            metrics.append(session.store.diagnostics())
            record_property(f'H{size}_payload_reads', metrics[-1].payload_reads)
            record_property(f'H{size}_payload_writes', metrics[-1].payload_writes)
            record_property(f'H{size}_metadata_rows', metrics[-1].metadata_rows)
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].payload_writes == metrics[1].payload_writes
    assert metrics[0].metadata_rows == metrics[1].metadata_rows


def test_recursive_descendants_survive_counted_admission_and_leaf_split(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_unpublished_promotion import counted_catalog
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared] * 128
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        session.world.households[1].members = root
        root.insert(64, child)
        assert len(root) == 129 and root[64] is child
        child.append(2)
        session.save()
        assert session.world.households[1].members is root
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.world.households[1].members
        assert root is session.skills[1, 'craft'].provenance
        assert root[0] is root[64] is root[-1] and list(root[64]) == [1, 2]


def test_recursive_retirement_removes_physical_placements_and_protects_old_pin(tmp_path):
    import gc
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.skills[1, 'craft'].provenance = [[1]]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        parent_inc, child_inc = root._incarnation, child._incarnation
        session.save()
        old = session.store.capture_pin()
        session.skills[1, 'craft'].provenance = []
        session.save()
        assert len(LazyHistoryList(session.store, old, parent_inc, recursive=True)) == 1
        session.store.release_pin(old)
        del root
        gc.collect()
        for number in range(12):
            session.skills[1, 'craft'].level = number + 1
            session.save()
        for number in range(12, 24):
            session.skills[1, 'craft'].level = number + 1
            session.save()
        group = coord.catalog.read_identity_group(session.pin, child_inc)
        assert not group.occurrences
        child.append(2)
        session.save()
        assert list(child) == [1, 2]


def test_recursive_detach_materializes_one_shared_native_graph(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared, {'notes': shared}, (shared,)]
        world = session.detach(materialize_history=True)
        root = world.skills.skills[1, 'craft'].provenance
        assert type(root) is list and type(root[0]) is list and type(root[1]) is dict
        assert root[0] is root[1]['notes'] is root[2][0]
        root[0].append(2)
        assert root[2][0] == [1, 2]


def test_cyclic_recursive_assignment_leaves_the_owner_and_journals_unchanged(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = session.skills[1, 'craft']
        original = record.provenance
        value = []
        value.append(value)
        before = session._registry.next_incarnation
        with pytest.raises(TypeError, match='cyclic'):
            record.provenance = value
        assert record.provenance is original
        assert not session._nested_dirty and session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head


@pytest.mark.parametrize('container', ['list', 'map'])
def test_parent_member_edit_checks_its_existing_child_group_before_changing_value(tmp_path, container):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared, {'notes': shared}]
        root = session.skills[1, 'craft'].provenance
        nested_map = root[1]
        session.save()
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?', (ENTRY_NAMESPACE,))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            root.append(3) if container == 'list' else nested_map.__setitem__('notes', [2])
        assert len(root) == 2
        assert not root._dirty_pages and not nested_map._dirty_entries


def test_counted_position_edit_checks_child_groups_before_rebalancing(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_unpublished_promotion import counted_catalog
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        session.skills[1, 'craft'].provenance = [shared, {'notes': shared}]
        root = session.skills[1, 'craft'].provenance
        session.world.households[1].members = root
        session.save()
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=?', (ENTRY_NAMESPACE,))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            root.insert(0, 5)
        assert len(root) == 2 and not root._dirty


def test_stale_recursive_session_can_read_pinned_children_but_cannot_edit(tmp_path):
    from ate_sim.incremental_store import StoreConflictError
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [[1]]
        session.save()
        root = session.skills[1, 'craft'].provenance
        session._state = 'stale'
        assert list(root[0]) == [1]
        with pytest.raises(StoreConflictError):
            root[0].append(2)


def test_cyclic_soul_assignment_is_rejected_before_owner_edit(tmp_path):
    from ate_sim.metaphysics import SoulState
    def configure(world, _history):
        world.metaphysics.souls[1] = SoulState(1)
    target = converted_catalog(tmp_path, configure_world=configure)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        soul = session.world.metaphysics.souls[1]
        original = soul.transformations
        cycle = []
        cycle.append(cycle)
        before = session._registry.next_incarnation
        with pytest.raises(TypeError, match='cyclic'):
            soul.transformations = cycle
        assert soul.transformations is original
        assert session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head


@pytest.mark.parametrize('kind', ['list', 'map', 'sequence'])
def test_new_scalar_physical_owner_can_gain_recursive_members_after_save(tmp_path, kind):
    from simulation.tests.test_stage_0_5_final_world_unpublished_promotion import counted_catalog
    target = counted_catalog(tmp_path) if kind == 'sequence' else converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [{'notes': 1}] if kind == 'map' else [1]
        root = session.skills[1, 'craft'].provenance
        if kind == 'sequence':
            session.world.households[1].members = root
        session.save()
        if kind == 'map':
            root[0]['notes'] = [2]
        else:
            root.append([2])
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert list(root[0]['notes'] if kind == 'map' else root[-1]) == [2]


@pytest.mark.parametrize('pending', [False, True])
def test_counted_recursive_bulk_failure_restores_placement_and_value_journals(tmp_path, pending):
    from simulation.tests.test_stage_0_5_final_world_unpublished_promotion import counted_catalog
    target = counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.skills[1, 'craft'].provenance = [[1]]
        root = session.skills[1, 'craft'].provenance
        child = root[0]
        session.world.households[1].members = root
        session.save()
        if pending:
            root.append(child)
            session._identity_bridge.synchronize_lazy_placements()
        before = dict(coord.placement_overlay)
        before_values = list(root)
        before_dirty = dict(root._dirty)
        with pytest.raises(TypeError):
            root.extend([child, child, object()])
        assert list(root) == before_values and root._dirty == before_dirty
        assert coord.placement_overlay == before
        session.save()
        assert session.save() == session.pin.captured_head
        root.extend([child, child])
        session.save()
        assert len(root) == len(before_values) + 2 and root[-1] is child
