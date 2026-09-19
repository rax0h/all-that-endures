from ate_sim import generate_world
from ate_sim.magic_resources import society_resource_step


def test_society_resource_step_creates_only_physical_demand_bounded_reserve():
    world=generate_world(843002);adventure=world.institutions.institution_by_kind('adventure_society')
    # Force one incomplete cadet and empty the opening institutional reserve.
    candidate=next(p for p in world.current_people() if p.age>=16 and not world.advancement.completed_path(p.id))
    from ate_sim.magic_resources import _aspiration
    a=_aspiration(world,candidate);a.cadet_class_year=0;a.cadet_branch=world.institutions.branch_for('adventure_society',candidate.settlement).id
    a.adventurer_aspiration=True;a.completion_goal=True;a.desired_base_essences=3;a.desired_abilities=20
    for r in list(world.magic_resources.inventory('institution',adventure.id)):
        world.magic_resources._index_remove(r);r.owner_kind='settlement';r.owner_id=r.location;world.magic_resources._index_add(r)
    world.year=1;society_resource_step(world,world.__class__.__module__ and __import__('ate_sim.core',fromlist=['RNG']).RNG(world.seed))
    reserve=world.magic_resources.inventory('institution',adventure.id)
    assert reserve
    assert all(r.origin_event in world.event_ids for r in reserve)
    recovered=[e for e in world.events if e.kind=='magical_expedition_resource_recovered' and e.year==1]
    assert recovered and all(e.data['custody']=='institution' for e in recovered)
