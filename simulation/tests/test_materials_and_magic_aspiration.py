from collections import Counter
from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation
from ate_sim.magic_resources import _aspiration,absorb_essence_resource
from ate_sim.semantic_dictionary import ESSENCES
from ate_sim.core import Layer,Ref


def test_material_crafting_consumes_real_produced_lots():
    w=generate_world(843000);Simulation(w).run(30)
    assert w.materials.lots
    for item in w.materials.items.values():
        assert item.materials
        for lid in item.materials:
            lot=w.materials.lots[lid]
            assert lot.origin_event in w.event_ids
            assert lot.consumed>0
            assert item.created_year>=lot.created_year


def test_material_production_is_not_fixed_one_lot_per_settlement_year():
    w=generate_world(843000);Simulation(w).run(40)
    produced=[e for e in w.events if e.kind=='material_produced']
    assert produced
    by_year_settlement=Counter((e.year,e.location.id) for e in produced if e.location is not None)
    assert any(count>1 for count in by_year_settlement.values())
    assert len(produced)!=40*len(w.settlements)


def test_magic_interest_is_not_universal_but_serious_aspirants_skew_to_completion():
    w=generate_world(843001);Simulation(w).run(40)
    aspirations=list(w.magic_resources.aspirations.values())
    assert aspirations
    assert any(a.desired_base_essences==0 for a in aspirations)
    interested=[a for a in aspirations if a.desired_base_essences>0]
    assert interested
    assert sum(a.completion_goal for a in interested)>len(interested)/2
    assert all(a.desired_base_essences==3 and a.desired_abilities==20 for a in interested if a.completion_goal)
    assert all(a.completion_goal for a in interested if a.adventurer_aspiration)


def test_absorbing_first_essence_can_turn_serious_interest_into_full_completion_goal():
    w=generate_world(843002);p=next(p for p in w.people.values() if p.alive and p.age>=18)
    a=_aspiration(w,p);a.drive=.6;a.completion_goal=False;a.desired_base_essences=1;a.desired_abilities=5
    found=w.emit('test_essence_found',Layer.REALITY,(Ref('person',p.id),),Ref('settlement',p.settlement),essence='fire')
    r=w.magic_resources.create('essence','fire',ESSENCES['fire']['rarity'],w.year,p.settlement,'person',p.id,found.id)
    absorb_essence_resource(w,p.id,r.id)
    assert a.completion_goal
    assert a.desired_base_essences==3
    assert a.desired_abilities==20


def test_transcendent_craft_cannot_be_randomly_rolled_by_mortal():
    w=generate_world(843002);Simulation(w).run(60)
    for item in w.materials.items.values():
        if item.rarity=='transcendent':
            assert w.metaphysics.soul(item.craftsperson).ontology!='mortal'
