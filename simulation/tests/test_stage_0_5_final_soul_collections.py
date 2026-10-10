"""Soul set/map histories are compact, shared and retirement-aware."""
import pytest

from ate_sim.core import World
from ate_sim.metaphysics import SoulState
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_nested_history import LazyHistoryMap, LazyHistorySet

RULES = 'final-soul-collections'


def converted(tmp_path, size=1000):
    world = World(843000)
    marks = {f'mark-{i}' for i in range(size)}
    links = {f'link-{i}': float(i) for i in range(size)}
    world.metaphysics.souls[1] = SoulState(1, authorities=marks, marks=marks, cosmic_links=links)
    world.metaphysics.souls[2] = SoulState(2, marks=marks, cosmic_links=links)
    world.currency.wallets[1] = {'marks': marks, 'links': links}
    source, target = tmp_path / 'cold.sqlite', tmp_path / 'lazy.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
def test_soul_scalar_save_reads_no_collection_pages(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        soul = session.souls[1]
        assert isinstance(soul.marks, LazyHistorySet)
        assert soul.authorities is soul.marks
        assert isinstance(soul.cosmic_links, LazyHistoryMap)
        soul.death_count += 1
        session.save()
        assert soul.marks.diagnostics()['entry_loads'] == 0
        assert soul.cosmic_links.diagnostics()['entry_loads'] == 0
        assert len(session.souls._baseline_payload[1]) < 2048


def test_cold_shared_alias_mutation_replacement_and_reopen(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        wallet = session.wallets[1]
        assert isinstance(wallet['marks'], LazyHistorySet)
        assert isinstance(wallet['links'], LazyHistoryMap)
        wallet['marks'].add('new')
        wallet['links']['new'] = 2.5
        assert session.souls[1].marks is session.souls[2].marks is wallet['marks']
        session.souls[1].marks = {'replacement'}
        wallet['marks'].discard('mark-1')
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        soul = session.souls[1]
        assert soul.marks == {'replacement'}
        assert soul.authorities is session.souls[2].marks is session.wallets[1]['marks']
        assert 'new' in soul.authorities and 'mark-1' not in soul.authorities
        assert soul.cosmic_links is session.souls[2].cosmic_links is session.wallets[1]['links']
        assert soul.cosmic_links['new'] == 2.5


def test_new_soul_preserves_shared_set_and_detach_memo(tmp_path):
    path = converted(tmp_path, 1)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        marks = {'same'}
        session.souls[3] = SoulState(3, authorities=marks, marks=marks)
        assert session.souls[3].authorities is session.souls[3].marks
        session.save()
        detached = session.detach(materialize_history=True)
        assert type(detached.metaphysics.souls[1].cosmic_links) is dict
        assert detached.metaphysics.souls[1].cosmic_links is detached.currency.wallets[1]['links']
        assert detached.metaphysics.souls[3].authorities is detached.metaphysics.souls[3].marks
