# ATE Cross-System Integration Audit v1

**Status:** integration authority for planning. No production implementation beyond Stage 0.5 is authorized until the gold baseline is frozen.  
**Purpose:** reconcile the current implementation architecture, roadmap and detailed design specifications into one ownership/dependency map before large-scale implementation begins.

## North star

ATE should not become a collection of excellent simulators that happen to share a repository.

It should behave as one causal world.

> **A fact should have one authoritative owner, many legitimate consequences, and no hidden duplicate truth.**

The integration test for every future primitive is therefore:

1. Who owns the objective fact?
2. Who may observe it?
3. Who may remember/believe it?
4. Which systems may act because of it?
5. Which domain resolves the attempted action?
6. Which event records the consequence?
7. Which indexes/projections may summarize it without becoming second authorities?

## 1. Authority chain after this audit

Planning/implementation authority should be read in this order:

1. `docs/PROJECT_CONSTITUTION.md`
2. `simulation/CURRENT_STANDARD.md`
3. `docs/LIVING_DESIGN.md`
4. `docs/IMPLEMENTATION_ARCHITECTURE.md`
5. `docs/STAGE_0_AUDIT_MATRIX.md`
6. `docs/STAGE_1_FOUNDATION_CONTRACTS.md`
7. this cross-system integration audit
8. detailed domain design specifications listed below
9. `docs/IMPLEMENTATION_ROADMAP.md` for sequencing
10. PR/task acceptance criteria
11. implementation

**Sequencing exception:** the Stage 0.5 hard gate in `IMPLEMENTATION_ROADMAP.md` remains absolute. No lower document may be interpreted as permission to implement Stage 1+ early.

Detailed domain specs refine semantics inside their domains but may not silently create a competing authority for a primitive assigned here.

## 2. Detailed design specifications currently in scope

The integrated design set includes at least:
- `HUMAN_PSYCHE_SEMANTICS.md`
- `HUMAN_DEVELOPMENT_MODEL.md`
- `INFORMATION_BELIEF_EVIDENCE_MODEL.md`
- `INSTITUTIONS_GOVERNANCE_POWER_MODEL.md`
- `CIVILIZATION_KNOWLEDGE_CREATION_MEMORY_MODEL.md`
- `CONFLICT_COMBAT_INJURY_HEALING_MODEL.md`
- `WORLD_ECOLOGY_ENVIRONMENT_MODEL.md`
- `MATERIAL_CIVILIZATION_ECONOMY_SETTLEMENT_MODEL.md`
- Stage 0/1 architecture/contracts and existing Living Design.

The repository does **not currently contain a dedicated relationship/social-life design document** matching the intended directional social architecture. That is a real planning gap, not permission for implementation agents to improvise it. Stage 1 directional relationship work remains governed by `IMPLEMENTATION_ARCHITECTURE.md` and `STAGE_1_FOUNDATION_CONTRACTS.md` until that gap is filled.

## 3. The one-world causal spine

The integrated causal architecture is:

`objective world/material/social state`
`-> opportunity / physical evidence / communication access`
`-> Observation`
`-> Belief + Memory + directional social assessment`
`-> Psyche drives/values/self-concept + active Goals`
`-> Agency chooses an attempt`
`-> owning domain validates/resolves feasibility/outcome`
`-> objective Event + objective state mutation`
`-> provenance / records / relationships / inventories / injuries / environmental changes`
`-> new evidence`
`-> future subjective updates and decisions`

No domain is allowed to jump backward across this chain for convenience.

Examples of forbidden shortcuts:
- relationship trust dropping because objective betrayal occurred but the person never learned it;
- migration because the simulator knows a distant mine exists;
- an investigator reading `KnowledgeClaim.truth`;
- prosperity creating food;
- a drought directly moving households;
- a government building infrastructure without labor/material access;
- an NPC reacting to archive-only history;
- combat deciding a person's long-term resentment directly;
- culture writing values directly into a child;
- ecology inventing magical laws before cosmology is authored.

## 4. Canonical ownership matrix

### Objective events and causal history
**Owner:** `core.py` Event/world event history.  
**Consumers:** every domain, archive, evidence/observation, provenance.  
**Rule:** no parallel event history.

