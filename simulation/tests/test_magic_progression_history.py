from ate_sim.worldgen import generate_world
from ate_sim.magic_resources import absorb_essence_resource, use_awakening_stone
from ate_sim.magic_progression import practice_ability, record_body_transition
from ate_sim.checkpoint import dumps, loads
from ate_sim.history_archive import export_archive, HistoryArchive
from validate_magic_progression import validate
import pytest


def test_absorption_cannot_mutate_history_or_path_without_ownership():
    world=generate_world(843000)
    p=next(p for p in world.people.values() if world.advancement.path(p.id) is None)
    resource=world.magic_resources.create('essence','fire','Common',0,p.settlement,'settlement',p.settlement)
    before=world.digest()
    with pytest.raises(ValueError):absorb_essence_resource(world,p.id,resource.id)
    assert world.digest()==before


def test_absorption_readiness_milestones_survive_checkpoint_and_archive(tmp_path):
    world = generate_world(843000)
    p = next(p for p in world.people.values() if world.advancement.path(p.id) is None)
    for key in ('fire', 'water', 'wind'):
        r = world.magic_resources.create('essence', key, 'Common', 0,
                                        p.settlement, 'person', p.id)
        absorb_essence_resource(world, p.id, r.id)
    assert p.rank == 0
    path = world.advancement.path(p.id)
    assert len(path.abilities) == 4
    assert any(e.kind == 'confluence_absorbed' for e in world.events)
    for essence in path.essences:
        for _ in range(4):
            r = world.magic_resources.create('awakening_stone', 'eyes', 'Common',
                                            0, p.settlement, 'person', p.id)
            use_awakening_stone(world, p.id, r.id, target_essence=essence)
    assert len(path.abilities) == 20
    assert p.rank == 1
    for i in range(20):
        before = world.advancement.rank(p.id)
        practice_ability(world, p, i, 1000., context='test_training')
        record_body_transition(world, p, before, context='test_training')
        assert p.rank == (2 if i == 19 else 1)
    transition = world.events[-1]
    assert transition.kind == 'rank_advanced'
    assert transition.data['body_rank_after'] == 'bronze'
    assert len(transition.causes) == 20
    milestones = {e.id: e for e in world.events
                  if e.kind == 'ability_rank_advanced'
                  and any(a.kind == 'person' and a.id == p.id for a in e.actors)}
    assert set(transition.causes) == set(milestones)
    assert all(e.data['ability_rank_after'] == 'bronze' for e in milestones.values())
    restored = loads(dumps(world))
    assert restored.digest() == world.digest()
    archive = tmp_path / 'magic.sqlite'
    export_archive(restored, archive)
    with HistoryArchive(archive) as history:
        assert validate(history)['valid']
        recorded = history.event(transition.id)
        assert recorded['causes'] == list(transition.causes)
        assert len(history.record('path', p.id)['abilities']) == 20
        assert all(history.event(eid)['kind'] == 'ability_rank_advanced'
                   for eid in recorded['causes'])
