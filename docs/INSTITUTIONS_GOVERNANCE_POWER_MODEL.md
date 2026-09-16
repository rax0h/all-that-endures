# ATE Institutions, Governance & Power Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze and prerequisite subjective/social contracts.  
**Purpose:** define how informal groups become durable institutions, how authority becomes legitimate or contested, how governance/law/bureaucracy work, and how power emerges from people, resources, relationships, records and dependency rather than abstract faction scores.

## North star

An institution exists because people repeatedly coordinate around a purpose and sustain roles, rules, resources, knowledge and legitimacy beyond one interaction.

The central questions are:

> Why does this institution exist? Why does anybody listen to it? What sustains it? What happens when the people who built it are gone?

The causal chain is:

`pressure/opportunity -> relationships + shared purpose -> repeated coordination -> roles/rules/resources -> institutional continuity -> decisions/actions -> consequences -> legitimacy/resources/membership/records change`

Institutions are not immortal containers. They are historical arrangements that must remain causally supported.

## 1. Existing institution authorities and required reconciliation

ATE currently contains **two institution representations**.

### `institutions.py`
This is the stronger general/Society-oriented authority. It currently owns:
- `Institution` with identity, kind, name, founding year/event, branches and members;
- `Branch` with settlement, authority, records and notices;
- Magic Society registration records;
- Adventure/Magic Society applications;
- Society notices;
- core Society founding/branch creation.

This namespace already connects institutions to events, lineage, records, transmission and settlement branches.

### `culture.py`
This contains a legacy/local cultural `Institution` with:
- settlement;
- kind;
- founding year;
- supported practices;
- authority;
- assets;
- legitimacy.

Culture uses these institutions to support retention of local practices.

### Migration rule
Do **not** create a third institution registry.

The future general institution authority should extend/reconcile `institutions.py`. The useful semantic state from `culture.py`—especially practice support, assets and legitimacy—must migrate or become linked components/projections under the unified institution identity.

`culture.py` should continue to own practices/adoption/cultural pressure, not independent institutional identity.

Exact schema migration waits for implementation-stage audit after Stage 0.5 freezes the baseline.

## 2. Informal group versus institution

Not every group is an institution.

An informal group may have:
- repeated membership/contact;
- shared interest/activity;
- social identity;
- temporary coordination.

It becomes institution-like when enough continuity mechanisms exist:
- recognized purpose;
- persistent identity/name;
- roles/offices;
- membership boundaries;
- rules/procedures;
- controlled resources/property;
- records/knowledge;
- succession/replacement mechanisms;
- external recognition/legitimacy;
- repeated collective action beyond one founder's personal relationships.

No fixed checklist must be mechanically satisfied, but persistence beyond the founding social circle requires causal infrastructure.

## 3. Founding

Institutions arise from pressures/opportunities such as:
- defense;
- trade coordination;
- magical danger/access;
- education;
- religion;
- mutual aid;
- craft standards;
- dispute resolution;
- property management;
- political coordination;
- labor organization;
- scholarship;
- crime/protection;
- transport/infrastructure;
- healthcare/healing;
- entertainment/culture.

Founding requires actual people/resources/opportunity. A settlement does not receive a guild merely because population crossed a designer threshold unless that threshold represents a documented approximation of causal pressure in the current legacy model.

Founding records should preserve:
- founding event/cause;
- founders;
- initial purpose;
- initial resources;
- initial place/branch;
- predecessor group/institution where applicable.

## 4. Institutional identity

An institution needs stable identity across changing members.

Identity can be sustained by:
- name/symbols;
- charter/rules;
- property/buildings;
- offices;
- records;
- rituals/practices;
- recognized membership;
- legal status;
- external relationships;
- continuity narratives.

An institution can change almost everything over centuries and still be treated as continuous if people/records/legal/social recognition preserve continuity.

Conversely, a new group using an old name does not automatically become objectively identical; continuity should be traceable.

## 5. Membership

