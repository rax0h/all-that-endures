# P4.9 — social graph lazy migration plan

**Date:** 2026-10-05
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and accepted P4 behavior through P4.8.

## Residual evidence after P4.8

Run `37409691977` on product head
`0ae6f1f1a1498cc963f0a2c74903742b7da0f540` measured the post-P4.8
residual eager graph.

At 10,000 synthetic relationship pairs:

- `world.social.edges`: 4,236,678 payload bytes / 10,000 rows;
- `world.social.adjacency`: 1,037,784 payload bytes / 20,000 rows;
- `world.social.partnerships`: 407,784 payload bytes / 10,000 rows.

The coherent social family therefore retains about **5.68 MB** and ordinary
residual open still scales from 19,035 reads / 2.71 MB at 1k to
190,035 reads / 27.42 MB at 10k.

## Scope

Migrate all three social collections together:

- `world.social.edges`;
- `world.social.adjacency`;
- `world.social.partnerships`.

Do not redesign social semantics in this tranche. Preserve the redundant
adjacency and partnership archives as authoritative stored collections; the
goal is bounded loading, not normalization.

## Edges

`Relationship` becomes tracking-aware without changing fields.
Each pair remains keyed by `(min(a,b),max(a,b))`.

Persist checked endpoint memberships for both people so
`relationships_for(pid)` can load only incident edges. The mutable
`shared_history` list remains identity-bearing and tracked. Direct scalar
edits and shared-history mutations dirty only that relationship owner.

The old `_relationships` strong-reference cache must not pin all loaded
relationships. Lazy sessions use the endpoint membership index directly;
ordinary eager worlds may retain compatibility behavior if desired.

## Adjacency

Each person -> neighbor-set row is lazy and bounded. Existing
`neighbors(pid)`, `get()`, direct set mutation, insert/delete/reinsert,
dictionary order, and pickle/checkpoint behavior remain exact.

The set itself remains identity-bearing. Retained neighbor-set aliases survive
clean-cache eviction and rebind to the same persisted incarnation.

## Partnerships

Each pair -> formation-event row is lazy. Persist checked endpoint memberships
for both people. `living_partnerships(people)` must use these memberships
rather than rebuilding/scanning the full partnership archive, including after
reopen and after unsaved local edits.

The legacy `_partnership_index` cache is not authoritative in lazy sessions
and must not recreate archive-sized memory.

## Acceptance

- ordinary lazy open decodes zero payloads from all three social namespaces;
- `social.get(a,b)` loads at most one existing edge or creates one row;
- `relationships_for(pid)` loads only incident edges;
- `neighbors(pid)` loads one adjacency bucket;
- `living_partnerships(living_people)` touches only partnerships incident to
  the living IDs and returns exact pair/event mappings;
- clean cache <=256 owners/table;
- direct relationship scalar edits and `shared_history` mutations save/reopen;
- adjacency set mutations save/reopen;
- partnership insert/replace/delete save/reopen and update endpoint queries;
- no-op save writes zero social payloads;
- one changed owner writes bounded evidence independent of total social history;
- materializing detach restores plain dict/set/list-compatible graph state;
- history archive export still emits relationship shared-history/event links and
  partnership partner/formed-event links;
- existing `test_living_partnerships.py`, agency, households, worldgen and P4
  identity/lifecycle regressions remain green;
- 1k -> 10k social history keeps ordinary-open social payload loads at zero and
  fixed relationship/partnership queries bounded.

After P4.9 closes, rerun residual inventory and continue by measured cost.
