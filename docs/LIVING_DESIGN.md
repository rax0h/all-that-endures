# ALL THAT ENDURES — Living Design Document

**Status:** Living design authority for new simulation direction.  
**Last cohesive update:** 2026-09-15  
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

A ranked person cannot exist without a complete magical path. All essences/confluence requirements and **all twenty abilities must be unlocked** before rank progression is valid. This applies even at Iron. An incomplete twenty-ability path is unranked, not a partial Iron character.

Recent validated PR #5 baseline: 91.55-second millennium run; 15 completed twenty-ability paths and therefore 15 ranked living paths (1 Iron, 2 Bronze, 3 Silver, 6 Gold, 3 Diamond), while 47 incomplete paths remain rank 0. Chronology/progression and wallet/treasury validation passed. The remaining concern is calibration rather than correctness: completion/access/liquidity is too low for the intended mature-world population, especially Gold.

### Four mastery stages inside every rank

Do not rebalance the established time-to-rank curve merely to add visible progression. Divide each existing per-skill rank interval into four equal stages.

- Each of the twenty skills independently occupies Stage 1, 2, 3, or 4, with 0.0–100.0% progress through that stage.
- Stage 1 = first 25% of the existing rank interval; Stage 2 = 25–50%; Stage 3 = 50–75%; Stage 4 = 75–100%.
- `Iron 3 — 0.0%` means that skill is halfway from Iron to Bronze.
- Crossing Stage 4 at completion advances that skill to Stage 1 at 0.0% of the next rank.
- Example: `Hand of the Reaper — Silver 3 — 45.0%`.
- Character rank advancement remains gated by all twenty skills meeting the required threshold.

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