Membership is objective institutional status where the institution recognizes it, but people's understanding of membership can still differ if records/communication fail.

Membership can arise through:
- application;
- invitation;
- employment;
- inheritance where rules permit;
- election/appointment;
- apprenticeship/initiation;
- coercion/conscription;
- purchase/dues;
- kinship where institutionally defined.

Membership should not imply:
- loyalty;
- agreement;
- friendship;
- knowledge of all institutional information;
- equal access;
- equal power.

## 6. Roles and offices

Institutions coordinate through roles.

A role defines some combination of:
- responsibilities;
- permissions;
- authority scope;
- information access;
- resource access;
- appointment/removal rules;
- term/duration;
- reporting relationships.

Examples:
- guildmaster;
- clerk;
- treasurer;
- teacher;
- judge;
- captain;
- priest;
- archivist;
- quartermaster;
- branch leader;
- investigator.

Role is not personality. Leadership competence emerges from capability, relationships, legitimacy, knowledge and conduct.

## 7. Authority, power and legitimacy are different

### Authority
Recognized right to make a decision/order within a domain.

### Power
Practical ability to cause outcomes or impose costs.

### Legitimacy
Degree to which relevant people/groups accept an authority/institution as entitled to act.

They can diverge.

A lawful mayor can have authority but little power. A wealthy merchant can have power without formal authority. A beloved elder can have legitimacy without office. A feared warlord can have power and compliance with little legitimacy.

Never collapse these into one `influence` score.

## 8. Why people comply

People obey/cooperate for different reasons:
- genuine legitimacy;
- shared values/purpose;
- trust/respect;
- law/norm;
- material dependency;
- expected benefit;
- habit/tradition;
- fear/coercion;
- reputation/status;
- relationship obligation;
- lack of alternatives;
- belief that others will comply;
- role identity/self-concept.

Outward compliance does not imply inward support.

This is crucial for strikes, coups, reform, corruption, rebellion and institutional collapse.

## 9. Legitimacy is observer/group-relative

There is no universally true `legitimacy=.73` in the final subjective model.

An engineering aggregate may summarize support for performance, but causal legitimacy lives in people/groups and evidence/history.

Different constituencies may regard the same institution as:
- rightful;
- useful but illegitimate;
- corrupt;
- sacred;
- foreign;
- oppressive;
- incompetent;
- indispensable.

Institutional behavior, records, culture and material outcomes affect these beliefs.

## 10. Resources and assets

Institutions need resources to do material things.

Possible assets:
- currency;
- land;
- buildings;
- tools;
- inventories;
- magical resources;
- records;
- transport;
- contractual claims/debts;
- controlled infrastructure.

Use existing economy/property/material/provenance authorities. Institution state should reference/control assets, not duplicate them into an abstract wealth pool when physical/economic state exists.

Some liquid budget abstraction may remain useful if grounded in currency/economic authority.

## 11. Institutional dependency

Institutions depend on people and systems:
- members/workers;
- funding;
- suppliers;
- records;
- buildings;
- public cooperation;
- legal recognition;
- magical specialists;
- transport;
- allied institutions;
- leadership;
- knowledge holders.

Dependency creates vulnerability.

A school can have students and a building but collapse because its only qualified teacher dies. A guild can survive founder death because procedures, property, apprentices and records remain.

## 12. Institutional knowledge and memory

Institutions know through:
- members;
- offices;
- records;
- procedures;
- archives;
- transmitted practices.

No hive mind.

A record can outlive everyone who created it. A secret known only by an officeholder can disappear at death. A new leader may inherit documents they misunderstand.

Institutional memory can disagree with:
- objective truth;
- personal memories;
- family narratives;
- rival institutional records.

## 13. Rules and procedures

Rules are information objects/claims backed by institutional recognition and enforcement practices.

Rules may govern:
- membership;
- promotion;
- discipline;
- resource use;
- elections/appointments;
- succession;
- contracts;
- record access;
- professional standards;
- dispute resolution;
- secrecy.