### Deterministic randomness
**Owner:** core namespaced RNG; future World Seed + History Seed contract.  
**Consumers:** all stochastic domain resolution.  
**Rule:** domains receive isolated streams after causal candidate formation; no hidden global random source.

### Person identity/life state
**Owner:** core Person + biology/genealogy/household authorities as applicable.  
**Consumers:** Psyche, social, economy, institutions, combat, development.  
**Rule:** Psyche does not duplicate age/species/parentage/health.

### Genealogy
**Owner:** existing genealogy/lineage systems according to current semantic split.  
**Consumers:** development, inheritance, culture/history, social kinship.  
**Rule:** kinship is objective relation; closeness is social/subjective.

### Household/co-residence
**Owner:** existing household/world state.  
**Consumers:** development, material economy, social contact, migration.  
**Rule:** household membership is not proof of affection or equal resource sharing.

### Psyche
**Owner:** future persistent subjective Psyche primitive.  
**Contains:** temperament, values/commitments, self-concept, drives/emotions, bounded goals.  
**Does not own:** objective truth, skills, relationships, wealth, culture, reputation.

### Observation
**Owner:** future Observation/perception boundary.  
**Consumes:** objective events/evidence/records/testimony/access.  
**Produces:** authorized subjective evidence.  
**Rule:** actor participation does not automatically imply full observation.

### Knowledge claims and beliefs
**Owner:** extend `knowledge.py`.  
**Consumes:** observations/testimony/records/inference.  
**Rule:** objective truth metadata is privileged and unavailable to NPC decisions.

### Memory
**Owner:** future bounded subjective Memory primitive.  
**Consumes:** selected observations/beliefs/experience.  
**Rule:** memory is not archive; forgetting never deletes objective history.

### Transmission
**Owner:** extend `transmission.py`.  
**Consumes:** claims/information objects/practices/skills where appropriate.  
**Rule:** rumor is transmission behavior, not a second information universe.

### Objective shared relationship history
**Owner:** extend/preserve `social.py` Relationship/shared-history layer.  
**Rule:** this records interactions/history, not a symmetric final opinion.

### Directional social assessment
**Owner:** future sparse A->B social assessment.  
**Contains as needed:** affection, trust, respect, fear, attraction, resentment, obligation, rivalry, dependency.  
**Rule:** A->B and B->A are independent; unknown is not neutral.

### Reputation
**Owner:** none as universal truth.  
**Representation:** derived observer/group beliefs from evidence and social transmission.  
**Rule:** never a global reputation/morality score.

### Agency
**Owner:** extend `agency.py`.  
**Owns:** candidate evaluation and attempt selection.  
**Does not own:** outcome resolution.  
**Rule:** reads only actor-authorized subjective/material state.

### Skills/capabilities
**Owner:** existing skills/advancement/biology authorities.  
**Consumers:** Agency and domain resolution.  
**Rule:** capability is separate from personality and opportunity.

### Magic progression
**Owner:** existing advancement/magic-resource systems under canonical rules.  
**Invariant:** no Iron+ without 3 base essences + confluence + all 20 skills. Partial paths are rank 0.  
**Rule:** economy controls access/resources, never bypasses prerequisites.

### Culture/practices
**Owner:** `culture.py` for practices/adoption/cultural pressure/history.  
**Rule:** culture is reconstructed from practices/history; it does not directly own personality or institution identity.

### Institution identity/lifecycle
**Owner:** reconcile toward `institutions.py`.  
**Migration:** legacy `culture.py` Institution semantics must migrate/link; no third registry.  
**Consumers:** governance, economy, education, religion, Society, records.

### Institutional records
**Owner:** institution/record/information-object architecture; exact storage contract later.  
**Rule:** institutional knowledge is carried by people/records/procedures, not hive-mind truth.

### Material lots/crafted provenance
**Owner:** existing `materials.py` and provenance authority.  
**Rule:** no second artifact-history system.

### Property claims
**Owner:** extend `economy.py` Property semantics.  
**Rule:** distinguish recognized ownership, possession, access and location where needed.

### Bulk inventory
**Owner:** future material-economy inventory primitive linked to owners/locations.  
**Rule:** fungible goods aggregate; historically meaningful objects individuate.

### Currency
**Owner:** existing currency/ranked-currency systems through Stage 0.5, then integrate.  
**Rule:** currency is stock/flow, not prosperity.

