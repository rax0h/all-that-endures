# ATE Implementation Roadmap v2

**Purpose:** stage the living design into bounded engineering work. This is sequencing, not permission to redesign canon.

## Work classification
Every proposed change must be tagged before implementation:
- **KEEP:** existing system already supplies the required primitive.
- **EXTEND:** existing authority remains; add fields/contracts/indexes/behavior.
- **MIGRATE:** deliberate compatibility transition is required.
- **NEW PRIMITIVE:** no existing authority provides the concept.
- **DERIVED:** should be composed from primitives rather than persisted as a new causal truth.
- **DEFER:** design/canon is not settled or dependency is not ready.

## Stage 0 — Baseline audit
**Goal:** know exactly what exists before changing foundations.

Deliverables:
- map `LIVING_DESIGN.md` requirements to existing modules;
- identify KEEP/EXTEND/MIGRATE/NEW/DERIVED/DEFER;
- preserve canonical tests/digests/performance gates;
- document checkpoint/schema compatibility constraints.

**Status:** planning audit completed in `STAGE_0_AUDIT_MATRIX.md`.

## Stage 0.5 — Current simulation stabilization and gold-baseline freeze
**HARD GATE: Stage 1 implementation must not begin until this stage is accepted.**

**Goal:** finish and validate the simulation ATE already has before introducing the new subjective-causality architecture. Planning for later stages may continue in parallel, but production implementation remains on the current simulation until this gate closes.

### Resume unfinished current work first
Astra should resume the existing stabilization/calibration thread rather than jumping to Psyche/Observation/Agency v2. At minimum inspect and finish:
- ranked-currency circulation and any currency bottleneck affecting magical progression;
- essence and awakening-stone access/liquidity;
- completion economy for canonical essence paths;
- mature-world completed-path population and resulting Iron/Bronze/Silver/Gold/Diamond distributions;
- any remaining failures, regressions, calibration notes, TODOs or CI issues from the current canonical-magic-progression work;
- deterministic 100/500/1,000-year behavior and <=120-second millennium performance;
- economy, threat ecology, lineages/dynasties, institutions, provenance/materials and other existing systems for obvious runaway/dead behavior exposed by the calibration changes.

### Canonical magic invariants during stabilization
- No person is Iron rank or above without all three base essences, confluence and all 20 skills unlocked.
- A partial path is not an Iron-rank person. Rank-facing diagnostics/counts must not label incomplete paths as ranked.
- Rank advancement remains governed by all 20 abilities and existing canonical gates.
- Fix access/liquidity bottlenecks without weakening the 20-skill requirement.
- Preserve the progression timing/curve unless evidence identifies a separate pacing defect. Access/completion calibration and mastery pacing are different problems.
- Do not manufacture Gold/Diamond counts by bypassing prerequisites, injecting completed paths, or loosening rank rules merely to hit a target distribution.

### Calibration method
Treat current low mature-rank counts as a causal calibration problem. Instrument the funnel rather than guessing:
1. population eligible for magic;
2. first essence acquisition;
3. second essence acquisition;
4. third essence acquisition;
5. confluence creation;
6. awakening-stone acquisition/use;
7. 20/20 completed paths;
8. time spent at each rank/stage of advancement;
9. deaths/attrition before completion/advancement;
10. currency/resource stock, production, sinks, hoarding, trade and geographic/institutional access at each bottleneck.

The objective is not a predetermined exact number of Golds. The objective is a mature world whose distribution is explainable from resources, opportunity, lifespan, advancement difficulty and history, and is rich enough to support the intended setting.

### Required stabilization validation
Run and retain comparable diagnostics for at least representative 100-, 500- and 1,000-year simulations. Validate:
- exact determinism for fixed seed/config;
- complete-path invariant for every ranked person;
- no negative/impossible currency or resource state;
- no accidental infinite resource/currency creation;
- acquisition/completion funnel is inspectable;
- rank populations are not dominated by an implementation bottleneck unrelated to canon;
- long-lived rankers and lineage survival remain plausible under existing canon;
- threat ecology and economy remain coupled rather than one system starving the other accidentally;
- existing provenance/institution/history outputs remain coherent;
- CI/test suite passes;
- canonical 1,000-year benchmark remains <=120 seconds.

