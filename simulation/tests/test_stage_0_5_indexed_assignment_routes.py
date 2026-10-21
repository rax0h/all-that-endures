"""Assignment-local route reuse must preserve all public notification fallbacks."""
from unittest.mock import patch

import pytest

from ate_sim.agency import MotiveState
from ate_sim.persistence_complete_format import upgrade_lazy_snapshot
from ate_sim.persistence_lazy import open_lazy_world_session
from simulation.tests.test_stage_0_5_final_identity_only_headers import complete, RULES
from simulation.tests.test_stage_0_5_final_catalog_copy import legacy_lazy


def shared_motives(tmp_path):
    def configure(world):
        shared = MotiveState(safety=.25)
        world.agency.motives.update({1: shared, 2: shared})
    source = legacy_lazy(tmp_path, configure=configure)
    target = tmp_path/'shared.sqlite'
    upgrade_lazy_snapshot(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('family,key,field,value', [
    ('people', 1, 'wealth', 2.), ('motives', 1, 'safety', .8),
    ('skills', (1, 'craft'), 'level', .9),
])
def test_scalar_assignment_checks_shared_routes_once(tmp_path, family, key, field, value):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = getattr(session, family)
        record = table[key]
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
            setattr(record, field, value)
        assert calls.call_count == 1
        assert key in table._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert getattr(getattr(session, family)[key], field) == value


def test_scalar_assignment_discovers_cold_peer_and_saves_alias(tmp_path):
    path = shared_motives(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.motives[1]
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
            record.safety = .75
        assert calls.call_count == 1
        assert session.motives[2] is record
        assert session.motives._dirty == {1, 2}
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.motives[1] is session.motives[2]
        assert session.motives[2].safety == .75


def test_structural_assignment_still_checks_and_tracks_children(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.skills[1, 'craft']
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
            record.provenance = [{'history': [3]}]
        assert calls.call_count >= 2
        record.provenance[0]['history'].append(4)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance[0]['history'] == [3, 4]


def test_custom_shared_notification_is_preserved(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.people[1]
        notified = []
        original = session.people.shared_record_changed
        def changed(obj):
            notified.append(obj)
            original(obj)
        session.people.shared_record_changed = changed
        record.wealth = 2.
        assert notified == [record]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 2.


@pytest.mark.parametrize('metadata', [('checked',), ()])
def test_custom_preflight_return_value_is_not_interpreted_as_routes(tmp_path, metadata):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.people[1]
        original = session.people.preflight_shared_record
        def preflight(obj):
            original(obj)
            return metadata
        session.people.preflight_shared_record = preflight
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
            record.wealth = .75
        assert calls.call_count == 2
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == .75


def test_hook_installed_during_notification_is_not_skipped(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.people
        record = table[1]
        notified = []
        original = table.shared_record_changed
        original_changed = table.changed
        def shared(obj):
            notified.append(obj)
            original(obj)
        def changed(key, field=None):
            if field == 'wealth': table.shared_record_changed = shared
            original_changed(key, field)
        with patch.object(table, 'changed', side_effect=changed): record.wealth = .75
        assert notified == [record]
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == .75


@pytest.mark.parametrize('runtime', ['_identity_bridge', '_recursive_histories'])
def test_synchronizing_runtime_falls_back(tmp_path, runtime):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.people[1]
        with patch.object(getattr(session, runtime), '_synchronizing', True):
            with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
                record.wealth = 2.
            assert calls.call_count == 2
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 2.


def test_reentrant_assignment_invalidates_outer_ticket(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.people
        record = table[1]
        old_age = record.age
        original = table.changed
        armed = True
        def changed(key, field=None):
            nonlocal armed
            if armed and field == 'wealth':
                armed = False
                record.age += 1
            original(key, field)
        with patch.object(table, 'changed', side_effect=changed):
            with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
                record.wealth = 2.
            assert calls.call_count >= 3
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 2. and session.people[1].age == old_age+1


def test_rolled_back_database_write_invalidates_ticket(tmp_path):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.people[1]
        original = session.people.changed
        def changed(key, field=None):
            if field == 'wealth':
                session.store.db.execute('SAVEPOINT epoch')
                session.store.db.execute("UPDATE store_metadata SET value=value WHERE key='codec_version'")
                session.store.db.execute('ROLLBACK TO epoch')
                session.store.db.execute('RELEASE epoch')
            original(key, field)
        with patch.object(session.people, 'changed', side_effect=changed):
            with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
                record.wealth = 2.
            assert calls.call_count == 2
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 2.


def test_peer_deletion_during_changed_never_resurrects_owner(tmp_path):
    path = shared_motives(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        table = session.motives
        record = table[1]
        original = table.changed
        victims = []
        def changed(key, field=None):
            if field == 'safety' and not victims:
                victim = 3-key
                victims.append(victim)
                del table[victim]
            original(key, field)
        with patch.object(table, 'changed', side_effect=changed): record.safety = .75
        assert victims[0] not in table
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert victims[0] not in session.motives
        assert session.motives[3-victims[0]].safety == .75


@pytest.mark.parametrize('value', [float('nan'), float('inf')])
def test_nonfinite_scalar_uses_full_routing(tmp_path, value):
    path = complete(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        record = session.people[1]
        with patch.object(session, '_shared_object_routes', wraps=session._shared_object_routes) as calls:
            record.wealth = value
        assert calls.call_count == 2
        record.wealth = 2.
        session.save()
