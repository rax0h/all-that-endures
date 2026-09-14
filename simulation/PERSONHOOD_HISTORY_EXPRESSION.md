# Personhood, history and expression

Status: Stage A implemented with a minimal, read-only Stage B contract. Stages B–G remain staged work, not claims about current simulated minds. This document governs this initiative under `CURRENT_STANDARD.md` and the project constitution. Existing executable systems remain authoritative where more precise.

## Contract

Simulation creates truth. Memory preserves and distorts it. Individuals perceive only part of it. Culture transmits versions. Expression reveals an individual; narrative interprets what happened. A person exists before a sentence does.

This PR changes no annual simulation behavior, RNG calls, balance constants, canonical World fields or checkpoint schema. It adds an optional export after simulation and a read-only personhood projection. It does not give agents new access to truth or insert language generation into the engine.

## Existing foundations and limits

| Existing implementation | Authority and limits |
|---|---|
| `core.py`, `engine.py` | Stable person/event IDs; ordered typed actors, locations, causal edges. Person holds current/last biological and social state, not a full biography. Founder origins may precede simulation. |
| `genealogy.py`, `households.py`, `civilization.py` | Parent/child relations, partnership/household formation, migrations and inheritance. Current residence must not be presented as birthplace. |
| `social.py` | Symmetric relationship weights with shared event references; no separate A-to-B and B-to-A judgments. Some changes lack explicit per-dimension causes. |
| `agency.py` | Separate current motives, near-best stochastic choices and practice. Action records retain only a 50,000-entry tail; motive snapshots are not lifelong desires or beliefs. |
| `skills.py`, `development.py`, `craft_careers.py` | Practice, teachers, teaching events and occupational transitions. Recorded skill levels are achievements, not innate aptitude. Not all transitions have events; schooling/literacy are absent. |
| `knowledge.py`, `transmission.py` | Claims with nullable truth, individual confidence, source/target transmission and reliability. These are not complete perceptual histories. Teaching events can carry evidence even when a skill's provenance list is empty. |
| `culture.py`, `communities.py`, `institutions.py` | Practices, descent, adoption, memberships, laws, guilds, Society branches and registrations. Culture is mutable and overlapping, not a personality preset. Culture institutions and core institutions have distinct ID namespaces despite some legacy lineage refs sharing `institution`. |
| `species.py`, `biology.py`, `rank.py` | Embodiment, habitat fit, lifespan and rank changes. They do not establish species personalities or a universal intelligence scale. |
| `advancement.py`, `magic_resources.py`, `materials.py`, `economy.py` | Paths, aspirations with formation years, discovered/consumed resources, material inputs, created objects, recorded ownership and transfer events. Some objects lack a complete ownership journal; the exporter cannot recover absent facts. |
| `lineage.py`, metaphysics/divinity, warfare/threats | Typed descent, souls, transformations, institutions and environmental causes. A threat or supernatural object is not automatically a sapient person. |
| `checkpoint.py`, diagnostics, long-history tools | Pickled schema-4 checkpoints resume trusted simulations; canonical digest covers declared dataclass fields. Archive is a separate inspection format, not a replacement checkpoint. Aggregate diagnostics remain available. |

## Personhood is independent of embodiment

`personhood.py` introduces immutable `EntityIdentity(kind,id)`, `Embodiment`, `Capabilities`, `Dispositions`, `EmotionalState`, `SubjectiveState` and `PersonhoodView`. Current `Person` objects adapt without mutation. A future sapient spirit or construct can use the same contract without a household, reproductive parents or a species string. No such entity is spawned by this PR.

Identity is a stable referent, not self-concept. Dependencies are references, not proof of ownership or obedience. Origin, embodiment, mortality and dependency models are independent and may be unknown. Summoning, awakening and a summoner's death eventually require explicit origin/relationship events. Canon must establish their actual meanings before simulation rules are added.

