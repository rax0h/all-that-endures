# ATE Civilization Knowledge, Creation & Memory Model v1

**Status:** design specification only. Implementation remains gated by Stage 0.5 and prerequisite subjective/institutional architecture.  
**Purpose:** define how civilizations learn, teach, invent, create, preserve, lose, reinterpret and rediscover knowledge across centuries without a global technology level or prewritten lore.

## North star

Civilization does not possess a technology tree. People know things. People teach things. People make things. Institutions preserve some of it. Objects and records survive unevenly. Much is forgotten.

The causal chain is:

`experience/problem -> observation/knowledge -> experimentation/practice -> innovation/creation -> teaching/record/object -> transmission/adoption -> refinement/mutation -> preservation or loss -> later interpretation/rediscovery`

Therefore:

> **The lore is not written before the simulation. The simulation creates the past, and the past becomes the lore.**

## 1. Existing authorities to extend

ATE already contains strong foundations:
- `knowledge.py` for claims/beliefs;
- `transmission.py` for movement/mutation lineage;
- `culture.py` for practices, adoption, refinement, mutation and loss;
- `skills.py` and existing teaching/apprenticeship;
- `materials.py` for crafted objects and provenance;
- Events/lineage for objective causal history;
- institutions/records;
- archive/historian for omniscient reconstruction.

Do not create parallel technology, invention, lore, provenance or knowledge-history systems.

## 2. Distinguish capability, knowledge, practice and artifact

These are different.

### Capability
What a person can physically/magically/cognitively do.

### Knowledge
Claims/models/instructions the person believes or understands.

### Practice/technique
A repeatable learned way of doing something, represented by existing cultural/skill authorities where appropriate.

### Artifact
A physical result/object whose provenance can preserve evidence of technique even when nobody remembers how it was made.

A person may know a technique theoretically but lack skill. A skilled craftsperson may execute a technique they cannot formally explain. An artifact may survive after both knowledge and practice disappear.

## 3. No global technology level

Forbidden final authority:
- `technology_level=7`;
- settlement unlock trees;
- civilization-wide automatic invention;
- knowledge becoming universal when one person discovers it.

Instead, availability depends on carriers and access.

A technique can exist in one valley and be unknown fifty miles away. A famous academy can know something most citizens do not. A secret workshop can hold advanced practice that dies with its members.

## 4. Problems and opportunities drive creation

Innovation pressure comes from concrete circumstances:
- scarcity;
- environmental conditions;
- hazards;
- war;
- trade;
- construction needs;
- agriculture;
- healing;
- magic;
- craft competition;
- curiosity;
- prestige;
- institutional demand;
- accidents;
- access to new materials/ideas.

Innovation is not guaranteed by need. Need creates incentive; capability, knowledge, resources, time, experimentation and luck determine outcome.

## 5. Invention and discovery

An innovation can arise through:
- deliberate experimentation;
- incremental refinement;
- combining known techniques;
- adapting imported practice to local conditions;
- accidental discovery followed by recognition;
- reverse engineering an artifact;
- independent rediscovery;
- magical research where canon permits.

The system should preserve ancestry where known:
- parent techniques/practices;
- contributing knowledge;
- materials/tools;
- inventor(s);
- location/year;
- triggering problem/event;
- experimental failures where historically consequential.

Do not require a lone-genius model. Many advances are collective/incremental.

## 6. Innovation is not adoption

Discovering something does not make society use it.

Adoption depends on:
- demonstrated usefulness;
- cost/resources;
- compatibility with existing infrastructure/practices;
- teacher availability;
- social/institutional trust;
- cultural fit;
- legal/religious constraints;
- status/prestige;
- competing practices;
- network/trade access;
- risk;
- political/economic interests.

A superior technique can fail to spread. An inferior one can persist because it is cheap, familiar or institutionally entrenched.

## 7. Practice ancestry and mutation

Existing practice ancestry/mutation remains foundational.

A transmitted technique may:
- copy closely;
- simplify;
- specialize;
- adapt to environment/materials;
- combine with another practice;
- become ritualized;
- drift through teaching error;
- improve through experimentation.

