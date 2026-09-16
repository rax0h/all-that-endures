# ATE Material Civilization: Settlements, Economy & Infrastructure Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze and must preserve the canonical millennium performance envelope.  
**Purpose:** unify settlements, households, property, production, inventories, currency, trade, infrastructure, construction, transportation, housing and material wealth into one causal material civilization rather than overlapping abstractions.

## North star

Civilization is material before it is statistical.

People need somewhere to live, something to eat, tools to work with, routes to move through, resources to transform, and institutions capable of coordinating things no household can do alone.

The causal chain is:

`environment/resources + people/skills/knowledge + property/access + labor/capital -> production -> inventories/services -> exchange/use -> wealth/shortage -> investment/migration/institutional response -> changed material world`

> **Do not simulate prosperity directly. Simulate the things prosperity is made of.**

## 1. Existing authorities and reconciliation rule

ATE already has substantial material foundations. Future work must extend/reconcile them rather than create replacements.

### Current economy/property
`economy.py` currently owns `Property` identity, ownership, value and provenance/ownership history. This is a useful property-right/provenance foundation, but it is not yet a full economy.

### Current settlement/civilization logic
`civilization.py` currently owns important legacy behavior:
- settlement carrying-capacity approximation;
- household migration;
- trade-route creation/use;
- food-stock exchange;
- settlement prosperity changes;
- trade-driven knowledge/practice transmission;
- legacy institution/law behavior.

These behaviors are causal seeds to preserve during migration, not permanent final abstractions.

### Current infrastructure
`infrastructure.py` owns durable infrastructure identity with kind, connected settlements, condition, capacity, build year and provenance.

`development.py` currently:
- decays infrastructure;
- maintains irrigation/roads;
- derives settlement irrigation/road summaries;
- creates roads after repeated trade use;
- practices agriculture/construction/craft skills.

### Current currency/magic economy
`currency.py` and current ranked-currency circulation are active Stage 0.5 authorities. Do not redesign or weaken them while stabilization is open.

### Materials/provenance
`materials.py` remains authority for material lots/crafted-item provenance.

### Reconciliation rule
Do **not** create a new parallel `MaterialEconomy` that owns copies of settlement food, property, currency, inventories, roads and crafted items.

The integrated architecture should connect existing authorities through stable IDs, transactions/events and derived indexes.

## 2. Hard performance contract

This layer must preserve the <=120-second millennium ceiling and, like ecology, should not consume available headroom merely because it exists.

Material depth comes from **stocks, flows, sparse transactions, aggregation and event-driven state**, not simulating every purchase or work-hour.

Every implementation PR in this layer eventually requires deterministic 100/500/1,000-year benchmark comparison against the frozen Stage 0.5 baseline.

## 3. Material layers

Distinguish five things:

1. **resources** — raw environmental/material availability;
2. **productive capacity** — people, skills, tools, land, workshops, infrastructure;
3. **stocks/inventories** — physically/economically available goods;
4. **claims/ownership** — who is recognized as controlling assets/goods/debts;
5. **flows** — production, consumption, transfer, trade, taxation, gifts, theft, destruction.

Do not collapse them into wealth/prosperity.

## 4. Goods versus services

### Goods
Persistable material outputs:
- food;
- timber;
- ore;
- cloth;
- tools;
- weapons;
- building materials;
- crafted goods;
- magical materials/resources where canonical.

### Services
Time/capability delivered without necessarily creating persistent inventory:
- construction labor;
- healing;
- teaching;
- transport;
- guarding;
- administration;
- entertainment;
- repair.

Services still consume time/resources and can transfer currency/obligation.

## 5. Commodity aggregation

Do not instantiate every grain of wheat or iron nail.

Bulk fungible goods should use quantity-based inventories/lots at appropriate ownership/location scale.

Individuate an item when identity/provenance matters:
- weapon/tool;
- crafted artwork;
- heirloom;
- magical object;
- contract/record;
- unusual high-value item;
- historically consequential object.

This preserves provenance without exploding object count.

## 6. Inventory

Inventory is quantity of a good controlled at a location/owner container.

