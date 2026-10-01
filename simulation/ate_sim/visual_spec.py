from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "ate.visual-spec.v0"


@dataclass(frozen=True)
class ProvenanceRef:
    """Causal source for a visible fact.

    The visual layer may choose how to render a fact, but it must be able to
    identify the simulation/history state that authorized the fact to exist.
    """

    source_kind: str
    source_id: str
    event_ids: tuple[str, ...] = ()
    source_year: int | None = None


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class Polyline:
    points: tuple[Vec3, ...]


@dataclass(frozen=True)
class TerrainRegionSpec:
    region_id: str
    boundary: tuple[Vec3, ...]
    elevation_band: tuple[float, float]
    soil_family: str
    moisture: float
    disturbance: float
    provenance: ProvenanceRef


@dataclass(frozen=True)
class RoadSpec:
    road_id: str
    centerline: Polyline
    width_m: float
    surface_family: str
    use_intensity: float
    condition: float
    provenance: ProvenanceRef


@dataclass(frozen=True)
class BuildingPhaseSpec:
    phase_id: str
    year: int
    action: str
    footprint_scale: float = 1.0
    material_families: tuple[str, ...] = ()
    damage_fraction: float = 0.0
    repair_fraction: float = 0.0
    provenance: ProvenanceRef | None = None


@dataclass(frozen=True)
class BuildingSpec:
    building_id: str
    parcel_id: str
    position: Vec3
    facing_degrees: float
    function: str
    style_lineage_ids: tuple[str, ...]
    wealth_band: str
    maintenance: float
    occupancy: str
    phases: tuple[BuildingPhaseSpec, ...]
    provenance: ProvenanceRef


@dataclass(frozen=True)
class VegetationZoneSpec:
    zone_id: str
    boundary: tuple[Vec3, ...]
    community_family: str
    density: float
    maturity: float
    disturbance: float
    provenance: ProvenanceRef


@dataclass(frozen=True)
class PopulationRepresentationSpec:
    person_id: str
    position: Vec3
    representation_tier: str
    species_id: str
    age_years: float
    occupation_id: str | None
    culture_ids: tuple[str, ...]
    wealth_band: str
    rank_id: str | None
    injury_markers: tuple[str, ...] = ()
    appearance_seed: int = 0
    provenance: ProvenanceRef | None = None


@dataclass(frozen=True)
class WeatherSpec:
    condition: str
    cloud_fraction: float
    precipitation: float
    wind_mps: float
    visibility_km: float
    surface_wetness: float
    provenance: ProvenanceRef


@dataclass(frozen=True)
class MagicManifestationSpec:
    manifestation_id: str
    position: Vec3
    phenomenon_family: str
    intensity: float
    radius_m: float
    persistent: bool
    provenance: ProvenanceRef


@dataclass(frozen=True)
class SettlementVisualSpec:
    """Renderer-independent visual truth for one settlement and time slice."""

    settlement_id: str
    world_seed: int
    visual_seed: int
    time_slice_year: int
    terrain_regions: tuple[TerrainRegionSpec, ...] = ()
    roads: tuple[RoadSpec, ...] = ()
    buildings: tuple[BuildingSpec, ...] = ()
    vegetation_zones: tuple[VegetationZoneSpec, ...] = ()
    population: tuple[PopulationRepresentationSpec, ...] = ()
    weather: WeatherSpec | None = None
    magic_manifestations: tuple[MagicManifestationSpec, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = _primitive(asdict(self))
        _validate_payload(payload)
        return payload

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _primitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _primitive(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_primitive(item) for item in value]
    if isinstance(value, list):
        return [_primitive(item) for item in value]
    return value


def _validate_payload(payload: Mapping[str, Any]) -> None:
    """Enforce a small constitutional boundary at serialization time."""

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported visual specification schema version")

    forbidden_key_fragments = (
        "asset_path",
        "asset_file",
        "mesh_file",
        "material_file",
        "unreal_path",
        "blueprint_path",
    )
    forbidden_value_fragments = ("/Game/", "\\Content\\", ".uasset")

    def walk(value: Any, path: str = "root") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in forbidden_key_fragments):
                    raise ValueError(f"renderer-specific key at {path}.{key}")
                walk(child, f"{path}.{key}")
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str):
            if any(fragment in value for fragment in forbidden_value_fragments):
                raise ValueError(f"renderer-specific asset reference at {path}")

    walk(payload)


def require_major_provenance(spec: SettlementVisualSpec) -> None:
    """Fail when major realized facts cannot explain why they exist."""

    missing: list[str] = []

    for region in spec.terrain_regions:
        if region.provenance is None:
            missing.append(f"terrain:{region.region_id}")
    for road in spec.roads:
        if road.provenance is None:
            missing.append(f"road:{road.road_id}")
    for building in spec.buildings:
        if building.provenance is None:
            missing.append(f"building:{building.building_id}")
        for phase in building.phases:
            if phase.provenance is None:
                missing.append(f"building_phase:{building.building_id}:{phase.phase_id}")
    for zone in spec.vegetation_zones:
        if zone.provenance is None:
            missing.append(f"vegetation:{zone.zone_id}")
    for manifestation in spec.magic_manifestations:
        if manifestation.provenance is None:
            missing.append(f"magic:{manifestation.manifestation_id}")
    if spec.weather is not None and spec.weather.provenance is None:
        missing.append("weather")

    if missing:
        raise ValueError("missing visual provenance: " + ", ".join(missing))