Descendants should preserve ancestry links so a millennium later the historian can reconstruct families of technique without a culture label.

## 8. Tacit versus explicit knowledge

Some knowledge is easier to record than other knowledge.

### Explicit
Rules, measurements, diagrams, recipes, claims, procedures.

### Tacit
Timing, touch, judgment, embodied technique, social know-how, magical feel where canon supports it.

Records can preserve explicit content well while losing tacit competence. This explains why a civilization can possess an old manual yet fail to reproduce the old work immediately.

Teaching/apprenticeship remains important even in literate societies.

## 9. Teaching

Teaching transfers knowledge/practice through actual relationships/institutions.

Effectiveness depends on:
- teacher knowledge/skill;
- student capability/prior knowledge;
- contact/time;
- trust/attention;
- teaching method;
- language;
- tools/material access;
- practice opportunity.

Teaching can transmit errors sincerely.

A teacher may intentionally conceal advanced details, creating partial lineages or trade secrets.

## 10. Education

Education is organized repeated teaching, not automatic stat gain.

Possible forms:
- family instruction;
- apprenticeship;
- peer learning;
- informal community teaching;
- religious teaching;
- guild/Society training;
- school/academy;
- self-directed reading/experimentation.

Schools become institutions only when continuity/resources/roles justify them under the institution model.

Curriculum is a selected body of information/practices. Selection reflects institutional goals, resources and beliefs; it is not identical to all available truth.

## 11. Literacy and language

Records only matter to people who can access/interpret them.

Future language architecture should support:
- spoken language/dialect;
- literacy;
- scripts;
- translation;
- semantic drift;
- specialized terminology;
- partial mutual intelligibility.

Until that model is frozen, information objects should not assume universal literacy or timeless readability.

Language change can make old records progressively difficult to interpret without destroying the physical record.

## 12. Information objects

A general information object is a structured carrier of claims/knowledge/expression with provenance.

Possible kinds:
- letter;
- ledger;
- map;
- manual;
- recipe;
- diagram;
- journal;
- legal code;
- genealogy;
- religious text;
- chronicle;
- research notes;
- poem/song/story;
- inscription;
- school text.

Where physically instantiated, use ordinary object/material provenance for existence/custody. Content references attach to it; do not duplicate physical provenance.

Copies are new objects with ancestry to source content and can introduce mutation/errors.

## 13. Records versus authored works

A record primarily attempts to preserve information about events/state/procedure.

An authored work may primarily express:
- interpretation;
- imagination;
- beauty;
- identity;
- persuasion;
- entertainment;
- ritual;
- philosophy.

Both may contain factual claims. Neither is automatically true.

The simulation should preserve enough structured ancestry/context to later render expressive content without making generated prose causal authority.

## 14. Art

Art emerges from people with capability, motives, materials, cultural exposure and opportunity.

Possible motives:
- enjoyment;
- grief;
- love;
- worship;
- status;
- patronage;
- protest;
- remembrance;
- beauty;
- humor;
- identity;
- experimentation;
- livelihood.

Do not generate “masterpieces” through a masterpiece roll.

Historical/cultural significance is derived later from reception, influence, survival, provenance and reinterpretation.

## 15. Artistic traditions

Artistic traditions emerge through:
- imitation;
- teaching;
- shared tools/materials;
- patronage;
- institutions;
- local environment;
- influential works;
- criticism/reaction;
- migration;
- hybridization.

A later historian may name a school/movement. The simulator need not know it is creating one.

## 16. Authorship and influence

Works should preserve:
- creator(s);
- year/place;
- medium/form;
- source/influence refs where known;
- patron/commission where applicable;
- associated events/people;
- copies/performances/transmissions;
- ownership/custody for physical works.

Influence requires access. A poet cannot influence someone who never encountered the work.

## 17. Reception

People/institutions can react differently to the same work:
- love;
- indifference;
- offense;
- admiration;
- imitation;
- censorship;
- preservation;
- destruction;
- reinterpretation.

There is no universal quality/reputation truth required for causal behavior.

Skill/craft properties can be objective-ish capabilities; cultural significance remains historical/observer-relative.

