"""Guarded point work must not revalidate unrelated packed action groups."""
from dataclasses import asdict
from unittest.mock import patch
import pytest
from ate_sim.agency import ActionRecord
from ate_sim.core import World, Layer
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.incremental_store import StoreIntegrityError
from ate_sim.incremental_store import CodecError
from ate_sim.persistence_adapters import PACKED_LIST_KEY

RULES = 'packed-action-speed-repair'
NS = 'world.agency.actions'


def fixture(tmp_path, size, *, shared=False):
    world = World(843000)
    world.agency.actions = [ActionRecord(0, i, 'work', 'wealth', .5) for i in range(size)]
    if shared:
        action = world.agency.actions[0]
        world.agency.actions.append(action)
        world.currency.wallets[1] = {'action': action}
        world.emit('shared-action', Layer.REALITY, action=action)
    cold, legacy, complete = (tmp_path/name for name in ('cold.sqlite', 'legacy.sqlite', 'complete.sqlite'))
    write_cold_snapshot(world, cold, rules_id=RULES)
    convert_cold_to_lazy(cold, legacy, rules_id=RULES, native_graph_buckets=True)
    upgrade_lazy_snapshot(legacy, complete, rules_id=RULES)
    return complete


@pytest.mark.parametrize('size', [16, 320])
def test_append_and_scalar_reconcile_check_only_affected_placements(tmp_path, size, record_property):
    path = fixture(tmp_path, size)
    rows = []
    with open_lazy_world_session(path, rules_id=RULES) as session:
        actions = session.world.agency.actions
        cat = session._identity_coordinator.catalog
        selected = actions[size//2]
        for label, operation in (
            ('append', lambda: actions.append(ActionRecord(1, size, 'learn', 'curiosity', .75))),
            ('scalar', lambda: setattr(selected, 'strength', .9)),
            ('append_again', lambda: actions.append(ActionRecord(1, size+1, 'learn', 'curiosity', .8))),
            ('new_scalar', lambda: setattr(actions[-1], 'strength', .85)),
        ):
            session.store.reset_diagnostics()
            with patch.object(cat, 'read_identity_group', wraps=cat.read_identity_group) as groups, \
                 patch.object(cat, 'read_owner_identity', wraps=cat.read_owner_identity) as owners, \
                 patch.object(cat, '_node', wraps=cat._node) as nodes:
                operation()
                session._identity_bridge.synchronize_lazy_placements()
                rows.append(dict(operation=label, groups=groups.call_count,
                    owners=owners.call_count, nodes=nodes.call_count,
                    io=asdict(session.store.diagnostics())))
        record_property('packed_action_local_reconcile', rows)
        assert all(row['owners'] == 0 for row in rows), rows
        assert all(row['groups'] <= 4 and row['nodes'] <= 128 for row in rows), rows
        assert all(row['io']['payload_reads'] <= 128 for row in rows), rows
        assert len(session._identity_coordinator.discovered_groups) <= 256
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert len(session.world.agency.actions) == size+2
        assert session.world.agency.actions[size//2].strength == .9
        assert [a.person for a in session.world.agency.actions[-2:]] == [size, size+1]


def test_shared_action_scalar_edit_after_append_preserves_cross_family_aliases(tmp_path):
    path = fixture(tmp_path, 320, shared=True)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        action = session.world.events[0].data['action']
        assert action is session.world.agency.actions[0] is session.world.agency.actions[-1]
        assert action is session.wallets[1]['action']
        session.world.agency.actions.append(ActionRecord(1, 500, 'learn', 'curiosity', .8))
        action.strength = .95
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        action = session.world.events[0].data['action']
        assert action is session.world.agency.actions[0] is session.world.agency.actions[-2]
        assert action is session.wallets[1]['action'] and action.strength == .95


def test_warmed_scalar_action_rejects_missing_authority_before_edit(tmp_path):
    path = fixture(tmp_path, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        action = session.world.agency.actions[0]
        coord = session._identity_coordinator
        incarnation = session._registry.incarnation_for_object(action)
        coord.discover_group(incarnation)
        session.store.db.execute('DELETE FROM lazy_identity_occurrence_versions '
            'WHERE owner_namespace=? AND owner_key=? AND occurrence_path=?',
            (NS, session.store.codec.encode(PACKED_LIST_KEY),
             session.store.codec.encode((('index', 0),))))
        session.store.db.commit()
        with pytest.raises(StoreIntegrityError):action.strength = .9
        assert action.strength == .5


def test_actual_mutable_import_after_trim_retains_children_and_old_alias(tmp_path):
    path = fixture(tmp_path, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        actions = session.world.agency.actions
        retired, survivor = actions[:2]
        del actions[:1]
        survivor.motive = {'values': [1, 2]}
        session._identity_bridge.synchronize_lazy_placements()
        survivor.motive['values'].append(3)
        retired.strength = .1
        session.save()
        assert actions[0] is survivor and len(actions) == 15
    with open_lazy_world_session(path, rules_id=RULES) as session:
        action = session.world.agency.actions[0]
        assert action.person == 1 and action.motive['values'] == [1, 2, 3]


def test_moves_duplicates_and_equal_distinct_replacement_keep_identity(tmp_path):
    path = fixture(tmp_path, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        actions = session.world.agency.actions
        held = actions[0]
        actions.reverse()
        actions[:] = [*actions, held]
        actions[0] = ActionRecord(0, 15, 'work', 'wealth', .5)
        held.strength = .9
        session.save()
        assert actions[-2] is held is actions[-1]
    with open_lazy_world_session(path, rules_id=RULES) as session:
        actions = session.world.agency.actions
        assert actions[-2] is actions[-1] and actions[-1].strength == .9
        assert actions[0].person == 15 and actions[0] is not actions[-1]


def test_wrapper_normalization_does_not_drop_unknown_record_state(tmp_path):
    path = fixture(tmp_path, 16)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        action = session.world.agency.actions[0]
        action.unclassified_state = 'must reject'
        with pytest.raises(CodecError, match='unclassified'):
            session.save()
