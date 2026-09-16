# ATE Implementation Roadmap v3

**Purpose:** stage the living design into bounded engineering work. This is sequencing, not permission to redesign canon.

## Work classification
Every proposed change must be tagged before implementation:
- **KEEP:** existing system already supplies the required primitive.
- **EXTEND:** existing authority remains; add fields/contracts/indexes/behavior.
- **MIGRATE:** deliberate compatibility transition is required.
- **NEW PRIMITIVE:** no existing authority provides the concept.
- **DERIVED:** should be composed from primitives rather than persisted as a new causal truth.
- **DEFER:** design/canon is not settled or dependency is not ready.

## Global architecture rules
- One authoritative owner per objective fact; many consequences are allowed, duplicate truth is not.
- NPC action consumes only legitimately available subjective information.
- Domain Agency chooses attempts; owning domains resolve outcomes.
- Derived summaries must not become independent causal truth.
- Prefer sparse state, indexes, event queues, lazy evaluation and aggregation.
- The canonical 1,000-year runtime target remains **<=120 seconds**, and that ceiling is not a budget to fill.
- Every major structural PR after the gold freeze reports deterministic 100/500/1,000-year runtime deltas.
- Coding agents do not invent answers explicitly left open by design specifications.

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
- economy, threat ecology, lineages/dynasties, institutions, provenance/materials and other existing systems for obvious runaway/dead behavior exposed by calibration changes.

### Canonical magic invariants during stabilization
- No person is Iron rank or above without all three base essences, confluence and all 20 skills unlocked.
- A partial path is rank 0. Rank-facing diagnostics/counts must not label incomplete paths as ranked.
- Rank advancement remains governed by all 20 abilities and existing canonical gates.
- Fix access/liquidity bottlenecks without weakening the 20-skill requirement.
- Preserve progression timing/curve unless evidence identifies a separate pacing defect.
- Do not manufacture Gold/Diamond counts by bypassing prerequisites, injecting completed paths or loosening rank rules merely to hit a target distribution.

### Calibration method
Instrument the causal funnel:
1. population eligible for magic;
2. first essence acquisition;
3. second essence acquisition;
4. third essence acquisition;
5. confluence creation;
6. awakening-stone acquisition/use;
7. 20/20 completed paths;
8. time spent at each rank/stage;
9. deaths/attrition before completion/advancement;
10. currency/resource stock, production, sinks, hoarding, trade and geographic/institutional access at each bottleneck.

The objective is not a predetermined exact number of Golds. The objective is an explainable mature distribution rich enough for the intended setting.

### Required stabilization validation
Validate representative 100-, 500- and 1,000-year runs for:
- exact determinism at fixed seed/config;
- complete-path invariant for every ranked person;
- no impossible currency/resource state or accidental infinite creation;
- inspectable acquisition/completion funnel;
- rank populations not dominated by implementation bottlenecks unrelated to canon;
- plausible long-lived rankers/lineages;
- coupled threat ecology/economy;
- coherent provenance/institutions/history;
- passing CI/tests;
- <=120-second canonical millennium benchmark.

### Gold-baseline freeze
Record on `main`:
- exact commit SHA;
- simulation/checkpoint/archive schema versions;
- benchmark command/config;
- representative seeds;
- runtime and calibration diagnostics;
- deterministic golden fixture/digest;
- intentionally deferred limitations.

All later migration is measured against this baseline.

**Best owner:** Astra/repo-wide integrator.

**Exit gate:** current ATE is deterministic, CI-clean, performant, canonically valid and sufficiently calibrated to freeze as the pre-subjective reference implementation.

## Stage 1 — Foundation contracts and subjective causality
**BLOCKED FOR IMPLEMENTATION until Stage 0.5 gold-baseline freeze.**

**Goal:** establish the subjective attachment points used by almost every later system.

Order:
1. isolated four-stage mastery projection/tests without pacing changes;
2. World Seed / History Seed migration infrastructure and deterministic tests;
3. Observation/access contract;
4. belief extension + bounded Memory;
5. persistent Psyche state;
6. sparse directional relationship assessments over existing shared history;
7. Agency v2 read boundary/DecisionTrace;
8. integration indexes/queues/performance.

