"""Packed current action storage retains its logical mutable placements."""
import pytest
from ate_sim.agency import ActionRecord
from ate_sim.core import Layer
from ate_sim.persistence_adapters import PACKED_LIST_KEY
from ate_sim.incremental_store import StoreIntegrityError
from simulation.tests.test_stage_0_5_final_world_catalog_bridge import converted_catalog, open_bridge, activate, RULES

NS = 'world.agency.actions'


def catalog_with_actions(tmp_path, shared=False, include_event=False):
    def configure(world, history):
        first = ActionRecord(0, 1, 'work', 'wealth', .5)
        world.agency.actions = [first, first if shared else ActionRecord(0, 2, 'learn', 'curiosity', .6)]
        if include_event:
            world.emit('identity-probe', Layer.REALITY, action=first)
    return converted_catalog(tmp_path, owners=1, configure_world=configure, packed_actions=True)


def test_packed_action_and_mutable_event_expose_one_canonical_record(tmp_path):
    target = catalog_with_actions(tmp_path, include_event=True)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        action = session.world.events[0].data['action']
        assert session.world.agency.actions[0] is action
        assert not coord.dirty_owners and not session._eager_tracker._dirty
        pin = session.pin
        assert session.save() == pin.captured_head and session.pin == pin
        action.strength = .9
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.events[0].data['action'] is session.world.agency.actions[0]
        assert session.world.agency.actions[0].strength == .9


def test_new_action_placements_use_actual_packed_owner(tmp_path):
    target = converted_catalog(tmp_path, owners=1, packed_actions=True)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        action = ActionRecord(0, 1, 'work', 'wealth', .5)
        session.world.agency.actions.append(action)
        session.save()
        placements = dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences)
        assert (('index', 0),) in placements
        assert coord.catalog.read_identity_group(session.pin, placements[(('index', 0),)]).occurrences == (
            (NS, PACKED_LIST_KEY, (('index', 0),)),)


def test_existing_action_scalar_edit_preserves_incarnation(tmp_path):
    target = catalog_with_actions(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        before = dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences)
        session.world.agency.actions[0].strength = .9
        session.save()
        assert dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences) == before
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert session.world.agency.actions[0].strength == .9


def test_shared_action_is_stitched_before_direct_mutation(tmp_path):
    target = catalog_with_actions(tmp_path, shared=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        first = session.world.agency.actions[0]
        assert session.world.agency.actions[1] is first
        first.strength = .9
        assert session.world.agency.actions[1] is first
        session.save()
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        first = session.world.agency.actions[0]
        first.strength = .8
        assert session.world.agency.actions[1] is first


def test_pending_append_does_not_choose_a_different_copy_before_direct_edit(tmp_path):
    target = catalog_with_actions(tmp_path, shared=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        second = session.world.agency.actions[1]
        session.world.agency.actions.append(ActionRecord(0, 2, 'learn', 'curiosity', .6))
        second.strength = .9
        assert session.world.agency.actions[0] is second and second.strength == .9
        session.save()


def test_corrupt_shared_action_group_rejects_before_field_change(tmp_path):
    target = catalog_with_actions(tmp_path, shared=True)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        first = session.world.agency.actions[0]
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions WHERE owner_namespace=? '
            'AND owner_key=? AND occurrence_path=?',
            (NS, session.store.codec.encode(PACKED_LIST_KEY), session.store.codec.encode((('index', 1),))))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):
            first.strength = .9
        assert first.strength == .5


def test_prefix_trim_moves_survivor_path_without_reallocating_identity(tmp_path):
    target = catalog_with_actions(tmp_path)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        before = dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences)
        retired, survivor = session.world.agency.actions
        del session.world.agency.actions[:1]
        survivor.strength = .8
        retired.strength = .1  # A private old alias must not resurrect position0.
        session.save()
        after = dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences)
        assert after == {(('index', 0),): before[(('index', 1),)]}
        assert session.world.agency.actions[0] is survivor and survivor.strength == .8
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert len(session.world.agency.actions) == 1 and session.world.agency.actions[0].person == 2
        assert session.world.agency.actions[0].strength == .8


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_new_packed_action_joins_exact_save_recovery(tmp_path, phase):
    target = converted_catalog(tmp_path, owners=1, packed_actions=True)
    with open_bridge(target, rules_id=RULES) as session:
        coord = activate(session)
        session.world.agency.actions.append(ActionRecord(0, 1, 'work', 'wealth', .5))
        def fail(at):
            if at == phase:
                raise OSError('packed action fault')
        session.store._phase_hook = fail
        with pytest.raises(OSError, match='packed action fault'):
            session.save()
        session.store._phase_hook = lambda _: None
        session.resolve_save()
        if phase == 'before_commit':
            session.save()
        assert coord.pin == session.pin and not coord.placement_overlay
        assert dict(coord.catalog.read_owner_identity(session.pin, (NS, PACKED_LIST_KEY)).occurrences)
    with open_bridge(target, rules_id=RULES) as session:
        activate(session)
        assert len(session.world.agency.actions) == 1
        assert session.world.agency.actions[0].strength == .5
