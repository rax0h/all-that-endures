# Native identity allocator and occurrence proof reads

Continue authorized inline Stage0.6 work from greenf08d2e1/run42169444866.
Bind the existing native allocator, exact placement, owner enumeration and
incarnation enumeration seams to accepted World authority. Keep original return
shapes, registry/catalog, publisher and legacy retained-pin paths. Full opening
audit remains until catalog/ordinary-roster/raw-consumer coverage is complete.
No main/default/mature/endurance action, no speed or mature acceptance claim.

Author design: read accepted allocator directly from manifest.head and check
accepted scoped component[1] agrees. Check actual current allocator interval,
types and checksum against that number. OwnerScope/GroupScope roots from the
already-manifest-bound scoped component authenticate exact placements, absence
and each complete enumerated window. Use existing scope resolution/seek/member
framing; no new authority or identity graph. Reuse immutable scoped summaries
only within existing ValidationScope; always recheck actual physical intervals.

For enumeration, accepted seek positions select bounded raw fields. Compare the
next physical indexed current locator to each accepted locator inside SQLite,
returning only a boolean plus bounded scalar interval/checksum metadata. Exact
point probes reject duplicate open locators and future closure; current rows
cannot start in the future. Validate both owner and group commitments for every
selected occurrence. Include lookahead and final surplus probe before decoding
any page. This avoids copying untrusted key/path blobs or ranking raw rows.
Owner-leading and incarnation-leading indexes bound work to selected scopes;
expired history is never scanned. No owner/archive payload bodies are fetched.

Actual caller pin, original accepted epoch and exact publisher/callback rules
remain mandatory. Release owned snapshots before public iterator yields; retain
only bounded decoded output/locators, no payloads. Owner enumeration keeps encoded
path order; group compatibility API keeps its existing decoded namespace/key/path
sort. A positive unallocated group ID remains an empty query if no physical rows
exist, authenticated by the accepted allocator; contradictory rows must reject.

Limits:128returned positions plus lookahead,1MiB encoded page/locator metadata,
existing4,096-byte namespace/key/path fields. Shrink long-field pages without
skips. Keep tuple APIs' existing output-size contract. Reject malformed/NUL text,
invalid/cross-generation/released pins, future/overlapping intervals, descriptor
and node corruption, coherent changed/missing/extra rows before output/decoding.

Alternatives rejected: trust checksums alone; use standalone root-selected pages
unchanged (unselected physical surplus is invisible); build a new identity
registry or remove full admission before remaining consumers are covered.

Test allocator/point/owner/group forgeries and positive aliases, empty/future
groups, long pages, budgets before transfer, pause/epoch/fault/recovery, callback
and scope invalidation, native catalog compatibility,1k/10k no-body controls and
exact canonical eager/fresh continuation. One independent whole-package review;
all findings including Minor close in one register, one bundled full/proof CI.

Implementation ruling: existing admitted format7 files have no standalone ate_occurrence_group_current/closed indexes. Use existing owner/incarnation interval indexes for future-closure probes. Group enumeration compares a single current-group COUNT (incarnation+valid_to NULL indexed prefix) to the accepted root count, then checks every selected exact locator against both roots. This is one linear pass over the selected current group, not expired history or the archive, with constant scalar count memory. It avoids an implicit index build or rejecting existing format7 files. Count stays within one original-epoch iterator, never across operations; complete exact selections+count prove no surplus, while missing+extra compensation fails at the missing accepted point. Owner windows keep indexed next/last surplus probes. Group page metadata remains bounded, but first-page CPU includes that one selected-group count.
