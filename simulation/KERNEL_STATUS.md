# ATE Simulation Kernel

This package is the clean replacement architecture for the world simulation. It does not grow the closed v8.4 function by accretion; v8.4 remains a behavioral reference while this kernel integrates new mechanics through shared primitives.

Current executable kernel proves: deterministic namespaced RNG, persistent identity, seeded physical geography, explicit people/households/settlements, event provenance and causal edges, weather -> production/scarcity, mortality -> bereavement, explicit reproduction without population floors, hazard x preparedness outcomes, settlement learning/memory, and queryable deterministic present state.

This is an implementation milestone, not completion of the 35-domain target. Every subsequent domain must enter through shared state/causality/pressure/observation/provenance primitives rather than isolated event-card systems.

## Architectural invariants

- One authoritative Reality transition; downstream systems react to it.
- Objective history is never fabricated by Narrative.
- Player relevance may change resolution, never probability.
- Persistent identity survives lower simulation resolution.
- Randomness is deterministic and namespaced so subsystem ordering does not silently rewrite unrelated history.
- No population floors or rescue births.
- No output-target patches: calibration changes causal assumptions, not desired results.
- Causal references must point backward to real events.

## Next integration tranche

Relationships/genealogy, travel and information propagation, object/material provenance, enterprises/economy, built-environment history, cognition/agency/creative practice, rank ontology, organizations/politics/law, culture/religion/language, knowledge/memory/evidence/archaeology, ecology/warfare/disasters, relevance scaling, and read-only narrative-pressure discovery.