Potential containers:
- household;
- person where needed;
- business/workshop;
- institution;
- settlement communal store;
- caravan/transport;
- warehouse;
- military force.

Inventory changes only through causal flows.

No system may spend goods it does not possess/access unless it creates an explicit debt/claim/transfer mechanism.

## 7. Food

Food is not merely a settlement scalar in the final architecture.

Useful aggregate categories may distinguish where consequences differ:
- staple food;
- perishable food;
- preserved food;
- livestock/animal products where useful.

Exact taxonomy remains open.

Settlement-level `food_stock` can remain a compatibility/diagnostic projection while authoritative food increasingly lives in actual stocks/ownership/access.

## 8. Consumption

People/households consume resources over time.

Background consumption should aggregate by household/population rather than create meal events.

Consumption depends on:
- household size/species needs;
- available inventory;
- market access;
- income/wealth;
- cultural/practice choices where relevant;
- rationing/institutional support;
- season.

Shortage affects health/Agency through the appropriate authorities rather than economy directly writing psychological outcomes.

## 9. Production

Production requires actual inputs.

Generic form:

`labor + skill/knowledge + tools/capital + site/land + material inputs + infrastructure + time -> output + waste/byproducts + wear`

Production systems include:
- farming;
- hunting/fishing;
- logging;
- mining;
- crafting;
- construction;
- transport;
- services.

Do not create output from settlement prosperity.

## 10. Production recipes/processes

A process describes causal requirements and outputs, not a technology-tree unlock.

A person/workshop can use a process only if they have sufficient:
- knowledge/practice;
- capability;
- inputs;
- tools/site;
- time/access.

Processes may have efficiency/quality variation from skill, equipment, environment and technique.

Exact recipe schema remains open.

## 11. Labor

Labor is people's time/capability.

People allocate labor through household needs, employment, institutions, obligations and Agency.

Background simulation may aggregate routine labor by household/workplace/occupation cohort, but labor cannot exceed plausible available population/time.

Population is not automatically productive capacity if people lack skills, tools, health or access.

## 12. Occupations and workplaces

Occupation describes repeated economic role, not an immutable class.

Work may occur through:
- household production;
- self-employment;
- workshop/business;
- institution;
- wage employment;
- apprenticeship;
- communal obligation;
- military service;
- coerced labor where culture/law permits.

A workplace can coordinate tools, inventories, labor and processes without requiring every workplace to become a formal institution.

## 13. Businesses/workshops

A persistent productive enterprise may own/control:
- premises;
- tools;
- inventories;
- currency;
- contracts/debts;
- workers/apprentices;
- recipes/practices;
- reputation/customer relationships.

Business continuity can survive founder death through inheritance/transfer/partnership/institutionalization—or fail.

Do not create a separate economic-person ontology when ordinary people/property/relationships can represent ownership and work.

## 14. Property

Property is socially/institutionally recognized control/claim over an asset, not metaphysical ownership.

Assets may include:
- land;
- buildings;
- tools;
- businesses;
- animals;
- inventories;
- crafted items;
- resource rights;
- vehicles/transport;
- currency;
- contractual claims.

Existing `Property` provenance/ownership history should be preserved and generalized carefully.

Ownership can be:
- personal;
- household/family;
- institutional;
- communal;
- partnership/shared;
- state/government where emergent.

## 15. Possession, ownership and access are different

A person can possess something they do not legally own. An owner can lack physical access. A tenant can use property they do not own. A thief can possess stolen goods.

Distinguish when relevant:
- title/recognized owner;
- current custodian/possessor;
- authorized users;
- location.

This supports theft, lending, renting, inheritance, confiscation and disputed property.

## 16. Land

Land matters because it provides location, productive capacity and access to environmental resources.

Land claims may cover:
- housing plot;
- farm;
- pasture;
- forest/resource rights;
- workshop/commercial site;
- institutional property.

Exact cadastral geometry is unnecessary for background simulation. Use parcels/areas/rights at sufficient spatial resolution.

Land ownership does not create fertility/resources; environment authority does.

## 17. Housing

Housing provides:
- shelter;
- household space;
- storage;
- privacy/crowding;
- location/access;
- status where socially interpreted.

