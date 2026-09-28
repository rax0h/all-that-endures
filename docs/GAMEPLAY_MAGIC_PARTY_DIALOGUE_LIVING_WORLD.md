# ATE — Gameplay, Magic, Party, Dialogue & Living World Notes

## Core Vision

ATE is intended to become a full 3D, AAA-quality RPG built on top of the deep simulation already being developed.

The long-term game should allow the player to physically inhabit a world that has already lived for roughly a thousand years before the player enters it, and that world should continue evolving while the player is present.

The goal is not merely to generate historical events. The simulation should generate people whose lives, relationships, beliefs, ambitions, failures, families, economic pressures, magical development, institutions, memories, and choices create history.

The player should feel that the world did not come into existence for them.

The project should be approached as a question of when the complete game is delivered, not whether it can be.

---

## Story Generation

ATE’s story generation should emerge primarily from people rather than from procedural quest templates.

The simulation is already moving toward individuals having:

- subjective memories
- asymmetric relationships
- motives and values
- self-concept
- professions
- families
- economic/material circumstances
- cultural background
- language/register
- magical abilities and development
- institutional affiliations
- personal histories
- incomplete or incorrect knowledge

Those systems should eventually produce stories because people act from their own histories and circumstances.

The challenge is not only generating rich lives but making those lives legible to the player.

History should surface through things such as:

- conversations
- rumors
- grudges
- friendships
- marriages and families
- inheritance disputes
- buildings and ruins
- magical traditions
- schools and teachers
- letters
- memorials
- abandoned projects
- damaged infrastructure
- local legends
- conflicting historical accounts
- institutions
- economic conditions
- scars left by wars, monsters, disasters, and ordinary human choices

The simulation should avoid reducing these things into generic quest markers.

A generated tragedy is wasted if the player only experiences it as:

> “Recover stolen sword — 250 XP.”

---

## Final Game Presentation

The envisioned final game is fully 3D with a large traversable world and AAA-quality art.

The player may ultimately play in first person, third person, or potentially have access to both perspectives depending on what proves best.

The world simulation should remain underneath the graphical game rather than being replaced by a conventional scripted RPG layer.

The world the player walks through should be the same world the simulation produced.

---

## Combat Direction

Two major inspirations currently fit ATE:

### Souls-like / real-time

Real-time combat would allow magic to feel physical and spectacular.

It would support:

- dodging
- blocking
- physical positioning
- movement abilities
- terrain use
- destructive magic
- aura pressure
- transformations
- monsters with large physical presence
- highly kinetic high-rank combat
- the feeling of magical power actually erupting into the environment

ATE’s progression-fantasy scale could look extraordinary in real time.

### Baldur’s Gate-like / tactical

Turn-based or heavily tactical combat would better expose the depth of ATE’s systems.

It could support:

- large ability sets
- complicated magical interactions
- statuses
- positioning
- companions
- familiars
- rituals
- terrain manipulation
- coordinated party strategies
- different character builds
- deliberate use of magical combinations

No final choice needs to be made yet.

---

## Possible Hybrid Direction

ATE should probably not maintain two completely separate combat systems.

One possible direction is:

**real-time physical combat with tactical decision windows.**

Movement, positioning, dodging, blocking, basic attacks, aiming, and immediate combat continue in real time.

More complicated magical or party decisions could invoke strong slow-time or near-pause tactical windows.

This could preserve real-time spectacle while allowing the player to meaningfully operate complicated magical systems.

The fundamental distinction would be:

**thinking time vs. execution time**

rather than:

**turn-based mode vs. action mode.**

This is only a possible direction and should remain open until the magic and combat systems themselves tell us what works best.

---

## Magic Expression

Magic in ATE should not behave like a normal RPG spell list where every ability is simply:

**button → animation → effect.**

The books and world imply a much wider range of magical expression.

Magic can involve:

- spoken spells
- gestures
- symbols drawn or carved into the ground
- rituals
- preparation
- magical objects
- environmental components
- emotional triggers
- familiars
- bodily manifestations
- aura effects
- spontaneous eruptions
- magic simply exploding out of a person

The way magic happens should be a meaningful part of an ability and potentially a meaningful part of a person.

---

## Possible Ability Dimensions

Future magic/ability modeling should consider first-class properties such as:

### Invocation

How the ability is initiated.

Examples:

- spoken phrase
- shouted word
- whisper
- gesture
- mental command
- prayer
- inscription
- physical movement
- emotional trigger
- object interaction
- ritual sequence

### Preparation

How much setup the ability requires.

Examples:

- instantaneous
- brief concentration
- several seconds
- prepared ground
- constructed ritual
- minutes
- hours
- group ritual

### Manifestation

How the magic physically appears.

Examples:

- projected outward
- erupts from the body
- surrounds the user
- changes the environment
- creates a construct
- summons something
- affects an object
- spreads through an aura
- alters another magical effect

### Control

How precisely the user can direct it.

Examples:

- precisely targeted
- loosely directed
- autonomous
- partially uncontrolled
- highly dangerous to contain

### Persistence

How long it remains.

Examples:

