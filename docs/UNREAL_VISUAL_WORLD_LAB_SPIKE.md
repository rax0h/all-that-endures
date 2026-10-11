# Unreal Visual World Laboratory — Technology Spike

Status: exploratory architecture note. This document does not replace the Project Constitution or silently settle unresolved canon.

## Why this spike exists

The Visual World Laboratory already defines the boundary:

`World/History State -> Visual Specification -> Asset Grammar -> 3D Realization -> Renderer`

The purpose of this spike is to map that boundary onto current Unreal Engine systems without allowing the renderer to become the authority on history.

The simulation remains authoritative. Unreal realizes state.

## Current Unreal systems that fit the problem

### Procedural Content Generation Framework (PCG)

Epic's current PCG framework is intended for procedural content ranging from individual asset utilities and buildings to biome generation and entire worlds.

Useful fit for ATE:

- terrain dressing from deterministic Visual Specification inputs;
- parcel/building grammar realization;
- biome and vegetation realization;
- road-edge and settlement dressing;
- material/weathering placement rules;
- runtime regeneration of bounded areas when simulated state changes.

`APCGWorldActor` supports runtime generation sources and integration with World Partition generation sources. That gives us a path to generate high-detail content around relevant regions instead of realizing the entire continent at maximum fidelity simultaneously.

Official reference:
https://dev.epicgames.com/documentation/unreal-engine/procedural-content-generation-framework-in-unreal-engine

### World Partition

World Partition provides the large-world streaming boundary.

ATE should treat it as a realization/streaming mechanism, not as the simulation model.

Proposed rule:

> Simulation relevance determines what state must be available. World Partition determines what high-fidelity spatial representation is resident.

This preserves the constitutional rule that player relevance may alter simulation resolution but may not alter historical probability.

Official API reference:
https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UWorldPartition

### Mass Entity

Mass Entity is Unreal's data-oriented framework for efficiently representing large numbers of entities.

This appears useful for the presentation side of population scale, especially if we distinguish:

- authoritative simulated person state;
- lightweight Unreal representation;
- near-player embodied Actor;
- far/off-screen Mass representation;
- dormant/no-render representation.

The Unreal representation must never become a second source of truth for a person's history, relationships, possessions, injuries, rank, or knowledge.

Mass should consume derived presentation state from the simulation.

Epic's current documentation describes MassEntity as a high-performance framework for large numbers of entities, with recent work emphasizing modularity, multi-core scheduling, signals, sparse/virtual fragments, and reduced memory cost.

## Proposed simulation-to-Unreal contract

### 1. Authoritative simulation state

Existing simulation owns causal reality.

Examples:

- settlement identity and history;
- building ownership and construction history;
- damage, repair, abandonment and rebuilding;
- roads and land-use changes;
- people, families, organizations and relationships;
- ecology;
- weather/climate state;
- artifacts;
- rank and Essence-derived physical state.

### 2. Visual Specification

A deterministic, versioned schema translates simulation state into renderer-independent visual facts.

Example:

```text
SettlementVisualSpec
  settlement_id
  visual_seed
  time_slice
  terrain_regions[]
  parcels[]
  roads[]
  buildings[]
  vegetation_zones[]
  population_representations[]
  weather_state
  lighting_context
  magic_manifestations[]
  provenance[]
```

No Unreal asset paths belong in this layer.

### 3. Unreal realization adapters

Unreal-specific code maps Visual Specification concepts onto:

- PCG graphs;
- World Partition cells/data layers;
- Mass entities;
- Actors;
- materials;
- Niagara/VFX;
- animation;
- lighting;
- water;
- audio.

This adapter layer may choose how to render truth. It may not invent truth.

## First executable proof when an Unreal workstation is available

Build one settlement-sized test map with:

- river or water feature;
- terrain relief;
- forest edge;
- roads/paths;
- 10–20 buildings;
- several deterministic historical states;
- one character path;
- one creature path;
- weather;
- physically situated magic;
- fixed camera anchors for repeatable captures.

Feed the scene from serialized Visual Specification fixtures, not hand-authored scene state.

Run at least four deterministic history states through the same Unreal realization pipeline.

Suggested initial states:

1. founding / sparse settlement;
2. mature prosperity;
3. damaged or disrupted period;
4. later repaired, expanded, declined, or culturally transformed state.

## Acceptance checks

The spike succeeds only if:

- identical simulation/visual seeds reproduce the same Visual Specification;
- Unreal can rebuild the scene from that specification;
- major visible changes have provenance back to simulation state;
- PCG does not invent objective history;
- streamed-out regions retain authoritative state outside Unreal;
- people can change representation level without changing identity;
- several history states remain visually coherent rather than one hero state looking good;
- the architecture can scale outward without making Unreal the simulation database.

## Immediate implementation work that does not require Unreal yet

1. Define the first versioned Visual Specification schema.
2. Produce deterministic fixture files from simulation state.
3. Add provenance IDs for every major visible feature.
4. Define representation tiers for people and creatures.
5. Define building-history visual facts independently of assets.
6. Define PCG-facing spatial inputs without Unreal asset references.
7. Create golden fixture cases for several time slices.
8. Add schema determinism tests.

## Tooling note

Current official Unreal documentation was checked through Context7 before this spike was written.

A remote Unreal workstation is not connected yet, so the next useful work is to make the Visual Specification contract strong enough that Unreal becomes an adapter target rather than a redesign of the simulation.
