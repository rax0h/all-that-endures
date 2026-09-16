# ATE Health, Disease, Aging & Reproduction Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze.  
**Purpose:** define ordinary bodily life—health, illness, disease, aging, recovery, disability, reproduction, pregnancy, birth and natural death—as one causal biological architecture integrated with existing species/rank biology, environment, material life, Psyche, development and the combat injury model.

## North star

A body is not a health bar and aging is not an annual death roll.

ATE should support lives in which people are usually healthy enough to live ordinary days, sometimes become ill, recover imperfectly or completely, age according to their biology and rank, reproduce under actual circumstances, and eventually die for a cause the simulation can explain.

The causal spine is:

`biology + age + prior health + environment + nutrition/rest + exposure + injury + care -> bodily state -> symptoms/function -> behavior/care access -> progression/recovery -> lasting consequence or return toward baseline`

> **Health is the changing condition of a body through time, not a probability attached to a person once per year.**

## 1. Existing authorities to preserve

### `biology.py`
Current `BiologyState` already composes species/rank into stature, mass, food/spirit/sleep/respiration needs, endurance, strength, environmental tolerances, perception, magical affinity/body and related capability.

It also currently provides:
- mortality risk;
- reproductive window;
- pair reproductive opportunity;
- child species inheritance;
- combat value;
- injury resilience.

This remains the natural home for derived biological capability/profile access, not a place to duplicate persistent disease history.

### `rank.py`
Current `RankProfile` already defines provisional mechanical effects including:
- aging rate;
- adult mortality;
- senescence start;
- disease resistance;
- healing;
- injury resilience;
- physical/cognitive capacity.

These are useful existing rank-biological authorities. Exact values remain calibration/canon concerns.

### Person health
Current Person state contains a compact `health` value used by existing systems.

During migration, this remains a compatibility projection. It should eventually summarize authoritative bodily conditions/function rather than remain the sole cause of illness, injury and mortality.

### Combat injury
`CONFLICT_COMBAT_INJURY_HEALING_MODEL.md` owns traumatic injury semantics: severity, immediate lethality, viability window, stabilization, healing and recovery after violence/accident.

This health model must share bodily state with injury rather than create parallel combat-health and ordinary-health universes.

## 2. Authority boundary

Future persistent health state should own:
- current illnesses/conditions;
- physiological stress/depletion where materially relevant;
- pregnancy/reproductive state;
- recovery state;
- lasting impairments;
- bodily function consequences;
- scheduled progression/recovery.

It should **not** own:
- objective environmental contamination/vector state;
- food inventories;
- Psyche/emotions;
- social caregiving relationships;
- healer knowledge;
- magical ability definitions;
- traumatic event history;
- species/rank rules.

Those remain external causes/capabilities referenced by health.

## 3. Ordinary health should usually be quiet

Most healthy people should not generate health events every year.

A healthy baseline can persist implicitly until something changes:
- aging threshold/slow decline;
- exposure;
- pregnancy;
- injury;
- malnutrition/dehydration;
- sleep deprivation;
- disease;
- chronic condition progression;
- treatment;
- recovery.

This is essential both for realism and millennium performance.

## 4. Health dimensions

Do not reduce all bodily condition to one number.

Useful authoritative dimensions may include only what systems need, such as:
- general physiological reserve;
- mobility;
- strength/endurance impairment;
- consciousness/neurological function;
- respiration;
- circulation;
- hydration/nutrition;
- infection burden;
- pain;
- reproductive state;
- organ/system impairment where consequential.

Exact schema remains open. A compact model is preferred over medical-simulation excess.

## 5. Health summary

A scalar `health` may remain useful as a **derived compatibility/capability projection** for legacy code.

It must not erase cause.

Two people at `health=.6` might differ because one has pneumonia and the other is recovering from a broken leg. Their risks, capabilities, treatment and future trajectories differ.

## 6. Symptoms versus disease

Symptoms are experienced/observable manifestations. Disease/condition is the underlying bodily process where objectively resolved.

People may observe:
- fever;
- cough;
- pain;
- weakness;
- rash;
- vomiting/diarrhea;
- bleeding;
- confusion;
- shortness of breath;
- swelling;
- fatigue.

They need not know the true cause.

The simulation can know an infection exists while the person/healer believes the wrong diagnosis.

## 7. Disease representation

