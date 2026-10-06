# Visual Constitution

## Long-term visual target

All That Endures is intended to become a **full 3D, AAA-quality RPG** capable of supporting first- or third-person play. The final game should feel physically present, historically layered and cinematic without sacrificing the causal truth of the simulation.

The simulation owns reality; the renderer realizes that reality. Visual systems may change over the life of the project, but the underlying world state must remain renderer-agnostic and sufficiently expressive to reconstruct why a place, object, person or event looks the way it does.

The early **Visual World Laboratory** may use a tightly art-directed elevated camera or 2.75D presentation to prove deterministic world realization, composition, streaming and historical layering quickly. That laboratory is a development strategy, not the final visual ceiling.

Real runtime depth includes terrain/elevation, volumetric architecture and props, interiors, occlusion, navigation/collision, perspective, environmental lighting/shadows, water, particles, atmosphere, weather and physically consequential destruction or alteration where the simulation supports it.

## Material language

Stone, timber, metal, cloth, soil, water, bark, foliage, fur and skin must read credibly. Surfaces carry age, use, moisture, damage, repair and environmental history. Physically coherent response is the foundation; artistic exaggeration of value, edge, atmosphere and light produces the illustrated result.

## Environment

Major buildings, bridges, cliffs, walls, stairs, terrain and other spatially consequential structures should generally be true geometry/material systems rather than painted cards. Dense vegetation is layered ecologically: canopy, understory, shrubs, grasses, flowers, deadfall, litter, moss, fungi and disturbance states as appropriate.

Weather modifies the whole frame: surface wetness/snow/mud, visibility, water, vegetation motion, particles, exposure, volumetrics and lighting.

## Lighting

Lighting is a primary art system, not a final polish pass. Combine coherent sun/sky and local lighting with contact/depth cues, atmospheric perspective and volumetrics. Magic exists in the scene: emissive phenomena illuminate fog, wet surfaces, characters and nearby materials where appropriate.

## Characters

Use a high-quality persistent parametric character system rather than disposable random NPC generation. Appearance derives from persistent identity and may include inherited morphology, age, body characteristics, life conditions, occupation, injuries/scars, culture, fashion, wealth, personal preference, equipment, Essence influence and rank transformation.

Rank transformation is biological/ontological, not merely a glow. The visual system must be capable of expressing increasingly magical bodies and eventually anatomy that is no longer conventionally organ-dependent, while preserving individual identity.

## Cultural visual lineage

Architecture, clothing, decoration, tools and art can develop style lineages. Motifs and techniques spread through actual contact, teaching, migration, trade, conquest, prestige and imitation. Hybrid visual traditions should therefore have historical ancestry rather than random theme mixing.

## Procedural world realization

Settlements, roads, buildings, interiors, landscapes and visible damage states must be realizable from simulation state rather than depend on fixed handcrafted maps.

Procedural does not mean arbitrary. Stable world and entity identifiers should produce persistent deterministic visual identities. Returning to an unchanged building should reproduce the same building. Historical changes should patch that realization rather than reroll unrelated geometry.

The art pipeline should build **visual languages and grammars**, not preset towns: coherent systems for structure, materials, architecture, vegetation, clothing, decoration, wear, damage, repairs and cultural lineage. These systems combine according to simulated terrain, climate, resources, wealth, technology, labor, culture, law, trade, migration, disaster and history.

A settlement should therefore look the way it does because of what happened there.

## Neural and future rendering

ATE should be designed to benefit from neural rendering and future graphics systems without depending on one named product or version. Neural reconstruction, lighting, material enhancement and similar technologies may supply expensive final-frame fidelity, but they must remain downstream of world truth.

Rendering technology may improve dramatically over the life of the project. The architecture should allow those improvements to be adopted without rewriting simulation history, character identity, settlement state or material causality.

## Generated cultural works

Generative media may be useful for paintings, manuscripts, heraldry, murals, decorative motifs, portraits and similar works, but outputs must be conditioned by the simulated creator, materials, technique, influences, culture and historical context. Generated media is not the foundation for spatial world geometry.

## Transparency

For isolated transparent runtime assets, transparency is authored at source/generation time as genuine RGBA. Do not use white/green/scenery backgrounds with an automatic removal step. Preserve source masters separately from runtime derivatives and validate alpha/edge integrity.

## Rejection conditions

Reject final visuals that read as flat vector villages, primitive final geometry, orthographic board-game framing, chibi/toy proportions, generic mobile-game art, single-plane backgrounds, giant opaque HUD blocks, ungrounded neon magic or procedural variety that routinely produces incoherent composition.

> **Procedural variation cannot lower the art standard. The simulation owns reality; the renderer realizes it.**