from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .visual_spec import (
    BuildingPhaseSpec,
    BuildingSpec,
    MagicManifestationSpec,
    Polyline,
    PopulationRepresentationSpec,
    ProvenanceRef,
    RoadSpec,
    SCHEMA_VERSION,
    SettlementVisualSpec,
    TerrainRegionSpec,
    Vec3,
    VegetationZoneSpec,
    WeatherSpec,
)


def _prov(value: Mapping[str, Any] | None) -> ProvenanceRef | None:
    if value is None:
        return None
    return ProvenanceRef(
        source_kind=str(value["source_kind"]),
        source_id=str(value["source_id"]),
        event_ids=tuple(str(item) for item in value.get("event_ids", ())),
        source_year=value.get("source_year"),
    )


def _vec(value: Mapping[str, Any]) -> Vec3:
    return Vec3(float(value["x"]), float(value["y"]), float(value.get("z", 0.0)))


def visual_spec_from_dict(payload: Mapping[str, Any]) -> SettlementVisualSpec:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported visual specification schema version: {payload.get('schema_version')!r}"
        )

    terrain = tuple(
        TerrainRegionSpec(
            region_id=str(item["region_id"]),
            boundary=tuple(_vec(point) for point in item.get("boundary", ())),
            elevation_band=tuple(float(v) for v in item.get("elevation_band", (0.0, 0.0))),
            soil_family=str(item.get("soil_family", "unknown")),
            moisture=float(item.get("moisture", 0.0)),
            disturbance=(None if item.get("disturbance") is None else float(item.get("disturbance"))),
            provenance=_prov(item.get("provenance")),
            surface_kind=str(item.get("surface_kind", "land")),
        )
        for item in payload.get("terrain_regions", ())
    )

    roads = tuple(
        RoadSpec(
            road_id=str(item["road_id"]),
            centerline=Polyline(
                tuple(_vec(point) for point in item.get("centerline", {}).get("points", ()))
            ),
            width_m=float(item.get("width_m", 1.0)),
            surface_family=str(item.get("surface_family", "unknown")),
            use_intensity=float(item.get("use_intensity", 0.0)),
            condition=float(item.get("condition", 0.0)),
            provenance=_prov(item.get("provenance")),
        )
        for item in payload.get("roads", ())
    )

    buildings = []
    for item in payload.get("buildings", ()):
        phases = tuple(
            BuildingPhaseSpec(
                phase_id=str(phase["phase_id"]),
                year=int(phase["year"]),
                action=str(phase["action"]),
                footprint_scale=float(phase.get("footprint_scale", 1.0)),
                material_families=tuple(str(v) for v in phase.get("material_families", ())),
                damage_fraction=float(phase.get("damage_fraction", 0.0)),
                repair_fraction=float(phase.get("repair_fraction", 0.0)),
                provenance=_prov(phase.get("provenance")),
            )
            for phase in item.get("phases", ())
        )
        size = item.get("footprint_size_m", (8.0, 6.0))
        buildings.append(
            BuildingSpec(
                building_id=str(item["building_id"]),
                parcel_id=str(item.get("parcel_id", "")),
                position=_vec(item["position"]),
                facing_degrees=float(item.get("facing_degrees", 0.0)),
                function=str(item.get("function", "unknown")),
                style_lineage_ids=tuple(str(v) for v in item.get("style_lineage_ids", ())),
                wealth_band=str(item.get("wealth_band", "unknown")),
                maintenance=float(item.get("maintenance", 0.0)),
                occupancy=str(item.get("occupancy", "unknown")),
                phases=phases,
                provenance=_prov(item.get("provenance")),
                footprint_size_m=(float(size[0]), float(size[1])),
            )
        )

    vegetation = tuple(
        VegetationZoneSpec(
            zone_id=str(item["zone_id"]),
            boundary=tuple(_vec(point) for point in item.get("boundary", ())),
            community_family=str(item.get("community_family", "unknown")),
            density=float(item.get("density", 0.0)),
            maturity=float(item.get("maturity", 0.0)),
            disturbance=float(item.get("disturbance", 0.0)),
            provenance=_prov(item.get("provenance")),
        )
        for item in payload.get("vegetation_zones", ())
    )

    population = tuple(
        PopulationRepresentationSpec(
            person_id=str(item["person_id"]),
            position=_vec(item["position"]),
            representation_tier=str(item.get("representation_tier", "marker")),
            species_id=str(item.get("species_id", "unknown")),
            age_years=float(item.get("age_years", 0.0)),
            occupation_id=item.get("occupation_id"),
            culture_ids=tuple(str(v) for v in item.get("culture_ids", ())),
            wealth_band=str(item.get("wealth_band", "unknown")),
            rank_id=item.get("rank_id"),
            injury_markers=tuple(str(v) for v in item.get("injury_markers", ())),
            appearance_seed=int(item.get("appearance_seed", 0)),
            provenance=_prov(item.get("provenance")),
        )
        for item in payload.get("population", ())
    )

    weather_value = payload.get("weather")
    weather = None
    if weather_value is not None:
        weather = WeatherSpec(
            condition=str(weather_value.get("condition", "clear")),
            cloud_fraction=float(weather_value.get("cloud_fraction", 0.0)),
            precipitation=float(weather_value.get("precipitation", 0.0)),
            wind_mps=float(weather_value.get("wind_mps", 0.0)),
            visibility_km=float(weather_value.get("visibility_km", 20.0)),
            surface_wetness=float(weather_value.get("surface_wetness", 0.0)),
            provenance=_prov(weather_value.get("provenance")),
        )

    magic = tuple(
        MagicManifestationSpec(
            manifestation_id=str(item["manifestation_id"]),
            position=_vec(item["position"]),
            phenomenon_family=str(item.get("phenomenon_family", "unknown")),
            intensity=float(item.get("intensity", 0.0)),
            radius_m=float(item.get("radius_m", 0.0)),
            persistent=bool(item.get("persistent", False)),
            provenance=_prov(item.get("provenance")),
        )
        for item in payload.get("magic_manifestations", ())
    )

    return SettlementVisualSpec(
        settlement_id=str(payload["settlement_id"]),
        world_seed=int(payload["world_seed"]),
        visual_seed=int(payload["visual_seed"]),
        time_slice_year=int(payload["time_slice_year"]),
        terrain_regions=terrain,
        roads=roads,
        buildings=tuple(buildings),
        vegetation_zones=vegetation,
        population=population,
        weather=weather,
        magic_manifestations=magic,
        metadata={str(k): str(v) for k, v in payload.get("metadata", {}).items()},
        focus_position=(_vec(payload["focus_position"]) if payload.get("focus_position") is not None else None),
        schema_version=str(payload["schema_version"]),
    )


def load_visual_spec(path: str | Path) -> SettlementVisualSpec:
    with Path(path).open("r", encoding="utf-8") as handle:
        return visual_spec_from_dict(json.load(handle))


def save_visual_spec(spec: SettlementVisualSpec, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(spec.canonical_json() + "\n", encoding="utf-8")
