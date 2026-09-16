# ATE Stage 0 Audit Matrix

**Status:** Stage 0 baseline audit completed against `main` on 2026-09-15.  
**Authority:** `PROJECT_CONSTITUTION.md` -> `simulation/CURRENT_STANDARD.md` -> `docs/LIVING_DESIGN.md` -> `docs/IMPLEMENTATION_ARCHITECTURE.md` -> this audit -> `docs/IMPLEMENTATION_ROADMAP.md`.

## Classification key
- **KEEP** — existing system already owns the required primitive.
- **EXTEND** — keep existing authority and deepen it.
- **MIGRATE** — deliberate state/schema/compatibility transition is required.
- **NEW PRIMITIVE** — no current authoritative state supplies the concept.
- **DERIVED** — compute from causal primitives; do not persist as independent truth.
- **DEFER** — canon/dependencies are not ready.

## Baseline conclusions
ATE is not missing a simulation foundation. It already has objective typed events/causal edges, deterministic namespaced RNG, genealogy/households, social relationships, claims/beliefs, generic transmission records, cultural practices with descent/mutation/loss, institutions/Society branches, skills/teaching, material production and crafted-item provenance, ranked advancement, warfare/threat ecology, archive/inspection, and a read-only personhood projection.

The main architectural gap is **subjective causality**: persistent psyche, authorized observation, bounded memory, directional interpersonal models, and Agency consuming those states rather than objective world truth. Stage 1 should therefore deepen the existing spine rather than build parallel systems.

## Audit matrix