Settlement population capacity should increasingly derive from actual housing + food/water/import/infrastructure capacity rather than a single formula.

Homelessness/overcrowding can exist when population exceeds accessible housing even if land exists.

## 18. Household economy

Household is a major material coordination unit.

Households may pool/share:
- food;
- housing;
- income;
- labor;
- childcare;
- tools;
- debt;
- property.

Exact pooling rules depend on relationships/culture and need not assume perfect equality.

Household economic stress feeds Development/Psyche through actual shortages, work burdens, debt and dependency.

## 19. Wealth

Wealth is derived from controlled assets, inventories, currency and claims minus liabilities—not a magical life-success number.

Liquid wealth differs from illiquid wealth.

A land-rich household can be cash-poor. A merchant can have large inventory but large debt. A powerful institution can own buildings while lacking currency for payroll.

Person `wealth` and settlement `prosperity` may remain compatibility projections until migration, but should not become final causal authorities.

## 20. Income and cash flow

Income arises from flows:
- sale of goods/services;
- wages;
- rent;
- investment/profit where modeled;
- gifts;
- institutional support;
- inheritance;
- spoils/theft;
- magical/Society rewards.

Outflows include consumption, inputs, wages, rent, debt service, taxes/dues, gifts, construction and losses.

Do not increment wealth because occupation is prestigious.

## 21. Currency

Currency is a transferable medium/claim used by the economy.

Existing currency and ranked-currency systems remain authoritative through Stage 0.5.

Future economy integration must support:
- holdings by people/households/institutions/businesses;
- transfer provenance/ledger where consequential;
- liquidity;
- hoarding;
- payment;
- exchange across settlements;
- sinks/sources grounded in canon.

Critical current concern: magic progression access is sensitive to ranked-currency circulation. Material-economy redesign must not accidentally reintroduce the bottleneck Stage 0.5 is calibrating.

## 22. Barter and non-currency exchange

Currency is not required for all exchange.

Exchange can use:
- goods;
- services;
- reciprocal obligation;
- credit/debt;
- gifts;
- institutional allocation.

The chosen mechanism depends on institutions, trust, liquidity and local practice.

## 23. Prices

Prices emerge from transactions/market conditions rather than a global price oracle.

Relevant pressures:
- local supply;
- demand/need;
- transport cost;
- competition;
- bargaining power;
- information;
- currency liquidity;
- institutions/law;
- expectations/stores.

Background markets may use settlement-level clearing/price indices for fungible commodities rather than simulate every buyer/seller negotiation.

Individuals can still face different effective prices through relationships, contracts, status, distance or discrimination.

## 24. Markets

A market is a repeated exchange network/place/institution, not necessarily a physical marketplace building.

Markets need:
- buyers/sellers;
- goods/services;
- information;
- access/transport;
- trust/enforcement or repeated relationships;
- exchange mechanism.

Physical market infrastructure may emerge when volume justifies it.

## 25. Trade

Trade moves goods/resources because location-specific supply/demand and transport allow beneficial exchange.

Current trade routes are valuable history-bearing connectivity and should migrate forward.

Trade requires:
- known route/partners;
- transport capacity;
- goods surplus/access;
- demand/opportunity;
- acceptable risk/cost;
- payment/exchange mechanism.

Trade should move actual quantities between inventories rather than only raise prosperity.

## 26. Trade routes

Trade routes strengthen through repeated use and infrastructure, and weaken when unused/dangerous/disrupted.

Current behavior where repeated exchange can physically establish roads is exactly the kind of causal composition ATE should preserve.

Routes can carry:
- goods;
- people;
- information/practices;
- disease pressure;
- institutions/cultural influence;
- threats/crime.

A route is not only an economic edge.

## 27. Transportation

Movement capacity depends on:
- distance/terrain;
- roads/bridges/water routes;
- vehicles/animals where available;
- weather;
- cargo mass/volume;
- security/threats;
- labor;
- fuel/feed where relevant.

Transport cost is material. A commodity can be abundant but economically inaccessible.

Do not simulate every wagon mile during background history; use route capacity/cost and instantiate journeys when consequential.

