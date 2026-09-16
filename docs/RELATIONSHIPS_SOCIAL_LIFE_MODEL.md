# ATE Relationships & Social Life Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze and the relevant Stage 1 subjective-state contracts.  
**Purpose:** define how repeated contact becomes familiarity, friendship, trust, love, resentment, obligation, rivalry, family bonds, enemies, social circles and collective relationships without reducing human connection to a universal affinity meter.

## North star

A relationship is not one number shared by two people.

ATE should model three distinct things:

1. **shared history** — objective interactions/events involving both people;
2. **A's model of B** — A's directional feelings, expectations and beliefs about B;
3. **B's model of A** — independently formed from B's evidence, memories and psyche.

Thus:

`shared events -> each person's observations/memories -> directional assessments -> future decisions -> new shared events`

Two people can participate in the same relationship while experiencing different relationships.

## 1. Existing authority

Current `SocialGraph`/`Relationship` remains the authority for pair identity, adjacency, partnerships and shared history until deliberate migration.

The current symmetric fields are compatibility state, not the final subjective model. Stage 1 adds sparse directional `(observer, subject)` assessments while preserving shared history.

Do not create a second disconnected social graph.

## 2. Shared history versus subjective relationship

### Shared history
Objective references to interactions/events both people participated in or that directly altered the relationship:
- meeting;
- conversation;
- trade;
- work;
- teaching;
- help/rescue;
- gift;
- promise;
- conflict;
- betrayal;
- intimacy;
- marriage/partnership;
- shared danger;
- caregiving;
- debt;
- public insult;
- reconciliation;
- separation;
- death.

Shared history does not contain a verdict such as `good_relationship=True`.

### Directional assessment
Each person may separately model:
- affection;
- trust;
- respect;
- fear;
- attraction;
- resentment;
- obligation;
- rivalry;
- dependency;
- familiarity.

`None` means unknown/unmodeled, not neutral.

Contradictory dimensions are valid. A can love B, fear B, resent B and depend on B simultaneously.

## 3. Familiarity

Familiarity is exposure/knowledge, not affection.

It increases through:
- repeated contact;
- shared work/home/community;
- meaningful events;
- learning information about the other person;
- indirect reputation where appropriate, though knowing *of* someone is distinct from knowing them personally.

Familiarity can decay in accessibility after long separation, but meaningful history may remain salient.

High familiarity can coexist with hatred.

## 4. Affection

Affection is positive emotional attachment/warmth toward a person.

Potential causes:
- enjoyable interaction;
- caregiving;
- shared history;
- similarity/understanding;
- admiration;
- gratitude;
- family attachment;
- companionship;
- intimacy;
- repeated reliable support.

Affection does not imply trust, compatibility, attraction, loyalty or moral approval.

A person can love someone they do not trust.

## 5. Trust

Trust is domain-sensitive expectation that another person will behave reliably/non-harmfully in a relevant context.

A single scalar may be an engineering approximation initially, but semantics must allow evidence to differ by domain:
- keeps promises;
- protects confidences;
- tells the truth;
- pays debts;
- performs competently;
- remains loyal under pressure;
- will not use violence.

Trust changes from **known evidence**, not hidden truth.

If A betrays B secretly and B never learns, B's trust does not magically decline. If B falsely believes A betrayed them, trust can collapse despite innocence.

Baseline trust affects priors; person-specific evidence should dominate with sufficient history.

## 6. Respect

Respect is positive assessment of competence, character, achievement, courage, judgment, status or other valued qualities.

It depends on what the observer values and believes.

A may respect B's fighting ability while despising B morally. A child may love a parent while losing respect for them. An enemy may earn respect.

Respect is not status itself.

## 7. Fear

Interpersonal fear is expectation of harm, loss, domination or dangerous unpredictability associated with another person.

Sources can include:
- witnessed violence;
- threats;
- reputation believed by observer;
- rank/power disparity when understood;
- coercive dependency;
- prior abuse;
- institutional authority;
- uncertainty combined with perceived danger.

Fear can coexist with affection, respect, attraction or loyalty.

## 8. Attraction

Attraction is not love and not partnership compatibility.

It may be influenced by:
- embodiment/preferences;
- familiarity;
- charisma/social interaction;
- admiration/status;
- novelty;
- emotional context;
- culture;
- existing relationship;
- individual developmental history.

Attraction creates pressure/opportunity for courtship/intimacy goals but never forces action.

Future species/culture design may alter mating/partnership patterns; do not assume one universal structure beyond explicit canon.

## 9. Resentment

Resentment is retained negative motivational/emotional response to perceived injury, unfairness, humiliation, exploitation, betrayal or unmet obligation.

It acts on perceived history. A can resent B for something B never did.

