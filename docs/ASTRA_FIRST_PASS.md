# Astra First Pass

## Mission

Build the first production-intent technology proof for **All That Endures**: the **Visual World Laboratory**.

Do not attempt the whole continent. Do not replace the simulation with scripted quest logic. Do not optimize for one screenshot. Build the smallest real architecture that can prove the simulation-to-visual pipeline repeatedly.

## Required reading order

1. `docs/PROJECT_CONSTITUTION.md`
2. `docs/SIMULATION_ARCHITECTURE.md`
3. `docs/WORLD_GENERATION.md`
4. `docs/VISUAL_CONSTITUTION.md`
5. `docs/WORLD_REALIZATION.md`
6. `docs/VISUAL_WORLD_LAB.md`
7. `docs/CANON_OPEN_QUESTIONS.md`
8. `simulation/` executable foundation and tests

## First-pass architecture

Implement clean boundaries for:

`World/History State -> Visual Specification -> Asset Grammar -> 3D Realization -> 2.75D Art-Direction Renderer`

The simulation must not reference renderer asset filenames. The renderer must not invent historical facts. The Visual Specification layer is the deterministic contract between them.

## Laboratory scope

A small terrain containing approximately one settlement-scale environment with a river/water feature, forest edge, roads/paths, terrain relief and enough buildings to exercise composition. Target roughly 10–20 realized buildings, but architecture quality and variation matter more than an arbitrary count.

The lab must be capable of presenting multiple deterministic settlement histories/states rather than one authored scene. At minimum exercise construction, expansion, wealth/maintenance differences, weathering/damage, repair/rebuilding, road/land-use change, vegetation response and occupant-driven dressing.

Include at least one production-intent character pipeline path, one creature path, weather/atmosphere, water, lighting and one physically situated magic effect. Rank appearance must have an extensible transformation contract even if only a small number of proof states are initially implemented.

## Art bar

The target is a beautiful, premium fantasy illustration in motion, supported by real 3D depth. Avoid flat vector treatment, toy/chibi proportions, generic mobile-game rendering, primitive production geometry, single-plane backgrounds and giant opaque HUD treatment.

Materials must read credibly as stone, timber, metal, cloth, soil, water, bark and foliage. Use depth haze, volumetric atmosphere, weathering, tonal separation and deliberate composition. Magic must illuminate/respond to nearby surfaces where physically appropriate.

The controlled elevated three-quarter camera is a production constraint and optimization tool. Spend geometry, shading and texture budget where the camera can see it; use LOD/impostor/occlusion cheats aggressively where they preserve the final frame.

## Procedural-quality gate

The lab fails if it can produce one beautiful configuration but routinely produces weak ones.

Create a deterministic visual test set spanning many seeds/history states and several time slices (for example present, +50, +200, +500 years or equivalent scenario states). Capture the same camera anchors across those states.

Acceptance requires:

- repeated compositions remain visually coherent;
- buildings have believable structure and material transitions;
- historical changes are visible without lore text;
- vegetation and weather do not read as sparse procedural scatter;
- character appearance remains persistent and state-derived;
- no visual system fabricates objective history;
- identical world/history/visual seeds reproduce identical specifications;
- the system can explain the provenance of every major realized change.

## Engineering priorities

1. Deterministic seed/version envelope.
2. Typed visual-specification schema.
3. Terrain/parcel/road realization interfaces.
4. Architectural grammar with legal composition constraints.
5. Material/weathering/repair layering.
6. Ecology/vegetation realization.
7. Character persistent appearance + rank-transformation interface.
8. Weather, lighting, volumetrics and water.
9. Camera/composition and LOD strategy.
10. Automated capture/validation harness for the procedural-quality gate.

## Asset rule

Do not build the proof out of disposable visual placeholders and then call the art problem solved. It is acceptable to stage implementation, but acceptance of the laboratory requires production-intent assets/materials in the tested paths.

For isolated transparent assets, author true RGBA transparency from the beginning. Do not make background stripping a normal pipeline step.

## What not to decide silently

Do not invent unresolved rank thresholds, Essence rules, world dimensions, history duration, population counts, engine choice or final content quantities merely to unblock code. Put such assumptions behind configuration and record them in `docs/CANON_OPEN_QUESTIONS.md` when a decision is required.

## Definition of first-pass success

A reviewer can launch the laboratory, select/replay several deterministic world/history states, and see a genuinely spatial, art-directed 2.75D settlement change in ways traceable to simulation state. The architecture is clearly capable of scaling outward without requiring the simulation to know about art assets or the renderer to invent history.