## 18. Patronage

Creation often depends on resources/time.

Patrons may fund:
- art;
- scholarship;
- architecture;
- exploration;
- magical research;
- schools;
- archives;
- craft experimentation.

Patronage creates relationships, obligations and possible influence over subject matter/distribution without guaranteeing control.

Wealth can therefore shape cultural survival without directly setting culture.

## 19. Scholarship

Scholarship is organized investigation, comparison, preservation and argument about claims/evidence.

Scholars can study:
- history;
- nature;
- magic;
- medicine/healing;
- materials;
- languages;
- law;
- religion;
- societies;
- artifacts.

They obey the same epistemic constraints as everyone else. Scholarship can converge toward truth, remain divided or confidently preserve error.

## 20. Research

Research is goal-directed acquisition/testing of evidence and techniques.

Generic loop:

`question/problem -> prior knowledge -> method/experiment/investigation -> observation -> interpretation -> claim/technique -> replication/critique/use`

Replication/corroboration matters where institutions/culture develop those norms, but no modern scientific method should be assumed universally from year zero.

Methods themselves are cultural/institutional practices that can evolve.

## 21. Failed experiments

Most failures need not persist individually.

Persist a failure when it:
- causes injury/death/disaster;
- materially changes resources;
- strongly changes beliefs/goals;
- becomes a known warning/teaching example;
- influences later successful work;
- creates an artifact/trace;
- triggers institutional/legal response.

Routine failed attempts can be bounded aggregate experience.

## 22. Knowledge distribution

For any claim/technique, distinguish:
- objective existence/truth;
- known by specific people;
- held by institution records;
- practiced at locations;
- available through books/objects;
- publicly reputed;
- accessible only through restricted networks.

“Civilization knows X” is historian shorthand, not causal state.

## 23. Secrecy and trade knowledge

Knowledge may be intentionally restricted for:
- economic advantage;
- magical danger;
- institutional authority;
- family tradition;
- military security;
- religious reasons;
- status/initiation.

Restriction works through access control, relationships, records and enforcement—not an unbreakable secret flag.

Secrets can leak, be stolen, independently discovered or die out.

## 24. Knowledge loss

Knowledge disappears from living civilization when no accessible competent carrier remains.

Loss mechanisms:
- death;
- failed apprenticeship;
- migration/separation;
- record destruction;
- language/script loss;
- institutional collapse;
- deliberate suppression;
- resource/material disappearance;
- technique becoming economically irrelevant;
- catastrophe/war;
- secrecy too successful;
- gradual mutation until original form disappears.

Objective archive truth persists for simulation research, but people cannot query it.

## 25. Partial loss

Loss need not be binary.

Civilization may retain:
- artifact but not method;
- recipe but not ingredient source;
- theory but not practical skill;
- name but not meaning;
- ritualized version of former practical technique;
- fragments/copies;
- false explanation of a working method.

Partial loss creates rich rediscovery paths.

## 26. Rediscovery

Rediscovery may arise from:
- archaeology;
- recovered archive;
- translation;
- reverse engineering;
- surviving isolated community;
- experimentation;
- independent invention.

The rediscovered technique/interpretation may not be identical to the original. Preserve ancestry when causal connection exists; independent invention remains separate ancestry despite functional similarity.

## 27. Archaeology

Archaeology is evidence-based reconstruction of past societies from surviving traces.

Sources:
- buildings/ruins;
- graves;
- tools/weapons;
- material lots/crafted items;
- inscriptions;
- refuse;
- roads/infrastructure;
- records;
- environmental modification;
- magical traces where canon permits.

Archaeologists infer claims. They do not receive archive truth.

A mundane object can become historically priceless because provenance/context survived or was reconstructed.

## 28. Historiography

History as understood by people is a changing body of claims/interpretations about objective past events.

Possible sources:
- witness testimony;
- family stories;
- institutional records;
- chronicles;
- artifacts;
- archaeology;
- prior scholarship;
- propaganda;
- long-lived witnesses.

Competing interpretations can coexist. New evidence can overturn consensus. Political/religious institutions can promote or suppress interpretations.