A disease/illness process may specify:
- cause/pathogen/category;
- incubation/latent period;
- transmissibility route where applicable;
- severity distribution;
- affected systems/symptoms;
- progression timeline;
- mortality/complication mechanisms;
- immunity/resistance effects;
- treatment responsiveness;
- recovery/immunity state where applicable.

Do not simulate molecular biology unless it creates gameplay/history consequences.

## 8. Exposure is not infection

Causal chain:

`source/environment -> exposure opportunity -> dose/contact + susceptibility -> infection/condition -> progression`

Not every exposure causes disease.

Environment owns vector habitat/contaminated water/seasonal suitability. Social/material systems own contact/co-residence/travel. Health resolves whether exposure becomes bodily disease.

## 9. Transmission routes

Disease may spread through routes such as:
- close respiratory contact;
- contaminated food/water;
- bodily-fluid/contact;
- vector;
- animal reservoir;
- wound contamination;
- environmental exposure.

Exact route taxonomy can remain compact.

Transmission should use actual contact/location/household/travel networks rather than all-person pairs.

## 10. Contagiousness through time

A disease can have stages with different transmission risk:
- incubation;
- presymptomatic where applicable;
- symptomatic infectious;
- recovering but infectious;
- resolved.

This allows quarantine/isolation and delayed recognition to matter without daily global simulation.

## 11. Immunity and resistance

Distinguish:
- species/rank disease resistance;
- prior acquired immunity;
- temporary protection;
- treatment/prevention;
- general physiological vulnerability.

Resistance changes probability/severity; it does not make disease impossible unless canon explicitly says so.

Rank profiles already contain disease resistance and should remain authoritative inputs.

## 12. Epidemics

An epidemic is an emergent pattern of many linked infections, not a special story event that simply subtracts population.

Spread depends on:
- infectious carriers;
- contact networks;
- settlement density/crowding;
- travel/trade;
- sanitation/water;
- season/environment;
- immunity;
- behavior/institutions;
- healer/public-health knowledge.

Background epidemics must use aggregate/cohort transmission where possible rather than simulate every contact.

## 13. Disease information

People respond to what they observe/believe.

They may:
- correctly recognize contagion;
- attribute illness to weather, spirits, food, enemies or other causes;
- isolate;
- seek healer;
- continue working;
- flee;
- hide symptoms;
- spread false cures;
- discover useful practices empirically without correct theory.

Health never writes beliefs directly. Symptoms/evidence create Observations; Information/Psyche/Agency determine response.

## 14. Public health

Collective disease response may emerge through institutions/practices:
- clean water;
- sanitation;
- waste handling;
- isolation/quarantine;
- burial/body handling;
- food inspection;
- healer networks;
- hospitals/clinics where institutions support them;
- vaccination/prevention if world knowledge eventually develops it.

These require knowledge, resources, authority and compliance.

No civilization-wide `medicine_level` automatically reduces disease.

## 15. Nutrition

Nutrition depends on actual accessible food and bodily need.

Short-term shortage may create hunger/fatigue. Sustained deficiency can reduce:
- physiological reserve;
- growth/development;
- fertility;
- immune resilience;
- work/combat capability;
- recovery/healing.

Exact nutrient simulation is unnecessary unless specific deficiencies become important. Aggregate adequacy/diversity can suffice.

Rank/species food needs come from biology.

## 16. Hydration

Water need and dehydration can matter during:
- drought;
- travel;
- illness;
- heat;
- siege;
- environmental exposure.

Background normal hydration should remain implicit where clean water access is adequate.

## 17. Sleep and rest

Species/rank biology already includes sleep need.

Acute sleep deprivation can impair:
- attention;
- physical performance;
- emotional regulation;
- recovery.

Do not run nightly sleep simulation for every person over a millennium. Track meaningful deprivation when circumstances actually prevent sufficient rest.

## 18. Environmental stress

Heat, cold, altitude/respiration, water exposure and other environmental conditions can exceed biological tolerance.

Environment supplies exposure; biology supplies tolerance; health resolves bodily consequences.

Ordinary compatible climate should not generate continuous health calculations.

## 19. Aging

Aging is gradual biological change shaped by species and rank.

Current `aging_rate` and `senescence_start` are existing provisional authority.

Aging may change:
- physiological reserve;
- recovery speed;
- fertility;
- sensory function;
- mobility/strength;
- disease vulnerability;
- mortality from age-related failure.

