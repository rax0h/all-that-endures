# Persistence review cleanup

User instruction: close review findings within their containing work group, including Minors, and promptly clear the older backlog. AGENTS.md now preserves this requirement. The consolidated closure register is review-cleanup/register.md; historical notes link to it without rewriting original reviews or raw logs.

Ten actionable groups were reconciled: module header, closed-session error contract, fixed-shape boundary coverage, per-backing page-cap contract, batch rollback edge tests, raw-target corruption tests, owner-target dedup/shared-budget/late-kind tests, nested/key/branch negative tests, simultaneous frozen parent+child certification/recovery, and duplicate Event-ID body reads. Raw-log whitespace is a completed evidence-preservation decision. The earlier ordered-seek parser boundary Minor had already been closed with permanent vectors.

Closed save/recovery now raise StoreError before any access to the closed connection. Incoming validation reuses a previously authenticated immutable Event-ID raw body within the same checked source operation, preserving its original source/byte charge and explicit owner schema, revision and checksum checks. Calls do not share this cache. New tests preserve aliases and old snapshots, use real post-insertion rollback failures, verify checksum-valid physical substitutions fail against accepted roots, and exercise remaining classifier/cap boundaries.

The128 removed-page cap remains intentionally per backing. Global512row and byte limits still apply; tests scale the per-backing threshold to verify independent-parent composition and over-cap checked fallback. This closes the documentation/contract finding without inventing a new global128page restriction.

Missing permanent tests generally exercised correct existing behavior and passed once fixture setup was correct; those are coverage additions, not claimed runtime fixes. The closed-operation and duplicate-read defects both reproduced RED before implementation and passed GREEN. The reference replacement test keeps the old target alive through another alias; partial-retirement support remains a separate fenced structural feature.

Exact final local XML, source hashes, scaling receipts and independent review disposition are retained in review-cleanup/. Hosted full/proof/all28matrix acceptance remains pending. No main merge/default activation/endurance, or completion of broader structural/open/mature/GC work, is claimed.

Final local verification:410 tests pass(290 owning modules,120native), with no failures/errors/skips; both affected1k/10k/100k matrices pass on runtime63d5ac487d0157a5ef521b4def8ee9ce94532e0c. Independent selected-case and review results are retained separately.