Resentment can:
- fade;
- persist;
- intensify through reinforcement;
- coexist with affection;
- motivate avoidance, confrontation, revenge or boundary-setting;
- survive reconciliation in reduced form.

Forgiveness does not require memory deletion.

## 10. Obligation

Obligation is perceived duty/debt toward another person.

Sources:
- kinship norms;
- promises;
- gifts/favors;
- rescue;
- debt;
- caregiving;
- employment/service;
- mentorship;
- marriage/partnership;
- institutional role;
- cultural expectation.

Objective contracts/debts may exist separately. Subjective obligation is what the person believes they owe.

A person may reject an obligation others believe is binding.

## 11. Rivalry

Rivalry is sustained comparative competition focused on another person/group.

It emerges from:
- competition for scarce opportunities;
- status sensitivity;
- repeated comparison;
- overlapping goals;
- institutional competition;
- romance;
- craft/magical achievement;
- inherited social conflict.

Rivalry need not imply hatred. Friendly rivalry and murderous rivalry use the same causal foundations but diverge through history/values/escalation.

## 12. Dependency

Dependency is practical reliance on another person for important needs/opportunities.

Examples:
- income/employment;
- housing;
- food;
- childcare;
- magical teaching/resources;
- healing;
- protection;
- market access;
- introductions/status;
- debt/credit;
- institutional access.

Dependency is not affection or loyalty. It changes the cost of disagreement, separation and betrayal.

Power frequently emerges from asymmetric dependency rather than a universal power score.

## 13. Friendship

Friendship is an emergent stable pattern, not a relationship class assigned at meeting.

Typical ingredients:
- voluntary repeated interaction;
- mutual affection;
- sufficient trust;
- shared experiences/interests;
- reciprocal support;
- social opportunity;
- persistence over time.

But friendships vary. Some are activity-based, intimate, practical, childhood-rooted, professional or intermittent.

Friendship can survive disagreement and distance. It can also quietly decay without a betrayal event.

### Non-instrumental interaction
People must sometimes socialize because they enjoy one another, not because every interaction optimizes resources.

Examples:
- visiting;
- eating/drinking together;
- games;
- stories/jokes;
- walking/traveling together;
- hobbies;
- festivals;
- watching competitions;
- casual conversation;
- helping with mundane work.

These interactions are important precisely because they create relationship history before dramatic events occur.

## 14. Enmity

Enemy is a retrospective/derived description of sustained hostile relationship, not a permanent boolean.

Enmity may arise from:
- direct harm;
- competition;
- revenge;
- family/institutional conflict;
- false belief;
- ideological disagreement;
- humiliation;
- resource disputes;
- violence.

Enemies can reconcile. Friends can become enemies. Neither transition requires deleting old history.

## 15. Reconciliation and forgiveness

Reconciliation is a process, not a button.

Potential causal ingredients:
- cessation of harm;
- apology/admission;
- restitution;
- changed behavior over time;
- new shared goals/threats;
- testimony/evidence changing beliefs;
- mediation;
- empathy;
- fatigue with conflict;
- changed dependencies;
- time/distance.

Possible outcomes:
- full renewed closeness;
- civil coexistence;
- forgiveness without trust;
- trust without affection;
- unresolved resentment despite cooperation;
- failed reconciliation.

A relationship can never be reconstructed solely from its current numeric assessments; shared history matters.

## 16. Family relationships

Kinship is objective genealogy/social structure. Family bond is lived relationship.

Biological relation does not guarantee:
- affection;
- trust;
- obligation;
- contact;
- loyalty.

Non-biological relationships can become family-like through caregiving, adoption, partnership, household history and cultural recognition.

Family dynamics emerge from:
- co-residence/contact;
- caregiving;
- inheritance/property;
- expectations;
- favoritism/comparison;
- shared loss;
- obligation;
- marriage/partnership;
- migration;
- class/status;
- magical tradition/access;
- transmitted stories/grievances.

## 17. Parent and adult child

Parent-child relationships continue changing after childhood.

Possible pressures:
- independence;
- marriage/partners;
- grandchildren;
- inheritance;
- profession;
- magical choices;
- migration;
- cultural/generational divergence;
- caregiving reversal in old age;
- long-lived ranked parents outliving ordinary descendants.

A parent can sincerely believe a relationship is close while the adult child experiences it as obligation or distance.

## 18. Sibling relationships

Sibling bonds depend on actual shared development:
- age gap;
- co-residence;
- competition for resources/attention;
- caretaking;
- shared peers;
- inheritance;
- comparison;
- protection;
- family crises;
- adult distance/cooperation.

No fixed sibling affinity bonus beyond appropriate familiarity/opportunity from shared household history.

## 19. Romance, courtship and partnership

