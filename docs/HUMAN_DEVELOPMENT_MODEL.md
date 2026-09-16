# ATE Human Development Model v1

**Status:** design specification only. Implementation remains blocked until Stage 0.5 current-simulation stabilization and gold-baseline freeze are complete.  
**Purpose:** define how a newborn becomes a particular adult through temperament, caregivers, household conditions, relationships, culture, education, class, events, opportunity and their own choices.

## North star
A child is not a smaller adult with randomized adult values. A child begins with biological/developmental potentials, needs and temperament tendencies, then accumulates a history.

ATE should be able to answer, after the fact:

> Why did these two siblings become different people?

The answer should be reconstructable from differences in temperament, caregiver relationships, birth order/household state, peers, teachers, material conditions, events, opportunities, beliefs, memories and choices—not from an unexplained personality reroll.

## 1. Existing-system boundary

The current `development.py` is primarily **settlement/infrastructure/skill development**: adult workers practice skills, apprenticeship transmission occurs, infrastructure is maintained, and repeated trade can establish roads. It is valuable existing authority and should remain so.

Human developmental psychology must **not replace or overload that module conceptually**. When implemented later, use a distinct person-development authority/module that integrates with genealogy, households, social, skills, knowledge, transmission, culture and Psyche.

Likewise:
- genealogy owns parentage/descent;
- households own co-residence/material household context;
- social owns relationship history;
- skills own learned capability;
- knowledge/transmission own information movement;
- culture owns practices/history;
- Psyche owns persistent subjective development;
- human development coordinates causal influence among them but does not duplicate their state.

## 2. Development is exposure plus response

The basic developmental unit is not `age -> trait change`.

It is:

`developmental state + exposure/event + relationship/source + interpretation + repetition/salience -> possible developmental update`

The same exposure can affect two children differently because temperament, prior attachment, existing beliefs, relationship trust, age and later reinforcement differ.

Examples:
- strict household discipline may produce conscientiousness, fear, resentment, imitation, rebellion or little lasting effect;
- poverty may produce caution, generosity, status ambition, hoarding, resignation, solidarity or nothing singular;
- a celebrated adventurer parent may inspire imitation in one child and rejection in another.

No deterministic social stereotype is acceptable.

## 3. What exists at birth

A newborn may begin with:
- identity/species/embodiment;
- parentage and household membership;
- biological/developmental capability potential;
- temperament potential/distribution;
- immediate physiological needs;
- capacity to form attachment and memory appropriate to development;
- inherited material/social circumstances.

A newborn does **not** begin with adult:
- ideology;
- profession preference;
- religion/theology;
- political allegiance;
- moral alignment;
- social class identity as a belief;
- magical career aspiration;
- loyalty to an institution;
- hatred of a rival family;
- detailed values;
- adult goals.

Those require exposure/history.

## 4. Temperament inheritance and individuality

Temperament may be partially heritable where species biology supports it, but inheritance is distributional rather than copying.

Conceptually:

`child potential = species distribution + parental tendency influence + developmental variance`

Environment then affects expression and modest developmental drift.

Requirements:
- siblings are correlated more than strangers on average where heredity applies, not clones;
- identical household does not imply identical development;
- no parent's moral/social label is inherited;
- species biology must not become species personality;
- non-human sapient species may later define different developmental constraints without rewriting the universal epistemic/causal rules.

Exact inheritance weights remain calibration, not v1 canon.

## 5. Caregiving as relationship history

Do not store `parenting_style = strict/loving/neglectful` as causal truth.

Caregiving is accumulated behavior and conditions:
- presence/absence;
- responsiveness to need;
- protection;
- affection;
- consistency;
- discipline/punishment;
- teaching;
- encouragement;
- criticism;
- modeling;
- promises kept/broken;
- conflict witnessed;
- resource provision;
- favoritism;
- delegation of care;
- abandonment/death/separation.

A retrospective inspector may summarize these patterns, but development consumes the underlying interactions/events.

### Attachment
Attachment is relationship-specific before it is a generalized expectation.

A child may trust one caregiver and fear another. Repeated caregiver experience can later influence baseline expectations of others, but specific relationships remain distinct.

