from __future__ import annotations

from .visual_spec import ProvenanceRef, SettlementVisualSpec, TerrainRegionSpec, Vec3


def _visual_seed(world_seed: int, settlement_id: int, year: int) -> int:
    return (
        (world_seed * 1315423911)
        ^ (settlement_id * 2654435761)
        ^ (year * 97531)
    ) & ((1 << 63) - 1)


def compile_settlement_visual_spec(world, settlement_id: int, radius_cells: int = 5) -> SettlementVisualSpec:
    """Compile only spatial facts that the current simulation actually knows.

    The current simulation tracks terrain cells and settlement centers, but it
    does not yet track within-settlement street geometry or building positions.
    Those layers are therefore intentionally absent rather than invented.
    """

    if settlement_id not in world.settlements:
        raise KeyError(f"unknown settlement {settlement_id}")
    if radius_cells < 0:
        raise ValueError("radius_cells must be non-negative")

    settlement = world.settlements[settlement_id]
    terrain = []

    min_x = settlement.x - radius_cells
    max_x = settlement.x + radius_cells
    min_y = settlement.y - radius_cells
    max_y = settlement.y + radius_cells

    for (x, y), cell in sorted(world.cells.items()):
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            continue
        terrain.append(
            TerrainRegionSpec(
                region_id=f"cell:{x},{y}",
                boundary=(
                    Vec3(x - 0.5, y - 0.5),
                    Vec3(x + 0.5, y - 0.5),
                    Vec3(x + 0.5, y + 0.5),
                    Vec3(x - 0.5, y + 0.5),
                ),
                elevation_band=(cell.elevation, cell.elevation),
                soil_family="unclassified",
                moisture=cell.moisture,
                disturbance=None,
                provenance=ProvenanceRef(
                    source_kind="worldgen_cell",
                    source_id=f"{x},{y}",
                    event_ids=(),
                    source_year=0,
                ),
                surface_kind="terrain",
            )
        )

    living = [
        person
        for person in world.people.values()
        if person.alive and person.settlement == settlement_id
    ]
    living_households = [
        household
        for household_id in settlement.households
        for household in [world.households[household_id]]
        if household.alive and any(world.people[pid].alive for pid in household.members)
    ]
    local = world.local[settlement_id]
    ambient = world.ambient_magic.field(settlement_id)
    center_cell = world.cells[(settlement.x, settlement.y)]

    metadata = {
        "ambient_magic": f"{ambient.level:.3f}",
        "defense": f"{settlement.defense:.3f}",
        "drought": f"{local.drought:.3f}",
        "elevation": f"{center_cell.elevation:.3f}",
        "fertility": f"{center_cell.fertility:.3f}",
        "flood": f"{local.flood:.3f}",
        "food_stock": f"{settlement.food_stock:.1f}",
        "forest": f"{center_cell.forest:.3f}",
        "hazard": f"{center_cell.hazard:.3f}",
        "households": str(len(living_households)),
        "irrigation": f"{settlement.irrigation:.3f}",
        "population": str(len(living)),
        "prosperity": f"{settlement.prosperity:.3f}",
        "rain": f"{local.rain:.3f}",
        "roads_index": f"{settlement.roads:.3f}",
        "scarcity": f"{local.scarcity:.3f}",
        "spatial_note": "roads/buildings omitted: current sim has no within-settlement geometry",
    }

    founded_events = [
        event
        for event in world.events
        if event.kind == "settlement_founded"
        and event.location is not None
        and event.location.kind == "settlement"
        and event.location.id == settlement_id
    ]
    if founded_events:
        metadata["founded_event"] = str(founded_events[0].id)

    return SettlementVisualSpec(
        settlement_id=f"settlement:{settlement_id}",
        world_seed=world.seed,
        visual_seed=_visual_seed(world.seed, settlement_id, world.year),
        time_slice_year=world.year,
        terrain_regions=tuple(terrain),
        roads=(),
        buildings=(),
        vegetation_zones=(),
        population=(),
        weather=None,
        magic_manifestations=(),
        metadata=metadata,
        focus_position=Vec3(settlement.x, settlement.y),
    )