Keep distinct:
- attraction;
- affection/love;
- compatibility;
- trust;
- commitment;
- sexual/romantic behavior;
- legal/cultural partnership status;
- household/economic partnership.

A relationship can have some without others.

Courtship/partnership decisions draw from:
- attraction;
- affection;
- values;
- goals;
- cultural/family expectations;
- material conditions;
- status/class;
- trust;
- opportunity/contact;
- existing commitments;
- known alternatives.

Ordinary stable partnerships should be common where conditions support them. The simulator should not manufacture romantic drama for entertainment.

## 20. Breakup, separation and widowhood

Relationships can end or transform through:
- incompatibility;
- betrayal;
- violence;
- changed goals;
- migration;
- institutional/religious/legal constraints;
- family pressure;
- economic conditions;
- death.

Ending partnership status does not erase relationship state/history. Former partners may retain affection, resentment, obligation, shared children, property or social ties.

Widowhood is not merely removal of partner edge; it can alter grief, household economy, caregiving, social network, goals and future relationship choices.

## 21. Social circles

Groups should emerge from overlapping actual relationships/contact, not assigned faction membership alone.

Examples:
- childhood friend circle;
- tavern regulars;
- craft peers;
- hunting companions;
- parents/households;
- adventuring companions;
- scholarly circle;
- neighborhood network;
- informal political clique.

A social circle can exist without formal institution state. It becomes formal only when roles/rules/resources/identity/continuity justify an institution.

### Group cohesion
Derived from network structure and shared history:
- density of ties;
- trust/affection;
- shared activities/goals;
- identity narratives;
- external pressure;
- internal conflict.

Do not store a magical cohesion score as causal authority if it can be derived/indexed.

## 22. Introductions and network access

Relationships create opportunity.

A person may learn about jobs, teachers, merchants, magic resources, partners, institutions, housing, credit or travel through people they know.

This makes social capital causal without requiring a universal social-capital stat.

Introductions should preserve source lineage: who connected whom can later matter for obligation, trust and reputation.

## 23. Gossip and third-party relationships

People form beliefs about people they have never met through testimony/reputation.

Distinguish:
- `knows_of` — has claims/information about person;
- `familiar_with` — meaningful direct exposure;
- `relationship` — enough actual or believed interpersonal history for directional assessment.

Gossip can alter anticipated trust/fear/respect before first meeting, but direct experience may later reinforce or overturn it.

## 24. Social status and humiliation

Status is contextual and observer/group-relative.

Public events can affect relationships because observers learn them:
- praise;
- promotion;
- victory;
- generosity;
- scandal;
- insult;
- failure;
- punishment;
- cowardice claims;
- displays of wealth/power.

Humiliation requires perceived social loss, not merely objective failure. Status-sensitive people weight it more strongly, but everyone remains context-dependent.

## 25. Conflict escalation

Interpersonal conflict should normally escalate through available stages rather than jump directly to violence:

`avoidance -> disagreement -> argument -> appeal/mediation -> gossip/social retaliation -> economic retaliation -> threats -> sabotage -> assault -> killing -> organized retaliation`

This is not a mandatory ladder. People may skip stages when danger, aggression, power, urgency or norms justify it. Most conflicts should stop before lethal violence.

Escalation pressure depends on:
- stakes;
- resentment;
- fear;
- aggression;
- injustice sensitivity;
- available mediation;
- legal/institutional constraints;
- power disparity;
- allies;
- values/self-concept;
- prior history;
- expected consequences.

## 26. Relationship events and interpretation

An objective interaction should produce different subjective updates for participants/observers.

Example: A gives B money.

Possible interpretations:
- B: gratitude/obligation;
- A: ordinary generosity;
- C: believes A is buying loyalty;
- D: sees favoritism and becomes resentful;
- B later learns A expected repayment and revises the memory.

One objective event can therefore propagate through social history without carrying a single canonical emotional meaning.

## 27. Absence, distance and time

Relationships should not require constant interaction to persist.

Effects of separation depend on:
- prior strength/history;
- communication channels;
- personality/needs;
- new relationships;
- unresolved conflict;
- major life events missed;
- duration;
- cultural expectations.

Some friendships resume easily after decades. Others fade. Long-lived people may reconnect after lifetimes of ordinary humans.

## 28. Death and social aftermath

Death freezes neither social history nor reputation.

After death:
- survivors retain memories/assessments;
- grief/relief/guilt may occur;
- debts/obligations/property transfer;
- secrets may die or surface;
- reputation can change through later evidence;
- descendants may inherit claims/grievances/obligations;
- institutions/families reinterpret the deceased.

A dead person's relationships continue causing history through survivors.

## 29. Power and relationships

Power changes relationship options and costs rather than generating loyalty.