| Living-design requirement | Existing authority | Class | Stage / implementation note |
|---|---|---|---|
| Objective truth, typed events, causal edges | `core.py` `Event`, `Layer`, `Ref`, `World.emit` | KEEP | Reality/event authority remains canonical. Participation must not imply perception. |
| Deterministic isolated randomness | `core.py` `RNG.stream(namespace,year,entity)` | KEEP + MIGRATE | Keep namespaced streams; Stage 1 explicitly separates World Seed from History Seed without weakening replay. |
| World Seed / History Seed alternate histories | single `World.seed` + `RNG(seed)` today | MIGRATE | Versioned Stage 1 migration. Same world seed must reproduce initial conditions; history seed drives stochastic history. Golden/checkpoint compatibility must be explicit. |
| Person identity independent of embodiment | `personhood.py` immutable `EntityIdentity`, `Embodiment`, `PersonhoodView` | KEEP + EXTEND | Projection contract is correct; later persistent state must not silently infer currently unknown capabilities. |
| Rich temperament dimensions | `Person.temperament/attachment/curiosity/inhibition`; `personhood.Dispositions` | MIGRATE | Existing four fields are legacy evidence, not final psyche. Freeze a disciplined persistent temperament schema before migration; do not map missing dimensions to 0.5 by assumption. |
| Values / enduring commitments | none authoritative | NEW PRIMITIVE | Stage 1 Psyche. Values require formation/revision evidence and bounded storage. |
| Drives / emotions | `agency.MotiveState`; `Person.grief/fear` | EXTEND | Preserve transient motive concept. Add bounded drive/emotion state and evidence-triggered updates; avoid duplicating Agency motives. |
| Self-concept | `SubjectiveState.self_claims` placeholder only | NEW PRIMITIVE | Stage 1 persistent self-model with belief/evidence semantics. |
| Bounded active goals | current Agency chooses directly from action weights | NEW PRIMITIVE | Stage 1. Small goal set, sparse reconsideration; goals produce candidate attempts rather than outcomes. |
| Human Agency decision engine | `agency.py` motive assessment + near-best stochastic action choice | EXTEND | Agency v2 replaces no domain authority. It must consume authorized beliefs/goals/relationships and choose attempts; domain systems resolve. |
| Three-speed human cadence | annual `agency_step`; existing per-system annual steps | NEW PRIMITIVE + EXTEND | Add background/active/event-reaction scheduling/indexes without person x archive scans. |
| Observation / perception boundary | epistemic contract documented; no persistent observation system | NEW PRIMITIVE | Highest-priority Stage 1 primitive. Objective event -> authorized observation only for observers with access. Information-leakage tests mandatory. |
| Beliefs / uncertain claims | `knowledge.py` claims + per-person confidence | EXTEND | Preserve claim authority. Add evidence/source lineage, acquisition/revision semantics and indexes rather than parallel belief store. |
| Bounded episodic memory | `personhood.SubjectiveState.memories` placeholder; no memory state | NEW PRIMITIVE | Stage 1. References/interpretations, not prose or event copies. Bounded caps and lazy decay/reinforcement. |
| Hearsay / rumor | `transmission.py` generic source->target records with reliability/mutation | EXTEND | Stage 3 connects transmissions to authorized claims/memories and source lineage. Do not create a second rumor transport. |
| Secrets / concealment / disclosure | institutional magic records already model disclosure levels; no general secret primitive | EXTEND + NEW PRIMITIVE | Generalize disclosure/access-control semantics after Observation exists. A secret is restricted true information, not a magic flag. |
| Symmetric social history | `social.py` relationship edges, shared event history | KEEP | Keep as compatibility authority during migration. |
| Directional relationship assessments | current edge is symmetric for trust/attachment/etc. | NEW PRIMITIVE + MIGRATE | Stage 1 sparse A->B evidence-backed assessments. Do not destroy shared-history edge; migrate consumers deliberately. |
| Friendship / ordinary socializing | `social.py` supports edges; Agency has `socialize` | EXTEND | Stage 2 adds non-instrumental interactions and differentiated effects on relationship dimensions. |
| Attraction/courtship/partnership | `Relationship.attraction`, `partnerships`, household/genealogy systems | EXTEND | Stage 2. Distinguish attraction, affection, compatibility, loyalty, marriage/partnership and actual family consequences. |
| Parenting / development | genealogy, households, `development.py`, skills/teaching exist | EXTEND | Stage 2 uses caregivers, household, peers, teachers and events to shape mutable character/worldview. |
| Magical identity preference / aspiration | advancement paths and existing aspirations referenced by archive/personhood initiative | EXTEND | Stage 2 feeds psyche preferences into existing magic-resource/opportunity systems. Preference must never guarantee build. |
| Canonical 20-skill path requirement | `advancement.py` capacity 20; current design authority says incomplete path is unranked | EXTEND / VALIDATE | Preserve all-20 requirement in all rank-facing consumers. Audit any code that still treats partial paths as ranked before Stage 1 merges. |
| Four mastery stages inside rank | `AbilityProgress.rank`, `level` 0-9, `progress` 0-1 | DERIVED first | Stage 1 should derive four equal quarters from existing continuous within-rank progress unless a demonstrated gameplay need requires persisted stage. No pacing change. |
| Rank progression pacing | `advancement.practice` | KEEP | Do not rebalance during architecture work. Gold revelation/integration gates remain authoritative. |
| Magic access/completion liquidity calibration | existing resource/advancement economy; prior baseline identified low completed paths | DEFER (separate calibration) | Track independently from foundation architecture; do not hide architecture regressions by rebalance. |
| Culture as emergent history | `culture.py` practices, adoption, mutation, loss; `CURRENT_STANDARD.md` | KEEP + EXTEND | Preserve causal culture. Later connect psyche, institutions, information and migration; never reintroduce monolithic culture personality tags. |
| Technique/practice ancestry and mutation | `Practice.parent`, lineage/transmission innovation records | KEEP + EXTEND | Strong foundation for Stage 5 knowledge/invention. |
| General transferable information objects | claims, practices, transmission exist but no common bounded work/idea object | NEW PRIMITIVE | Stage 5 after subjective/institutional foundations. Must compose with existing claims/practices/transmission/provenance rather than supersede them. |
| Knowledge loss / rediscovery | practices can be lost; transmission exists; general idea loss/rediscovery incomplete | EXTEND | Stage 5. Loss must result from accessibility/teacher/copy history; independent rediscovery gets new provenance. |
| Institutions / branches / membership | `institutions.py`; separate legacy cultural institution registry | KEEP + MIGRATE | Keep current Society authority. Before generalized lifecycle, reconcile/bridge the two institution namespaces deliberately; do not add a third registry. |
| Institutional lifecycle / succession | founding/branches/membership exist; generalized succession/decline/schism absent | EXTEND | Stage 4 shared lifecycle primitive. Founder death should be an input, not a scripted collapse. |
| Emergent schools / mentorship | skills/teaching and institutions exist; schooling/literacy absent | EXTEND | Stage 4. Schools arise from teachers/demand/resources/property/legitimacy/succession. |
| Governance / legitimacy | cultural institutions have authority/legitimacy; laws have enforcement; no general governance authority model | EXTEND + NEW PRIMITIVE | Stage 4 should reuse legitimacy/law/institution primitives, adding roles/succession/coordination rather than `Kingdom` story objects first. |
| Law | `culture.Law(strictness,enforcement,origin_event)` | EXTEND | Add jurisdiction, recognized authority, adjudication/enforcement actors and records as needed. |
| Bureaucracy / institutional memory | branches have record IDs; archive exists; no mutable in-world general record object | NEW PRIMITIVE | Stage 3/4 durable in-world records distinct from omniscient export archive. Records can be forged/lost/destroyed/copied. |
| Collective action / group formation | communities/institutions/social graph | EXTEND | Stage 4 group formation must require relationships, shared goals/opportunity/resources. |
| Dependency / social leverage | wealth, households, property/material ownership, social obligation exist | EXTEND + DERIVED | Persist concrete obligations/contracts/property/employment where needed; derive broad “power” from networks rather than universal score. |
| Observer/group-relative reputation | no authoritative reputation model | DERIVED + NEW INDEX | Stage 3 model as evidence-backed beliefs/models held by observers/groups. Do not persist universal fame/morality truth. |
| Crime | objective events/property/social systems exist; no general crime economy/investigation loop | EXTEND | Stage 3 evidence + Stage 4 incentives/networks/law. Crime is behavior under conditions, not a criminal personality/faction flag. |
| Evidence / investigation | events/provenance/claims provide raw evidence; no case/inquiry decision system | EXTEND + NEW PRIMITIVE | Stage 3 evidence links/cases/investigator beliefs. Facts never directly set `guilty=true` in a mind. |
| Corruption | obligations/wealth/institutions exist | DERIVED | Agency under conflicting dependencies/values/risks. No corruption stat required as causal truth. |
| Conflict/grievance escalation | social resentment + settlement tensions + warfare | EXTEND | Add interpersonal grievance/escalation through Agency before organized warfare. Keep warfare as domain resolution, not human motive engine. |
| Warfare | `warfare.py` tensions/conflicts/battles | KEEP + EXTEND | Preserve macro conflict authority; later consume richer political/social causes and combat domain results. |
| Temporal combat encounters | warfare currently resolves probabilistic casualties annually | NEW PRIMITIVE | Stage 6 encounter state for player/important fights; must coexist with aggregate millennium-scale conflict resolution. |
| Injury / survival window / healing | biology resilience and mortality exist; current war casualty can kill immediately | NEW PRIMITIVE + EXTEND | Stage 6 separates injury severity, viability window, stabilization, healing rate, regeneration/resilience and rescue timing. |
| One-life / resurrection | mortality/metaphysics/divinity foundations exist; final gameplay contract not integrated | DEFER + EXTEND | Stage 7 after combat/injury; resurrection must be an in-world causal event and never rewind consequences. |
| Material production / crafted objects | `materials.py` lots/items with producer/crafter/materials/origin | KEEP | Existing authority. |
| Provenance / custody | materials record origin/current owner/transfers; archive exposes provenance but history can be incomplete | KEEP + EXTEND | Never duplicate. Improve ownership/custody journals where producer evidence exists; connect later to records/cultural significance. |
| Relics / historical significance | no need for spawned relic primitive | DERIVED | Significance arises from provenance + events + beliefs + institutional/cultural attention. |
| Architecture / historical buildings | infrastructure/culture construction foundations exist; full building lifecycle incomplete | EXTEND | Later causal chain: need -> finance -> land -> design -> materials -> labor -> construction -> maintenance. Use existing materials/property/provenance. |
| Migration / cultural movement | civilization/genealogy/culture/transmission foundations exist | EXTEND | Feed actual migration into exposure, language, knowledge, relationships and institutional change. |
| Language/dialect ancestry/exposure | documented Stage D plan; no authoritative language ecology yet | NEW PRIMITIVE | Stage 5 after information/exposure foundations. No species-language shortcut or heavy phonetic caricature. |
| Authored records/letters/books/art/music/folklore | archive and material items exist; authored work semantics absent | NEW PRIMITIVE + EXTEND | Stage 5 information objects + existing physical provenance/custody. Full prose is non-authoritative optional rendering. |
| Historiography / archaeology | archive/inspector and provenance already support research; in-world scholarship absent | EXTEND | Stage 5 historians are people with limited records/evidence. Inspector remains omniscient developer tool only. |
| Gods / objective cosmology | metaphysics/divinity modules exist | DEFER | Existing executable mechanics remain; no expansion or inferred metaphysical truth until objective cosmology is authored. |
| Religion / theology / schism | culture/institutions can support later religious institutions | DEFER + EXTEND | Stage 8 after cosmology. Keep gods, mortal beliefs and religious institutions separate. |
| Adventure Society membership/contracts | `institutions.py`, `society_accountability.py` | KEEP + EXTEND | Stage 7 adds demonstrated judgment/star responsibility using actual outcomes; star rank != magical rank. |
| Player obeys same epistemic/agency world | no full player-facing layer yet | NEW INTEGRATION | Stage 7. Player receives only available evidence; no hidden omniscient quest truth. |
| Narrative/historian interpretation | archive/inspector + personhood initiative | KEEP | Read-only. Never back-write narrative importance into simulation truth. |
| Millennium performance | existing long-history runner/gates/index optimizations | KEEP | Every stage must profile. Prefer sparse state, indexes, queues, bounded containers and aggregation. <=120s remains hard acceptance gate. |
| Checkpoint/archive compatibility | schema-4 trusted pickle checkpoint; archive schema v1 separate | KEEP + MIGRATE AS NEEDED | Any new persistent Stage 1 fields require explicit checkpoint schema/version migration or a deliberate baseline break approved at authority level. Archive schema evolves separately with explicit reader migration/rejection. |