Caregivers need not be biological parents. Grandparents, siblings, foster/adoptive kin, household members, teachers or community members may become major developmental figures if actual care/contact supports it.

## 6. Household material conditions

Children experience class/resources through concrete consequences rather than an abstract class modifier:
- food security;
- housing stability/quality;
- crowding/privacy;
- caregiver time;
- access to books/tools/training;
- work obligations;
- debt/financial stress;
- servants/dependents where culture supports them;
- exposure to trade/travel;
- safety/violence;
- healthcare/healing access;
- magical resources/teachers;
- inherited property/business/institutional connections.

Wealth changes opportunity and pressure. It does not write values directly.

## 7. Developmental periods

Age bands are scheduling/sensitivity guides, not hard personality scripts. Species lifespan/development may alter their boundaries later.

### Infancy / very early childhood
Primary processes:
- attachment;
- safety expectation;
- sensory/social exposure;
- basic regulation;
- early familiarity;
- language exposure where appropriate.

Most experiences need not become explicit episodic memories to affect relationship familiarity/development.

### Childhood
Primary processes expand to:
- imitation;
- reinforcement;
- rule learning;
- play;
- sibling/peer relationships;
- skill discovery;
- stories/family narratives;
- local practices;
- school/apprenticeship exposure;
- competence/failure feedback;
- emerging self-concept.

### Adolescence / transition to adult autonomy
Possible pressures increase around:
- independence;
- peer belonging;
- attraction;
- status;
- vocation;
- magical aspiration/opportunity;
- inherited expectations;
- identity differentiation;
- risk;
- institutional entry;
- conflict between family/culture/self.

There is no mandatory rebellion mechanic. A young person may embrace, reinterpret, ignore or reject inherited expectations.

### Adulthood
Development continues through:
- partnership/marriage;
- parenthood;
- work/craft;
- magic progression;
- friendship;
- grief;
- injury;
- migration;
- wealth/poverty;
- institutional responsibility;
- conflict;
- discovery;
- aging;
- changes in culture around the person.

### Long-lived adulthood
For Gold/Diamond-scale lifespans, century boundaries themselves should not trigger personality rerolls. Long lives instead create unusual accumulations of relationships, losses, institutions, cultural displacement, mentorship and repeated identity revision.

## 8. Family narratives and inherited beliefs

Children can inherit **claims**, not truth.

Examples:
- “Our family built this town.”
- “The Harrow family betrayed us.”
- “Nobody from our house joins the Society.”
- “Your grandmother was chosen by a god.”
- “This sword belonged to your ancestor.”

These enter through ordinary knowledge/transmission channels with sources and confidence. Provenance/records may later support or contradict them.

This permits inherited grudges, pride, shame and obligation without genetically inherited ideology.

## 9. Siblings and birth-order effects

Do not create fixed firstborn/middle/youngest personality modifiers.

Birth order matters only through changed circumstances, such as:
- caregiver experience/age;
- household wealth at different years;
- number of competing dependents;
- responsibilities assigned to older children;
- sibling caretaking;
- inheritance expectations;
- parental death/remarriage;
- historical events occurring at different developmental ages;
- comparison/favoritism;
- different peer cohorts/teachers.

Thus birth order can matter enormously in one family and barely at all in another.

## 10. Peers and friendship

Peers are not generic `peer influence` multipliers. Influence depends on actual relationships:
- affection;
- trust;
- admiration/respect;
- status sensitivity;
- belonging need;
- frequency of contact;
- shared activities;
- perceived similarity/difference;
- fear/exclusion.

Children and adolescents should be able to teach one another, transmit beliefs/practices, reinforce norms, create private group norms, compete, bully, reconcile and drift apart.

Friendship can become developmentally important without serving a material goal.

## 11. Teachers, mentors and apprenticeship

The existing simulation already models skill teaching/transmission. Human development should deepen its personal consequences rather than invent a second teaching system.

A teacher/mentor can affect:
- skill/capability through existing skill systems;
- knowledge through knowledge/transmission;
- relationship state through social interaction;
- self-concept through success/failure/recognition;
- values through observed conduct and trusted claims;
- goals through newly known opportunities.

