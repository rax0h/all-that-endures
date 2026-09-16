# ATE World, Ecology & Environment Model v1

**Status:** design specification only. Implementation remains gated behind Stage 0.5 stabilization/gold-baseline freeze.  
**Purpose:** define the physical/ecological world as a causal participant in history while preserving deterministic millennium performance.

## North star

**The world is not scenery. It is another participant in history.**

ATE should support chains such as:

`weather/climate -> water/soil/vegetation -> harvest/wildlife/resources -> prices/health/threats -> migration/settlement pressure -> institutions/conflict -> land use -> changed environment`

No famine storyline is authored. A famine may emerge because enough causal systems failed together.

## 1. Hard performance contract

Environmental depth must **not materially compromise the canonical <=120-second 1,000-year simulation target**.

More importantly, the ceiling is not a budget to consume. If the frozen Stage 0.5 baseline is substantially faster than 120 seconds, ecology should preserve as much of that headroom as practical for later systems.

### Required engineering principle

> **Depth comes from causal composition, not simulation frequency.**

The environment receives a bounded computational budget. When greater detail would materially increase millennium runtime, resolution must become coarser, event-driven, lazy or procedurally reconstructable rather than simply running more updates.

### Implementation acceptance
Every environment/ecology PR must benchmark deterministic 100/500/1,000-year runs against the frozen gold baseline and report:
- runtime delta;
- peak memory delta where available;
- deterministic digest/fixture result;
- environmental active-region/event counts;
- any resolution degradation triggered.

A feature with disproportionate runtime cost does not merge merely because total runtime remains below 120 seconds.

## 2. Resolution philosophy

ATE does not need to simulate every tree, deer, raindrop, seed, soil organism or square meter.

Use the cheapest authoritative representation that preserves meaningful consequences.

### Default levels

**Regional aggregate** — climate, watershed, biome, broad vegetation, wildlife populations, resource abundance.

**Local/cell aggregate** — settlement catchments, farms, forests, rivers, roads, mines, important habitats and disturbed areas.

**Focused entity/site** — only when a particular animal, plant, hazard, object/site or environmental interaction becomes individually consequential.

Resolution changes detail, not underlying environmental canon.

## 3. Static world foundation

Expensive stable facts should be generated once and reused:
- elevation/topography;
- slope;
- watershed/drainage structure;
- coastlines/lakes/rivers baseline;
- geology;
- soil parent material;
- broad climate normals;
- resource deposits;
- biome potential;
- travel constraints.

Do not recompute immutable geography annually.

World Seed owns initial physical world generation. History Seed owns post-start stochastic environmental history where appropriate.

## 4. Geography

Geography creates opportunity and constraint through:
- elevation;
- slope;
- rivers/water bodies;
- passes/choke points;
- coasts;
- wetlands;
- forests/open land;
- soil/productivity;
- mineral/material deposits;
- natural hazards;
- travel distance.

Geography affects settlement, agriculture, trade, war, migration and culture without directly assigning outcomes.

A mountain does not create a mountain culture tag. It changes what people repeatedly have to solve.

## 5. Spatial representation

The exact map topology is not frozen, but the architecture should support sparse adjacency and hierarchical regions.

Requirements:
- stable location IDs;
- parent region/local area relationships;
- neighbor/travel connectivity;
- watershed connectivity where needed;
- settlement/resource/site references;
- compact environmental state per active spatial unit.

Avoid dense all-cell interactions.

## 6. Climate versus weather

### Climate
Long-run distributions/seasonal expectations for temperature, precipitation, storm likelihood and related conditions.

### Weather
Specific realized conditions/events within history.

Climate should usually be cheap, mostly static/slow-changing parameters. Weather should be generated only at temporal/spatial resolution needed by causal systems.

No requirement for daily weather across the entire world for 365,000 days.

## 7. Seasonal environment

Seasonality can affect:
- planting/harvest;
- water availability;
- travel;
- animal movement;
- disease vectors where modeled;
- heating/shelter needs;
- storm/fire risk;
- construction;
- food storage.

Background simulation may summarize seasonal outcomes annually or by a few meaningful seasonal phases. Focused/player-facing simulation may reconstruct finer deterministic weather when needed.

## 8. Deterministic procedural weather reconstruction