Sources of interpersonal power:
- wealth;
- rank/magic;
- institutional authority;
- legal authority;
- dependency;
- information/secrets;
- reputation;
- family/network connections;
- violence capability;
- control of scarce resources.

A subordinate can love, hate, fear, respect and depend on the same superior simultaneously.

Power can conceal relationship truth because outward compliance is not inward loyalty.

## 30. Relationships and Agency

Agency should consume directional assessments only when relevant to known candidates.

Examples:
- high trust lowers perceived risk of cooperation;
- affection increases weight of another person's welfare;
- obligation creates pressure to help;
- resentment raises attractiveness of retaliation/refusal;
- fear raises expected cost of confrontation;
- attraction can generate courtship/intimacy goals;
- dependency raises cost of severing ties;
- respect raises source credibility/advice weight in relevant domains.

No dimension is an action command. High resentment does not force revenge. High affection does not force sacrifice.

## 31. Relationship change semantics

Updates require evidence/experience.

Large changes should generally require:
- high-salience event;
- repeated pattern;
- strong new evidence;
- major reinterpretation.

Mundane repeated contact can use bounded aggregates rather than event-per-conversation storage.

Avoid yearly arbitrary drift toward neutral. Relationships can remain stable across long quiet periods.

## 32. Performance architecture

Relationships are sparse.

Rules:
- no all-person pair matrix;
- create/activate edges through household, locality, work, school, institution, trade, travel, events and introductions;
- shared history stores bounded/significant refs plus optional compact aggregate interaction summaries;
- directional assessments indexed by observer;
- routine social interaction sampled from plausible local networks;
- event reactions target participants/observers/close affected ties;
- dead/distant low-salience edges may become cold/archive state without deletion of important history;
- no yearly all-edge emotional recomputation.

Most strangers remain strangers.

## 33. Behavioral acceptance scenarios

1. A trusts B more than B trusts A.
2. A loves B but does not trust B.
3. A fears and respects an enemy simultaneously.
4. Secret betrayal does not reduce victim trust until evidence arrives.
5. False betrayal evidence can destroy an innocent relationship.
6. Friendship can form from repeated ordinary enjoyable contact without shared crisis.
7. Childhood friends can drift apart without a betrayal event.
8. Estranged friends can reconnect while retaining old grievances/memories.
9. Forgiveness can occur without restored trust.
10. A sibling relationship reflects actual childhood history rather than a fixed kinship bonus.
11. Biological kin can be emotionally distant; non-kin caregiver can become family-like.
12. Attraction can exist without affection or compatibility.
13. Stable ordinary marriage/partnership can persist for decades without drama injection.
14. Former partners retain shared children/property/obligation/history after separation.
15. A social circle emerges from overlapping ties without becoming a formal institution.
16. A job/magic opportunity can propagate through introductions and relationship networks.
17. Two regions can treat the same person differently because reputation evidence differs.
18. Public compliance with a powerful person does not imply private loyalty.
19. A person can remain friends with someone whose conduct they morally disapprove of, with resulting dissonance/conflict.
20. An enemy can become a trusted ally through sufficient shared history without resetting the relationship.
21. Death of a central person can reorganize a network causally rather than simply deleting edges.
22. Most people have bounded local social networks rather than relationships with the whole settlement/world.
23. Removing derived labels `friend`, `enemy`, `leader`, `popular` does not change underlying causal behavior.

## 34. Open design questions

Not yet frozen:
- whether trust needs explicit domain subcomponents in persistent state or evidence-derived overlays;
- exact routine-contact aggregation representation;
- attraction preference/compatibility semantics across species/cultures;
- partnership/marriage forms beyond current baseline;
- jealousy semantics and whether it needs a distinct drive versus composed fear/status/attachment;
- group/social-circle detection algorithm;
- how long-lived people maintain very large lifetime networks while preserving bounded active state;
- inheritance of obligations/debts/grievances across generations;
- social norms around kinship/partnership once culture is richer;
- network effects on migration and settlement formation;
- how institutional roles modify contact frequency without conflating role with personal relationship.

Coding agents must not invent these answers merely for convenience.

## 35. Implementation sequencing

1. Stage 0.5: stabilize current simulation and freeze gold baseline.
2. Stage 1: preserve shared `SocialGraph`; add sparse directional assessment contract and Observation/Memory/Psyche/Agency foundations.
3. Stage 2: friendship, family-development, courtship/partnership, ordinary socializing and generational relationships.
4. Stage 3: gossip/reputation/secrets interacting with relationships.
5. Stage 4: social circles feeding collective action/institution formation, dependency/power and governance.
6. Stage 6: conflict escalation connecting relationships to temporal violence.
7. Stage 7: player-facing relationships without universal loyalty/faction meters.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Social principle:** people do not share a relationship state; they share a history and carry their own relationship to it.
