# World Realization Architecture

## Boundary

The simulation describes what exists and why. The renderer describes how a visual specification is drawn. Between them sits the **World Realization Compiler**.

`Simulation State -> Visual Specification -> Asset Grammar -> Spatial Realization -> 2.75D Rendering`

This boundary is mandatory. Simulation code must not depend on asset filenames. Rendering code must not invent history.

## Visual Specification

A visual specification is deterministic data derived from simulation state. It can include terrain state, parcel boundaries, structure dimensions, construction phases, material families, cultural style lineage, wealth/workmanship, damage, repairs, current maintenance, dressing, vegetation state, character appearance parameters, rank manifestation and current environmental conditions.

Every consequential field should be traceable to source state/provenance.

## Buildings

Do not store a bespoke mesh for every historical version of every building. Preserve construction history and compile the currently relevant physical state.

Example lifecycle:

`foundation -> addition -> ownership change -> fire -> repair -> workshop conversion -> abandonment -> collapse -> burial -> excavation`

The realization system should be able to reconstruct surviving layers when archaeology or later construction exposes them.

## Architectural grammar

Composition is constrained hierarchically:

`geography/material availability -> climate -> technology -> culture/style lineage -> period -> wealth -> function -> builder capability/preferences -> construction history -> occupants/maintenance -> current weather`

The grammar is not unrestricted mesh randomization. Every legal combination must satisfy structural, spatial and artistic constraints.

## Authored asset classes

1. **Natural primitives/material systems**: geology, soil, vegetation components, water, snow/mud and related reusable systems.
2. **Modular constructed vocabulary**: structural frames, walls, foundations, roofs, openings, stairs, bridges, furniture, roads, clothing/equipment and repair/damage pieces.
3. **Parametric living systems**: people, creatures and vegetation with persistent variation and shared animation/rigging where appropriate.
4. **Unique cultural works**: art, manuscripts, heraldry, sculpture, music/textual works and decorative media whose provenance belongs to simulated creators.

## Visual genealogy

Styles are persistent lineages. A motif or construction technique can be invented, taught, copied, hybridized, forgotten and rediscovered. The realization compiler uses that lineage to select/parameterize compatible authored vocabulary.

## Historical dressing

A wealthy family repairing an old structure with imported stone should not produce the same visual state as a poor family patching it with local timber. Damage, repair, inheritance, occupation and maintenance should accumulate visibly.

## Characters

Character realization is persistent. Reopening a save does not reroll a person's face or clothing. Genetics, age, life history, injury, occupation, culture, wealth, fashion, preference, rank and magic provide deterministic inputs. Clothing and possessions can themselves have provenance.

## Rank

Expose rank transformation as a first-class visual/physical contract. Do not hard-code it as shader intensity. The specification must eventually support changes to anatomy, tissue/material behavior, age presentation, movement, injury state and Essence-specific manifestations.

## Caching and promotion

Expensive realized geometry/media may be cached, but the authoritative source remains simulation + visual specification + versioned grammar. Relevance scaling may promote a location/object/person to richer visual/historical detail without changing the historical probability that produced it.

## Validation

A realization is invalid when it violates source history, produces illegal construction, loses persistent identity, silently changes seed output, or falls below the procedural-quality art gate.