Where fine-grained weather is needed but was not explicitly persisted, it may be reconstructed from:
- World Seed;
- History Seed;
- simulation version;
- location;
- date/time;
- climate state;
- relevant persisted large-scale anomaly/event.

This allows detailed local weather without storing or simulating every day globally.

Reconstruction must not contradict persisted consequential weather events.

## 9. Climate variability

Long-term variability may include:
- wet/dry periods;
- warm/cool periods;
- multi-year drought;
- unusually severe winters/summers;
- storm clusters;
- slow secular changes if world canon supports them.

Use low-frequency regional state/anomalies rather than expensive global daily simulation.

Climate variability creates pressure; it does not directly create migration/famine/war flags.

## 10. Water

Water is a major causal resource.

Relevant aggregate state may include:
- baseline source/catchment;
- seasonal availability;
- storage;
- flow condition;
- drought/flood anomaly;
- quality/contamination where relevant;
- infrastructure modification.

Water affects:
- drinking;
- agriculture;
- settlement capacity;
- industry/craft;
- transport;
- sanitation/health;
- conflict;
- ecosystems.

Hydrology should follow precomputed watershed/connectivity rather than full fluid simulation.

## 11. Rivers and flooding

Rivers can change history through:
- transport;
- irrigation;
- fishing;
- water supply;
- floodplain fertility;
- flooding;
- bridges/fords/choke points.

Flood events should target connected vulnerable areas. Do not scan every world location for every flood.

Major persistent river-course change may exist if justified by long-term geomorphology/disaster mechanics, but routine channel simulation is unnecessary.

## 12. Soil

Soil is slow-changing productive state, not annual randomized fertility.

Useful dimensions may include:
- baseline fertility;
- moisture retention/drainage;
- erosion vulnerability;
- current nutrient/productivity condition;
- degradation/recovery pressure.

Soil changes from:
- cultivation intensity;
- fallow/rotation practices;
- erosion;
- flooding/sedimentation;
- vegetation cover;
- manure/amendment;
- fire;
- drought.

Use lazy/aggregate updates when land use changes or productivity is queried.

## 13. Vegetation and biomes

Biome/vegetation should represent ecological composition sufficiently to affect resources and hazards.

Possible aggregate dimensions:
- dominant vegetation types;
- biomass/cover;
- maturity;
- productivity;
- disturbance;
- regeneration potential;
- habitat quality.

A forest is not 800,000 simulated trees. It is a changing ecological resource/habitat until an individual tree matters for a focused interaction.

## 14. Succession and recovery

Abandoned/disturbed land can change over time:
- cleared field -> scrub -> young woodland -> mature forest;
- burned forest -> regeneration;
- overgrazed land -> slow recovery or persistent degradation;
- abandoned settlement -> vegetation reclaiming structures.

Succession should use analytic/lazy time-since-disturbance functions where possible rather than yearly stepping.

## 15. Plants and useful species

Specific plant species need individual simulation only when they materially differ in:
- food value;
- medicine;
- construction/craft use;
- magical/ecological role;
- cultivation requirements;
- habitat effects.

Most vegetation can remain grouped functional/ecological categories.

Domesticated/cultivated plants can have richer state because agriculture/economy directly depends on them.

## 16. Wildlife populations

Most wildlife exists as population/range state, not individual agents.

Useful dimensions:
- species/group;
- population abundance;
- carrying capacity;
- range/habitat;
- reproduction pressure;
- mortality pressure;
- migration/seasonality where important;
- hunting/predation pressure.

Individual animals are instantiated only when needed for focused hunting, taming, notable encounters, disease transmission or other consequential events.

## 17. Population ecology

Population changes should respond to:
- food/habitat;
- predation;
- disease;
- hunting;
- weather;
- competition;
- migration;
- disturbance.

Avoid annual individual births/deaths for background wildlife. Use bounded population dynamics or analytic updates.

## 18. Food webs

ATE does not require full species-by-species trophic simulation.

Use functional relationships sufficient for consequences:
- producers/forage;
- herbivores/prey;
- predators;
- scavengers;
- key competitors;
- special/magical ecological roles.

Only model a link explicitly when changes in one population can materially affect another system.

## 19. Carrying capacity

