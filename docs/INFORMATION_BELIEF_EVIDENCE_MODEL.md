# ATE Information, Belief & Evidence Model v1

**Status:** design specification only. Stage 1+ implementation remains blocked until Stage 0.5 current-simulation stabilization and gold-baseline freeze are complete.  
**Purpose:** define how objective reality becomes partial, local, fallible knowledge without duplicating existing Event, Knowledge, Transmission, Provenance or Archive authorities.

## North star

**The simulation knows what happened. People do not.**

ATE must preserve a hard boundary between objective reality and subjective knowledge:

`Reality -> Evidence/Access -> Observation -> Memory -> Belief -> Decision`

Communication creates another causal chain:

`Belief/Memory -> Claim/Information Object -> Transmission -> Recipient Observation -> Recipient Belief`

Material history creates another:

`Reality -> Object/Record/Trace -> preservation/change/loss -> later discovery -> Observation -> Belief`

At no point does truth automatically propagate into minds.

## 1. Existing authorities to extend, not replace

ATE already has the important foundations:
- objective typed `Event`s with causal references;
- `KnowledgeClaim` and per-person belief confidence;
- `Transmission` with source/target/reliability/mutation lineage;
- material/crafted-object provenance and transfers;
- institutional records/notices in existing institution structures;
- omniscient archive/inspector for research;
- social shared history;
- read-only personhood epistemic levels.

Future work must compose these. Do not create parallel event history, parallel beliefs, parallel rumor storage, parallel provenance or a second omniscient archive.

## 2. Five epistemic layers

### Layer A — Objective reality
What actually happened or exists in authoritative world state.

Examples:
- a person killed another;
- a sword was forged from specific material lots;
- a shipment arrived;
- a marriage occurred;
- an institution issued an order;
- a magical effect occurred.

Objective reality is not itself a belief.

### Layer B — Evidence and traces
Things that can potentially reveal reality:
- witnessed sights/sounds;
- bodies/wounds;
- footprints/tracks;
- possession;
- material provenance;
- letters/records;
- magical residue where canon supports it;
- transaction records;
- physical damage;
- testimony;
- absence/non-arrival where a person expected something.

Evidence may be ambiguous, incomplete, misleading, altered or destroyed.

### Layer C — Observation
What a particular person actually gains access to from evidence/events/claims. Observation authorizes information entering a mind.

Observation is partial. Seeing a body does not reveal the killer. Hearing an argument does not reveal every word or motive. Being an actor in an event does not imply awareness of every objective field.

### Layer D — Memory and belief
The person's retained/interpreted model of what happened or is true. Memories can fade or be reinterpreted. Beliefs have confidence and evidence ancestry and can be false.

### Layer E — Public/private expression
What a person chooses to communicate, record, teach, conceal or lie about. Expression is an action, not a transparent dump of belief.

A person may:
- tell the truth;
- lie knowingly;
- speak uncertainly;
- repeat falsehood sincerely;
- omit details;
- exaggerate;
- protect a secret;
- misremember;
- write propaganda;
- record something accurately despite disliking it.

## 3. Truth metadata is privileged

`KnowledgeClaim.truth` or equivalent omniscient truth metadata exists for simulation/testing/historian use only.

Forbidden consumers:
- NPC Agency;
- relationship assessment;
- rumor generation;
- investigation decisions;
- institutional judgment;
- player-facing knowledge unless the player legitimately learned it;
- dialogue/expression generation.

A subsystem that asks “is this claim actually true?” before deciding whether a person believes/acts on it has crossed the epistemic boundary unless it is explicitly an omniscient research/validation system.

## 4. Observation semantics

Observation answers:

> What evidence became available to this person, through what channel, and what portion of it could they perceive?

Channels may include:
- direct sensory observation;
- conversation/testimony;
- reading a record;
- teaching;
- institutional notice;
- inspecting an object/body/site;
- inference from multiple observations;
- magical perception where canon permits it.

