import pytest

from ate_sim.worldgen import generate_world
from ate_sim.core import RNG
from ate_sim.currency import RankedCurrencyState,value_of
from ate_sim.checkpoint import dumps,loads
from ate_sim.magic_resources import _ordinary_manifestations,_aspiration,ORDINARY_ESSENCE_IDS
from ate_sim.magic_economy import apprenticeship_step


def test_mature_boundary_ranked_people_are_complete_and_legal():
    world=generate_world(117)
    assert hasattr(world,'health')
    ranked=[p for p in world.current_people() if p.rank>=1]
    assert ranked
    for person in ranked:
        path=world.advancement.path(person.id)
        assert path is not None
        assert len(path.base_essences)==3
        assert path.confluence is not None
        assert len(path.abilities)==20
        assert all(sum(a.essence==essence for a in path.abilities)==5 for essence in path.essences)
        assert world.advancement.rank(person.id)==person.rank


def test_runtime_view_is_rebuildable_after_age_sensitive_change():
    world=generate_world(118)
    person=min(world.current_people(),key=lambda p:p.id)
    with world.current_people_scope():
        before=world.runtime_view()
        person.age=17
        world.invalidate_runtime()
        assert person not in world.runtime_view().adults18_by_settlement[person.settlement]
        person.age=18
        world.invalidate_runtime()
        after=world.runtime_view()
        assert after is not before
        assert person in after.adults18_by_settlement[person.settlement]


def test_treasury_change_has_real_counterparty_and_conserves_value():
    currency=RankedCurrencyState()
    currency.treasuries[1]={'bronze':1}
    currency.wallets[7]={'iron':10}
    before=value_of(currency.treasuries[1])+value_of(currency.wallets[7])
    result=currency.treasury_exchange(1,7,{'bronze':1},{'iron':10})
    assert result=={'treasury_gives':{'bronze':1},'person_gives':{'iron':10}}
    assert currency.treasuries[1].get('bronze',0)==0
    assert currency.treasuries[1]['iron']==10
    assert currency.wallets[7]['bronze']==1
    assert currency.wallets[7].get('iron',0)==0
    assert value_of(currency.treasuries[1])+value_of(currency.wallets[7])==before
    with pytest.raises(ValueError):
        currency.treasury_exchange(1,7,{'iron':1},{'lesser':1})


def test_checkpoint_drops_runtime_caches_without_changing_digest():
    world=generate_world(119)
    pid=min(world.people)
    with world.current_people_scope():
        world.runtime_view()
        world.social.max_attachment(pid)
        world.infrastructure.route_condition(1,2)
        world.institutions.institution_by_kind('adventure_society')
        assert '_runtime_view' in world.__dict__
    digest=world.digest()
    restored=loads(dumps(world))
    assert restored.digest()==digest
    assert '_runtime_view' not in restored.__dict__
    assert '_attachment_max' not in restored.social.__dict__
    assert '_kind_index' not in restored.institutions.__dict__
    assert '_route_index' not in restored.infrastructure.__dict__


def test_ordinary_manifestations_create_physical_settlement_stock():
    world=generate_world(120)
    sid=min(world.settlements)
    people=[p for p in world.current_people() if p.settlement==sid and p.age>=16]
    before={r.id for r in world.magic_resources.inventory('settlement',sid,'essence')}
    created=_ordinary_manifestations(world,RNG(world.seed),sid,people)
    after=[r for r in world.magic_resources.inventory('settlement',sid,'essence') if r.id not in before]
    assert created==len(after)
    assert created>0
    assert all(r.owner_kind=='settlement' and r.owner_id==sid for r in after)
    assert all(r.key in ORDINARY_ESSENCE_IDS for r in after)


def test_cadet_pipeline_uses_real_resources_and_only_graduates_legal_iron():
    world=generate_world(121)
    adventure=world.institutions.institution_by_kind('adventure_society')
    candidate=next(p for p in world.current_people() if p.age>=16 and p.id not in adventure.members)
    candidate.curiosity=1.;candidate.inhibition=0.;candidate.occupation='guard'
    world.skills.practice(candidate.id,'defense',3.)
    aspiration=_aspiration(world,candidate)
    aspiration.drive=1.;aspiration.preparation=1.;aspiration.risk_tolerance=1.;aspiration.adventurer_aspiration=True
    world.year=1
    apprenticeship_step(world)
    cohorts=[c for c in world.institutions.cadet_cohorts.values() if candidate.id in c.cadets]
    assert cohorts
    issued=[e for e in world.events if e.kind=='society_cadet_resource_issued']
    assert issued
    for event in issued:
        resource=world.magic_resources.resources[event.data['resource']]
        assert resource.origin_event is not None
        assert resource.consumed_event is not None or resource.owner_kind=='person'
    for cohort in world.institutions.cadet_cohorts.values():
        for pid in cohort.graduates:
            path=world.advancement.path(pid)
            assert path is not None and len(path.abilities)==20
            assert world.advancement.rank(pid)>=1
            assert pid in adventure.members
