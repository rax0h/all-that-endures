"""Native record identity through the existing recursive World publisher."""
import pytest

from ate_sim.agency import ActionRecord
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy_nested_history import LazyHistoryList
from ate_sim.incremental_store import StoreError, StoreIntegrityError, StoreConflictError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    converted_catalog, open_bridge, activate, RULES,
)


def test_native_record_shared_by_recursive_owners_mutates_and_reopens(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record, {'record': record}, (record,)]
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1]['record'] is root[2][0] is record
        inc = session._registry.incarnation_for_object(record)
        assert session._registry.object_for_incarnation(inc) is record
        record.strength = .75
        session.save()
        assert session.save() == session.pin.captured_head
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        record = root[0]
        assert type(record) is ActionRecord
        assert root[1]['record'] is root[2][0] is record
        assert record.strength == .75
        record.strength = .9
        session.save()


def test_native_record_children_share_histories_and_replacement_preserves_old_alias(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [3]
        record = SkillHistory(7, 'alchemy', teachers=shared, provenance=shared)
        session.skills[1, 'craft'].provenance = [record, shared]
        root = session.skills[1, 'craft'].provenance
        assert root[0] is record
        assert type(record.teachers) is LazyHistoryList
        assert record.teachers is record.provenance is root[1]
        session.save()
        old = record.provenance
        record.provenance = [9]
        old.append(4)
        session.save()
        assert list(record.provenance) == [9] and list(record.teachers) == [3, 4]
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        record = root[0]
        assert type(record) is SkillHistory
        assert record.teachers is root[1]
        assert list(record.teachers) == [3, 4] and list(record.provenance) == [9]


def test_record_graph_preflight_rejects_cycle_before_allocating_earlier_children(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        before = session._registry.next_incarnation
        record = SkillHistory(7, 'alchemy', teachers=[1])
        record.provenance = [record]
        root = session.skills[1, 'craft'].provenance
        with pytest.raises(TypeError, match='cyclic'):
            root.append(record)
        assert session._registry.next_incarnation == before
        assert record.teachers == [1]


def test_record_assignment_preflights_invalid_graph_and_closed_alias_rejects(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = SkillHistory(7, 'alchemy')
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        old = record.provenance
        before = session._registry.next_incarnation
        with pytest.raises(TypeError):
            record.provenance = [[1], object()]
        assert record.provenance is old
        assert session._registry.next_incarnation == before
    with pytest.raises(StoreError, match='closed'):
        record.level = .9


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_record_save_fault_preserves_exact_frozen_world_plan(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = SkillHistory(7, 'alchemy', provenance=[3])
        session.skills[1, 'craft'].provenance = [record]
        def fail(at):
            if at == phase:
                raise OSError('record save fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='record save fault'):
            session.save()
        with pytest.raises(StoreError):
            record.level = .9
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            record.level = .9
            session.save()
        assert session.skills[1, 'craft'].provenance[0] is record
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert list(session.skills[1, 'craft'].provenance[0].provenance) == [3]


def test_held_orphan_record_keeps_private_edit_and_revives_same_incarnation(tmp_path):
    from ate_sim.persistence_record_headers import read_record_header, restore_record_header
    from ate_sim.persistence_history_dependencies import active_backing_dependencies
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        inc = session._registry.incarnation_for_object(record)
        session.skills[1, 'craft'].provenance.clear()
        record.strength = .9
        session.save()
        assert restore_record_header(read_record_header(session.store, session.pin, inc.value)).strength == .5
        for _ in range(3):
            session.world.year += 1
            session.save()
            assert active_backing_dependencies(session.store, session.pin, inc.value) == (session.pin.token,)
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        assert session._registry.incarnation_for_object(record) == inc
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.skills[1, 'craft'].provenance[0].strength == .9


def test_clean_record_body_and_binding_are_weak_after_parent_cache_releases(tmp_path):
    import gc
    import weakref
    from ate_sim.persistence_tracking import _BINDINGS
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        root = session.skills[1, 'craft'].provenance
        session.save()
        ident, ref = id(record), weakref.ref(record)
        del record
        root._clear_cache()
        gc.collect()
        assert ref() is None and ident not in _BINDINGS
        assert type(root[0]) is ActionRecord


def test_record_corrupt_physical_placement_rejects_before_native_field_edit(tmp_path):
    from ate_sim.persistence_lazy_nested_history import PAGE_NAMESPACE
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record, record]
        session.save()
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? AND occurrence_path=?',
            (PAGE_NAMESPACE, session.store.codec.encode((('index', 1),))))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            record.strength = .9
        assert record.strength == .5


def test_record_detach_materializes_one_plain_shared_native_graph(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [3]
        record = SkillHistory(7, 'alchemy', teachers=shared, provenance=shared)
        session.skills[1, 'craft'].provenance = [record, record, shared]
        plain = session.detach(materialize_history=True)
    root = plain.skills.skills[1, 'craft'].provenance
    assert root[0] is root[1]
    assert root[0].teachers is root[0].provenance is root[2]
    assert type(root[0]) is SkillHistory and type(root[0].teachers) is list
    root[0].level = .9


def test_record_shared_with_existing_eager_packed_action_is_one_native_object(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_packed_actions import catalog_with_actions
    target = catalog_with_actions(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        action = session.world.agency.actions[0]
        inc = session._registry.incarnation_for_object(action)
        session.skills[1, 'craft'].provenance = [action]
        assert session.skills[1, 'craft'].provenance[0] is action
        assert session._registry.incarnation_for_object(action) == inc
        action.strength = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = session.skills[1, 'craft'].provenance[0]
        assert record.strength == .9
        record.strength = .8
        assert session.world.agency.actions[0] is record
        session.save()


def test_record_last_physical_owner_retirement_preserves_old_pin_and_reclaims_children(tmp_path):
    import gc
    import weakref
    from ate_sim.persistence_record_headers import read_record_header, NAMESPACE
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        record = SkillHistory(7, 'alchemy', teachers=[3], provenance=[4])
        session.skills[1, 'craft'].provenance = [record]
        root = session.skills[1, 'craft'].provenance
        session.save()
        inc = session._registry.incarnation_for_object(record).value
        child_inc = record.provenance._incarnation
        old = session.store.capture_pin()
        ref = weakref.ref(record)
        root.clear()
        session.save()
        assert not coord.catalog.read_identity_group(session.pin, inc).occurrences
        del record
        gc.collect()
        assert ref() is None
        assert read_record_header(session.store, old, inc)[2][0] == 7
        session.store.release_pin(old)
        for number in range(24):
            session.world.year += 1
            session.save()
        assert not session.store.contains_lazy_key(session.pin, NAMESPACE, (inc, 0))
        assert not coord.catalog.read_identity_group(session.pin, child_inc).occurrences


def test_record_stale_session_reads_pinned_body_but_rejects_mutation_and_cross_session(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as initial:
        activate(initial)
        initial.skills[1, 'craft'].provenance = [ActionRecord(1, 2, 'work', 'wealth', .5)]
        initial.save()
    with open_bridge(target, rules_id=RULES) as session, open_bridge(target, rules_id=RULES) as peer:
        activate(session)
        activate(peer)
        record = session.skills[1, 'craft'].provenance[0]
        before = peer._registry.next_incarnation
        with pytest.raises(StoreError, match='cross-session'):
            peer.skills[1, 'craft'].provenance = [record]
        assert peer._registry.next_incarnation == before
        peer.world.year += 1
        peer.save()
        with pytest.raises(StoreConflictError):
            session.save()
        assert record.strength == .5
        with pytest.raises(StoreError):
            record.strength = .9
        assert record.strength == .5


def test_record_point_edit_save_and_noop_are_independent_of_unrelated_history(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = converted_catalog(directory, size=size, owners=24)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            record = SkillHistory(7, 'alchemy', provenance=[3])
            session.skills[1, 'craft'].provenance = [record, {'record': record}]
            root = session.skills[1, 'craft'].provenance
            # Hold the same related owner aliases at both scales. A temporary
            # map alias could otherwise be collected during one measured save
            # and change dependency-pruning work independently of history size.
            related_map = root[1]
            unrelated = session.skills[2, 'craft'].provenance
            session.save()
            session._registry.live_bindings = lambda: pytest.fail('record edit searched global registry')
            unrelated._read_page = lambda *_: pytest.fail('record edit read unrelated history')
            session.store.reset_diagnostics()
            record.level = .9
            session.save()
            assert root[0] is related_map['record'] is record
            before = session.store.diagnostics()
            session.save()
            now = session.store.diagnostics()
            assert now.payload_writes == before.payload_writes
            metrics.append((now.payload_reads, now.payload_writes, now.metadata_rows))
            for label, count in zip(('payload_reads', 'payload_writes', 'metadata_rows'), metrics[-1]):
                record_property(f'H{size}_{label}', count)
    assert metrics[0] == metrics[1]


def test_native_record_can_contain_shared_native_record_child_and_replace_it(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        child = ActionRecord(1, 2, 'work', 'wealth', .5)
        parent = ActionRecord(1, 3, 'observe', child, .6)
        session.skills[1, 'craft'].provenance = [parent, child]
        root = session.skills[1, 'craft'].provenance
        assert parent.motive is child is root[1]
        session.save()
        parent.motive = ActionRecord(2, 3, 'learn', 'curiosity', .7)
        child.strength = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert type(root[0].motive) is ActionRecord
        assert root[0].motive.action == 'learn' and root[1].strength == .9


@pytest.mark.parametrize('invalid', ['extra', 'missing', 'foreign', 'event'])
def test_native_record_admission_is_closed_and_failed_input_allocates_nothing(tmp_path, invalid):
    from dataclasses import dataclass
    from ate_sim.core import Event, Layer
    @dataclass
    class Foreign:
        year: int
    record = ActionRecord(1, 2, 'work', 'wealth', .5)
    if invalid == 'extra':
        object.__setattr__(record, 'secret', [])
    elif invalid == 'missing':
        del vars(record)['year']
    elif invalid == 'foreign':
        record = Foreign(1)
    else:
        record = Event(1, 0, 'birth', Layer.SOCIETY)
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        before = session._registry.next_incarnation
        with pytest.raises((TypeError, StoreError)):
            root[:] = [[1], record]
        assert session._registry.next_incarnation == before


def test_record_self_assignment_rejects_before_owner_and_allocator_changes(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        before = session._registry.next_incarnation
        with pytest.raises(TypeError, match='cyclic'):
            record.motive = (record,)
        assert record.motive == 'wealth' and session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head


@pytest.mark.parametrize('operation', ['record_field', 'list_append', 'map_set', 'finite_slice'])
def test_existing_canonical_reference_cycle_rejects_without_archive_walk(tmp_path, operation):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = SkillHistory(7, 'alchemy', provenance=[{'child': []}])
        session.skills[1, 'craft'].provenance = [record]
        root = session.skills[1, 'craft'].provenance
        child_map = record.provenance[0]
        child_list = child_map['child']
        session.save()
        before = session._registry.next_incarnation
        record.provenance._read_page = lambda *_: pytest.fail('cycle check walked a history payload')
        with pytest.raises(TypeError, match='cyclic'):
            if operation == 'record_field':
                record.provenance = root
            elif operation == 'list_append':
                child_list.append(record)
            elif operation == 'map_set':
                child_map['record'] = record
            else:
                child_list[:] = [record]
        assert session._registry.next_incarnation == before
        assert session.save() == session.pin.captured_head


def test_unsaved_record_close_does_not_keep_native_body_alive(tmp_path):
    import gc
    import weakref
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        ref = weakref.ref(record)
    del record, session
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize('operation', ['list_slice', 'counted_slice', 'counted_extend'])
def test_finite_record_batches_keep_shared_native_identity_after_reopen(tmp_path, operation):
    from simulation.tests.test_stage_0_5_final_world_unpublished_promotion import counted_catalog
    target = converted_catalog(tmp_path) if operation == 'list_slice' else counted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = []
        root = session.skills[1, 'craft'].provenance
        if operation != 'list_slice':
            session.world.households[1].members = root
            session.world.households[1].members = [1]
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        if operation == 'counted_extend':
            root.extend([record] * 48)
        else:
            root[:] = [record] * 48
        assert root[0] is root[-1] is record
        record.strength = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[-1] and root[0].strength == .9


def test_top_level_lazy_record_peer_keeps_backing_and_family_header_consistent(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        peer = session.skills[2, 'craft']
        inc = session._registry.incarnation_for_object(peer)
        session.skills[1, 'craft'].provenance = [peer]
        assert session.skills[1, 'craft'].provenance[0] is peer
        assert session._registry.incarnation_for_object(peer) == inc
        peer.provenance = [9]
        peer.level = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        record = root[0]
        assert record is session.skills[2, 'craft']
        assert record.level == .9 and list(record.provenance) == [9]


def test_materialized_detach_releases_native_record_that_now_has_only_eager_owner(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_packed_actions import catalog_with_actions
    target = catalog_with_actions(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = session.world.agency.actions[0]
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        session.skills[1, 'craft'].provenance.clear()
        session.save()
        plain = session.detach(materialize_history=True)
    plain.agency.actions[0].strength = .9


def test_native_record_backing_is_rechecked_before_field_edit(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        object.__setattr__(record, 'hidden', [])
        with pytest.raises(StoreError):
            record.strength = .9
        assert record.strength == .5
        del vars(record)['hidden']


def test_cold_lazy_family_first_assignment_updates_its_shared_record_backing(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [session.skills[2, 'craft']]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        # Choose the ordinary lazy family as the first access, before touching
        # the recursive placement which creates the record assignment binding.
        peer = session.skills[2, 'craft']
        peer.level = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        peer = session.skills[1, 'craft'].provenance[0]
        assert peer.level == .9 and session.skills[2, 'craft'] is peer


def test_identical_record_assignment_and_return_to_baseline_are_noop_saves(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = ActionRecord(1, 2, 'work', 'wealth', .5)
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        generation = session.pin.captured_head
        record.strength = .5
        assert session.save() == generation
        record.strength = .9
        record.strength = .5
        assert session.save() == generation
