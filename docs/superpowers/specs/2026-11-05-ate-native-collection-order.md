# Native collection state and order proof integration

Continue from verified green e3d5df9/run42042165724 (4,641 tests). User approval
to continue inline toward Stage0.6 speed/integrity targets remains active.

Intent: native namespace counts, next insertion ordinals, key existence and key
iteration must use accepted collection authority, rather than locally consistent
namespace/order checksums alone. A valid value source must not be paired with a
forged count, omitted key or changed RNG/iteration order.

Author choice: use existing immutable collection directory and ordered seek
proofs at native store seams. Capture component certificate pairs only after
joining them to the accepted seven-root manifest via existing `_load`; refresh
with the manifest/read pin on commit and recovery. This is accepted read context,
not a source cache or separate authority. Initial full audit stays mandatory.
Rejected approaches: omit the full opening audit now (query/identity/raw consumer
coverage incomplete), or build a parallel native registry/ordering publisher.

State lookup authenticates namespace presence/absence, exact count and next
ordinal against the accepted directory. Physical intervals/types/checksums remain
checked; current accepted state/order rows must be open. Point order joins its
actual ordinal/key to the accepted collection seek leaf. Missing point order
requires accepted version absence, using the audited World's one-record/one-order
invariant; a missing physical order for an accepted version must reject.

Iteration compares a bounded physical indexed window to the accepted seek window
before decoding keys. Include lookahead and the final empty/surplus window so
missing/extra rows cannot be hidden by count or end-of-page changes. Validate
every returned body's existing source proof, preserve original iteration order,
release snapshots before user-visible yields and reject paused iterators after
generation/epoch drift. Keyless length preflight prevents oversized window
transfer. Maximum128returned keys plus lookahead,32,760-byte typed keys,1MiB
combined window metadata; shrink internal pages when needed, never omit output.
No archived body scans. Counts/existence read no unrelated source bodies.

Reuse the existing short-lived ValidationScope only for immutable directory
certificate summaries, keyed by accepted directory commitment and namespace.
No cache across operations/writes/generations, no skipped physical state or order
validation and no source-body/path cache. Reject TEMP shadow/trigger sources.
Busy preparation is not an exemption: staging bypass is only the exact owned
publisher outside callbacks, inherited from the native source bridge.

Tests: checksum-consistent state/count/ordinal/missing/extra/future interval
forgeries; empty/absent declarations; pagination/lookahead/page-size1 and128,
long keys and metadata pretransfer; altered seek/directory bodies; generation
and paused iterator drift; save/fault/recovery/aliases, exact eager/fresh restore.
Use real native APIs and isolate accepted-root checks from epoch rejection where
necessary. One independent whole-package review; every finding including Minor
closed together. Retain raw history and exact source/pin/fingerprints; one bundled
full/proof CI publication. No default/main/mature/endurance action or speed claim.

This closes collection-state/order native fetch seams only. Query, identity,
ordinary roster and remaining direct SQL consumers still block proof-only opening.
