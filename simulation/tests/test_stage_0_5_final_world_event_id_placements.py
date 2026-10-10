"""Event-ID descriptor and fixed internal backings share checked publication."""
import pytest

from ate_sim.persistence_history_retirement import pending_retirement
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES

OWNER = ('world.event_ids', 0)
REMOVED = (('field', '_exact'), ('field', 'removed'))
ADDED = (('field', '_exact'), ('field', 'added'))


def catalog_with_ids(tmp_path, size=32):
    def configure(world, history):
        world.event_ids = set(range(1, size + 1))
    return converted_catalog(tmp_path, owners=1, configure_world=configure)


def test_exception_descriptor_backings_have_checked_owner_placements(tmp_path):
    target = catalog_with_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        ids = session.world.event_ids
        before = dict(coord.catalog.read_owner_identity(session.pin, OWNER).occurrences)
        ids.remove(2)
        ids.add(99)
        session.save()
        placements = dict(coord.catalog.read_owner_identity(session.pin, OWNER).occurrences)
        assert placements[()] == before[()]
        assert placements[REMOVED] == ids._exact.removed._incarnation
        assert placements[ADDED] == ids._exact.added._incarnation
        assert ids.diagnostics()['member_visits'] == 0
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert 2 not in session.world.event_ids and 99 in session.world.event_ids


def test_clear_retires_backing_slots_without_replacing_facade_identity(tmp_path):
    target = catalog_with_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        ids = session.world.event_ids
        ids.remove(2)
        ids.add(99)
        session.save()
        removed, added = ids._exact.histories
        before = dict(coord.catalog.read_owner_identity(session.pin, OWNER).occurrences)
        ids.clear()
        session.save()
        assert dict(coord.catalog.read_owner_identity(session.pin, OWNER).occurrences) == {(): before[()]}
        assert session.world.event_ids is ids and len(ids) == 0
        assert pending_retirement(session.store, session.pin, removed._incarnation)
        assert pending_retirement(session.store, session.pin, added._incarnation)
        assert removed[0] == 2 and 99 in added


def test_guarded_no_effect_id_edits_do_not_force_a_save(tmp_path):
    target = catalog_with_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        pin = session.pin
        ids = session.world.event_ids
        ids.add(1)
        ids.discard(-1)
        assert session.save() == pin.captured_head and session.pin == pin


def test_exception_edit_checked_work_is_independent_of_prefix_history(tmp_path):
    metrics = []
    for size in (1000, 10000):
        directory = tmp_path / str(size)
        directory.mkdir()
        target = catalog_with_ids(directory, size)
        with open_bridge(target, rules_id=RULES) as session:
            activate(session)
            ids = session.world.event_ids
            session.store.reset_diagnostics()
            ids.remove(2)
            ids.add(size + 99)
            session._registry.live_bindings = lambda: pytest.fail('ID save inventoried live bindings')
            session._eager_tracker._contains_identity = lambda *_: pytest.fail('ID save searched owner graphs')
            session.save()
            assert ids.diagnostics()['member_visits'] == 0
            metrics.append(session.store.diagnostics())
    assert metrics[0].payload_reads == metrics[1].payload_reads
    assert metrics[0].metadata_rows == metrics[1].metadata_rows
    assert metrics[0].payload_writes == metrics[1].payload_writes


def catalog_with_shared_ids(tmp_path):
    from ate_sim.metaphysics import SoulState
    def configure(world, history):
        world.event_ids = set(range(1, 33))
        world.metaphysics.souls[1] = SoulState(1, authorities=world.event_ids)
    return converted_catalog(tmp_path, owners=1, configure_world=configure)


def test_range_edit_forces_unchanged_shared_cold_header(tmp_path):
    namespace = 'world.metaphysics.souls'
    target = catalog_with_shared_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        ids = session.world.event_ids
        assert not dict.__contains__(session.souls, 1)
        ids.add(33)
        assert session.souls[1].authorities is ids
        session.save()
        with session.store.read_snapshot(session.pin):
            row = session.store.read_version(session.pin, namespace, 1, expected_record_schema=1)
            assert row.valid_from == session.pin.captured_head
        assert not coord.dirty_owners
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.souls[1].authorities is session.world.event_ids
        assert 33 in session.souls[1].authorities


def test_no_effect_shared_id_edit_stitches_cold_peer_without_publication(tmp_path):
    target = catalog_with_shared_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        pin = session.pin
        session.world.event_ids.add(1)
        assert session.souls[1].authorities is session.world.event_ids
        assert not coord.dirty_owners and not coord._value_dirty_groups
        assert session.save() == pin.captured_head and session.pin == pin


def test_pending_shared_facade_replacement_wins_before_old_alias_edit(tmp_path):
    target = catalog_with_shared_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        ids = session.world.event_ids
        session.souls[1].authorities = {'private'}
        ids.add(33)
        assert session.souls[1].authorities is not ids
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert set(session.souls[1].authorities) == {'private'}
        assert 33 in session.world.event_ids


def test_corrupt_facade_group_rejects_before_value_edit(tmp_path):
    from ate_sim.incremental_store import StoreIntegrityError
    target = catalog_with_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? '
            'AND owner_key=? AND occurrence_path=?',
            (OWNER[0], session.store.codec.encode(OWNER[1]), session.store.codec.encode(())))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            session.world.event_ids.add(33)
        assert len(session.world.event_ids) == 32


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_exception_backings_and_fixed_slots_share_save_recovery(tmp_path, phase):
    target = catalog_with_ids(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        ids = session.world.event_ids
        ids.remove(2)
        ids.add(99)
        def fail(at):
            if at == phase:
                raise OSError('event-ID publication fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='event-ID publication fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert coord.pin == session.pin and session._backing_dependencies.pin == session.pin
        assert not coord.placement_overlay and not coord.dirty_owners
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        ids = session.world.event_ids
        assert 2 not in ids and 99 in ids
        assert dict(coord.catalog.read_owner_identity(session.pin, OWNER).occurrences)[ADDED] == ids._exact.added._incarnation
