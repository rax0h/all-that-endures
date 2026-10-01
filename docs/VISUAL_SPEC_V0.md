# Visual Specification v0

Status: experimental contract on `spike/unreal-visual-world-lab`. It is intentionally renderer-independent and does not settle unresolved canon.

## Purpose

The Visual Specification is the deterministic handoff between simulated reality and any renderer.

`Simulation / History -> Visual Specification -> Asset Grammar -> Unreal or other renderer`

The simulation owns why something exists. The renderer owns how that truth is realized.

## First code contract

The initial Python contract lives in:

`simulation/ate_sim/visual_spec.py`

It currently represents:

- terrain regions;
- roads;
- buildings and construction/damage/repair phases;
- vegetation zones;
- population representation hooks;
- weather;
- physically situated magic manifestations;
- causal provenance for major visible facts.

This is deliberately small enough to test before binding it to the full simulation.

## Determinism

A `SettlementVisualSpec` serializes to canonical JSON with stable key ordering and exposes a SHA-256 digest.

Equivalent specifications must produce identical canonical JSON and identical digests.

That digest can later become part of:

- golden visual fixtures;
- Unreal import/cache keys;
- deterministic capture tests;
- regression comparisons;
- asset-realization caches.

## Provenance rule

Every major realized change must be able to answer why it exists.

The v0 provenance gate currently covers terrain regions, roads, buildings, every building phase, vegetation zones, weather and magic manifestations.

A fire-repair phase therefore cannot merely say:

`damage = 0.35`

It must also preserve a reference to the source state/event that authorized that visible history.

## Renderer boundary

The Visual Specification rejects obvious renderer-specific asset references such as Unreal `/Game/` paths and `.uasset` references.

That is intentional.

A visual specification may say:

- local stone;
- slate roof;
- river-founder style lineage;
- wealthy workmanship;
- repaired after fire;
- 0.72 maintenance.

It may not say:

- `/Game/Buildings/SM_Smithy_04.uasset`.

The Unreal adapter will make that downstream selection.

## Next adapter step

The next implementation step is to compile a real simulated settlement into this schema without introducing new historical facts.

That adapter should begin narrowly:

1. stable settlement identity and time slice;
2. terrain/ecology facts already present in simulation state;
3. roads/built-environment only where the simulation actually contains authoritative facts;
4. people represented by persistent identity hooks;
5. explicit placeholders for facts the current simulation does not yet model.

Missing state is preferable to fabricated state.

## Validation

Tests live in:

`simulation/tests/test_visual_spec.py`

They prove:

- canonical serialization is deterministic;
- metadata insertion order does not affect output;
- major historical visual facts carry provenance;
- a building phase without provenance fails the gate;
- Unreal asset references cannot leak across the boundary.
