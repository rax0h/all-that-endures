# ATE Pre-Cosmology Architecture Reconciliation

**Date:** 2026-09-15  
**Status:** planning reconciliation/freeze marker. Production implementation remains subject to the Stage 0.5 hard gate in `IMPLEMENTATION_ROADMAP.md`.

## Purpose

This note closes the planning gaps identified by `CROSS_SYSTEM_INTEGRATION_AUDIT.md` and records the current coherent pre-cosmology design set.

It does **not** replace the detailed specifications. It records that the previously identified top-level gaps have now received dedicated design authority and points implementation agents to the reconciled roadmap.

## Resolved audit gaps

### Relationships and social life — RESOLVED
Dedicated authority now exists:

`docs/RELATIONSHIPS_SOCIAL_LIFE_MODEL.md`

It defines:
- objective shared relationship history versus directional A->B/B->A subjective assessment;
- familiarity, affection, trust, respect, fear, attraction, resentment, obligation, rivalry and dependency;
- friendship and non-instrumental social interaction;
- kinship/family bonds from lived history rather than genealogy alone;
- romance/courtship/partnership without a soulmate/drama system;
- promises, caregiving, betrayal, forgiveness, reconciliation and estrangement;
- social circles/network access/gossip;
- conflict escalation/de-escalation;
- sparse/event-driven performance semantics.

The existing `social.py` graph remains the migration foundation for pair identity, adjacency, partnerships and shared history. No second disconnected social graph is authorized.

### Ordinary health, disease, aging and reproduction — RESOLVED
Dedicated authority now exists:

`docs/HEALTH_DISEASE_AGING_REPRODUCTION_MODEL.md`

It defines:
- persistent bodily condition/recovery semantics;
- symptoms versus objective disease;
- exposure/transmission/immunity and cohort epidemics;
- nutrition, hydration, sleep/rest and environmental stress;
- aging, senescence and causal natural death;
- chronic conditions, disability/impairment and pain;
- healer/treatment semantics under subjective knowledge;
- reproduction, conception, pregnancy, birth and infant health;
- species/rank longevity integration;
- one shared bodily authority for later combat injury/healing;
- lazy/event-driven performance semantics.

`biology.py`/`rank.py` remain sources of species/rank biological capability and modifiers. Legacy scalar Person health becomes a migration/derived projection rather than a permanent competing health universe.

## Reconciled implementation roadmap

`docs/IMPLEMENTATION_ROADMAP.md` v3 is the current sequencing authority.

It now explicitly includes:
- Stage 5.5 — Physical world and ecology integration;
- Stage 5.75 — Material civilization, economy and settlements;
- Stage 5.9 — Ordinary health, disease, aging and reproduction;
- Stage 6 consuming the shared bodily-health authority plus mature material/environment/logistics systems.

These stages formalize newer design work that did not exist when roadmap v2 was written.

## Current coherent design set

The major pre-cosmology architecture now has dedicated authority for:

1. implementation/core causal architecture;
2. Stage 1 subjective foundation contracts;
3. Human Psyche;
4. Human Development;
5. Relationships & Social Life;
6. Information, Belief & Evidence;
7. Institutions, Governance & Power;
8. Civilization Knowledge, Creation & Memory;
9. World, Ecology & Environment;
10. Material Civilization, Economy & Settlements;
11. Health, Disease, Aging & Reproduction;
12. Conflict, Combat, Injury, Healing & War;
13. cross-system ownership/dependency integration.

This is enough top-level architecture to stop creating new major subsystems merely for completeness.

## Cross-system spine

The integrated causal chain remains:

`objective state/event`
`-> legitimate evidence/access`
`-> Observation`
`-> Belief + Memory + directional social assessment`
`-> Psyche + Goals`
`-> Agency attempt`
`-> owning domain resolution`
`-> objective state mutation/Event`
`-> material/social/institutional/environmental/bodily consequences`
`-> new evidence`
`-> future subjective decisions`

The rule remains:

> **A fact has one authoritative owner, many legitimate consequences, and no hidden duplicate truth.**

## Important resolved boundaries

