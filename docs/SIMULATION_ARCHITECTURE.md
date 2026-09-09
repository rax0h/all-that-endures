# Simulation Architecture

## Status

The executable simulation currently in `simulation/` is a stable foundation, not the finished world simulation. The architecture below is the target being built outward from that foundation.

The central product is not any individual subsystem:

> **The interaction graph is the product.**

## Four interpretive layers

### Reality
Objective physical/causal state: people, bodies, geography, ecology, objects, construction, travel, combat, disasters and what actually occurred.

### Society
How intelligent beings organize around Reality: households, relationships, organizations, politics, law, economy, culture, religion, institutions and reputation.

### Knowledge
What anyone believes or can establish about Reality: perception, memory, testimony, records, rumor, scholarship, archaeology, secrets and contested interpretation.

### Narrative
A read-only-with-respect-to-history layer that identifies unresolved pressure, motives, mysteries, obligations, journeys and opportunities for player agency. Narrative cannot manufacture objective history.

## World Causality Graph

Every meaningful persistent node should be connected to causes and consequences at an appropriate resolution. Nodes include people, households, dynasties, organizations, settlements, buildings, roads, artifacts, laws, techniques, traditions, memories, recordings, names, ecological changes and events.

Example:

`mine discovery <- expedition <- merchant financing`

`mine discovery -> resource conflict -> invasion -> destroyed city -> refugee migration -> community memory -> cultural practice -> festival`

Causal structure also drives relevance scaling. Detail may be promoted around something that later becomes important without rewriting its past.

## Persistent identity and continuity

Persistent entities retain identity through time. A six-thousand-year-old person must possess six thousand years of actual simulated continuity at an appropriate resolution, not a biography paragraph generated at the moment they become relevant. Objects, buildings, organizations and traditions follow the same principle.

## Resolution and relevance

Not every entity needs maximal detail every tick. Resolution can range from coarse causally equivalent state to fully explicit local simulation. Compression is legal only when it preserves outcomes relevant to downstream causality. Average-output aggregation that destroys identity, ownership, genealogy or causal provenance is not acceptable where those facts can matter.

**Player relevance may determine resolution, never probability.**

## Domain map

### 1. Individuals
Birth/death/age, rank history, abilities/Essences, personality, desires/fears, skills, relationships, family, possessions, wealth, occupation, education, reputation, loyalties, beliefs, memories, knowledge, injuries/scars, residences, travel, organizations, promises/debts, accomplishments/failures and continuity.

### 2. Rank ecology and ontology
Rank changes lifespan, cognition, perception, travel, labor, wealth, politics, warfare, status, family, architecture, law, economics, memory, physiology and magical sustenance. Consequences must be centralized rather than independently guessed by subsystems.

### 3. Population and demography
Births, deaths, fertility, mortality shocks, age structure, migration, marriage customs, inheritance, households, urbanization, collapse/recovery and rank-dependent longevity.

### 4. Genealogy and dynasties
Actual parent/child, partnership/marriage, adoption, branch, house/cadet-house and succession graphs.

### 5. Relationships and social networks
Friendship, rivalry, mentorship, romance, marriage, hatred, gratitude, obligation, jealousy, admiration, fear, patronage and shared history.

### 6. Organizations
Guilds, governments, armies, religions, schools, businesses, criminal groups, scholars, banks, mercenaries, factions and secret societies: founding, membership, leadership, assets, ideology, internal politics, splits, mergers and collapse.

### 7. Politics
Territory, governance, legitimacy, taxation, offices, succession, diplomacy, treaties, rebellion, annexation, coups and federation. Political maps emerge from history.

### 8. Law and justice
Culturally/historically grounded law, crime, investigation, trial, punishment and precedent. Law is distinct from raw power.

### 9. Economy
Resources -> extraction -> production -> labor -> transport -> markets -> ownership -> consumption -> investment. Historical change physically changes economic possibilities.

### 10. Material provenance
Source -> maker -> owner -> transfer -> modification -> loss -> burial -> discovery. Transformation preserves genealogy; consumption preserves terminal history.

### 11. Geography and landscape history
Rivers migrate, forests change, land is cleared, roads appear/vanish, mines expand, settlements bury predecessors, coasts and battlefields change.

### 12. Built environment
Buildings/sites preserve construction, purpose, renovation, damage, ownership, rebuilding, abandonment and reuse.

### 13. Naming and language
Names mutate, languages split, pronunciation shifts, spellings change, political renames happen and old forms persist in old speakers/records.

