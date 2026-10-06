# P4.11A — lazy lineage nodes

**Date:** 2026-10-05
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and accepted P4 behavior through P4.10.

## Residual evidence

Post-skills residual run `37413656322` measured ordinary open at:

- 1,000-row fixture: **9,035 payload reads / 1,036,546 bytes**;
- 10,000-row fixture: **90,035 payload reads / 10,423,592 bytes**.

`world.agency.actions` is larger but explicitly capped at 50,000 rows, so it
is not an unbounded-history blocker. The largest remaining unbounded row
namespace is `world.lineage.nodes`: **10,000 rows / 1,966,678 payload bytes**.

## Scope

Migrate only `world.lineage.nodes`.

Leave `world.lineage.children` eager in P4.11A. Re-measure after nodes are
removed from ordinary-open cost before deciding whether the children index
needs its own P4.11B slice.

Each `(kind,id)` key owns one scalar `LineageNode`. Parents are immutable
typed-reference tuples. Preserve exact `register()` and `ancestors()`
behavior and all lineage/history-archive semantics.

## Acceptance

- ordinary lazy open decodes zero lineage-node payloads;
- `nodes.get(key)` and direct indexing load only requested rows;
- `ancestors()` performs only bounded point reads implied by traversal depth;
- `register()` inserts a lazy node while continuing to update eager children;
- direct scalar field edits save/reopen;
- clean cache <=256 nodes;
- no-op save writes zero lineage-node payloads;
- one changed node writes bounded evidence independent of historical node count;
- insert/delete/reinsert preserves dictionary order;
- materializing detach restores a plain dict of `LineageNode` records;
- history archive export remains unchanged;
- 1k -> 10k node history keeps ordinary-open lineage-node payload work at zero.

After focused + scaling + affected gates, rerun residual inventory.


## Focused and scaling evidence

Product implementation head: `b7e006345e0ddb0d76b1240c6c67c068fece4a98`.

Corrected focused run `37414711945` passed **9/9 in 38.09s**.

Scaling run `37415118779` passed the 1,000/10,000 bounded-work proof:

| Measure | 1,000 nodes | 10,000 nodes |
| --- | ---: | ---: |
| ordinary-open payload reads | 33 | 33 |
| ordinary-open payload bytes | 16,658 | 16,660 |
| fixed ancestor-walk payload reads | 3 | 3 |
| fixed ancestor-walk payload bytes | 588 | 588 |
| one-node save payload writes | 3 | 3 |
| one-node save payload bytes | 357 | 357 |
| resident lineage nodes | 3 | 3 |

The broad affected P4 regression gate is still required before P4.11A is
accepted closed.
