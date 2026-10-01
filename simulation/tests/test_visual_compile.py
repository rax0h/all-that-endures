from ate_sim.engine import Simulation
from ate_sim.visual_compile import compile_settlement_visual_spec
from ate_sim.worldgen import generate_world


def test_compiler_uses_real_terrain_and_settlement_state():
    world = generate_world(843000)
    Simulation(world).run(5)
    spec = compile_settlement_visual_spec(world, 1, radius_cells=2)
    settlement = world.settlements[1]
    center = world.cells[(settlement.x, settlement.y)]

    assert spec.world_seed == world.seed
    assert spec.time_slice_year == 5
    assert spec.focus_position.x == settlement.x
    assert spec.focus_position.y == settlement.y
    assert spec.metadata["population"] == str(
        sum(1 for p in world.people.values() if p.alive and p.settlement == 1)
    )
    center_region = next(
        region for region in spec.terrain_regions
        if region.region_id == f"cell:{settlement.x},{settlement.y}"
    )
    assert center_region.elevation_band == (center.elevation, center.elevation)
    assert center_region.moisture == center.moisture


def test_compiler_does_not_invent_spatial_roads_or_buildings():
    world = generate_world(843000)
    Simulation(world).run(10)
    spec = compile_settlement_visual_spec(world, 1)

    assert spec.roads == ()
    assert spec.buildings == ()
    assert "omitted" in spec.metadata["spatial_note"]


def test_compiler_is_deterministic():
    first = generate_world(843000)
    second = generate_world(843000)
    Simulation(first).run(10)
    Simulation(second).run(10)

    a = compile_settlement_visual_spec(first, 1)
    b = compile_settlement_visual_spec(second, 1)

    assert a.canonical_json() == b.canonical_json()
    assert a.digest() == b.digest()