Observation stores evidence access, not a prose sentence.

### Partial access
Events need visibility semantics/adapters. Examples:
- a public market transaction may be observable to nearby participants;
- a private payment may not be;
- a murder victim necessarily experiences the attack while conscious, but not necessarily attacker identity;
- a distant family member learns of a death only through transmission;
- a battle participant may know local combat but not command decisions elsewhere.

No universal actor-to-full-event-payload rule.

## 5. Perception error

Perception can fail without becoming arbitrary noise.

Sources of error include:
- distance;
- darkness/weather;
- crowding;
- concealment/disguise;
- speed;
- injury/fear/distraction;
- unfamiliar phenomena;
- poor sensory capability;
- magical interference where modeled.

Obvious nearby facts should not require pointless RNG rolls. Uncertainty should arise where the world actually provides uncertainty.

## 6. Claims

A claim is a structured proposition that can be believed, denied, transmitted, recorded or investigated.

Examples:
- `person:17 killed person:44`
- `object:9 belonged to person:3`
- `settlement:2 is unsafe`
- `person:8 can be trusted`
- `practice:12 originated in settlement:4`
- `god:X caused event:Y` (mortal theological claim unless objective divine causation is separately established by future cosmology)

Claims should be semantically stable enough to identify the same proposition across transmissions without requiring natural-language equality.

Claims may have objective truth status where the simulator can establish it, or `unknown` where reality itself does not resolve the proposition cleanly.

## 7. Belief

Belief is observer-specific confidence in a claim based on accessible evidence.

A person may:
- strongly believe a false claim;
- weakly believe a true claim;
- suspend judgment;
- hold contradictory claims with differing confidence;
- revise belief after new evidence;
- refuse evidence because of distrust or competing interpretation;
- forget why they believe something while retaining the belief weakly.

### Evidence weighting
Belief revision may consider:
- directness of observation;
- source-specific trust;
- source competence;
- corroboration/independence;
- contradiction;
- physical evidence;
- prior belief;
- cultural/institutional credibility;
- self-interest/identity pressure;
- memory accessibility;
- known deception history.

Do not implement a single universal Bayesian truth machine. Humans are bounded, evidence is heterogeneous and interpretation matters.

## 8. Testimony, honesty and deception

Communication separates three things:
1. what the speaker believes;
2. what the speaker intends the listener to believe;
3. what the speaker actually communicates.

A lie requires sufficient speaker knowledge/intention to distinguish it from sincere error.

Possible communication behavior:
- accurate testimony;
- sincere mistaken testimony;
- deliberate falsehood;
- selective omission;
- strategic ambiguity;
- exaggeration/minimization;
- refusal/silence;
- secret disclosure;
- coerced statement.

Honesty is therefore not a global trait. It is repeated conduct emerging from values, self-concept, relationships, fear, goals, incentives and expected consequences.

## 9. Source lineage

Information must retain enough ancestry to distinguish independent corroboration from repetition.

If Alice tells Bob, Bob tells Cara, and Cara tells Dan, Dan has not received four independent sources.

Transmission lineage should permit the system to identify:
- originating observation/claim where known;
- immediate source;
- chain length;
- mutations introduced along the chain;
- whether multiple reports share a common ancestor.

This prevents rumor popularity from automatically becoming evidence strength.

## 10. Rumor

Rumor is not a separate truth system. It is claim transmission through informal social channels with incomplete source authority and possible mutation.

Rumor spread depends on:
- contact/network structure;
- salience/novelty;
- relevance;
- trust;
- status of source;
- emotional charge;
- secrecy pressure;
- cultural interest;
- opportunity to communicate.

Mutation can include:
- entity substitution;
- certainty inflation/deflation;
- causal simplification;
- motive invention;
- quantity exaggeration;
- omitted qualifiers;
- merging related claims.

Mutation must remain causally linked to source information rather than generating arbitrary lore.

