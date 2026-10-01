from ate_sim.engine import Simulation
from ate_sim.visual_compile import compile_settlement_visual_spec
from ate_sim.worldgen import generate_world


def test_compiler_uses_real_settlement_spatial_state():
    world = generate_world(843000)
    Simulation(world).run(5)
    spec = compile_settlement_visual_spec(world, 1)
    center_patch = next(
        patch
        for patch in world.settlement_space.terrain_patches.values()
        if patch.settlement == 1 and patch.grid_x == 0 and patch.grid_y == 0
    )

    assert spec.world_seed == world.seed
    assert spec.time_slice_year == 5
    assert spec.focus_position.x == 0
    assert spec.focus_position.y == 0
    assert spec.metadata["population"] == str(
        sum(1 for p in world.people.values() if p.alive and p.settlement == 1)
    )
    compiled_center = next(
        region
        for region in spec.terrain_regions
        if region.region_id == f"terrain-patch:{center_patch.id}"
    )
    assert compiled_center.elevation_band == (center_patch.elevation, center_patch.elevation)
    assert compiled_center.moisture == center_patch.moisture
    assert len(spec.parcels) > 0
    assert len(spec.buildings) > 0
    assert len(spec.roads) > 0


def test_compiler_matches_authoritative_parcel_and_structure_coordinates():
    world = generate_world(843000)
    Simulation(world).run(10)
    spec = compile_settlement_visual_spec(world, 1)

    parcel = next(p for p in world.settlement_space.parcels.values() if p.settlement == 1)
    compiled_parcel = next(p for p in spec.parcels if p.parcel_id == f"parcel:{parcel.id}")
    assert compiled_parcel.position.x == parcel.center_x_m
    assert compiled_parcel.position.y == parcel.center_y_m
    assert compiled_parcel.size_m == (parcel.width_m, parcel.depth_m)

    structure = next(s for s in world.settlement_space.structures.values() if s.settlement == 1)
    compiled_structure = next(b for b in spec.buildings if b.building_id == f"building:{structure.id}")
    assert compiled_structure.position.x == structure.center_x_m
    assert compiled_structure.position.y == structure.center_y_m
    assert compiled_structure.footprint_size_m == (structure.width_m, structure.depth_m)


def test_compiler_is_deterministic():
    first = generate_world(843000)
    second = generate_world(843000)
    Simulation(first).run(10)
    Simulation(second).run(10)

    a = compile_settlement_visual_spec(first, 1)
    b = compile_settlement_visual_spec(second, 1)

    assert a.canonical_json() == b.canonical_json()
    assert a.digest() == b.digest()



def test_compiler_exposes_real_local_terrain_layers():
    world = Simulation(generate_world(843000)).run(20)
    spec = compile_settlement_visual_spec(world, 1)

    patch_count = sum(
        1 for patch in world.settlement_space.terrain_patches.values()
        if patch.settlement == 1
    )
    field_count = sum(
        1 for field in world.settlement_space.fields.values()
        if field.settlement == 1 and field.active
    )
    assert len([r for r in spec.terrain_regions if r.region_id.startswith("terrain-patch:")]) == patch_count
    assert len([r for r in spec.terrain_regions if r.surface_kind == "field"]) == field_count
    assert len(spec.watercourses) == sum(
        1 for water in world.settlement_space.watercourses.values()
        if water.settlement == 1
    )
    assert spec.vegetation_zones
    assert int(spec.metadata["terrain_patches"]) == patch_count
    assert int(spec.metadata["fields"]) == field_count
