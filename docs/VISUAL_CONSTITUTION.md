# Visual Constitution

## Long-term visual target

All That Endures is intended to become a **full 3D, AAA-quality RPG** capable of supporting first- or third-person play. The final game should feel physically present, historically layered and cinematic without sacrificing the causal truth of the simulation.

The simulation owns reality; the renderer realizes that reality. Visual systems may change over the life of the project, but the underlying world state must remain renderer-agnostic and sufficiently expressive to reconstruct why a place, object, person or event looks the way it does.

The early **Visual World Laboratory** may use a tightly art-directed elevated camera or 2.75D presentation to prove deterministic world realization, composition, streaming and historical layering quickly. That laboratory is a development strategy, not the final visual ceiling.

Real runtime depth includes terrain/elevation, volumetric architecture and props, interiors, occlusion, navigation/collision, perspective, environmental lighting/shadows, water, particles, atmosphere, weather and physically consequential destruction or alteration where the simulation supports it.

## Material language

Stone, timber, metal, cloth, soil, water, bark, foliage, fur and skin must read credibly. Surfaces carry age, use, moisture, damage, repair and environmental history. Physically coherent response is the foundation; artistic exaggeration of value, edge, atmosphere and light produces the illustrated result.

## Physical credibility and restrained magic

Visual design begins with physical credibility. An asset should first read as a believable object, material, organism or structure with convincing mass, construction, wear, function and age. Magic is expressed through that physical substrate rather than replacing it with generic fantasy decoration.

A magical stone should still read as stone. A magical weapon should still communicate how it was forged, held, damaged and repaired. Architecture, armor, tools, creatures and artifacts should remain materially and mechanically legible even when supernatural forces alter what they can do.

Prefer supernatural expression that appears embedded in or acting upon real matter: subsurface light, crystalline inclusions, altered tissue, heat, frost, stress fractures, phase changes, local deformation, atmospheric interaction or other effects supported by the object's history and capabilities. Avoid gratuitous neon filigree, homogeneous glow, decorative runes without cultural or causal justification, excessive bloom and other effects that make magic feel painted onto the asset.

**Generated assets are judged on physical credibility first and spectacle second.** Text-to-3D, image-guided generation, authored modeling and future generation methods may all be used where appropriate, but they pass through the same art gate. Hero assets may justify tighter reference-driven art direction; ordinary props may use faster generation paths. The production method never lowers the final visual standard.

The target feeling is tactile: objects should look as though they could be picked up, weighed, handled, weathered and broken. Supernatural elements should make that reality stranger, not erase it.

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