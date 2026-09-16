# ATE Conflict, Combat, Injury, Healing & War Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze and prerequisite Psyche, Information, Relationship and Institution architecture.  
**Purpose:** define one causal model spanning interpersonal conflict, temporal combat, injury, rescue, healing, assassination, monsters, battles and long wars without reducing violence to rank arithmetic or injecting dramatic outcomes.

## North star

Violence is an event in time, not a comparison of two combat ratings.

The causal chain is:

`pressure/conflict -> decision to engage/avoid -> positioning + preparation + capability + environment -> temporal actions -> wounds/exhaustion/control -> escape/surrender/incapacitation/death -> rescue/healing -> social/institutional consequences`

Rank matters enormously. It is not a narrative veto.

> **Power determines the shape of possibility. Circumstance determines which possibility becomes real.**

## 1. Existing authorities to extend

ATE already has:
- `warfare.py` for macro annual conflict, tensions, battles, casualties, war score and peace;
- advancement/rank/ability state;
- Agency for attempted choices;
- threat ecology;
- relationships and social conflict foundations;
- economy/materials/inventory/provenance;
- institutions/Society accountability;
- objective Events/causal refs.

Future temporal combat/injury must integrate with these. Do not create a second war-history authority or replace macro warfare with millions of fully simulated duels.

## 2. Conflict is broader than combat

Conflict can arise from:
- scarcity;
- property/debt;
- humiliation;
- romance/family;
- inheritance;
- rivalry;
- ideology/religion;
- institutional authority;
- class/dependency;
- revenge;
- fear;
- discrimination/exclusion;
- territory;
- trade;
- magical resources;
- crime;
- monsters/threats;
- war.

Most conflict should not become lethal violence.

## 3. Escalation

Possible escalation:

`avoidance -> disagreement -> argument -> restitution/mediation -> gossip/social retaliation -> economic retaliation -> threats -> sabotage -> assault -> attempted killing -> organized retaliation -> open conflict`

This is not a mandatory ladder. Urgency, aggression, fear, norms, power and immediate danger can skip stages.

De-escalation is equally causal:
- apology;
- restitution;
- mediation;
- fear of consequences;
- affection;
- shared interests;
- exhaustion;
- surrender;
- separation;
- new evidence;
- institutional intervention.

## 4. Intent and objectives

Combatants do not all enter violence with `kill` as objective.

Possible objectives:
- escape;
- intimidate;
- restrain;
- arrest;
- protect another;
- steal/recover object;
- force retreat;
- incapacitate;
- capture;
- delay;
- hold position;
- break through;
- survive;
- kill.

Objective affects tactics, acceptable risk and stopping conditions.

A lethal outcome can occur even when nobody intended death.

## 5. Combat is temporal

Meaningful combat resolves through a bounded sequence of exchanges/windows, not a single strength roll.

State may include:
- participants;
- location/terrain;
- distance/position;
- awareness/surprise;
- current objective;
- wounds;
- stamina/endurance;
- available abilities/equipment;
- allies;
- escape routes;
- environmental hazards;
- time elapsed;
- reinforcements/rescue arrival;
- morale/willingness to continue.

The simulation need not model every sword swing. It must preserve enough temporal structure that timing can cause outcomes.

## 6. Rank disparity

Rank is a major physical/magical asymmetry.

Direct healthy confrontation across ranks should strongly favor the higher-ranked combatant. An Iron should almost always lose a straightforward fight against a healthy Silver.

But **almost always is not never**.

Lower-rank success requires extraordinary causal advantage such as combinations of:
- surprise;
- preparation;
- terrain;
- traps;
- superior numbers;
- specialized counter-capability;
- target already wounded/exhausted;
- objective short of defeating target directly;
- environmental catastrophe;
- allies/reinforcements;
- target mistakes/constraints;
- rare but legitimate stochastic outcome.

Never inject an upset because it would be dramatic.

## 7. Within-rank mastery

The four-stage mastery projection can affect relative capability within a rank without changing canonical advancement pacing.