Known temperament, attachment, curiosity, inhibition, grief and fear are copied from existing fields. Cognitive axes remain `None`: reasoning, learning, working memory, long-term memory, verbal, spatial, numerical, practical, social perception, creativity and attention. Unknown does not mean average, zero or incapable. No correlations or ranks are invented. Future persistence must be an explicit versioned state migration; this projection is not hidden authoritative state.

Capability != knowledge != skill != education != experience != personality != motive != outcome. Keep independent evidence and development mechanisms. Health, opportunity, teachers, prejudice, resources, accidents and institutions mediate outcomes. Recognize historical achievement from consequences after it occurs; never assign legendary importance at birth.

## Epistemic boundaries

Five levels remain distinct:

1. Objective record: an event happened, an object was transferred, or someone held a belief.
2. Observation: what an individual actually perceived, with channels and omissions.
3. Memory/belief: what they retain or accept, possibly mistaken.
4. Public claim: a culturally/institutionally transmitted assertion.
5. Authored interpretation: a later analysis or narration.

An objective record that someone believes X does not make X true. The archive preserves `KnowledgeClaim.truth=None` and confidence separately. Existing event `layer` records are preserved, not flattened into claims of universal truth. Actor participation never automatically creates a memory, observation or knowledge of all event data.

The inspector is an omniscient research tool, never the input directly handed to an NPC. Future perception services must authorize an evidence subset before mind/decision systems see it. Person A's impression of B must reference A's evidence, not B's private state. The player uses these same boundaries.

## Memory and subjective mind (planned)

Keep the objective archive append-only during future recording; memories are small subjective references plus interpretation, not copied prose. A bounded memory record needs observer identity, source event or source claim, acquisition time/channel, salience, confidence, emotional relevance and retained content. Hearsay requires speaker and transmission evidence. Forgetting or revision alters subjective accessibility, never objective history.

Use deterministic tie-breaking and explicit caps per mind. Evaluate salience at consequential perceptions; decay lazily or in bounded batches. No yearly person × all-events scans. Repetition, age, capacity, contradiction, trauma and cultural retelling can modulate retention in later validated work. Do not implement trauma as guaranteed permanent destiny. Distortion must preserve its epistemic label and source lineage.

`SubjectiveState` now exposes only existing per-person claim confidence. Observation, memory and self-claim tuples are empty because those systems do not yet exist. It does not claim the person has no experiences.

## Relationships, development and expertise (planned beyond existing evidence)

Retain the current social graph as a compatibility authority until a deliberate migration. Add directional assessments keyed by observer and subject, each with consequential evidence: trust, affection, resentment, fear, admiration, attraction, obligation, rivalry or dependency as needed. Do not allocate every dimension for every possible pair. A reason for distrust needs evidence; current symmetric resentment alone cannot answer why A dislikes B.

Identity commitments, values and ambitions should carry formation/revision evidence distinct from transient needs. An internal self-model may contradict achievement. Conflicting motives use the existing agency system rather than replacing it with prose planning. Traits bias choices with existing deterministic isolated streams; they do not prescribe destiny.

Development follows origin, household, caregivers, peers, teachers, migration, health, work and events across an actual lifespan. Long lifespan changes exposure and generational relationships, not automatic wisdom. Profession derives from practice and networks, with domain-specific attention and vocabulary. Literacy, schooling, reading, public speaking and writing practice remain independent. Missing schooling evidence means unknown, not illiterate. Existing skill thresholds and balance are outside this PR.

## Language ecology (Stage D, planned)

Languages and dialects become historical objects with parentage, contact, borrowing and transmission. Geography, households, migration, trade, institutions, occupation and reading establish exposure. Language does not equal species. Institutional standardization and prestige require causal events. Cultural practices can support education and etiquette, but must not become immutable civilization voices.