## 11. Secrets

A secret is **true or believed information with intentionally restricted access**, not a magic `secret` flag that makes everyone behave correctly around it.

Secret state is relational/access-based:
- who knows/believes it;
- who is believed to know it;
- who is authorized to know it;
- who wants it concealed/revealed;
- evidence/records that could expose it.

Secrets can leak through:
- deliberate disclosure;
- betrayal;
- overhearing;
- stolen/found records;
- investigation;
- inference;
- coercion;
- careless behavior;
- death/inheritance of records.

A person can wrongly believe a secret is still contained.

## 12. Records and information objects

Stage 5 will generalize information objects, but the epistemic contract is frozen here.

An information object may be:
- letter;
- diary/journal;
- ledger;
- legal record;
- institutional notice;
- map;
- inscription;
- book/manual;
- family genealogy;
- testimony transcript;
- research notes;
- religious text;
- artistic work carrying factual claims.

A record contains claims/assertions created by an author/institution at a time. The record itself is an objective artifact; its contents are not automatically true.

Records have provenance:
- creator;
- creation event/year;
- ownership/custody;
- copies/derivatives;
- alteration/forgery where applicable;
- destruction/loss;
- discovery/access.

Do not duplicate existing material provenance. Information objects should attach content/claim references to ordinary object/provenance authority where physically instantiated.

## 13. Institutional knowledge

An institution does not possess magical hive-mind knowledge.

Institutional knowledge exists through:
- living members;
- roles/offices;
- records;
- procedures;
- archives;
- transmitted practices;
- institutional claims/notices.

Consequences:
- founder death can remove undocumented knowledge;
- a bureaucracy can remember what every current member forgot if records survive;
- records can contradict current leadership;
- factions within one institution can believe different things;
- forged/destroyed records can alter institutional decisions;
- succession can change interpretation without changing archived facts.

## 14. Family memory

Families transmit claims, objects and practices across generations through ordinary channels.

A family story may begin with a true event and drift. A relic may corroborate part of it. A ledger may contradict it. A long-lived ranked ancestor may personally remember the event but still possess a subjective memory rather than privileged access to the event object.

Long-lived witnesses are valuable evidence sources, not omniscient truth terminals.

## 15. Reputation

Reputation is a derived model of what an observer/group believes about a person, based on evidence and transmitted claims.

There is no universal `reputation = 73`.

Possible observer-specific assessments include:
- trustworthy;
- dangerous;
- generous;
- skilled;
- cowardly;
- honorable;
- corrupt;
- pious;
- unreliable;
- competent.

These are beliefs/interpretations with evidence, not objective personality fields.

A celebrated war hero in one settlement can be remembered as a butcher in another without the simulation choosing one reputation as globally correct.

## 16. Investigation

Investigation is purposeful evidence acquisition and belief revision.

A generic investigation loop:

`question/goal -> known evidence -> hypotheses/claims -> choose next accessible lead -> acquire observation -> revise beliefs -> continue/stop/act`

Investigators can:
- miss evidence;
- misinterpret evidence;
- trust a liar;
- distrust a truthful witness;
- find forged records;
- contaminate/destroy evidence;
- stop too early;
- be pressured/bribed/threatened;
- correctly solve a case;
- remain uncertain.

No `solve_crime()` truth lookup.

## 17. Crime and legal judgment

Objective guilt and legal/social judgment are separate.

The world can know that Person A killed Person B. A court may convict A, convict C, acquit everyone or never learn a killing occurred.

Legal outcomes depend on:
- law/jurisdiction;
- evidence available;
- investigators;
- witnesses;
- credibility/trust;
- records;
- procedure;
- power/dependency/corruption;
- decision makers' beliefs.

Wrongful conviction and unsolved crime must be possible without scripted drama.

## 18. Propaganda and misinformation