Written rules and actual practice can diverge.

An institution can formally prohibit behavior that leadership routinely tolerates. That gap can affect legitimacy, corruption and later reform.

## 14. Succession

Succession is a first-class historical process.

When a role becomes vacant, replacement depends on institutional rules and actual power:
- election;
- appointment;
- inheritance;
- seniority;
- examination;
- acclaim;
- purchase;
- force;
- negotiated compromise;
- emergency assumption of authority.

The formal successor may fail to secure compliance. Multiple claimants can exist.

Succession disputes can cause:
- faction formation;
- schism;
- violence;
- reform;
- legal precedent;
- institutional collapse;
- external intervention.

Do not hard-code founder death -> collapse or smooth replacement.

## 15. Factions inside institutions

Formal membership does not imply unified goals.

Factions emerge from actual networks and interests:
- friendships/kinship;
- ideological/value disagreement;
- profession/department;
- regional branch interests;
- resource competition;
- leadership succession;
- class/status;
- corruption/dependency;
- differing institutional interpretations.

Faction is preferably a derived/social structure until persistence/coordination makes it institution-like itself.

## 16. Branches

A branch is a local organizational node of a wider institution.

Branches may differ in:
- membership;
- local relationships;
- resources;
- records;
- practices;
- interpretation of rules;
- authority/legitimacy;
- local priorities.

A distant branch should not automatically know everything headquarters knows.

Branches communicate through transmission/records/travel. Delay and loss matter.

Branches can become semi-autonomous, secede, split or become the surviving core after headquarters collapses.

## 17. Institutional lifecycle

Possible states are derived from underlying condition, not story beats:
- founding;
- growth;
- stabilization;
- stagnation;
- reform;
- expansion;
- centralization/decentralization;
- schism;
- merger;
- capture;
- decline;
- collapse;
- revival.

The historian may label these afterward.

Causal health depends on members, resources, legitimacy, leadership, records, purpose relevance, competition and external conditions.

## 18. Collapse

Institutional collapse occurs when continuity mechanisms fail enough that coordinated identity/action can no longer be sustained.

Possible causes:
- member loss;
- resource exhaustion;
- lost legitimacy;
- military destruction;
- founder/key-person dependency;
- succession failure;
- records/knowledge loss;
- legal suppression;
- migration;
- purpose becoming obsolete;
- internal schism;
- corruption/predation;
- competing institution replacing function.

Collapse does not delete buildings, records, debts, former relationships or cultural influence. Ruins and archives can remain historically important.

## 19. Merger and schism

### Merger
Requires negotiated/forced continuity of people, assets, rules, records and identity. The resulting institution should preserve ancestry to predecessors.

### Schism
Occurs when coordinated subgroups cease accepting common authority/identity while retaining enough organization to persist separately.

Property, records, doctrine, membership and legitimacy can become contested.

No `split_chance` should operate without causal pressure.

## 20. Governance

Governance is coordination over shared problems/resources backed by accepted or imposed decision processes.

It need not begin as a state.

Possible governance sources:
- household heads;
- councils;
- assemblies;
- elders;
- guild coalitions;
- military command;
- religious authority;
- property owners;
- appointed officials;
- elected representatives;
- monarchic/dynastic systems;
- ad hoc emergency committees.

ATE must not assume an inevitable elder -> mayor -> king progression.

Governance form emerges from scale, history, culture, threats, resources, institutions and power relationships.

## 21. Jurisdiction

Authority has scope.

Jurisdiction can be bounded by:
- territory;
- membership;
- profession;
- property;
- legal domain;
- religious participation;
- institution branch;
- contract.

Overlapping jurisdictions create disputes.

A guild rule may bind members but not outsiders. A settlement court may lack practical reach beyond controlled territory. A religious institution may impose social consequences without legal authority.

## 22. Law

Law is not merely a strictness number.