Represent accent mainly through syntax, rhythm, vocabulary, idiom, register and discourse habits. Avoid heavy phonetic spelling and caricature. Register depends on audience, relationship, setting, medium, intention and emotion. A person's home speech can persist alongside formal or professional registers. A reading history may supply vocabulary without speaking confidence.

## Interaction and expression (Stage E, planned)

World reality → authorized perception → interpretation through subjective memory/belief → competing motives → decision → disclosure intention → expression → another person's limited perception.

Perception, interpretation, internal thought, intention and expression are separate typed results. Silence and concealment are valid decisions. A person can recognize deception without revealing that recognition, or speak confidently while uncertain. One generator must never operate both private minds omnisciently. NPC–NPC and NPC–player interactions share the same contract.

A future language renderer receives only authorized character evidence, intention, communicative ability, audience and register. It cannot invent memories, transfer assets, resolve combat or establish facts. Any generated interpretation is an offline/non-authoritative artifact unless a later deterministic mechanism explicitly records it. This PR uses no LLM/API prose.

## Avoiding a universal machine voice

Do not delegate individuality to a final “sound human” prompt. Limit the renderer's evidence and linguistic capabilities. Do not let model reasoning, emotional insight or vocabulary leak into a character. Motivation need not be spoken. Banal practical exchanges, repetition, incomplete utterances, avoidance, misunderstanding and no thematic resolution are legitimate outcomes. No mandatory wit, metaphors, symmetry, insight or historical significance. People may discuss dinner while history changes nearby.

## Cultural artifacts and literature (Stages F–G, planned)

First represent ordinary authored objects: notes, notices, letters, inscriptions, records and journals. An artifact requires an author when known, medium, production event, intended audience, custody and transmission. Anonymous or misattributed authorship is a claim, distinct from objective production. Reading/copying, loss, censorship, translation and rediscovery require their own evidence.

Literary development combines perception, verbal aptitude, imagination, taste, reading, practice, discipline, opportunity, culture and audience. No `great_writer` flag. Public speaking is not writing. Excellence is an outcome, not a prior assignment. Works influence people through exposure; influence can later reach speech without remembered attribution. Historians may misinterpret earlier artifacts without changing the archive.

## Archive schema v1 (implemented)

SQLite with fixed DDL, sorted insertion and compact canonical JSON payloads per record, not an opaque whole-world JSON dump. `records(kind,id)` retains explicit allowlisted collections; tuple keys use compact JSON arrays. `events(id)` stores year, kind, original layer and full payload. `causes(event,cause,ordinal)` preserves edge order with foreign keys. `links(source_kind,source_id,relation,target_kind,target_id,ordinal)` indexes exact actor roles/order, event location, parents, material inputs, origin/consumption/transfer events, ownership, teachers, partnerships and person-linked snapshots. Reverse indexes support person/event/provenance queries.

`metadata` stores schema, seed, year, source World digest, collection manifest and coverage. No wall-clock timestamp or filename enters archive contents. A logical SHA256 covers ordered exported rows (excluding its own metadata row); identical SQLite versions/settings also produce identical database bytes. Physical SQLite layout across library versions is not the portable determinism contract.

Collections explicitly include people, households, settlements, genealogy, relationships, partnerships, skills, claims/beliefs, culture, communities, transmission, lineage, infrastructure, both institution registries, registrations/applications/notices, advancement, aspirations/motives, materials/items/resources/property, souls, divine entities, threats, conflicts, inquiries, wallets, ambient fields and trade routes. Derived indexes and caches are excluded. The retained action tail and adapted personhood views have their own record kinds. Personhood views are projections, not newly simulated achievements.

The file is created through a temporary database and published exclusively after success. Existing paths are never overwritten. Export validates causal direction, cause existence and linked event existence. Future schemas need explicit migrations or rejection; reader v1 rejects other versions. The reader opens SQLite read-only. Checkpoint loading remains trusted-input-only pickle and is not required by the inspector.

### Coverage and honest answers