### Gold-baseline freeze
When stabilization is accepted:
- merge/identify one exact commit on `main` as the **pre-subjective-architecture gold baseline**;
- record its commit SHA, simulation/checkpoint/archive schema versions, canonical benchmark command/config, representative seed(s), runtime and key calibration diagnostics;
- preserve a deterministic golden fixture/digest from that baseline;
- document known limitations that are intentionally deferred to Stage 1+ rather than silently treating them as fixed.

All Stage 1 migration and compatibility work is measured against this baseline, not against an older intermediate commit.

**Best owner:** Astra/repo-wide integrator. This is continuation of current implementation work, not a new architecture pass.

**Exit gate:** current ATE is deterministic, CI-clean, performant, canonically valid, and its magic/currency/access economy is sufficiently calibrated that we are willing to freeze it as the reference implementation before structural migration.

## Stage 1 — Foundation contracts and subjective causality
**BLOCKED FOR IMPLEMENTATION until Stage 0.5 gold-baseline freeze. Planning/specification may continue.**

**Goal:** establish attachment points for everything later.

Work packages:
1. four-stage mastery projection/state refinement without changing rank pacing;
2. World Seed / History Seed migration design and deterministic tests;
3. persistent Psyche state contract: temperament, values/commitments, self-concept, drives, bounded goals;
4. Observation contract/access control;
5. bounded Memory contract;
6. sparse directional relationship assessment contract;
7. Agency v2 interface that extends current `agency.py` rather than replacing domain authorities;
8. performance indexes/queues required by these contracts.

Detailed contracts live in `STAGE_1_FOUNDATION_CONTRACTS.md`. They are planning authority only until Stage 0.5 closes.

**Gate:** no omniscient information leakage; deterministic replay; existing magic chronology preserved; benchmark regression understood and bounded.

**Best owner:** Astra for integration spine. Smaller agents may implement isolated tests/projections after contracts are frozen and Stage 0.5 closes.

## Stage 2 — Human development and ordinary life
**Dependencies:** Stage 1 Psyche, Memory, Relationship, Agency.

Work packages:
- childhood/caregiver developmental influence;
- values/worldview revision from consequential experience;
- friendship and non-instrumental social interaction;
- attraction/courtship/partnership extensions;
- family modeling, generational expectations/rebellion;
- bounded habits/appetites/vice responses;
- magical aspirations/preferences feeding existing opportunity/resource systems;
- employment/education/mentorship goals using existing economy/skills.

**Gate:** people with similar starts can diverge through history; most lives remain computationally cheap and often ordinary.

## Stage 3 — Information society
**Dependencies:** Observation, Memory, Belief, Relationship.

Work packages:
- rumor/hearsay transmission with source lineage;
- secrets/concealment/disclosure;
- observer/group-relative reputation;
- institutional records and archival memory;
- evidence objects/links and investigation beliefs;
- misinformation, contradiction, revision, rediscovery.

**Gate:** truth remains separate from knowledge; investigations can fail without dice-scripted outcomes; no universal reputation score.

## Stage 4 — Institutions, governance, and collective action
**Dependencies:** Agency, relationships, records, economy/property, existing institutions.

Work packages:
- generalized institutional lifecycle/succession;
- emergent schools/apprenticeships/academies;
- governance legitimacy and succession;
- bureaucracy/record-keeping roles;
- collective action/group formation through actual relationships;
- law/enforcement legitimacy;
- corruption from dependency/conflicting obligations;
- crime/black markets/organized crime from incentives/networks;
- migration/class/dependency feedback.

**Gate:** institutions can arise, persist, reform, split, merge, or die for causal reasons; founder death is not a hard-coded outcome.

## Stage 5 — Knowledge, invention, art, and civilization memory
**Dependencies:** information objects, records, institutions, existing provenance/transmission.

Work packages:
- transferable information-object primitive;
- discovery/invention/combination/independent rediscovery;
- scholarship, criticism, competing theories;
- authored objects: notices, letters, journals, inscriptions, books;
- art/music/folklore works as grounded cultural artifacts;
- loss/copying/censorship/preservation/translation;
- archaeology and historical reinterpretation;
- language/dialect ancestry/exposure foundation (not full prose generation);
- connect existing provenance to cultural/historical significance.