A functioning law requires:
- a rule/prohibition/obligation;
- recognized jurisdiction;
- knowledge/publication/access;
- enforcement capacity;
- procedure;
- decision authority;
- consequences/remedies;
- some level of legitimacy/compliance.

Current `culture.py` law fields (`domain`, `strictness`, `enforcement`, `origin_event`) are useful legacy approximations but should eventually migrate into richer legal/institutional structures rather than becoming a parallel permanent legal universe.

## 23. Enforcement

Law without enforcement may remain symbolic/normative.

Enforcement depends on:
- personnel;
- information/evidence;
- resources;
- jurisdiction;
- willingness to act;
- relationships/dependencies;
- corruption;
- fear of retaliation;
- public cooperation.

Enforcement can be selective without a global corruption roll.

## 24. Legal process and judgment

Legal institutions obey the epistemic model.

They act on:
- testimony;
- records;
- physical evidence;
- reputation/credibility beliefs;
- procedure;
- applicable law;
- decision-maker beliefs;
- power/pressure.

Objective guilt does not guarantee conviction. Legal innocence does not alter objective events. Wrong judgments remain historical facts with consequences.

## 25. Bureaucracy

Bureaucracy is institutional memory and coordination embodied in roles, procedures and records.

It becomes useful when scale exceeds personal relationship management.

Bureaucratic functions include:
- registration;
- accounting;
- taxation/dues;
- inventory;
- contracts;
- permits;
- membership rolls;
- correspondence;
- court records;
- archives;
- appointments;
- logistics.

Bureaucracy has costs: labor, literacy, record storage, delay and opportunities for error/manipulation.

Do not spawn clerks because an institution reaches level 3. Roles arise when coordination load/resources justify them.

## 26. Collective action

People can coordinate without formal institutions around:
- mutual aid;
- protest;
- strike;
- rebellion;
- militia;
- migration;
- construction;
- festival;
- boycott;
- vigilante action;
- disaster response.

Collective action requires enough communication, shared motive, trust/expectation and opportunity.

Key problem:

> Why does each participant believe enough others will participate to make action worthwhile?

Relationships, reputation, organizers, institutions, public commitments and prior success help solve this coordination problem.

Repeated collective action can institutionalize.

## 27. Political power without a power meter

Political power is the ability to shape collective outcomes through combinations of:
- legitimate office;
- wealth/property;
- control of resources/infrastructure;
- military/magical capability;
- dependency networks;
- information/secrets;
- reputation;
- kinship/marriage;
- institutional membership;
- patronage;
- legal authority;
- social network position.

Different forms of power substitute imperfectly.

A Diamond-ranked person may be physically overwhelming yet politically isolated. A mundane administrator controlling records, payments and appointments may wield enormous institutional power.

## 28. Patronage and dependency networks

Powerful families/people can emerge through repeated dependencies:
- jobs;
- housing;
- loans;
- land;
- healing;
- magical training/resources;
- introductions;
- protection;
- contracts;
- legal favors;
- institutional appointments.

Favor creates possible obligation, not guaranteed loyalty.

Over generations, these relationships can create dynastic influence without a `powerful_family=True` flag.

## 29. Corruption

Corruption is behavior produced by conflicting obligations, incentives, secrecy, power and weak accountability—not a corruption stat.

Examples:
- clerk alters record for kin;
- official awards contract to patron;
- investigator suppresses evidence under threat;
- leader uses public assets privately;
- guild protects member despite known wrongdoing;
- bribe changes a decision.

The same act may be described differently by different cultures/laws/observers. Objective action and material transfer remain recordable even when moral/legal classification is contested.

## 30. Accountability

Accountability mechanisms alter expected consequences:
- audits;
- competing offices;
- public records;
- elections;
- courts;
- member votes;
- professional review;
- whistleblowers;
- rival institutions;
- reputation;
- removal procedures;
- force.

They require actual people, information access and enforcement. A written anti-corruption rule does nothing by itself.