The omniscient historian/inspector remains read-only and can compare later belief to actual simulated history.

## 29. Civilization memory

Civilization memory is distributed across:
- people;
- families;
- practices;
- institutions;
- records;
- objects;
- buildings;
- landscapes;
- rituals;
- stories/art.

There is no single civilization-memory object that automatically knows everything preserved somewhere.

A record locked in an unread archive exists but is not socially active knowledge until accessed.

## 30. Monuments and commemoration

Communities/institutions may deliberately preserve interpretations through:
- monuments;
- named buildings/roads;
- graves;
- holidays;
- ceremonies;
- songs/stories;
- archives;
- official histories.

Commemoration records what people chose to remember, not objective importance.

Later generations can neglect, reinterpret, destroy or restore monuments.

## 31. Relics and significance

Do not generate relics as an item rarity category merely because an object is old.

An object becomes significant through history:
- famous owner;
- consequential event;
- unusual craft/material;
- institutional/religious association;
- family inheritance;
- survival from lost era;
- scholarly discovery;
- public narrative.

Significance is observer/culture-relative and can change.

**Don't generate relics. Let objects become relics.**

## 32. Libraries and archives

Libraries/archives are institutions/collections that improve preservation/access but require:
- buildings/storage;
- staff;
- organization/indexing;
- literacy;
- resources;
- copying/maintenance;
- security;
- institutional continuity.

They can burn, decay, censor, miscatalog, disperse or become unreadable.

A great archive creates opportunity for future knowledge; it does not place its contents in every citizen's mind.

## 33. Printing/copying/distribution technologies

If/when copying technologies emerge, they change transmission cost/fidelity/scale rather than unlocking “mass literacy” automatically.

Effects depend on:
- materials;
- production capability;
- economics;
- literacy;
- institutions;
- transport;
- censorship;
- demand.

The same principle applies to any future communication technology.

## 34. Knowledge and economy

Knowledge can have economic value through:
- productivity;
- scarce expertise;
- patents/privileges if institutions invent them;
- trade secrets;
- education fees;
- commissioned work;
- maps/navigation;
- magical instruction;
- medical/healing practice.

Economic incentives can promote diffusion or secrecy.

Do not duplicate economy state; knowledge changes capabilities/opportunities and therefore economic outcomes.

## 35. Knowledge and war

Conflict can accelerate, redirect or destroy knowledge through:
- weapons/defense research;
- logistics;
- medicine;
- fortification;
- captured specialists;
- espionage;
- destroyed schools/archives;
- migration;
- state patronage;
- secrecy.

No universal “war boosts technology” modifier. Effects depend on actual resources, survival and institutions.

## 36. Magic and knowledge

Magic knowledge obeys ordinary epistemic/transmission rules unless objective magic canon explicitly says otherwise.

Distinguish:
- possession/access to essences/stones;
- knowledge about them;
- practical magical capability;
- beliefs/theories about magic;
- institutional records;
- secret techniques.

People can hold false magical theories while still using working practices.

Canonical progression/rank rules remain untouched.

## 37. Long-lived people and knowledge continuity

Gold/Diamond-scale lifespans alter civilization memory without making it perfect.

A long-lived person can:
- preserve techniques personally;
- mentor many generations;
- remember obsolete institutions/languages;
- become a primary historical source;
- resist or encourage innovation;
- accumulate enormous expertise;
- lose/reinterpret memories;
- become culturally isolated from younger generations.

Their existence reduces some transmission gaps but does not eliminate subjective memory, secrecy, access or catastrophe.

## 38. Cultural change without culture tags

A culture remains reconstructable from:
- practiced techniques;
- institutions;
- laws;
- architecture;
- objects/art;
- language;
- food/clothing;
- education;
- rituals;
- relationship/family norms;
- records/stories;
- economic behavior;
- responses to environment/history.

If summary culture labels are removed, the civilization should still visibly have a history.

## 39. Expression layer

Generated prose/dialogue/art descriptions are downstream expression, never causal authority.

