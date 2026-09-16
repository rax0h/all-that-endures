# ATE Human Psyche Semantics v1

**Status:** design specification only. Stage 1 implementation remains blocked by the Stage 0.5 current-simulation stabilization/gold-baseline gate.  
**Purpose:** define what a person means inside ATE before code assigns weights or schemas to human behavior.

## North star
ATE does not generate heroes, villains, leaders, cowards, recluses, saints, criminals, lovers or tyrants as personality classes. It generates people with dispositions, needs, values, beliefs, memories, relationships, identities, opportunities and power. Those recognizable human roles are descriptions of lives after the fact.

The causal loop is:

`temperament -> development -> values/self-concept -> current drives -> beliefs/memories -> relationships -> goals -> known opportunities -> decision -> consequence -> updated person/world`

No single layer determines behavior. Preference is not destiny. Character is not a score.

## 1. Five distinct layers of personhood

### Temperament — how a person tends to respond
Slow-moving baseline dispositions. Partially innate/developmental, never moral. Temperament changes only modestly over ordinary adulthood but can be shaped during development and sometimes altered by extraordinary experience.

### Character and values — what a person has learned to care about
Revisable commitments formed through family, culture, experience, imitation, institutions, success, failure and reflection. Values can conflict.

### Drives and emotions — what is pressing now
Dynamic state such as hunger, safety, belonging, grief, anger, attraction, recognition, revenge, rest or curiosity. Drives can temporarily overwhelm stable preferences without rewriting character.

### Beliefs, memory and self-concept — what the person thinks is true
Includes beliefs about the world, remembered experience, interpretations of events and beliefs about oneself. These may be wrong.

### Goals and decisions — what the person is trying to do
A bounded active set produced by the layers above plus circumstances. Goals are not personality. Agency chooses attempts from what the person actually knows and believes is possible.

## 2. Temperament dimensions

Use continuous dimensions, not named types. Each dimension should have a semantic meaning independent of gameplay outcome.

### Sociability
Baseline reward/comfort from interpersonal engagement.
- low: solitude is less costly and often preferred;
- high: interaction, company and social stimulation are more rewarding.
Does not equal kindness, charisma, popularity or social skill.

### Empathy
Tendency to internally weight and respond to perceived states of others.
- low empathy does not imply cruelty;
- high empathy does not imply courage, wisdom or altruistic action.
Empathy requires perception: a highly empathic person cannot respond to suffering they do not know about.

### Assertiveness
Readiness to state preferences, initiate interpersonal action, resist pressure and occupy social space.
Distinct from aggression, confidence, leadership and status desire.

### Conscientiousness
Tendency toward planning, follow-through, order, delayed gratification and obligation completion.
Can make a benevolent person reliable or a harmful person frighteningly methodical.

### Openness
Readiness to entertain unfamiliar ideas, experiences, customs, techniques and interpretations.
Distinct from curiosity: a person can intensely investigate a narrow familiar field while being closed to alternatives.

### Risk tolerance
Willingness to accept uncertainty and potential loss for expected gain or valued action.
Context and stakes matter; risk tolerance does not mean ignorance of danger.

### Aggression
Readiness to use confrontation, coercion or force when frustrated, threatened or pursuing a goal.
Does not mean sadism or evil. Protective aggression and predatory aggression may share disposition but differ in motive/value/context.

### Patience
Tolerance for delay, frustration and slow reward before abandoning/escalating/changing course.
Distinct from conscientiousness.

### Baseline trust
Prior tendency to extend credibility/good faith before strong person-specific evidence exists.
Specific learned trust overrides this through relationships and evidence.

### Ambition
Strength of desire to expand capability, achievement, influence, mastery or life position beyond the current state.
The object of ambition comes from values/goals. Ambition can produce scholarship, craftsmanship, wealth, service, power or adventure.

### Competitiveness
Degree to which relative performance/status against others is motivating.
A highly ambitious but noncompetitive person may seek mastery without caring whether anyone loses.

### Independence
Preference for self-direction and resistance to reliance/control by others.
Does not eliminate attachment or cooperation.

### Emotional volatility
Magnitude/speed of emotional response and return toward baseline.
Does not encode which emotions occur or whether behavior follows them.

### Curiosity
Drive to reduce uncertainty and acquire information/experience.
Distinct from openness and intelligence.

