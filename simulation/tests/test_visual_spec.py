import json

import pytest

from ate_sim.visual_spec import (
    BuildingPhaseSpec,
    BuildingSpec,
    MagicManifestationSpec,
    Polyline,
    ProvenanceRef,
    RoadSpec,
    SettlementVisualSpec,
    TerrainRegionSpec,
    Vec3,
    VegetationZoneSpec,
    WeatherSpec,
    require_major_provenance,
)


def _prov(kind: str, ident: str, year: int = 100) -> ProvenanceRef:
    return ProvenanceRef(kind, ident, (f"event:{ident}",), year)


def _fixture(metadata=None) -> SettlementVisualSpec:
    return SettlementVisualSpec(
        settlement_id="settlement:7",
        world_seed=843000,
        visual_seed=991,
        time_slice_year=240,
        terrain_regions=(
            TerrainRegionSpec(
                "terrain:bank",
                (Vec3(0, 0), Vec3(20, 0), Vec3(20, 20), Vec3(0, 20)),
                (0.12, 0.28),
                "alluvial_loam",
                0.74,
                0.18,
                _prov("terrain_region", "bank", 0),
            ),
        ),
        roads=(
            RoadSpec(
                "road:market",
                Polyline((Vec3(1, 8), Vec3(9, 9), Vec3(18, 12))),
                3.4,
                "compacted_gravel",
                0.82,
                0.61,
                _prov("road", "market", 88),
            ),
        ),
        buildings=(
            BuildingSpec(
                "building:smithy",
                "parcel:12",
                Vec3(8, 10),
                173.0,
                "smithy",
                ("style:river-founders", "style:iron-quarter"),
                "comfortable",
                0.72,
                "occupied",
                (
                    BuildingPhaseSpec(
                        "phase:foundation",
                        102,
                        "construct",
                        material_families=("local_stone", "oak"),
                        provenance=_prov("construction_event", "smithy-foundation", 102),
                    ),
                    BuildingPhaseSpec(
                        "phase:fire-repair",
                        219,
                        "repair",
                        damage_fraction=0.35,
                        repair_fraction=0.31,
                        material_families=("imported_slate", "oak"),
                        provenance=_prov("repair_event", "smithy-fire-repair", 219),
                    ),
                ),
                _prov("building", "smithy", 102),
            ),
        ),
        vegetation_zones=(
            VegetationZoneSpec(
                "vegetation:riparian",
                (Vec3(0, 0), Vec3(20, 0), Vec3(20, 5), Vec3(0, 5)),
                "temperate_riparian",
                0.78,
                0.64,
                0.12,
                _prov("ecology_state", "riparian", 240),
            ),
        ),
        weather=WeatherSpec(
            "light_rain",
            0.81,
            0.34,
            5.2,
            8.0,
            0.67,
            _prov("weather_state", "rain-240", 240),
        ),
        magic_manifestations=(
            MagicManifestationSpec(
                "magic:ward-3",
                Vec3(8.5, 10.2, 1.3),
                "persistent_ward",
                0.42,
                2.5,
                True,
                _prov("magic_effect", "ward-3", 237),
            ),
        ),
        metadata=metadata or {"scenario": "prosperity_after_fire"},
    )


def test_visual_spec_is_deterministic_and_canonical():
    first = _fixture({"z": "last", "a": "first"})
    second = _fixture({"a": "first", "z": "last"})

    assert first.canonical_json() == second.canonical_json()
    assert first.digest() == second.digest()
    assert json.loads(first.canonical_json())["schema_version"] == "ate.visual-spec.v0"


def test_major_visual_facts_have_provenance():
    spec = _fixture()
    require_major_provenance(spec)


def test_building_phase_without_provenance_is_rejected_by_provenance_gate():
    spec = _fixture()
    building = spec.buildings[0]
    broken_phase = BuildingPhaseSpec(
        "phase:unknown",
        230,
        "repair",
        provenance=None,
    )
    broken_building = BuildingSpec(
        building.building_id,
        building.parcel_id,
        building.position,
        building.facing_degrees,
        building.function,
        building.style_lineage_ids,
        building.wealth_band,
        building.maintenance,
        building.occupancy,
        building.phases + (broken_phase,),
        building.provenance,
    )
    broken = SettlementVisualSpec(
        settlement_id=spec.settlement_id,
        world_seed=spec.world_seed,
        visual_seed=spec.visual_seed,
        time_slice_year=spec.time_slice_year,
        terrain_regions=spec.terrain_regions,
        roads=spec.roads,
        buildings=(broken_building,),
        vegetation_zones=spec.vegetation_zones,
        weather=spec.weather,
        magic_manifestations=spec.magic_manifestations,
    )

    with pytest.raises(ValueError, match="building_phase"):
        require_major_provenance(broken)


def test_renderer_asset_paths_do_not_cross_visual_spec_boundary():
    spec = _fixture({"debug": "/Game/Buildings/SM_Smithy.uasset"})

    with pytest.raises(ValueError, match="renderer-specific asset reference"):
        spec.canonical_json()
