"""Event bodies remain native; snapshot children use checked readonly histories."""
import pickle
import pytest
from ate_sim.core import Event, Layer, Ref
from ate_sim.event_log import FrozenDict, FrozenList
from ate_sim.agency import ActionRecord
from ate_sim.persistence_lazy_nested_history import LazyFrozenHistoryMap, LazyFrozenHistoryList
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def test_unsealed_event_record_data_aliases_mutate_and_reopen(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        shared = [1]
        event = Event(17, 2, 'memory', Layer.SOCIETY, (Ref('person', 1),), data={'a':shared, 'b':shared})
        session.skills[1, 'craft'].provenance = [event, event]
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1] is event
        event.data['a'].append(2)
        event.kind = 'updated'
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        event = root[0]
        assert type(event) is Event and root[1] is event
        assert event.kind == 'updated' and event.data['a'] is event.data['b']
        assert list(event.data['a']) == [1, 2]
        assert '_sealed' not in vars(event)


@pytest.mark.parametrize('already_sealed', [False, True])
def test_event_seal_copies_mutable_container_aliases_and_persists_immutable_snapshot(tmp_path, already_sealed):
    target = converted_catalog(tmp_path)
    event = Event(17, 2, 'memory', Layer.SOCIETY, data={'values':[1]})
    if already_sealed:
        event.seal()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        session.skills[1, 'craft'].provenance = [event]
        old = event.data
        if not already_sealed:
            event.seal()
            old['values'].append(2)
        assert vars(event)['_sealed'] is True
        assert type(event.data) is LazyFrozenHistoryMap
        assert type(event.data['values']) is LazyFrozenHistoryList
        assert list(event.data['values']) == [1]
        with pytest.raises(TypeError): event.kind = 'edit'
        with pytest.raises(TypeError): event.data['values'].append(3)
        session.save()
        # Pickled pending chunks carry standalone snapshot values, never a
        # store connection or a live backing reference.
        snapshot = pickle.loads(pickle.dumps(event))
        assert type(snapshot.data) is FrozenDict and type(snapshot.data['values']) is FrozenList
        assert snapshot.data['values'] == [1]
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        restored = session.skills[1, 'craft'].provenance[0]
        assert vars(restored)['_sealed'] is True
        with pytest.raises(TypeError): restored.data['values'].clear()
        plain = session.detach(materialize_history=True)
    event = plain.skills.skills[1, 'craft'].provenance[0]
    assert type(event.data) is FrozenDict and vars(event)['_sealed'] is True
    with pytest.raises(TypeError): event.kind = 'edit'


def test_event_freeze_preserves_native_mutable_record_child_behavior(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        action = ActionRecord(1, 2, 'work', 'wealth', .5)
        event = Event(17, 2, 'memory', Layer.SOCIETY, data={'action':action})
        session.skills[1, 'craft'].provenance = [event, action]
        event.seal()
        assert event.data['action'] is action
        action.strength = .9
        session.save()
        assert event.data['action'].strength == .9
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        root = session.skills[1, 'craft'].provenance
        assert root[0].data['action'] is root[1]
        assert root[1].strength == .9


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_event_snapshot_save_fault_preserves_retry_and_alias(tmp_path, phase):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = Event(17, 2, 'memory', Layer.SOCIETY, data={'values':[1]})
        session.skills[1, 'craft'].provenance = [event, event]
        event.seal()
        old_generation = session.pin.captured_head
        def fail(at):
            if at == phase:
                raise OSError('Event snapshot fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='snapshot fault'): session.save()
        session.store._phase_hook = lambda _: None
        assert session.resolve_save() == old_generation + (phase == 'after_commit')
        session.save()
        assert session.pin.captured_head == old_generation + 1
        root = session.skills[1, 'craft'].provenance
        assert root[0] is root[1] is event
        assert list(event.data['values']) == [1]
        assert session.save() == session.pin.captured_head
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.skills[1, 'craft'].provenance[0]
        assert vars(event)['_sealed'] is True and list(event.data['values']) == [1]


def test_detach_reads_uncached_record_and_snapshot_descendants(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = Event(17, 2, 'memory', Layer.SOCIETY, data={'values':[1]})
        event.seal()
        session.skills[1, 'craft'].provenance = [event]
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        # No Event or frozen child has been read in this publisher session.
        plain = session.detach(materialize_history=True)
    event = plain.skills.skills[1, 'craft'].provenance[0]
    assert type(event) is Event and vars(event)['_sealed'] is True
    assert type(event.data) is FrozenDict and type(event.data['values']) is FrozenList


def test_event_header_edit_save_has_fixed_unrelated_history_work(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = converted_catalog(directory, size=size, owners=24)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            event = Event(17, 2, 'memory', Layer.SOCIETY, data={'values':list(range(1000))})
            session.skills[1, 'craft'].provenance = [event, event]
            root, data, values = session.skills[1, 'craft'].provenance, event.data, event.data['values']
            unrelated = session.skills[2, 'craft'].provenance
            session.save()
            values._read_page = lambda *_: pytest.fail('header edit read Event data archive')
            unrelated._read_page = lambda *_: pytest.fail('header edit read unrelated history')
            session._registry.live_bindings = lambda: pytest.fail('header edit scanned global registry')
            session.store.reset_diagnostics()
            event.kind = 'updated'
            session.save()
            assert root[0] is root[1] is event and event.data is data
            session.save()
            now = session.store.diagnostics()
            metric = now.payload_reads, now.payload_writes, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads', 'payload_writes', 'metadata_rows'), metric):
                record_property(f'H{size}_{label}', count)
    assert metrics[0] == metrics[1]


def test_legacy_tracked_world_event_input_rejects_before_recursive_admission(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_event_placements import catalog_with_event
    target = catalog_with_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.world.events[0]
        root = session.skills[1, 'craft'].provenance
        before = session._registry.next_incarnation
        # Existing eager tracked dict identity needs explicit complete-format
        # conversion. Do not copy it and split the native Event's held aliases.
        with pytest.raises(TypeError, match='typed container schema'):
            session.skills[1, 'craft'].provenance = [event]
        assert session.skills[1, 'craft'].provenance is root
        assert session._registry.next_incarnation == before
        assert session.world.events[0] is event