Authority:
- `STAGE_1_FOUNDATION_CONTRACTS.md`
- `HUMAN_PSYCHE_SEMANTICS.md`
- `INFORMATION_BELIEF_EVIDENCE_MODEL.md`
- `RELATIONSHIPS_SOCIAL_LIFE_MODEL.md`
- `CROSS_SYSTEM_INTEGRATION_AUDIT.md`

**Gate:** no omniscient leakage; directional relationships react to perceived evidence rather than hidden truth; deterministic replay; existing magic chronology preserved; runtime regression bounded.

## Stage 2 — Human development and ordinary social life
**Dependencies:** Stage 1 Psyche, Observation, Memory/Belief, directional relationships and Agency.

Work packages:
- childhood/caregiver developmental influence;
- values/worldview/self-concept revision from experience;
- friendship and non-instrumental social interaction;
- kinship/family relationship development;
- attraction/courtship/partnership;
- promises, caregiving, rivalry, betrayal, forgiveness and reconciliation;
- bounded habits/appetites/vice responses;
- magical aspirations/preferences feeding existing opportunity/resource systems;
- employment/education/mentorship goals using existing economy/skills.

Authority:
- `HUMAN_DEVELOPMENT_MODEL.md`
- `RELATIONSHIPS_SOCIAL_LIFE_MODEL.md`
- `HUMAN_PSYCHE_SEMANTICS.md`

**Gate:** similar starts can diverge through history; relationships can be asymmetric; stable ordinary lives are common; no drama maximization; social work remains sparse.

## Stage 3 — Information society
**Dependencies:** Observation, Memory, Belief, relationships.

Work packages:
- rumor/hearsay transmission with source lineage;
- secrets/concealment/disclosure;
- observer/group-relative reputation;
- institutional records and archival memory;
- evidence objects/links and investigation beliefs;
- misinformation, contradiction, revision, rediscovery.

Authority: `INFORMATION_BELIEF_EVIDENCE_MODEL.md`.

**Gate:** truth remains separate from knowledge; investigations can fail; no universal reputation score.

## Stage 4 — Institutions, governance and collective action
**Dependencies:** Agency, relationships, records, existing institutions, minimum property/inventory/record interfaces.

Work packages:
- reconcile institution identity toward `institutions.py` without a third registry;
- generalized institutional lifecycle/succession;
- schools/apprenticeships/academies;
- governance legitimacy/succession;
- bureaucracy/record roles;
- collective action/factions through actual relationships/interests;
- law/enforcement legitimacy;
- corruption from incentives/dependency/conflicting obligations;
- crime/black markets/organized crime from incentives/networks;
- migration/class/dependency feedback.

Authority: `INSTITUTIONS_GOVERNANCE_POWER_MODEL.md`.

**Gate:** institutions arise, persist, reform, split, merge or die for causal reasons; no hive mind; founder death is not scripted collapse.

## Stage 5 — Knowledge, invention, art and civilization memory
**Dependencies:** information objects, records, institutions, existing provenance/transmission.

Work packages:
- transferable information objects;
- discovery/invention/combination/independent rediscovery;
- scholarship, criticism, competing theories;
- notices, letters, journals, inscriptions, books;
- art/music/folklore as grounded artifacts;
- loss/copying/censorship/preservation/translation;
- archaeology/historical reinterpretation;
- language/dialect ancestry/exposure foundation;
- provenance -> cultural/historical significance.

Authority: `CIVILIZATION_KNOWLEDGE_CREATION_MEMORY_MODEL.md`.

**Gate:** knowledge can genuinely disappear/reappear; ordinary objects can become relics through history; lore is reconstructable from the simulated past.

## Stage 5.5 — Physical world and ecology integration
**Dependencies:** existing world/settlement/threat ecology plus stable event/index architecture.

**Goal:** make environment a causal participant without spending the millennium performance budget.

Work packages:
- static geography/spatial indexes;
- climate/weather/season interfaces;
- lazy/aggregate water, soil, vegetation and wildlife state;
- agriculture/environment yield inputs;
- spatial resources and extraction effects;
- bounded disaster events;
- environmental degradation/recovery;
- settlement/environment feedback;
- existing ranked threat ecology integration through habitat/resource/disturbance inputs;
- environmental traces/provenance where historically consequential.

Authority: `WORLD_ECOLOGY_ENVIRONMENT_MODEL.md`.