## 28. Infrastructure

Existing `Infrastructure` remains the durable asset authority.

Infrastructure may include:
- roads;
- bridges;
- irrigation;
- wells/waterworks;
- storage;
- walls/fortifications;
- docks;
- workshops;
- public buildings;
- schools/archives;
- sanitation;
- mines/extraction works;
- transport systems.

Buildings may need a richer subtype/property link, but do not duplicate infrastructure identity unnecessarily.

## 29. Infrastructure condition and capacity

Condition affects usable capacity/performance.

Capacity should represent what the asset can materially support.

Infrastructure degrades from:
- time/weather;
- use;
- disaster;
- war;
- neglect.

Maintenance requires labor/materials/resources, not merely a prosperity multiplier in the final model.

Current cheap decay/maintenance can remain compatibility behavior until migrated.

## 30. Construction

Construction is a material project:

`recognized need/goal -> site/rights -> design/knowledge -> financing/resources -> materials -> labor -> construction time -> completed asset -> maintenance`

Construction cannot appear solely because a settlement statistic crossed a threshold.

Possible builders/funders:
- household/person;
- business;
- institution;
- government;
- patron;
- cooperative group.

## 31. Projects

Large construction should use bounded project state:
- sponsor;
- objective/design;
- location;
- required materials;
- labor requirement;
- funding/access;
- progress;
- delays/damage;
- completion event.

Small routine construction can aggregate.

Projects create visible demand in the economy rather than receiving free materials.

## 32. Maintenance

Maintenance competes with new construction for resources.

A civilization can overbuild and later fail to maintain what it created.

Deferred maintenance reduces condition/capacity and can eventually cause failure.

Institutions/households may knowingly tolerate degradation when resources are scarce.

## 33. Storage

Storage changes resilience.

Capacity/quality affects:
- spoilage;
- seasonal buffering;
- famine resistance;
- trade timing;
- institutional/military supply.

A bumper harvest without storage can still be largely lost.

Storage buildings/infrastructure should connect to actual inventory capacity where useful.

## 34. Spoilage and inventory decay

Perishable goods can decay over time.

Use category-level/lazy spoilage rather than annual item scans.

Preservation practices/infrastructure change decay rates.

Nonperishable bulk goods should not incur pointless update cost.

## 35. Scarcity

Scarcity is mismatch between accessible need/demand and available supply, not merely low total world stock.

A settlement can experience scarcity while food exists elsewhere because:
- route failed;
- price unaffordable;
- war/blockade;
- information failure;
- institutional distribution failure;
- hoarding;
- transport capacity.

Current local scarcity can remain a derived compatibility signal while authoritative causes become material.

## 36. Prosperity

Settlement `prosperity` should become a diagnostic/derived summary, not causal money from nowhere.

Possible contributing observations:
- food/material security;
- productive output;
- trade volume;
- household wealth distribution;
- infrastructure;
- employment/opportunity;
- institutional capacity.

Systems should not produce goods or legitimacy merely because prosperity is high.

## 37. Poverty

Poverty is limited command/access over resources needed for desired/basic life, not a moral/personality condition.

It may arise from:
- low income;
- lack of property;
- debt;
- unemployment;
- disability/health;
- dependents;
- discrimination/exclusion;
- disaster;
- migration;
- high local prices;
- institutional extraction.

People in poverty can still own skills, relationships, knowledge and culturally significant assets.

## 38. Inequality

Inequality emerges from distribution of property, income, inheritance, debt, institutions, magical access and opportunity.

Diagnostics may summarize concentration, but no inequality meter should directly create unrest.

People react to conditions they perceive through values, relationships, beliefs and institutions.

## 39. Inheritance

Death can transfer:
- property;
- currency;
- business ownership;
- debt/claims where law permits;
- objects/heirlooms;
- housing/land rights.

Inheritance depends on law, family relationships, wills/records, institutions and actual control.

Disputed inheritance can become social/legal conflict.

Do not automatically divide assets evenly unless current compatibility rules require it pending richer law.

## 40. Debt and credit

Credit allows present access in exchange for future obligation.