Skill-level rank/stage/progress may inform execution, control, efficiency or access to practiced ability performance as existing canon permits.

Do not convert mastery stage into a separate combat level or change XP/rank timing.

## 8. Capability is multidimensional

Combat capability can depend on:
- rank;
- relevant abilities/skills;
- mastery;
- species/embodiment;
- health;
- injury;
- endurance;
- equipment;
- training;
- tactical knowledge;
- coordination;
- environment;
- information;
- preparation.

No single combat-power score should become final causal truth. Derived estimates are acceptable for fast resolution/diagnostics if components remain authoritative.

## 9. Knowledge and combat

Combatants act on what they know/believe.

They may misjudge:
- opponent rank;
- abilities;
- numbers;
- terrain;
- allies;
- wounds;
- intentions;
- traps.

A person cannot counter an ability they have no reason to anticipate merely because the simulator knows it exists.

Reputation can cause avoidance or overconfidence without changing actual capability.

## 10. Preparation

Preparation can materially change odds:
- scouting;
- equipment;
- chosen terrain;
- fortification;
- ambush;
- healing supplies;
- allies;
- escape planning;
- countermeasures;
- rest;
- intelligence.

Preparation consumes time/resources and can be discovered.

This gives weaker actors meaningful strategic agency without flattening rank differences.

## 11. Surprise and initiative

Surprise is an information/position advantage, not a free critical-hit token.

It can create one or more early action windows before the target responds effectively.

Magnitude depends on:
- concealment;
- awareness;
- distance;
- attacker preparation;
- target vigilance;
- environment;
- speed/reaction capability.

Higher-rank resilience/reaction may reduce consequences without making surprise meaningless.

## 12. Position and terrain

Environment matters when it changes available actions/consequences:
- elevation;
- cover;
- choke points;
- water;
- unstable ground;
- buildings;
- fire;
- weather;
- darkness;
- crowding;
- cliffs;
- magical/environmental hazards.

Do not add terrain modifiers everywhere for flavor. Use terrain when causally relevant.

## 13. Groups and coordination

Numbers matter through action economy, coverage, fatigue, distraction and control—not a flat `+10% per ally`.

Group effectiveness depends on:
- communication;
- training;
- trust;
- command;
- formation/space;
- objectives;
- morale;
- capability mix.

A crowd of ordinary people should not automatically defeat a Diamond because population arithmetic says so. Conversely, enough coordinated capability, preparation or environmental leverage can matter where physically plausible under canon.

## 14. Wounds are state, not hit-point subtraction alone

Injury should represent meaningful bodily harm.

A wound can have:
- location/type;
- severity;
- bleeding/ongoing damage;
- pain;
- impairment;
- immediate lethality;
- survival/viability window;
- infection/complication risk where applicable;
- healing requirements;
- scarring/permanent consequence potential.

A compact implementation may abstract anatomy, but it must preserve these semantic distinctions.

## 15. Separate severity, lethality, viability and healing

These four concepts must not collapse into one health value.

### Damage severity
How much harm occurred.

### Immediate lethality
Whether the injury kills essentially at once.

### Viability/survival window
How long the injured person can remain alive without sufficient intervention/stabilization.

### Healing rate
How quickly tissue/function recovers once survival is secured.

A severe wound can be survivable for an hour but heal over months. Another can look smaller yet kill rapidly through bleeding or organ damage.

## 16. Rank and survivability

Higher rank/resilience may affect:
- tolerance of trauma;
- bleeding/shock resistance;
- consciousness/function after injury;
- survival window;
- natural recovery;
- resistance to infection/toxins where canon supports it.

This is **not automatically healing magic**.

A high-ranked person can remain viable longer without actually closing the wound. This creates meaningful rescue/healer timing.

## 17. Incapacitation

A combatant may become unable/unwilling to continue before death through:
- unconsciousness;
- severe pain;
- structural injury;
- exhaustion;
- restraint;
- fear/surrender;
- magical disabling effects;
- loss of objective.