**Performance rule:** environmental depth must not materially compromise the canonical <=120-second millennium target. Resolution degrades before the runtime ceiling is consumed. Prefer regional aggregate state, lazy elapsed-time updates, event-driven transitions and deterministic reconstruction. No per-tree/per-animal/per-square-meter simulation.

**Gate:** environment creates causal pressures rather than authored famine/disaster stories; same storm can have different consequences due preparation/exposure; deterministic millennium runtime remains bounded with meaningful headroom.

## Stage 5.75 — Material civilization, economy and settlements
**Dependencies:** physical environment interfaces, existing economy/materials/infrastructure/property, institutions.

Work packages:
- bulk inventories and actual production/consumption;
- food storage/spoilage/transport;
- sparse markets/prices/trade;
- property/possession/access/location distinctions;
- housing/crowding/access;
- labor/business/debt/institution-finance interfaces;
- infrastructure projects/maintenance/material requirements;
- roads/irrigation settlement scalars migrated toward derived projections;
- prosperity/scarcity/wealth compatibility summaries migrated toward richer authoritative state;
- carrying capacity derived from food/water/housing/technology/trade rather than an independent cap.

Authority: `MATERIAL_CIVILIZATION_ECONOMY_SETTLEMENT_MODEL.md` and `CROSS_SYSTEM_INTEGRATION_AUDIT.md`.

**Gate:** goods do not appear from prosperity; trade moves actual resources; infrastructure consumes/sustains material inputs; migration reacts to known opportunities/pressures rather than omniscient best destinations; runtime remains sparse/bounded.

## Stage 5.9 — Ordinary health, disease, aging and reproduction
**Dependencies:** Stage 1 subjective information for perceived illness/care decisions, Stage 2 social/reproductive opportunity, Stage 5.5 environmental exposure, Stage 5.75 material nutrition/care access, existing biology/rank.

**Goal:** establish one bodily-life authority before focused injury/combat plugs into it.

Work packages:
1. shared persistent bodily-condition/recovery schema + derived legacy `health` projection;
2. lazy aging/senescence/natural-death causes calibrated to species/rank longevity;
3. nutrition/hydration/rest/environment exposure interfaces;
4. disease/exposure/immunity + cohort outbreak model;
5. care/treatment/healer/institution integration;
6. reproduction/conception/pregnancy/birth/infant-health migration from current compatibility rules;
7. permanent impairment boundary shared with later combat.

Authority: `HEALTH_DISEASE_AGING_REPRODUCTION_MODEL.md`.

**Performance rule:** healthy people remain dormant; aging is lazy; active conditions use scheduled/analytic progression; epidemics use contact/cohort indexes; pregnancy uses milestones. No daily all-person health loop.

**Gate:** natural death has a bodily cause; long-lived ranks obey canonical longevity; disease spreads through actual exposure networks; reproduction follows actual social opportunity; combat will have one health authority to consume rather than creating parallel HP truth.

## Stage 6 — Conflict, combat, injury, healing, rescue and war
**Dependencies:** Agency, relationships, information, institutions, material logistics, environment/terrain, Stage 5.9 bodily-health authority, existing warfare/threat ecology/magic.

Work packages:
- temporal encounter state/objectives;
- injury severity vs immediate lethality vs viability window vs healing rate;
- shared injury/health state and stabilization;
- rank resilience/regeneration effects;
- ally arrival/rescue/extraction;
- escalation from interpersonal conflict to organized violence;
- macro warfare integration with logistics, command, morale and institutions;
- civilian/displacement/property/infrastructure consequences.

Authority: `CONFLICT_COMBAT_INJURY_HEALING_MODEL.md`.

**Gate:** violence is temporal and causal; rank disparity is severe but not an absolute outcome lock; rare upsets have inspectable causes; healing does not imply resurrection; macro war does not become millions of focused duels.

## Stage 7 — Player-facing deep simulation
**Dependencies:** stable human/information/material/health/combat layers.

Work packages:
- player obeys same knowledge/evidence rules;
- Adventure Society judgment/star progression from demonstrated responsibility;
- contracts with objectives, not designer-approved solutions;
- one-life/death integration;
- player reputation/relationships without universal faction meter;
- interaction/expression contract; optional language renderer remains non-authoritative.

**Gate:** player relevance may change simulation resolution, never historical probability or hidden rules.

## Stage 8 — Cosmology, divinity and religion
**BLOCKED until objective cosmology is authored by design.**