Mentorship effectiveness therefore depends on both teaching capability and relationship/access/history.

A technically excellent teacher can be hated. A beloved mentor can be mediocre at instruction. Keep those distinct.

## 12. Culture and local norms

Culture influences development through concrete exposure:
- common practices;
- household routines;
- festivals/rituals;
- stories;
- laws/enforcement;
- status rewards;
- sanctions/shame;
- professions visible nearby;
- architecture/public space;
- religion/institutions;
- gender/family-role expectations where a culture actually developed them;
- food/clothing/art/music;
- attitudes toward magic, wealth, violence, outsiders, learning, etc.

A child can conform without consciously endorsing a norm. Later self-concept/value formation may preserve, reinterpret or reject it.

Again: **culture creates pressure, not destiny.**

## 13. Education access and literacy

Education is opportunity constrained.

A child can learn through:
- family;
- informal community teaching;
- apprenticeships;
- schools/academies once institutions support them;
- religious institutions;
- Society training;
- books/records if literacy/access exists;
- self-directed experimentation;
- peers.

Do not assume universal school attendance or literacy.

Education affects known opportunities as much as raw capability. A capable child who never learns that a profession or magical path exists cannot simply choose it from an omniscient career menu.

## 14. Work and childhood responsibility

Historical/material conditions may require children or adolescents to contribute labor. This should arise from household economy/culture rather than a universal modern childhood assumption.

Consequences can include:
- skill acquisition;
- reduced formal learning time;
- household obligation;
- pride/competence;
- resentment;
- injury/risk;
- relationships with coworkers/kin;
- early knowledge of trades;
- altered goals.

Do not automatically treat work as either beneficial or harmful; simulate conditions and consequences.

## 15. Magic during development

Magic must obey the same rule as every other opportunity:

`preference + knowledge + access + resources + teachers/relationships + circumstance + luck -> actual path`

A child may:
- grow up surrounded by magic but dislike the expected path;
- desperately want magic but lack essence/stone access;
- inherit family contacts that make acquisition easier;
- encounter an unusual opportunity absent from family tradition;
- imitate a magical parent;
- reject magic because of a formative event;
- discover after commitment that available essences do not match the imagined identity.

No `family_magic_class` should force a build.

The canonical complete-path/rank rules remain untouched.

## 16. Formative events

A formative event is not a special event type. It is an ordinary objective event that becomes developmentally influential because of:
- developmental timing;
- personal consequence;
- emotional intensity;
- repetition;
- relationship involvement;
- novelty;
- later reinforcement/reinterpretation.

Potential examples include:
- caregiver death;
- sibling birth/death;
- migration;
- disaster;
- public humiliation;
- first major success;
- betrayal;
- rescue;
- violence witnessed;
- magical awakening/access;
- apprenticeship acceptance/rejection;
- institutional recognition;
- poverty/wealth transition;
- war;
- religious experience where canon permits an objective event or mortal interpretation.

The historian can later call something formative. The event itself does not carry `formative=True` as destiny.

## 17. Trauma-like persistence without diagnostic labels

ATE can model long-lasting effects of frightening/harmful events without assigning modern clinical diagnoses as universal simulation truth.

Persistent effects can emerge through:
- high-salience memories;
- fear/avoidance drives;
- changed trust assessments;
- changed safety expectations;
- self-concept;
- recurring triggers/associations;
- relationship changes;
- altered goals;
- habituation/recovery through later safe experience.

Recovery is possible and causal. Persistence is possible and causal. Neither is guaranteed by a single event flag.

## 18. Rebellion, conformity and generational change

Generational change emerges when younger people experience a world different from the one that formed their elders.

Drivers include:
- changed scarcity/prosperity;
- new technology/knowledge;
- migration;
- war/peace;
- different institutions;
- different magic access;
- demographic change;
- perceived hypocrisy;
- peer networks;
- new records/evidence challenging inherited narratives;
- long-lived elders retaining older norms.

A child rejecting a parent's value should have a reason. A child preserving it should also have a reason.

