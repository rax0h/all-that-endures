# ATE Implementation Architecture v1

**Status:** planning authority beneath `PROJECT_CONSTITUTION.md`, `simulation/CURRENT_STANDARD.md`, and `LIVING_DESIGN.md`.

## Purpose
Translate the living design into implementation contracts without asking a coding agent to invent the design while coding it. Existing executable systems remain authoritative until deliberately migrated. Inspect before replacing.

## Authority chain
1. `docs/PROJECT_CONSTITUTION.md`
2. `simulation/CURRENT_STANDARD.md`
3. `docs/LIVING_DESIGN.md`
4. this document
5. `docs/IMPLEMENTATION_ROADMAP.md`
6. task/PR acceptance criteria
7. implementation

Conflicts move upward for reconciliation; lower layers do not silently improvise.

## Existing foundations to extend, not duplicate
The repo already contains typed objective Events/causal edges, deterministic namespaced RNG, genealogy/households, social graph, economy, knowledge/transmission, culture, communities, skills, infrastructure, agency, advancement, magic resources, institutions, metaphysics/divinity, materials/provenance, warfare, Society accountability, ranked currency, threat ecology, archive/inspector, and a read-only personhood projection.

`PERSONHOOD_HISTORY_EXPRESSION.md` already establishes: objective record -> observation -> memory/belief -> public claim -> authored interpretation. Preserve this split.

Current `agency.py` is a useful prototype, not the final Human Psyche: it computes transient motives and chooses among a small action set. Expand through compatible contracts rather than creating a second decision engine.

## Shared primitives
### Identity / personhood
Stable identity is independent from embodiment. Where canon permits, different sapient embodiments should use common higher-level contracts. Species is not personality, morality, culture, or intelligence.

### Objective Event
`Event` remains authoritative truth that something happened. Participation does not imply perception or knowledge.

### Observation
Bounded evidence an observer actually had access to, through a channel. Observation is the gateway from objective truth into a subjective mind.

### Knowledge / Belief
Structured claims held with confidence, evidence/source lineage, and acquisition/revision history. NPC decisions consult beliefs, never unavailable omniscient truth.

### Memory
Bounded subjective references to consequential experience/claims, not copied prose or full archives. Carry owner, evidence, acquisition/channel, salience, confidence, emotional relevance, and interpretation. Forgetting changes accessibility, never objective history.

### Psyche
Separate slow temperament/dispositions, revisable values/identity commitments, current drives/emotions, self-concept, and a small active goal set. No hero/villain/leader/hermit personality classes.

### Relationship
Preserve the current social graph during migration. Add sparse directional assessments only where evidence exists: affection, trust, respect/admiration, fear, attraction, resentment, obligation, rivalry/dependency as required. A-to-B need not equal B-to-A.

### Agency
One decision architecture for major choices. Candidate actions come from goals + knowledge + opportunity. Evaluation uses temperament, values, drives, beliefs, relationships, expected consequences, capability, resources, and bounded rationality. Deterministic weighted stochastic choice resolves among plausible alternatives. Agency chooses attempts; domain systems resolve feasibility/outcomes.

### Institution
Share lifecycle primitives where possible: founding cause, founders, membership/constituency, resources/property, roles/rules, knowledge/practices, legitimacy/reputation, succession, alliances/rivals, growth/reform/schism/merger/decline/collapse. Schools, guilds, governments, religions, companies, Society branches, and criminal organizations specialize this rather than duplicating it.

### Record / institutional memory
Durable information objects: deeds, contracts, cases, births/deaths/marriages, taxes, reports, enrollment, correspondence, plans. Records may be copied, forged, hidden, lost, destroyed, preserved, or rediscovered. Evidence is not automatic truth.

### Provenance
Extend existing provenance; never create a parallel artifact-history system. Historical significance is derived from actual maker/origin/material/custody/use/event associations.

### Information object
Bounded transferable ideas/works/techniques/discoveries with creator/source, semantic/domain tags, prerequisites, accuracy/uncertainty, accessibility, prestige, variants, transmission/provenance, and institutional associations. Full generated text is not required for simulation truth.

### Reputation / model of others
Observer/group-relative, evidence-backed beliefs about conduct/capability. Never a universal morality/fame score.

