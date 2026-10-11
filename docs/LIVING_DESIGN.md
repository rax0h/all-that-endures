# ALL THAT ENDURES — Living Design Document

**Status:** Living design authority for new simulation direction.  
**Last cohesive update:** 2026-10-11  
**Purpose:** Preserve design decisions as they become coherent. Before replacing an existing system, inspect the repository and extend shared causal primitives where possible.

> **North star:** Not simulated stories. Simulated people whose lives become stories.

ATE should not merely simulate a fantasy setting. It should simulate the processes by which a fantasy civilization becomes a civilization. The world should not know what kind of story it is telling. It should know that people remember, want, believe, choose, act, succeed or fail, change, influence others, build things, form institutions, preserve or lose knowledge, and eventually die.

## 1. Non-negotiable simulation constraints

- Preserve a causally rich 1,000-year simulation. The benchmark target remains <=120 seconds; optimization must not gut history, ecology, lineages, economy, magic, or social causality.
- Prefer persistent hot-state indexes and bounded/event-driven work over repeated archive scans.
- Systems establish possibilities. People and circumstances produce outcomes. Do not manufacture outcomes because a story needs them.
- Truth exists globally, but knowledge exists locally.
- The player is another causal actor inside the same world. NPCs are not props orbiting the player.

## 2. Canonical magic progression

**Owner-confirmed canonical Essence-rank progression (2026-10-11; supersedes the older twenty-before-Iron rule):**

- **No Confluence = unranked.** A person holding zero, one, or two base Essences has not attained Iron rank, even if one or two innate abilities are awakened. They may have magic without having a complete Essence path.
- **Confluence = Iron.** Acquiring a third base Essence automatically produces the fourth, the **Confluence Essence**. This is the transition to **Iron rank**, **without** requiring all twenty abilities first.
- Each absorbed base Essence awakens its one innate ability; the Confluence produces one innate ability of its own. An ordinary newly confluenced Iron has **4 of 20 abilities awakened**: one under each of the four Essences. The remaining sixteen are gained through awakening stones and actual in-world access, not given automatically on reaching Iron.
- **Bronze gate:** An overall Essence user may become **Bronze only once all twenty abilities exist and all twenty have individually advanced to the Bronze threshold**. An ability may reach Bronze individually while its owner remains Iron; newly awakened Iron abilities still block whole-person promotion until they catch up. The same all-twenty qualification applies to subsequent overall rank transitions as defined by the ranked-progression contracts.
- Separate **person rank** from **ability rank**, **Essence completion** from **ability completion**, and **natural magical access** from **ranked magical body/ontology**. Do not infer whole-person Iron status merely because one ability is Iron.

