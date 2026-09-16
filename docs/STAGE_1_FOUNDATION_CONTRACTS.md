# ATE Stage 1 Foundation Contracts v1

**Status:** implementation specification. This document freezes the Stage 1 attachment points before coding.  
**Scope:** mastery projection, seed separation, Observation, Memory, Psyche, directional social assessment, Agency v2, cadence/indexes, compatibility and tests.  
**Non-goal:** this is not permission to implement Stage 2+ society features early.

## 1. Authority and invariants

Authority chain:
1. `docs/PROJECT_CONSTITUTION.md`
2. `simulation/CURRENT_STANDARD.md`
3. `docs/LIVING_DESIGN.md`
4. `docs/IMPLEMENTATION_ARCHITECTURE.md`
5. `docs/STAGE_0_AUDIT_MATRIX.md`
6. this document
7. `docs/IMPLEMENTATION_ROADMAP.md`
8. PR acceptance criteria
9. code

Stage 1 MUST preserve these invariants:
- `Event` remains objective history. Actors/location/causes do not imply perception.
- `KnowledgeState` remains the claim/belief authority and is extended, not duplicated.
- `SocialGraph` shared relationship/history remains during migration.
- `AgencyState` remains the decision-engine authority and is extended, not replaced.
- domain systems resolve outcomes; Agency chooses attempts.
- existing provenance/transmission/institution systems are not duplicated.
- no global morality, villain, hero, leader, personality-type, faction-loyalty or universal reputation score.
- no Stage 1 rebalance of canonical magic pacing/access.
- no NPC may query omniscient archive/history as knowledge.
- <=120 seconds for the canonical 1,000-year benchmark remains a hard gate.

## 2. Compatibility strategy

Stage 1 is a **versioned migration**, not a flag-day rewrite.

### Compatibility modes
During implementation, support two explicit modes:
- `legacy_v1`: current single-seed/Agency behavior for golden fixtures and migration comparison.
- `subjective_v2`: new seed/Observation/Memory/Psyche/directional-social/Agency contracts.

The mode is configuration, not hidden state. New tests must state which mode they exercise. Once v2 passes behavioral/performance gates, a later authority change may make it default. Do not silently delete legacy behavior in the same PR that introduces a primitive.

### Checkpoints
Current checkpoint schema is 4 and stores `year`, one `seed`, digest and pickled `World`. Stage 1 persistent state requires a schema bump only when the first persistent v2 field lands.

Rules:
- schema-4 checkpoints remain loadable through an explicit migration path while Stage 1 is active;
- migration must never invent subjective facts;
- missing v2 state is initialized as **unknown/empty**, except values directly evidenced by legacy persisted fields;
- migrated checkpoint output receives the current schema and a deterministic migrated digest;
- archive schema and checkpoint schema remain separate concerns;
- never refresh golden digests merely to silence failures; every expected digest change must be explained by an approved migration.

## 3. Seed contract

### Persistent seed state
Target world fields:
```python
world_seed: int
history_seed: int
simulation_version: str
```

Compatibility alias during migration:
```python
seed  # legacy fixture input only; not a third causal seed
```

### Semantics
- `world_seed` controls initial physical/geographic/start-state generation and deterministic identity/name inputs that exist before historical simulation begins.
- `history_seed` controls stochastic choices/events after the starting state is fixed.
- deterministic semantic construction that is a property of an already-fixed object may use stable object inputs; it must not accidentally couple unrelated histories.
- same `world_seed + history_seed + simulation_version + config` => exact replay.
- same `world_seed`, different `history_seed` => byte/canonical-equivalent initial state before history begins, then permitted divergence.

### Legacy mapping
For a schema-4/single-seed run in `legacy_v1`, preserve current RNG semantics exactly.
For a migrated run where no explicit history seed exists:
```text
world_seed = legacy seed
history_seed = deterministic domain-separated derivation of legacy seed
```
The derivation string/version must be frozen in code/tests. Do not use Python process hash.

### RNG namespaces
Keep the current namespaced stream model. New namespaces should be stable nouns/verbs such as:
- `observation_access`
- `observation_noise`
- `memory_retention`
- `psyche_background`
- `goal_reconsideration`
- `agency_v2`

A namespace is part of replay compatibility once released. Renaming one is a migration.

## 4. Mastery-stage projection contract

No persisted `stage` field in Stage 1.

