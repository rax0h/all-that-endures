# Visual World Laboratory

## Purpose

The Visual World Laboratory is the first proof that the simulation architecture can become an exceptionally beautiful game. It is not a hand-authored vertical slice and not a placeholder scene.

## Environment

Build one settlement-scale test environment with meaningful terrain relief, a river/water feature, forest/ecological edge, paths/roads and roughly 10–20 buildings or enough structures to prove the grammar. Include camera anchors that can be reproduced across state changes.

## Required systems

- real 3D terrain and spatial architecture;
- deterministic Visual Specification pipeline;
- modular architectural grammar;
- material aging, damage and repair;
- dense ecology/vegetation;
- water;
- weather and seasonal hooks;
- production-intent lighting and volumetric atmosphere;
- controlled elevated three-quarter camera;
- at least one persistent character realization path;
- extensible rank-transformation path;
- at least one creature path;
- at least one physically situated magic effect;
- LOD/streaming strategy appropriate to the camera;
- deterministic capture/inspection harness.

## Historical variation scenarios

The same settlement grammar should be exercised across many seeds/state bundles and multiple historical time slices. Scenarios should include prosperity, poverty/maintenance decline, construction/expansion, fire/storm/flood damage, rebuilding with changed resources/style, road or land-use changes, vegetation succession and occupant turnover.

No scenario exists merely to make an attractive screenshot. Its visual state must be explained by supplied simulation/history inputs.

## Quality gate

The lab succeeds only if many generated states look like they belong in the finished game. A single hero composition is insufficient.

Review a deterministic matrix of seeds × time states × weather/lighting conditions from fixed camera anchors. Track failures such as illegal architecture, visual repetition, weak silhouettes, sparse vegetation, material incoherence, clipping, unreadable character scale, broken alpha, rank inconsistency and loss of historical provenance.

The goal is not infinite combinations. The goal is a constrained vocabulary whose legal combinations remain beautiful.

## Historical readability gate

Without opening a lore panel, a reviewer should be able to perceive selected state differences such as an addition, repair, abandoned structure, changed prosperity, altered road use or ecological recovery. The exact interpretation may require knowledge, but physical history must exist in the frame.

## Performance gate

Performance budgets are not yet canonized, but the architecture must assume production constraints from the beginning. Use the camera to concentrate quality: LOD, occlusion, instancing, impostors and selective complexity are expected. Do not solve performance by flattening the world into non-spatial scenery.

## Exit criterion

Do not scale to continent production merely because the lab runs. Scale when the repeated-state quality gate, determinism/provenance gate and performance direction are all credible.