"""Clean record caps apply during real run/step lifetimes, with live aliases."""
import pytest

from ate_sim.core import World, Person
from ate_sim.skills import SkillHistory
from ate_sim.lineage import LineageNode
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot

RULES = 'final-step-record-caps'


@pytest.mark.parametrize('family', ['people', 'skills', 'lineage_nodes', 'genealogy_children'])
def test_step_record_cap_drops_sidecars_without_losing_external_alias(tmp_path, family):
    world = World(843000)
    count = 600
    for number in range(1, count + 1):
        if family == 'people':
            world.people[number] = Person(number, 0, 1, 1)
        elif family == 'skills':
            world.skills.skills[number, 'craft'] = SkillHistory(number, 'craft')
        elif family == 'lineage_nodes':
            world.lineage.nodes['person', number] = LineageNode('person', number, 101, 2)
        else:
            world.genealogy.children[number] = [number]
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    key = lambda number: (number, 'craft') if family == 'skills' else ('person', number) if family == 'lineage_nodes' else number
    with open_lazy_world_session(target, rules_id=RULES) as session:
        table = getattr(session, family)
        retained = table[key(1)]
        lifetime = session.world.__dict__['_ate_persistence_lifetime']
        lifetime.begin_run()
        lifetime.begin_step()
        try:
            for number in range(2, count + 1):
                table[key(number)]
                assert len(table._lru) <= 256
                assert len(table._lru._step_touched) <= 256
            assert not dict.__contains__(table, key(1))
            for field in ('_baseline_payload', '_baseline_presence', '_baseline_incarnation',
                          '_baseline_ordinal', '_baseline_identity_labels'):
                assert set(getattr(table, field, {})) <= set(dict.keys(table))
            if family == 'genealogy_children':
                retained.append(9999)
            else:
                field = {'people': 'wealth', 'skills': 'level', 'lineage_nodes': 'origin_year'}[family]
                setattr(retained, field, 99)
            assert table[key(1)] is retained
        finally:
            lifetime.end_step()
            lifetime.end_run()
        assert len(table._lru) <= 256
        assert not table._lru._step_touched
        assert session._record_cache_budget.diagnostics()['bytes'] <= 32 * 1024 * 1024
        session.save()
    with open_lazy_world_session(target, rules_id=RULES) as session:
        record = getattr(session, family)[key(1)]
        if family == 'genealogy_children':
            assert list(record) == [1, 9999]
        else:
            assert getattr(record, field) == 99


def test_many_empty_current_queries_keep_cache_and_step_metadata_capped(tmp_path):
    world = World(843000)
    world.people[1] = Person(1, 0, 1, 1)
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES, native_graph_buckets=True)
    with open_lazy_world_session(target, rules_id=RULES) as session:
        lifetime = session.world.__dict__['_ate_persistence_lifetime']
        lifetime.begin_run()
        lifetime.begin_step()
        try:
            for key in range(2, 1002):
                assert list(session.people.ids('alive', key)) == []
                for cache in session.people._query_caches:
                    assert len(cache) <= 256
                    assert len(cache._step_touched) <= 256
            assert dict.__len__(session.people) == 0
            assert not session.people._baseline_presence
        finally:
            lifetime.end_step()
            lifetime.end_run()
        assert all(not cache._step_touched for cache in session.people._query_caches)