Combat should often end at incapacitation, retreat or surrender rather than death.

## 18. Death

Death occurs from causal bodily/magical failure, not because combat resolution selected `loser`.

Possible pathways:
- immediate catastrophic injury;
- accumulated trauma;
- bleeding/shock after combat;
- untreated complications;
- environmental exposure;
- poison/disease where modeled;
- execution after capture;
- later failure of treatment.

The death event should reference the causal injury/event chain.

## 19. Rescue

Rescue is a race between viability and access.

Factors:
- whether anyone knows the person is injured;
- distance;
- terrain;
- transport;
- ongoing danger;
- relationship/motive to help;
- available rescuers;
- stabilization knowledge;
- healer availability;
- institutional emergency capacity.

A healer existing in the settlement does nothing if nobody finds the victim in time.

## 20. Stabilization

Stabilization prevents/extends immediate deterioration without necessarily healing the injury.

Examples:
- stopping bleeding;
- splinting;
- airway/support;
- moving from hazard;
- mundane first aid;
- magical stabilization where abilities permit.

This distinction allows ordinary people to save lives even when they cannot perform advanced healing.

## 21. Healing

Healing is performed by actual people/abilities/resources.

A healer must:
- know the patient needs help;
- be able/willing to reach them;
- possess appropriate capability;
- have required resources if any;
- arrive while intervention can still matter.

Healing outcomes depend on injury and capability, not a generic full-health button.

## 22. Magical healing

Magical healing should obey explicit ability semantics.

It may affect one or more of:
- bleeding;
- tissue repair;
- pain;
- infection;
- poison;
- organ damage;
- stabilization;
- recovery time.

Do not assume every healing ability cures every condition. Ability identity/function remains authoritative.

## 23. Recovery

Survival is not instant restoration.

Recovery can include:
- bed rest;
- reduced capability;
- rehabilitation;
- scarring;
- chronic pain/impairment;
- psychological/social consequences;
- lost work/income;
- caregiver burden;
- debt/resources consumed.

Higher rank/magic may shorten recovery, but meaningful wounds can still alter lives.

## 24. Permanent injury

Permanent consequences should arise when damage/healing plausibly leaves lasting impairment.

Do not create disability for drama. Do not erase it merely for convenience.

Permanent injury can affect:
- occupation;
- combat capability;
- goals;
- relationships;
- dependency;
- psyche/self-concept;
- institutional role.

## 25. Assassination

Assassination is planned violence exploiting information and vulnerability.

Success depends on:
- target routine/location knowledge;
- secrecy;
- access;
- surprise;
- attacker capability;
- target rank/resilience;
- guards/allies;
- escape plan;
- weapon/ability suitability;
- evidence left behind.

A low-ranked assassin should not bypass rank simply because the action is tagged `assassination`. But preparation can create circumstances very different from a duel.

## 26. Capture and imprisonment

Capture requires actual control/restraint and continued ability to hold the prisoner.

Ranked prisoners may require appropriate restraints, guards, environment or magical countermeasures where canon supports them.

Imprisonment creates logistical/social/institutional costs and opportunities for:
- escape;
- rescue;
- interrogation;
- trial;
- exchange/ransom;
- recruitment;
- execution.

## 27. Surrender and mercy

Surrender is a decision under perceived expected outcomes.

Factors:
- fear;
- injury;
- objective failure;
- trust in opponent/institution;
- cultural norms;
- expected treatment;
- dependents/obligations;
- self-concept;
- possibility of escape.

Acceptance of surrender is another decision. Mercy is behavior, not a morality stat.

## 28. Monsters and nonhuman threats

Threat ecology should feed the same consequence model where practical.

A monster encounter involves:
- detection/knowledge;
- threat capability;
- terrain;
- objectives/behavior;
- human preparation;
- combat/injury;
- escape/rescue;
- material/economic consequences.

Do not make monsters a separate damage universe if shared combat/injury semantics can apply.