### Production/consumption/markets
**Owner:** future material-economy domain extending current civilization/economy behavior.  
**Rule:** output requires inputs; trade moves actual goods; prices are local/derived.

### Infrastructure
**Owner:** existing `infrastructure.py`.  
**Rule:** enrich condition/capacity/projects/material maintenance rather than duplicate roads/buildings elsewhere.

### Settlement
**Owner:** existing world settlement identity.  
**Consumers:** economy, environment, institutions, culture, social indexes.  
**Rule:** settlement summaries such as prosperity/scarcity/roads/irrigation become compatibility/derived projections where richer authorities supersede them.

### Geography/environment
**Owner:** world/environment spatial authority.  
**Rule:** static geography generated once; slow ecology lazy/aggregate; consequential events persisted.

### Threat ecology
**Owner:** existing ranked threat ecology.  
**Integration:** environment supplies habitat/resource/disturbance context; threats remain canonical authority for ranked threat behavior.

### Combat/injury
**Owner:** future encounter/injury domain integrated with existing warfare/health/rank systems.  
**Rule:** severity, immediate lethality, survival window and healing rate remain distinct.

### Macro warfare
**Owner:** existing warfare authority, later enriched by material logistics/institutions and focused encounter semantics.  
**Rule:** do not replace armies with thousands of focused duels.

### Archive/historian
**Owner:** existing archive/inspector.  
**Rule:** omniscient read-only observer; never NPC input.

### Narrative/expression
**Owner:** non-authoritative renderer/interpreter.  
**Rule:** may describe facts/subjective states but cannot create them.

### Cosmology/divinity
**Owner:** deliberately unresolved objective canon.  
**Rule:** implementation agents may not infer metaphysical truth from existing convenient mechanics.

## 5. Duplicate-authority hazards found

### Hazard A — Institutions
Known duplicate: `culture.py` and `institutions.py` both represent institutions.

**Resolution:** `institutions.py` becomes general identity/lifecycle authority; culture retains practice/adoption state and references institution IDs.

### Hazard B — Relationships
Current `social.py` relationship dimensions are symmetric, while future semantics require directional subjective assessments.

**Resolution:** preserve objective/shared interaction history; migrate opinion-like dimensions into sparse directional assessments. Do not simply make the existing whole object directional if that would duplicate shared history.

### Hazard C — Subjective state versus personhood projection
`personhood.py` already exposes read-only epistemic projections but is not persistent Psyche.

**Resolution:** keep personhood as projection/inspection; persistent Psyche is new authoritative subjective state.

### Hazard D — Belief versus memory versus archive
Existing knowledge beliefs, future memory and omniscient archive can look similar.

**Resolution:** claims/beliefs answer "what proposition does this person accept and how strongly?" Memory answers "what experience/evidence remains accessible to this person?" Archive answers "what objectively happened?"

### Hazard E — Economy summary versus material truth
Current settlement `food_stock`, `prosperity`, local `scarcity`, Person `wealth` and trade effects are compact causal proxies.

**Resolution:** retain for baseline compatibility, then migrate toward derived summaries as actual inventories/property/currency/production become authoritative. Never maintain two independent versions indefinitely.

### Hazard F — Roads/infrastructure versus settlement road scalar
`infrastructure.py` has physical road assets while settlement `roads` is also used as a scalar.

**Resolution:** physical infrastructure owns truth; settlement road value becomes derived accessibility/condition projection.

### Hazard G — Irrigation
Same pattern: infrastructure assets versus settlement irrigation scalar.

**Resolution:** infrastructure/environment own physical truth; settlement scalar becomes derived compatibility projection.

### Hazard H — Carrying capacity
Current civilization code computes capacity from fertility/irrigation/roads/hazard. World/ecology and material design require housing/food/water/import capacity.

**Resolution:** preserve current formula through baseline; later replace with derived material/environment capacity. Do not create an independent new `carrying_capacity` causal field.

### Hazard I — Trade route versus road
TradeRoute is social/economic connectivity; road is infrastructure. They are related but not identical.

**Resolution:** preserve both. Repeated route use can cause road creation; road condition changes route cost/capacity. A trade route can exist without a road and a road can outlive trade.

### Hazard J — Property versus material provenance
Property tracks recognized ownership; material provenance tracks physical/material history.

**Resolution:** link them, do not merge them. Ownership can be disputed/false while physical provenance remains objective.