After canon is settled:
- objective metaphysical laws;
- divine personhood/agency where appropriate;
- objective divine events separated from mortal belief;
- religions/institutions/schisms as human historical systems;
- theological disagreement despite objectively existing gods;
- explicit magical healing/resurrection/environmental effects where canon permits.

Astra must not infer metaphysical truth from convenient mechanics.

## Stage 9 — Full millennium integration/calibration
Repeated 100/500/1,000-year runs. Inspect histories, not only aggregate metrics.

Validate:
- determinism and alternate-history semantics;
- population, health and lineage stability;
- magic access/rank distributions;
- ordinary social-life distributions;
- institutional diversity/lifecycle;
- knowledge preservation/loss;
- environment/material feedback;
- disease/demography;
- conflict rates/escalation/war logistics;
- cultural differentiation;
- dead systems/runaway loops;
- archive inspectability;
- <=120-second canonical millennium gate with retained headroom.

Optimization must preserve causal semantics. Prefer indexes, sparse state, bounded work, event queues, lazy evaluation and aggregation over deleting depth.

## Delegation map
### Keep with Astra / repo-wide integrator
- Stage 0.5 stabilization/baseline freeze;
- schema/checkpoint migrations;
- Psyche/Agency integration spine;
- Observation/knowledge authorization boundary;
- seed architecture;
- event scheduling/cadence/performance infrastructure;
- cross-system authority migrations;
- final millennium optimization/integration.

### Safe to delegate after interfaces freeze AND Stage 0.5 closes
- four-stage mastery projection/tests;
- bounded memory utilities;
- directional relationship structures/tests;
- record/evidence schemas/indexes;
- institution lifecycle helpers;
- information-object structures;
- ecology aggregate primitives behind frozen interfaces;
- health condition containers/schedulers behind frozen interfaces;
- historian/diagnostic queries;
- benchmark fixtures/behavioral scenario tests;
- documentation/archive inspector extensions.

### Do not delegate independently yet
- current magic/currency/access calibration away from Astra's active stabilization thread;
- objective cosmology;
- final open health/reproduction/species calibration questions;
- final open environment/material representation questions;
- morality/ethics shortcuts;
- universal dialogue/personality generation;
- major magic balance changes;
- anything creating parallel provenance, agency, knowledge, institution, health, social, environment or event authority.

## PR sizing rule
A PR should normally introduce one primitive or one coherent integration slice plus tests. Avoid "implement society" PRs.

Each PR states:
1. authority documents;
2. existing modules inspected;
3. owner of each new field;
4. objective vs subjective vs derived state;
5. evidence/access boundary where relevant;
6. domain resolver/event fan-out;
7. state/schema/checkpoint changes;
8. RNG namespace changes;
9. 100/500/1,000-year performance delta where structural;
10. behavioral acceptance scenarios covered;
11. what it explicitly does not implement.

## Planning status at v3
The major pre-cosmology architecture is now specified deeply enough to stop inventing new top-level human/material subsystems for their own sake.

Completed design authorities include:
- Human Psyche;
- Human Development;
- Relationships & Social Life;
- Information/Belief/Evidence;
- Institutions/Governance/Power;
- Civilization Knowledge/Creation/Memory;
- World/Ecology/Environment;
- Material Civilization/Economy/Settlement;
- Health/Disease/Aging/Reproduction;
- Conflict/Combat/Injury/Healing/War;
- cross-system integration ownership/dependencies.

Remaining open questions inside those documents are implementation-time contract/calibration decisions unless explicitly marked as requiring design/canon. **Cosmology remains deliberately unresolved and must be authored before Stage 8.**

## Immediate work split
**Planning:** reconcile documents when genuine contradictions are discovered; do not keep adding architecture merely to add architecture.

**Astra when available:** resume and finish Stage 0.5 only. Do not implement Stage 1+ until the gold baseline is accepted and recorded.

Once Stage 0.5 closes, begin Stage 1 in the order above and use `CROSS_SYSTEM_INTEGRATION_AUDIT.md` as the ownership/dependency map.

> **Stabilize what exists. Freeze it. Add subjective causality. Build ordinary human life. Connect information and institutions. Deepen the physical/material world. Give bodies causal continuity. Resolve conflict through the same causes. Add the player. Author metaphysics deliberately. Then run a thousand years and see what endured.**