### Status sensitivity
Degree to which recognition, rank, prestige, humiliation and relative standing carry emotional weight.
Can motivate conformity, achievement, resentment, generosity, display or withdrawal depending on the rest of the person.

### Injustice sensitivity
Degree to which perceived unfairness, broken reciprocity or illegitimate treatment produces motivational/emotional response.
It acts on **perceived** injustice, so beliefs/culture can point it in very different directions.

## 3. Traits deliberately excluded
Do not persist these as foundational temperament dimensions:
- good/evil;
- brave/cowardly;
- loyal/disloyal;
- honest/dishonest;
- leader/follower;
- introvert/extrovert as a categorical type;
- intelligent/stupid as one score;
- criminal/lawful;
- religious/secular;
- romantic/promiscuous;
- hero/villain;
- work ethic as a moral label.

These are outcomes, reputations, beliefs, capabilities, values or context-dependent patterns that should emerge from more basic causes.

## 4. Capabilities are not temperament
Reasoning, learning, memory, verbal/spatial/numerical/practical ability, social perception, creativity, attention, physical capability and magical capability belong to capability/biology/skill systems, not Psyche temperament.

A brilliant person can be incurious. A curious person can reason poorly. A socially perceptive person can be unempathetic. A high-empathy person can misunderstand someone. Keep these separations because they create people rather than archetypes.

## 5. Values and commitments

Values answer: **what outcomes or principles matter to this person over time?**

Initial vocabulary should be broad but bounded and extensible. Candidate domains:
- family/kin;
- friendship/companionship;
- community;
- autonomy/freedom;
- security/stability;
- duty/obligation;
- justice/fairness;
- tradition/continuity;
- faith/devotion (only as mortal commitment; no assumption about theological truth);
- knowledge/understanding;
- mastery/craft;
- achievement;
- wealth/material comfort;
- status/recognition;
- power/control;
- service/protection;
- pleasure/enjoyment;
- exploration/novelty;
- legacy/posterity;
- beauty/creation.

Values are weighted commitments, not exclusive identities. A person may strongly value both family and autonomy. Conflict between values is a primary source of meaningful decisions.

### Formation
Adult values must have causal ancestry. Sources can include:
- caregiver modeling and reinforcement;
- household conditions;
- local culture/practices;
- peers/friends;
- teachers/mentors;
- institutions;
- formative memories;
- success/failure;
- deprivation/abundance;
- perceived injustice;
- admiration or rejection of exemplars;
- reflection after consequential events.

No culture writes a value directly into a person. Culture supplies repeated pressure, models, rewards, narratives and opportunities.

### Change
Values should usually drift slowly, but contradiction and major events can produce faster revision. Change can include strengthening, weakening, reinterpretation or reprioritization rather than simply flipping a value.

## 6. Drives and emotions

Drives answer: **what need, appetite or emotional pressure currently demands attention?**

Useful domains include:
- hunger/material need;
- safety/fear;
- belonging/loneliness;
- attachment/caregiving;
- attraction/intimacy;
- recognition/status;
- autonomy;
- curiosity;
- mastery/competence;
- wealth/security;
- rest/recovery;
- grief;
- anger;
- shame;
- guilt;
- revenge/retribution;
- purpose;
- obligation;
- pleasure/appetite.

Not every person carries every drive at all times. Store active/material drives sparsely.

### Emotion is not an action command
Anger does not mean attack. Fear does not mean flee. Grief does not mean withdraw. They alter attention, expected consequences and candidate weights through temperament, values, beliefs and circumstances.

Two people with equal grief may seek family, drink, pray, work obsessively, hunt the responsible party, leave town or continue functioning quietly.

## 7. Self-concept

Self-concept consists of beliefs about one's own identity, conduct, competence and obligations. Examples:
- I protect my family.
- I keep my word.
- I am a capable smith.
- I am a coward.
- I don't need anyone.
- People like us do not beg.
- I am meant for something greater.

Self-beliefs are claims with confidence/evidence, not hidden truth.

### Cognitive dissonance
When conduct or evidence conflicts with self-concept, Agency/Psyche may respond through several causally available paths:
- acknowledge and revise self-belief;
- guilt/shame;
- restitution/apology;
- renewed commitment;
- reinterpret the event;
- rationalize conduct;
- blame another person;
- suppress/avoid reminders;
- double down on a changed worldview.

There is no `redemption_arc()` or `corruption += 1`. Repeated decisions and reinterpretations create those trajectories.

## 8. Moral conduct without a morality meter

