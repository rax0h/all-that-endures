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
    VegetationZoneSpec,
    WatercourseSpec,
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


def _square_boundary(x: float, y: float, size: float) -> tuple[Vec3, ...]:
    half = size / 2.0
    return (
        Vec3(x - half, y - half),
        Vec3(x + half, y - half),
        Vec3(x + half, y + half),
        Vec3(x - half, y + half),
    )


def _rotated_boundary(
    x: float,
    y: float,
    width: float,
    depth: float,
    degrees: float,
) -> tuple[Vec3, ...]:
    import math

    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    points = []
    for lx, ly in (
        (-width / 2, -depth / 2),
        (width / 2, -depth / 2),
        (width / 2, depth / 2),
        (-width / 2, depth / 2),
    ):
        points.append(Vec3(x + lx * c - ly * s, y + lx * s + ly * c))
    return tuple(points)


def compile_settlement_visual_spec(world, settlement_id: int, radius_cells: int = 5) -> SettlementVisualSpec:
    """Compile persistent settlement geography and built state from Reality."""

    if settlement_id not in world.settlements:
        raise KeyError(f"unknown settlement {settlement_id}")

    state = world.settlement_space
    settlement = world.settlements[settlement_id]

    field_patch_ids = {
        field.terrain_patch
        for field in state.fields.values()
        if field.settlement == settlement_id and field.active
    }

    terrain = []
    vegetation = []
    for patch in sorted(state.terrain_patches.values(), key=lambda p: p.id):
        if patch.settlement != settlement_id:
            continue
        terrain.append(
            TerrainRegionSpec(
                region_id=f"terrain-patch:{patch.id}",
                boundary=_square_boundary(
                    patch.center_x_m,
                    patch.center_y_m,
                    patch.size_m,
                ),
                elevation_band=(patch.elevation, patch.elevation),
                soil_family="local_ground",
                moisture=patch.moisture,
                disturbance=1.0 - patch.usable_score,
                provenance=_prov(
                    "local_terrain_patch",
                    str(patch.id),
                    0,
                    None,
                ),
                surface_kind=patch.surface_kind,
            )
        )
        if patch.forest >= 0.38 and patch.id not in field_patch_ids:
            vegetation.append(
                VegetationZoneSpec(
                    zone_id=f"forest-patch:{patch.id}",
                    boundary=_square_boundary(
                        patch.center_x_m,
                        patch.center_y_m,
                        patch.size_m,
                    ),
                    community_family=(
                        "riparian_woodland"
                        if patch.moisture >= 0.72
                        else "local_woodland"
                    ),
                    density=patch.forest,
                    maturity=min(1.0, 0.35 + patch.forest * 0.58),
                    disturbance=max(0.0, 0.25 - patch.usable_score * 0.12),
                    provenance=_prov(
                        "local_terrain_patch",
                        str(patch.id),
                        0,
                        None,
                    ),
                )
            )

    # Cultivation is a historical overlay on the generated terrain rather than a
    # renderer decoration. Each field points back to the field-clearing event.
    for field in sorted(state.fields.values(), key=lambda f: f.id):
        if field.settlement != settlement_id or not field.active:
            continue
        patch = state.terrain_patches[field.terrain_patch]
        terrain.append(
            TerrainRegionSpec(
                region_id=f"field:{field.id}",
                boundary=_rotated_boundary(
                    field.center_x_m,
                    field.center_y_m,
                    field.width_m,
                    field.depth_m,
                    field.facing_degrees,
                ),
                elevation_band=(patch.elevation, patch.elevation),
                soil_family="cultivated",
                moisture=patch.moisture,
                disturbance=0.72,
                provenance=_prov(
                    "field_plot",
                    str(field.id),
                    field.created_year,
                    field.origin_event,
                ),
                surface_kind="field",
            )
        )

    watercourses = tuple(
        WatercourseSpec(
            watercourse_id=f"watercourse:{water.id}",
            centerline=Polyline(tuple(Vec3(x, y) for x, y in water.points_m)),
            width_m=water.width_m,
            kind=water.kind,
            perennial=water.perennial,
            provenance=_prov(
                "local_watercourse",
                str(water.id),
                0,
                water.origin_event,
            ),
        )
        for water in sorted(state.watercourses.values(), key=lambda w: w.id)
        if water.settlement == settlement_id
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
        for parcel in sorted(state.parcels.values(), key=lambda p: p.id)
        if parcel.settlement == settlement_id and parcel.active
    )

    roads = tuple(
        RoadSpec(
            road_id=f"street:{street.id}",
            centerline=Polyline(tuple(Vec3(x, y) for x, y in street.points_m)),
            width_m=street.width_m,
            surface_family=street.surface_family,
            use_intensity={
                "main": 0.85,
                "cross": 0.68,
                "lane": 0.45,
                "gateway": 0.78,
                "growth_lane": 0.38,
            }.get(street.kind, 0.4),
            condition=street.condition,
            provenance=_prov(
                "settlement_street",
                str(street.id),
                street.built_year,
                street.origin_event,
            ),
        )
        for street in sorted(state.streets.values(), key=lambda s: s.id)
        if street.settlement == settlement_id and street.active
    )

    buildings = []
    for structure in sorted(state.structures.values(), key=lambda s: s.id):
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
                occupancy=(
                    "occupied"
                    if structure.occupied_by_household is not None
                    else "unoccupied"
                ),
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
        if household.alive
        and any(world.people[pid].alive for pid in household.members)
    ]

    profile = state.site_profiles.get(settlement_id)
    local_patches = [
        patch for patch in state.terrain_patches.values()
        if patch.settlement == settlement_id
    ]
    metadata = {
        "ambient_magic": f"{ambient.level:.3f}",
        "buildings": str(len(buildings)),
        "defense": f"{settlement.defense:.3f}",
        "fields": str(sum(1 for f in state.fields.values() if f.settlement == settlement_id and f.active)),
        "food_stock": f"{settlement.food_stock:.1f}",
        "forest_cover": (
            f"{sum(p.forest for p in local_patches) / len(local_patches):.3f}"
            if local_patches else "0.000"
        ),
        "households": str(len(living_households)),
        "irrigation": f"{settlement.irrigation:.3f}",
        "parcels": str(len(parcels)),
        "population": str(len(living)),
        "prosperity": f"{settlement.prosperity:.3f}",
        "rain": f"{local.rain:.3f}",
        "roads": str(len(roads)),
        "scarcity": f"{local.scarcity:.3f}",
        "terrain_patches": str(len(local_patches)),
        "watercourses": str(len(watercourses)),
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
        terrain_regions=tuple(terrain),
        parcels=parcels,
        watercourses=watercourses,
        roads=roads,
        buildings=tuple(buildings),
        vegetation_zones=tuple(vegetation),
        population=(),
        weather=None,
        magic_manifestations=(),
        metadata=metadata,
        focus_position=Vec3(0, 0),
    )