Existing Society accountability should be preserved and integrated rather than replaced by generic abstractions.

## 31. Class and institutions

Class is not a caste tag unless a culture/institution explicitly creates one.

Material/social class patterns emerge from:
- property;
- income;
- occupation;
- inheritance;
- education;
- magical access;
- institutional roles;
- debt;
- social networks;
- legal privilege;
- geography.

Institutions can reproduce or disrupt class through access rules, credentials, inheritance, patronage and redistribution.

## 32. Organized crime

Do not create a special criminal-faction ontology.

Organized crime emerges when people repeatedly coordinate profitable/protective illegal activity and develop institutional continuity:
- roles;
- territory/markets;
- enforcement;
- records/secrets;
- patronage;
- corruption;
- succession;
- membership.

At sufficient persistence it is simply an institution whose activities conflict with applicable law/other institutions.

## 33. Religion and institutions

Religious institutions eventually use the same general institution mechanics: members, roles, property, records, succession, branches, legitimacy and schism.

Their theological claims remain mortal beliefs unless objective cosmology separately establishes divine facts.

Implementation remains deferred until objective cosmology is authored.

## 34. Schools and knowledge institutions

A school should emerge when sustained teaching demand/resources become institutionalized.

It requires some combination of:
- teachers;
- learners;
- curriculum/knowledge;
- place/resources;
- funding/support;
- rules/roles;
- continuity.

A single master with apprentices is not automatically a school. A school can collapse when teachers/funding disappear even if the building remains.

## 35. Adventure Society and Magic Society

These remain important canonical institutions but should eventually obey the same generalized lifecycle rather than being metaphysically guaranteed eternal exceptions.

Current legacy behavior can continue through Stage 0.5.

Future integration must preserve:
- branches;
- registration/records;
- applications;
- notices;
- Adventure Society star rank as trust/judgment/operational responsibility, **not magical power**.

Critical magic invariant: Society eligibility/rank-facing logic must respect canonical complete-path rules. A ranked person requires all essences/confluence and all 20 abilities. Existing helpers that only test essence/confluence completeness must be audited during Stage 0.5/current magic stabilization rather than silently treated as final canon.

## 36. Institutional decisions and Agency

Institutions do not think as magical super-agents.

Institutional decisions occur through people in roles/processes:
- leader decision;
- council vote;
- member vote;
- delegated officer;
- procedure/rule;
- emergency command;
- negotiated coalition.

The people involved use their own beliefs, relationships, values and incentives, constrained by institutional roles/rules/resources.

The institution then owns the resulting official action/record where appropriate.

## 37. Institutional action and responsibility

Separate:
- individual actor;
- role authority;
- official institutional action;
- private misuse of office.

An officer can act outside authority. Others may still believe the institution authorized it. Later review can ratify, repudiate or punish the action.

This distinction is important for diplomacy, law, corruption and war.

## 38. Diplomacy and inter-institution relationships

Institutions can have objective agreements/conflicts, but negotiations occur through people/representatives.

Possible relations:
- alliance;
- trade agreement;
- recognition;
- rivalry;
- jurisdiction dispute;
- debt;
- patronage;
- merger negotiation;
- hostility/war;
- information sharing.

Representative relationships and trust can materially affect outcomes without replacing institutional interests.

## 39. Buildings and institutional continuity

Buildings are infrastructure/property, not institutions.

An institution can:
- exist without dedicated building;
- move;
- occupy multiple buildings;
- lose headquarters and survive;
- collapse while its building remains;
- inherit/reuse another institution's building.

Construction follows existing causal architecture: need -> financing/resources -> land -> design -> materials -> labor -> construction -> maintenance.

## 40. Institutional performance model

Do not run full governance cognition for every institution every year.

### Background
Cheap maintenance of membership, resources, roles, routine records and existing obligations.

### Active
Institutions with current projects, elections, applications, disputes, shortages, expansion or external threats receive richer updates.

