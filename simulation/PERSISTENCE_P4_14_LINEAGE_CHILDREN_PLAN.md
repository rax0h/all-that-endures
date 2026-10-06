# P4.14 — sharded lazy lineage children

Post-P4.13 residual run 37502904071 leaves one unbounded eager family:
`world.lineage.children`.

Measured residual:
- 1k: one bucket / 42,926 payload bytes
- 10k: one bucket / 438,927 payload bytes

The remaining larger family, `world.agency.actions`, is explicitly capped at
50,000 rows and is not an unbounded P4 blocker.

A simple lazy parent->set row is insufficient because one parent bucket can grow
without bound. P4.14 therefore splits storage into:

1. `world.lineage.children`: one small parent-bucket authority row preserving
   parent-key insertion order, bucket existence, bucket mutable identity, and
   current child count.
2. `world.lineage.child_edges`: one scalar edge row per
   `(parent_key, child_key)`, indexed by parent.

The runtime mapping still exposes the existing
`dict[parent_key] -> set[child_key]` behavior. The returned set facade supports
membership, len, iteration, add/discard/remove/pop/clear/update and the ordinary
set mutation operators. Ordinary `setdefault(parent,set()).add(child)` remains
bounded and is the hot registration path.

Acceptance:
- ordinary lazy open decodes zero lineage-child bucket/edge payloads;
- retrieving a bucket decodes only its small bucket record, not all children;
- membership and add/remove are O(1)-style checked point operations independent
  of total lineage size;
- len uses the small bucket count and does not enumerate edges;
- full iteration materializes only when explicitly requested and may scale with
  that requested bucket;
- one edge add/save remains bounded from 1k to 10k;
- parent bucket identity survives save/reopen and materializing detach;
- arbitrary supported set edits preserve exact set contents;
- delete/reinsert preserves top-level dict ordering;
- register updates the lineage node and child edge in one hybrid generation;
- focused, scaling and affected gates pass.

After P4.14, rerun residual eager inventory. If only bounded/capped/fixed
families remain, proceed to integrated P4 closeout.

P4.14 focused run 37507068538: 10/10 passed in 4.19s.
