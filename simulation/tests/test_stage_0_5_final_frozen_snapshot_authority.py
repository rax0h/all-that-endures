"""Readonly roles and deep immutable snapshot certification are distinct."""
import pytest
from ate_sim.core import Event, Layer
from ate_sim.agency import ActionRecord
from ate_sim.event_log import FrozenDict
from ate_sim.incremental_store import StoreFormatError
from ate_sim.persistence_events import _validate_sealed_event
from ate_sim.persistence_lazy_nested_history import DESCRIPTOR_NAMESPACE
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


@pytest.mark.parametrize('mutable_child', [False, True])
def test_frozen_descriptor_certifies_only_deep_immutable_native_snapshot(tmp_path, mutable_child):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        child = ActionRecord(1, 0, 'work', 'wealth', .5) if mutable_child else [1, 2]
        event = Event(17, 0, 'memory', Layer.SOCIETY, data={'child':child})
        s.skills[1, 'craft'].provenance = [event]
        event.seal()
        s.save()
        descriptor = s.store.read_version(s.pin, DESCRIPTOR_NAMESPACE, event.data._incarnation, expected_record_schema=1).value
        assert len(descriptor) == 4 and descriptor[3] is (not mutable_child)
        # Pure segment validation retains its native standalone value contract.
        with pytest.raises(StoreFormatError): _validate_sealed_event(event)


def test_backed_event_seals_and_reopens_as_checked_world_suffix(tmp_path):
    from simulation.tests.test_stage_0_5_final_world_native_event_peers import with_native_event
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        event = s.skills[1, 'craft'].provenance[0]
        event.seal()
        # Explicit sealing already copied and certified actual incoming D.
        event.data.items = lambda: pytest.fail('sealed suffix validation walked archived snapshot')
        s.save()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        event = s.world.events[0]
        assert vars(event)['_sealed'] is True and list(event.data['values']) == [1]
        with pytest.raises(TypeError): event.data['values'].append(2)


def test_sealed_world_snapshot_keeps_custody_after_record_owner_removed(tmp_path):
    from ate_sim.persistence_lazy_identity import IncarnationId
    from simulation.tests.test_stage_0_5_final_world_native_event_peers import with_native_event
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        coord = activate(s)
        event = s.skills[1, 'craft'].provenance[0]
        event.seal()
        snapshot = event.data
        s.skills[1, 'craft'].provenance = []
        s.save()
        placements = coord._current_placements(coord.discover_group(
            IncarnationId(s.store.store_identity, snapshot._incarnation)))
        try:
            assert ('world.events', 0, (('field', 'data'),)) in placements
            assert ('world.events', 0, ()) not in placements
        finally:
            if hasattr(placements, 'close'): placements.close()
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert list(s.world.events[0].data['values']) == [1]
        world = s.detach(materialize_history=True)
    assert type(world.events[0].data) is FrozenDict
    assert world.events[0].data['values'] == [1]


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_sealed_world_snapshot_commit_fault_preserves_exact_custody(tmp_path, phase):
    from simulation.tests.test_stage_0_5_final_world_native_event_peers import with_native_event
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        event = s.skills[1, 'craft'].provenance[0]
        event.seal()
        snapshot = event.data
        before = s.pin.captured_head
        def fail(at):
            if at == phase: raise OSError('sealed suffix fault')
        s.store._phase_hook = fail
        with pytest.raises(OSError, match='sealed suffix fault'): s.save()
        s.store._phase_hook = lambda _: None
        assert s.resolve_save() == before + (phase == 'after_commit')
        s.save()
        assert event.data is snapshot and s.world.events[0] is event
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert list(s.world.events[0].data['values']) == [1]
        assert s.world.events[0].data is s.skills[1, 'craft'].provenance[0].data