Propaganda does not require a special mind-control mechanic. It is strategic information production/distribution using ordinary systems:
- repeated claims;
- selective facts;
- omission;
- forged/manipulated evidence;
- institutional authority;
- emotional salience;
- censorship;
- source control;
- social repetition.

Effectiveness depends on recipient prior beliefs, trust, access to alternatives, relationships, identity/values and corroborating experience.

Truthful information can also be propaganda if strategically selected/distributed. The system should model mechanism, not moral label.

## 19. Lost knowledge and rediscovery

Knowledge genuinely disappears when no accessible carrier remains:
- all knowledgeable people die/forget;
- records are destroyed/lost/unreadable;
- practice transmission breaks;
- language changes beyond interpretation;
- institution collapses;
- secret holders disappear.

Objective historical truth remains in the simulator/archive, but civilization no longer knows it.

Rediscovery can occur through:
- independent invention;
- archaeology;
- recovered records;
- surviving objects;
- rediscovered teacher/community;
- experimentation;
- translation/decipherment.

Rediscovery need not recreate the original interpretation exactly.

## 20. Archaeology and historiography

Later people reconstruct the past from surviving evidence, not from the archive.

Potential sources:
- ruins;
- graves/bodies;
- crafted objects/provenance clues;
- inscriptions;
- records/copies;
- oral traditions;
- institutional archives;
- environmental traces;
- long-lived witnesses;
- magical evidence where canon permits.

Historical interpretations are claims. Competing schools can exist. New evidence can overturn consensus.

The omniscient archive exists so developers/players in appropriate research modes can compare historical belief to what actually happened; it never leaks into in-world scholarship.

## 21. Player epistemics

Eventually the player obeys the same information rules as NPCs.

The player may know:
- what they directly observed;
- what others told them;
- what records/objects they accessed;
- what they inferred;
- any explicit meta-knowledge permitted by the game design across replays.

The player character does not automatically inherit the human player's previous-timeline knowledge.

UI must distinguish, where useful, between:
- observed fact/evidence;
- reported claim and source;
- character belief/inference;
- uncertain/contradictory information.

Do not expose hidden truth merely because the UI can access it internally.

## 22. Information and Agency

Agency candidate generation is epistemically constrained.

A person cannot:
- investigate a suspect they have no reason to know exists;
- travel to a secret location they never learned;
- buy from a merchant they do not know about;
- exploit an enemy weakness they have not discovered;
- react to a death before news arrives;
- choose a magical opportunity absent from their known opportunity set.

They can act on false information. This is essential.

## 23. Information and relationships

Relationship assessments update from observed/remembered/transmitted evidence, not objective private state.

If A secretly betrays B and B never learns, B's trust does not drop because the simulator knows the betrayal occurred.

If B falsely believes A betrayed them, trust may collapse despite A's innocence.

This single rule is central to making social history genuinely causal.

## 24. Information and Psyche

Psyche affects interpretation without creating facts.

Examples:
- baseline trust affects initial source weighting;
- status sensitivity affects attention to humiliation/status claims;
- fear increases salience of threat evidence;
- values/self-concept affect motivated interpretation;
- relationships affect testimony credibility;
- curiosity affects investigation/information seeking.

Psyche may alter what evidence means to a person, but cannot authorize evidence the person never received.

## 25. Performance architecture

Deep epistemics must remain sparse.

Rules:
- event-driven observation fan-out only to plausible observers/recipients;
- index observations by observer/event;
- index beliefs by person/claim;
- transmission uses social/institutional/contact pathways, not population-wide broadcast unless the channel actually is public/broadcast;
- memory remains bounded;
- records/objects persist through provenance rather than being copied into every person's mind;
- rumor lineage uses compact references;
- belief revision occurs when new evidence arrives or a relevant goal triggers reconsideration, not every year for every claim;
- no person x all-events or person x all-claims scans.

## 26. Information lifecycle examples

