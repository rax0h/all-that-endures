"""Mutable LOG placements use the same checked routing as cold families."""
import pytest
from ate_sim.core import Layer
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES


def catalog_with_event(tmp_path, size=32):
    def configure(world, history):
        world.emit('identity-probe', Layer.REALITY, history=history)
    return converted_catalog(tmp_path, size=size, owners=1, configure_world=configure)


def test_replaced_event_child_routes_old_alias_only_to_remaining_owner(tmp_path):
    target = catalog_with_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        event = session.world.events[0]
        child = event.data['history']
        event.data['history'] = [777]
        child.append(99)
        assert session.skills[1, 'craft'].provenance is child
        assert ('world.events', 0) in coord.dirty_owners
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert list(session.world.events[0].data['history']) == [777]
        assert session.skills[1, 'craft'].provenance[-1] == 99


def test_new_event_attaches_existing_lazy_child_to_checked_catalog(tmp_path):
    target = converted_catalog(tmp_path, owners=1)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        event = session.world.emit('identity-probe', Layer.REALITY, history=child)
        child.append(99)
        assert event.data['history'] is child
        assert ('world.events', 0) in coord.dirty_owners
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['history'] is session.skills[1, 'craft'].provenance
        assert session.world.events[0].data['history'][-1] == 99


def test_shared_child_forces_unchanged_event_envelope(tmp_path):
    target = catalog_with_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        child.append(99)
        assert session.world.events[0].data['history'] is child
        assert ('world.events', 0) in coord.dirty_owners
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['history'] is session.skills[1, 'craft'].provenance
        assert session.world.events[0].data['history'][-1] == 99


def test_sealed_event_retires_mutable_placements_without_retiring_shared_backing(tmp_path):
    target = catalog_with_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        event = session.world.events[0]
        child = event.data['history']
        event.seal()
        child.append(99)
        assert event.data['history'][-1] == 31
        session.save()
        checked = coord.catalog.read_owner_identity(session.pin, ('world.events', 0))
        assert tuple(checked.occurrences) == ()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['history'][-1] == 31
        assert session.skills[1, 'craft'].provenance[-1] == 99


def test_scalar_event_edit_preserves_original_event_and_data_incarnations(tmp_path):
    target = catalog_with_event(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        checked = coord.catalog.read_owner_identity(session.pin, ('world.events', 0))
        before = dict(checked.occurrences)
        session.world.events[0].kind = 'edited'
        session.save()
        checked = coord.catalog.read_owner_identity(session.pin, ('world.events', 0))
        assert dict(checked.occurrences) == before


def test_event_shared_edit_has_identical_checked_work_at_paired_archive_sizes(tmp_path):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = catalog_with_event(directory, size)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            child = session.skills[1, 'craft'].provenance
            session.store.reset_diagnostics()
            child.append(size)
            child._read_page = lambda *_: pytest.fail('event save read historical members')
            session._registry.live_bindings = lambda: pytest.fail('event save inventoried live bindings')
            session._eager_tracker._contains_identity = lambda *_: pytest.fail('event save searched owner graphs')
            session.save()
            diagnostics = session.store.diagnostics()
            assert diagnostics.payload_read_bytes < 32768
            metrics.append(diagnostics)
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].metadata_rows == metrics[1].metadata_rows
    assert metrics[0].payload_writes == metrics[1].payload_writes


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_new_event_placement_and_backing_share_exact_save_recovery(tmp_path, phase):
    target = converted_catalog(tmp_path, owners=1)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        child = session.skills[1, 'craft'].provenance
        session.world.emit('identity-probe', Layer.REALITY, history=child)
        child.append(99)
        def fail(at):
            if at == phase:
                raise OSError('event placement fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='event placement fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert coord.pin == session.pin
        assert not coord.dirty_owners and not coord.placement_overlay
        assert session._backing_dependencies.pin == session.pin
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['history'] is session.skills[1, 'craft'].provenance
        assert session.world.events[0].data['history'][-1] == 99