Existing per-ability state remains authoritative:
```python
rank: int
level: int       # 0..9 within rank
progress: float  # 0..1 within level
```

Projection:
```python
rank_fraction = clamp((level + progress) / 10.0, 0.0, <1.0)
stage = min(4, floor(rank_fraction * 4) + 1)
stage_fraction = rank_fraction * 4 - floor(rank_fraction * 4)
stage_percent = stage_fraction * 100
```

Examples:
- level 0, progress 0.0 -> Stage 1, 0%
- level 2, progress 0.5 -> Stage 2, 0%
- level 5, progress 0.0 -> Stage 3, 0%
- level 7, progress 0.5 -> Stage 4, 0%
- Stage 3, 0% means 50% through the current rank.

Rank advancement remains dependent on the canonical complete 20-skill path and existing advancement gates. Projection must not alter gain, level, rank, revelation or integration state.

## 5. Observation contract

Observation is the only direct gateway from objective events/evidence into a mind.

### Proposed state
```python
@dataclass
class Observation:
    id: int
    observer: int
    acquired_year: int
    channel: str
    source_event: int | None = None
    source_claim: int | None = None
    source_entity_kind: str | None = None
    source_entity_id: int | None = None
    evidence_refs: tuple[tuple[str, int], ...] = ()
    perceived_fields: tuple[str, ...] = ()
    clarity: float = 1.0
    reliability: float = 1.0
    location: int | None = None

@dataclass
class ObservationState:
    observations: dict[int, Observation]
    by_observer: dict[int, list[int]]
    by_event: dict[int, list[int]]
    next_id: int
```

### Rules
- exactly one of `source_event`, `source_claim`, or a defined evidence source may be primary; composite observations reference evidence refs.
- an observation does **not** copy an entire Event payload.
- `perceived_fields` declares what information was accessible. Missing fields remain unknown.
- channels are controlled vocabulary, initially: `direct`, `heard`, `read_record`, `taught`, `inferred`, `magical`, `institutional_notice`.
- `clarity` models perceptual completeness; `reliability` models source/channel trustworthiness. Neither equals objective truth.
- no random roll is required for obvious direct perception. RNG is used only when perception/noise is genuinely uncertain.
- observations are immutable evidence records. Later belief changes do not rewrite them.

### Access authorization
Observation creation occurs only through domain adapters that can justify access. Initial authorization helpers may use:
- actor/target identity when the event itself necessarily entails awareness;
- co-location and event visibility/audibility class;
- explicit communication/transmission;
- possession/access to an in-world record/evidence object;
- magical perception ability when actually modeled.

There is no generic rule `event.actors -> know event.data`.

## 6. Knowledge / belief extension

Keep `KnowledgeClaim` and `KnowledgeState`; extend them.

### Claim
A claim remains a proposition about a subject. `truth` is omniscient developer/world metadata and **must never be consulted by NPC Agency**.

Add stable semantic support as needed:
```python
kind: str = 'proposition'
origin_event: int | None
```

### Belief evidence
Replace bare confidence-only semantics over time with an evidence-backed assessment:
```python
@dataclass
class BeliefAssessment:
    person: int
    claim: int
    confidence: float
    evidence: tuple[int, ...] = ()       # Observation IDs
    last_revised_year: int = 0
```

Compatibility may continue exposing `beliefs[(person, claim)] -> confidence` until consumers migrate.

Rules:
- confidence changes require observation/evidence, memory reinterpretation, trusted testimony, or explicit inference.
- contradictory evidence can coexist; revision is not automatic truth convergence.
- `KnowledgeClaim.truth` is excluded from decision APIs.

## 7. Memory contract

Memory is bounded subjective state, not a duplicate event archive.

### Proposed state
```python
@dataclass
class Memory:
    id: int
    owner: int
    acquired_year: int
    last_reinforced_year: int
    observation_ids: tuple[int, ...] = ()
    claim_ids: tuple[int, ...] = ()
    related_entities: tuple[tuple[str, int], ...] = ()
    salience: float = 0.0
    accessibility: float = 1.0
    confidence: float = 1.0
    valence: float = 0.0
    arousal: float = 0.0
    interpretation_tags: tuple[str, ...] = ()

@dataclass
class MemoryState:
    memories: dict[int, Memory]
    by_owner: dict[int, list[int]]
    next_id: int
```

