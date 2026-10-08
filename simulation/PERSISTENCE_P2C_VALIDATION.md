# P2C review — accepted within scope

Implementation: `420be224cae4820181cfc3469ccb98bd657b61ef`.
P2C is accepted. Stage 0.5 remains decision B pending integrated storage and
long-history validation; this is not a merge or release approval.

## Evidence verified

* [Focused CI 36369701501](https://github.com/rax0h/all-that-endures/actions/runs/36369701501):
  **143 passed in 82.88s**.
* [Full CI 36369828218](https://github.com/rax0h/all-that-endures/actions/runs/36369828218):
  **327 passed in 237.72s**.
* All five landed code/test files match the full-suite candidate
  `43745ea28df2ac3c8a989d50a47b93368be42f74` byte-for-byte.
* Review reran `simulation/tests/test_persistence_p2c.py` locally:
  **21 passed in 2.64s**. The full suite was not rerun unnecessarily.

## Accepted behavior

New opt-in snapshots have one explicit current identity authority. Typed target
paths address current owner paths in `world_identity_links`; changes replace or
delete rows atomically with World edits. They do not append/replay identity deltas.
Pending changes reduce to final target state in owner-refresh order, including
transient aliases from list shifts. No global alias rewrite is required.

The locally rerun cases prove 20 and 200 alternating alias edits retain only
zero or one live identity row, never the lifetime edit count. Tests at 100, 300
and 1,000 unrelated groups limit a local alias addition to one changed identity
row and two total payload writes. Removal deletes its current row; no-op saves
write nothing. Earlier structural-layout bounds remain covered by verified CI.

Legacy base links, double-digit delta sequences and live-layout overlays remain
readable. Explicit conversion retains the source, refuses destination overwrite,
and preserves identity/digest/continuation. Existing legacy writers retain their
documented replay cost until conversion. Corrupt/mixed authorities fail closed.
Commit failure, lost acknowledgement, subprocess death, stale writers and portable
backup cases passed. No simulation rules or ordinary checkpoint APIs changed.

## Next boundary

Stop after P2C review. Astra must define P3's session lifetime, save publication,
immutable-event storage and failure boundaries before its implementation.
Full World restore/bind still has full-state cost; lazy loading, eviction and
bounded resident memory are not provided by P2C. P4/P5 and measured integrated
long-horizon evidence remain necessary before Stage 0.5 freeze.

No P3 implementation, millennium, balance change, Stage 1 or merge in this review.
