# Stage 0.6 — rank-neighbor native proof boundary (implementation handoff)

Baseline: `7339565824ef0b64421b6241b75cd70c783a3852`; full-suite and proof-map green in run 42349958178. The full audited opener is still mandatory.

## Concrete uncovered read

`simulation/ate_sim/persistence_lazy_minimum.py:rank_neighbor` performs direct `SELECT index_value,record_key,ordinal FROM lazy_query_versions` with `ORDER BY ... LIMIT 1`, and decodes the returned rank/key before `checked_marker`. The latter validates row checksum and selected owner metadata but **does not establish that the selected row is the first eligible row in the accepted ordered scope**. A checksum-consistent inserted row, omitted smaller row, or forged ordering may change the neighbor without failing this local check. The current proof-backed `persistence_proof_native_query.iter_memberships` validates a scope's accepted positions and physical window, but its ordering is **ordinal then typed key**, not `index_value,ordinal,record_key`. Replacing `rank_neighbor` with a query-membership scan would change asymptotic cost and is not an acceptable performance repair.

`MinimumQueries._header` and `_node` already use checked auxiliary version reads. `_persisted_ordinal` and `checked_marker` directly select a visible owner row but call `_check_record_row(...,decode=False)`; confirm that the native source preflight covers those exact call sites under the active pin, including absent-row claims. The critical new obligation is the **negative proof** that no better eligible neighbor exists.

## Required implementation

1. Add a rank-order accepted component or a certified rank-index projection whose canonical key is `(namespace, scope, numeric_rank, ordinal, typed_record_key)`. It must be published atomically with the existing query/record/auxiliary changes and be tied to the accepted generation. Do **not** reinterpret the existing query scope root as rank ordered; its positions are ordered by ordinal, not rank.
2. Implement bounded predecessor/successor and first/last seek using the accepted rank root. Verify the exact physical current-row window, including the surplus lookahead, before decoding selected values. Preserve `before`, rank/ordinal strict inequality, exclusions, and generation-bound visibility. Excluded candidates may be skipped only after their membership metadata is verified. Cap metadata and field lengths using existing proof-window limits.
3. Tie every seek/page to the original caller pin, accepted epoch, immutable root, and a read snapshot. No user codec callbacks before accepted/physical metadata comparison; no ambient publisher bypass; reject future closures, duplicate visible rows, compensating insertion/deletion, noncanonical typed keys, and cross-generation resumes.
4. Keep the current `rank_neighbor` path and full audited opener until the new root is available for existing format-7 saves, or explicitly version/gate the new representation. Never silently treat a missing new root as an empty bucket. Do not add an unbounded fallback or perform an archive-wide scan.
5. Red tests first: forged checksum-consistent earlier/later candidate; missing true minimum; same-rank ordinal tie; exclusion of first candidate; before/after strict boundary; empty/nonempty bucket; future closure; retained 1k/10k history; codec side-effect sentinel; callback/publisher; stale pin; paused iterator; existing format compatibility. Check that no unrelated owner bodies are read.
6. One independent whole-package review, all severities closed, targeted/broad local regression, exact runtime-tree pin and launcher fingerprints, eager/fresh canonical-year equivalence, then a single bundled full-suite/proof-map hosted gate. Do not assert speed improvement from shared-host microbenchmarks.

## Other admission gaps to inventory after this package

- `persistence_lazy_store.py` direct head/metadata readers and all direct `lazy_record_versions` / `lazy_query_versions` consumers not yet routed through native source/query/order/identity/roster proof.
- `persistence_lazy_identity_retired.py` `scrub` is intentionally an explicit full enumeration; keep it diagnostic, never move it into ordinary open/save.
- Every cache-hit read must retain accepted epoch/pin and physical-source authority; cached decoded values alone cannot replace a proof.
- Only after an exhaustive call-site inventory and negative controls may the full opening audit be removed.

## Acceptance

No new gameplay semantics, persistence format default, mature fixture mutation, or main merge. Stage 0.6 remains open until mature-world `open+restore <=10s`, `save <=2s`, `warm year <=1s`, and deterministic continuation are independently verified.