## 29. Adventure Society contracts

Society response to threats should connect:

`notice/evidence -> threat assessment -> contract/assignment -> team preparation -> travel -> encounter -> outcome/evidence -> institutional record/accountability`

Star rank remains trust/judgment/operational responsibility, not magical power.

Contract outcome should evaluate actual objectives/consequences, not hidden designer-approved solutions.

## 30. Crime and violence

Violent crime uses the same combat/injury system as other violence.

Afterward, the information/evidence model determines what anyone knows:
- witnesses;
- wounds;
- bodies;
- weapon/object provenance;
- magical traces where canon supports them;
- statements;
- records.

Combat resolution must not automatically reveal attacker identity to investigators.

## 31. Domestic/interpersonal violence

No special dramatic subsystem. It arises from ordinary relationships, power, fear, conflict and Agency.

The system must distinguish outward household/partnership status from subjective safety/trust/affection.

Institutional/legal/community responses depend on evidence, norms, relationships and enforcement.

## 32. Battles

Large battles cannot run full detailed cognition for every individual exchange.

Use hierarchical resolution:
- strategic/operational state determines forces, objectives, terrain, preparation and broad phases;
- formations/groups resolve aggregate exchanges;
- individual temporal combat expands only for consequential agents/events where needed;
- aggregate casualties instantiate causal injuries/deaths consistent with force capability and battle conditions;
- named/important people are not protected by narrative importance.

The same underlying capability/injury semantics should calibrate both aggregate and expanded resolution.

## 33. Warfare authority

Existing `warfare.py` remains macro authority through current stabilization.

Future integration should evolve it from annual strength/casualty resolution toward richer inputs while preserving millennium performance.

War state may include:
- belligerents;
- causes/claims;
- objectives;
- forces/resources;
- fronts/territory;
- logistics;
- alliances;
- morale/support;
- command;
- battles/raids/sieges;
- casualties;
- war exhaustion;
- negotiations;
- settlement/destruction/displacement consequences.

Do not discard existing conflict history during migration.

## 34. Why wars begin

War requires actors/institutions choosing organized violence under pressure.

Causes may include:
- territory/resources;
- defense;
- succession;
- trade routes;
- retaliation;
- ideology/religion;
- alliance obligations;
- fear/preemption;
- internal legitimacy;
- magical threats/resources;
- accumulated unresolved disputes.

A tension metric can summarize pressure but must not become a causeless `if tension > X: war` final architecture.

## 35. Mobilization

Institutions need practical capacity to wage war:
- people;
- command;
- weapons/equipment;
- food;
- transport;
- money;
- magical capability;
- information;
- legitimacy/coercion;
- training;
- supply networks.

Population is not automatically an army.

## 36. Logistics

War capability decays without supply.

Relevant resources:
- food/water;
- equipment/repair;
- medicine/healers;
- transport;
- currency/pay;
- magical consumables;
- replacement personnel;
- shelter.

Distance, weather, roads, enemy action and infrastructure affect logistics.

A stronger force can lose operationally because it cannot sustain itself.

## 37. Command and information

Commanders operate on incomplete information.

Orders require communication and can be delayed, misunderstood or become obsolete.

Subordinates may:
- obey;
- misunderstand;
- improvise;
- refuse;
- betray;
- be unable to comply.

Institutional authority does not create telepathy.

## 38. Morale and willingness

Morale is not one magical army-health bar.

Group willingness to continue emerges from:
- casualties;
- fear;
- trust in leadership;
- objective importance;
- cohesion/relationships;
- supply;
- perceived chance of success;
- treatment of deserters/prisoners;
- homes/families threatened;
- prior victories/defeats.

Aggregate morale diagnostics may summarize this for performance.

## 39. Sieges and settlements

Sieges connect warfare to infrastructure/economy/population.

Relevant state:
- fortification;
- food/water stocks;
- population;
- disease/sanitation where modeled;
- defenders;
- relief forces;
- siege capability;
- trade isolation;
- civilian morale;
- internal politics.

