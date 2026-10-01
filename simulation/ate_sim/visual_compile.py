from __future__ import annotations

from .visual_spec import (
    BuildingPhaseSpec,
    BuildingSpec,
    ParcelSpec,
    Polyline,
    ProvenanceRef,
    RoadSpec,
    SettlementVisualSpec,
    TerrainRegionSpec,
    Vec3,
)


def _visual_seed(world_seed: int, settlement_id: int, year: int) -> int:
    return (
        (world_seed * 1315423911)
        ^ (settlement_id * 2654435761)
        ^ (year * 97531)
    ) & ((1 << 63) - 1)


def _prov(kind: str, ident: str, year: int | None, event_id: int | None) -> ProvenanceRef:
    return ProvenanceRef(
        source_kind=kind,
        source_id=ident,
        event_ids=(() if event_id is None else (str(event_id),)),
        source_year=year,
    )


def _wealth_band(world, structure) -> str:
    if structure.occupied_by_household is not None:
        household = world.households.get(structure.occupied_by_household)
        if household is not None:
            wealth = household.wealth
            if wealth >= 120:
                return "prosperous"
            if wealth >= 45:
                return "comfortable"
            return "modest"
    return "institutional" if "hall" in structure.kind else "unknown"


def _extent(world, sid):
    points = []
    for parcel in world.settlement_space.parcels.values():
        if parcel.settlement != sid or not parcel.active:
            continue
        points.extend(
            (
                parcel.center_x_m - parcel.width_m / 2,
                parcel.center_x_m + parcel.width_m / 2,
                parcel.center_y_m - parcel.depth_m / 2,
                parcel.center_y_m + parcel.depth_m / 2,
            )
        )
    for street in world.settlement_space.streets.values():
        if street.settlement != sid or not street.active:
            continue
        for x, y in street.points_m:
            points.extend((x, x, y, y))
    if not points:
        return 180.0
    return max(180.0, max(abs(value) for value in points) + 28.0)


def compile_settlement_visual_spec(world, settlement_id: int, radius_cells: int = 5) -> SettlementVisualSpec:
    """Compile the persistent local settlement layout now stored in Reality."""

    if settlement_id not in world.settlements:
        raise KeyError(f"unknown settlement {settlement_id}")

    settlement = world.settlements[settlement_id]
    cell = world.cells[(settlement.x, settlement.y)]
    extent = _extent(world, settlement_id)

    terrain = (
        TerrainRegionSpec(
            region_id=f"settlement-ground:{settlement_id}",
            boundary=(
                Vec3(-extent, -extent),
                Vec3(extent, -extent),
                Vec3(extent, extent),
                Vec3(-extent, extent),
            ),
            elevation_band=(cell.elevation, cell.elevation),
            soil_family="local_ground",
            moisture=cell.moisture,
            disturbance=None,
            provenance=_prov("worldgen_cell", f"{settlement.x},{settlement.y}", 0, None),
            surface_kind="land",
        ),
    )

    parcels = tuple(
        ParcelSpec(
            parcel_id=f"parcel:{parcel.id}",
            position=Vec3(parcel.center_x_m, parcel.center_y_m),
            facing_degrees=parcel.facing_degrees,
            size_m=(parcel.width_m, parcel.depth_m),
            land_use=parcel.kind,
            owner_kind=parcel.owner_kind,
            owner_id=None if parcel.owner_id is None else str(parcel.owner_id),
            provenance=_prov(
                "settlement_parcel",
                str(parcel.id),
                parcel.created_year,
                parcel.origin_event,
            ),
        )
        for parcel in sorted(world.settlement_space.parcels.values(), key=lambda p: p.id)
        if parcel.settlement == settlement_id and parcel.active
    )

    roads = tuple(
        RoadSpec(
            road_id=f"street:{street.id}",
            centerline=Polyline(tuple(Vec3(x, y) for x, y in street.points_m)),
            width_m=street.width_m,
            surface_family=street.surface_family,
            use_intensity={"main": 0.85, "cross": 0.68, "lane": 0.45}.get(street.kind, 0.4),
            condition=street.condition,
            provenance=_prov(
                "settlement_street",
                str(street.id),
                street.built_year,
                street.origin_event,
            ),
        )
        for street in sorted(world.settlement_space.streets.values(), key=lambda s: s.id)
        if street.settlement == settlement_id and street.active
    )

    buildings = []
    for structure in sorted(world.settlement_space.structures.values(), key=lambda s: s.id):
        if structure.settlement != settlement_id or not structure.active:
            continue
        provenance = _prov(
            "settlement_structure",
            str(structure.id),
            structure.built_year,
            structure.origin_event,
        )
        phase = BuildingPhaseSpec(
            phase_id=f"phase:{structure.id}:construction",
            year=structure.built_year,
            action="construct",
            material_families=(),
            provenance=provenance,
        )
        buildings.append(
            BuildingSpec(
                building_id=f"building:{structure.id}",
                parcel_id=f"parcel:{structure.parcel}",
                position=Vec3(structure.center_x_m, structure.center_y_m),
                facing_degrees=structure.facing_degrees,
                function=structure.kind,
                style_lineage_ids=(),
                wealth_band=_wealth_band(world, structure),
                maintenance=structure.condition,
                occupancy=("occupied" if structure.occupied_by_household is not None else "unoccupied"),
                phases=(phase,),
                provenance=provenance,
                footprint_size_m=(structure.width_m, structure.depth_m),
            )
        )

    living = [
        person
        for person in world.people.values()
        if person.alive and person.settlement == settlement_id
    ]
    local = world.local[settlement_id]
    ambient = world.ambient_magic.field(settlement_id)
    living_households = [
        household
        for household_id in settlement.households
        for household in [world.households[household_id]]
        if household.alive and any(world.people[pid].alive for pid in household.members)
    ]

    profile = world.settlement_space.site_profiles.get(settlement_id)
    metadata = {
        "ambient_magic": f"{ambient.level:.3f}",
        "buildings": str(len(buildings)),
        "defense": f"{settlement.defense:.3f}",
        "food_stock": f"{settlement.food_stock:.1f}",
        "households": str(len(living_households)),
        "irrigation": f"{settlement.irrigation:.3f}",
        "parcels": str(len(parcels)),
        "population": str(len(living)),
        "prosperity": f"{settlement.prosperity:.3f}",
        "rain": f"{local.rain:.3f}",
        "roads": str(len(roads)),
        "roads_index": f"{settlement.roads:.3f}",
        "scarcity": f"{local.scarcity:.3f}",
    }
    if profile is not None:
        metadata.update({
            "site_archetype": profile.archetype,
            "site_main_axis": f"{profile.main_angle_degrees:.1f} deg",
            "site_slope": f"{profile.slope_strength:.4f}",
            "site_moisture_gradient": f"{profile.moisture_gradient:.4f}",
            "site_forest_gradient": f"{profile.forest_gradient:.4f}",
            "growth_bias": f"{profile.growth_bias_degrees:.1f} deg",
        })

    return SettlementVisualSpec(
        settlement_id=f"settlement:{settlement_id}",
        world_seed=world.seed,
        visual_seed=_visual_seed(world.seed, settlement_id, world.year),
        time_slice_year=world.year,
        terrain_regions=terrain,
        parcels=parcels,
        roads=roads,
        buildings=tuple(buildings),
        vegetation_zones=(),
        population=(),
        weather=None,
        magic_manifestations=(),
        metadata=metadata,
        focus_position=Vec3(0, 0),
    )