def test_full_snapshot_scrub_rejects_false_certification(tmp_path):
    from ate_sim.persistence_lazy_nested_history import HistoryReference
    from ate_sim.persistence_frozen_snapshots import read_frozen_certification, verify_frozen_certification
    from ate_sim.incremental_store import StoreIntegrityError
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        event = Event(17, 0, 'memory', Layer.SOCIETY, data={'child':[1, 2]})
        s.skills[1, 'craft'].provenance = [event]
        event.seal()
        s.save()
        snapshot = event.data
        assert read_frozen_certification(s.store, s.pin, HistoryReference('frozen-map', snapshot._incarnation))
        verify_frozen_certification(snapshot)
        snapshot._deep_immutable = False
        with pytest.raises(StoreIntegrityError, match='certification disagrees'):
            verify_frozen_certification(snapshot)


def test_sealed_suffix_publish_has_fixed_unrelated_history_work(tmp_path, record_property):
    from simulation.tests.test_stage_0_5_final_world_native_event_peers import with_native_event
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = with_native_event(directory, size=size, owners=24)
        with open_bridge(target, rules_id=RULES) as s:
            activate(s)
            event = s.skills[1, 'craft'].provenance[0]
            event.seal()
            event.data.items = lambda: pytest.fail('save walked sealed data archive')
            unrelated = s.skills[2, 'craft'].provenance
            unrelated._read_page = lambda *_: pytest.fail('save walked unrelated archive')
            s._registry.live_bindings = lambda: pytest.fail('save inventoried registry')
            s.store.reset_diagnostics()
            s.save()
            s.save()
            now = s.store.diagnostics()
            metric = now.payload_reads, now.payload_writes, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads','payload_writes','metadata_rows'), metric):
                record_property(f'H{size}_{label}', count)
    assert metrics[0] == metrics[1]


def test_readonly_snapshot_with_mutable_record_cannot_enter_sealed_world_suffix(tmp_path):
    target = converted_catalog(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        event = Event(1, 0, 'memory', Layer.SOCIETY,
                      data={'action':ActionRecord(1, 0, 'work', 'wealth', .5)})
        s.skills[1, 'craft'].provenance = [event]
        s.world.events.append(event)
        s.world.event_ids.add(1)
        s.world.next_event = 2
        event.seal()
        before = s.pin.captured_head
        with pytest.raises(StoreFormatError, match='deep immutable'):
            s.save()
        assert s.store.checked_head().generation == before


@pytest.mark.parametrize('bad', [1, None, 'true'])
def test_frozen_descriptor_certification_requires_exact_boolean(bad):
    from ate_sim.persistence_frozen_snapshots import checked_frozen_descriptor
    from ate_sim.incremental_store import StoreIntegrityError
    with pytest.raises(StoreIntegrityError):
        checked_frozen_descriptor(('frozen-map', 0, 0, bad))


def test_recursive_snapshot_transfers_to_strict_standalone_event_segment(tmp_path):
    from ate_sim.persistence_events import CHUNK_SIZE
    from simulation.tests.test_stage_0_5_final_world_native_event_peers import with_native_event
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        first = s.skills[1, 'craft'].provenance[0]
        # Activate the native peer before sealing all complete tail chunks.
        assert first is s.world.events[0]
        for ident in range(2, CHUNK_SIZE + 1):
            s.world.events.append(Event(ident, 0, 'memory', Layer.SOCIETY, data={}))
        s.world.event_ids.update(range(2, CHUNK_SIZE + 1))
        s.world.next_event = CHUNK_SIZE + 1
        s.world.events.seal_before(1)
        pending = s.world.events._chunk(0)
        assert type(pending[0].data) is FrozenDict
        _validate_sealed_event(pending[0])
        s.save()
        assert s.world.events._disk_count == CHUNK_SIZE
    with open_bridge(target, rules_id=RULES) as s:
        activate(s)
        assert s.world.events._disk_count == CHUNK_SIZE
        assert type(s.world.events[0].data) is FrozenDict
        assert s.world.events[0].data['values'] == [1]
