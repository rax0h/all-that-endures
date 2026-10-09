"""The concrete family bindings govern both owner routing and record callbacks."""
import weakref

import pytest

from ate_sim.core import World
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.skills import SkillHistory
from ate_sim.lineage import LineageNode

RULES = 'final-runtime-family-bindings'


def converted(tmp_path, world):
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


def test_all_concrete_tables_bound_once_without_loading_owners(tmp_path):
    world = World(843000)
    path = converted(tmp_path, world)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        from ate_sim.persistence_lazy_families import RUNTIME_FAMILIES
        bindings = session._family_bindings
        assert set(bindings.tables) == set(RUNTIME_FAMILIES) | set(session._scalar_tables)
        assert bindings.indexed_tables['world.skills.skills'] is session.skills
        assert bindings.indexed_tables['world.lineage.nodes'] is session.lineage_nodes
        assert 'world.magic_resources.owner_index' not in bindings.indexed_tables
        for namespace, table in bindings.tables.items():
            assert table._namespace == namespace
            assert dict.__len__(table) == 0
        with pytest.raises(TypeError):
            bindings.tables['world.people'] = None


@pytest.mark.parametrize('kind', ['skill', 'lineage'])
def test_cold_indexed_alias_gets_its_authority_callback_before_mutation(tmp_path, kind):
    world = World(843000)
    if kind == 'skill':
        key, record = (1, 'craft'), SkillHistory(1, 'craft', level=.25)
        world.skills.skills[key] = record
        field, updated, attribute = 'level', .75, 'skills'
    else:
        key, record = ('person', 1), LineageNode('person', 1, 101, 2)
        world.lineage.nodes[key] = record
        field, updated, attribute = 'origin_year', 9, 'lineage_nodes'
    world.currency.wallets[1] = {'alias': record}
    path = converted(tmp_path, world)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.wallets[1]['alias']
        table = getattr(session, attribute)
        assert not dict.__contains__(table, key)
        callback = alias.__dict__.get('_index_table')
        assert isinstance(callback, weakref.ReferenceType) and callback() is table
        setattr(alias, field, updated)
        assert table[key] is alias
        assert key in table._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.wallets[1]['alias']
        assert getattr(getattr(session, attribute)[key], field) == updated
        assert getattr(session, attribute)[key] is alias


def test_cold_skill_child_alias_routes_before_mutation(tmp_path):
    world = World(843000)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=[101])
    world.currency.wallets[1] = {'alias': world.skills.skills[1, 'craft']}
    path = converted(tmp_path, world)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        child = session.wallets[1]['alias'].provenance
        assert not dict.__contains__(session.skills, (1, 'craft'))
        child.append(102)
        assert session.skills[1, 'craft'].provenance is child
        assert (1, 'craft') in session.skills._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance == [101, 102]
        assert session.wallets[1]['alias'] is session.skills[1, 'craft']


@pytest.mark.parametrize('kind,child', [('skill', False), ('skill', True), ('lineage', False)])
def test_eager_settlement_record_alias_reuses_concrete_lazy_authority(tmp_path, kind, child):
    from ate_sim.core import Settlement
    world = World(843000)
    if kind == 'skill':
        key, record, attribute = (1, 'craft'), SkillHistory(1, 'craft', provenance=[101]), 'skills'
        field, updated = 'level', .75
        world.skills.skills[key] = record
    else:
        key, record, attribute = ('person', 1), LineageNode('person', 1, 101, 2), 'lineage_nodes'
        field, updated = 'origin_year', 9
        world.lineage.nodes[key] = record
    world.settlements[1] = Settlement(1, 0, 0, memory={'alias': record})
    path = converted(tmp_path, world)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.world.settlements[1].memory['alias']
        table = getattr(session, attribute)
        assert alias.__dict__['_index_table']() is table
        if child:
            alias.provenance.append(102)
        else:
            setattr(alias, field, updated)
        assert table[key] is alias and key in table._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.world.settlements[1].memory['alias']
        assert getattr(session, attribute)[key] is alias
        if child:
            assert alias.provenance == [101, 102]
        else:
            assert getattr(alias, field) == updated


def test_direct_eager_skill_child_alias_partial_extend_is_saved(tmp_path):
    from ate_sim.core import Settlement
    world = World(843000)
    child = [101]
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=child)
    world.settlements[1] = Settlement(1, 0, 0, memory={'alias': child})
    path = converted(tmp_path, world)
    def broken():
        yield 102
        raise ValueError('iterator failed')
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.world.settlements[1].memory['alias']
        with pytest.raises(ValueError, match='iterator failed'):
            alias.extend(broken())
        assert alias == [101, 102]
        assert (1, 'craft') in session.skills._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance == [101, 102]
        assert session.world.settlements[1].memory['alias'] is session.skills[1, 'craft'].provenance


def test_direct_eager_skill_child_alias_retired_placement_does_not_return(tmp_path):
    from ate_sim.core import Settlement
    from ate_sim.incremental_store import StoreError
    world = World(843000)
    child = [101]
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=child)
    world.settlements[1] = Settlement(1, 0, 0, memory={'alias': child})
    path = converted(tmp_path, world)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.world.settlements[1].memory.pop('alias')
        session.save()
        alias.append(102)
        session.save()
        assert 'alias' not in session.world.settlements[1].memory
    with pytest.raises(StoreError):
        alias.append(103)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.skills[1, 'craft'].provenance == [101, 102]
        assert 'alias' not in session.world.settlements[1].memory


@pytest.mark.parametrize('method,value,expected', [
    ('update', 'second', {'first', 'second'}),
    ('difference_update', 'first', set()),
])
def test_direct_eager_soul_child_partial_set_mutation_is_saved(tmp_path, method, value, expected):
    from ate_sim.core import Settlement
    from ate_sim.metaphysics import SoulState
    world = World(843000)
    child = {'first'}
    world.metaphysics.souls[1] = SoulState(1, marks=child)
    world.settlements[1] = Settlement(1, 0, 0, memory={'alias': child})
    path = converted(tmp_path, world)
    def broken():
        yield value
        raise ValueError('iterator failed')
    with open_lazy_world_session(path, rules_id=RULES) as session:
        alias = session.world.settlements[1].memory['alias']
        with pytest.raises(ValueError, match='iterator failed'):
            getattr(alias, method)(broken())
        assert alias == expected
        assert 1 in session.souls._dirty
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.souls[1].marks == expected
        assert session.world.settlements[1].memory['alias'] is session.souls[1].marks