### Hazard K — Information object versus material record
A book/letter/deed may be both a physical object and an information carrier.

**Resolution:** physical object identity/provenance belongs to material authority; semantic claims/content belong to information/record authority; link by stable ID.

### Hazard L — Institution assets versus economy property
Legacy institution models contain generic `assets` numbers.

**Resolution:** migrate meaningful assets into actual property/currency/inventory claims. Generic asset scalar becomes compatibility/diagnostic only.

### Hazard M — Culture transmission versus information transmission
Practices already spread via transmission; future rumor/records also use transmission.

**Resolution:** one generic transmission lineage mechanism with typed item/channel semantics. Do not create separate rumor propagation infrastructure.

### Hazard N — Development naming
Existing `development.py` is settlement skill/infrastructure development, not human psychological development.

**Resolution:** do not overload it with childhood Psyche logic. Human development should have a clearly distinct module/namespace while reusing skills/households/social/transmission.

### Hazard O — Environmental health versus person health
Environment can generate contamination/vector/exposure pressure; biology/health resolves person consequences.

**Resolution:** environment owns exposure conditions, not illness state.

### Hazard P — Combat injury versus health
Combat creates injuries/viability; health/biology owns ongoing body state where appropriate.

**Resolution:** exact schema boundary must be frozen before Stage 6 implementation. Do not create duplicate HP/health histories.

### Hazard Q — Threat ecology versus magical ecology
Existing threat ecology is real canon. New environmental design intentionally leaves broader magical ecology unresolved.

**Resolution:** integrate habitat/resource/disturbance around existing threats without inventing ambient metaphysics.

## 6. Missing causal bridges found

These are not necessarily missing code today; they are required integration contracts before their implementation stages.

### Bridge 1 — Event -> Observation authorization
Needed for almost every subjective system. Must exist before Psyche-driven Agency can be trusted.

### Bridge 2 — Observation -> Belief/Memory selection
Not every observation becomes durable memory; belief update and memory retention are separate bounded operations.

### Bridge 3 — Belief/Memory -> directional relationship update
Perceived conduct, not objective hidden conduct, changes trust/resentment/etc.

### Bridge 4 — Psyche + subjective state -> Agency candidates
Goals/preferences must generate plausible attempts without Agency querying hidden world truth.

### Bridge 5 — Agency attempt -> domain resolver
Every action category needs a single owning resolver. Agency never mutates economy/combat/social/environment directly merely because it selected an action.

### Bridge 6 — Material state -> actor-known opportunity
Employment, trade, migration, magic-resource acquisition and investment require an epistemic view of markets/resources, not direct global state reads.

### Bridge 7 — Environment -> material production
Soil/water/weather/resources affect yields/extraction; economy consumes those interfaces rather than duplicating environment calculations.

### Bridge 8 — Material economy -> household development
Food security, crowding, caregiver work burden, debt and tools become concrete developmental exposures rather than abstract wealth modifiers.

### Bridge 9 — Infrastructure -> transport/market/settlement capacity
Roads, storage, waterworks and housing need material effects; summary scalars become projections.

### Bridge 10 — Institutions -> actual resources/property/records
Institutions require assets, staff, offices, records and finance that exist in other authorities.

### Bridge 11 — Relationships -> institutions/collective action
Recruitment, factions, patronage, corruption and group formation should arise through actual social edges/obligations rather than faction affinity scores.

### Bridge 12 — Information -> law/investigation
Legal outcomes must consume evidence/beliefs/records rather than objective guilt.

### Bridge 13 — Material logistics -> warfare/combat
Armies require food, equipment, transport and organization. Macro warfare should consume material/institutional capacity.

### Bridge 14 — Combat -> social/information consequences
Witnessed violence produces observations, injuries, deaths, property effects and later beliefs/relationships; combat must not author reputations directly.

### Bridge 15 — Death -> inheritance/institution/social/development
One objective death event fans out only to relevant/authorized systems: property succession, offices, dependents, grief, records, rumors, etc.

### Bridge 16 — Long-lived rank -> ordinary systems
Longevity should change exposure duration, accumulated skill/property/relationships and generational position through ordinary systems—not a special "ancient" personality/economy path.