## Duplicate-system hazards found

1. **Institution namespaces already overlap.** `culture.py` owns a legacy `Institution` registry while `institutions.py` owns Society/general branch structures. Stage 4 must reconcile/bridge these; do not create another generalized institution registry.
2. **Relationship truth is currently symmetric.** Do not simply add directional fields onto the existing shared edge and pretend historical semantics changed. Preserve shared history and migrate assessments separately.
3. **Knowledge already has claims/beliefs and transmission already has generic movement.** Rumor, records, secrets and information objects must extend these concepts rather than introduce unrelated claim graphs.
4. **Provenance already exists.** Cultural artifacts/relics use material/item provenance plus events/transmission/records; no second artifact-history database.
5. **Personhood is currently a read-only projection.** Persistent psyche/memory state must be a deliberate schema addition, not silently stuffed into projection objects.
6. **The omniscient archive is not in-world institutional memory.** Never let NPCs query archive truth; create bounded in-world records/evidence and expose only authorized information.

## Stage 1 contract freeze — decisions now safe to make

The audit supports the following Stage 1 boundaries:

### 1. Observation
Create a persistent bounded observation/evidence primitive keyed by observer and source event/claim, with acquisition year/channel, perceived fields or evidence references, confidence/clarity and source lineage. Observation creation must be event-driven/indexed. No automatic actor->full-event knowledge.