### Bounds
Initial engineering cap: **64 retained episodic memories per person**. This is a performance default, not metaphysical canon. PR benchmarks may justify a different cap, but it must remain bounded.

When over cap:
1. never delete objective events/observations/claims;
2. retain highly salient/recent/reinforced memories preferentially;
3. low-accessibility memories may be evicted from active memory state;
4. eviction means the person no longer has accessible episodic recall, not that history vanished.

### Decay
No annual per-memory mutation across the population. Accessibility is lazily evaluated from stored accessibility, elapsed years, salience/reinforcement and psyche factors when queried/reconsidered. Material reinforcement writes a new `last_reinforced_year`/state update.

### Formation
Not every observation creates an episodic memory. Formation probability/priority depends on consequence, salience, novelty, emotional arousal, personal relevance and repetition. Obvious formative events may be deterministic.

## 8. Psyche contract

Persistent Psyche is separate from biological `Person` and from read-only `PersonhoodView`.

### Temperament dimensions v1
Use a compact non-moral vector:
- sociability
- empathy
- assertiveness
- conscientiousness
- openness
- risk_tolerance
- aggression
- patience
- baseline_trust
- ambition
- competitiveness
- independence
- emotional_volatility
- curiosity
- status_sensitivity
- injustice_sensitivity

Values are normalized floats only when modeled; **missing is `None`, not 0.5**.

### Persistent state
```python
@dataclass
class TraitValue:
    value: float | None
    confidence: float = 1.0
    evidence: tuple[int, ...] = ()
    last_changed_year: int | None = None

@dataclass
class Commitment:
    key: str
    strength: float
    evidence: tuple[int, ...] = ()
    last_changed_year: int = 0

@dataclass
class SelfBelief:
    claim_id: int
    confidence: float
    evidence: tuple[int, ...] = ()

@dataclass
class DriveState:
    key: str
    intensity: float
    updated_year: int
    cause_refs: tuple[tuple[str, int], ...] = ()

@dataclass
class Goal:
    id: int
    owner: int
    kind: str
    target: tuple[str, int] | None
    strength: float
    created_year: int
    source_refs: tuple[tuple[str, int], ...] = ()
    status: str = 'active'

@dataclass
class Psyche:
    person: int
    temperament: dict[str, TraitValue]
    values: dict[str, Commitment]
    self_beliefs: dict[int, SelfBelief]
    drives: dict[str, DriveState]
    active_goals: list[int]
    last_background_update: int
    last_goal_review: int

@dataclass
class PsycheState:
    people: dict[int, Psyche]
    goals: dict[int, Goal]
    next_goal: int
```

### Goal bound
Maximum **5 active goals per person** in Stage 1. This is an engineering cap. Completed/abandoned goals may be represented by consequential events/history rather than retained forever in active state.

### Legacy migration
Legacy fields are evidence, not a complete personality.
- `Person.curiosity` -> `curiosity` trait may be migrated directly.
- `Person.inhibition` informs but is **not identical to** patience/risk tolerance/conscientiousness. Do not fabricate exact mappings.
- `Person.attachment` is not empathy/sociability. Keep as legacy evidence until development/social migration defines its role.
- `Person.temperament` is too semantically broad to populate sixteen dimensions. Preserve it as legacy evidence/compatibility input only.
- grief/fear may seed matching current drives/emotions because they are directly persisted states.

Newborn/new-person initialization under v2 uses deterministic developmental initialization defined in a later Stage 1 PR; it must not infer morality or adult values.

## 9. Directional social assessment contract

Preserve current `Relationship(a,b, shared_history...)` as shared relational history/compatibility state.

Add:
```python
@dataclass
class SocialAssessment:
    observer: int
    subject: int
    affection: float | None = None
    trust: float | None = None
    respect: float | None = None
    fear: float | None = None
    attraction: float | None = None
    resentment: float | None = None
    obligation: float | None = None
    rivalry: float | None = None
    dependency: float | None = None
    evidence: tuple[int, ...] = ()       # observation/memory IDs
    last_updated_year: int = 0

@dataclass
class SocialAssessmentState:
    assessments: dict[tuple[int, int], SocialAssessment]
    by_observer: dict[int, set[int]]
```

Rules:
- sparse: no edge until evidence/interaction requires one;
- directional: A->B and B->A independent;
- `None` = unknown/unmodeled, not neutral;
- broad reputation is derived from observer/group assessments and evidence, not stored here as global truth;
- shared-history event IDs remain on `SocialGraph`.