A debt should preserve:
- creditor;
- debtor;
- principal/value;
- origin;
- terms/due condition where modeled;
- repayments/transfers;
- status/default.

Credit availability depends on trust, collateral/property, institutions, reputation and liquidity.

Debt creates dependency/power without requiring a debt-personality mechanic.

## 41. Rent and tenancy

People can use land/buildings/tools they do not own through rental/tenancy/share arrangements.

These create recurring flows and obligations.

Tenure systems are cultural/legal/institutional and should not be universally assumed.

## 42. Taxation, dues and institutional finance

Institutions/governments require material support.

Potential revenue:
- taxes;
- dues;
- fees;
- donations;
- rents/property;
- trade;
- patronage;
- contract revenue;
- spoils.

Collection requires authority, information and enforcement.

Institutional spending should draw from actual controlled resources/currency.

A government cannot build a road merely because `authority > .5`.

## 43. Public/collective goods

Infrastructure/services may benefit people beyond the payer:
- roads;
- walls;
- wells;
- sanitation;
- schools;
- archives;
- defense.

Their provision requires coordination/financing and can create free-rider/conflict questions handled by institutions/relationships.

## 44. Theft and material crime

Theft is unauthorized transfer/possession of actual goods/property.

It changes material state first. Whether anyone knows/proves it belongs to Information/Law.

Stolen goods retain provenance. They can be sold, gifted, recovered or become heirlooms while ownership claims remain disputed.

## 45. Destruction and loss

Goods/property/infrastructure can be destroyed by:
- consumption;
- wear;
- fire/flood/weather;
- war;
- sabotage;
- accident;
- abandonment/decay.

Destroyed material must leave inventories/assets rather than merely reduce value.

Consequential destruction should preserve causal event/provenance.

## 46. Craft quality

Quality should emerge from:
- material quality;
- craft skill/mastery;
- technique;
- tools/workshop;
- time/effort;
- condition/errors.

Quality can affect durability/performance/value.

Do not use quality as a disguised universal item rarity ladder.

## 47. Provenance and value

Market value and historical/cultural significance differ.

An ordinary sword can become valuable because of provenance. A technically excellent tool can remain cheap if common.

Material provenance should remain objective history; perceived provenance can be false/forged through the Information system.

## 48. Magic and the material economy

Magic participates materially through:
- essence/awakening-stone access;
- ranked currency;
- magical services;
- crafting/materials;
- threat-response work;
- long-lived skilled labor/capital accumulation;
- institutions/Societies.

Canonical rule remains absolute: no ranked magic user exists without all 3 base essences, confluence and all 20 abilities unlocked.

Economic calibration may improve access/liquidity but must never bypass those prerequisites.

## 49. Long-lived ranked people and capital

Gold/Diamond longevity can create unusual economic effects:
- centuries of skill accumulation;
- long-term businesses/property;
- compound relationship networks;
- patient investment;
- dynastic asymmetry;
- living founders;
- persistent creditors/debtors;
- old property claims.

Do not automatically make long-lived people wealthy. War, generosity, poor decisions, institutional constraints, loss and changing markets still matter.

## 50. Settlement identity

A settlement is a persistent inhabited place/network, not merely population + coordinates.

It accumulates:
- households/people;
- buildings/infrastructure;
- property;
- markets/workplaces;
- institutions;
- roads/routes;
- environmental modifications;
- records/history;
- neighborhoods/districts later if scale requires.

Settlement continuity can survive population turnover. A settlement can shrink, relocate partially, be abandoned or be reoccupied.

## 51. Settlement growth

Growth requires material support:
- housing;
- food/water;
- work/opportunity;
- security;
- transport/trade;
- institutions;
- environmental capacity/imports.

Births/migration create population pressure. Construction/investment can respond.

Do not automatically create housing/infrastructure to match population.

## 52. Settlement decline

Decline can result from:
- lost trade route;
- resource exhaustion;
- environmental pressure;
- war/threats;
- institutional collapse;
- migration;
- infrastructure decay;
- economic displacement.

Decline leaves material history: empty buildings, roads, property claims, ruins, abandoned workshops, records.

## 53. Cities and scale