### 2. Memory
Create bounded per-mind memory references derived only from authorized observations/claims. Store salience, retained confidence, emotional relevance, interpretation tags and acquisition/reinforcement evidence. Use caps and lazy/event-driven decay. Objective events remain untouched.

### 3. Psyche
Persist a versioned psyche state separate from `Person`: disciplined temperament vector, revisable value/identity commitments with evidence, current drives/emotions, self-beliefs and a small active-goal set. Existing `temperament/attachment/curiosity/inhibition/grief/fear` remain legacy inputs until explicitly migrated.

### 4. Directional social assessment
Keep `SocialGraph` shared edges/history. Add sparse `(observer, subject)` assessments with only evidenced dimensions. Missing dimension means unknown/unmodeled, not neutral. Consumers migrate incrementally.

### 5. Agency v2
Extend `AgencyState`; do not create another engine. Candidate attempts are supplied by goals + known opportunities/domain adapters. Evaluation reads psyche, beliefs, memories, directional assessments, capability/resources and expected consequences. Weighted stochastic choice uses isolated deterministic streams. Domain systems resolve results.

### 6. Mastery stages
Initially **derive**, do not persist. Existing ability progression has ten levels per rank plus fractional progress. Compute normalized within-rank progress as `(level + progress) / 10`, then map to four equal quarters for Stage 1–4 display/state projection. This preserves exact pacing and avoids schema churn. Persist only if later mechanics genuinely need stage as causal state.