ATE needs moral behavior but not universal numerical morality.

A decision can be affected by:
- empathy;
- values such as justice, family, duty, power or security;
- relationship attachment/resentment/obligation;
- beliefs about who deserves what;
- expected social/legal consequences;
- self-concept;
- immediate drives;
- opportunity and capability.

The world records what happened. Observers judge it according to their own beliefs/values/culture. Historians may later describe a life. None of those judgments become a hidden global alignment score.

## 9. Courage, loyalty, leadership and similar emergent traits

### Courage
Not a trait. A courageous act occurs when a person knowingly accepts meaningful danger for another goal/value despite fear. Repeated conduct may cause observers or the person to believe they are brave.

### Loyalty
Not a trait. Loyalty emerges when attachment, trust, obligation, shared identity/history and values repeatedly outweigh competing incentives.

### Leadership
Not a trait. Leadership emerges when someone initiates/co-ordinates collective action and others accept influence because of trust, legitimacy, competence, status, dependency, fear, charisma-like social capability or circumstance.

### Honesty
Not a trait. Truth-telling behavior depends on values, expected consequences, fear, self-concept, relationships, goals and opportunity. A reputation for honesty is observer-relative evidence accumulated over time.

### Recluse
Not a trait. Low sociability, distrust, grief, fear, independence, circumstance and history may produce withdrawal. The same person may later re-enter society.

## 10. Development across a life

### Infancy/early childhood
No adult values/goals. Begin with temperament potential, needs, attachment formation and experience. Caregiver reliability, safety, stimulation, deprivation and social environment matter.

### Childhood
Imitation, reinforcement, family narratives, peers, local culture and early success/failure begin shaping values, self-concept, expectations and baseline social models.

### Adolescence
Identity differentiation, status sensitivity, peer influence, independence, attraction, ambition and conflict with inherited expectations can intensify. This is a strong period for worldview/value revision, not a scripted rebellion phase.

### Adulthood
Temperament is relatively stable; values/self-concept/relationships remain revisable. Work, marriage, children, loss, magic, institutions, conflict, wealth and failure create ongoing development.

### Long-lived ranked adulthood
Gold/Diamond longevity must not freeze personality. Centuries allow accumulated grief, changing cultures, repeated reinvention, entrenched commitments, fatigue, mentorship, dynastic relationships and very long memories/legends. Rate of change can slow through stability but never because rank mechanically locks psyche.

## 11. Family and culture are pressure, not destiny

Heritability may influence temperament distributions where appropriate, but a child is not a personality clone.

Family transmits through:
- genes/temperament tendencies where modeled;
- caregiver behavior;
- attachment/safety;
- stories and beliefs;
- values demonstrated in action;
- resources/class/opportunity;
- profession/craft exposure;
- magical access/tradition;
- relationships and obligations.

Culture transmits through repeated exposure, institutions, practices, stories, sanctions, rewards, peers and opportunities. Migration, generational change and personal rejection produce drift.

## 12. Goals

Goals are bounded active commitments generated from person + circumstances. They should be concrete enough to create candidate actions but broad enough to permit multiple strategies.

Examples:
- secure food for household;
- earn enough for an awakening stone;
- repair relationship with daughter;
- become competent in a craft;
- investigate brother's death;
- find companionship;
- protect settlement;
- gain recognition in Society;
- leave an unsafe marriage;
- preserve family workshop;
- avenge humiliation;
- understand an unusual magical phenomenon.

### Goal generation
Potential goal pressure is composed from:
`drives + values + self-concept + beliefs + relationships + obligations + known opportunities/threats + capabilities/resources`

Agency does not generate a goal from unavailable knowledge.

### Goal competition
Maximum active-goal cap remains 5 for Stage 1 engineering. Goals compete for attention by urgency, value fit, emotional pressure, opportunity windows, obligation and expected feasibility. Low-priority goals can remain latent rather than disappearing from the person's broader preferences.

## 13. Decision semantics

For a major choice, Agency should conceptually answer:
1. What am I currently trying to accomplish?
2. What do I believe is happening?
3. What options do I know about?
4. What do I expect each option to cost/risk/achieve?
5. How do those consequences interact with my values, drives, relationships and self-concept?
6. What am I capable of attempting?
7. Among the plausible options, what do I actually choose this time?

Weighted stochastic choice is appropriate only at step 7 after the plausible option set/weights are causally formed. RNG supplies historical contingency; it does not substitute for motivation.

