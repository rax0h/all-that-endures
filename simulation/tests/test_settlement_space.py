from ate_sim.checkpoint import dumps, loads
from ate_sim.engine import Simulation
from ate_sim.worldgen import generate_world


def test_founder_households_have_authoritative_residences():
    world = generate_world(843000)

    for sid, settlement in world.settlements.items():
        living_households = [
            hid for hid in settlement.households
            if world.households[hid].alive
        ]
        assert living_households
        for hid in living_households:
            structure_id = world.settlement_space.household_residence.get(hid)
            assert structure_id is not None
            structure = world.settlement_space.structures[structure_id]
            assert structure.settlement == sid
            assert structure.occupied_by_household == hid
            parcel = world.settlement_space.parcels[structure.parcel]
            assert parcel.settlement == sid


def test_layout_is_persistent_across_checkpoint_resume():
    staged = Simulation(generate_world(843000)).run(10)
    restored = loads(dumps(staged))

    assert restored.settlement_space == staged.settlement_space

    direct = Simulation(generate_world(843000)).run(20)
    resumed = Simulation(restored).run(10)
    assert resumed.digest() == direct.digest()


def test_new_households_expand_persistent_spatial_state():
    world = generate_world(843000)
    initial_structures = len(world.settlement_space.structures)
    initial_parcels = len(world.settlement_space.parcels)

    Simulation(world).run(100)

    assert len(world.settlement_space.structures) >= initial_structures
    assert len(world.settlement_space.parcels) >= initial_parcels
    for hid, structure_id in world.settlement_space.household_residence.items():
        household = world.households.get(hid)
        structure = world.settlement_space.structures[structure_id]
        if household is not None and household.alive:
            assert structure.settlement == household.settlement
            assert structure.occupied_by_household == hid


def test_spatial_state_contains_real_streets_and_nonresidential_structures_after_history():
    world = Simulation(generate_world(843000)).run(100)

    assert any(street.active for street in world.settlement_space.streets.values())
    kinds = {structure.kind for structure in world.settlement_space.structures.values() if structure.active}
    assert "dwelling" in kinds or "leased_dwelling" in kinds
    # Repeated trade establishes a market in at least one settlement in the canonical seed.
    assert any(kind == "market_hall" for kind in kinds)