Not every dimension must decline identically or every year.

## 20. Biological versus chronological age

Chronological age records elapsed years lived.

Biological aging reflects species/rank body progression.

Long-lived ranked people may be centuries old chronologically without corresponding ordinary senescence.

This does not make them psychologically frozen. Psyche, memory, relationships and culture continue through chronological experience.

## 21. Senescence

Senescence should create increasing vulnerability/functional decline, not an arbitrary maximum-age execution.

Possible outcomes:
- gradual decline;
- age-related chronic conditions;
- reduced recovery;
- increased infection vulnerability;
- natural organ/system failure.

Individuals vary stochastically within species/rank constraints.

## 22. Natural death

Natural death should eventually be attributable to a bodily failure/process rather than `annual_mortality_roll_failed` as the final historical explanation.

Legacy annual mortality can remain through baseline and early migration, but final architecture should use it as a hazard scheduler/candidate generator if retained—not the semantic cause of death.

Examples:
- age-related systemic failure;
- acute infection;
- chronic organ failure;
- stroke-like/vascular event where modeled;
- pregnancy complication;
- malnutrition;
- untreated injury.

Exact diagnostic naming can remain abstract enough for the setting.

## 23. Longevity and rank

Rank materially changes aging, disease resistance, healing and injury resilience according to canonical biology.

It does not guarantee immortality unless the rank profile/canon explicitly does.

Gold/Diamond rules must remain consistent with established longevity expectations. Do not casually kill high ranks through ordinary-age hazards calibrated for ordinary humans.

Conversely, longevity is not invulnerability to catastrophic injury, rare disease or other canon-supported causes.

## 24. Chronic conditions

Some conditions persist for years/life.

They may affect:
- mobility;
- endurance;
- pain;
- work;
- sleep;
- fertility;
- treatment needs;
- dependency;
- goals/relationships.

Chronic condition state should update only when progression/treatment/relevant events occur, not every tick.

## 25. Disability and impairment

Disability is the interaction between bodily impairment and actual environment/social/material demands, not a personality trait.

A mobility impairment may matter very differently depending on:
- occupation;
- infrastructure/accessibility;
- wealth;
- household support;
- available magic/technology;
- social norms;
- transportation.

No universal `disabled -> unhappy` rule.

## 26. Pain

Pain can affect current capability/Agency attention without becoming personality.

Persistent pain may create memories, goals, frustration or changed behavior through Psyche only when experienced/interpreted.

Pain should not require continuous numerical ticking if condition state can derive it.

## 27. Recovery

Recovery is a process toward a new or prior baseline.

It depends on:
- condition/injury;
- biology/rank healing;
- nutrition/rest;
- treatment;
- reinjury/exposure;
- age;
- complications.

Recovery may be complete, partial or fail.

Use scheduled milestones/analytic elapsed-time progression rather than daily healing loops for background people.

## 28. Medical/healing care

Care is delivered by actual people/institutions with knowledge, skills, tools, resources and access.

A healer can:
- observe symptoms;
- form possibly wrong beliefs;
- attempt treatment;
- stabilize;
- prescribe practices;
- use mundane/magical capability;
- refer/seek help where institutions permit.

Treatment outcome is resolved against the actual condition while healer choice is based on subjective information.

## 29. Treatment can be ineffective or harmful

A sincere healer can be wrong.

Treatment may:
- help;
- do nothing;
- delay better care;
- cause side effects/injury;
- worsen disease;
- appear to work because natural recovery occurs.

This allows medical knowledge to improve historically through evidence/transmission rather than granting healers simulator truth.

## 30. Magical healing boundary

Magical healing obeys explicit ability semantics and existing rank/magic rules.

It does not automatically:
- cure every infection;
- reverse aging;
- restore missing tissue;
- eliminate chronic conditions;
- guarantee pregnancy survival;
- resurrect the dead.

Those effects require explicit canonical abilities/cosmology.

Rank profile `healing` may affect natural bodily recovery without implying an active healing spell.

## 31. Reproduction is bodily and social

Reproduction requires biological compatibility/opportunity **and** actual social/behavioral circumstances.

Biology owns:
- reproductive capability/window;
- species compatibility;
- fertility potential;
- pregnancy physiology;
- child species inheritance.

