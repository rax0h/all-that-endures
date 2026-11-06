# Native query membership proof reads

Continue inline from verified green2fc836a/run42148312728 (4,694tests+2subtests).
Existing authorization covers implementation in the dedicated branch, fixes,
one package review and bundled publication. No main/default/mature/endurance.

Native query_memberships/query_keys/iter_query_memberships must join query
membership selection and absence to the accepted scoped directory and ordered
seek roots before decoding selected keys. The same accepted World component
context, source proof adapter and original atomic publisher remain authorities.
Keep full audited opening: identity, ordinary-roster and raw-consumer coverage
remain separate gates. This package makes no speed or mature acceptance claim.

Author approach: resolve QueryScope through authority.read_components[1], already
bound by manifests._load. Use existing scope descriptor decoding/seek framing.
Compare every bounded indexed current physical query window with exact accepted
positions, including lookahead/final surplus. Validate all returned interval,
storage-type and checksum fields before SQLite materialization; bound CTE fields
too. Share this window machinery with native collection order rather than
creating a second copy of its security-sensitive SQL. Retained/publisher/legacy
paths remain unchanged. Reject future-start/future-closure and overlaps at the
admitted current head without scanning expired history. Actual caller pin and
the original accepted epoch guard every page/resume; release owned snapshots and
selected source-body locals before user-visible yields.

Preserve tuple API ordering by ordinal/key, ordinal multiplicity, optional limit
and exclusions. Stream API may use this canonical order (its existing contract
does not specify order). A limit selects a checked prefix after exclusions;
it does not certify unvisited suffix bytes. Verify excluded positions' metadata
when visited but fetch only selected owner source bodies. Each selected owner
must pass its existing actual-source proof and contain the exact encoded query
membership before key decode. Preserve canonical keys, duplicates at different
ordinals, save/rollback/resolve and shared identities. Limit0 still authenticates
the caller pin/context/scope, returns empty, and reads no owner bodies.

Limits:128selected positions per internal window plus lookahead,1MiB combined
window metadata (shrink long-key pages without skipping),4,096-byte query scope
fields/result keys from the existing scope constructor,1MiB locator/exclusion
metadata. No global result-count cap on tuple APIs; output size is their existing
contract. Deduplicate encoded exclusions in a bounded set; no SQL parameter or
unbounded raw-row transfer. No cross-operation source/proof-path cache. Existing
ValidationScope may cache immutable resolved root summaries only, keyed by
accepted scoped commitment and exact encoded scope, with all physical reads kept.

Alternatives rejected: use physical checksum query rows as authority (omissions
and coherent forgeries remain invisible), call the standalone seek-page reader
unchanged (it selects only accepted rows and cannot detect physical surplus), or
remove opening audit before remaining relation consumers are covered.

Tests use real admitted native sessions: coherent missing/extra/order/ordinal,
empty/absent, limit/exclusions, negative prefix and complete-suffix semantics,
forged owner/descriptor/seek nodes, future intervals/overlaps, budgets before
transfer/materialization, invalid/released/compatible pins, paused iteration and
same-generation recovery, callback rejection, scope invalidation, shared aliases
and exact generated-year eager/fresh restore. Retain1k/10k no-unrelated-body
controls with actual source locators and SQLite physical selection instrumentation.
One independent whole-package review; every finding including Minor closes here.
