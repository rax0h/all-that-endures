# Visual Preview Map

Status: branch-only Visual World Laboratory tooling.

## Purpose

The preview map is an engineering instrument for inspecting the simulation-to-visual boundary before Unreal is involved.

It is not final art direction and it does not attempt to make the world look photorealistic.

The map answers a simpler question first:

> Did the renderer receive and display the physical truth the Visual Specification actually contains?

## Current layers

The first renderer draws, in order:

1. terrain and water regions;
2. vegetation zones;
3. roads and paths;
4. building footprints;
5. damage and repair hints;
6. population markers;
7. physically situated magic;
8. title and legend.

Water is explicit through `TerrainRegionSpec.surface_kind`.

Building footprints are explicit through `BuildingSpec.footprint_size_m`; the preview must not invent final architectural geometry.

## Historical overlays

A building with historical damage receives a damage outline.

A building with a later repair phase also receives a repair marker.

These are diagnostic symbols. They prove that historical state survives the handoff. They are not intended to represent the final visual treatment of burned masonry, rebuilt roofs, patched timber, soot, or weathering.

## Command line

From the repository root:

```bash
python simulation/visual_preview.py \
  simulation/fixtures/visual/settlement_v0.json \
  --out settlement_v0.png
```

Optional switches:

- `--width`
- `--height`
- `--no-people`
- `--no-labels`

## First fixture

`simulation/fixtures/visual/settlement_v0.json` is deliberately hand-authored.

It exists only to prove the renderer independently from the simulation compiler.

Its metadata explicitly marks it as a debug fixture rather than canonical world history.

The next milestone is to compile an actual simulated settlement into the same schema.

## Acceptance gate

The preview path is credible when:

- the same specification renders deterministically;
- invalid schema versions fail loudly;
- optional display layers do not change source state;
- major visible facts remain provenance-bearing;
- no Unreal asset paths are needed;
- renderer-only convenience does not fabricate historical facts.

## Direction

The expected progression is:

`simulation/history -> Visual Specification -> debug map -> Unreal realization`

The debug map may remain useful even after full 3D rendering exists because it provides a fast, deterministic way to inspect spatial state and historical changes across many seeds and time slices.