Carrying capacity is dynamic and local, affected by:
- water;
- food/productivity;
- habitat;
- season/climate;
- human land use;
- infrastructure;
- predation;
- disturbance.

It is not a permanent population cap.

Human settlement capacity similarly emerges from food/water/housing/economy/import access rather than one fixed terrain number.

## 20. Agriculture

Agriculture connects ecology to economy and settlement.

Production depends on:
- cultivated area;
- crop/practice;
- soil;
- water;
- seasonal weather;
- labor;
- tools/infrastructure;
- pests/disease where modeled;
- knowledge/skill;
- seed/input availability.

Do not roll harvest independently of these causes.

Background farms can aggregate at household/settlement catchment scale. Focused farms may expose plots/crops when player-facing.

## 21. Crop failure and famine

Crop failure is reduced production from environmental/material causes.

Famine requires downstream failure of food access:
- harvest shortfall;
- insufficient stores;
- failed imports/trade;
- poverty/distribution failure;
- war/blockade;
- transport disruption;
- institutional failure.

A bad harvest is not automatically famine.

This distinction is essential for emergent history.

## 22. Livestock/domesticated animals

Domesticated populations may need richer aggregate state than wildlife because they are property/economic assets.

Track at the cheapest useful level:
- herd/flock counts;
- species;
- ownership;
- productivity;
- feed/pasture pressure;
- mortality/disease;
- breeding/replacement.

Individuate notable animals only when consequential.

## 23. Hunting and fishing

Harvest pressure changes wildlife/fish abundance and future availability.

Success depends on:
- local population;
- season;
- knowledge/skill;
- equipment;
- access;
- weather;
- competition/regulation.

Overharvest can reduce future returns without requiring a conservation morality mechanic.

## 24. Natural resources

Resources may include:
- timber;
- stone;
- metals/minerals;
- clay/sand;
- fuels;
- fibers;
- salt;
- rare/magical materials where canon supports them.

Distinguish:
- deposit/stock;
- known deposit;
- accessible deposit;
- extraction capacity;
- remaining economically useful amount.

The simulator can know a mineral deposit exists while civilization does not.

## 25. Extraction

Extraction changes world state through:
- depletion;
- labor/resource cost;
- landscape disturbance;
- pollution/waste where relevant;
- infrastructure creation;
- settlement/economic incentives.

Do not update untouched deposits annually. Update on extraction/query.

## 26. Human land use

Humans alter ecology through:
- clearing;
- farming;
- grazing;
- irrigation/drainage;
- roads;
- settlements;
- mining;
- hunting;
- fire;
- waste/pollution;
- dams/bridges where supported;
- magical alteration where canon permits.

Environmental consequences feed back into human systems.

No generic `environmental_damage` morality score is required.

## 27. Environmental degradation

Degradation should be domain-specific:
- soil erosion/exhaustion;
- deforestation;
- depleted wildlife;
- contaminated water;
- overgrazing;
- mine exhaustion;
- damaged habitat.

It can be temporary or persistent depending on process and recovery conditions.

People may notice effects without understanding causes correctly.

## 28. Fire

Fire can be:
- natural;
- accidental;
- agricultural;
- deliberate/warfare;
- infrastructure-related;
- magical where canon permits.

Fire outcome depends on:
- fuel/vegetation/buildings;
- moisture/weather;
- wind;
- detection;
- response capacity;
- terrain.

Use event propagation across only connected exposed areas, bounded by fuel/weather, not world-wide per-tick fire simulation.

## 29. Storms and severe weather

Potential events:
- thunderstorms;
- high wind;
- hail;
- tornadoes/cyclones where climate supports them;
- blizzards;
- extreme heat/cold;
- heavy rain/flooding.

Events arise from regional weather/climate distributions and affect exposed locations/assets/people.

Persist consequential events. Routine weather can remain reconstructed/aggregate.

## 30. Drought

Drought is sustained water deficit, not one bad-weather roll.

It can affect:
- crops;
- rivers/wells;
- wildfire risk;
- wildlife;
- livestock;
- prices;
- migration;
- conflict.

Downstream systems react through their own causal rules.

## 31. Geological hazards

Where geography supports them, rare hazards may include:
- earthquakes;
- landslides;
- volcanic events;
- erosion/collapse.

