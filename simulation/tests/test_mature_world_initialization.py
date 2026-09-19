from ate_sim import generate_world


def test_year_zero_is_mature_magical_observation_boundary():
    world=generate_world(843000)
    adults=[p for p in world.current_people() if p.age>=18]
    users=[p for p in adults if world.advancement.essence_user(p.id)]
    complete=[p for p in adults if world.advancement.completed_path(p.id)]
    assert len(users)/len(adults)>=.60
    assert complete
    assert all(p.rank>=1 for p in complete)
    assert all(world.advancement.completed_path(p.id) for p in adults if p.rank>=1)
    assert any(e.kind=='preexisting_rank_observed' for e in world.events)
    assert all(e.data.get('observation_boundary') for e in world.events if e.kind=='preexisting_rank_observed')


def test_core_societies_begin_with_real_qualified_continuity():
    world=generate_world(843000)
    adventure=world.institutions.institution_by_kind('adventure_society')
    magic=world.institutions.institution_by_kind('magic_society')
    assert adventure is not None and magic is not None
    assert len(adventure.branches)==len(world.settlements)
    assert len(magic.branches)==len(world.settlements)
    assert adventure.members and magic.members
    assert all(world.advancement.completed_path(pid) for pid in adventure.members|magic.members)
    for sid in world.settlements:
        branch=world.institutions.branch_for('adventure_society',sid)
        assert branch is not None
        assert any(world.people[pid].settlement==sid for pid in adventure.members)