### 7. Seeds
Design migration before code. Starting-world generation and historical entropy need separate inputs while preserving a compatibility path for existing single-seed fixtures. RNG namespaces remain isolated. No golden digest refresh merely to make tests pass.

### 8. Performance
No annual full-history scans. New subjective state must have per-person indexes and bounded containers. Consequential events fan out only to plausible observers/affected entities. Background psyche updates use sparse cadence; active goals use bounded reconsideration; event reactions are targeted.

## Stage 1 acceptance gates

1. Same legacy fixture under compatibility mode preserves current canonical behavior/digest unless an explicitly approved migration test says otherwise.
2. Same World Seed + same History Seed + same version/config reproduces exact state/history.
3. Same World Seed + different History Seed produces identical starting state and may diverge only after history begins.
4. A person cannot believe/use event data they did not observe, receive, infer from authorized evidence, or already know.
5. Two observers can form different memories/beliefs about one event.
6. Directional trust can differ A->B vs B->A while shared event history remains common.
7. Agency v2 can explain every chosen major attempt through inspectable inputs and does not directly mutate domain outcomes it does not own.
8. Four-stage mastery projection produces exact quarter semantics without changing advancement timing.
9. New per-person state is bounded and does not introduce person x archive scans.
10. Canonical 1,000-year benchmark remains <=120 seconds or the PR is not accepted.

## Immediate implementation sequence

1. Write Stage 1 schema/compatibility specification (no behavior change).
2. Implement mastery-stage projection/tests as a small isolated PR.
3. Implement seed-separation compatibility layer/tests.
4. Add Observation contract + authorization tests.
5. Add bounded Memory state consuming Observation only.
6. Add persistent Psyche state and migration from legacy evidence without invented defaults.
7. Add sparse directional social assessments.
8. Integrate Agency v2 behind compatibility/feature gate; migrate one domain adapter at a time.
9. Profile short/100/1,000-year runs and inspect behavioral scenarios before enabling new architecture by default.

At the end of Stage 1, ATE should still look recognizably like the current simulation from the outside. The difference is that people will finally have a safe causal interior for later ordinary life, rumor, politics, institutions, crime, knowledge, art, combat decisions and player interaction to build on.