Siege outcomes should cause actual shortages, deaths, migration, property damage and institutional consequences.

## 40. Civilians

War affects people not participating in combat through:
- displacement;
- shortages;
- destroyed property/infrastructure;
- loss of family;
- conscription;
- taxation/debt;
- crime;
- disease/injury;
- refugee flows;
- occupation;
- cultural/knowledge loss.

Civilian consequences should feed future Psyche, relationships, economy, politics and generational history.

## 41. Occupation

Controlling territory requires more than winning a battle.

Occupation depends on:
- force presence;
- administration;
- local institutions;
- supply;
- legitimacy/fear;
- collaborators/resistance;
- information;
- geography.

Resistance can be political, economic, informational or violent.

## 42. War termination

Wars end through causal changes:
- objective achieved/abandoned;
- resource exhaustion;
- leadership change;
- military defeat;
- negotiated settlement;
- alliance change;
- internal revolt;
- external threat;
- inability to continue.

Peace agreements are information/legal/institutional objects requiring parties and enforcement. Ending official war does not erase resentment, occupation or unresolved claims.

## 43. Atrocity, restraint and norms

Do not use global good/evil flags.

Conduct in war emerges from:
- orders;
- values;
- fear;
- revenge;
- discipline;
- dehumanizing beliefs;
- institutional norms;
- incentives;
- accountability;
- local opportunity.

Different observers/institutions may classify the same conduct differently, while objective acts remain recorded.

## 44. Veterans and aftermath

Survivors carry consequences:
- injury/disability;
- grief;
- fear;
- memories;
- relationships/comradeship;
- status/reputation;
- skills;
- debt/wealth;
- political expectations;
- difficulty reintegrating;
- new institutions/networks.

Do not force a universal veteran psychology. Outcomes depend on experience/person.

## 45. Historical consequences of violence

Violence can create:
- feuds;
- martyrs/heroes in observer-relative memory;
- legal reforms;
- institutions;
- migrations;
- destroyed knowledge;
- relic-significant objects;
- border changes;
- family extinction/succession;
- economic shifts;
- cultural practices;
- monuments/commemorations.

These arise through downstream systems, not combat tagging an event as `historically_important`.

## 46. Resurrection

Default death remains one-life unless explicit in-world magic prevents/reverses it.

Resurrection is not UI respawn and does not rewind history.

Future resurrection mechanics require explicit magic/cosmology authority for:
- eligibility;
- time limits;
- bodily requirements;
- cost/resources;
- identity continuity;
- memory effects;
- social/legal consequences.

Until authored, do not invent convenient resurrection rules.

## 47. Player parity

The player obeys the same causal combat/injury rules as simulated people unless an explicitly authored mechanic says otherwise.

No narrative immunity. No NPC immunity because they are historically interesting.

Across alternate histories, the human player may possess meta-knowledge, but the player character only possesses information legitimately available in-world.

## 48. Resolution levels for performance

Use three levels:

### Aggregate
Routine/background violence, large-scale battle portions, low-consequence encounters. Preserve causal inputs/outcomes without exchange detail.

### Encounter
Bounded temporal sequence for meaningful fights involving simulated persons.

### Focused
Higher-resolution sequence for player-facing or unusually consequential encounters, still using the same semantics.

Resolution level may change detail, **not underlying physics/canon**.

## 49. Determinism and stochasticity

Combat uses isolated deterministic RNG namespaces.

Same world/history/version/config reproduces outcomes exactly.

Randomness represents legitimate uncertainty in execution, perception, timing and chaotic interaction—not authorial drama.

Adding unrelated simulation detail should not perturb combat streams where namespace isolation can prevent it.

## 50. Performance constraints

- no per-frame combat for offscreen millennium simulation;
- bounded exchange counts;
- aggregate large battles;
- expand only consequential individuals/events;
- injury deterioration scheduled only while relevant;
- no annual scan of all historical wounds;
- healed/dead injuries become archival state;
- index active wounded by next deterioration/recovery event;
- healer search localized through settlement/institution/relationship indexes;
- war updates event/phase driven where possible;
- preserve ≤120 sec canonical millennium target.

