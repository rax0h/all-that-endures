from ate_sim import generate_world
from ate_sim.magic_economy import apprenticeship_step


def test_society_forms_real_annual_cadet_cohorts_and_only_graduates_20_20():
    world=generate_world(843000)
    adventure=world.institutions.institution_by_kind('adventure_society')
    before=set(adventure.members)
    world.year=1
    apprenticeship_step(world)
    aspirations=list(world.magic_resources.aspirations.values())
    admitted=[a for a in aspirations if a.cadet_class_year==1]
    assert admitted
    assert any(e.kind=='society_cadet_class_formed' and e.year==1 for e in world.events)
    graduates=[pid for pid,a in world.magic_resources.aspirations.items() if a.cadet_graduated_year==1]
    assert all(world.advancement.completed_path(pid) and pid in adventure.members for pid in graduates)
    assert all(world.advancement.completed_path(pid) for pid in adventure.members-before)


def test_cadet_resource_issues_are_real_transfers_and_remote_stock_is_allowed():
    world=generate_world(843001);adventure=world.institutions.institution_by_kind('adventure_society')
    world.year=1;apprenticeship_step(world)
    issues=[e for e in world.events if e.kind=='society_cadet_resource_issued' and e.year==1]
    assert issues
    for e in issues:
        resource=world.magic_resources.resources[e.data['resource']]
        assert resource.consumed_year==1 and resource.consumed_by==e.actors[0].id
        if e.data['remote_order']:
            assert e.data['delivery_days']==14 and e.data['source_settlement']!=e.data['destination_settlement']