Relationships/Psyche/Agency/culture own:
- partnership/intimacy behavior;
- desire/avoidance;
- household formation;
- contraception/fertility practices if known;
- caregiving expectations.

Do not turn every compatible pair into a reproductive roll.

## 32. Reproductive windows

Current `biology.reproductive_window()` is a simple compatibility rule based on adulthood + species reproductive span.

Future architecture may refine onset/decline by species/rank/sex/reproductive biology, but must preserve the principle that lifetime fertility emerges from actual survived opportunities rather than pre-discounting long-lived species.

Exact reproductive-age rules remain open until audited against species canon.

## 33. Fertility

Fertility is probability/capability under actual reproductive opportunity, not desire for children.

It may depend on:
- species;
- age/biological age;
- rank/canon;
- health;
- nutrition;
- pregnancy/postpartum state;
- condition-specific effects.

Infertility/subfertility can exist without being globally visible to characters.

## 34. Conception

Conception occurs only after an actual reproductive opportunity established by social/behavioral simulation.

Health resolves biological probability using fertility/compatibility/current bodily state.

Do not scan all compatible pairs annually.

## 35. Pregnancy

Pregnancy is persistent timed bodily state.

It should track only causally useful dimensions:
- gestational progress;
- parent health/risk;
- fetal/multiple state where needed;
- complications;
- nutrition/exposure effects;
- expected delivery window.

Routine healthy pregnancy should advance mostly by scheduled milestones, not daily simulation.

## 36. Pregnancy effects

Pregnancy may change:
- nutrition/rest needs;
- physical capacity;
- vulnerability to certain conditions;
- work/travel choices;
- household planning;
- care needs.

Psyche/social effects are not automatic. Different people interpret pregnancy differently.

## 37. Pregnancy loss

Pregnancy loss can occur from biological complication, disease, severe deprivation, injury or other canon-supported causes.

It should not be injected for drama.

If it occurs, objective bodily event is separate from who knows, how it is interpreted and its psychological/social consequences.

## 38. Birth

Birth is a timed health event with outcomes for parent and child.

Factors may include:
- species biology;
- parent health/nutrition;
- complications;
- skilled assistance;
- sanitation;
- environment;
- magical care where applicable;
- multiple birth;
- access/timing.

Birth should create an actual child identity/genealogy/household consequence only after successful live birth.

## 39. Maternal/gestational mortality and complications

Birth/pregnancy can be dangerous where world biology/medicine supports it, but risk must be calibrated—not used as generic medieval-grimness seasoning.

Rank disease resistance/healing/resilience and available care may materially alter outcomes.

The system must avoid unrealistic population collapse from over-aggressive reproductive mortality.

## 40. Newborn and infant health

Infants have age-specific vulnerability/needs.

Relevant causes may include:
- birth complications;
- feeding/nutrition;
- infection;
- temperature/environment;
- caregiving access;
- species biology.

Do not simulate constant infant crises. Healthy infants can remain healthy implicitly while Development models caregiving/exposure.

## 41. Childhood growth

Physical growth belongs to biology/health and should coordinate with Human Development.

Growth can depend on:
- species trajectory;
- age;
- nutrition;
- chronic disease;
- severe deprivation.

Psychological development remains in the Human Development/Psyche architecture.

## 42. Puberty/adult maturation

Physical maturation may change reproductive capability/body state while developmental/social consequences belong elsewhere.

No automatic personality change from puberty.

Exact species maturation schedules remain open.

## 43. Postpartum/recovery

Birth can require bodily recovery and may affect fertility/energy for a period.

Caregiving burden belongs to household/development/social systems. Health owns only bodily recovery/condition.

## 44. Family planning

Where knowledge/culture/resources support it, people may attempt to influence reproduction.

Methods can vary in effectiveness and require actual knowledge/access.

No universal modern contraception assumption and no forced universal pronatalism.

## 45. Population consequences

Demography should emerge from:
- births;
- deaths;
- migration;
- species/rank longevity;
- reproductive opportunity;
- health/nutrition;
- war/disaster/disease.

Do not tune population through invisible corrective fertility/death events unless explicitly documented as calibration machinery and causally represented.

## 46. Death certification versus truth

Objective health system may know physiological cause of death.

Characters/institutions may record a different cause based on evidence/medical knowledge.

This supports mistaken historical diagnoses and later reinterpretation.

## 47. Bodies after death

Death creates a body/remains state where materially relevant.