### Bridge 17 — Environment -> threat ecology -> settlements
Human land use changes habitat/disturbance; threat system resolves threat response; settlements experience consequences. No direct ecology-to-monster-attack script.

### Bridge 18 — Provenance -> information/reputation/value
Objective object history can become evidence; people may know/misunderstand it; market/cultural value derives partly from believed provenance.

## 7. Cross-system event fan-out rule

One objective event may have many consequences, but fan-out must be indexed and relevance-based.

Example: `person_died`

Immediate objective/domain effects may include:
- alive/body state;
- office vacancy;
- property/inventory custody transition pending succession;
- dependent household pressure;
- combat outcome if applicable.

Then evidence is exposed only to:
- witnesses;
- nearby discoverers;
- notified kin/institutions;
- record systems with access.

Only those observations can update:
- grief/memory;
- beliefs;
- relationships;
- goals;
- rumors;
- institutional decisions.

Never loop every person over every death.

## 8. Cross-system transaction rule

Material movement should have one objective transfer and optional semantic consequences.

Example: a sword is sold.

Objective:
- currency transfer;
- possession/location transfer;
- recognized ownership transfer if transaction valid;
- provenance/event link.

Subjective/social consequences occur only if relevant:
- buyer/seller observe transaction;
- witnesses learn it;
- debt fulfilled;
- trust changes if promise kept/broken;
- later record/deed created.

Do not separately mutate economy, property and materials with unrelated pseudo-transactions.

## 9. Cross-system opportunity rule

Objective opportunity and known opportunity are different.

Examples:
- job opening exists;
- unclaimed mineral deposit exists;
- essence seller has stock;
- safe migration destination has housing;
- healer is nearby;
- evidence is hidden in a room.

Agency can consider it only after legitimate discovery/communication/knowledge.

This rule must be enforced at interfaces, not merely documented as good behavior.

## 10. Cross-system summary/projection rule

Derived values are useful for diagnostics, compatibility and cheap decisions when their inputs are authorized.

Examples:
- settlement prosperity;
- local scarcity;
- road accessibility;
- housing pressure;
- personal net wealth;
- reputation summary;
- relationship category;
- cultural prevalence.

A projection must:
- identify authoritative inputs;
- be reproducible from them;
- not diverge as a separately mutated truth;
- not leak inaccessible information into Agency.

If a projection becomes causally necessary, either compute it from authorized state or promote its true underlying primitive—not the summary itself—into authority.

## 11. Stage dependency corrections

The current roadmap is broadly sound, but the newer design work exposes sequencing refinements.

### Stage 0.5 remains unchanged and absolute
Finish current magic/currency/access calibration, CI, determinism and performance. Freeze exact gold baseline.

### Stage 1 — subjective foundation
Order should be:
1. mastery projection/tests where isolated;
2. seed/version migration infrastructure;
3. Observation/access contract;
4. belief extension + bounded Memory;
5. Psyche persistent state;
6. directional social assessment;
7. Agency v2 read boundary/DecisionTrace;
8. integration indexes/performance.

Observation should precede any feature that would otherwise populate beliefs/memory from omniscient events.

### Stage 2 — human development + ordinary relationships
Human development requires Psyche, Observation/Memory, directional relationships and material household exposure interfaces.

A dedicated relationship/social-life semantics document should be completed before Stage 2 implementation begins.

### Stage 3 — information society
Rumor, secrets, records, evidence, reputation and investigation build on Stage 1 and social network semantics.

### Stage 4 — institutions/governance/power
Before deep institutional finance/governance, define minimal property/inventory/record attachment interfaces. Full material economy need not all land first, but institutions cannot be built around generic magic asset numbers that will immediately be replaced.

### Stage 5 — civilization knowledge/creation/memory
Information objects, scholarship, art, language ancestry, archaeology and cultural memory use records/provenance/institutions.

### Material/environment foundation — should be staged before full conflict and millennium integration
The roadmap currently lacks explicit stages for the newly authored World/Ecology and Material Civilization specs.

Recommended insertion:

**Stage 5.5 — Physical world/ecology integration**
- static geography/spatial indexes;
- climate/environment interfaces;
- lazy water/soil/vegetation/wildlife/resources;
- bounded disasters;
- threat-ecology environmental integration.

**Stage 5.75 — Material civilization integration**
- bulk inventories/production/consumption;
- sparse markets/trade/transport;
- property/access/housing;
- infrastructure projects/maintenance;
- business/debt/institution finance interfaces;
- migrate prosperity/scarcity/wealth summary causality.