**Known discrepancy to repair later, not during Stage 0.5:** The current advancement runtime and some tests still implement the older/incorrect behavior; see [issue #17](https://github.com/rax0h/all-that-endures/issues/17) and Section 57. This document now records the **intended design**, not a claim that current code, checkpoints or test oracles already implement it.

**Historical, not re-certified under the corrected rule:** The accepted PR #5 benchmark (91.55 seconds, 15 completed twenty-ability paths recorded as ranked under that source's definition: 1 Iron, 2 Bronze, 3 Silver, 6 Gold, 3 Diamond; 47 incomplete paths rank 0) must retain its original meaning and reproducibility. Do **not** silently reinterpret its counts or change deterministic baselines. Future recalibration should measure the population distribution under corrected rank semantics, including Iron users with only four or more abilities.

### Four mastery stages inside every rank

Do not rebalance the established time-to-rank curve merely to add visible progression. Divide each existing per-skill rank interval into four equal stages.

- Each of the twenty skills independently occupies Stage 1, 2, 3, or 4, with 0.0–100.0% progress through that stage.
- Stage 1 = first 25% of the existing rank interval; Stage 2 = 25–50%; Stage 3 = 50–75%; Stage 4 = 75–100%.
- `Iron 3 — 0.0%` means that skill is halfway from Iron to Bronze.
- Crossing Stage 4 at completion advances that skill to Stage 1 at 0.0% of the next rank.
- Example: `Hand of the Reaper — Silver 3 — 45.0%`.
- **Iron entry is the exception:** Confluence creates Iron with four innate abilities; **Bronze and later overall rank advancement** are gated by all twenty abilities existing and meeting the required next-rank threshold.

This is a resolution/state/display refinement, not a pacing rewrite.

## 3. Seeds, alternate histories, and replay

ATE should preserve deterministic replay for engineering without requiring every fresh run of the same starting world to generate the same history.

- **World Seed:** geography, starting populations, resources, cultures, and other initial conditions.
- **History/Entropy Seed:** stochastic choices/events during history.
- World Seed + History Seed + simulation version/configuration must reproduce the exact timeline for debugging and benchmarking.
- Same World Seed + different History Seed creates an alternate history from the same beginning.
- Replaying a World Seed with different player actions creates new causal inputs and therefore divergence.

The same person can become a feared antagonist in one history and an ordinary respected smith, parent, or friend in another because the turning incident never occurs or because relationships and circumstances differ.

## 4. Human Psyche / Agency

Do not generate leaders, villains, hermits, heroes, criminals, or adventurers as preset character types. Generate people rich enough that those identities emerge.

**Core loop:** Temperament -> Values -> Needs/Drives -> Beliefs -> Memories -> Relationships -> Situation/Opportunity -> Decision -> Consequence -> updated person/world.

### Temperament

Use continuous foundational traits rather than rigid personality labels. Possible dimensions include sociability, empathy, assertiveness, conscientiousness, openness, risk tolerance, aggression, patience, trust, ambition, competitiveness, independence, emotional volatility, curiosity, sensitivity to status, and sensitivity to injustice. Keep the set disciplined (~15–20). Temperament is relatively stable and may be partially heritable; it is not morality.

### Values, drives, beliefs, self-concept

- **Values:** family, freedom, duty, wealth, status, knowledge, community, faith, justice, tradition, achievement, pleasure, security, power, craftsmanship, exploration, legacy, etc. Values can change.
- **Drives:** current pressures such as belonging, recognition, autonomy, revenge, romance, mastery, purpose, rest, safety, status, wealth.
- **Beliefs:** what a person thinks is true, including confidence and source: observation, trusted person, rumor, institution, family story, inference. Beliefs can be false.
- **Self-concept:** beliefs about oneself — brave, protector, scholar, failure, honorable, independent, etc. Contradictory experiences can create cognitive dissonance.

### Memory

Store significant episodic memories rather than every mundane event. Memories should carry associated people/places, emotional intensity, interpretation, and relevant emotions. They may decay, be reinforced, become formative, or be transmitted as family/community stories.

Descendants can inherit grievances and loyalties about events they never witnessed. History therefore has teeth without omniscience.

### Relationships

Relationships are multidimensional: affection, trust, respect, fear, attraction, resentment, obligation, familiarity/history. A person can love, distrust, respect, fear, and resent the same person simultaneously.

Different interactions change different dimensions. Fighting beside someone is not the same as drinking together; teaching can build respect; keeping a secret builds trust; saving a life may create obligation without affection.

### Goals and decisions

Characters maintain a small bounded set of current goals rather than evaluating every possible action continuously. Available actions arise from goals, knowledge, circumstances, resources, relationships, and opportunities.

Agency evaluates plausible actions using temperament, values, drives/emotions, beliefs, relationships, expected consequences, capability, opportunity, and bounded rationality. People can be impulsive, mistaken, frightened, angry, habitual, sacrificial, principled, or irrational.

Use weighted stochastic choice where appropriate. The psyche shapes the probability landscape; history entropy resolves among genuinely plausible actions. Preference is not outcome.

### Development and arcs

Separate relatively stable temperament from mutable character/worldview. Children do not spawn with completed adult psyches. Family, class, culture, education, mentors, love, neglect, loss, success, failure, magic, and history shape adults.

Do not script arcs. A historian may later recognize redemption, fall from grace, radicalization, reconciliation, withdrawal, revenge, corruption, recovery, etc., but the simulation never calls `begin_redemption_arc()`.

Redemption does not erase consequences. Most lives should remain ordinary enough for extraordinary lives to mean something.

## 5. Performance model for agency

Use depth on demand.

1. **Background state:** slow-changing temperament, values, worldview, long-term ambitions, relationships, magical aspirations.
2. **Active state:** current concerns/goals, reconsidered periodically or when circumstances change.
3. **Event reaction:** deeper immediate evaluation after significant events — death, attack, betrayal, inheritance, magical opportunity, childbirth, humiliation, disaster, etc.

Most people cost little most of the time. Something happens, then they think.

## 6. Magic as an expression of the person

Personality, values, goals, family tradition, mentors, prestige, safety, utility, healing, control, wealth potential, and curiosity influence what magical identity a person wants. Actual opportunity is constrained by availability, wealth, knowledge, relationships, Society access, luck, and the essence/stone economy.

**Personality produces preference. Circumstance produces opportunity. Preference != outcome.**

## 7. Conflict, villains, redemption, and falls

Do not build a villain system. Build conflict, grievance, memory, motive, power, reputation, and escalation.

Conflict can emerge from scarcity, humiliation, bereavement, debt, romance, political exclusion, monster attacks, discrimination, rivalry, inheritance, wealth shifts, magic, fear, ideology/religion, territory, class resentment, revenge, and betrayal.

Escalation can move through avoidance -> argument -> restitution demand -> gossip/reputation damage -> arbitration -> economic retaliation -> threats -> sabotage -> assault -> murder -> organized retaliation -> open conflict. Most disputes should stop early. Some become feuds, wars, or institutions.

Power determines reach. A vindictive Iron cobbler can ruin a neighbor; a vindictive Diamond can alter a continent. Long-lived Gold/Diamond people can carry loyalties and grudges across ordinary generations.

## 8. Truth, information, evidence, and investigation

> **Truth exists globally; knowledge exists locally; evidence is the bridge between them.**

Events leave causal traces: bodies, wounds, possessions, witnesses, travel history, purchases, magical residue, relationships, last-known plans, property transfers, and more.

Witnesses hold beliefs and memories, not perfect transcripts. They may be mistaken, biased, loyal, frightened, bribed, or lying. Investigators gather testimony, inspect evidence, compare accounts, use applicable skills/magic, and form uncertain beliefs. They can be wrong. Innocent people can be framed. Corrupt officials can suppress truth. Old cases can reopen decades later.

Magic can assist investigation — tracking, aura residue, enhanced senses, memory/corpse/divination-like abilities — but should not collapse into a universal `detect murderer` button.

## 9. Rumor, secrets, and reputation

Information propagates through observation, family, friends, travelers, merchants, organizations, proclamations, religion, and rumor. Transmission can distort facts; competing histories can coexist.

Secrets are true information someone actively wants restricted: crimes, affairs, parentage, hidden wealth, forbidden magic, political plans, betrayals. Secrets can be protected, leaked, traded, blackmailed, accidentally revealed, or taken to the grave.

Reputation is observer/group-relative, never one universal score. People are known *for things*: keeping confidences, protecting civilians, honoring contracts, being violent when challenged, accepting bribes, abandoning companions, excellent monster hunting, etc. Different groups value the same conduct differently.

## 10. Friendship, groups, leadership, and organizations

Groups require relationships. Avoid frictionless `CREATE GUILD` abstractions.

People must sometimes socialize for no instrumental reason: dinner, drinking, hunting, games, festivals, conversation, visiting family, celebration. Those apparently useless interactions create the relationships that later matter.

Group formation exposes interpersonal friction. The best healer may not trust the founder; two strong members may hate each other; a parent may refuse long expeditions. Leadership emerges from competence, temperament, trust, legitimacy, relationships, and circumstances. Founding a group does not guarantee being its natural leader.

Organizations can outlive founders and acquire property, traditions, enemies, internal factions, institutional interests, and reputations distinct from members.

## 11. Adventure Society star rank

Star rank measures demonstrated trust, judgment, and operational responsibility — not raw magical power. A Diamond can be a poor 1-star adventurer; an experienced Silver can be an exceptional 3-star.

A true 3-star understands not only the immediate job but its ramifications: politics, families, property, collateral damage, information sensitivity, downstream conflict, and when solving the immediate problem creates a larger one.

Contracts should have objectives, not designer-approved answers.

## 12. Dependence, families, class, politics, and social power

Power emerges from dependency networks: employment, land, debt, mentorship, supply chains, healing, education, introductions, marriage, family ties, institutional roles, magical strength, and old favors.

Rich/powerful families can become dynasties through property, marriage, institutional influence, magic, reputation, and inherited relationships. The player can become politically associated with a family or faction through conduct without selecting a faction menu.

Social class is not identical to wealth. Old money, new money, respected poor surnames, craftspeople, merchants, laborers, adventurers, scholars, nobles/religious classes where applicable, and rural/urban identities create different social positions. Inequality, inheritance, luck, magic access, connections, and perceived unfairness generate pressure without requiring scripted ideology.

Corruption emerges from competing obligations and dependencies rather than a corruption roll.

## 13. Law, legitimacy, crime, and the underbelly

Law is recognized authority plus enforcement, not merely written rules. Places can regulate property, contracts, violence, inheritance, marriage, trade, debt, magic, and adventuring differently.

Crime emerges where incentives, desperation, opportunity, social networks, and weak legitimate systems make it viable: theft, fraud, smuggling, extortion, protection rackets, banditry, black markets, counterfeiting, corruption, kidnapping, assassination, fencing, etc.

Organized crime emerges when cooperation becomes safer or more profitable. Criminal and legitimate society overlap through relatives, businesses, officials, debt, favors, and dependency.

## 14. Love, marriage, family, and generations

Attraction, love, compatibility, loyalty, and marriage are distinct. People can court, be rejected, marry for love/status/money/security, have affairs, separate, reconcile, become widowed, and remarry.

Most relationships should be ordinary: stable marriages, family dinners, money arguments, raising children, growing old together.

Children inherit environment as well as biology and wealth: parenting, modeled behavior, stories, class, opportunity, education, magical traditions, expectations, and trauma. Family magical traditions emerge through teaching/resources/prestige rather than hard-coded lineage classes. Children can rebel against parental culture, professions, magic, politics, and religion.

## 15. Ordinary life, vice, culture, community, migration

People need humor, affection, favorite foods, teasing, storytelling, celebrations, embarrassment, nostalgia, generosity, grudges, pets, habits, hobbies, and harmless dislikes.

Vice/appetite can include alcohol-equivalents, gambling, intoxicants, status, spending, sex, or risk-taking. The same pressure can produce very different responses in different people.

Community mixing events matter: births, weddings, funerals, markets, festivals, religious observances, competitions, harvests, taverns, public events, neighborhood disputes, children playing.

Culture emerges from repeated local conditions and transmission. **Culture creates pressure, not destiny.** Migration moves people, skills, wealth, genes, culture, religion, rumors, grievances, disease, and magical traditions.

## 16. Education, knowledge transmission, schools, and mentorship

Education must be emergent, not a population-threshold building spawn. A school begins because someone teaches.

Education paths include parents, tutors, apprenticeships, retired adventurers, temples, governments, community-funded teachers, magical masters, academies, guilds, and Society training.

A teacher with six students can become an institution through demand, payment, space, additional teachers, curriculum, records, reputation, and succession. The crucial question is whether it survives its founder.

Some schools last months; others centuries. They can decline, merge, relocate, become obsolete, be destroyed, or be repurposed. They compete for teachers, students, money, property, legitimacy, and prestige. Knowledge can be intentionally withheld; a master dying without a successor can erase techniques from the world.

## 17. Architecture, construction, and historical buildings

Architects/builders emerge through skill, apprenticeship, craft experience, and demand. Major construction follows a causal chain:

**need -> financing -> land -> design -> materials -> labor -> construction -> maintenance**

Buildings can be expanded, damaged, rebuilt, abandoned, repurposed, inherited, or become historically important. An old hall should be old because it was actually built centuries earlier, not because an old texture was selected.

## 18. Gods, religion, and cosmology

ATE may follow the story-inspired premise that gods are objectively real beings, but three layers remain separate:

1. the gods themselves;
2. what mortals believe about them;
3. religious institutions.

The objective cosmology should be deliberately authored before Astra implements the divine layer. A god's existence does not settle theology. Mortals can disagree about what a god wants, whether it deserves worship, death, creation, morality, ritual, and interpretation.

Religions emerge through observation, testimony, interpretation, teaching, gathering, ritual, leadership, property, doctrine, succession, reform, and schism. Multiple religions may interpret the same objectively real being differently.

Gods should possess their own agency, history, relationships, preferences, goals, knowledge, and limitations, but should not simply be immortal humans with larger statistics. Divine politics can exist independently of mortal politics and intersect with it.

The player does not automatically know theological truth.

## 19. Death, one life, resurrection, healing, and training

Current direction: one mortal life by default. Death is final unless an in-world magical mechanism genuinely prevents or reverses it.

Possible exceptions include Phoenix-equivalent resurrection resources/entities, regeneration capable of surviving otherwise mortal damage, or later abilities that genuinely return someone from death. Resurrection is magic, not a UI extra life, and should be rare and consequential.

Healing is strategically/socially important. A healer is a person with needs, fear, family, limits, and agency. Training is preparation rather than grind: abilities, monsters, terrain, equipment, escape, party composition, and knowing when not to fight matter because death has weight.

Doing good does not receive automatic cosmic protection. Relationships remember actual acts. Resurrection does not rewind history: grief, inheritance, remarriage, appointments, rumors, property transfers, and institutional changes remain real.

## 20. Institutional life cycle

Schools, temples, guilds, governments, businesses, Adventure Society chapters, criminal organizations, and similar institutions should share general causal primitives where possible:

- founding cause / unmet need;
- founders and initial relationships;
- resources and property;
- membership/clientele/constituency;
- rules, roles, culture, and knowledge;
- legitimacy and reputation;
- succession;
- competition and alliances;
- growth, stagnation, reform, schism, merger, decline, collapse, or survival.

Nothing gets permanence for free.

## 21. Governance, succession, and bureaucracy

Governance emerges from coordination pressure. As settlements grow, roads, bridges, markets, property disputes, defense, crime, taxation/contributions, records, and communal resources create demand for durable authority.

Authority and raw magical power are separate. A Diamond can physically dominate a town without possessing legitimacy; an elderly Iron can wield enormous authority because everyone trusts her judgment.

Government forms can emerge around councils of families, merchants, elections, temples, protectors, hereditary offices, decentralized arrangements, or hybrids. Legitimacy can derive from tradition, competence, consent, religion, lineage, law, protection, wealth, institutional role, or combinations.

Succession is a real historical problem. A leader's death can produce inheritance, election, compromise, reform, schism, coup, or civil conflict. A successful improvised solution can become tradition and later be remembered as ancient.

Bureaucracy is civilization's connective tissue: clerks, archivists, judges, tax collectors, surveyors, inspectors, messengers, administrators, registrars, and other specialists.

## 22. Institutional memory and records

ATE distinguishes human memory from institutional memory. People remember experiences and stories; institutions preserve records. Governments, schools, religions, guilds, families, and the Adventure Society can therefore preserve different and contradictory histories.

Records may include births, deaths, marriages, property deeds, contracts, criminal cases, taxes, censuses, enrollment, membership, Society reports, construction plans, judgments, and correspondence.

Records can be incomplete, biased, forged, hidden, censored, misfiled, destroyed, copied, translated, rediscovered, or preserved for centuries. Their existence and quality affect what later investigators, scholars, officials, and players can know.

Historical consensus can change when new evidence appears. The event does not change; society's understanding of it does.

## 23. Ideas, knowledge, scholarship, art, and cultural transmission

ATE should simulate the processes by which civilization creates and preserves ideas rather than assigning a settlement `technology_level` or a shallow culture tag.

Knowledge begins with people. A person can discover, infer, teach, demonstrate, write, conceal, misunderstand, improve, combine, forget, or die with knowledge.

Inventions have actual inventors and causal precursors. Techniques spread through teaching, migration, books, apprenticeships, institutions, trade, imitation, conquest, or espionage.

Use bounded information objects rather than attempting to generate every sentence of every book. Useful fields include creator, subject/meaning tags, prerequisites, provenance, accuracy, accessibility, prestige, transmission history, mutations/variants, and associated institutions.

Scholarship permits disagreement, criticism, competing theories, rediscovery, and correction. Art — songs, stories, paintings, monuments, performances, sayings, folklore — preserves and transforms culture and history. Folklore can become mythology; mythology can be mistaken for history; real history can be dismissed as mythology.

Language should have architectural room for long-horizon cultural drift, borrowed words, sayings, names, terminology, and historical expressions without requiring a full linguistic simulation immediately.

> **The lore is not written before the simulation. The simulation creates the past, and the past becomes the lore.**

## 24. Existing provenance as the material-history backbone

ATE already has provenance concepts. Do **not** create a parallel historical-artifact system. Inspect and extend the existing machinery.

Ordinary crafted objects can become historically important through ownership, use, location, association with events, inheritance, or later interpretation. A mundane sword can become culturally priceless because somebody important carried it.

Existing maker/material/ownership/transfer/use history should connect where appropriate to records, beliefs, scholarship, reputation, archaeology, inheritance, theft, collections, religion, and cultural memory. Buildings likewise accumulate histories through architects, patrons, construction phases, repairs, fires, owners, occupants, and events.

**Do not generate relics. Let objects become relics.**

## 25. Archaeology, loss, rediscovery, and reinterpretation

Material and documentary history should make archaeology possible without a bespoke quest system. Settlements disappear, roads are abandoned, buildings collapse, archives burn, and graves, ruins, battlefields, buried objects, foundations, copies, and fragments remain.

Lost techniques, works, records, and objects can be rediscovered. Discovery is a new event that changes knowledge and beliefs. It can rehabilitate a reputation, reopen a crime, alter a religious interpretation, expose a lineage claim, or revive forgotten knowledge.

## 26. Innovation and civilizational change

The world at Year 1000 should be capable of becoming a genuinely different civilization from Year 0. Avoid a rigid Civilization-style technology tree as the primary model.

Innovation emerges when people encounter problems, possess relevant knowledge/resources, experiment, imitate, combine techniques, make mistakes, and occasionally discover something new. Institutions can accelerate, suppress, monopolize, standardize, preserve, or lose innovation. Knowledge can regress when transmission networks collapse.

## 27. Combat as a temporal causal process

Rank disparity should be enormous without becoming an absolute prohibition. An Iron surviving or even killing a Silver-level threat should be extraordinary and causally explainable, not evidence that Iron and Silver are normally comparable.

Combat is not `power A vs power B -> winner`. It unfolds through time: positioning, ability interactions, terrain, objectives, injury, endurance, resources, morale, escape routes, allies, arrival times, healing, and chance.

A weaker combatant may be trying to survive until allies arrive, delay an enemy, protect someone, reach terrain, escape, or keep an opponent occupied rather than defeat it immediately.

Most severely mismatched encounters should end as the disparity suggests. Rare upsets become historically notable because the simulation can explain exactly how they happened. Do not manufacture them for drama.

## 28. Injury, survivability windows, healing, and rescue

Healing is not instantaneous rescue from arbitrary damage. A critically injured person must remain viable long enough for healing to repair them.

- Distinguish damage severity from immediate death, remaining survivability, and healing rate/effectiveness.
- Resilience, regeneration, unusual physiology, rank, defensive abilities, and special conditions can extend the survival window without directly healing the wound.
- External healing matters only if it arrives and acts before that window closes.
- Companions matter temporally: allies can return in time, extract someone, stabilize the fight, protect a healer, or simply buy the seconds required for healing to work.
- Two people with the same wound may have different survival windows because of physiology, rank, abilities, exhaustion, prior injuries, or other conditions.

This reinforces one-life play: sometimes the difference between a legendary survival and a dead character is whether friends make it back in time.

## 29. Civilization loop

**Person -> idea -> creation -> transmission -> institution -> tradition -> history -> loss -> discovery -> reinterpretation -> new idea.**

This joins Agency to institutions, records, provenance, scholarship, material culture, archaeology, and civilizational change.

## 30. Core architectural rule

Every major human decision should ultimately pass through one Agency interface. Downstream systems determine what is possible; Agency determines what this person attempts; the world resolves what actually happens.

- Economy: these jobs/resources are available.
- Magic: these essences/stones/training opportunities are available.
- Society: these organizations will accept/reject you.
- Relationships: these people can help, oppose, teach, employ, shelter, betray, or influence you.
- Conflict/law: these responses and consequences are possible.
- Agency: given who this person is, what they know, and what they want, what do they attempt?

## 31. Implementation direction

Do not implement this entire document as one monolithic pass. The intended order is:

1. Preserve and finish canonical magic-access/completion calibration without destabilizing the validated progression backbone.
2. Add four-stage per-skill mastery as a non-rebalancing representation of existing progress.
3. Establish compact deterministic Human Psyche state and knowledge hooks.
4. Establish bounded/event-driven Agency and World Seed/History Seed replay semantics.
5. Create event -> observation -> evidence -> knowledge/belief plumbing.
6. Route a small number of existing systems through Agency first, ideally magic aspiration/acquisition and bounded social/relationship decisions.
7. Add shared institutional life-cycle hooks.
8. Expand gradually into conflict/grievance, reputation, Society judgment, group formation, governance, records, crime/investigation, family/culture, knowledge/art/innovation, and ordinary social life.
9. Author the objective cosmology separately before implementing the divine layer.
10. Inspect existing provenance before expanding material history; extend rather than duplicate.
11. Integrate combat/injury/healing with temporal survivability and ally-arrival logic rather than flat power comparisons or instant healing.

## 32. Design test

At every layer, we should be able to ask:

> **Why did this person do that?**

The answer should be traceable to the person and the world — never merely because the simulation needed an outcome.

## 33. Living-document rule

This file is intended to remain in the repository and evolve. Add concepts after they are reconciled with existing canon and architecture. When implementation reveals that a design assumption is wrong, update this document alongside the code rather than letting design and simulation silently diverge.

## 34. Simulation-driven visual realization and procedural 3D world

ATE's long-term presentation target is a full 3D, AAA-quality RPG, intended to support first- or third-person play and eventual Unreal Engine 5-class production. Older 2.75D work may remain useful as a prototype or Visual World Laboratory, but it is not the final visual ceiling.

The visual system must be built around one governing rule:

> **The simulation owns reality. The renderer realizes that reality.**

The simulation must never need to know what a mesh, particle system, texture, shader, LOD, neural renderer, or engine-specific asset is. It should know what physically and historically exists: materials, dimensions, age, condition, ownership, construction, repairs, damage, climate exposure, culture, wealth, use, terrain, vegetation, weather, bodies, clothing, equipment, and other causal state. A replaceable presentation layer translates those truths into the best graphics technology available.

The intended pipeline is:

**Simulation state -> physical/world description -> deterministic visual realization -> engine scene -> lighting/VFX/material rendering -> neural/future rendering layer.**

This boundary is important because rendering technology will change much faster than the simulation. ATE should be able to adopt future neural rendering, reconstruction, lighting, material, animation, and generation systems without rewriting what happened in the world.

### Procedural does not mean temporary or arbitrary

World seeds and simulated history produce different settlements, landscapes, buildings, interiors, people, damage states, and cultural mixtures. The game therefore cannot depend on a fixed library of preset towns.

Instead, visual realization should compile simulated state into persistent deterministic 3D form.

- Stable world/entity identifiers plus deterministic visual seeds should reproduce the same unchanged place exactly.
- Returning to a house should not reroll it.
- When history changes the house, only the consequences of that history should change its realized form.
- Expensive realized geometry may be cached or streamed; the authoritative source remains simulation state plus the minimum visual realization state needed for exact reproduction.
- Large world changes should be patched incrementally rather than regenerating unrelated regions.

A town is therefore not a prefab. It is the current visual projection of its terrain, economy, culture, population, infrastructure, construction history, disasters, maintenance, wealth, migration, conflict, trade, and individual lives.

### Build visual languages, not maps

The art workload should focus on high-quality visual grammars capable of expressing many historically valid worlds.

Examples include structural systems, wall and roof families, foundations, beams, doors, windows, stairs, roads, bridges, furniture, tools, vegetation, clothing construction, material systems, damage states, decoration, and cultural motifs. Rules combine these elements according to actual simulated conditions.

Architecture should emerge from constraints such as:

- available local and traded materials;
- climate, rainfall, wind, snow and terrain;
- wealth and labor;
- building skill and known techniques;
- cultural preferences and prestige;
- laws, defensive needs and land availability;
- age, maintenance, expansion, fire, flood, storm and war damage;
- historical contact, migration, conquest, imitation and trade.

This allows one carefully authored architectural tradition to generate thousands of coherent buildings without making them look randomly assembled.

### History must remain visible

Visual state should expose actual history rather than select generic "old," "damaged," or "poor" variants.

A building may visibly carry its construction age, materials, repairs, additions, water exposure, soot, cracking, replacement roof sections, storm damage, ownership changes, cheap repairs, abandonment, or later reuse. Roads can preserve ancient routes after the reason for the route has disappeared. A modern street can remain crooked because it once followed a creek centuries earlier. Border architecture can show genuine blended ancestry between cultures.

The same principle applies to people and objects.

A person's appearance may express inherited morphology, age, occupation, injuries, rank transformation, nutrition, climate exposure, fashion, wealth, sleep, labor, equipment and personal preference without replacing that person with a newly generated identity.

An artifact's present appearance may derive from its material, maker, age, owners, repairs, use, storage, environmental exposure, battles, fire, water, magic and neglect. Do not select `OldSwordTexture07`; realize what this particular sword has become.

### Hierarchical realization and streaming

The same authoritative world should support multiple visual resolutions depending on distance and relevance.

At continental or extreme distance, the renderer may need only terrain, water, vegetation masses, settlement silhouettes and large atmospheric systems. Closer ranges progressively realize roads, structures, vegetation, crowds, props, interiors, wear, possessions and fine material state.

This is a presentation optimization, not a change in reality. The underlying settlement and its history remain the same at every distance.

### Weather, disasters and physical consequences

Dynamic events should be realized from their actual simulated state rather than by choosing canned spectacle.

A tornado, flood, wildfire, blizzard, battle, magical disaster or structural collapse should inherit its appearance and effects from the conditions that produced it and the environment it encounters.

For a tornado, relevant state may include wind field, pressure, moisture, terrain, soil, vegetation, structures, debris sources, rain, visibility and motion. Debris should come from actual affected materials where feasible. Damage should persist afterward because the same world was changed; there is no separate "after tornado" map.

The goal is not merely movie-quality weather. The goal is a visually extraordinary event whose details are consequences of a real event in the simulation.

### Neural rendering and future graphics technology

ATE should be designed to benefit from neural rendering without depending on one named product or version.

Technologies such as DLSS-style neural rendering can increasingly supply expensive final-frame detail, material response, lighting fidelity, reconstruction and related visual richness. Treat that capability as a replaceable renderer layer, not as the owner of world truth.

This lets the project concentrate human effort where it has the highest enduring value:

- simulation depth;
- art direction;
- coherent geometry and visual grammars;
- persistent identity;
- physical and historical state;
- animation and behavior;
- lighting intent;
- causal environmental interaction.

Future rendering systems may radically improve the final image. They must not be allowed to invent or overwrite the underlying history merely to make an attractive frame.

### Visual architecture test

For any visible thing, ask:

> **If the graphics system were replaced tomorrow, would the simulation still contain enough truth to reconstruct why this thing looks this way?**

If the answer is no, too much world truth has leaked into the renderer.

ATE should not hand-author every possible world. It should build an exceptionally strong visual language and let thousands of years of simulation write with it.



## 35. Player inhabitation, lived interfaces, and settlement change through participation

ATE must remain, first and foremost, a breathtakingly good RPG. The deep simulation exists to make the role-playing, adventuring, combat, exploration, magic, relationships, discovery, danger, and long-term consequences better — not to turn the player into an administrator watching systems from above.

A player must be able to choose one person, remain with that person for a long time, become a formidable adventurer, build a party, hunt monsters, explore dangerous places, develop an extraordinary magical identity, acquire wealth and reputation, and experience a complete RPG life without ever needing to switch characters.

At the same time, the world supports a broader form of play:

> **The player can inhabit people, shape portions of their lives, release them back into autonomous existence, and encounter them again after the world has continued without the player.**

### Inhabiting and releasing people

The player is not limited to one permanent protagonist. Across a continuing world, the player may create a person, inhabit an existing person where the game permits it, or move among multiple lives over years, decades, generations, and longer historical spans.

Leaving a person does not freeze, store, despawn, or demote them into a dormant former-player-character state. They return fully to the same autonomous simulation as everyone else.

They may:

- marry, separate, have children, lose family, or form new relationships;
- change profession, ambitions, loyalties, residence, habits, beliefs, or social position;
- gain or lose wealth and property;
- continue training or abandon it;
- learn techniques the player never selected;
- join organizations or leave them;
- become respected, forgotten, notorious, comfortable, bitter, powerful, poor, injured, disabled, old, or dead;
- become involved in historical events the player did not plan;
- live a completely ordinary and satisfying life.

Returning to such a person means returning to the life that actually occurred. The player does not reload the earlier version of the character.

A person briefly inhabited at nineteen might next be encountered at fifty-three with a spouse, adult children, obligations, scars, friends, enemies, property, debts, skills, beliefs, memories, and decades of history the player did not personally direct.

> **The player leaves people behind, not characters behind.**

Released people belong to themselves again.

### Player influence is history, not permanent puppetry

Actions taken while inhabiting someone become part of that person's actual history, but they do not erase the person's temperament, values, relationships, memories, circumstances, or later agency.

Player control should leave fingerprints rather than permanent mind-control scars.

A character the player pushed toward adventuring may later decide to stop. A deliberately optimized fighter may become a parent, teacher, farmer, merchant, official, recluse, or something else if later circumstances support it. A character whose build seemed disappointing to the player may find an excellent life or profession for that exact magic.

This is especially important because not every person is supposed to become historically important. A baker, fisher, farmer, craftsperson, caravan guard, healer, teacher, or shopkeeper can remain an entirely valid life to inhabit.

The world should occasionally make more of an abandoned character than the player did — and sometimes less.

### Old characters can return naturally

Formerly inhabited people may later re-enter the player's experience because their lives intersect with current events, not because the game artificially preserves them for a callback.

A former adventurer may become a captain in a later war. A briefly played healer may run a field hospital decades later. A farmer may become locally famous for magical agriculture. A forgotten child may become a merchant, criminal, official, teacher, parent, or nobody in particular.

Sometimes the return is dramatic. Sometimes the player simply recognizes an elderly shopkeeper and realizes they once played that person as a teenager.

That ordinary continuity is as important as spectacular historical payoff.

### Knowledge of former characters is not automatically omniscient

The player should not necessarily possess perfect current information about every person ever inhabited.

If a former character has not been seen, heard from, written to, recorded, or otherwise tracked for twenty years, their current location or status may genuinely be unknown.

Finding them again can itself become play.

Any history or character-record interface should distinguish what the player actually knows from hidden simulation truth.

### One world can support many styles of play

The same world should support radically different player relationships with history.

A player may:

- spend a hundred hours with one adventurer and never switch;
- inhabit many people for short stretches;
- follow one family across generations;
- return repeatedly to a small group of favorite people;
- briefly steer people toward magical, professional, social, or economic paths and release them;
- remain attached to one long-lived high-rank person across centuries;
- use different lives to experience the same settlement, conflict, organization, or historical event from multiple legitimate perspectives.

None of these is the privileged "correct" mode.

### The player shapes settlements by living inside them

ATE should never reduce settlement well-being to a direct player-facing prosperity control.

There should be no generic action such as `Improve Town`, no invisible player lever called `Prosperity +10`, and no requirement that the player become a mayor or city-builder to affect a place deeply.

The player changes the conditions under which people live.

The settlement changes because people respond.

A merchant may establish a viable trade route. A fisher may discover productive waters and build knowledge around seasons, techniques, and locations. A farmer may introduce a crop or magical agricultural practice. A blacksmith may benefit from more reliable iron. A healer may reduce mortality during an epidemic. A builder may solve a recurring infrastructure problem. A teacher may begin a school. A religious figure may make the town a destination. A wealthy family may finance construction.

An adventurer or monster hunter can alter the same settlement just as powerfully without participating directly in commerce.

Clearing dangerous territory may:

- make a road usable;
- reduce caravan losses;
- allow travelers to return;
- make previously dangerous land viable for settlement;
- reduce livestock loss;
- permit hunters, loggers, farmers, miners, or gatherers to work farther from protection;
- lower some transport risks;
- attract workers, families, merchants, guards, or competing interests;
- create new consequences by disturbing ecology, territory, politics, or existing livelihoods.

The causal sequence matters.

For example:

**monster pressure falls -> road becomes safer -> traffic returns -> trade becomes viable -> material availability changes -> local production changes -> employment changes -> migration becomes more attractive -> construction follows demand**

No step exists merely to reward the player with a town-upgrade token.

### Prosperity is a description, not a governing variable

"Prosperity" may be useful language for a player, historian, or designer describing a settlement after the fact, but it should not be the master cause from which local life is generated.

Two places that both look prosperous may have reached that state through completely different histories and may therefore be fundamentally different places.

One may thrive on trade. Another on agriculture. Another on monster-hunting traffic. Another on mining. Another on pilgrimage. Another because an unusually powerful protector makes the region safe. Another may be rich while most residents remain miserable.

Settlement conditions emerge from interacting realities such as:

- people and households;
- food and water;
- housing and land;
- work and wages;
- prices and material availability;
- skills and professions;
- trade and transportation;
- safety and monster pressure;
- property and accumulated wealth;
- institutions;
- political legitimacy;
- crime;
- health and disease;
- ecology and weather;
- magic;
- migration;
- family and dependency networks;
- historical events and individual choices.

Do not collapse those causes into one simulation slider merely because the resulting settlement can later be described as thriving, declining, wealthy, poor, safe, dangerous, stable, or strained.

> **The player does not improve a settlement directly. The player changes reality, and people build their lives around the changed reality.**

### Consequences need not be cleanly positive

A player may make a place safer and unintentionally create later problems.

Removing a predator may destabilize another population. Opening a road may enable invasion as well as commerce. A lucrative resource may create inequality, exploitation, crime, territorial conflict, or ecological exhaustion. Successful monster hunters may produce a local boom economy that collapses after they leave. A newly safe valley may attract settlers into land another community already considers theirs.

The simulation should not need to decide whether the player "helped the town."

It should resolve what changed.

People decide what happens next.

### Subjective lived interface

ATE should distinguish simulation truth from what a person experiences.

Most people should be capable of living inside their magic by feel: knowing an ability is nearly ready, sensing exhaustion, recognizing that aura pressure is wrong, feeling that they have enough strength for another attempt, or understanding familiar magic through practice rather than explicit floating statistics.

A more formal game-like magical interface can exist as an in-world phenomenon, especially through soulspace or related magic, but it must obey the same epistemic rule as every other part of ATE:

> **An interface may organize what a person can legitimately know or perceive. It may not expose hidden simulation truth simply because the player is looking.**

Thus the player should never walk into a settlement and receive an omniscient `Economic Health: 63%` readout.

A merchant who has gathered prices, contracts, supply information, local knowledge, and observations may have that information organized exceptionally well. A healer may experience health information differently. A monster specialist may recognize a creature that another person cannot identify. A soldier may organize threats and terrain differently from a fisher.

Different people can therefore experience the same world through different informational affordances while the game's controls remain understandable and usable.

Whether a broadly available soulspace interface eventually becomes universal, historically spreads, or remains restricted is a world/cosmology decision still open to further design.

### Looting remains an open design decision

Do not yet canonize universal magical looting.

Physical scavenging and magical loot extraction should remain conceptually distinct while the design is unresolved.

Anyone may be able to take actual physical possessions or harvest physical remains when capable of doing so. Whether essences, awakening stones, condensed magical resources, or other special rewards require a dedicated looting power, specialist, familiar, item, technique, profession, soulspace function, or later universal interface remains open.

Preserve the value of looting as a potentially meaningful magical niche until this question is resolved.

### Player-facing design test

For every deep simulation feature, ask two separate questions:

1. **Is the world causally deep enough that this outcome actually makes sense?**
2. **Is the player's immediate experience still that of an exceptional RPG rather than operating a simulation dashboard?**

Complexity belongs beneath the player.

Clarity, responsiveness, beauty, danger, discovery, agency, and consequence belong in front of them.


## 36. Life-path depth: no disposable side activities

ATE should not divide the world into "the real game" and shallow side activities.

> **If a person could plausibly build a life around something, that thing must eventually be rich enough to support a life.**

Fishing, farming, cooking, smithing, trade, medicine, hunting, construction, scholarship, teaching, tailoring, mining, animal husbandry, sailing, crafting, and similar pursuits should not be reduced to decorative minigames or a single skill number that silently increases output.

This does not mean every profession needs maximum mechanical complexity or thousands of bespoke interactions. It means each life-path needs meaningful internal structure.

Where appropriate, a mature profession should contain:

- real knowledge that can be discovered, remembered, taught, guarded, forgotten, improved, or passed through families and institutions;
- tools with properties and intended uses rather than generic numerical upgrades;
- techniques, judgment, timing, environment, preparation, and experience;
- meaningful differences between novices, competent practitioners, specialists, and masters;
- regional, cultural, family, institutional, and personal traditions;
- relationships with other professions and supply chains;
- mistakes, risks, shortcuts, innovation, and changing conditions;
- outputs whose usefulness, quality, provenance, and reputation can matter;
- enough variety that two masters in the same profession can practice it differently.

### Fishing as the model example

Fishing should illustrate the intended standard.

A skilled fisher may learn depth, current, temperature, weather, seasonal movement, spawning behavior, prey, vegetation, shade, bottom composition, water clarity, predator pressure, magical ecology, bait, lure behavior, hook choice, line, boats, nets, preservation, and local geography.

A good fishing location is good because conditions make it good, not because it contains a hidden `rare_fish_bonus`.

Those conditions can change.

Floods can reshape channels. Construction can alter flow. Pollution can ruin spawning grounds. Predators can move in or disappear. Climate and weather can shift seasonal behavior. Human pressure can overfish a population. A bridge, mill, dam, settlement, magical event, or ecological change can make old knowledge obsolete or create new opportunities.

A fisher who spends decades learning one river may possess knowledge no newcomer has. That knowledge can be taught to children or apprentices, sold, concealed, written down, distorted, or lost.

The player should also become better through experience. Character capability and accumulated knowledge can expose useful observations and improve execution without reducing the activity to automated success.

### Knowledge creates professional history

Professional knowledge should participate in the same historical model as everything else.

A family may know a river for generations. A smithing tradition may develop characteristic methods. A healer may discover a treatment others later teach. A cook may create a preparation that becomes regional cuisine. A lure-maker may invent a design that carries a family name centuries later. Farming practices may adapt through generations of observation and selective breeding.

Professions are therefore not isolated mechanics. They are domains through which civilization develops.

### Depth without chores

Richness does not mean requiring the player to perform every microscopic repetition forever.

A master smith should not become "deeper" because the player must click the hammer thousands of times. Expertise should allow the player to operate at the level where decisions remain meaningful while routine execution becomes increasingly fluent, delegated, embodied, or automated where that makes sense in-world.

The target is not maximum complication.

The target is maximum meaningfulness.

An adventurer who fishes twice should feel that fishing belongs to a deep discipline. A player who devotes an entire life to fishing should find enough knowledge, challenge, change, mastery, relationships, equipment, ecology, economics, and personal history to make that life worth playing.

## 37. Diegetic multiplayer, intersecting worlds, expeditions, and shared risk

ATE must remain a complete and exceptional single-player game.

Multiplayer must never require turning the player's living world into a conventional public server, lobby, or MMO shard. It should arise from capabilities, places, artifacts, institutions, and cosmological rules that genuinely exist inside the setting.

> **Multiplayer adds human presence to the living world. It must not turn the living world into a multiplayer lobby.**

A player who never uses networked features should still receive the complete core RPG and living-world experience.

### Multiplayer requires an in-world reason

The game should not treat a Steam friend list or menu button as sufficient fictional justification for crossing worlds.

If someone enters an astral space, they must reach or possess whatever enables that transit.

If another player is invited into a personal world, some real capability must make that possible: portal magic, an artifact, a ritual, infrastructure, a soulspace ability, an institution, a stable dimensional route, or another setting-consistent mechanism.

The exact mechanisms remain open to cosmology design, but the governing principle is not open:

> **If something happens to a person in ATE, there must be an in-world reason it can happen to that person.**

This applies equally to multiplayer access, inter-world travel, world invitations, shared expeditions, tournaments, special housing, trade, and other networked interactions.

### Personal worlds remain personal

A player's world contains actual history: families, settlements, dead characters, artifacts, former player-inhabited people, mistakes, relationships, wars, businesses, institutions, and places with potentially hundreds of hours of accumulated meaning.

Inviting another human into that world should therefore become a meaningful act rather than casual lobby access.

Different degrees of presence may eventually exist — observation, projection, limited interaction, full physical access, or other forms — but full consequential presence should require genuine trust and suitable in-world capability.

If another player is truly present and capable of acting materially, their actions should be real. Saving someone, destroying property, stealing an object, killing a person, helping construct something, changing a relationship, or altering history cannot become consequence-free simply because the actor is another human.

The host must nevertheless retain sufficient protection against unwanted destruction of a long-lived world. The exact player-safety and permission design remains open and should be reconciled with the fiction rather than ignored.

The emotional target is:

> **You do not merely invite someone to a session. You invite them into your history.**

### Shared spaces can have different stakes

Not every connected space should follow the same death rule.

**Mirage spaces** are projected or otherwise protected spaces in which participants can train, duel, compete, experiment, and die within the experience without that death automatically killing the actual person. They can support tournaments, organized PvP, team contests, training environments, and spectacular rule sets without trivializing mortality in the real world.

**Astral spaces** can be genuinely dangerous. Entering them may expose the actual soul or otherwise place the person at real risk. Death can be real where the cosmology says it is real.

**Physical or astral expeditions** may also carry genuine mortality. Some expeditions may use protected projection; others may transport people into places from which they may not return.

The entry mechanism and nature of the destination determine the stakes. Do not impose one universal multiplayer death rule.

This distinction should create different cultures of preparation.

A tournament can encourage wild experimentation.

A lethal astral expedition should make people prepare equipment, party composition, healing, escape plans, logistics, contracts, and whether the reward is worth risking an actual life.

### Mirage chambers and tournament realms

Mirage chambers can become real institutions and places in civilization rather than matchmaking terminals disguised as architecture.

Cities may maintain famous chambers. Cultures may use them differently: athletics, military training, magical research, prestige competition, public entertainment, private dueling, or professional tournament circuits.

Tournament spaces can range from simple arenas to large generated environments: forests, ruins, cities, mountains, naval spaces, survival trials, monster hunts, team battles, objective-based conflicts, or other magical realms.

Tournaments can accumulate genuine history.

Participants can become famous. Rivalries can persist outside the chamber. Institutions can sponsor competitors. Spectators can attend. Wagers, careers, training traditions, scandals, and legendary matches can emerge around them.

### Expeditions are undertakings, not a game mode

"Expedition" should describe what people are doing, not a predefined content category.

An expedition emerges when one or more people decide that something worth accomplishing requires leaving ordinary safety, assembling capability, traveling somewhere difficult, and accepting unusual uncertainty or risk.

The causes can be almost anything:

- exploration;
- monster hunting;
- archaeology;
- rescue;
- scholarship or mapping;
- acquisition of an artifact;
- collection of rare medicine or magical material;
- pilgrimage;
- trade-route establishment;
- diplomacy or first contact;
- military reconnaissance;
- colonization or settlement;
- mining or resource surveys;
- ecological study;
- a search for a missing person;
- recovery of lost property;
- a dangerous hunt or fishery;
- personal curiosity;
- a private patron's unusual objective.

Some expeditions are carefully financed and organized for years. Others begin with a few people deciding to see what is over a mountain.

An expedition should have whatever its circumstances actually require: purpose, destination, leadership, participants, knowledge, transportation, supplies, financing, contracts, reward terms, specialists, rank restrictions, legal or institutional authority, and risk.

Not every expedition succeeds. Some return rich. Some discover nothing. Some lose people. Some disappear. Some accidentally change history. Some become famous only after later generations understand what they found.

The simulation does not declare an expedition historically important in advance.

### Restrictions should arise from the place

A destination may be accessible only to certain ranks, physiologies, magical characteristics, numbers of people, or forms of transit because the place itself imposes those conditions.

A powerful Gold- or Diamond-ranker may therefore genuinely need Iron-rank people to accomplish something they cannot personally do.

For example, a high-rank patron might seek an artifact inside a realm that only Iron-rankers can enter. They could recruit a large group, finance the journey, set contract terms, and offer a spectacular reward to whoever succeeds.

This is not a `Required Level: 20` gate.

It is a property of reality.

That distinction allows low-rank people to matter to extremely powerful people without pretending their raw capabilities are equivalent.

### Multiplayer participants and simulated participants coexist

Expeditions, tournaments, organizations, and shared spaces do not need to segregate humans from simulated people.

An expedition might contain one human player and five simulated companions, four human players among thirty simulated participants, or a large event with many humans present.

The world should not need to treat human-controlled people as a separate species of person.

### Cross-world exchange must remain part of the world

Inter-world trade, if adopted, must not flatten local economies into an unrestricted global auction house.

Goods crossing worlds should remain actual objects with provenance, makers, materials, histories, restrictions, transport mechanisms, scarcity, and consequences.

A weapon forged by a player's smith in another world can be meaningful precisely because it remains the work of that person. If the smith later dies, surviving objects can outlive them in other histories.

The exact scope of cross-world markets remains open. Protect local causality and avoid allowing network optimization or real-money-style pressures to erase the simulated economies.

### Asynchronous traces and messages remain promising but open

Souls-like messages, notes, warnings, discoveries, rumors, maps, or other limited traces between players could fit ATE extremely well if grounded in an actual magical or cosmological mechanism.

Do not yet canonize the exact form.

The important boundary is that asynchronous presence should enrich discovery without filling intimate worlds with immersion-breaking spam or omniscient information.

### Cloud houses are real magical property

Cloud houses should exist in ATE.

They are not cosmetic housing skins or menu instances. They are actual magical homes with ownership, location or movement, interiors, storage, guests, history, provenance, and whatever capabilities their individual construction provides.

Different cloud houses may vary substantially in size, quality, mobility, defenses, comfort, magical features, prestige, age, condition, and history.

They can be awarded, purchased, inherited, gifted, damaged, repaired, modified, lost, stolen where possible, or passed down.

A cloud house awarded as the prize for a dangerous expedition should remain that same object centuries later. Its history can include its builder, owners, journeys, repairs, battles, accidents, guests, deaths, modifications, and changing social meaning.

Do not generate "legendary player housing."

Let a house become legendary because of what actually happened to it.

### Networked-world design test

For any multiplayer feature, ask:

1. **What exists inside the world that allows this interaction to happen?**
2. **What form of the person actually crosses the boundary — projection, soul, body, object, information, or something else?**
3. **What are the real stakes of that form of entry?**
4. **Can a player ignore the feature completely and still have the full single-player game?**
5. **Does the feature preserve local history and causality rather than replacing them with lobby logic?**

If those questions cannot be answered coherently, the multiplayer feature is not ready to become canon.


## 38. Emergent roles: do the thing before the world names it

ATE should avoid career-mode selectors, identity buttons, and abstract role assignment wherever a lived path can emerge from ordinary action.

The player should not choose `Become Merchant`, `Become Criminal`, `Become Hunter`, `Become Scholar`, `Create Gang`, `Found School`, or similar high-level identities from a menu unless an in-world institution is literally offering a formal role that requires such a choice.

Instead:

> **Do the thing. Become known for doing the thing. Let the world decide what that makes you.**

A person becomes a merchant by trading, building supplier relationships, moving goods, managing risk, learning prices, extending credit, hiring help, and developing a reputation.

A person becomes a hunter by learning animals, terrain, signs, weather, weapons, processing, danger, and where the work is.

A person becomes a teacher because other people begin learning from them.

A group becomes a gang, guild, company, school, expedition party, household name, political faction, or institution because repeated relationships and coordinated activity make that description increasingly true.

The simulation should prefer **behavior first, label second**.

### Opportunity comes from the world

ATE should repeatedly ask:

**What is the player trying to do, and do they actually have the means to do it?**

That means a desired life-path should arise through concrete access:

- knowledge;
- tools;
- money;
- relationships;
- reputation;
- location;
- timing;
- physical ability;
- magic;
- legal standing;
- transportation;
- information;
- opportunity;
- willingness to accept risk.

If the player wants to do something unusual, the game should not first ask whether a predefined career supports it.

It should ask whether the world supports it.

### Preparation is part of play

Many meaningful activities should reward observation and preparation rather than appearing as instant context actions.

A person who wants to intercept trade, discover a resource, open a business, hunt a dangerous creature, organize an expedition, become a respected craftsperson, manipulate a market, investigate a mystery, or build an institution may need to spend time learning how the surrounding world actually works.

That can include watching routes, learning schedules, asking questions, cultivating contacts, testing tools, studying terrain, gaining trust, securing financing, training, scouting, experimenting, or simply waiting for the right conditions.

Preparation should not become mandatory busywork. It matters when the undertaking itself logically requires knowledge or setup.

### Consequences emerge from affected people and systems

ATE should resist generic consequence meters when more specific causal consequences are available.

An action can alter:

- what particular people know or believe;
- relationships;
- prices and availability;
- security;
- travel behavior;
- local reputation;
- institutional policy;
- family decisions;
- employment;
- ecological pressure;
- political responses;
- investigation;
- opportunity;
- future risk.

The world reacts because something happened to someone or something, not because the player filled a hidden morality, crime, career, or prosperity bar.

Abstract summaries may exist where useful, but they must summarize deeper state rather than replace it.

### Discovery over feature advertising

ATE should not present itself as "a game where you can do everything."

That promise is both impossible and contrary to the desired player experience.

The better goal is:

> **The player should repeatedly discover that something they assumed was background scenery is actually part of the playable world.**

A boat can be owned because boats are real property.
A forge can be worked because smithing is a real discipline.
A caravan can be joined because it is actually traveling somewhere.
A route can be established because goods and people genuinely move.
A life can be built around fishing because the water, fish, knowledge, tools, buyers, weather, and traditions all exist.

The desired reaction is not:

*"The feature list says I can do this."*

It is:

*"Wait. I can actually do this?"*

ATE should cultivate unexpected possibility rather than advertise infinite possibility.

## 39. Future-facing development architecture

ATE should be designed for the game-development environment that is arriving, not only for the production constraints of 2026.

AI-assisted coding, neural rendering, generated animation, dynamic voice, procedural asset realization, automated testing, system analysis, and agent-driven implementation are expected to change rapidly during the years in which ATE is being built. The project should therefore avoid binding its deepest simulation work to whichever rendering, content-production, or authoring techniques happen to be current when a subsystem is first implemented.

The governing principle is:

> **Reality first. Generation second.**

The canonical world state must determine what is true.

Presentation systems may interpret and express that truth through meshes, animation, speech, neural rendering, conventional rendering, procedural generation, sound, cinematography, or future techniques that do not yet exist. Those presentation systems must not become the authority for what happened.

A town should exist because the simulation contains the people, buildings, roads, ownership, history, ecology, economy, institutions, and conditions that make the town real. A future realization layer may then decide how that state becomes a visible AAA-quality environment.

The same principle applies to characters.

The simulation should know who a person is, what they remember, what they believe, what they can do, what injuries they carry, what relationships they have, what languages they know, what promises they have made, and what they are trying to accomplish. A dialogue or voice system may then express that person. It must not invent a replacement person every time the player speaks to them.

This allows future technology to improve the presentation without forcing the world model to be rebuilt.

### Separate canonical state from realization

Where practical, preserve a clear conceptual chain:

**canonical simulation state -> interpretation/intent -> realization/presentation**

The realization layer can become radically more capable over time while the underlying world remains coherent.

A neural renderer may eventually replace large parts of a conventional materials pipeline.
A generated animation system may eventually realize actions that once required large libraries of bespoke clips.
A voice system may preserve identity, age, injury, language, accent, mood, and history dynamically.
An AI direction layer may frame a conversation or battle cinematically.
None of those systems should be permitted to rewrite the causal state merely because they can produce convincing output.

ATE should therefore be built so that a better presentation system can be attached later rather than requiring a new world underneath it.

### Build for machine comprehension as well as human comprehension

Future development may involve many short-lived or specialized software agents inspecting, modifying, testing, and comparing parts of the codebase.

The code should therefore favor:

- explicit subsystem boundaries;
- stable contracts;
- clear data ownership;
- canonical source-of-truth state;
- deterministic or reproducible tests where appropriate;
- strong invariants;
- modular components;
- documented reasons for non-obvious behavior;
- instrumentation;
- versioned interfaces;
- small replaceable implementation surfaces around stable concepts.

This is not an excuse to over-abstract everything. It is a requirement that important systems be understandable enough that both human developers and future engineering agents can change one part without casually breaking five others.

The long-term production advantage should come from the quality of the world model and the project's design judgment, not from making the code difficult to inspect.

## 40. Reference-system study: learn the essence, rebuild the system

ATE may study existing games deeply, including through lawful reverse engineering of observable behavior, technical analysis, frame/timing measurement, public research, open-source analogues, and controlled experimentation.

The purpose is not to clone proprietary games.

The purpose is to discover **why a strong system works**.

The development method should be:

> **Observe -> Decompose -> Abstract -> Rebuild -> Integrate -> Simulate -> Playtest**

Do not ask only:

*"How do we make combat like Elden Ring?"*

Ask:

- What creates weight?
- What creates readable danger?
- What creates commitment?
- What makes spacing matter?
- What makes mistakes feel earned?
- Which of those principles survive when the surrounding game is completely different?

Do not ask only:

*"How do we copy UFC grappling?"*

Ask:

- Which representations of range, stance, leverage, control, fatigue, takedown threat, and positional advantage make close combat feel intelligible?
- Which of those truths can be represented with a much simpler player-facing control system?
- Which details become relevant only for characters who specialize deeply in the discipline?

The same process can be used for traversal, riding, archery, ecology, economy, crafting, sailing, construction, social systems, tactics, party control, survival, investigation, or any other domain.

### Extract principles, not protected expression

ATE should not depend on copied proprietary source code, art, maps, animations, writing, audio, or other protected content.

The goal is independent implementation informed by what can be learned from successful systems.

When a reference system is useful, document the underlying principle in neutral terms rather than preserving implementation-specific quirks merely because another game has them.

A useful result of studying a game is not:

> "We reproduced its dodge roll."

A useful result is:

> "We learned that commitment, recovery time, readable intent, spacing, and the cost of panic inputs create a particular kind of combat tension. Here is how those truths belong inside ATE."

### A mechanics laboratory

ATE should eventually support rapid experimental implementations of important systems.

When feasible, build competing prototypes under the same test conditions.

For example:

- locomotion model A emphasizes inertia;
- locomotion model B emphasizes immediate responsiveness;
- locomotion model C preserves inertia but permits magical impulse correction.

Run them with the same character, terrain, controller assumptions, and instrumentation. Compare measurable behavior, then play them.

The project should be willing to discard a technically impressive implementation when it does not feel right.

AI-assisted development should make these experiments cheaper, but design judgment remains the authority.

The target is not a collage of recognizable systems from other games.

The target is a system that could only exist once those lessons were rebuilt around ATE's simulation, magic, people, and world.

## 41. Combat: accessible surface, deep physical interior

ATE combat should seek a combination of:

- Souls-like consequence, readability, spacing, danger, and action commitment;
- simulator-style causality and physical consequence;
- the useful essence of real combat sports and martial systems;
- meaningful weapon, armor, terrain, physiology, party, and magical differences.

It should **not** require every player to operate a full UFC simulation, historical fencing simulator, biomechanics laboratory, or tactical command interface every time a fight begins.

> **The world may understand far more about the fight than the controls ask the player to specify.**

### The simulation can know more than the input exposes

A relatively simple player intent such as strike, guard, evade, grapple, shove, takedown, break control, or disengage can be resolved through a much deeper internal state.

The combat model may consider:

- range;
- facing;
- stance;
- center of mass;
- planted feet;
- momentum;
- balance;
- leverage;
- grip;
- guard position;
- reach;
- relative mass;
- fatigue;
- wounds;
- pain;
- armor;
- carried equipment;
- terrain;
- nearby obstacles;
- current magical effects;
- training;
- practiced technique;
- perception;
- reaction;
- intent.

This depth should produce contextually appropriate outcomes without demanding that every player manually select every mechanical detail.

A takedown should not always be one canned animation merely because the same button was pressed. The available result can differ because one combatant is off-balance, another has inside control, one leg is injured, a wall is nearby, footing is poor, the attacker is stronger, or the defender is much more technically skilled.

### Combat should be layered

The combat architecture should remain conceptually separable into at least these layers:

1. **Physical state** — bodies, contact, mass, velocity, posture, footing, collision, reach, terrain.
2. **Combat intent** — what the person is trying to accomplish.
3. **Technique/execution** — how training and experience turn intent into action.
4. **Character state** — injury, fatigue, fear, concentration, equipment, physiology, magic.
5. **Tactical intelligence** — what a person chooses to attempt and why.
6. **Presentation** — animation, sound, camera, effects, hit reaction, neural or conventional realization.

Do not allow presentation to become the hidden combat rules.

### Take the essence of combat sports, not their entire interface

Modern combat-sport games can provide useful lessons about distance, stance, guard, clinch control, takedowns, sprawls, transitions, body targeting, positional advantage, and fatigue.

ATE should use only the amount of that depth necessary to make physical combat convincing.

A general adventurer should be able to fight competently with an understandable control vocabulary.

A dedicated wrestler, prizefighter, soldier, duelist, martial instructor, assassin, or other specialist may develop access to richer technique, better contextual choices, specialized counters, stance work, chain attacks, clinch skill, weapon retention, throws, ground control, feints, or other domain-specific mastery.

This follows the same life-path rule established elsewhere:

> **Simple usable surface. Deep simulated interior. More of the interior becomes relevant when a person's life makes that depth meaningful.**

### Weapons are different physical problems

Do not reduce weapons to animation sets with damage numbers.

A spear changes distance and leverage.
A shield changes posture, vision, protection, and available actions.
Heavy armor changes movement, endurance, heat, protection, and vulnerability.
A bow changes positioning, timing, ammunition, line of sight, and exposure.
Mounted combat changes velocity, reach, stability, collision, animal behavior, and terrain.

Each weapon family should inherit as much as possible from shared physical/combat primitives while preserving the things that actually make it distinct.

### Party competence should be learned

Long-term companions should not merely gain statistical synergy bonuses.

People who have fought together for years can learn one another's habits, timing, preferred openings, retreat patterns, signals, strengths, weaknesses, and magical combinations.

A veteran companion may recognize what the player is setting up before receiving an explicit command.

Team competence should emerge from experience, training, communication, relationships, shared doctrine, and memory.

## 42. Profession depth is selective, expandable, and contextual

The existing life-path rule does not require maximum simulation detail everywhere at once.

The project should seek the **minimum depth necessary to make a discipline feel true**, then expand where player specialization, profession, culture, technology, or magic makes additional depth worthwhile.

A person who fishes twice should not need to learn a professional fishing simulator.

A person who spends twenty in-world years fishing should discover considerably more beneath the surface.

The same applies to fighting, smithing, medicine, hunting, sailing, farming, trade, scholarship, construction, and other lives.

This creates an important production rule:

> **Implement the shared causal truth first. Expose additional resolution where expertise makes it meaningful.**

For hand-to-hand combat, the baseline may represent balance, distance, guard, stamina, leverage, injury, and control.

A specialized grappler may later require much more detailed positional and transition logic.

For fishing, the baseline may represent species, water, weather, equipment, knowledge, and skill.

A professional fisher may later interact with finer-grained behavior involving season, depth, current, feeding, spawning, boat handling, preservation, markets, and regional knowledge.

The system should therefore be expandable without requiring every subsystem to begin at maximum complexity.

## 43. Magic is a capability architecture, not a class overlay

The HWFWM-inspired Essence/Confluence/Awakening structure is one of ATE's major departures from conventional recent RPG design.

ATE should not reduce that structure to classes wearing different names.

A person's magical identity emerges from their Essence combination, Confluence, awakened abilities, rank, training, experience, equipment, physiology, circumstances, and personal style.

Two people at the same rank should be capable of fighting, traveling, working, solving problems, and experiencing the world in radically different ways.

Combat and world systems must therefore reason about **capabilities**, not predefined classes.

### Magic should alter causes, not merely numbers

When practical, an ability should interact with the system it claims to affect.

A strength ability should not automatically collapse into `+30% melee damage`.

It might alter acceleration, grip, lifting force, striking force, posture, jump capability, load carrying, resistance to displacement, or the ability to impose movement on another body.

A kinetic ability may alter momentum transfer.

An air ability may alter movement, pressure, footing, projectiles, sound, breathing, or environment depending on its actual design.

A perception ability may change what information is available and how quickly it is processed rather than simply granting a universal critical-hit bonus.

A healing ability should participate in the health/injury system rather than merely refill an abstract combat bar.

The same ability may therefore matter in combat, travel, work, rescue, construction, crime, medicine, logistics, sport, exploration, or ordinary life.

### Magic belongs to the world's physics

ATE magic is not solely a combat feature.

If a person can move heavy objects magically, that affects labor and construction.
If a person can heal, that affects medicine, war, childbirth, risk, work, status, and institutions.
If a person can alter water, that affects travel, irrigation, drought, fishing, settlement, and disaster.
If a person can move goods unusually efficiently, someone may eventually build a business around it.

The simulation should ask what people would actually do with capabilities that exist.

Do not reserve magical creativity for the player.

### Rank changes the space of possible combat

At low rank, a person may still fight largely within human physical assumptions while gaining important magical advantages.

At higher ranks, those assumptions can progressively break.

Greater speed, durability, perception, movement, recovery, environmental manipulation, aura, range, summoned entities, transformation, and other capabilities can make higher-rank combat qualitatively different rather than merely numerically larger.

The underlying combat architecture should remain coherent enough that superhuman action still has causes.

A powerful combatant may jump farther, redirect momentum, survive greater impacts, use terrain differently, or fight through injuries that would disable an ordinary person. The system should understand why.

### Emergence through interaction

The strongest magical moments should often come from systems interacting rather than from bespoke cinematic scripts.

A character redirects momentum.
A companion strikes the target from another angle.
The target collides with a damaged structure.
The structure fails.
Debris blocks a route.
Fire spreads.
Bystanders react.
Property is destroyed.
Witnesses remember who caused it.

No designer needed to author a specific "monster crashes through this wall" quest beat.

The world produced an event because its systems agreed that the event could happen.

That is the target.

## 44. Commercial resilience in an AI/open-source future

ATE should be finished regardless of how the surrounding game industry changes.

The project should not make its long-term commercial value dependent on code secrecy.

AI-assisted development may make competent game construction dramatically cheaper. Open-source indie development may become increasingly normal. Mechanics may become easier to analyze and independently reproduce. None of those futures should invalidate the project.

The durable value should come from the quality and continuity of the actual world:

- the canonical setting;
- the official universe and history;
- trusted releases;
- long-term development;
- community;
- curation;
- art direction;
- official content;
- persistent player histories;
- creator ecosystems;
- hosted infrastructure where useful;
- the accumulated quality of the complete experience.

An eventual model such as **open engine / owned universe** may be viable, but it is not yet a binding licensing decision.

The binding principle is simpler:

> **Do not build a moat out of inaccessible code. Build a world worth returning to.**

If future players can easily create thousands or millions of games, abundance does not eliminate the value of authorship, taste, continuity, coherence, trust, and a world people care about.

ATE's development strategy should therefore remain flexible enough to thrive whether the final commercial environment favors conventional premium releases, open-source ecosystems, creator platforms, hosted persistent worlds, major expansions, or some combination that does not yet exist.

The path may change.

The project does not.

## 45. Character creation, origins, and voluntary magical identity

**Design status:** Core freedoms and constraints below are adopted. Exact creation-screen flow, race catalogue, trials, starting allocation and numerical balance remain design work.

ATE begins with a person entering an already living world, not a premade class or a guaranteed hero's journey. Character creation should provide considerable physical customization and a comprehensible starting situation while leaving most of the character's future to life and circumstance.

### Two ways to enter the world

Offer two broad origin directions:

- **Isekai / outsider:** A person arrives from another world. Their arrival requires a valid in-world cosmological cause, not an unexplained menu exception. They may lack local knowledge and relationships; they are not automatically chosen, cosmically favored or destined for importance.
- **Natural-born / native:** A person belongs to the simulated world. Their family, birthplace, upbringing, cultural understanding, socioeconomic circumstances and existing ties must be compatible with actual world history. Do not invent an isolated biography that contradicts the save.

Both origins can pursue any legitimate life, magical or mundane. Neither grants automatic superiority. The precise rules by which newly created people are introduced into an established historical timeline, and by which outsiders cross worlds, still need design.

### Customization and presentation boundaries

Support meaningful freedom across the world's playable races, sex and physical appearance, with detailed control over face, body, height and proportions, hair, coloration, markings, scars and physiology-specific traits. Race must correspond to an actual world physiology; its physical properties can matter without reducing people to classes or fixed destinies. Provide usable presets as well as advanced customization. The final catalogue of playable physiologies is not yet fixed.

The game may address adult subjects without displaying explicit nudity. Character creation and ordinary presentation should use appropriate clothing/undergarments; anatomical customization does not require nude display. No finished HUD or character-editor layout is canonized by this section.

### Starting Essence: three legitimate magical beginnings (updated 2026-10-11)

**Adopted player choice:** Standard character creation should permit an **unawakened** beginning, a **first-Essence** beginning, or an **Iron-rank** beginning. This replaces the older restriction that a normal player could select only one Common Essence. None is an inferior mode or an automatic guarantee of exceptional future success.

1. **Unawakened / no Essence:** Start with no Essences or awakened abilities, with the freedom to remain mundane for an entire life or seek magic in-world. This leaves open the possibility of eventually discovering **Legendary** Essences or a **potential Transcendent** tier/opportunity if that upper category is formally defined and implemented; neither discovery nor successful acquisition is guaranteed. **"Transcendent Essence" is currently a design possibility, not a confirmed catalogued item or fixed rarity/progression rule.**
2. **First-Essence beginning:** Start with one **Common** Essence and its innate ability, while remaining **unranked** until two more base Essences are acquired and the Confluence forms. Further Essences and abilities are earned in play. A possible optional in-world *trial* to qualify for rarer initial access remains open design, not a guaranteed Uncommon/Rare grant, unbounded reroll or settled fourth starting path.
3. **Iron-rank beginning:** Select **three base Essences** from a deliberately **Common-and-Uncommon-focused starting pool**, with a **limited Rare selection** if supported by the actual catalogue and in-world acquisition/provenance. The **Confluence automatically forms** from these three; the player **does not independently pick the Confluence**. Each Essence, including Confluence, begins with **one awakened innate ability**. Therefore the character starts at **Iron rank with exactly four awakened abilities (4/20)**—not with all twenty. The other **sixteen** must be unlocked and developed during the living game.

**Bronze is not a character-creation shortcut.** An Iron-start character must eventually awaken the other sixteen and progress **every one** of all twenty to Bronze. The choice of three starting Essences fixes meaningful, potentially irreversible parts of the path but leaves most ability acquisition, rank development, tactics and life history open. An Iron-start person's prior acquisition, training, relationships, origin and real magical resources require a world-causal introduction; creating six roster characters must not become infinite resource generation. Exact creation-pool members, Rare access restrictions, ability customization at creation and world-provenance mechanism remain open design.

**Rarity is not a direct combat-strength rating or a quality-of-person score.** Rarer Essences may have unusual properties, availability constraints and greater or different *potential*; they do not inherently make their users better adventurers. Actual effectiveness is shaped by ability expression, rank, mastery, training, experience, creativity, equipment, physiology, strategy, matchup, environment and relationships. A deeply skilled adventurer possessing **only Common Essences** can be among the greatest in the world. Do not impose a universal rarity-damage multiplier or script a Legendary-Essence user to outperform a Common-Essence master.

The Mirage Arena remains the **separate in-world experimentation sandbox**, not a route to grant all twenty real abilities at creation. A full build selected there need not be obtained, or manifest identically, in the living world.

All starts remain available independently of isekai/natural-born origin where their actual world explanations are legitimate; detailed limitations are to be designed. Explain Essence commitment consequences clearly.

**Mundane life is a complete life-path, not a beginner state, missing class, challenge penalty or failed magical build.** A person can remain without Essence magic until death and still be a master craftsperson, respected parent, politician, soldier, investigator, scholar, entrepreneur, farmer or historical figure. Do not award magic merely to validate a life well lived, or require it for meaningful play. Physical and magical power disparities remain real: an excellent mundane fighter is not secretly made equal to a Diamond.

### Classes are emergent descriptions

No conventional immutable class selector should govern ATE. The four-Essence/twenty-ability framework creates capabilities; profession, equipment, training, technique, reputation, relationships and conduct create a person's practice and social description. Terms like duelist, battlemage, healer, blacksmith or adventurer may help players understand or describe someone, but must not become invisible restrictions on what they can attempt. Two people with the same Essence combination can develop substantially different lives and effective builds.

## 46. The world is the save; playable lives are inhabitants

**Governing rule:** **The world is the persistent game. A character is a life inside it, not the container holding the save.**

The player may spend an entire game with one person, create several people, inhabit existing simulated people where permitted, follow a family across generations, or move between unrelated lives. No protagonist is required to survive for the world to continue.

### Personal creation roster versus people one can inhabit

Adopt **at least six personally created lives per world as the initial roster design target**. Six is not a permanent ceiling on the number of people one may know, revisit or inhabit; capacity, slot reuse, and final UI remain to be specified. A created person is an actual member of the world, not a separate save branch or a disposable character preset.

Maintain two distinct notions:

1. **Created lives / roster:** People the player personally introduces through legitimate origins, initially targeting six or more.
2. **Inhabited lives / history:** Any existing person whom the game's eventual inhabitation rules permit the player to control, whether or not originally created. Formerly inhabited people may be followed or bookmarked without consuming a created-character slot.

**Do not interpret the six slots as an adventuring party.** Each person may live on another continent, maintain an unrelated career and have their own family, crew, guild or companions. Their paths may cross through causality, but the system must never force crossover because both are on the player's roster. A player can intentionally keep their lives separate by where and how they live; they cannot suspend the world's ordinary causal possibilities.

An adventurer can assemble companions naturally. Those companions are autonomous people, not automatically the user's other created lives; permitted inhabitation of one of them changes viewpoint without magically making the group into six authored protagonists.

### Shared time, mortality and release

All characters inhabit **one world clock and one actual history**. Playing one does not freeze the others. Switching viewpoints must neither duplicate time nor silently fast-forward far beyond the player's informed choice. World-time flow, waiting and explicit long-history advances require clear controls and safeguards; no assumption is made that real-life offline time advances the world.

When the player releases a person, that person returns to the same agency and simulation rules as everyone else. They may train, prosper, fail, change jobs, fall in love, have children, move, join a movement, abandon an ambition, age or die. On return, the player inherits the person's *actual intervening life*, not their earlier snapshot. Player-directed history influences them but does not permanently lock their desires or future decisions.

Death is a real world event and is generally permanent under the existing one-life rule, subject only to genuine rare in-world resurrection mechanisms. It changes inheritance, property, grief, relationships, careers, organizations and history. It does **not** delete the world save or require a restart. The player may continue another existing life or introduce a new life through legitimate origins. The dead remain in memory and history, not erased to make a slot look unused.

### Information and perspective separation

The human player may remember information learned while inhabiting someone else; the current person does not thereby gain it. Knowledge, maps, rumors, private plans, hidden property, identities and relationships remain situated within actual observers and transmission. No shared-roster telepathy, automatic companionship or inventory pooling. Interactions between lives require real-world contact, messages, contracts, trade, inheritance, discovery or other legitimate causes.

### Deliberately shaped people, unpredictable futures

The player may develop someone ruthless, ambitious, cruel or unusually powerful and release them far from familiar settlements. That person might become a feared antagonist, establish an institution, live quietly, reform or die. **There is no Create Villain function and no guaranteed villain trajectory.** A former player-inhabited person is not plot-armored, preserved as a future encounter or obligated to become an adversary. This is one of the central tests of autonomous personhood.

## 47. Autonomous release goals, plans and life commitments

**Core decision:** When leaving an inhabited person, the player may express intentions for that person's future activity, continue existing commitments, or add no new direction. These intentions enter the **same bounded Agency system** that governs every other person; they are not remote-control orders, job-queue cheats, guaranteed outcome scripts or a separate former-player AI.

### Release choices

A proposed release interface should make three intentions intelligible without forcing elaborate micromanagement:

1. **Continue existing life:** Keep present goals, routines, obligations and commitments.
2. **Prioritize selected goals:** Record specific desired outcomes and priorities for the autonomous person to pursue, to the extent feasible and compatible with who they are.
3. **No new direction / live freely:** Add no player-authored goals; the person still has memory, needs, habits, existing promises and the freedom to form new plans. This choice does not wipe their prior identity or debts.

The wording and layout of the release screen are not finalized. The player can later inhabit the person again and change their own plans, but intervening consequences and commitments remain real.

### Goal representation and decision model

Represent a goal with enough causal structure to guide action without pretending it determines success. A useful bounded goal record may hold:

- the **desired condition** and subject (e.g., host a banquet, learn a technique, recruit a student);
- **motivation and personal importance**, distinguished from an external command;
- a **deadline or horizon** where real, and expected effort;
- known **prerequisites, dependencies and feasible next steps**;
- perceived **resource requirements** (money, materials, labor, tools, transport, property, skills, knowledge, time);
- relevant **relationships, promises, contracts, permissions and consequences**;
- **confidence, uncertainty and information provenance** from the person's knowledge, not global truth;
- priority, current status, previous attempts and reasons to continue, delay, renegotiate or abandon.

Goals may overlap, conflict or support one another. Deadline-driven obligations can outrank distant ambitions, while illness, family emergencies, weather, violence, opportunities or changed values may rationally cause reprioritization. Failure may generate debt, reputation change, disappointment, loss of a contract, learning or a new plan. A stated goal must never skip the actual work required by downstream systems.

Agency chooses among plausible efforts using the existing person/world model. Profession systems resolve the practical work; economy resolves resources and prices; social systems resolve cooperation; the world resolves whether outcomes are possible. **Instruction is intention; choice is agency; achievement is consequence.**

### Chef: five simultaneous intentions as an integration test

A restaurant-owning chef is released with five goals, not five completion timers:

| Goal | Real work and dependencies | Possible consequences |
|---|---|---|
| **Study advanced cooking techniques** | Find sources or teachers, arrange time, buy or borrow tools/ingredients, practice, fail and improve | Greater competence, expenses, relationships, discoveries, limited or lost time for paid work |
| **Prepare for the harvest banquet** | Accept/confirm an actual obligation; plan menu and portions; acquire food, staff, equipment, venue and transport before a real date | Income and prestige if successful; shortages, illness, weather or mistakes may cause renegotiation or failure |
| **Develop a signature regional dish** | Experiment with regional produce, taste, preservation, technique, available equipment and consumer preferences | Original knowledge, regional identity, imitation, prestige, sales or an expensive unsuccessful experiment |
| **Expand the restaurant** | Determine actual demand, secure finance, property, materials, labor, permits or local consent where applicable | More capacity, jobs and influence—or debt, vacancies, supply stress and closure |
| **Recruit and train an apprentice** | Find a willing person, agree on terms, allocate teaching time, teach real techniques, earn trust and assess progress | Transmitted knowledge, mutual loyalty or resentment, succession, competition, departure or an institution surviving its founder |

A harvest deadline may draw effort away from studying. An apprentice might make the banquet viable and later develop the signature dish further. Expansion can fail because trade collapses or succeed because new roads reopen. The chef may fall in love, become ill, have children or change careers. None of the five goals immunizes them from life.

The player returning after months or years should find inspectable evidence of what happened: contracts, purchases, actual changes to the restaurant, learned techniques, recipes or their bounded knowledge representations, coworkers, apprentices, debts, reputation by observer, and events. No invented summary claiming the chef "completed banquet 100%" without real underlying state.

### Scope and scalability

A person should hold a **small bounded set** of active concerns and goals, with dormant longer-range ambitions where justified. Reassess them on meaningful events, deadlines and coarse cadence, not by repeatedly scanning global historical archives or deliberating in maximum detail every simulation tick. Released characters must have no more special per-tick machinery than comparable never-inhabited people.

Test routine continuity, conflicting priorities, failure, an unmet prerequisite, a broken contract, discovery of new information, a changed relationship, unexpected success, and a person explicitly abandoning the player's former objective.

## 48. Mirage Arena: diegetic sandbox and imperfect rehearsal of reality

**Core decision:** The **Mirage Arena is the sandbox**. Do not create a second disconnected, omnipotent "sandbox universe" as the conceptual default.

Mirage chambers are real magical locations/institutions governed by in-world access, capability and history, as established in Section 37. An appropriate chamber or player-facing Mirage experimentation context may permit simulated Essence selection, rank and mastery settings, twenty-ability configurations, equipment, monsters, opponents, environments and combat trials. It may permit mundane experimentation as well. The confluence still follows the legitimate Essence combination rather than becoming an independently arbitrary fourth choice.

**Simulated success grants no real Essence, Awakening Stone, rank, rare possession or permanent magical capability.** The living world retains actual scarcity, access restrictions, training, risk, relationships and consequences. Projected deaths do not automatically kill the actual participant, unlike genuinely lethal astral or physical expeditions. Keep those modes distinct.

### Model accuracy is conditional, not a guaranteed percentage

A Mirage reflects its model of physical and magical reality, its technical or magical sophistication, and the quality of information available to it. A sophisticated arena may predict many known interactions extremely well; an older or poorly informed one may fail on rare abilities, unusual environments, unknown power expressions, individual physiology or poorly studied magical combinations.

The player's illustrative idea of "90% accurate" describes meaningful **remaining uncertainty**, not a mandate to implement a fixed 10% error chance or to manufacture a surprise on every tenth event. Test whether the modeled causes are sound; **do not roll a separate narrative inaccuracy die.**

A Mirage-tested ideal three-Legendary build might never be obtainable in the actual world. Even if the real Essences are eventually found, awakening stones, available ability outcomes, training, body, timing, mentors and circumstances may yield a different toolkit. It is also possible to reproduce a projected outcome when the real causes align. Neither success nor divergence is guaranteed for dramatic convenience.

People can practice, learn and plan inside a Mirage where justified by in-world rules, but practice must not bypass real acquisition, material resources or irreversible consequences. The Mirage can show **what might be possible**. The living simulation determines **what actually happens**.

## 49. Consequential civilization and the conditions for emergent stories

**North star, restated:** **Do not write the stories in advance. Construct a world deep enough that meaningful stories and gameplay emerge from people, circumstances and history.**

Every profession, magical capability, relationship, institution, possession and environmental intervention must connect to real causal state. A superb farmer should produce materially different possibilities than an unskilled farmer in otherwise comparable conditions. An ill-equipped merchant should face genuine transport, supply, financial and social risk; good preparation should help but not guarantee victory. These consequences should propagate through specific people, places, inventories, wages, food, debt, trust, jobs, health, ecology, travel, property and knowledge—not through a generic "story importance" or "town prosperity" increment.

### Example: the farmer, the merchant and a drought

A farmer who invested years in irrigation, breeding, reserves and local relationships may weather a drought better than neighbors. Grain scarcity changes prices and leverage. A poorly prepared merchant carrying supplies might break down or fail delivery, worsening local shortages. Those combined effects may change jobs, migration, theft, bargains, influence, family futures or political disputes. The prepared farmer can still fail through disease, bad judgment or wider catastrophe; the merchant can recover through skill, help or improvisation.

The point is not to force drought drama. The point is that the systems recognize what was actually prepared, exposed, attempted, bought, saved, broken, promised or lost.

### Development levers: tune causes, not endings

Designers need explicit calibrated parameters and observability for the processes that make varied histories possible. Important families are:

1. **Scarcity and abundance:** resources, labor, food, land, logistics and unequal access.
2. **Opportunity and access:** learning, magic acquisition, discovery, careers, encounters, travel and institutions.
3. **Individual agency:** temperament, values, beliefs, emotion, ability, risk appetite and goals.
4. **Social friction and conflict response:** grievance, status, exclusion, debt, justice, retaliation and negotiation.
5. **Interdependence:** trade, family, mentorship, employment, supply chains, services and obligations.
6. **Environment and ecology:** climate, monsters, health, catastrophe, local habitat and changing resources.
7. **Institutional resilience and legitimacy:** governance, succession, law, capacity, memory, corruption, reform and collapse.
8. **Memory and information transmission:** witness knowledge, rumor, records, reputation, inheritance, education and cultural change.

These are broad **causal calibration families**, not eight global "drama sliders" or a replacement for existing subsystem rules. Preserve local differences, random-seed reproducibility and the distinction between what is true and what each individual knows.

### Escalation, climax and resolution without an arc director

A conflict can travel from a small disagreement to a feud, a court case, sabotage, war, compromise, reconciliation or disappearance. A romance may grow, fail, endure, end in death or become a family institution. A discovery may transform a craft or remain forgotten. **Climax is a later observer's description of a decisive change, not a simulation event type that must be produced.**

Do not implement commands like Force War, Start Redemption Arc, Make Epic Romance, Generate Legendary Hero or Save The Protagonist. People pursue motives; circumstances permit actions; consequences change future opportunity. Extraordinary action remains possible for people never inhabited by the player. Ordinary peace, prosperity, artistry and family life may be just as valuable as catastrophe.

### Seed quality without narrative quotas

Every valid seed should support substantial **opportunity for** adventure, surprise, meaningful choice, love, conflict, danger, learning, recovery, social change and historical development. Do **not** guarantee one war, one legendary romance or one cinematic climax in each century or world. An unusually peaceful and creatively productive century can be a successful history. A sterile thousand years of nearly consequence-free behavior is cause for investigation.

Use reproducible multi-seed testing to assess, at minimum:

- Whether goals lead to actual attempts, resource use and changed circumstances.
- Whether effort, preparation, competence and mistakes make outcomes causally different.
- Whether relationships, promises and observer-specific reputation influence later decisions.
- Whether some disputes escalate, others resolve, and both paths leave comprehensible evidence.
- Whether technologies, professions, institutions, families and cultures develop, transmit knowledge, fail or survive.
- Whether unusual events arise from mechanisms that can be reconstructed rather than narrative quotas.
- Whether players can **discover and act upon** consequential events through plausible information channels.

Measure distributions, stagnation, extreme outcomes and causal traceability across seeds. Diagnose weak causes and thin connections rather than injecting plot to satisfy a checklist. Preserve the established millennium performance target and long-history state integrity; observing richness cannot require universal expensive deliberation.

### Playability: history must be encounterable

An extraordinary event on another continent may be hidden from the current character, but the world needs genuine routes by which its effects become encounterable: travelers, prices, trade networks, witnesses, letters, institutional records, apprentices, rumors, archaeology, family stories, displacement and later meetings. A farmer, merchant, scholar, chef and adventurer legitimately experience different portions of the same history.

The player must have ways to investigate, participate, prepare, cooperate, refuse and bear consequences, while retaining the possibility that some events pass unnoticed. Depth without discoverability becomes an invisible database; discoverability without causality becomes a scripted amusement park.

## 50. Character-facing information and interface direction

**Directional, not a finished HUD specification.** The world remains primary. The interface should be clean, legible, flexible and context-sensitive rather than a perpetual dashboard of omniscient statistics.

- Surface combat resources, risks and available actions when relevant without requiring a full-screen spreadsheet.
- Organize magical progress, Essence paths and abilities through diegetic perception or legitimate soulspace/system interfaces where cosmology permits, never unrestricted hidden-world truth.
- Show maps, knowledge, contracts, profession information and relationships according to what the currently inhabited person can know.
- Let mundane characters have rich profession, skill, relationship, equipment, resource and life interfaces; do not permanently display twenty empty magic slots as if their lives were unfinished.
- Provide comprehensible character selection, world-time change, return, release-goal and history interfaces without making former player characters freeze in menu space.
- Preserve accessibility, player-configurable clarity and usable controls even where information is represented diegetically.

No precise HUD layout, display style, control mapping or universal soulspace grant is decided here. These must be prototyped alongside an actual playable slice rather than locked down solely by prose.

## 51. Independent completion, audience development and release strategy

**Preferred strategic direction, not a signed distribution or licensing decision:** ATE should be built to a genuinely completed, polished, commercially releasable game and **self-published** where practical. Retain control of the game's intellectual property, canon, creative direction, technology choices, releases and player experience. Do not treat a publisher, investor or exclusive revenue-share agreement as mandatory merely because the team is small.

- **Steam first** is the preferred primary PC storefront to evaluate when a market-ready project exists. Consider GOG and other stores on their actual terms; consoles are a later technical, compliance and business decision.
- Avoid giving away IP, unnecessary exclusivity or major revenue participation in exchange for vague marketing promises. Distribution platforms necessarily have agreements, fees and obligations; independently review real contracts rather than pretending that publishing can occur with no terms at all.
- Do not wait until finished development to introduce the game publicly. Once a **truthful, convincing playable vertical slice** exists, begin an audience/wishlist/community effort grounded in actual footage and credible claims.
- Prefer a representative polished demo and complete release over selling promises. Early access is a possible deliberate future choice, **not** the default method of funding an unfinished vision.
- Evaluate practical economics before launch: pricing, storefront fees, taxes, conversion, wishlists, marketing costs, support burden, QA, certification, localization, accessibility, infrastructure and post-release obligations.
- Design commercial sustainability so the project does not *require* blockbuster sales to be viable. Future business models remain open until supported by evidence.
- AI-assisted and agent-driven development can multiply implementation capacity but do not eliminate the need for independent quality judgment, security, testing, playtesting and responsible release management.

The production order should not confuse long-term aspiration with validated completion. Finish Stage 0.5's persistence independently; build the living-simulation/Agency integrations and a small **playable** slice in a coordinated way after the foundation stabilizes; then expand, evaluate and test the complete RPG. Do not spend indefinitely building invisible infrastructure without validating that entering, living in and changing the world is a compelling experience.

## 52. Decision register and implementation boundaries for Sections 45–51

**Agreed core direction:**

- World-owned persistence, real mortality and continuing history; several created lives in one world, no forced shared party.
- Player inhabitation of existing people where the rules permit; releases return people to full autonomous life.
- Optional goals on release, processed through ordinary Agency rather than puppet orders.
- Isekai or natural-born beginnings; substantial customization; no explicit nudity required.
- **Three standard magic starts:** no Essence, one Common Essence (unranked), or an **Iron start with three chosen Common/Uncommon-focused Essences, limited Rare possibilities, automatic Confluence, and 4/20 awakened abilities**. Unlock and train the other sixteen in-world; mundane play remains fully valid. Iron = Confluence; Bronze requires all 20 abilities individually at Bronze. See Section 2 and issue #17.
- No traditional binding class selection; skills, magic, careers and status emerge from actual capabilities and behavior.
- Mirage Arena as the in-world sandbox and rehearsal, not a guarantee of actual magic outcomes.
- Consequential professions, relationships, history, failure and preparation; causal tuning rather than generated plot quotas.
- Long-term independent release and retained creative/IP control as the preferred business strategy.

**Provisional implementation details (do not quietly promote to canon):**

- Final count above the **at-least-six created-life target**, slot replacement/history interface and restrictions/costs for inhabiting any person.
- Starting trial access to Uncommon/Rare Essences; exact Iron-creation pool and rarity constraints, economic/provenance guardrails, permitted initial ability choices, and the potential **Transcendent** tier's actual definition and source.
- Exact race catalogue, age/background generation, character-editor controls and HUD.
- Mirage availability, permissions, custom-build tooling, degree of modeled uncertainty, training carryover and individual chamber capabilities.
- Release-goal priority UI, active-goal limits, time-advance options and how free-form intentions are captured in player controls.
- Final storefront, pricing, commercial structure and launch/release schedule.

**Verification requirements before implementation acceptance:** Shared-time continuity; no roster-forced meetings; death retains historical consequences; correct character-relative knowledge; held identity and lawful release/return; autonomous goal abandonment and completion grounded in actual work; real magic rarity and irreversible commitment; genuine mundane alternatives; Mirage/live-world separation; multi-seed causal richness without scripted quotas; bounded per-person Agency and persistence; and a playable interface exposing legitimate opportunities without omniscience.

**Relationship to current architecture:** Extend existing Agency, goal/memory, information, profession, event, identity, magic, economy, institutional, provenance and persistence mechanisms. Do not introduce parallel story, player-NPC, historical artifact, AI companion, loot or world-truth registries where existing primitives can be extended. This design update makes **no claim** that these proposed systems are already implemented, nor does it approve changes to the in-progress Stage 0.5 closeout branch.

## 53. Product scale decision: Game 1 is one deeply lived kingdom

**Adopted scope direction (2026-10-11):** Build and finish **Game 1 as one geographically coherent, deeply simulated kingdom or kingdom-scale region supporting approximately 1,500 living people at a time**. This is not a temporary fake map, a mandatory tutorial, a single-city quest hub, or an unfinished fragment of a promised continent-spanning game. It is the proposed **complete setting for the first finished, polished, independently released game**. The broader multi-kingdom/civilization ambition remains valuable, but Game 1's release must not depend on already supporting millions of simultaneous people.

The same kingdom can support a development vertical slice, then a public-facing demo, then a complete Game 1:

- **Development vertical slice:** Prove a genuinely playable and visually realized portion of the real kingdom, including ordinary life, travel, danger, professions, magic where available, relationships, character inhabitation/release, and persistent consequences. Scope small enough to implement and measure. It is a proof of integration, not the finished game.
- **Public demo:** A representative, engaging segment of the actual game that demonstrates its central promise without inventing fake quests, simulated cinematic history, or systems that disappear in the release. Demo extent, starting conditions and accessibility remain to design.
- **Finished Game 1:** The connected kingdom with sufficient geographic, social, professional, ecological, magical, historical and gameplay breadth to stand alone as a substantial RPG. Multiple lives and play styles are genuinely supported; it should not feel like a prototype waiting for a second game to become complete.

The kingdom's boundaries, travel times, geographic footprint, political structure, number of settlements and starting historical age will be determined by world generation, design/testing and playable realization—not fixed by this section. A plausible mixture might include a principal market town, agricultural communities, smaller villages/hamlets, working sites, wilderness, routes and ruins; this is a **possibility**, not a prescribed generated map or settlement quota. Concentrate population and meaningful interactions enough for an inhabited society. Do not stretch roughly 1,500 people across many empty continents to claim map size.

**Approximately 1,500 is an observed current scale and a practical initial performance/design target, not an immutable population law.** Birth, death, disease, migration, settlement growth and loss remain causal. Do not stop births or manufacture deaths when a population counter reaches an exact target. The actual supported operating range, seed distributions and upper acceptable performance bounds are to be established with evidence. Test whether such a society can sustain enough food, labor, trade, family continuity, specialization, ranks, defense, institutions and meaningful player opportunities without implausible occupational staffing. Do not fabricate a huge metropolis or empire inside a population that cannot maintain it.

The full standard set of Game 1 design promises still applies at this smaller scope: autonomous individual lives, player-controlled and released people, six-or-more created-life design target, optional mundane and magical paths, Essence acquisition, Mirage experimentation, combat, professions, families, institutions, real deaths, long history, causal environments, and consequences. Narrower geography does **not** authorize a shallow simulation.

### Small-population conflict and historical weight

At this scale, small groups can matter profoundly. Conflict may consist of a feud, a robbery, threatened violence, a raid involving a handful of people, a skirmish among settlement defenders, or a prolonged series of retaliations and truces. There need not be a single pitched battle for a warlike relationship to exist.

A battle with **100–200 total participants** is a conceivable **exceptional** local engagement, not a required or default size: at 1,500 total living people it involves approximately 7–13% of the entire world's current population, before accounting for children, elders, noncombatants, distance, loyalty, ability, injuries and logistical commitments. The actual scale emerges from who is available and who can be recruited, supplied, persuaded or compelled. Never conjure an army of thousands to make a cinematic scene, or treat every polity as capable of standing battalions.

Consequences must propagate beyond casualty counts: fewer workers and caregivers; damaged farms and trade; widowhood, succession and inheritance; interrupted learning, teaching and professions; food shortages; refugees; trauma, injury and recovery; inter-family grievances; shifts in legitimacy; and alliances or institutions that may endure for generations. A 15-person raid may have more historical consequence than a larger battle if particular participants and dependencies make it so.

Ranked magic changes military capability without removing the need for physical logistics, situated information, relationships, recruitment, organizational competence or exposure to actual countermeasures. A few powerful people might deter a war, destabilize an institution or make a coalition possible. They do not create extra population for free. Rare **cosmic or existential threats** may plausibly motivate extraordinary alliances and mobilization, but no threat is required to trigger scripted climaxes, and no emergency creates nonexistent soldiers or unsupported magical resources.

### Game 2 or later: expansion, not a debt Game 1 must repay

**Larger and fundamentally different population scales may belong to a later game or a future architecture generation**, particularly if better tooling or a more advanced simulation approach is necessary. Multi-kingdom politics, very large armies, continent-spanning supply systems, empires and millions of living people are **future ambitions, not Game 1 release requirements**. This is a scope boundary, not a cancellation or a promise of a particular sequel.

Preserve extensible IDs, world truth, causal semantics, bounded history access and versioned persistence where reasonable; do not force today's team to build a million-person runtime before delivering the 1,500-person kingdom. Game 1 must stand alone. Later technical work can expand it or inform a successor without retroactively making the original product incomplete.

## 54. Human and civilizational causality: research into why people and groups act

**Active evidence record:** [Human & Civilizational Causality — Research Record](research/HUMAN_CIVILIZATIONAL_CAUSALITY.md). This separate document maintains published sources, competing explanations, explicitly provisional hypotheses and proposed counterfactual tests; research does not automatically change gameplay canon.

**Research direction, not a claim of completed scientific validation.** To make unscripted love, leadership, innovation, cooperation, greatness, conflict, peace and war possible, ATE must investigate the underlying causes of those outcomes. Do **not** start from lists of compelling stories and then reverse-engineer NPC behavior to guarantee them.

Study human history and relevant empirical/theoretical work across individual psychology, social psychology, anthropology, political science, economic history, ecology, institutional economics, collective action, military history and disaster studies. Separate established evidence, contested theories, useful modeling approximations and fantasy-specific rules. Historical cases should inform *mechanisms*, not become plot templates or universal claims about human nature.

### Individual development: greatness is not a hidden stat

Distinguish **character and ethics**, **developed competence**, **social recognition**, and **historical consequence**. Exceptional influence may arise through an interaction of temperament, goals, sustained practice, opportunity, health, knowledge, environment, upbringing, mentors, social access, institutions, timing, luck and earlier consequences. No universal innate hero/villain/greatness score. Do not assume famous equals good or ordinary equals insignificant. A well-prepared farmer may save a community; an extraordinary fighter may leave only destruction; a capable scholar may go unrecognized because access was denied.

Build individual trajectories as feedback loops: experience changes memory, belief, skill, trust, resources, health, obligations and future opportunity. A person's choices must remain situated, uncertain, and changeable. Investigate the conditions that enable or block excellence, including ordinary failure, stable competence, unfair advantage, mentorship and cooperation.

### Group formation and durable coordination

Study how kin groups, crews, adventuring parties, households, workshops, guilds and settlements coordinate: shared purposes, complementary skills, trust, reciprocity, leadership, conflict resolution, collective knowledge, norms, institutions, training, access to resources and credible commitments. A group is not merely the sum of individual capability scores, but neither should it receive a free mystical teamwork bonus.

Group effectiveness should arise from what members actually know about one another, what routines and commitments they share, and what relationships and institutions persist. A party assembled through adventures may become extremely capable, fragment, or continue after its leader dies. Ordinary communities must have the same causal access to collective competence as player-associated groups.

### Conflict and war: explain causes and constraints

A conflict need not be driven by innate aggression, arbitrary faction hostility or an abstract war-frequency timer. Investigate interacting causes such as conflicting claims or interests, resources, unequal political access, leadership incentives, fear, inaccurate intelligence, grievances, social bonds, breakdown of negotiation, uncertainty about opponents, credibility of agreements and changing balances of power.

Also simulate the practical *capacity* for organized violence: willing or coerced participants, hierarchy, equipment, transport, food, money, communication, local support, terrain, rank asymmetry and the opportunity cost of removing people from ordinary life. Incentives and fears can produce a failed negotiation even when peace might be materially better; institutions, credible agreements, interdependence and trusted relationships can also prevent war. **The same pressure must be capable of producing cooperation, migration, adaptation or conflict depending on circumstances.**

Do not hard-code any fantasy race, ancestry, religion or cultural group as inherently warlike, cowardly, peaceful or destined to rule. Peoples, institutions and beliefs have history and internal diversity. Avoid false universal rules such as "drought causes war" or "trade guarantees peace."

### Environment is a pressure; vulnerability and response make the consequences

Climate, flood, drought, fire, disease, ecological change, monster activity and other hazards operate through actual systems, not narrative disaster schedules. The harm from the same physical event depends on settlement placement, food stocks, health, housing, infrastructure, transport, prior preparation, warning, resources, governance, trust, magic, and people's choices.

A drought can produce cooperation, altered crop choices, rationing, hardship, migration, banditry or political conflict. Every outcome should be traceable through real states and actions, not a disaster-to-plot lookup table. Investigate especially the social and economic mechanisms that make an event survivable in one community and catastrophic in another.

### Research outputs and experimental method

Prepare a **separate, evidence-grounded Human and Civilizational Causality research record** when the research work begins. Record for each proposed mechanism: the question, source/case, competing explanations, confidence and limitations, candidate world variables, causal process, required domain system, observable consequences, counterexamples, and expected computational cost. Promote findings into design authority only after scrutiny; this section is the research mandate, not proof all models are correct.

Test competing initial conditions using reproducible seed pairs and controlled counterfactuals. Useful questions include:

- Why did one talented person flourish and another lose access to training or opportunity?
- How did a particular group become coordinated, and what happened after a trusted leader left or died?
- Why did one water dispute end in negotiation while another escalated to raids?
- How did real farming, business preparedness, equipment or local trust change survival under hardship?
- What caused a kingdom to develop a school, establish a guild, lose specialist knowledge, or recover after a disaster?
- Which meaningful histories became accessible to a chef, merchant, scholar, parent or adventurer through legitimate information routes?
- When a seed experiences a long peaceful period, what institutions and incentives maintained it? When a seed stagnates, which causal opportunities were absent?

Do not require a war, spectacular romance, legendary leader or catastrophe in each seed. Seek credible, varied causal histories and meaningful gameplay; investigate stagnation without injecting scripted drama.

The results must eventually become **specific, bounded engineering hypotheses** for Agency and other existing systems: what facts are represented, when decisions occur, how resources constrain attempts, how group/institution processes resolve, how events persist, how subjective knowledge travels, and how simulation quality is measured over long timelines. Defer detailed implementations and tuning until Stage 0.5 closeout and subsequent authorized simulation development. Research does not require modifying persistence or implementing Stage 1 prematurely.

## 55. Population scale and simulation fidelity are separate engineering budgets

Stage 0.5 is primarily a **persistence, identity, history, retrieval, recovery and bounded-storage architecture investment**, not proof that millions of simultaneously living people can think, work, socialize and fight with full detail.

Distinguish at least three workloads:

1. **Historical scale:** Many distinct people, events, relationships, items and institutions recorded across centuries, most no longer actively living.
2. **Concurrent living population:** People whose biographies and material circumstances continue to evolve during the same world-time interval.
3. **Immediate high-resolution play:** Nearby actions, physics, combat, dialogue, animated characters, detailed spaces and precise reactions actually being experienced.

Do not infer one capacity from another. Paired 1,000/10,000 archived-history or page-backing tests establish properties of the tested history operations, **not** the ability to simulate 10,000 living agents. The historical roughly 1,300–1,500 living-person millennium workload is useful evidence for existing versions, not a promise of a million living people or a certified Game 1 performance envelope.

For a future larger population, explore legitimate variable-resolution and event-driven processing without granting distant people a different fictional physics. Active local people may require high-resolution interactions; regional people may update around obligations and consequential events; distant people may use coarser but still causally constrained schedules. **Less frequent computation must not mean fabricating accomplishments, learning, resources or changed relationships when the player returns.** Truth, knowledge, persistent identity, inventories, resource constraints and consequences remain authoritative at every resolution.

Measure separate budgets for storage, retained history, memory, CPU per simulated year, rendered-frame cost, local active people, number of interacting relationships, event volume, family growth, professional specialization, magical-rank ecology and extreme disasters. Test high and low population seeds, demographic variation and long-horizon sustainability—not only the mean headcount. Never use artificial population deaths, frozen offscreen lives or secret resource injection to hide performance defects.

**Game 1 acceptance focus:** a polished kingdom-scale 1,500-ish concurrent population with robust variation, sustainable historical change and richly playable lives on realistic target hardware. **Future scalability focus:** preserve architecture options for larger games without consuming Game 1's delivery budget to prove million-agent runtime today.

## 56. Scope decision register (Sections 53–55)

**Adopted:**
- Game 1 is a **complete, satisfying single-kingdom/kingdom-scale living RPG**, not a prelude that requires another title to become whole.
- Plan around approximately **1,500 simultaneous living people initially**, not 1,500 total people across all history; do not enforce a hard birth/death cap. Final acceptable population/performance range is evidence-dependent.
- Build an actual integrated playable vertical slice, then a credible public demo, then finish the connected kingdom as Game 1.
- Natural conflict at this scale is likely often personal or small-group; 100–200 total combatants is an **exceptional conceivable** event, never a forced quota. Cosmic threats may produce extraordinary mobilization but no artificial armies.
- Research individual/group/civilizational motives, cooperation, hardship, war prevention and conflict escalation to inform **causal mechanics**, not a story generator.
- Preserve deeper simulated personhood and meaningful consequences at the smaller geographical scale.
- Larger civilizations, armies, continents and potentially millions of living agents may belong to a future game/architecture; they are not dependencies of Game 1 or claims made about completed Stage 0.5.

**Open until tested/designed:** exact kingdom geography and settlement count; economically viable profession/rank/ecology distribution; demographic and simulated population limits; age and scope of generated prehistory; precise combat formations and recruitment; actual hardware budgets; what the public demo exposes; future sequel/expansion structure; and the evidence-supported causal rules derived from research.

**Do not infer implemented status** from a design section. No change here approves new Stage 0.5 scope, PR merge, million-person optimization work, population balancing or simulation-rule changes without explicit development authorization.

## 57. Essence-rank correction and future gameplay migration — Sol 6.1 / Astra handoff

**Status (2026-10-11): Owner-confirmed rules updated in Sections 2, 45 and 52; current implementation is NOT aligned. [GitHub issue #17](https://github.com/rax0h/all-that-endures/issues/17) is the tracking authority for the discrepancy and its later repair.**

### Exact conflict to avoid propagating

The older Section 2 mistakenly said all twenty abilities must be awakened before **Iron**, and historical completion metrics used this assumption. The owner clarified that **three base Essences cause the Confluence, and that moment makes the character Iron, ordinarily with 4/20 innate abilities**. **Bronze requires all twenty unlocked and each at Bronze**.

The existing \`simulation/ate_sim/advancement.py\` \`AdvancementState.rank(pid)\` instead returns the minimum rank of the **currently awakened** abilities, or zero if there are none. This reports **Iron for a one-Essence person** and can award **Bronze or higher before a Confluence or before twenty ability thresholds are satisfied**. \`simulation/tests/test_advancement.py\` explicitly asserts Iron after one Essence in \`test_absorbing_essence_intrinsically_awakens_catalog_innate\`. By contrast \`test_three_base_essences_form_person_shaped_confluence_and_innate\` already supports **automatic Confluence and four initial abilities**. \`simulation/ate_sim/institutions.py\` \`full_essence_user\` checks for Confluence/four Essences; audit its rank-adjacent consumers without conflating Society eligibility with bodily rank.

**Do not silently "fix" this in Stage 0.5 persistence.** Sol 6.1 is still implementing storage/identity/history, and Astra's Stage 0.5 review must remain evidence-based against its authorized contracts. This is a **deferred gameplay/rules migration**, not a Stage 0.5 release blocker unless a concrete persistence invariant depends on the old behavior. Historical tests and seed digests are previous-version evidence, not updated proof. No instructions here authorize rewriting old stored outcomes, changing population calibration or merging the active persistence PR.

### What must be addressed later

- Separate canonical **overall person rank**, **Essence completion milestone**, **per-ability rank**, and **unawakened ability slots**. Prove that a one- or two-Essence person with strong individual skills remains unranked, completing the Confluence enters Iron, and progression to Bronze waits for 20/20 at Bronze.
- Evaluate rank-body ontology, physiology/aging, rank ecology, institution eligibility, monster difficulty, economy, NPC advancement, rewards, save/restore, event causality and benchmark diagnostics for assumptions about \`AdvancementState.rank\` and any replicated rank fields.
- Introduce an explicit **rules version** and carefully designed save/benchmark migration or compatibility path if corrected ranks change observable old outcomes. Preserve deterministic source-specific historical artifacts; no retroactive in-place reinterpretation.
- Add focused regressions for zero to three Essences, Confluence, four innate skills, stone-unlocked remaining sixteen, partially elevated/missing skills, and all-twenty Bronze gate. Run an affected integration suite and Astra's independent review before adoption.
- Design character creation to preserve world scarcity and provenance: no freely spawned rare material, no self-selected Confluence, no unearned twenty-skill unlock and no automatic rarity-derived superiority.
- Treat **Transcendent** Essence access as **aspirational/unresolved rarity ontology** until the actual catalog, world rules and interactions distinguish it from transcendent/divine *powers beyond the normal twenty-ability framework*.

### Source boundaries

The locally supplied rank-ecology design note supports qualitative rank expressions, twenty abilities as a capability ecology, and separation between normal Essence abilities and exceptional external powers. The supplied Jason Asano sheet illustrates 4/4 Essences, 5/5 abilities per Essence and other exceptional powers, **but does not itself establish the Iron-onset or Bronze-gate rule**. The **owner's explicit 2026-10-11 design decision** is authoritative for those thresholds; do not misattribute them to the sheet. See issue #17 for exact source paths/test names.

**Priority:** Document now; **implement only after explicit gameplay authorization outside Stage 0.5**. Sol and Astra may acknowledge the item in their future architecture reviews without interrupting the currently authorized persistence effort.