Bodies can matter for:
- discovery/evidence;
- burial/ritual;
- disease exposure where appropriate;
- investigation;
- archaeology;
- resurrection rules later.

Exact corpse/remains representation should reuse material/location/provenance concepts without turning every dead body into an expensive permanent active agent.

## 48. Health and Psyche

Health affects Psyche through experienced consequences, not direct personality rewrites.

Examples:
- chronic illness may constrain goals;
- near-death may become salient memory;
- infertility may matter deeply to one person and little to another;
- aging may change self-concept depending on values/culture;
- pain may increase immediate irritability/avoidance without permanently increasing aggression.

Psyche owns interpretation.

## 49. Health and relationships

Caregiving, abandonment, contagion, medical help and dependency create objective interactions/observations that can alter relationships.

No automatic `nursed_me -> +trust` rule. The recipient must know/interpret what happened.

## 50. Health and economy

Illness can affect:
- labor availability;
- household consumption/care burden;
- healer demand;
- medical resource use;
- travel/trade;
- debt;
- institutional capacity.

Economy resolves material consequences. Health supplies bodily capability/needs.

## 51. Health and institutions

Institutions may support:
- healers;
- hospitals/clinics;
- sanitation;
- quarantine;
- disability support;
- burial;
- research/records.

Institution existence does not guarantee access or competence.

## 52. Health and environment

Environment supplies:
- heat/cold exposure;
- contaminated water;
- vector pressure;
- toxins/pollution;
- food production constraints;
- disaster injury opportunities.

Health resolves bodily effect using actual biology.

## 53. Health and conflict

Combat/accident injury uses the shared bodily model.

Health owns ongoing deterioration/recovery; combat owns how traumatic injury was caused/resolved during encounter.

A wound should not exist simultaneously as unrelated combat HP loss and separate health condition.

## 54. Accidents

Non-combat injury may occur through:
- work;
- construction;
- travel;
- falls;
- fire;
- animals;
- environmental hazards.

Use the same injury/health semantics where possible.

Accident risk should arise from actual activity/hazard, not annual random injury rolls for every person.

## 55. Aging and occupation

Aging can alter capability and therefore economic/social choices, but does not force retirement.

People may:
- continue work;
- reduce workload;
- teach/mentor;
- change occupation;
- depend on family/institutions;
- remain highly capable due rank/species.

Agency/institutions determine response to capability changes.

## 56. Long-lived societies

Long-lived ranked people create unusual health/demographic realities:
- living multi-century relatives;
- very long caregiver/mentor horizons;
- long reproductive windows where species/canon supports them;
- different age structures;
- accumulated chronic injuries/conditions;
- centuries of medical knowledge exposure.

Do not apply ordinary-human age categories blindly to ranked longevity.

## 57. Performance architecture

### Event-driven health
Only active conditions/pregnancies/recoveries need scheduled updates.

### Lazy aging
Biological age/function derived from chronological age + species/rank profile when queried or at sparse life-stage thresholds.

### Cohort disease
Background epidemics use settlement/household/contact cohorts and instantiate individual cases where consequences require it.

### Sparse exposure
Use household/workplace/school/travel/settlement/environment indexes; no all-pairs infection scans.

### Analytic recovery
Compute condition progression from elapsed time where deterministic/simple rather than daily ticks.

### Dormant healthy people
No yearly health update merely to confirm continued health.

### Bounded condition history
Resolved mundane illnesses can collapse into summary history unless medically/socially/historically consequential.

### Scheduled pregnancy
Milestones/delivery event rather than hundreds of gestational ticks.

## 58. Performance contract

Health/disease/reproduction implementation must not materially compromise the frozen millennium baseline.

Every structural PR eventually reports deterministic 100/500/1,000-year runtime and active-condition/event counts.

A disease system that requires touching every person every day is architecturally rejected even if medically detailed.

## 59. Determinism

Stochastic health resolution uses isolated namespaced RNG after causal eligibility/exposure exists.

Potential namespaces:
- `infection_acquisition`;
- `disease_course`;
- `health_complication`;
- `conception`;
- `pregnancy_course`;
- `birth_outcome`;
- `age_hazard`.

Exact namespaces freeze during implementation.

## 60. Diagnostics