Expression reads structured state:
- creator psyche;
- known beliefs/memories;
- language/culture;
- intended audience;
- medium;
- influences;
- purpose;
- objective artifact context.

Expression may then create an in-world information object/event, but the rendered text itself must not silently invent authoritative facts absent from structured state.

## 40. Performance architecture

A millennium requires aggressive sparsity.

Rules:
- no person x all-knowledge scans;
- claims/practices indexed by carrier/location/institution;
- bounded personal memory;
- transmission occurs through actual contact/routes/institutions;
- routine teaching/practice can aggregate while preserving meaningful lineage;
- persist significant works/records/artifacts, not every mundane note;
- lazy decay/loss checks when carriers/records change rather than annual global scans;
- scholar/research cognition only for active relevant agents;
- archaeology triggered by access/projects/discovery, not continual world-wide ruin scanning;
- derived cultural/historical summaries remain rebuildable/read-only.

## 41. Behavioral acceptance scenarios

1. One person invents a useful technique and it remains locally unknown elsewhere until transmission occurs.
2. A technically superior practice fails to spread because costs/access/institutions make adoption unattractive.
3. Two regions independently invent functionally similar techniques with separate ancestry.
4. Imported technique mutates to fit different materials/environment.
5. A manual survives while practical competence disappears.
6. Skilled craft survives orally after all written records are lost.
7. Trade secret dies because holders fail to transmit it.
8. Lost technique is partially reconstructed from surviving artifacts.
9. Rediscovery differs from original despite solving the same problem.
10. An institution preserves knowledge for centuries after creators die.
11. Institutional collapse destroys access to some knowledge while scattered copies survive elsewhere.
12. A false theory persists because its associated practice works for misunderstood reasons.
13. A scholar overturns accepted history using newly discovered provenance/records.
14. Two scholarly traditions retain competing interpretations of the same event.
15. A long-lived witness is valuable but can still misremember/be contradicted by evidence.
16. An ordinary crafted object becomes a major relic because later history makes its provenance significant.
17. A deliberately created monument becomes forgotten or reinterpreted centuries later.
18. An artwork influences later creators only where copies/performances actually reach them.
19. A celebrated work in one culture is ignored or condemned in another.
20. A school transmits selected curriculum rather than all truth known to the simulation.
21. A civilization can lose literacy in an old script while physical records remain.
22. War can destroy knowledge in one region while causing concentrated research in another.
23. Removing `technology_level`, `masterpiece`, `relic`, `cultural_era` and similar summary labels does not remove causal civilization history.
24. A thousand-year archive can be reconstructed from actual events, works, institutions, practices, objects and records without prewritten lore.

## 42. Open design questions

Not yet frozen:
- structured representation for general techniques beyond current practices/skills;
- invention candidate generation without combinatorial explosion;
- explicit/tacit knowledge representation depth;
- language/dialect/script model;
- literacy acquisition;
- information-object content schema;
- copying/translation mutation mechanics;
- art-form/medium taxonomy;
- research-method evolution;
- scholarship/institutional peer evaluation;
- archive/library collection indexing;
- archaeology site/trace persistence;
- intellectual property/legal privilege if emergent institutions create it;
- magical research semantics;
- how much rendered language can safely become persistent content;
- significance/relic diagnostics without turning them into causal scores.

Coding agents must not invent these answers merely to finish an interface.

## 43. Implementation sequencing

1. Stage 0.5: stabilize current simulation and freeze gold baseline.
2. Stage 1: Observation/Memory/Belief/Psyche/Agency epistemic foundations.
3. Stage 2: human teaching/development and ordinary transmission.
4. Stage 3: rumor/secrets/records/evidence/reputation.
5. Stage 4: institutional records, schools/governance foundations.
6. Stage 5: general information objects, invention/refinement, language interfaces, authored works, scholarship, lost knowledge, archaeology and historiography.
7. Stage 7: player-facing discovery/knowledge presentation.
8. Stage 8: religious/theological knowledge only after objective cosmology is authored.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Civilization principle:** civilization remembers only what people, practices, institutions, objects and places manage to carry forward—and every carrier can change, fail, disappear or be found again.