### Event reaction
Deaths, succession vacancies, scandals, disasters, war, discoveries, major resource shocks, legal disputes and public failures trigger targeted reconsideration.

Performance rules:
- indexed membership/roles/branches;
- bounded active issues/projects;
- no institution x all-people scans;
- local recruitment through actual networks/settlements;
- records referenced rather than copied;
- aggregate routine administrative work where individual detail is irrelevant;
- expand individual simulation only when decisions/consequences matter.

## 41. Behavioral acceptance scenarios

1. A founder dies and the institution survives because roles, records, resources and successor legitimacy remain.
2. A founder dies and a different institution collapses because continuity depended almost entirely on that person's relationships/knowledge.
3. Formal successor takes office but fails to secure practical compliance.
4. Two legitimate claimants create a succession dispute and possible schism without scripted civil war.
5. A branch develops different practices/priorities because information/local pressures differ.
6. A distant branch fails to learn headquarters information until transmission arrives.
7. An institution preserves knowledge after every founding member dies.
8. Undocumented institutional knowledge disappears with the last holder.
9. A lawful official has authority but insufficient power to enforce an order.
10. A person without office influences policy through wealth/dependency/network relationships.
11. A physically powerful ranked person fails to dominate politics because they lack legitimacy/allies/information/institutional control.
12. A mundane clerk materially changes history through control/manipulation of records.
13. Written rules diverge from actual institutional practice.
14. Selective enforcement emerges from relationships/incentives rather than a random corruption flag.
15. A strike/protest forms from real communication/network coordination and can fail from insufficient participation.
16. Repeated informal collective action can become a durable institution.
17. A social circle remains informal when it lacks continuity/resources/roles.
18. A school forms from sustained teaching demand rather than population threshold alone.
19. A school collapses when teachers/funding vanish while its building survives.
20. A criminal organization emerges using the same institutional primitives as legal organizations.
21. Two constituencies hold sharply different legitimacy beliefs about the same government.
22. Public compliance under coercion does not become private support.
23. Institution merger preserves ancestry/provenance of predecessor institutions.
24. Institution collapse leaves records, ruins, debts, former members and cultural effects in the world.
25. Removing labels such as `corrupt`, `powerful_family`, `stable_government` and `criminal_faction` does not remove the underlying causal behavior.

## 42. Open design questions

Not yet frozen:
- exact unified institution schema after legacy reconciliation;
- migration path for `culture.py` institutions/laws;
- generic role/office representation;
- formal rule/procedure representation;
- voting/coalition mechanics;
- taxation/dues/budget architecture;
- legal jurisdiction representation;
- legitimacy aggregation for performance/diagnostics without making aggregate causal truth;
- faction detection/persistence;
- collective-action commitment/coordination mechanics;
- inheritance of institutional/property rights;
- diplomacy treaties and enforcement;
- scalable bureaucracy/record storage;
- government formation at settlement/region scales;
- long-lived ranked people holding office for centuries and resulting succession/cultural pressures;
- how advanced polities federate/confederate/centralize;
- objective cosmology's later effect on religious institutional authority.

Coding agents must not invent these answers merely to complete an interface.

## 43. Implementation sequencing

1. Stage 0.5: finish current currency/magic-access/completion stabilization and freeze gold baseline.
2. Stage 1: subjective information/relationship/Agency foundations only; do not migrate institutions yet unless required for compatibility.
3. Stage 3: records/evidence/reputation provide the information substrate institutions need.
4. Stage 4: reconcile institution namespaces, add generalized lifecycle/roles/governance/law/bureaucracy/collective action/dependency power.
5. Stage 5: deepen schools, scholarship, archives and institutional knowledge.
6. Stage 6: connect institutions/governance to organized conflict/war.
7. Stage 8: religious institutions integrate only after objective cosmology is authored.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Institutional principle:** an institution is not a container full of people; it is a historically sustained agreement about roles, resources, rules, memory and authority—and it survives only while enough of that agreement remains real.