### 14. Culture
Food, clothing, architecture, manners, funerals, courtship, hospitality, music, art, humor, taboo, family custom, attitudes to rank/magic, holidays and geographic diffusion.

### 15. Religion, philosophy and mythology
Beliefs evolve through movements, splits, saints/heroes, mythologization, merging, reform and institutionalization. Evidence can contradict sacred narratives without mechanically settling faith.

### 16. Information propagation
Events are not globally known. Information moves through witnesses, travelers, messages, institutions, rumor and rank-dependent communication.

### 17. Perception
Objective event is distinct from observer-accessible information. Rank, position, attention, sensory limits and conditions affect what can be perceived.

### 18. Recording technology and magic
Recordings have resolution, cost, alteration/copy/destruction/authentication constraints and become historical artifacts themselves.

### 19. Memory
Individual, collective and recorded memory can disagree, decay and distort. High rank does not imply perfect recall unless canon explicitly says so.

### 20. Knowledge and scholarship
Historians, archaeologists and scholars gather evidence, hypothesize, publish, argue and revise. Player discoveries can alter scholarship, education and future belief.

### 21. Archaeology
Stratigraphy, preservation, disturbance, excavation, provenance, dating, interpretation, looting, museums/private collections, forgery, black markets, disputes and negative evidence.

### 22. Warfare
Cause -> mobilization -> logistics -> command -> campaigns -> battles -> casualties/destruction -> occupation -> treaty -> aftermath. Rank changes doctrine.

### 23. Technology, technique and knowledge progression
Discovery, spread, secrecy, monopoly, improvement, forgetting and rediscovery across mundane and magical knowledge.

### 24. Ecology
Populations, habitats, predators, hunting, magical creatures and ecosystem interaction. Human/magical history can leave ecological consequences.

### 25. Disasters and environmental shocks
Fire, flood, drought, earthquake, disease and magical/environmental events are processes with propagated consequences, never isolated event cards.

### 26. Travel and logistics
Actual travel time and capacity affect trade, information, relationships, warfare and migration. Rank changes experienced geography.

### 27. Space/off-world geography
Reserved for canon-permitted high-rank expansion: orbital estates/refuges/vaults/routes, jurisdiction, construction, battles, artifacts and archaeology.

### 28. Reputation and fame
Reputation is distinct from objective significance and varies by culture/community: hero, monster, recluse, protector, fraud, saint, tyrant and so on.

### 29. Secrets
Truth -> witnesses/evidence -> secrecy -> cover story/public account -> suppression/concealment/discovery.

### 30. Counterfactual pressure
Preserve consequential near misses selectively: almost-ascensions, failed assassinations, cities nearly falling and similar pressures that affect personal/institutional history. Do not create alternate universes.

### 31. Player historical agency
The player remains inside simulation rules and can become a relationship, enemy, ancestor, organization member/founder, business owner, discoverer, criminal, archaeological cause, famous owner, recorded combatant or cultural memory.

### 32. Narrative emergence, lore and adventure
Consumes world state to identify unresolved conflicts, mysteries, journeys, obligations, ambitions, tragedies, transformations, dangerous knowledge, lost places and intervention opportunities.

Quest pressure is:

`current world pressure + motivated actors + causal history + incomplete knowledge + possible player agency`

not a retrieve/kill quest template that invents facts.

### 33. Cognition, creativity and intellectual life
Intelligence is multidimensional: abstraction, memory, verbal/spatial ability, social perception, pattern recognition, imagination, attention, introspection, processing speed, judgment, curiosity and creativity may vary independently.

Creative practice has continuity: aptitude, temperament, influences, teachers, access, habits, failures, obsessions, technical knowledge and accumulated work. The hundredth poem is downstream of the previous ninety-nine.

Model inspiration as latent integration rather than a random creativity bonus:

`exposure -> knowledge -> experience -> practice -> latent associations -> receptivity -> insight -> recognition -> execution -> work -> reception -> influence`

A person may interpret insight as muse, divinity, Essence, dream or subconscious process. The simulation need not settle metaphysics. Receiving an idea is distinct from possessing the skill to realize it.

Works preserve provenance: creator, development/drafts where relevant, influences, circumstances, technique/materials, reception, criticism, copying/performance/translation, censorship, rediscovery and later influence.

Philosophy emerges from actual problems and reasoning around mortality, longevity, inequality, suffering, obligation, consciousness, identity, memory, power, magic, family, beauty, death and transcendence rather than selection from a fixed philosophy list.