Long-lived Gold/Diamond people create especially interesting generational pressure because living witnesses to old eras may coexist with descendants formed under radically different conditions.

## 19. Developmental update semantics

When Stage 2 eventually implements this model, developmental changes should be evidence-backed and sparse.

A consequential exposure may affect:
- relationship assessment;
- belief confidence;
- memory salience;
- self-concept;
- value commitment;
- active drive;
- known opportunity;
- goal generation;
- modest temperament expression/development where age permits.

It should not rewrite the whole psyche.

### Repetition
Repeated low-intensity experience can matter without storing every occurrence forever. Aggregate exposure summaries may be used as bounded causal state where they preserve source/domain/time window and cannot be mistaken for objective moral labels.

Examples:
- caregiver reliability exposure;
- repeated peer exclusion;
- repeated craft success;
- repeated food insecurity;
- repeated institutional praise.

## 20. Performance model

Do not simulate every childhood minute.

Use the three-speed model:

### Background
Cheap developmental aging and bounded accumulated exposures.

### Active
People in important developmental transitions or active education/relationship situations receive somewhat richer periodic updates.

### Event reaction
Consequential events produce targeted developmental reactions only for people who actually experienced/learned of them.

Performance rules:
- no child x all-adults relationship scans;
- use household, settlement, school/apprenticeship and social indexes;
- no child x event-history scans;
- retain bounded exposure summaries and significant memories;
- cohort/background aggregation is acceptable for mundane repeated interactions if individual causal distinctions remain available when needed.

## 21. Developmental acceptance scenarios

1. Two siblings raised together become different adults for inspectable reasons without independent adult-personality rerolls.
2. A biological child raised by other caregivers is shaped primarily by actual caregiving relationships while retaining plausible temperament heredity.
3. A wealthy child can become security-obsessed after a later collapse; wealth itself does not guarantee entitlement or generosity.
4. A poor child can value wealth strongly, reject material ambition, or prioritize community depending on history.
5. An older sibling becomes protective because they actually cared for younger siblings—not because firstborns receive a protection bonus.
6. A younger sibling can become more skilled than an older one through different teacher/access/opportunity history.
7. A family grievance can cross generations through transmitted claims even when descendants never witnessed the original event.
8. New evidence can cause a descendant to reject or revise that grievance.
9. A child can reject a prestigious family magical tradition despite having access.
10. A child can desire that tradition but fail to obtain a complete path because resources/opportunity do not cooperate.
11. A mentor can materially change a student's goals/self-concept while existing skill/knowledge systems remain the authority for what was actually taught.
12. A childhood friend can influence values/beliefs without being a scripted companion archetype.
13. Migration during childhood can produce mixed cultural exposure rather than instantly replacing one culture tag with another.
14. A traumatic event can have lasting effects, fade, or be reinterpreted depending on subsequent history.
15. Adolescence can pass without rebellion.
16. A long-lived parent can become culturally alien to descendants without either side being marked objectively right/wrong.
17. An ordinary stable childhood can produce an ordinary stable adult without requiring a formative crisis.
18. Removing birth-order/class/culture summary labels does not erase the causal history that produced the person.

## 22. Open design questions

Not yet frozen:
- species-specific developmental ages/lifespans;
- exact temperament heredity formula;
- exact attachment-generalization mechanics;
- how much pre-explicit-memory experience is retained as exposure summaries;
- education/literacy architecture before Stage 4 institutional schools;
- childhood labor norms by emergent culture/economy;
- how capability development and Psyche development exchange feedback;
- how magical rank/longevity changes developmental expectations for descendants;
- non-human family structures;
- whether some magical effects can alter memory/personality directly under future canon.

Coding agents must not invent these answers.

## 23. Implementation sequencing

This document does **not** move human development ahead of the roadmap.

1. Finish Stage 0.5 currency/magic-access/completion stabilization.
2. Freeze the pre-subjective-architecture gold baseline.
3. Implement Stage 1 Observation/Memory/Psyche/directional-social/Agency contracts.
4. Only then implement this model as Stage 2 by extending existing genealogy/household/social/skill/knowledge/culture systems.

Until then, this is design authority for future work, not an implementation task.