## 14. Power changes consequences, not personality

Gaining wealth, office, magical rank or institutional authority does not automatically corrupt or ennoble a person. Power changes:
- available actions;
- cost of acting;
- who seeks the person's favor;
- exposure to temptation/threat;
- ability to avoid consequences;
- obligations and dependents;
- information access;
- social feedback.

The same psyche under new power may therefore produce very different conduct. This is how corruption, restraint, tyranny, service or withdrawal can emerge without a corruption mechanic.

## 15. Character arcs are historian descriptions

Possible retrospective classifications include:
- rise to prominence;
- fall from grace;
- redemption;
- radicalization;
- reconciliation;
- withdrawal;
- recovery;
- revenge;
- burnout;
- reinvention.

These are derived descriptions of event/person trajectories. They never feed back as causal state.

A villain can be redeemed because beliefs, relationships, values, circumstances and choices can change. Redemption does not erase victims' memories, legal consequences, reputations, deaths or history.

## 16. Ordinary people are the baseline

The system must not maximize drama. Most people should spend most years doing ordinary things: working, eating, raising children, maintaining friendships, learning, resting, celebrating, grieving, arguing, saving, wasting money, visiting, joking, making things and getting older.

Interesting history matters because it occurs among ordinary life. If every person constantly pursues extreme goals, the simulation has failed even if its event log is entertaining.

## 17. Performance semantics

Psychological depth is event-driven and sparse.

### Background state
Temperament, commitments and long-term self-concept are stored compactly and reconsidered rarely.

### Active state
Only a few current drives/goals require periodic evaluation.

### Event reaction
Deep reconsideration occurs when something consequential actually reaches the person: death, betrayal, birth, injury, inheritance, humiliation, opportunity, promotion, disaster, magical acquisition, relationship rupture, discovery, etc.

Do not calculate a full personality interpretation for every person every tick. The person is deep because state persists and consequences accumulate, not because the CPU re-simulates their entire mind annually.

## 18. Behavioral acceptance scenarios

1. Two children with comparable initial temperament but different caregivers can become meaningfully different adults.
2. Two siblings in the same household can diverge because temperament, relationships, peer experiences and opportunities differ.
3. A highly empathic person can still harm someone when beliefs, fear, duty or relationships make the act seem necessary.
4. A low-empathy person can live honorably because values, self-concept, relationships and expected consequences support it.
5. A fearful person can perform a courageous act; fear remains part of why the act is courageous.
6. A generally nonaggressive person can become violent after a sufficiently important threat without permanently acquiring an aggression flag.
7. A trusted person can betray someone, and the betrayal can produce different self-concept responses depending on psyche/history.
8. A former enemy can become a friend without deleting the earlier grievance/history.
9. A villainous historical reputation can coexist with sincere love from family or admiration from beneficiaries.
10. A person can rationalize wrongdoing for decades and later reinterpret it after new evidence/relationships.
11. A high-status person can voluntarily relinquish power; another can cling to it; neither outcome is hard-coded from rank.
12. A person can desire a magical identity they never obtain because opportunity/resources differ from preference.
13. An ordinary person can remain ordinary for an entire life without the simulator manufacturing an arc.
14. A Gold/Diamond person can meaningfully change over centuries without random personality rerolls.
15. Removing retrospective labels such as hero/villain/leader/recluse does not change simulation behavior.

## 19. Open questions intentionally not frozen yet

These require further design/calibration before implementation weights are frozen:
- exact inheritance/development distribution for temperament;
- whether all 16 dimensions need persistent values for every person or can be lazily instantiated/packed;
- exact value vocabulary and whether rare culture-specific values use an extensible semantic registry;
- exact drive activation/decay equations;
- goal scoring weights;
- degree of self-concept persistence/forgetting;
- how cognitive capabilities constrain planning horizon/candidate generation;
- how trauma-like long-term changes are represented without diagnostic labels;
- how magical abilities can directly affect emotion/memory/personality under canon;
- how non-human sapient psychologies reuse/diverge from the human contract.

These are design questions, not invitations for a coding agent to choose defaults.

## 20. Implementation prohibition while Stage 0.5 is open

Astra and other coding agents may read this document for future architecture context, but **must not implement this Psyche model until the Stage 0.5 gold baseline is frozen**. Current work remains the currency/magic-access/completion calibration and stabilization of the existing simulation.

Planning can continue. Code waits.