Millennium diagnostics should include:
- births/deaths by cause category;
- age/rank/species structure;
- life expectancy distributions by relevant cohort;
- pregnancy/live-birth/loss counts;
- active/recovered disease burden;
- major outbreaks;
- nutrition-related morbidity/mortality;
- chronic impairment prevalence;
- healer/care access where modeled;
- health contribution to labor/migration;
- health runtime share;
- active health-state/event counts.

Diagnostics are read-only.

## 61. Behavioral acceptance scenarios

1. Healthy person can pass decades without generating annual health events.
2. Same pathogen exposure infects one person and not another due biology/immunity without arbitrary narrative choice.
3. Infection spreads through actual household/contact/travel networks rather than all-person proximity magic.
4. Disease can spread before people correctly understand its cause.
5. Institution can reduce outbreak through sanitation/isolation only if knowledge/resources/compliance exist.
6. False medical theory can coexist with an empirically useful treatment.
7. Healer can sincerely misdiagnose and give ineffective/harmful care.
8. Ranked disease resistance reduces ordinary disease burden without granting undefined immunity.
9. Long-lived Gold/Diamond does not die from ordinary-human senescence schedule.
10. Aging gradually changes vulnerability/function without arbitrary maximum-age death.
11. Natural death has a bodily causal process, not merely a failed annual mortality roll.
12. Chronic condition persists sparsely for years without yearly full-state processing.
13. Mobility impairment affects a laborer differently from a wealthy administrator because environment/occupation differ.
14. Food shortage reduces health only through actual inadequate access/consumption.
15. Clean water infrastructure reduces waterborne exposure without directly changing disease truth.
16. Reproduction occurs only after actual social/behavioral opportunity, never from all-compatible-pair scanning.
17. Two compatible couples can have different fertility histories due age, health, opportunity and chance.
18. Healthy pregnancy advances mostly through scheduled milestones.
19. Pregnancy complication can be survivable with timely skilled care and fatal when care is unavailable, without scripted tragedy.
20. Birth creates genealogy/person state only after resolved live birth.
21. Infant health depends on caregiving/material/environmental exposure while psychological development remains separate.
22. Combat wound and ordinary health share one ongoing recovery state rather than duplicate HP/condition histories.
23. A healer existing nearby does nothing for an unconscious isolated patient until someone discovers/reaches them.
24. Death cause known to simulator can be misrecorded by historical people/institutions.
25. Long-lived population remains demographically viable without artificial extinction pressure from pre-discounted future fertility.
26. Health integration remains deterministic and within bounded marginal millennium runtime.

## 62. Open design questions

Not yet frozen:
- exact persistent body/health schema;
- disease/pathogen taxonomy and content scope;
- immunity duration/representation;
- epidemic cohort algorithm;
- nutrition detail;
- sanitation representation;
- age-related condition categories;
- exact natural-death hazard-to-cause conversion;
- species-specific maturation/reproductive schedules;
- sex/reproductive biology representation;
- fertility/pregnancy calibration;
- multiple births;
- infant mortality calibration;
- medical skill/knowledge specialization;
- mundane treatment item/process representation;
- hospital/clinic architecture;
- corpse/remains persistence;
- permanent impairment schema shared with combat;
- magical healing/resurrection effects pending explicit canon.

Coding agents must not invent these answers merely to finish an interface.

## 63. Integration sequencing

1. Stage 0.5: freeze current baseline first.
2. Stage 1: Observation/Belief/Memory/Psyche/Agency foundation.
3. Stage 2: Human Development + relationship/social architecture; audit current reproduction against social opportunity semantics.
4. Health A: shared persistent bodily-condition/recovery schema + derived legacy `health` projection.
5. Health B: lazy aging/senescence/natural-death causes calibrated against current species/rank longevity.
6. Health C: nutrition/environment exposure interfaces.
7. Health D: disease/exposure/immunity + cohort outbreak model.
8. Health E: care/treatment/healer/institution integration.
9. Health F: reproduction/conception/pregnancy/birth/infant-health migration from current compatibility rules.
10. Stage 6 combat: traumatic injury plugs into the same bodily-condition/recovery authority.
11. After every structural step: deterministic 100/500/1,000-year benchmark and demographic calibration.
12. Resurrection/reversal of death remains blocked until cosmology/magic canon is authored.

Until the relevant implementation stage opens, this document is design authority—not permission to code ahead.

**Health principle:** bodies change because something happened to them, survive because their biology and circumstances allowed it, and die for causes that remain part of history.
