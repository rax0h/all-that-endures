# P4.12 — lazy genealogy

Post-P4.11A residual run 37477473930 shows genealogy is the next unbounded family:

- world.genealogy.parents: 10,000 rows / 527,784 bytes
- world.genealogy.children: 10,000 rows / 517,788 bytes
- combined: about 1.05 MB

world.agency.actions is larger by bytes but is explicitly capped at 50,000 records.

## P4.12A — parents

Migrate world.genealogy.parents first. Each child ID owns one immutable tuple of parent IDs.

Preserve exact values, order, get/membership/iteration, insert/delete/reinsert, ancestor traversal, no-op save, atomic save/reopen, and materializing detach.

Acceptance: zero parent payloads on ordinary lazy open; one get loads at most one row; fixed-depth ancestors scale with traversed ancestry rather than total history; one-row save is bounded from 1k to 10k; clean cache <=256.

## P4.12B — children

Then migrate world.genealogy.children. Each parent ID owns one mutable ordered list of child IDs.

Preserve list identity and direct setdefault(...).append(...) behavior used by birth, retained aliases, insertion/deletion/reinsertion, no-op save, atomic save/reopen, and plain-list materializing detach.

Birth must update the child parent tuple and both parent child-lists in one hybrid generation.

After both slices are focused/scaling green, run one affected P4 matrix, close P4.12, and remeasure residual eager history.


P4.12A focused run 37493767218: 9/9 passed in 1.11s.

P4.12A scaling run 37494131473: open 33 reads at 1k and 10k; point lookup 1 read / 35 bytes; one-parent save 3 writes / 169 bytes; resident parent rows 1.

P4.12B scaling run 37495816413: open 33 reads at 1k and 10k; point lookup 1 read / 27 bytes; one child-list mutation save 3 writes / 190 bytes; resident child buckets 1.