Snapshots mean state at export, or last retained state for a dead person, not state at every previous age. Full event payloads retain details even where there is no typed secondary link. Ordered actors retain role evidence without inferring what anyone perceived. Missing information returns null/unknown; empty history is not proof nothing happened.

The archive preserves existing lineage refs, including institution ambiguity, without guessing a registry. `lineage_parent` links target lineage keys rather than an invented resolved institution. Current ownership and recorded historical ownership have distinct relations. Some resource transfers can be reconstructed only from the transfer event payload; absence of an initial-owner field must not be filled from a later snapshot.

No importance/strangeness rankings are claimed. Analysts may derive metrics from event counts or causal descendants, but must label the metric and avoid equating frequency with greatness. A causal chain is a recorded dependency graph, not proof that an expedition uniquely caused all later developments.

## Inspector (implemented)

Run from repository root:

```
PYTHONPATH=.:simulation python simulation/run_long_history.py 843000 100 --archive /tmp/ate-history.sqlite
python simulation/history_inspect.py /tmp/ate-history.sqlite metadata
python simulation/history_inspect.py /tmp/ate-history.sqlite records person --limit 10
python simulation/history_inspect.py /tmp/ate-history.sqlite person 1 --limit 30
python simulation/history_inspect.py /tmp/ate-history.sqlite settlement 3 20 40
python simulation/history_inspect.py /tmp/ate-history.sqlite provenance magic_resource 1
python simulation/history_inspect.py /tmp/ate-history.sqlite causes 100 --descendants
```

Use IDs from query results; examples do not assert significance. Person results include parent/household links, linked records and paginated actor timelines. Provenance exposes exact retained fields, links and events; follow material and origin references explicitly. Causal traversal is iterative/recursive-SQL, cycle-deduplicated and bounded, with truncation reported. Timeline uses stable year/ID order and explicit limit/offset. Settlement queries mean recorded location, not every resident's entire life. SQL remains available for research over indexed tables; no generative answers are fabricated.

## Performance, determinism and validation

There are zero changes to `Simulation.step`, `World`, `Person`, RNG or checkpoint serialization. Export is optional and runs after the separately timed simulation, diagnostics, digest and causal validation. Existing 120-second gate remains unchanged. `--archive` reports generation seconds, bytes and logical hash separately, including export validation. A caller can reuse the measured digest to avoid a duplicate archive hash of World. Large histories cost roughly O(records log records + links log links) during export, not each year. Compact payloads avoid repeating event bodies inside each person's history.

Tests must cover actual generated family/teaching/material/resource chains, deterministic bytes/logical rows across reordering and checkpoint restoration, unchanged continued simulation after export, unknown facts, read-only access, invalid causes, bounded deep chains and nonbiological personhood construction. Existing golden digests must not be refreshed. Use short profiles for development and one stable canonical run with archive metrics for acceptance. A slow runner must be reported, not excused by weakening gates.

## Roadmap and gates

- **A — Historical truth: implemented here.** Archive and inspector, with explicit retained-history limits. Extend typed links only from real producer evidence.
- **B — Personhood: contract/projection only here.** Later persist independent capabilities, developmental evidence, identities, enduring motives and directional relationship assessments. Requires schema compatibility and dedicated semantic tests.
- **C — Subjective mind: planned.** Perception access control, bounded memories, ignorance, rumor, revision and models of others. Must pass information-leakage tests.
- **D — Language ecology: planned.** Language descent, exposure, literacy, register and transmission, without species stereotypes.
- **E — Interaction: planned.** Independent minds, choices and disclosure, speech separate from thought, same rules for player.
- **F — Artifacts: planned.** Ordinary grounded writing and its custody/transmission before literary ambition.
- **G — Literature: planned.** Authors, readership, influence, preservation, criticism and historical reputation grounded in prior stages.

Broader economic calibration is separately deferred. This initiative does not reopen income, resource availability, Diamond rarity, Society behavior or production tuning.
