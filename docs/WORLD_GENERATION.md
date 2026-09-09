# World Generation

## Principle

A new game begins before history. The physical world is generated first; history then happens inside it.

`World Seed -> Physical World -> Ecology/Resources -> Initial Peoples -> Historical Simulation -> Playable Present -> Player Divergence`

The map is the world. It is not a high-resolution player bubble surrounded by invented flavor geography.

## Physical world

The intended topology is one primary connected Pangaea-like continent, with room for islands, inland seas and other secondary features where generation produces them. The world generator should support coherent variation in:

- coastlines and drainage basins;
- elevation, mountain chains, passes and valleys;
- geology and resource distribution;
- rivers, lakes, wetlands and floodplains;
- latitude/climate logic, seasons and prevailing weather;
- forests, grasslands, deserts, tundra and other biomes;
- soil/fertility and ecological productivity;
- habitats and natural movement corridors;
- defensibility and human travel corridors.

The generator must create causal starting conditions, not prewritten historical scenery. Ancient ruins, legendary battlefields, dynastic capitals and sacred monuments are historical outputs, not map-generation decorations.

## Scale

Do not assume Earth scale. Choose a world size that creates meaningful travel, regional separation, climate/biome diversity and long-range exploration while remaining simulatable and realizable as a game world.

Rank changes the experienced scale of the same geography. A journey that defines an ordinary person's world may become routine for a sufficiently advanced person. The map need not expand to create that progression.

Exact world dimensions are unresolved.

## Determinism

Separate at least:

- **World Seed**: immutable natural starting conditions.
- **History Seed**: stochastic historical evolution before the player's entry.
- **Player-era stochastic stream(s)**: deterministic/replayable randomness after entry.
- **Simulation/realization version identifiers**: required to reproduce a world under evolving software.

Seed streams should be partitioned so unrelated implementation changes do not unnecessarily reshuffle the entire world.

## Historical impartiality

The simulation does not know which town the player will start in or where a generated adventure will eventually lead.

> **Player relevance may determine resolution, never probability.**

Narrative systems may discover that a faraway event is compelling and give the player reasons to travel there. They may not cause the event because the player needs content.

Peaceful regions and eras are valid outputs.

## Geography as causal pressure

Geography changes probability rather than dictating destiny. A narrow mountain pass can affect migration, language separation, trade, settlement wealth, fortification, war and later memory. The fortress exists because history made it sensible, not because a level designer tagged a mountain biome as needing a castle.

The World Causality Graph must preserve these chains at an appropriate resolution.

## Historical landscape

Physical geography can itself change through erosion, river migration, flooding, fire, vegetation succession, land clearance, mining, construction and magical/environmental events. Historical terrain change must be representable without requiring every square meter to be simulated at maximal resolution for millennia.

## Reachability rule

Every concrete location asserted by objective generated history must be grounded in the simulated world. A character may believe in a nonexistent golden city; that belief can be wrong. But the belief, its transmission and what actually exists beyond the mountains all belong to the same causal world.