Use low-frequency event scheduling and spatial exposure indexes. Do not continuously simulate plate tectonics.

## 32. Disease and ecology boundary

Environment can provide disease pressure/vector conditions, but detailed human disease belongs in a health/demography system rather than ecology duplicating person health.

Ecology may own:
- vector habitat pressure;
- contaminated water exposure;
- animal reservoir pressure;
- seasonal environmental suitability.

Health authority resolves infection/illness consequences.

## 33. Pollution and contamination

Pollution emerges from actual production/waste/extraction practices.

Potential effects:
- water quality;
- soil productivity;
- health exposure;
- wildlife;
- social/legal conflict.

Only model contaminants/categories that create meaningful consequences. Do not simulate chemistry for its own sake.

## 34. Threat ecology integration

Existing ranked threat ecology remains an authority to integrate, not replace.

Future environment work should give threats ecological context:
- habitat/range;
- prey/resources;
- environmental suitability;
- disturbance;
- migration;
- settlement proximity;
- monster surges/canonical magical pressures.

Human expansion may disturb habitat and alter encounter frequency. Threats may alter ordinary wildlife/settlement behavior.

Do not weaken current ranked-threat canon during environment integration.

## 35. Magical ecology boundary

Objective magical environmental rules require explicit canon.

Until authored, the environment may reference existing canonical threat/magic resources but must not invent:
- ambient mana climate;
- magical ley-line physics;
- divine weather;
- spontaneous magical biomes;
- soul ecology;
- metaphysical corruption.

Those belong to later cosmology/magic worldbuilding.

## 36. Settlement placement and growth

Environment influences settlement viability through:
- water;
- food potential;
- resources;
- defensibility;
- travel/trade access;
- hazard exposure;
- existing infrastructure;
- threat ecology.

But settlements grow through people/economy/institutions, not environmental suitability alone.

A poor site can persist because history/infrastructure makes abandonment costly. A superb site can remain empty because nobody knows/reaches it.

## 37. Migration

Environmental pressure can contribute to migration through:
- drought;
- resource depletion;
- repeated floods/fire;
- failed harvests;
- threat movement;
- land scarcity;
- changing opportunity elsewhere.

Migration remains a human/Agency decision constrained by knowledge, relationships, resources and alternatives.

No environment system directly teleports population after crossing a hardship threshold.

## 38. Economy integration

Environmental state should expose causal production/access inputs rather than independently changing prices.

Examples:
- crop yield -> commodity supply;
- timber stock/access -> logging output;
- mine deposit/access -> ore output;
- wildlife -> hunting yield;
- flood -> infrastructure/inventory loss.

Economy authority then resolves inventories, trade and prices.

## 39. Infrastructure integration

Infrastructure changes environmental access/impact:
- roads reduce transport friction;
- irrigation changes water/agriculture;
- bridges change connectivity;
- fortifications alter flood/fire exposure only where physically relevant;
- mines/logging camps expand extraction;
- storage mitigates seasonal/famine risk.

Infrastructure also requires maintenance and can fail under environmental stress.

## 40. Knowledge and environment

People do not automatically know environmental truth.

They may know/believe:
- seasonal patterns;
- safe water sources;
- soil quality;
- animal ranges;
- storm signs;
- resource locations;
- farming practices;
- hazard history.

Local ecological knowledge can be transmitted/lost. People can misattribute drought, disease, crop failure or animal decline.

The simulator's environmental state remains privileged objective truth.

## 41. Culture and environment

Environment creates repeated pressures/opportunities from which practices may emerge:
- food preservation;
- architecture;
- seasonal festivals;
- clothing;
- migration routines;
- water law;
- hunting norms;
- crop traditions;
- disaster memory.

Never directly map biome -> culture personality.

## 42. Environmental history and memory

Consequential environmental events should enter ordinary event/history systems:
- great flood;
- multi-year drought;
- catastrophic fire;
- famous winter;
- river change;
- mine exhaustion;
- forest clearing/regrowth.

People/institutions may remember them inaccurately. Later historians/archaeologists can reconstruct them from records and physical traces.

The environment creates facts; culture creates meanings.

## 43. Landscapes as provenance

Places accumulate history.

A landscape may preserve traces of:
- old roads;
- abandoned farms;
- ruins;
- mines;
- cleared forest;
- battle damage;
- graves;
- irrigation;
- former settlements.