### Social versus genealogy
Genealogy owns objective kin relation. Social systems own lived relationship history and subjective interpersonal assessment.

### Social versus reproduction
Social/Agency establishes actual intimacy/reproductive opportunity. Health/Reproduction resolves biological conception/pregnancy/birth.

### Environment versus health
Environment owns exposure conditions. Health resolves bodily consequences.

### Material economy versus health
Material systems own food/water/resources/access. Health resolves physiological consequences of actual consumption/deprivation.

### Health versus combat
Combat/accident owns how traumatic injury occurs during an encounter. Health owns the continuing bodily condition, deterioration, stabilization/recovery and impairment. No duplicate HP history.

### Biology/rank versus health
Biology/rank owns species/rank capability, aging-rate, disease-resistance, healing/resilience inputs. Health owns actual individual condition through time.

### Information versus health
The simulator may know the actual disease/cause. People/healers know only observations/evidence and may diagnose incorrectly.

### Material provenance versus information
Physical object history remains objective provenance. Claims/records about that history may be true, false, incomplete or lost.

### Infrastructure versus settlement summaries
Physical infrastructure owns roads/waterworks/etc. Legacy settlement scalars migrate toward derived projections.

## Performance freeze principles

All future architecture must preserve the canonical millennium target and avoid consuming headroom casually.

The shared strategy is now consistent across domains:
- sparse social edges rather than all-pairs people;
- bounded Memory/Goals;
- event-driven subjective updates;
- aggregate/lazy ecology rather than per-organism simulation;
- sparse markets/routes rather than all-settlement pair scans;
- dormant healthy people rather than annual health ticking;
- cohort disease rather than all-contact simulation;
- scheduled pregnancy/recovery;
- aggregate warfare with focused encounter expansion only when needed;
- deterministic reconstruction where persistence is unnecessary.

> **Depth comes from causal composition, not simulation frequency.**

The <=120-second millennium target is a ceiling, not a runtime budget to fill.

## What remains deliberately unresolved

The existence of open questions inside detailed specifications is intentional. They fall into three classes:

### Implementation-contract questions
Exact schema shapes, indexes, bounded capacities and migration details should be resolved immediately before the PR that needs them, against existing code and benchmarks.

### Calibration questions
Rates/distributions such as fertility, disease severity, aging curves, ecological recovery, market parameters and combat timing require measured simulation calibration rather than speculative prose.

### Canon/design questions
Objective metaphysics/cosmology remains deliberately unresolved. Coding agents must not invent gods, resurrection rules, afterlife mechanics, ambient magical ecology or other metaphysical truth from implementation convenience.

## Immediate implementation authority

Despite the maturity of later-stage planning, **Stage 0.5 remains the only production implementation work currently authorized until its exit gate is accepted.**

Astra/repo-wide integrator should:
1. resume current magic/currency/access stabilization;
2. verify canonical 20/20 ranked-path invariants;
3. calibrate the completion/access funnel;
4. run deterministic 100/500/1,000-year validation;
5. preserve <=120-second millennium performance;
6. clear CI/regressions;
7. record the exact gold baseline on `main` with schemas, command/config, seeds, runtime, diagnostics and deterministic fixture/digest.

Only then should Stage 1 production begin.

## Stage 1 handoff after gold freeze

Once Stage 0.5 closes, implementation begins in this order:

1. mastery projection/tests where isolated;
2. World Seed / History Seed migration infrastructure;
3. Observation/access boundary;
4. Belief extension + bounded Memory;
5. persistent Psyche;
6. sparse directional relationships;
7. Agency v2 read boundary/DecisionTrace;
8. indexes/integration/performance.

No later subsystem should bypass these foundations.

## Planning conclusion

ATE's pre-cosmology architecture is now sufficiently complete and reconciled for implementation sequencing.

Further planning should be driven by an actual contradiction, missing interface, measured calibration problem or explicit canon decision—not by a desire to keep adding documents.

The next major design frontier is objective cosmology/metaphysics, and it remains intentionally deferred until authored deliberately.

Until Stage 0.5 closes, the correct move is not more architecture and not Stage 1 code.

It is to **finish the simulation we already have, freeze the gold baseline, and then build forward from it.**