Larger settlements require more coordination/infrastructure because personal household networks cannot handle every function.

Scale pressures can create:
- specialized occupations;
- markets;
- storage;
- sanitation;
- bureaucracy;
- transport infrastructure;
- districts;
- policing/fire response;
- public works.

Do not unlock city systems purely at arbitrary population levels; population thresholds may trigger *pressure checks* for causal needs.

## 54. Migration and material opportunity

Migration choices should consider known/perceived:
- jobs/land;
- food/security;
- housing;
- family/social networks;
- travel cost;
- species habitat fit;
- institutions;
- threats.

Current migration's scarcity/crowding/prosperity behavior is useful compatibility logic but should eventually be grounded in these material causes.

## 55. Economic information

People do not know global prices/inventories.

They learn through:
- local market experience;
- traders;
- records;
- relationships;
- institutions;
- travel.

A merchant can profit from information asymmetry. Rumors can cause hoarding/panic even when objective supply is adequate.

Agency uses actor-known economic opportunity, not omniscient market state.

## 56. Contracts

Contracts are information/legal objects describing promised future transfers/services.

They may cover:
- employment;
- trade;
- debt;
- rent;
- construction;
- transport;
- Society work;
- partnership.

A contract does not enforce itself. Compliance depends on incentives, relationships, law/institutions and capability.

## 57. Economic shocks

Shocks are ordinary causal changes:
- harvest failure;
- mine discovery/exhaustion;
- trade-route closure;
- war;
- disaster;
- migration;
- new technique;
- institutional policy;
- magical resource change.

The economy should transmit shocks through stocks/flows/prices/access rather than applying generic prosperity penalties.

## 58. Feedback loops

ATE should permit feedback such as:

`trade volume -> route use -> road establishment -> lower transport cost -> more trade -> settlement growth`

and:

`resource extraction -> local wealth -> population/infrastructure -> faster extraction -> depletion -> declining output -> migration/transition`

and:

`harvest failure -> food stock drawdown -> higher prices -> imports -> route strengthening -> storage investment`

No loop should grow without physical/resource constraints.

## 59. Failure modes to prevent

The integrated material system must explicitly guard against:
- goods created from prosperity/stat multipliers without inputs;
- infinite inventories/currency;
- markets trading goods nobody owns;
- infrastructure built without resources/labor;
- households consuming negative stock;
- migration responding to omniscient opportunities;
- roads improving without maintenance/history;
- every object being individually simulated;
- all-pairs settlement trade scans at large world scale;
- rich-get-richer runaway with no consumption/risk/depreciation;
- dead economies where liquidity/transport prevents all progression;
- magic-resource access being accidentally bypassed.

## 60. Performance architecture

### Aggregation
Routine production/consumption at household/workplace/settlement cohort scale.

### Sparse markets
Only settlements/routes with actual connectivity exchange. Use adjacency/route indexes rather than all-pairs as world scale grows.

### Lazy stocks
Spoilage/depreciation computed from elapsed time when accessed where possible.

### Bounded transaction detail
Persist consequential transfers and aggregate routine commodity clearing.

### Individual expansion
Individuate transactions when they matter for player interaction, provenance, relationships, crime, contracts, inheritance or major history.

### Project scheduling
Construction/maintenance uses active project queues rather than scanning every possible project.

### Derived summaries
Prosperity/scarcity/wealth diagnostics rebuilt cheaply from authoritative state and never used as hidden duplication when detailed state exists.

## 61. Determinism

Economic stochasticity uses isolated deterministic RNG namespaces after causal candidate formation.

Potential namespaces:
- `market_matching`;
- `production_variance`;
- `migration_economic_choice`;
- `business_formation`;
- `construction_delay`.

Exact names freeze at implementation.

Same seeds/version/config must reproduce stocks, routes, property and major economic history.

## 62. Diagnostics

Millennium diagnostics should include:
- population/households by settlement;
- food/material production and consumption;
- inventories/stores;
- commodity scarcity/price indices;
- trade volume/routes;
- currency liquidity/hoarding;
- property/wealth concentration summaries;
- housing capacity/crowding;
- infrastructure condition/capacity;
- construction/maintenance backlog;
- resource depletion;
- business/workplace counts;
- migration causes;
- magic-resource/currency access funnel;
- economy/material runtime share.

