# Stage 0.5: current state and historical truth

## Contract

Simulation owns reality. Selection probability never depends on player
relevance. An index, compressed segment, inspector, renderer or narrator is
not a second authority. No rank, economy or recruitment calibration is part
of this pass. The owner accepts sparse Diamonds and naturally empty Iron
graduation years. The former 120-second millennium target is an optimization
goal, not a reason to change the world model.

## Implemented separation

* Identity-bearing records remain in their authoritative dictionaries.
  `RecordTable` supplies rebuildable field-value indexes. Assignment to an
  indexed record notifies its table; inserts, replacements and removals also
  invalidate the affected memberships. Queries repair changed rows only.
  Notification links and indexes are not checkpoint or canonical facts.
* Living people, active households, open/assigned notices, pending
  applications, active threats/wars/inquiries and property owners use those
  indexes. Historical records are not deleted. Inheritance starts from living
  children and follows real genealogy to an inactive parent's household;
  estates with no living eligible heir remain real property.
* `EventLog` retains consecutive event IDs and chronological order. Segments
  of 2,048 completed events older than the two-year working window become
  losslessly compressed bytes. A four-segment read cache and current tail
  bound resident event objects. A sparse year-to-offset index makes recent
  queries independent of archive length. Cold records are immutable, including
  nested dictionaries/lists; correction requires another causal event.
* The compressed bytes belong to the world and travel in its checkpoint.
  They are not an optional cache, inferred summary, regenerated narrative,
  or external dependency. Old event IDs, actors, causes and payloads still
  resolve. SQLite export streams them without unpacking all history at once.
* Canonical hashing streams the established JSON representation rather than
  materializing a second expanded copy of the entire world. Storage layout,
  index construction, segment boundaries and read-cache contents do not affect
  the digest. Checkpoints remain trusted local pickle data, not an untrusted
  interchange format.

## Determinism correction, not calibration

The old low-skill crafting selector chose an index into a Python set. A
checkpoint can reconstruct the same set with a different iteration order.
On the unchanged PR #14 implementation, founder seed 843000 saved at year 110
first diverges at year 121: the same crafter selects material 4436 versus 341.
The existing short resume test did not reach that failure.

Material selection now uses ascending stable IDs. A Fenwick-count inventory
selects the kth available lot in logarithmic time; arrivals and exhaustion
update it incrementally, with amortized compaction of empty slots. Every
eligible lot retains the same uniform probability; price, ownership,
availability, quantity, RNG draws and crafting rules are unchanged. This
necessary ordering correction changes fixed-seed outcomes. It is not valid
to claim the former canonical millennium digest still applies. The new
100-year founder reference is
`df38fe532db745b33d2e4bc36b45bd509273083f7b64e0311b88eeb9e5fba300`.

A sparse-ID fixture exposed the same pre-existing defect in church followers:
the church consumed a shared RNG stream in Python set order. The follow-up
processes the intersection of living IDs and historical membership in sorted
ID order. It preserves membership and grant probability, and avoids walking
deceased followers. Material summation order and archive set-membership link
ordinals are now stable as well. The founder golden above remains unchanged;
the previously measured millennium is historical evidence for the preceding
implementation, not a golden for this further correction.

Storage/index changes alone, before this correction, reproduced the exact
baseline digest after replaying years 1001–1020 from the saved seed-843010
world: `db0537187e6099c77e8cd39ad4e1cb914e9f01e31fe0d9a629f8e8f6eb9f4dfc`.

## Interactive continuation boundary

The owner intends a save to remain playable without a designed end date. This
is a continuing-world contract, not a promise of infinite history in finite
storage. World age alone must not determine annual processing or autosave cost.
Genuinely expanding active populations, institutions or inventories may require
more work, but routine queries must not inspect every retained object merely
because it exists. Historical storage can grow on disk; stable IDs, provenance
and exact recovery cannot expire. Incremental persistence and bounded resident
working sets remain required follow-up, not features already delivered here.

The current annual step is historical-generation resolution, not an
implementation of real-time gameplay. Do not claim that calling it once a
second produces equivalent gameplay.

Future player and NPC commands must enter the same authoritative mutation
operations: ownership transfers, resource consumption, bodily progression,
death, construction and institutional decisions. Those operations validate
current state, mutate real records, then append causes. A controller may
choose an action; it may not bypass prerequisites or author replacement facts.
The active indexes observe these mutations regardless of who initiated them.

When subannual causality is implemented, introduce an explicit ordered time
and action/scheduling contract, including tie-breaking and replay, before
mixing resolutions. Player-local detail must refine the same world state.
Distant batching is valid only with a demonstrated equivalent causal result,
not an aggregate substitute for people or ownership that could matter later.
No speculative scheduler, parallel gameplay world or Stage 1 mind model is
introduced here. Objective records remain distinct from future observations,
memories, beliefs and authored interpretations.

## Limits and validation

The next persistence implementation must follow
[INCREMENTAL_PERSISTENCE.md](INCREMENTAL_PERSISTENCE.md): explicit record
ownership and mutation coverage, atomic publication, identity-safe lazy reads,
unchanged canonical validation, and staged implementation. That contract is a
design, not an already implemented replacement for schema-8 checkpoints.

Compressed events still consume storage proportional to history. Other
identity-bearing archives (people, materials, paths, transmissions and items)
are still resident records. Unconsumed stock is genuinely current property;
calling it old does not justify deleting it. This pass does not promise
constant total RAM or infinite play. Disk-backed cold segments/record pages
can later implement the same ID/query contract without changing truth.

`long_history_scaling.py` measures 250-year blocks with separate inspections,
active population/ranks, currency conservation, configuration/body/ability
invariants, recent causal links, resource counts, Iron renewal and resident
event statistics. State audits do not replace chronological progression
validation. Full archive export is an explicit post-run action, not a
milestone side effect. Checkpoint/resume and compressed/plain archive tests
protect exact truth and continuation. Measurements and the freeze verdict
belong in `LONG_HISTORY_VALIDATION.md`; do not infer readiness from this design
description alone.
