"""A native recursively backed Event and its mutable World log peer are one body."""
import pytest
from ate_sim.core import Event, Layer
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def with_native_event(tmp_path, *, size=32, owners=2):
    target = converted_catalog(tmp_path, size=size, owners=owners)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = Event(1, 0, 'memory', Layer.SOCIETY, data={'values':[1]})
        session.skills[1, 'craft'].provenance = [event]
        session.world.events.append(event)
        session.world.event_ids.add(1)
        session.world.next_event = 2
        session.save()
    return target


@pytest.mark.parametrize('first', ['history', 'world-log'])
def test_native_event_peer_reopens_and_first_edit_publishes_one_body(tmp_path, first):
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = (session.skills[1, 'craft'].provenance[0] if first == 'history' else session.world.events[0])
        event.kind = 'updated'
        assert session.skills[1, 'craft'].provenance[0] is session.world.events[0] is event
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.skills[1, 'craft'].provenance[0]
        assert event is session.world.events[0] and event.kind == 'updated'
        assert list(event.data['values']) == [1]


def test_uncached_native_event_peer_detach_keeps_one_shared_body(tmp_path):
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        world = session.detach(materialize_history=True)
    assert world.skills.skills[1, 'craft'].provenance[0] is world.events[0]


def test_resident_event_payload_disagreement_rejects_before_alias_install(tmp_path):
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.world.events[0]
        object.__setattr__(event, 'kind', 'untracked mismatch')
        with pytest.raises(StoreIntegrityError):
            session.skills[1, 'craft'].provenance[0]
        assert session.world.events[0] is event


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_first_world_event_edit_has_exact_backing_recovery(tmp_path, phase):
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.world.events[0]
        event.kind = 'updated'
        def fail(at):
            if at == phase:
                raise OSError('native Event peer fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='native Event peer fault'): session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        session.save()
        assert session.world.events[0] is session.skills[1, 'craft'].provenance[0] is event
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.skills[1, 'craft'].provenance[0]
        assert session.world.events[0] is event and event.kind == 'updated'


def test_native_event_peer_detach_staging_failure_preserves_publisher_body(tmp_path, monkeypatch):
    from ate_sim import persistence_lifecycle as lifecycle
    from ate_sim.persistence_lazy_nested_history import LazyHistoryMap
    target = with_native_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        event = session.world.events[0]
        old_log, data = session.world.events, event.data
        def fail(at, owner):
            if at == 'before_publish':
                raise OSError('native Event detach staging fault')
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', fail)
        with pytest.raises(OSError, match='detach staging fault'):
            session.detach(materialize_history=True)
        assert session.world.events is old_log and old_log[0] is event
        assert event.data is data and type(data) is LazyHistoryMap
        assert session.skills[1, 'craft'].provenance[0] is event
        monkeypatch.setattr(lifecycle, '_lifecycle_phase', lambda *_: None)
        world = session.detach(materialize_history=True)
    assert world.events[0] is world.skills.skills[1, 'craft'].provenance[0]


def test_first_resident_event_edit_has_fixed_related_group_work(tmp_path, record_property):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = with_native_event(directory, size=size, owners=24)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            event = session.world.events[0]
            data = event.data
            root = session.skills[1, 'craft'].provenance
            unrelated = session.skills[2, 'craft'].provenance
            unrelated._read_page = lambda *_: pytest.fail('Event peer edit read unrelated archive')
            data.items = lambda: pytest.fail('Event peer selection walked data archive')
            session._registry.live_bindings = lambda: pytest.fail('Event peer selection inventoried registry')
            session.store.reset_diagnostics()
            event.kind = 'updated'
            assert root[0] is event and event.data is data
            session.save()
            session.save()
            now = session.store.diagnostics()
            metric = now.payload_reads, now.payload_writes, now.metadata_rows
            metrics.append(metric)
            for label, count in zip(('payload_reads', 'payload_writes', 'metadata_rows'), metric):
                record_property(f'H{size}_{label}', count)
    assert metrics[0] == metrics[1]