## 51. Behavioral acceptance scenarios

1. Healthy Silver overwhelmingly defeats healthy Iron in direct fair combat across repeated seeds.
2. Iron can achieve a rare causal success against Silver through substantial preparation/surprise/environment/injury advantage without rank bypass.
3. No upset occurs solely because an important story would result.
4. Two same-rank combatants differ meaningfully because mastery, abilities, equipment, health and terrain differ.
5. Combat ends in retreat/surrender/incapacitation without death when objectives/conditions support it.
6. A nonlethal-intent fight can accidentally cause death.
7. A catastrophic injury can kill immediately before healer intervention.
8. A severe but non-immediate-lethal injury creates a finite rescue window.
9. Higher-rank resilience extends viability without automatically healing the wound.
10. A healer saves a person when reached in time and fails to save the same injury when arrival is too late.
11. Mundane stabilization can extend survival until advanced healing arrives.
12. A healer cannot treat an injury they never learn about.
13. A survivor can require long recovery despite successful healing.
14. Permanent impairment can alter occupation/goals/relationships without scripted tragedy.
15. Assassination success depends on preparation/access rather than an assassination tag bypassing rank.
16. A combatant makes a bad tactical choice from false information without reading hidden truth.
17. Monster encounters use compatible injury/rescue semantics.
18. Adventure Society star rank does not alter physical combat power.
19. Large battle resolution produces casualties consistent with the same capability/injury assumptions as expanded encounters.
20. Named/high-significance people receive no survival protection.
21. Stronger army can lose campaign effectiveness through failed logistics.
22. Commander orders can fail because communication/access breaks.
23. Winning a battle does not automatically produce stable occupation.
24. War damages economy, infrastructure, families, institutions and knowledge through actual causal effects.
25. Peace ends organized hostilities without resetting resentment or historical consequences.
26. Same seeds/config reproduce combat and war outcomes exactly.
27. Millennium simulation remains within performance target after integration.

## 52. Open design questions

Not yet frozen:
- compact injury anatomy/body-zone representation;
- exact rank-to-resilience scaling;
- exact temporal exchange duration/granularity;
- stamina/endurance model;
- ability targeting/range/cooldown semantics from canonical magic data;
- armor/equipment protection model;
- poison/disease integration;
- pain/consciousness modeling depth;
- permanent impairment representation;
- capture/restraint rules across ranks;
- healer triage/medical knowledge architecture;
- battle aggregation calibration against encounter model;
- force organization/unit structures;
- logistics detail level;
- siege mechanics;
- territorial/front representation;
- naval/air/magical warfare if world canon eventually supports them;
- resurrection rules pending authored cosmology/magic.

Coding agents must not invent these answers merely to complete an interface.

## 53. Implementation sequencing

1. Stage 0.5: stabilize current simulation, including threat ecology/warfare regressions, and freeze gold baseline.
2. Stage 1–5: establish Psyche, Information, Relationships, Institutions and knowledge prerequisites.
3. Stage 6A: injury/viability/recovery state and scheduled deterioration.
4. Stage 6B: temporal encounter resolver integrated with Agency/rank/abilities/environment.
5. Stage 6C: rescue/stabilization/healing.
6. Stage 6D: crime/assassination/capture/Society threat integration.
7. Stage 6E: calibrate hierarchical battle resolution against encounter semantics and migrate macro warfare incrementally.
8. Stage 6F: logistics/sieges/occupation/war termination and cross-system consequences.
9. Stage 7: player-facing combat/injury presentation using identical causal rules.
10. Stage 8+: resurrection only after objective cosmology/magic rules are authored.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Conflict principle:** violence does not decide who deserves to win; it resolves what these people, with these capabilities, wounds, beliefs, allies, resources and surroundings, manage to do before time runs out.