**Gate:** knowledge can genuinely disappear and reappear; ordinary objects can become relics through history; lore can be reconstructed from simulated past.

## Stage 6 — Conflict, combat, injury, healing, and rescue
**Dependencies:** Agency, relationships, goals, event reactions; existing warfare/threat ecology/magic.

Work packages:
- temporal encounter state and objectives;
- injury severity vs viability/survival window;
- healing rate/effectiveness and stabilization;
- resilience/regeneration/rank effects on viability;
- ally arrival/rescue/extraction;
- escalation from interpersonal conflict to organized violence;
- long-lived ranked-person social consequences.

**Gate:** rank disparity is severe but not an absolute outcome lock; rare upsets have inspectable causes; healing cannot resurrect someone merely because a healer is nearby.

## Stage 7 — Player-facing deep simulation
**Dependencies:** stable human/information/combat layers.

Work packages:
- player obeys same knowledge/evidence rules;
- Adventure Society judgment/star progression from demonstrated responsibility;
- contracts with objectives, not designer-approved solutions;
- one-life/death/resurrection integration;
- player reputation/relationships without universal faction meter;
- interaction/expression contract; optional language renderer remains non-authoritative.

## Stage 8 — Cosmology/divinity/religion
**BLOCKED until objective cosmology is authored by design.**

After canon is settled:
- divine personhood/agency where appropriate;
- objective divine events separated from mortal belief;
- religions/institutions/schisms as human historical systems;
- theological disagreement despite objectively existing gods.

Astra must not infer metaphysical truth from convenient mechanics.

## Stage 9 — Millennium integration/calibration
Repeated 100/500/1,000-year runs. Inspect histories, not only aggregate metrics.

Validate:
- determinism and alternate-history semantics;
- population and lineage health;
- magic access/rank distributions;
- social/institutional diversity;
- knowledge preservation/loss;
- conflict rates and escalation;
- cultural differentiation;
- dead systems/runaway loops;
- archive inspectability;
- <=120-second canonical millennium gate.

Optimization must preserve causal semantics. Prefer indexes, sparse state, bounded work, event queues, lazy evaluation and aggregation over deleting depth.

## Delegation map
### Keep with Astra / repo-wide integrator
- Stage 0.5 current-simulation stabilization and baseline freeze;
- schema/checkpoint migrations;
- Psyche/Agency integration spine;
- Observation/knowledge authorization boundary;
- seed architecture;
- event scheduling/cadence/performance infrastructure;
- cross-system integration and final millennium optimization.

### Safe to delegate after interfaces freeze AND Stage 0.5 closes
- four-stage mastery projection/tests;
- bounded memory container/decay utilities;
- directional relationship data structures/tests;
- record/evidence schemas and indexes;
- institution lifecycle helpers;
- information-object structures;
- historian/diagnostic queries;
- benchmark fixtures and behavioral scenario tests;
- documentation and archive inspector extensions.

### Do not delegate independently yet
- current magic/currency/access calibration away from Astra's active stabilization thread;
- objective cosmology;
- final personality dimensions/weights;
- morality/ethics shortcuts;
- universal dialogue/personality generation;
- major magic balance changes;
- anything that creates a parallel provenance, agency, knowledge, institution, or event system.

## PR sizing rule
A PR should normally introduce one primitive or one coherent integration slice plus tests. Avoid "implement society" PRs. Each PR must state:
1. authority documents;
2. existing modules inspected;
3. state/schema changes;
4. RNG changes;
5. performance cost;
6. behavioral acceptance scenarios covered;
7. what it explicitly does not implement.

## Immediate work split
**Planning here:** continue Stage 1+ design, especially Human Psyche semantics, information contracts, later dependency maps and acceptance scenarios. Planning changes may be committed as documentation.

**Astra when available:** resume and finish Stage 0.5 only. Do not implement Stage 1 architecture until the current simulation has passed stabilization and the gold baseline is recorded.

This preserves a clean before/after comparison: first make the existing simulation solid; then transform it deliberately.