### Murder with no witness
1. A kills B privately.
2. Objective event records A/B and causes.
3. A may observe/remember their own conduct according to access/consciousness.
4. C later finds B's body and observes wounds/location—not killer identity.
5. C forms hypotheses.
6. D lies that E was seen nearby.
7. C trusts D and raises confidence in E's guilt.
8. Physical evidence later implicates A.
9. Depending on access/trust/institutions, belief may revise—or not.

### Family legend
1. Ancestor saves settlement.
2. Family witnesses/records transmit claims.
3. Over generations motive/details mutate.
4. Sword with provenance survives and becomes symbolically important.
5. A later historian finds contemporary ledger showing the ancestor was paid heavily.
6. Descendants disagree whether this changes the meaning of the act.

The objective event never changed. Human history did.

### Lost technique
1. Craftsperson develops technique.
2. Teaches two apprentices and records partial notes.
3. One apprentice dies; another migrates.
4. Workshop burns, destroying notes.
5. Local practice disappears.
6. Centuries later an archaeologist finds an object displaying unexplained construction evidence.
7. Scholars form competing claims.
8. A craftsperson independently reconstructs a similar technique.

No technology-level counter was required.

## 27. Behavioral acceptance scenarios

1. Two co-located witnesses can retain different beliefs about the same event.
2. A person cannot use an event field they did not observe.
3. A sincere false witness can mislead an investigation without any liar flag.
4. A deliberate liar can fail because physical evidence/source distrust outweighs testimony.
5. Ten repeated reports descended from one rumor source are distinguishable from ten independent observations.
6. A secret can remain hidden despite objective archive truth.
7. A secret can leak without the owner learning that it leaked.
8. A person can falsely believe another person knows their secret.
9. An institution can preserve knowledge after all original participants die.
10. An institution can lose undocumented knowledge when key people die.
11. A forged record can influence history while remaining objectively forged.
12. Later provenance/evidence can expose that forgery.
13. Two regions can hold opposing reputations of the same person.
14. B's trust in A does not change from A's secret action until evidence reaches B.
15. B can distrust innocent A because false evidence reached B.
16. A court can reach the wrong verdict through causally legitimate evidence/belief processes.
17. A crime can remain permanently unsolved.
18. Knowledge can disappear from civilization while objective archive truth persists.
19. Rediscovery can produce a new interpretation rather than restoring an old culture tag.
20. A long-lived witness can be wrong about an event they personally experienced.
21. Player/NPC knowledge obeys the same access boundary.
22. Removing omniscient archive access from all NPC-facing APIs does not break legitimate knowledge transmission.

## 28. Open design questions

Not yet frozen:
- exact structured proposition grammar for claims;
- how inference creates new claims from multiple observations without combinatorial explosion;
- source-lineage compression strategy;
- record-copy/translation fidelity mechanics;
- literacy/language gating;
- evidence persistence/decay for physical traces;
- magical detection/divination rules pending objective magic/cosmology canon;
- interrogation/coercion mechanics;
- institutional access permissions and secrecy classes;
- public-news/broadcast scale in advanced societies;
- exact belief-confidence revision equations;
- historian disagreement/academic-school mechanics;
- how much information-object content is structured vs rendered language.

Coding agents must not invent these as convenient defaults.

## 29. Implementation sequencing

This design spans multiple roadmap stages and must be implemented incrementally:

1. Stage 0.5: finish existing simulation stabilization and freeze gold baseline.
2. Stage 1: Observation authorization, evidence-backed belief, bounded Memory and Agency epistemic boundary.
3. Stage 2: developmental transmission/family/peer/mentor integration.
4. Stage 3: rumor, secrets, reputation, records/evidence and investigation.
5. Stage 4: institutional records, legal judgment, governance information flows.
6. Stage 5: general information objects, scholarship, lost knowledge, archaeology, historiography, authored works/language interfaces.
7. Stage 7: player-facing epistemic UI/interaction.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Information principle:** truth exists globally; knowledge exists locally; evidence is the bridge; history is what survives the crossing.