These numbers are planning labels only; roadmap should be updated in a later reconciliation commit rather than silently assumed by coding agents.

### Stage 6 — conflict/combat/injury/healing
Now consumes mature material logistics, environment/terrain, relationships and information.

### Stage 7 — player-facing deep simulation
Same epistemic/material rules as NPCs.

### Stage 8 — cosmology
Still blocked until objective metaphysics is authored.

### Stage 9 — millennium integration/calibration
Becomes final full-system calibration rather than first time environment/economy are connected.

## 12. Performance budget architecture

The <=120-second millennium gate remains global.

No subsystem receives an automatic fixed slice of the unused time.

### Global rules
- no person x all-events scans;
- no all-pairs people relationship simulation;
- no all-pairs settlement trade at scale;
- no every-cell every-year ecology;
- no every-object every-year decay;
- no every-person every-year deep Agency;
- no focused combat for background armies;
- no generated prose in authoritative simulation loops.

### Preferred tools
- sparse indexes;
- event queues;
- active sets;
- lazy elapsed-time updates;
- aggregate cohorts/stocks;
- bounded memory/goals/social edges;
- deterministic procedural reconstruction;
- derived projections;
- focused expansion only when consequence/player relevance requires detail, without changing historical probability.

### Benchmark discipline
After gold baseline, every structural PR reports:
- 100/500/1,000-year runtime;
- deterministic digest/fixture status;
- state-count deltas for the primitive introduced;
- hot-path/profile note if runtime grows materially;
- why the cost is causally necessary;
- optimization/degradation strategy if needed.

Passing 120 seconds is necessary but not sufficient. Disproportionate marginal cost is grounds for redesign.

## 13. Schema/checkpoint integration rule

Current checkpoint schema is legacy baseline state.

After gold freeze:
- schema migrations must be explicit/versioned;
- old baseline checkpoint remains loadable through documented migration where promised;
- migration may preserve known objective facts;
- migration must not fabricate subjective history that never existed.

Examples:
- legacy symmetric relationship history may seed shared history, but cannot invent precise directional trust if evidence does not support it;
- legacy temperament fields may map only where semantics genuinely match;
- old prosperity/wealth can remain compatibility values but should not be decomposed into fictional inventories/property histories;
- old seed maps through explicit legacy semantics, not guessed alternate history.

## 14. Testing hierarchy

Each primitive needs four levels of tests.

### Contract tests
Data invariants and access rules.

### Behavioral scenario tests
Small causal worlds demonstrating intended semantics.

### Cross-system integration tests
One event flows through multiple authorities without duplicate truth or leakage.

### Millennium calibration
Distribution, determinism, runtime and dead/runaway-system checks.

A unit test proving a dataclass exists is not sufficient evidence that a simulation feature works.

## 15. High-value cross-system acceptance scenarios

1. **Secret betrayal:** objective betrayal occurs; victim's trust does not change until evidence reaches them.
2. **False accusation:** innocent person loses trust/reputation because believable false evidence spreads; objective innocence remains unchanged.
3. **Drought without famine:** ecology reduces yield; stores/trade/institutions buffer consumption.
4. **Drought with migration:** prolonged shortage exhausts buffers; households who know viable destinations and can afford travel may migrate.
5. **Unknown mine:** deposit exists for centuries; no economic effect until discovered, believed, accessed and developed.
6. **Trade builds road:** repeated inventory movement strengthens route demand; construction creates infrastructure; transport cost falls; future trade changes.
7. **Road outlives trade:** route collapses but physical road remains and decays/gets repurposed.
8. **Institution founder dies:** office vacancy, property/records/succession mechanisms determine continuity; no founder-death script.
9. **Forged deed:** physical record exists, semantic claim is false, institution believes it, property judgment changes, later evidence can reverse it.
10. **Stolen heirloom:** possession changes without legitimate ownership; provenance remains; later descendants can unknowingly possess disputed property.
11. **Unwitnessed murder:** injury/death objective; no NPC knows killer automatically; investigation uses evidence and can fail.
12. **Battle logistics:** superior force suffers because supply/transport/institutional coordination fail; outcome remains inspectable.
13. **Healer timing:** same injury and healer capability produce different survival depending on travel/rescue time.
14. **Childhood scarcity:** material household shortage creates actual work/care/exposure changes; siblings may interpret/respond differently through temperament/relationships.
15. **Long-lived founder:** Gold founder remains alive across generations; institution can still change against their preference because members/resources/legitimacy evolve.
16. **Magic access:** person has aptitude/desire but cannot rank because canonical essence/confluence/20-skill resource path is incomplete; no shortcut.
17. **Rumor market panic:** false shortage claim changes beliefs/hoarding/local price despite adequate objective regional stock.
18. **Abandoned town:** migration removes population; infrastructure/property/records/environmental traces persist and later archaeology can reconstruct imperfect history.
19. **Lost technique:** last accessible teacher/record disappears; objective archive knows it existed but society cannot use it until rediscovery.
20. **Ordinary life:** many people live stable lives with modest work, relationships and local events; simulation does not maximize drama.
21. **Performance:** all above semantics remain compatible with deterministic <=120-second millennium and bounded marginal subsystem cost.

