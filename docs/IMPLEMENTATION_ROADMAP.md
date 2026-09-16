# ATE Implementation Roadmap v1

**Purpose:** stage the living design into bounded engineering work. This is sequencing, not permission to redesign canon.

## Work classification
Every proposed change must be tagged before implementation:
- **KEEP:** existing system already supplies the required primitive.
- **EXTEND:** existing authority remains; add fields/contracts/indexes/behavior.
- **MIGRATE:** deliberate compatibility transition is required.
- **NEW PRIMITIVE:** no existing authority provides the concept.
- **DERIVED:** should be composed from primitives rather than persisted as a new causal truth.
- **DEFER:** design/canon is not settled or dependency is not ready.

## Stage 0 — Baseline lock and audit
**Goal:** know exactly what exists before changing foundations.

Deliverables:
- map `LIVING_DESIGN.md` requirements to existing modules;
- identify KEEP/EXTEND/MIGRATE/NEW/DERIVED/DEFER;
- preserve canonical tests/digests/performance gates;
- document checkpoint/schema compatibility constraints;
- confirm current magic completion/access calibration baseline separately from architecture work.

**Best owner:** Astra/repo-wide agent for inspection; planning/review here.

## Stage 1 — Foundation contracts
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

**Gate:** no omniscient information leakage; deterministic replay; existing magic chronology preserved; benchmark regression understood and bounded.

**Best owner:** Astra for integration spine. Smaller agents may implement isolated tests/projections after contracts are frozen.

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
- Stage 0 repo audit;
- schema/checkpoint migrations;
- Psyche/Agency integration spine;
- Observation/knowledge authorization boundary;
- seed architecture;
- event scheduling/cadence/performance infrastructure;
- cross-system integration and final millennium optimization.

### Safe to delegate after interfaces freeze
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

## Immediate next planning work
Before another large Astra coding pass, finish the Stage 0 audit matrix and freeze the Stage 1 data contracts sufficiently that Astra is primarily coding, integrating, profiling, and validating rather than inventing architecture.