Do not store every visual detail. Preserve consequential modifications/provenance sufficient for later reconstruction and focused rendering.

## 44. Abandonment and rewilding

When human use stops, infrastructure and ecology evolve:
- buildings decay;
- roads degrade;
- fields succeed to vegetation;
- wildlife returns/changes;
- mines flood/collapse;
- records/objects remain/loss depends on storage.

Use time-since-abandonment analytic/lazy reconstruction where possible.

## 45. Extinction and local extirpation

Species/populations can disappear locally or globally if causal pressures support it.

Drivers:
- habitat loss;
- overharvest;
- climate shift;
- disease;
- predation/competition;
- catastrophe;
- magical threats where canonical.

Do not force extinction for drama. Recovery/recolonization may occur if populations/routes remain.

## 46. Environmental conservation

Conservation behavior can emerge without a modern environmental ideology flag.

People/institutions may restrict use because of:
- declining yields;
- property interests;
- sacred/cultural practice;
- hunting privilege;
- long-term planning;
- observed erosion/flooding;
- scientific/ecological knowledge;
- institutional regulation.

The same rule can be motivated differently by different people.

## 47. Catastrophe scale

Environmental events should have spatial footprints and intensity.

Possible resolution:
- site/local;
- settlement/catchment;
- regional;
- multi-region exceptional event.

Most events should be local/regional. World-wide catastrophe requires explicit world/cosmology canon rather than random drama generation.

## 48. Event-driven environmental scheduler

Environmental computation should be organized around next meaningful changes rather than annual full-world loops where possible.

Examples:
- drought anomaly begins/ends;
- crop season resolves;
- wildfire ignites/resolves;
- wildlife population queried after N years -> analytic advance from last update;
- mine extraction changes stock;
- abandoned field queried -> succession reconstructed from elapsed time;
- flood event touches indexed downstream exposed locations.

Each environmental entity/state should ideally carry `last_updated` and enough parameters to advance lazily.

## 49. Analytic/lazy evolution

Prefer closed-form/bounded-step evolution for slow systems.

Examples:
- forest regrowth from time since disturbance;
- resource depletion only on extraction;
- infrastructure-independent soil recovery over elapsed fallow time;
- wildlife carrying-capacity approach over elapsed years;
- contamination decay where simple model is sufficient.

Do not iterate 300 unchanged years when the same state can be computed from elapsed time.

## 50. Active-set architecture

Only environmental units with meaningful current interaction need frequent updates.

Active triggers include:
- nearby settlement/farm/extraction;
- disaster/anomaly;
- migration/threat movement;
- player/focused simulation;
- current institutional project;
- significant ecological imbalance.

Dormant remote regions remain represented but update lazily on access/event.

## 51. Sparse fan-out

Environmental events affect indexed exposure sets.

Examples:
- flood -> downstream floodplain sites;
- fire -> neighboring fuel-connected areas;
- drought -> region/catchment;
- storm -> footprint;
- predator/threat migration -> adjacent suitable habitat.

No event should scan every settlement/person/location unless it is genuinely world-scale.

## 52. Resolution degradation under budget

If environmental workload grows unexpectedly, deterministic degradation strategies may include:
- merge adjacent low-activity cells into regional aggregate updates;
- increase update intervals for dormant populations;
- aggregate minor weather into seasonal indices;
- suppress individuation of non-consequential animals/sites;
- combine low-salience disturbances;
- delay non-causal visual reconstruction until queried.

Degradation must be deterministic and preserve significant causal events.

Never silently drop famine, settlement destruction, extinction, major resource exhaustion or other consequences merely to hit runtime.

## 53. Diagnostics

Millennium diagnostics should summarize enough ecology to detect dead/runaway systems without expensive full dumps:
- climate anomalies by region;
- cultivated area/productivity;
- forest/vegetation cover trends;
- key wildlife/threat populations;
- water stress;
- resource extraction/depletion;
- major disasters;
- abandoned/recovered land;
- environmental contribution to migration/food shortage;
- active versus dormant spatial units;
- environment runtime share.

Diagnostics are read-only summaries, not causal inputs.

## 54. Determinism

All stochastic environmental history uses isolated namespaced RNG.

