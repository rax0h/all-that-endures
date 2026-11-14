# First playable versus formal performance targets

Response to Daniel's question during the ongoing speed work. This is an
engineering interpretation, not a relaxation of Stage0.6 acceptance.

The benchmark advances an entire simulated year and saves persistent World
state. It does not measure a button press, movement, conversation, combat frame
or UI response. Annual throughput alone neither proves nor rules out playable
interaction. The current synchronous calls would block their caller; background
work and responsive presentation are not demonstrated by these fixtures.

General usability reference: [Jakob Nielsen, Response Times: The 3 Important Limits](https://www.nngroup.com/articles/response-times-3-important-limits/).
About0.1s feels immediate, about1s preserves interaction flow; longer operations
need appropriate feedback and handling. These are guidance, not universal game
simulation cutoffs.

For an early ATE prototype, a reasonable proposed bar is immediate visible input
feedback and ordinary player requests around1s or less. A rare turn/world advance
of a few seconds can be workable with feedback; a several-second save can be
workable if controls and required state access remain responsive in the background.
This requires an actual interactive test under load, not a theoretical division
of annual time into days/frames or an assumed asynchronous implementation.

Current small-world throughput is compatible with trying a coarse turn-based
prototype, but responsive live gameplay and mature-world behavior remain unproven.
Formal goals remain10sopen/2ssave/1swarm with exact state and deterministic
continuation. They provide performance/scale headroom; they are not a universal
boundary below which all games are interactive and above which none are playable.