### Entropy
Preserve deterministic isolated streams. Target separate World Seed and History/Entropy Seed while guaranteeing exact replay from world + history + version/config.

## Causal pipeline
`world condition -> opportunity/evidence -> authorized perception -> belief/memory update -> drives/goals -> Agency attempt -> domain resolution -> objective Event -> consequences -> new evidence/relationships/records/provenance -> future decisions`

Narrative/historian/expression layers read authoritative state; they never invent facts backward into reality.

## Three-speed cadence
**Background:** slow/event-triggered temperament development, values, identity, cultural exposure, long-term relationships, magical aspirations.

**Active:** bounded goals/current concerns, reconsidered on sparse cadence or material state change.

**Event reaction:** deeper processing after consequential events such as death, birth, betrayal, attack, inheritance, humiliation, disaster, magical opportunity, promotion, or crime evidence. Only affected/aware entities react.

Performance rule: prefer indexed event fan-out over person x event scans. Use bounded memory/goals, sparse relationship dimensions, lazy decay, persistent indexes, and deterministic queues.

## Combat / injury contract
Rank creates major capability differences but no absolute `lower_rank_cannot_kill_higher_rank` rule. Combat unfolds through time: position, abilities, terrain, objectives, endurance, injury, resources, morale, escape, allies, arrival times, and healing.

Separate injury severity, immediate lethality, remaining survival window, and healing/repair rate. Resilience, rank, regeneration, or unusual physiology may extend viability without repairing damage. External healing succeeds only if it arrives/acts before viability closes. Rare rank upsets must be causally produced, never injected for drama.

## Data ownership
- Reality owns objective state/events.
- Perception controls evidence entering minds.
- Subjective mind owns memories/beliefs/self-model.
- Social owns relationships/interpersonal evidence.
- Agency owns evaluation/choice, not domain outcomes.
- Domain systems own feasibility/resolution.
- Archive/historian reads outputs but cannot alter truth.
- Expression may verbalize authorized state but cannot create authoritative facts.

## Seed migration target
Current `World.seed`/`RNG(seed)` is an existing determinism foundation. Do not casually break golden digests. Introduce World/History seed separation through explicit versioned migration and tests:
1. same world+history+version => exact digest;
2. same world, different history => same initial state, divergent valid history;
3. isolated namespace additions should not perturb unrelated streams where feasible.

## Behavioral acceptance scenarios
1. Comparable children raised in materially different households can become meaningfully different adults without destiny flags.
2. A person cannot act on a secret opportunity never perceived or learned.
3. Different observers can retain different beliefs about one objective event.
4. Trust can fall or recover through evidenced conduct without erasing history.
5. An unwitnessed murder with surviving evidence may remain unsolved, be solved later, or produce a mistaken accusation through actual evidence/investigation.
6. Destroying the only accessible copy/teacher of a technique before transmission can make it unreachable until independent rediscovery.
7. A founder's death may collapse an institution or leave it functioning depending on actual succession/resources/roles/legitimacy.
8. A mundane provenance-tracked object can become culturally important through later history without spawning as a relic.
9. An Iron almost always loses a clean direct confrontation with a healthy Silver-level threat, while extraordinary causal circumstances can still produce survival/upset.
10. A critically injured person can die despite a nearby healer if the survival window closes first; resilience or allies buying time can change the outcome.
11. Reputation differs by observer/group based on known evidence.
12. Same World Seed + alternate History Seed preserves the starting world while allowing different trajectories.
13. Remove culture labels and recognizable cultural patterns remain reconstructable from actual history.
14. Canonical 1,000-year benchmark remains <=120 seconds; semantic depth cannot be purchased by weakening the gate.

## Foundation non-goals
Do not yet implement authored cosmology, full divine agency, free-form LLM dialogue, complete natural-language evolution, universal crime solving, global morality, story arcs, faction menus, tech trees, or bespoke villain/hero systems.

## Architecture principle
**Build causes once, let many stories use them.** A murder, school, marriage, feud, religion, invention, or legendary rescue should compose shared people/events/knowledge/relationships/institutions/provenance rather than require a special narrative engine for each story type.
