"""Soul transformation history shares the same bounded list authority as skills."""
import pytest

from ate_sim.core import World, Settlement
from ate_sim.metaphysics import SoulState
from ate_sim.skills import SkillHistory
from ate_sim.persistence_lazy import convert_cold_to_lazy, open_lazy_world_session
from ate_sim.persistence_session import write_cold_snapshot
from ate_sim.persistence_lazy_nested_history import LazyHistoryList

RULES = 'final-paged-soul-transformations'


def converted(tmp_path, size=1000):
    world = World(843000)
    history = list(range(size))
    world.metaphysics.souls[1] = SoulState(1, transformations=history)
    world.skills.skills[1, 'craft'] = SkillHistory(1, 'craft', provenance=history)
    world.settlements[1] = Settlement(1, 0, 0, memory={'history': history})
    source, target = tmp_path / 'source.sqlite', tmp_path / 'target.sqlite'
    write_cold_snapshot(world, source, rules_id=RULES)
    convert_cold_to_lazy(source, target, rules_id=RULES)
    return target


@pytest.mark.parametrize('size', [1000, 10000])
def test_soul_scalar_edit_preserves_compact_history_without_page_reads(tmp_path, size):
    path = converted(tmp_path, size)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        soul = session.souls[1]
        history = soul.transformations
        assert isinstance(history, LazyHistoryList)
        assert history.diagnostics()['page_loads'] == 0
        soul.death_count += 1
        session.save()
        assert history.diagnostics()['page_loads'] == 0
        assert len(session.souls._baseline_payload[1]) < 2048
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.souls[1].death_count == 1
        assert session.souls[1].transformations[-1] == size - 1


def test_soul_skill_and_eager_alias_share_append_and_replacement(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        history = session.world.settlements[1].memory['history']
        assert isinstance(history, LazyHistoryList)
        history.append(1000)
        soul = session.souls[1]
        assert soul.transformations is session.skills[1, 'craft'].provenance is history
        soul.transformations = [91]
        history.append(1001)
        session.save()
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert session.souls[1].transformations == [91]
        history = session.skills[1, 'craft'].provenance
        assert history is session.world.settlements[1].memory['history']
        assert history[-2:] == [1000, 1001]


def test_soul_skill_detach_materializes_one_shared_list(tmp_path):
    path = converted(tmp_path)
    with open_lazy_world_session(path, rules_id=RULES) as session:
        assert isinstance(session.souls[1].transformations, LazyHistoryList)
        detached = session.detach(materialize_history=True)
    history = detached.metaphysics.souls[1].transformations
    assert type(history) is list
    assert detached.skills.skills[1, 'craft'].provenance is history
    assert detached.settlements[1].memory['history'] is history