Candidate namespaces may include:
- `climate_anomaly`;
- `severe_weather`;
- `wildfire_ignition`;
- `wildlife_population`;
- `crop_environment`;
- `geologic_hazard`.

Exact namespaces freeze at implementation.

Unrelated new systems should not perturb environmental outcomes where RNG isolation can prevent it.

## 55. Behavioral acceptance scenarios

1. Two identical seeds/configs produce identical environmental history/digest.
2. Same World Seed with different History Seed begins with identical geography/resources/climate normals and diverges in realized environmental history.
3. A remote untouched forest can advance centuries without yearly simulation.
4. Clearing a forest changes timber/habitat/erosion state and later regrowth occurs causally after abandonment.
5. A multi-year drought reduces water/crop/wildlife productivity without directly issuing migration/famine events.
6. A poor harvest does not cause famine when stores/imports/institutions compensate.
7. The same harvest failure causes severe hunger where those buffers are absent.
8. Flood affects downstream exposed locations without scanning the entire world.
9. A mineral deposit can exist objectively for centuries while remaining unknown to civilization.
10. Extraction depletes a deposit only through actual use.
11. Wildlife declines under sustained overharvest and can recover when pressure falls/habitat remains.
12. Individual wildlife is not simulated until a focused interaction requires it.
13. Settlement expansion can disturb threat habitat and alter encounter pressure through existing threat ecology.
14. A settlement can persist on environmentally mediocre land because infrastructure/history/trade compensate.
15. An environmentally excellent location remains unsettled if people lack knowledge/access/incentive.
16. Environmental pressure influences migration through Agency rather than moving population directly.
17. Fire severity changes with fuel/moisture/wind and response capacity.
18. A great fire leaves material/institutional/ecological consequences and later landscape recovery.
19. Abandoned farmland rewilds through elapsed-time reconstruction rather than annual ticks.
20. A civilization loses accurate knowledge of an old drought while physical/archaeological evidence remains.
21. Different cultures respond differently to similar environments because practices/history differ.
22. No biome automatically generates a personality/culture tag.
23. Environment integration preserves canonical ranked threat and magic progression invariants.
24. Environmental additions do not materially compromise the frozen millennium performance baseline.
25. No ecology PR is accepted solely because total runtime remains under 120 seconds if its marginal cost is disproportionate.

## 56. Open design questions

Not yet frozen:
- exact hierarchical map/cell representation;
- world dimensions/scale;
- biome taxonomy;
- climate normal generation;
- seasonal phase granularity;
- hydrology detail;
- soil dimensions;
- wildlife species versus functional-group taxonomy;
- agriculture crop/livestock catalog;
- disease ecology depth;
- pollution categories;
- environmental trace persistence for archaeology;
- natural resource regeneration/deposit rules;
- exact environment runtime budget after Stage 0.5 gold baseline is frozen;
- deterministic resolution-degradation thresholds;
- player-facing focused weather/ecology resolution;
- magical ecology pending objective cosmology.

Coding agents must not invent these answers merely to finish an interface.

## 57. Implementation sequencing

1. Stage 0.5: stabilize current simulation and freeze exact gold performance/determinism baseline.
2. Post-baseline audit: map existing geography, economy, agriculture, development, infrastructure and threat-ecology authorities to this model; do not duplicate them.
3. Environment A: static geography/hierarchical spatial indexes and climate normals, generated once.
4. Environment B: cheap seasonal/climate anomalies, water/soil/productivity interfaces.
5. Environment C: vegetation/wildlife/resources using lazy analytic state.
6. Environment D: agriculture/environment feedback and food-shortage causality.
7. Environment E: bounded disasters/fire/flood/drought and exposure fan-out.
8. Environment F: human land use, degradation, abandonment/recovery and landscape provenance.
9. Environment G: threat-ecology integration and calibration.
10. After every step: deterministic 100/500/1,000-year benchmark against frozen baseline; reject/rework disproportionate runtime growth.
11. Player-facing focused ecology/weather can later reconstruct detail from the same authoritative aggregate state.
12. Magical ecology waits for objective cosmology.

Until the relevant stage opens, this document is design authority—not permission to code ahead.

**Environmental principle:** simulate the consequence, preserve the cause, and never spend a thousand years calculating scenery that did not change history.