## 10. Agency v2 contract

Agency chooses **attempts**, not outcomes.

### Inputs
Agency may read only:
- current authorized beliefs/memories;
- Psyche temperament/values/drives/self-beliefs/goals;
- directional social assessments available to the person;
- direct bodily/current-resource state the person necessarily knows;
- domain-provided known opportunities;
- modeled capabilities/skills;
- bounded expected consequences inferred from known state.

Agency may not read hidden event truth, claim `truth`, inaccessible inventories/records, future state or archive interpretations.

### Candidate interface
```python
@dataclass(frozen=True)
class ActionCandidate:
    kind: str
    domain: str
    target: tuple[str, int] | None = None
    opportunity_ref: tuple[str, int] | None = None
    known_cost: float | None = None
    known_risk: float | None = None
    metadata: tuple[tuple[str, object], ...] = ()

@dataclass
class DecisionTrace:
    year: int
    person: int
    goal_ids: tuple[int, ...]
    candidates: tuple[str, ...]
    chosen: str
    motive_weights: tuple[tuple[str, float], ...]
    value_weights: tuple[tuple[str, float], ...]
    relationship_refs: tuple[tuple[int, str], ...]
    belief_refs: tuple[int, ...]
    rng_namespace: str
```

Decision traces are bounded diagnostics, not autobiographical prose and not permanent objective facts unless a consequential attempt emits an Event.

### Evaluation
A candidate score is a transparent weighted combination of relevant drives, values, temperament, goal fit, expected consequences, social considerations, capability/resources and uncertainty. No single universal utility formula must encode every domain; domain adapters may provide candidate-specific features, but they cannot bypass Agency for major human choices.

### Choice
- discard impossible candidates known to the actor;
- retain a bounded plausible set;
- weighted stochastic choice among plausible alternatives using `agency_v2` isolated stream;
- extreme weights may make choices effectively deterministic;
- bounded rationality is produced by incomplete beliefs, uncertainty, temperament/drives and limited candidate generation—not by injecting arbitrary stupidity rolls.

### Resolution
Agency returns an `ActionCandidate`/attempt. The owning domain resolves feasibility and outcome and emits objective events. Resulting events may create observations/memories/relationship changes and future goal revision.

## 11. Cadence and scheduling

### Background cadence
Psyche developmental/background reconsideration:
- children/adolescents: event-driven plus sparse periodic review;
- adults: no more than once per 5 simulated years absent consequential triggers in Stage 1;
- temperament changes should be rare/small; values/self-concept may change more readily after evidence.

### Active cadence
Goal review occurs on:
- goal completion/failure/blockage;
- material household/resource/status change;
- major relationship change;
- newly learned consequential opportunity/threat;
- periodic sparse fallback, initially no more than once per simulated year for active adults.

### Event reaction
Consequential events enqueue only plausible observers/affected persons. Reaction processing may update observations, memories, drives, beliefs, social assessments and goal-review flags.

### Required indexes/queues
At minimum:
- observations by observer/event;
- memories by owner;
- beliefs by person/claim (existing compatibility plus richer assessment index);
- social assessments by observer;
- active goals by owner;
- pending event reactions by person/year;
- known opportunity index supplied by domain where necessary.

No Stage 1 feature may scan all historic events for every living person each year.

## 12. Birth, death and resurrection semantics

Stage 1 only establishes state lifecycle:
- birth/new sapient person creates empty subjective state and appropriate developmental Psyche shell;
- death stops active goal/Agency scheduling but does **not** delete observations, memories, beliefs, relationships, provenance or history;
- inactive/dead subjective state may be compacted only by an explicit archival policy that preserves required historical queries;
- resurrection, if existing mechanics produce it, reactivates the same identity and retained subjective state. Stage 1 does not redesign resurrection canon.

## 13. Persistence and canonical digest

All persistent causal v2 state is included in `World.digest()` through normal dataclass canonicalization. Pure derived indexes/caches must be excluded from canonical state by convention (underscore-prefixed runtime attributes or explicit rebuildable containers outside persisted dataclass fields).

Persist:
- seed/version/config identity needed for replay;
- observations;
- belief assessments;
- retained memories;
- psyche/goals;
- directional social assessments.

