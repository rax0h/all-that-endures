"""Shared record bytes include payload sidecars and preserve retained aliases."""
import pytest

from ate_sim.core import Person
from ate_sim.persistence_lazy import open_lazy_world_session, convert_cold_to_lazy
from ate_sim.persistence_lazy_budget import SharedCacheBudget
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.skills import SkillHistory
from simulation.tests.test_persistence_lazy_people import people_world, RULES


def converted(tmp_path, count=20, *, width=400):
    world = people_world(count)
    for pid, person in world.people.items():
        person.parents = tuple(range(width))
        world.skills.skills[pid, 'craft'] = SkillHistory(pid, 'craft',
            teachers=list(range(width)), provenance=list(range(width)))
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


def small_budget(session, byte_limit):
    budget = SharedCacheBudget(entry_limit=4096, byte_limit=byte_limit)
    session._record_cache_budget = budget
    return budget


def test_records_and_sidecars_share_one_byte_budget_across_families(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        budget = small_budget(session, 64 * 1024)
        for pid in range(1, 21):
            assert session.people[pid].id == pid
            assert session.skills[pid, 'craft'].person == pid
            diag = budget.diagnostics()
            assert 0 < diag['bytes'] <= budget.byte_limit
        assert budget.diagnostics()['evictions'] > 0
        assert dict.__len__(session.people) + dict.__len__(session.skills) < 40
        for table in (session.people, session.skills):
            for field in ('_baseline_payload', '_baseline_presence', '_baseline_incarnation',
                          '_baseline_ordinal', '_baseline_identity_labels'):
                assert set(getattr(table, field, {})) <= set(dict.keys(table))
        assert session.diagnostics()['record_cache'] == budget.diagnostics()
    assert budget.diagnostics()['entries'] == budget.diagnostics()['bytes'] == 0


def test_evicted_external_alias_rehydrates_same_object_and_saves(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        budget = small_budget(session, 32 * 1024)
        retained = session.people[1]
        for pid in range(2, 21):
            session.people[pid]
            session.skills[pid, 'craft']
        assert not dict.__contains__(session.people, 1)
        retained.wealth = 99.0
        assert session.people[1] is retained
        assert 1 in session.people._dirty
        # Dirty state is charged separately and cannot be evicted as clean.
        for pid in range(2, 21):
            session.people[pid]
        assert session.people[1] is retained
        assert budget.diagnostics()['bytes'] <= budget.byte_limit
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 99.0


def test_oversize_point_read_returns_record_without_retaining_cache(tmp_path):
    path = converted(tmp_path, count=1)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        budget = small_budget(session, 128)
        person = session.people[1]
        assert isinstance(person, Person) and len(person.parents) == 400
        assert not dict.__contains__(session.people, 1)
        assert budget.diagnostics()['entries'] == 0
        person.wealth = 88.0
        assert session.people[1] is person
        session.save()


def test_byte_budget_applies_inside_simulation_step(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        budget = small_budget(session, 32 * 1024)
        lifetime = session.world.__dict__['_ate_persistence_lifetime']
        lifetime.begin_run()
        lifetime.begin_step()
        try:
            for pid in range(1, 21):
                assert session.people[pid].id == pid
                session.skills[pid, 'craft']
                assert budget.diagnostics()['bytes'] <= budget.byte_limit
            assert budget.diagnostics()['evictions'] > 0
        finally:
            lifetime.end_step()
            lifetime.end_run()


@pytest.mark.parametrize('phase', ['before_commit', 'after_commit'])
def test_tiny_cache_budget_preserves_frozen_save_and_exact_recovery(tmp_path, phase):
    path = converted(tmp_path, count=8, width=100)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        small_budget(session, 128)
        retained = session.people[1]
        retained.wealth = 77.
        before = session.pin.captured_head
        def fail(current):
            if current == phase:
                raise OSError(phase)
        session.store._phase_hook = fail
        with pytest.raises(OSError, match=phase):
            session.save()
        publication = session._pending_save.publication
        fingerprint = tuple(unit.delta.fingerprint for unit in publication.participants)
        session.store._phase_hook = lambda phase: None
        resolved = session.resolve_save()
        if phase == 'before_commit':
            assert resolved == before
            assert 1 in session.people._dirty
            session.save()
        else:
            assert resolved == before + 1
            assert all(unit.accepted for unit in publication.participants)
        assert fingerprint == tuple(unit.delta.fingerprint for unit in publication.participants)
        assert session.people[1] is retained
        assert retained.wealth == 77.
        assert session.save() == before + 1
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.people[1].wealth == 77.


def test_query_cache_bytes_share_record_budget_and_drop_step_metadata(tmp_path):
    path = converted(tmp_path, count=8, width=10)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        from ate_sim.persistence_lazy import _StepAwareLRU
        budget = small_budget(session, 1024)
        cache = _StepAwareLRU(session)
        lifetime = session.world.__dict__['_ate_persistence_lifetime']
        lifetime.begin_run()
        lifetime.begin_step()
        try:
            for key in range(1000):
                cache[key] = ('x' * 500, key)
            assert budget.diagnostics()['bytes'] <= 1024
            assert len(cache._step_touched) <= len(cache)
            cache[1001] = 'y' * 10000
            assert 1001 not in cache and 1001 not in cache._step_touched
        finally:
            lifetime.end_step()
            lifetime.end_run()
        cache.clear()
        assert budget.diagnostics()['entries'] == 0


@pytest.mark.parametrize('family,child', [
    ('skills', False), ('skills', True), ('souls', False), ('souls', True),
    ('wallets', False), ('social_edges', False), ('social_edges', True),
    ('property', False), ('property', True),
])
def test_oversized_record_mutation_pins_dirty_owner_before_rehydration(tmp_path, family, child):
    from ate_sim.core import World
    from ate_sim.metaphysics import SoulState
    from ate_sim.social import Relationship
    from ate_sim.economy import Property
    world = World(843000)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=[101])
    world.metaphysics.souls[1] = SoulState(1, transformations=[101])
    world.currency.wallets[1] = {'gold': 3}
    world.social.edges[1, 2] = Relationship(1, 2, shared_history=[101])
    world.economy.property[1] = Property(1, 'farm', 1, 'household', 1, 10., 3, provenance=[101])
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    keys = {'skills': (1, 'craft'), 'souls': 1, 'wallets': 1, 'social_edges': (1, 2), 'property': 1}
    fields = {'skills': ('level', 'provenance'), 'souls': ('death_count', 'transformations'),
              'social_edges': ('trust', 'shared_history'), 'property': ('value', 'provenance')}
    def table_for(session):
        return session.world.economy.property if family == 'property' else getattr(session, family)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        small_budget(session, 128)
        table, key = table_for(session), keys[family]
        record = table[key]
        assert not dict.__contains__(table, key)
        if family == 'wallets':
            record['gold'] = 99
        elif child:
            getattr(record, fields[family][1]).append(102)
        else:
            setattr(record, fields[family][0], 9)
        assert key in table._dirty
        assert table[key] is record
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        record = table_for(session)[keys[family]]
        if family == 'wallets':
            assert record['gold'] == 99
        elif child:
            assert list(getattr(record, fields[family][1])) == [101, 102]
        else:
            assert getattr(record, fields[family][0]) == 9