### 34. Embodied mind and human condition
Thought is embodied. Hunger, pain, exhaustion, cold, heat, illness, comfort, touch, sleep, attraction, safety and bodily change affect attention and decisions.

Relationships are not single emotion meters. Track conditions such as attachment, trust, intimacy, attraction, admiration, dependence, resentment, gratitude, obligation, familiarity and shared history. Love, grief, jealousy, longing and sacrifice emerge from interacting conditions and current circumstances.

Distinguish temperament, emotional state, mood, attachment and formative experience. Conflicting emotions are valid. People may feel emotions about their emotions.

Impulse and inhibition vary with fatigue, anger, attraction, intoxication, humiliation, excitement, boredom, curiosity, desperation and individual disposition. People can knowingly act against long-term interests and later regret it.

Psychological variation and disorder must be represented carefully rather than as cartoon traits. Subjective experience can be compelling while differing from objective Reality. Depression-like states, mania-like states, anxiety, trauma, compulsions, addiction, cognitive decline and disordered grief can affect life without reducing a person to a diagnosis. Magic does not automatically cure every organization/function of mind.

Dialogue/content realization must derive from the person, motive, relationship, perception, memory, beliefs/claims, culture, role and immediate context. Avoid universal eloquence, complete self-awareness and interchangeable polished voices.

### 35. Climate, seasons and weather

`climate -> seasons -> weather systems -> local conditions -> physical consequences -> human experience`

Weather affects roads, rivers, ships, crops, visibility, travel, warfare, buildings, fire, communication, ecology, markets and personal life. Drought and flood propagate through physical and social systems rather than appearing as event cards.

Example drought chain:

`rainfall deficit -> soil moisture -> crop yield -> food supply -> prices -> nutrition/livestock -> debt/crime/migration -> political pressure/unrest -> disease vulnerability -> abandoned land -> ecology -> culture/memory`

## Shared primitive: World Pressure

World Pressure represents states that create incentives, constraints and risk: scarcity, abundance, danger, attraction, disease, grief, hunger, opportunity, population pressure, debt, instability, ecological imbalance, loneliness, fear, status competition, drought, flood, war, persecution, technological disruption and monster activity.

Pressure propagates through the interaction graph. The same pressure produces different responses because individuals, settlements and institutions have different histories and states.

## Preparedness and path dependence

Catastrophe outcome depends on accumulated state, conceptually:

`hazard × exposure × vulnerability × preparedness × response × circumstance`

Preparedness itself has history. Walls, reserves, healers, roads, evacuation plans, laws, alliances, monster knowledge and military experience exist because earlier people made decisions under uncertainty and accepted opportunity costs.

A town that funded irrigation rather than walls was not necessarily foolish. A later monster surge can make that old tradeoff consequential. A decision in year 143 can alter possibilities in year 2,800.

## Narrative quality

Great story is not a content table. Story emerges from desire, conflict, sacrifice, consequence, reversal, loyalty, betrayal, inheritance, exile, return, discovery, taboo, loss, obsession, duty, ambition and tension between belief and truth.

Heroic/mythic structures may be recognized as affordances after causal conditions exist; they are never mandatory templates imposed on Reality.

Legendary places and objects accumulate significance because real events, memories, uses, losses, rediscoveries and reinterpretations attach to them.

## Stress tests

The architecture should eventually survive at least these classes of tests:

1. Similar monster surges strike independently evolved settlements; preparedness/history produces materially different outcomes.
2. The same family tragedy produces different but traceable individual responses.
3. Drought propagates through ecology, economy, household life, migration, politics and memory.
4. Flood physically changes routes/buildings/land use and later archaeology.
5. A peaceful century remains causally rich without forced catastrophe.
6. A mundane object becomes historically significant centuries later and its full provenance can be promoted.
7. A false legend becomes culturally powerful without overwriting objective history.
8. A player discovery changes scholarship and later education/belief.
9. A high-rank person's ancient relationships and experiences remain actual continuity rather than generated backstory.
10. A creator's mature work is demonstrably downstream of training, influences, earlier work and lived experience.
11. Two similar settlements make different rational investments under uncertainty and later experience different disaster severity.
12. A rank transition changes physiology, needs, medicine, appearance and social consequences consistently across domains.

## Constitutional tests

A subsystem is architecturally wrong if it needs to invent a causal past that should already exist, biases objective events toward player entertainment, erases persistent identity for convenience, gives every NPC the same polished voice, treats disasters as isolated cards, or treats rank as a stat multiplier when its ontological consequences are relevant.