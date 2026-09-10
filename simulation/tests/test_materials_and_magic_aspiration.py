from ate_sim.worldgen import generate_world
from ate_sim.engine import Simulation


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


def test_magic_aspiration_is_not_universal_and_can_stop_short_of_full_configuration():
    w=generate_world(843001);Simulation(w).run(40)
    aspirations=list(w.magic_resources.aspirations.values())
    assert aspirations
    assert any(a.desired_base_essences==0 for a in aspirations)
    assert any(a.desired_base_essences in (1,2) for a in aspirations)
    assert any(a.desired_base_essences==3 for a in aspirations)


def test_transcendent_craft_cannot_be_randomly_rolled_by_mortal():
    w=generate_world(843002);Simulation(w).run(60)
    for item in w.materials.items.values():
        if item.rarity=='transcendent':
            assert w.metaphysics.soul(item.craftsperson).ontology!='mortal'
