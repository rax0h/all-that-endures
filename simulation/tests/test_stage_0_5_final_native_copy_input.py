"""Explicit legacy input copy borrows ordinary admission, never source mutation."""
import pytest
from ate_sim.core import Event, Layer
from ate_sim.persistence_tracking import TrackedDict
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap
from ate_sim.incremental_store import CodecError, StoreError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import (
    converted_catalog, open_bridge, activate, RULES,
)


def test_real_tracked_log_event_copy_admits_and_reopens_without_changing_source(tmp_path):
    def configure(world, _history):
        world.events.append(Event(1, 0, 'legacy', Layer.SOCIETY, data={'items': [1]}))
        world.event_ids.add(1)
        world.next_event = 2
    target = converted_catalog(tmp_path, configure_world=configure)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        original = session.world.events[0]
        data = original.data
        assert type(data) is TrackedDict
        copied = session._recursive_histories.copy_input([original, original])
        assert copied[0] is copied[1] and copied[0] is not original
        assert copied[0].data is not data and original.data is data
        session.skills[1, 'craft'].provenance = copied
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1] and type(root[0].data) is LazyHistoryMap
        root[0].data['items'].append(2)
        assert original.data['items'] == [1]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1] and list(root[0].data['items']) == [1, 2]
        assert session.world.events[0].data['items'] == [1]


def test_record_table_copy_keeps_internal_sharing_and_leaves_source_indexes_bound(tmp_path):
    from ate_sim.record_index import RecordTable
    from ate_sim.skills import SkillHistory
    target = converted_catalog(tmp_path)
    shared = [3]
    record = SkillHistory(7, 'alchemy', teachers=shared, provenance=shared)
    source = RecordTable({7: record})
    assert source.select('domain', 'alchemy') == [record]
    indexes, binding = source._indexes, record._index_table
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        copied = session._recursive_histories.copy_input([source, record, shared])
        assert type(copied[0]) is dict and copied[0][7] is copied[1]
        assert copied[1] is not record
        assert copied[1].teachers is copied[1].provenance is copied[2]
        assert '_index_table' not in vars(copied[1])
        assert source._indexes is indexes and record._index_table is binding and binding() is source
        session.skills[1, 'craft'].provenance = copied
        root = session.skills[1, 'craft'].provenance
        assert root[0][7] is root[1] and root[1].teachers is root[2]
        root[1].teachers.append(4)
        assert shared == [3]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0][7] is root[1] and root[1].teachers is root[2]
        assert list(root[2]) == [3, 4]