Diagnostics are read-only.

## 63. Behavioral acceptance scenarios

1. A settlement cannot consume more food than households/stores/imports provide without producing shortage consequences.
2. A bumper harvest increases available stock but may spoil if storage is inadequate.
3. A bad harvest is absorbed by stores/imports in a connected wealthy settlement.
4. The same harvest failure creates severe shortage in an isolated settlement.
5. A trade route moves actual goods between inventories rather than merely increasing prosperity.
6. Repeated trade can justify road construction/establishment and lower future transport friction.
7. Route disruption raises effective scarcity despite abundant goods elsewhere.
8. A mineral discovery changes production only after people know/access/develop it.
9. A mine eventually depletes through actual extraction.
10. Construction cannot finish without required labor/material access.
11. Infrastructure deteriorates when maintenance is deferred and materially loses capacity.
12. Settlement can overbuild during prosperity and struggle with maintenance later.
13. Household can be asset-rich but currency-poor.
14. Debt can create dependency without changing affection/loyalty automatically.
15. Stolen item retains provenance and can later be identified/recovered through evidence.
16. Business can survive founder death through causal succession/ownership transfer.
17. Another business collapses because skills/relationships/property continuity fail.
18. Settlement grows because housing/work/food/trade support incoming people rather than population automatically generating capacity.
19. Settlement decline leaves recoverable buildings/property/roads/records.
20. Large city develops specialized coordination because material scale creates need, not because it crossed a civilization-level threshold.
21. A person misses a profitable opportunity because they do not know it exists.
22. Rumor can cause local hoarding/price pressure without objective world shortage.
23. Gold/Diamond longevity can support centuries-old enterprises without guaranteeing wealth.
24. Ranked-currency circulation remains capable of supporting canonical magic progression without bypassing 20-skill completion.
25. Removing `prosperity`, `scarcity`, `wealth` summary fields from causal decision paths leaves material stocks/flows capable of explaining outcomes.
26. Material integration does not materially compromise the frozen millennium runtime baseline.

## 64. Open design questions

Not yet frozen:
- commodity taxonomy;
- authoritative inventory container schema;
- bulk lot versus generic quantity representation;
- production recipe/process schema;
- workplace/business entity representation;
- land parcel/right representation;
- housing/building representation and relation to infrastructure/property;
- household pooling rules;
- market-clearing/pricing algorithm;
- barter/credit prevalence;
- debt/contract schema;
- transport capacity/cost model;
- construction project granularity;
- storage/spoilage categories;
- tax/dues architecture;
- inheritance defaults before richer law/culture;
- currency integration after Stage 0.5 calibration;
- settlement districts/city scale;
- exact migration replacement for current prosperity/scarcity approximations;
- economic aggregation thresholds under performance budget.

Coding agents must not invent these answers merely to finish an interface.

## 65. Implementation sequencing

1. Stage 0.5: finish current currency/magic-access/completion calibration and freeze gold baseline.
2. Post-baseline audit: map every current stock/flow/property/infrastructure/currency/material field and identify compatibility projections versus authorities.
3. Material A: unified bulk inventory/commodity interfaces linked to existing property/material/currency authorities.
4. Material B: household consumption, production processes and workplaces using existing skills/environment.
5. Material C: sparse markets/trade routes moving real inventory; preserve current route history/transmission behavior.
6. Material D: transport capacity/cost and infrastructure effects.
7. Material E: buildings/housing/property access and settlement carrying capacity derived from material state.
8. Material F: construction/maintenance projects consuming labor/materials.
9. Material G: debt/contracts/business continuity/inheritance/institutional finance.
10. Material H: migrate prosperity/scarcity/wealth into compatibility diagnostics where detailed state supersedes them.
11. After every step: deterministic 100/500/1,000-year performance/calibration check against frozen baseline.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Material principle:** if civilization possesses, builds, consumes, sells, loses or inherits something, the simulation should be able to point to where it came from, who could access it, and what changed when it moved.