- instant
- sustained
- channeled
- lingering
- semi-permanent
- permanent alteration

### Conditions

What must be true for the ability to work.

Examples:

- voice available
- free hands
- prepared symbols
- particular materials
- existing fire
- certain terrain
- another participant
- environmental condition
- specific magical state

### Consequences

What using the ability leaves behind.

Examples:

- exhaustion
- physical injury
- magical residue
- altered terrain
- disrupted aura
- visible evidence
- instability
- attention from other magical entities or people

---

## Magical Traditions and History

The same underlying magical principle may manifest differently depending on:

- culture
- teacher
- school
- region
- personal discovery
- personality
- experience
- historical tradition

One person may perform a carefully taught spoken invocation with precise posture and gestures.

Another person may have discovered a similar effect independently and manifest it violently without words.

These differences could propagate through teaching.

That means magical techniques themselves can develop historical lineages.

A symbol used in year 1000 could exist because someone hundreds of years earlier discovered that a particular geometry stabilized an otherwise dangerous ability.

That knowledge could pass through apprentices, schools, cultural traditions, and divergent branches.

This makes magical archaeology possible.

The player may encounter ancient symbols, rituals, or techniques that are ancestors of modern magical practices.

---

## Magic and Balance

The existing skill/ability balance should be deliberately re-audited when these manifestation dimensions are introduced.

Invocation, preparation, manifestation, control, conditions, persistence, and consequences all alter the practical strength of an ability.

An instantaneous silent ability may be dramatically more useful than an equally powerful ability requiring ten seconds of spoken preparation.

These properties should not be reduced to simplistic formulas such as:

> “+3 seconds casting time = +20% damage.”

They should create qualitative tradeoffs.

Examples:

- spoken magic can be interrupted or overheard
- ground symbols require space and time but may allow much larger effects
- rituals may accomplish things impossible during ordinary combat
- uncontrollable eruptions may be extremely powerful but dangerous
- silent/internal magic may be difficult to interrupt but have other costs

The simulation must also avoid optimizing all magical diversity away over centuries.

Different styles of magic need to remain viable enough that cultures and traditions can retain meaningful variation.

Future magic-system changes should therefore include:

1. an audit of the existing skill/ability balance
2. implementation of manifestation dimensions as first-class properties
3. generation/balance testing to ensure one manifestation style does not dominate all others over long simulation periods

---

## Party Gameplay

ATE should support parties ranging from intimate two-person teams to groups of roughly six people.

A major design principle is:

> The player should know their team and trust them to do their jobs.

Companions should not feel like unreliable AI attachments that require constant babysitting.

Characters should be capable autonomous combatants.

---

## Party Synergy

Party members should be able to develop genuine tactical synergy.

Examples:

- one person holds enemies away from a ritualist
- one specializes in interrupting spoken magic
- one creates terrain another character exploits
- one protects a fragile caster during preparation
- one creates an opening another recognizes and immediately uses
- familiars or summons coordinate with multiple members
- abilities become especially effective when used in known combinations

Team synergy should not merely be a static numerical bonus.

Characters who have fought together for twenty years should coordinate differently from strangers.

They should learn:

- each other’s timing
- ability tells
- preferred tactics
- strengths
- weaknesses
- likely reactions
- habitual combinations

A highly familiar companion might begin reacting to another character’s ability before the invocation is complete because they already know what is coming.

---

## Party Member Control

A major gameplay priority is opening play opportunities for the player.

Any active party member should potentially be directly playable.

This would allow the player to experience multiple very different combat styles within the same party and campaign.

Examples:

- melee combatant
- ritualist
- ranged caster
- controller
- support specialist
- familiar/summon-focused character
- defensive fighter
- highly mobile magical combatant

The player might stay with one character for an entire battle or frequently swap between several.

When direct control leaves a character, that character should immediately return to competent autonomous behavior.

The model should therefore be:

> Every party member is both a full playable character and an autonomous person.

Direct control should be optional, not required to compensate for bad AI.

---

## Tactical Commands

Even without directly swapping, the player should be able to issue useful lightweight tactical commands such as:

- hold this position
- protect this person
- interrupt that caster
- prepare this ritual
- focus that enemy
- fall back
- cover me

A player should be able to operate anywhere along a spectrum between:

**trusting their team almost completely**

and

**personally controlling nearly every important action.**

---

## Party Members Outside Combat

Character swapping may also matter outside combat.

Different party members possess different:

- knowledge
- relationships
- reputations
- physical capabilities
- magical abilities
- histories
- cultural backgrounds

The person currently interacting with the world should matter.

Examples:

A blacksmith may dislike the protagonist but have known one companion since childhood.

One character may recognize an ancient magical notation that everyone else misses.

One may understand a regional dialect.

One may be able to survive an environment the others cannot.

This should not become a simplistic “choose the highest Charisma character” system.

It should come from the actual people and their histories.

The party should feel like a group of protagonists, not one protagonist carrying five followers.

---

## Generated Voices

Modern generative voice technology makes ATE’s scale of simulated people much more feasible.

The game may eventually contain thousands of people capable of saying things that were never pre-written.

