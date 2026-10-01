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



def test_different_world_seeds_produce_different_site_plans():
    first = generate_world(843000)
    second = generate_world(843001)

    profile_a = first.settlement_space.site_profiles[1]
    profile_b = second.settlement_space.site_profiles[1]
    plan_a = (
        profile_a.archetype,
        round(profile_a.main_angle_degrees, 4),
        round(profile_a.curvature_m, 4),
        tuple(
            (round(p.center_x_m, 3), round(p.center_y_m, 3))
            for p in sorted(first.settlement_space.parcels.values(), key=lambda p: p.id)
            if p.settlement == 1
        ),
    )
    plan_b = (
        profile_b.archetype,
        round(profile_b.main_angle_degrees, 4),
        round(profile_b.curvature_m, 4),
        tuple(
            (round(p.center_x_m, 3), round(p.center_y_m, 3))
            for p in sorted(second.settlement_space.parcels.values(), key=lambda p: p.id)
            if p.settlement == 1
        ),
    )

    assert plan_a != plan_b


def test_physical_intersettlement_roads_create_local_gateways():
    world = Simulation(generate_world(843000)).run(100)

    physical = [
        asset
        for asset in world.infrastructure.assets.values()
        if asset.kind == "road" and len(asset.settlements) == 2
    ]
    assert physical
    for asset in physical:
        a, b = asset.settlements
        assert (a, f"gateway:{b}") in world.settlement_space.street_ids
        assert (b, f"gateway:{a}") in world.settlement_space.street_ids



def test_local_terrain_is_authoritative_and_persistent():
    world = generate_world(843000)

    patches = [
        patch
        for patch in world.settlement_space.terrain_patches.values()
        if patch.settlement == 1
    ]
    assert len(patches) == 19 * 19
    assert all(0.0 <= patch.elevation <= 1.0 for patch in patches)
    assert all(0.0 <= patch.moisture <= 1.0 for patch in patches)
    assert all(0.0 <= patch.fertility <= 1.0 for patch in patches)
    assert all(0.0 <= patch.forest <= 1.0 for patch in patches)
    assert {patch.surface_kind for patch in patches} <= {"land", "wetland", "rock"}

    restored = loads(dumps(world))
    assert restored.settlement_space.terrain_patches == world.settlement_space.terrain_patches


def test_founder_fields_are_real_land_use_with_provenance():
    world = generate_world(843000)

    fields = [
        field
        for field in world.settlement_space.fields.values()
        if field.settlement == 1 and field.active
    ]
    assert fields
    for field in fields:
        patch = world.settlement_space.terrain_patches[field.terrain_patch]
        assert patch.settlement == 1
        assert field.origin_event in world.event_ids
        event = next(e for e in world.events if e.id == field.origin_event)
        assert event.kind == "field_cleared"


def test_fields_can_expand_with_settlement_history():
    world = generate_world(843000)
    before = sum(
        1 for field in world.settlement_space.fields.values()
        if field.settlement == 1 and field.active
    )

    Simulation(world).run(100)

    after = sum(
        1 for field in world.settlement_space.fields.values()
        if field.settlement == 1 and field.active
    )
    assert after >= before


def test_local_hydrology_is_seeded_from_site_conditions():
    world = generate_world(843000)

    assert world.settlement_space.watercourses
    for water in world.settlement_space.watercourses.values():
        assert water.width_m > 0
        assert len(water.points_m) >= 2
        assert water.kind in {"river", "stream", "seasonal_drainage"}