Do not persist as causal truth:
- mastery stage projection;
- universal reputation;
- personality type labels;
- hero/villain/leader classifications;
- narrative arcs;
- historian significance;
- cache/index order that can be rebuilt deterministically.

## 14. PR decomposition

### PR 1A — mastery projection
Files likely: `advancement.py`, tests, archive/diagnostic display only.
No schema bump. No pacing change.

### PR 1B — seed architecture
Add explicit world/history seed semantics, compatibility mode and deterministic tests. Avoid unrelated simulation changes.

### PR 1C — Observation
New state/module + `World` field + checkpoint migration + authorization tests. Integrate only a tiny representative set of event adapters first.

### PR 1D — Belief evidence + Memory
Extend `knowledge.py`; add bounded memory state. Belief APIs must stop exposing `truth` to Agency-facing callers.

### PR 1E — Psyche
Persistent schema, legacy evidence adapter, bounded goals, background/update scheduling. No broad behavior migration yet.

### PR 1F — directional social assessment
Add sparse state alongside `SocialGraph`; migrate one consumer and prove asymmetry.

### PR 1G — Agency v2 spine
Extend `AgencyState`, candidate/trace contracts, known-opportunity adapters and compatibility gate. Migrate a small coherent action subset before expanding.

### PR 1H — Stage 1 integration/performance
Behavioral scenarios, checkpoint round-trip/migration, deterministic replay, 100/1,000-year profiles, archive inspectability, compatibility cleanup proposal.

No PR should implement multiple later-stage systems merely because the new primitives make them possible.

## 15. Required tests

### Mastery
- exact boundary tests at 0, 25, 50, 75 and just below 100 percent;
- rank progression chronology unchanged before/after projection helper;
- incomplete path never becomes valid ranked user through projection.

### Seeds
- same world/history exact digest;
- same world/different history identical initial digest then allowed divergence;
- legacy mode reproduces frozen fixture;
- adding a new unused RNG namespace does not perturb existing streams.

### Observation/knowledge
- actor participation alone does not grant full payload knowledge;
- co-located observer sees only authorized fields;
- distant person learns only after a transmission/record channel;
- NPC-facing belief API cannot access claim truth;
- contradictory testimony can create different beliefs.

### Memory
- cap enforced deterministically;
- formative high-salience memory survives pressure from trivial memories;
- eviction does not delete objective event/observation;
- lazy decay yields same result regardless of query frequency.

### Psyche
- missing trait remains unknown rather than neutral default;
- legacy curiosity migration is exact;
- legacy broad temperament does not fabricate 16 dimensions;
- values/self-beliefs require evidence/change records;
- active goal cap enforced.

### Relationships
- A trusts B while B distrusts A is representable;
- shared history remains common;
- no assessment edge exists for strangers without evidence;
- reputation query can differ by observer/group without global score.

### Agency
- secret unavailable to person cannot generate candidate;
- candidate choice is deterministic for same inputs/seed;
- changing a known belief can change candidate weights without changing objective truth;
- Agency cannot directly mutate a domain outcome;
- decision trace identifies causal inputs without reading hidden truth.

### Performance/checkpoint
- schema-4 fixture migration deterministic;
- current-schema round trip exact digest;
- no unbounded memory/goals/decision-trace growth;
- no person x historical-event loop in profiling;
- canonical 1,000-year run <=120 seconds.

## 16. Stage 1 exit criteria

Stage 1 is complete only when:
1. mastery stages are available with unchanged progression timing;
2. World/History seed semantics and legacy compatibility are tested;
3. objective events can enter minds only through authorized Observation;
4. beliefs are evidence-backed and Agency-facing code cannot inspect objective truth;
5. memories are bounded, subjective and causally linked to evidence;
6. persistent Psyche exists without morality/type shortcuts or fabricated migration values;
7. directional social assessments coexist safely with shared relationship history;
8. Agency v2 chooses inspectable attempts from known opportunities and subjective state while domains resolve outcomes;
9. checkpoint migration/round-trip is deterministic;
10. 1,000-year performance gate still passes;
11. Stage 2 can attach to these contracts without introducing parallel psyche/knowledge/social/agency systems.

**Stage 1 north star:** the world may know everything that objectively happened; a person knows only what reached them, remembers only part of it, interprets it through who they have become, and acts from that bounded interior. The code must preserve that distinction cheaply enough to simulate a millennium.