def test_copy_already_backed_records_and_histories_produces_portable_values(tmp_path):
    from ate_sim.skills import SkillHistory
    from ate_sim.core import Household
    from ate_sim.persistence_lazy_sequence import LazyOrderedSequence
    def configure(world, _history): world.households[1] = Household(1, 1, members=[1, 2])
    target = converted_catalog(tmp_path, configure_world=configure, counted_households=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        record = SkillHistory(7, 'alchemy', teachers=[3])
        session.skills[1, 'craft'].provenance = [record]
        session.save()
        inc = session._registry.incarnation_for_object(record)
        counted = session.world.households[1].members
        assert type(counted) is LazyOrderedSequence
        copied = session._recursive_histories.copy_input([record, record.teachers, counted, counted])
        assert copied[0] is not record and copied[0].teachers is copied[1]
        assert type(copied[1]) is list and type(copied[2]) is list and copied[2] is copied[3]
        assert copied[2] == [1, 2]
        assert session._registry.incarnation_for_object(record) == inc
        copied[1].append(9)
        assert list(record.teachers) == [3]


@pytest.mark.parametrize('state', [None, False, True])
def test_copy_preserves_exact_event_seal_presence_and_readonly_container_roles(tmp_path, state):
    from ate_sim.event_log import FrozenDict, FrozenList
    target = converted_catalog(tmp_path)
    event = Event(17, 2, 'memory', Layer.SOCIETY, data={'items': [1]})
    if state is not None:
        if state: event.seal()
        else: object.__setattr__(event, '_sealed', False)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        copied = session._recursive_histories.copy_input(event)
        assert copied is not event
        assert ('_sealed' in vars(copied)) is (state is not None)
        if state is not None: assert vars(copied)['_sealed'] is state
        assert type(copied.data) is (FrozenDict if state else dict)
        assert type(copied.data['items']) is (FrozenList if state else list)
        session.skills[1, 'craft'].provenance = [copied]
        session.save()


@pytest.mark.parametrize('kind', ['cycle', 'unknown', 'subclass', 'record-state', 'snapshot-state'])
def test_copy_invalid_input_preserves_destination_allocator_and_recovers_guard(tmp_path, kind):
    from ate_sim.skills import SkillHistory
    from ate_sim.event_log import FrozenList
    target = converted_catalog(tmp_path)
    if kind == 'cycle':
        bad = []; bad.append(bad)
    elif kind == 'unknown': bad = object()
    elif kind == 'subclass':
        class Unsupported(list): pass
        bad = Unsupported([1])
    elif kind == 'record-state':
        bad = SkillHistory(7, 'alchemy'); bad.undeclared = 3
    else:
        bad = FrozenList([1]); bad.undeclared = 3
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        before = session._registry.next_incarnation
        original = session.skills[1, 'craft'].provenance
        with pytest.raises((TypeError, ValueError, CodecError)):
            session._recursive_histories.copy_input([[1], bad])
        assert session._registry.next_incarnation == before
        assert session.skills[1, 'craft'].provenance is original
        assert session._lifecycle_operation is None
        assert session._recursive_histories.copy_input([1]) == [1]


@pytest.mark.parametrize('name', ['TrackedDict', 'TrackedList', 'TrackedSet',
    '_RootDict', '_RootList', '_RootSet', '_RootRecordTable'])
def test_known_tracking_container_classes_normalize_without_source_writes(tmp_path, name):
    from ate_sim import persistence_tracking as tracking
    target = converted_catalog(tmp_path)
    cls = getattr(tracking, name)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        source = cls.__new__(cls)
        if issubclass(cls, dict):
            dict.__init__(source, {'value': [1]})
            expected, output_cls = {'value': [1]}, dict
        elif issubclass(cls, list):
            list.__init__(source, [1, 2]); expected, output_cls = [1, 2], list
        else:
            set.__init__(source, {1, 2}); expected, output_cls = {1, 2}, set
        if name == '_RootList':
            source._setup(session._eager_tracker, 'world.test-copy')
        elif name.startswith('_Root'):
            source._setup(session._eager_tracker, 'world.test-copy', name, {})
        else: source._setup(session._eager_tracker, ())
        original_state = dict(vars(source))
        copied = session._recursive_histories.copy_input([source, source])
        assert type(copied[0]) is output_cls and copied[0] == expected
        assert copied[0] is copied[1] and copied[0] is not source
        assert vars(source) == original_state


def test_copy_default_native_world_and_indexed_state_uses_actual_declared_fields(tmp_path):
    from ate_sim.core import World
    from ate_sim.record_index import indexed
    from ate_sim.skills import SkillHistory
    target = converted_catalog(tmp_path)
    world = World(17)
    shared = [1]
    indexed(world.skills, 'skills')[7, 'alchemy'] = SkillHistory(7, 'alchemy',
        teachers=shared, provenance=shared)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        copied = session._recursive_histories.copy_input(world)
        assert type(copied) is World and copied is not world and copied.seed == 17
        assert type(copied.skills.skills) is dict
        record = copied.skills.skills[7, 'alchemy']
        assert record.teachers is record.provenance and record.teachers is not shared
        session.skills[1, 'craft'].provenance = [copied]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        copied = session.skills[1, 'craft'].provenance[0]
        assert type(copied) is World and copied.seed == 17
        record = copied.skills.skills[7, 'alchemy']
        assert record.teachers is record.provenance and list(record.teachers) == [1]


def test_copy_blocks_mutating_read_callback_and_clears_lifecycle_guard(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        source = TrackedDict(value=1)
        source._setup(session._eager_tracker, ())
        def mutate():
            session.world.year += 1
            return dict.items(source)
        source.items = mutate
        before = session.world.year, session._registry.next_incarnation
        with pytest.raises(StoreError, match='copy-history-input'):
            session._recursive_histories.copy_input(source)
        assert (session.world.year, session._registry.next_incarnation) == before
        assert session._lifecycle_operation is None
        session.world.year += 1


def test_copy_closed_source_or_destination_rejects_explicitly(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        backed = session.skills[1, 'craft'].provenance
        runtime = session._recursive_histories
    with pytest.raises(StoreError, match='closed'): runtime.copy_input([1])
    other = tmp_path / 'other'; other.mkdir()
    second = converted_catalog(other)
    with open_bridge(second, rules_id=RULES) as session:
        activate(session)
        with pytest.raises(StoreError, match='closed'):
            session._recursive_histories.copy_input(backed)
        assert session._lifecycle_operation is None


def test_copy_requires_same_publisher_for_live_bound_sources(tmp_path):
    first = converted_catalog(tmp_path)
    directory = tmp_path / 'second'; directory.mkdir()
    second = converted_catalog(directory)
    with open_bridge(first, rules_id=RULES) as source, open_bridge(second, rules_id=RULES) as target:
        activate(source); activate(target)
        alias = source.skills[1, 'craft'].provenance
        with pytest.raises(StoreError, match='cross-session'):
            target._recursive_histories.copy_input(alias)
        assert target._lifecycle_operation is None
        assert list(alias) == list(range(32))


def test_copy_backed_frozen_snapshot_materializes_native_readonly_values(tmp_path):
    from ate_sim.event_log import FrozenDict, FrozenList
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = Event(17, 2, 'memory', Layer.SOCIETY, data={'values': [1]})
        session.skills[1, 'craft'].provenance = [event]
        event.seal(); session.save()
        copied = session._recursive_histories.copy_input([event.data, event.data])
        assert copied[0] is copied[1] and type(copied[0]) is FrozenDict
        assert type(copied[0]['values']) is FrozenList
        with pytest.raises(TypeError): copied[0]['values'].append(2)


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_copied_input_save_fault_keeps_native_source_and_resolves_existing_plan(tmp_path, phase):
    from ate_sim.skills import SkillHistory
    from ate_sim.record_index import RecordTable
    target = converted_catalog(tmp_path)
    record = SkillHistory(7, 'alchemy', provenance=[3])
    source = RecordTable({7: record})
    index = record._index_table
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        copied = session._recursive_histories.copy_input([source, record])
        session.skills[1, 'craft'].provenance = copied
        def fail(at):
            if at == phase: raise OSError('copied input save fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='copied input save fault'): session.save()
        assert record._index_table is index and index() is source and record.provenance == [3]
        with pytest.raises(StoreError): session._recursive_histories.copy_input(source)
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit': session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0][7] is root[1] and list(root[1].provenance) == [3]