## 16. Current unresolved planning gaps

### Gap A — dedicated relationships/social-life model
Still needed before Stage 2 implementation. Must settle friendship, kin bonds, romance/partnership, unrequited attraction, promises, betrayal, forgiveness, rivalry, dependency, social circles, contact/decay and derived relationship categories without drama scripting.

### Gap B — health/disease/ordinary bodily life
Combat spec covers injury/healing, ecology defines disease exposure boundary, biology exists, but a full ordinary health/disease/aging architecture has not been reconciled at the same depth. This may need a dedicated pass before Stage 6/player integration depending on existing biology scope.

### Gap C — exact building/housing representation
Material spec intentionally leaves building vs infrastructure/property schema open.

### Gap D — exact information-object/record physical linkage
Semantics are clear; schema remains open.

### Gap E — exact law/legal procedure representation
Institution/information specs define causal requirements but final schema/procedure granularity remains open.

### Gap F — cosmology
Intentionally blocked. No implementation agent fills it.

## 17. What should be frozen before Astra starts Stage 1

Stage 0.5 gold baseline must be frozen first.

Before Stage 1 production begins, the following planning artifacts should also be considered stable enough for implementation:
- Stage 1 foundation contracts;
- Human Psyche semantics;
- Information/Belief/Evidence model;
- this integration ownership map;
- dedicated relationship/social-life model;
- explicit migration/access rules for Observation/Belief/Memory/Relationship/Agency.

Later-stage domain specs can continue evolving without blocking Stage 1 if their Stage 1 attachment points are frozen.

## 18. What Astra must inspect before each PR

Every implementation PR should identify:
- authoritative design documents;
- existing modules touched/consumed;
- owner of each new field;
- whether each state is objective, subjective or derived;
- evidence/access boundary;
- domain resolver;
- event emitted;
- indexes/fan-out;
- checkpoint migration;
- RNG namespace impact;
- performance delta;
- acceptance scenarios.

If two modules appear to own the same truth, stop and reconcile before coding.

## 19. Integration conclusion

The architecture is coherent. The detailed design work has not revealed a need to restart the simulation or replace its core foundations.

The strongest existing foundations remain exactly the ones we wanted:
- objective typed events;
- deterministic RNG;
- genealogy/households;
- skills/magic advancement;
- knowledge/transmission;
- provenance;
- infrastructure;
- institutions/Societies;
- threat ecology;
- archive/inspector.

The major transformation is still what Stage 0 identified: **subjective causality**. Once Observation, bounded Memory/Belief, persistent Psyche, directional relationships and Agency v2 exist, the later environment/material/institution/conflict systems can compose around people who actually know only part of their world.

The newer World/Ecology and Material Civilization designs fit that architecture rather than contradicting it. Their principal demand is that several current summary scalars become derived compatibility projections over richer causal state instead of permanent independent authorities.

The largest planning hole is now explicit rather than hidden: **relationship/social-life semantics still need their dedicated authority document before Stage 2.**

And the implementation order remains disciplined:

> **Stabilize what exists. Freeze it. Add subjective causality. Build ordinary human life on that foundation. Connect information and institutions. Deepen the physical/material world. Resolve conflict through the same causes. Add the player last. Author metaphysics deliberately. Then run a thousand years and see what endured.**
