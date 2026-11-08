# Rank selection proof index

Implements the existing `2026-11-07-ate-rank-neighbor-proof-boundary.md`
handoff. The user authorized continuing that work after the baseline full/proof
run 42417207328 passed at f1ecae0.

Use a seventh scope directory root, certificate version 4, for independently
rank-ordered minimum buckets. RankScope(namespace, index_name) is distinct from
QueryScope: its positions order encoded rank, ordinal, then typed key. Existing
query positions and the six existing root domains retain their meanings.
Bootstrap opts in with include_rank=True (requires sequence/child inventory).
Explicit proof-copy opts in with rank_proofs=True. Existing format-7 six-root
copies and legacy minimum reads remain supported and keep audited admission.
No missing seventh root may be interpreted as an empty ranked bucket.

The existing scope publisher stages this projection from exactly the actual old
and new query memberships, inside its existing atomic transaction. No extra
publisher, mutable identity registry, default-format change, or history scan is
introduced into native operations. A bounded accepted seek proves the first or
last eligible position; scalar-only physical preflight and an exact ordered
window comparison precede user-codec decoding. Excluded candidates still have
their query membership and selected owner metadata verified. Use existing 4096
byte scope fields and 1 MiB metadata window cap. Enforce caller pin, accepted
epoch, callback guard, and current-generation intervals at every read.

Alternative considered: scan existing ordinal-ordered query proofs. Rejected
because it changes a rank seek into a bucket scan. Reusing an existing root with
synthetic scope tags avoids a certificate version but obscures compatibility;
an explicit seventh root makes the authority boundary inspectable.

Retain full opening audits. Mature 10s open/2s save/1s warm-year acceptance is a
later gate and cannot be inferred from component timings.