Traditional fully authored voice acting cannot cover that possibility alone.

Each person could instead have a persistent voice identity influenced by things such as:

- age
- physiology
- region
- culture
- language
- upbringing
- social environment
- education
- personality
- emotional state
- fatigue
- conversational register
- current relationship with the listener

Voices should remain coherent across a character’s life.

Regional accents, school registers, family influence, migration, aging, and social background may all shape speech.

Any real performers or voice data used should be licensed and handled with explicit consent and appropriate compensation.

Important authored characters could still receive additional human performance or direction.

---

## Free-Form Conversation

ATE should not rely primarily on prewritten dialogue wheels.

The player should be able to communicate naturally through:

- keyboard input
- microphone input

Both should feed into the same underlying conversation system.

Example:

Instead of choosing:

1. Ask about the ruins
2. Ask about her father
3. Leave

the player could simply type or say:

> “Why did you hesitate when you mentioned the ruins?”

---

## Simulation-Constrained Dialogue

NPCs should not behave like omniscient chatbots.

A character’s answer must be constrained by what that person actually:

- knows
- remembers
- believes
- wants
- fears
- suspects
- misunderstands
- chooses to reveal
- chooses to hide

Characters may:

- lie
- misremember
- refuse to answer
- change the subject
- misunderstand the player
- confidently believe something false
- protect another person
- reveal only part of what they know

The language-generation system handles expression.

It should not freely create canonical facts.

The simulation remains the authority.

---

## Conversational Context

When a conversation occurs, the game can construct a temporary context containing relevant information such as:

- who the NPC is
- what they know
- what they remember
- current motives
- personality
- current emotional state
- relationship with the speaker
- cultural and linguistic register
- recent events
- important relationship history
- information being intentionally concealed
- immediate surroundings

The generated response must remain inside those boundaries.

---

## Conversation Depends on Who Is Speaking

Because party members are actual people, an NPC may respond differently depending on which member of the party is currently speaking.

The world should not respond to an abstract entity called “the player.”

It responds to the person being controlled.

Someone may hate one party member and trust another.

Someone may recognize one companion’s family name.

Someone may respond to a shared history unknown to the rest of the group.

This makes party switching relevant socially as well as tactically.

---

## Voice Input

Microphone input can eventually add another layer of immersion.

The player could naturally talk to characters rather than selecting dialogue options.

Voice input should remain optional.

Keyboard input should always remain available for:

- precision
- privacy
- accessibility
- situations where speaking aloud is inconvenient

The important feature is free-form communication, not the particular input method.

Potentially, limited vocal information such as shouting, whispering, or calm speech could matter where appropriate, but the system should not rely on unreliable attempts to perfectly infer emotional state from voice.

---

## Social Texture and Unscripted Encounters

ATE needs a very broad range of human behavior.

The world should contain far more than useful quest NPCs.

Possible people encountered in towns and streets include:

- eccentric people
- lonely people
- drunks
- zealots
- hustlers
- grieving people
- compulsive talkers
- paranoid people
- street preachers
- performers
- con artists
- veterans
- beggars
- wealthy people
- children
- people asking for help
- people who recognize a party member
- people who simply want someone to talk to
- unusual inventors
- obsessives
- hermits
- reckless people
- exceptionally generous people
- people pursuing strange personal projects

These should emerge from simulated people rather than from a generic:

> “5% chance of weird NPC encounter.”

---

## Not Every Interaction Is a Quest

This is fundamental.

A stranger may approach the party and there may be:

- no quest
- no reward
- no hidden objective
- no major plot significance

They are simply a person doing something.

Someone may say something bizarre.

They may be:

- wrong
- lying
- confused
- eccentric
- intoxicated
- genuinely insightful
- describing something real that nobody believes

The player decides whether it matters.

Someone claiming to have discovered awakening without stones might be a fraud.

Or they might not be.

The game should not immediately tell the player which.

---

## Restraint in Ambient Interaction

The social world should be rich without becoming noisy or artificial.

Most people should leave the player alone most of the time.

If strangers constantly interrupt the player, unusual encounters become background clutter.

Therefore, when someone actually crosses the street and deliberately approaches the party, the player should notice.

Rarity gives these interactions weight.

---

## Human Outliers

The personhood simulation must permit genuinely unusual people.

If every simulated character is rational, psychologically tidy, and optimized toward sensible goals, the world will feel artificial.

Some people should:

- develop obsessions
- hold irrational beliefs
- behave recklessly
- dedicate decades to strange projects
- isolate themselves
- pursue hopeless goals
- repeatedly tell the same stories
- misunderstand important events
- become unusually generous
- become difficult or abrasive
- create things nobody asked for

These outliers may generate some of the most memorable emergent stories in the game.

---

## The Larger Goal

ATE should not merely simulate important people.

It should simulate enough of the breadth of human life that wandering through a town can remain interesting even when nothing traditionally “important” is happening.

Ultimately the loop becomes:

**simulation → lived experience → memory → belief/personality/relationship → behavior → dialogue → voice/performance → player response → new simulation consequences**

The player is not consuming a prewritten history.

They are entering an already living history and becoming another causal participant inside it.
