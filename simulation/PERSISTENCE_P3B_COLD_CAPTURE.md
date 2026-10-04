# P3B next bounded assignment: capture a cold-format World

Review update: implementation at `77c6ccd` was reviewed; two narrow typed checks
were corrected, but this slice is not yet fully accepted. See
`PERSISTENCE_P3B_COLD_CAPTURE_REVIEW.md`. The next authorized assignment is
`PERSISTENCE_P3B_COLD_CAPTURE_FOLLOWUP.md`, completing this contract's evidence.

Status: architecture/implementation specification following the cold identity
restore review. Read `PERSISTENCE_P3B_IDENTITY_RESTORE_REVIEW.md` and the parent
`PERSISTENCE_P3B.md`. Verify the current PR #14 head before editing.

## Goal and scope

Restore a complete, unbound World from the specified cold record format while
borrowing an already-open store and capturing exactly one read transaction.
Keep the immutable disk prefix lazy. This is the internal loader that the later
owned World/session API will use; it is not that public API yet.

Allowed product files: new `ate_sim/persistence_session.py` for the internal
capture helper/result; `persistence_adapters.py` for narrowly factored format and
record restoration helpers; and `incremental_store.py` only for the checked head
accessor below. Add `tests/test_persistence_cold_capture.py` and
`PERSISTENCE_P3B_COLD_CAPTURE_VALIDATION.md`. Reuse accepted EventLog, P3A reader,
codecs and cold identity restoration without redesigning them.

Do not implement snapshot creation/conversion, public `open_world_session`,
tracking/binding, save/acknowledgement recovery, ownership/close/detach APIs,
checkpoint/export changes, engine guards or normal checkpoint replacement.
Do not instantiate `IncrementalWorldSession` or route through its full-history
baseline comparison. No simulation, gameplay or sealing-rule change.

## 1. Internal API and lifetime

Add `_capture_cold_world(store)` requiring an active caller-owned
`TransactionalStore.read_transaction()`, just like the accepted P3A factory.
The caller must have opened the store with WorldCodec and the expected simulation
schema/rules identity. The helper does not open a filename or start/end a
transaction, and rejects use outside an active read transaction before work.

Return an internal `ColdWorldCapture` result containing the reconstructed World,
borrowed-store prefix reader, captured generation, checked head metadata,
effective manifest/layout, current identity links and validated tail/commit
descriptors. This result is not serializable persistence state or a new session.
Do not retain raw decoded suffix rows or expanded pending Events in it.

Capture every component, including identity relinking/verification, before
leaving the caller's snapshot. Use
`SealedEventPrefix.from_active_read_transaction(store)`; never nest the standalone
reader constructor's transaction. Prefix and result generations must agree.

On failure, close any reader created by this helper, drop the partial World,
leave the borrowed store open and leave the caller's transaction active. On
success the caller owns the returned reader's lifetime. After the caller exits
the read transaction, the fixed-prefix reader remains valid while its store is
open. Closing the reader/store gives the already accepted EventLog failure
behavior; this slice does not promise fail-before-step-mutation for a World
whose store was closed. That guard belongs to the public session integration.

## 2. Checked bounded head access

`head_metadata()`/`generation` alone do not recheck the complete head checksum
inside an already-open connection. Add one narrow read-only P1 accessor returning
generation, parent generation, decoded head metadata and committed namespace
counts from the SAME checked head row. Reuse P1's checksum, typed decoding and
namespace-count validation. Require an open store; do not commit or silently
start a transaction. No record/segment payload enumeration, integrity_check,
table-wide segment count or full scrub belongs in this accessor.

The cold capture compares its descriptors and loaded record counts to these
committed counts. An absent count for a declared empty namespace means zero,
as in P1. Validate the published inventory/count structure using accepted P1
rules. Preserve all existing accessors and checked storage semantics; no format
version or durability-setting change. Raw SQL for these checks stays inside P1.

## 3. Exact cold-format acceptance

Use section 3 of the parent architecture without inventing a parallel format:

* Manifest: existing schema/collections plus
  `identity_storage="current-links/v1"` and
  `event_storage="sealed-prefix-tail/v1"`. Accept only this cold mode here.
  Reject legacy event modes with a conversion-required error, unknown modes,
  identity-delta authority, mixed manifests and unknown canonical roots.
* The effective collections/v1 overlay follows accepted P2C semantics. The
  world.events description is `("EventLog-disk/v1", N, F//2048)`; other collection
  descriptions and stable insertion ordinals retain their accepted meaning.
* Namespace inventory is exactly the canonical collection namespaces, World
  metadata, current identity links and the two accepted P3A namespaces. Declare
  the identity and P3A namespaces even when empty. No legacy delta namespace.
* world_event_storage contains exactly the P3A descriptor plus
  `session-tail/v1 = (1,D,F,N,last_event_year)` and
  `session-commit/v1 = (1,captured_generation,commit_token)`, all schema 1.
  Require exact integer types (not bool) for counts/generation and
  `0 <= D <= F <= N`, with D and F multiples of 2,048.
* To make the previously opaque commit token representation concrete, use a
  32-character lowercase hexadecimal string. A later writer generates it from
  outside simulation RNG (for example UUID4 hex). This is acknowledgement
  identity, not a simulation value. Validate shape here; do not generate one.
* Prefix descriptor count is D, its segment count is D/2048, and that segment
  count matches the checked head's committed count for world_sealed_events.
  Its record count is zero. world.events has N-D records and no segments;
  other canonical namespaces contain records only. Check all loaded record
  totals against the checked head, including metadata/current identity rows.

Normal lazy capture deliberately does not prove the physical integrity of every
cold segment row. Missing/corrupt payloads may fail later on access or explicit
P3A verification. Do not secretly enumerate cold segment headers/payloads to
upgrade that promise. The checked committed head/descriptor must agree now.

Keep legacy APIs explicit: existing `read_snapshot`, `write_snapshot`,
`bind_snapshot` and conversion retain their accepted modes and continue to reject
cold input. Factor shared manifest/link validation with an explicit mode parameter
or helper; do not strip unknown keys just to make the old parser accept cold data.

## 4. Restore records and current identity

Reuse the closed World/root schema and accepted non-event collection restoration.
Allocate the same root types without running world generation or consuming RNG.
Validate every loaded record through checked storage/schema APIs.

Read only world.events suffix rows. Their typed integer keys and envelope ordinals
must be exactly the absolute positions `[D,N)` with no gaps, duplicates or extras,
including no row below D. Do not rely on encoded-key/SQLite lexical order: order
these resident suffix rows numerically. Require exact Event type, integer IDs
`index+1`, integer nondecreasing years and valid sealed-flag representation.
Compare the first suffix year with the descriptor's last year. Require
`next_event == N+1` and the final year to match session-tail; last year is None
iff N is zero. When suffix is empty, use the descriptor's last year.

For `[D,F)`, require sealed Events and their accepted recursively frozen value
semantics; reuse P3A's sealed-event validation. For `[F,N)`, preserve each Event's
sealed flag exactly, including individually sealed tail Events, and validate
frozen semantics when sealed. Never call seal() to repair persisted values.

Construct the accepted composite EventLog from the prefix and resident suffix,
packing exactly F-D already-sealed Events as pending chunks. Release expanded
pending Events after construction. Do not recreate resident bytes/index entries
for `[0,D)` or attach identity owners to any sealed LOG occurrence.

Restore P2C current links using the accepted cold-mode preflight/relink helpers,
then verify the projected current identity graph. Bad links into excluded
history must fail before disk access. Preserve non-log sharing and mutable-tail
sharing, including parent/descendant aliases and exact typed copies. Validate
World seed/year/all next-ID counters against the checked head. Do not call
legacy `_audit` on the cold World, digest, archive export, verify_all or bind.

## 5. Required evidence

Build small cold-format fixtures in TESTS using accepted P1/P2/P3A APIs. A fixture
may first export an independent in-memory World through accepted P2C, then
explicitly assemble cold records in a test-only transaction. The test assembler
must not call the loader under test to derive expected state or be exposed as a
production converter. Persist post-seal current links explicitly; do not retain
old sealed-log identity paths. Use synthetic chunk-crossing history, not a long
simulation.

Prove:

1. A complete World is reconstructed with exact non-event values, insertion
   order, seed/year/counters and event values/IDs/years/causes/frozen flags.
   Test empty, prefix-only, tail-only, pending backlog and mixed partitions,
   including more than four pending chunks and equal-year boundaries.
2. Current aliases survive through independent persisted payload copies,
   including tail data and nested parent/descendant relationships. A malformed
   link into disk/pending/individually sealed tail fails with zero cold reads.
3. Missing/extra/below-D suffix rows, wrong ordinals/IDs, bool counts/keys,
   chronology/frozen-value errors, unknown/mixed modes, missing empty descriptor,
   namespace/count disagreement and mismatched World/head/commit generation
   fail cleanly. Corrupt a head after opening the connection: capture must
   detect it through the new checked accessor, without a full scrub.
4. One caller transaction captures a consistent generation across World,
   descriptors, identity links and reader; no nested transaction or hidden commit.
   After failure the store and outer transaction remain caller-owned/usable.
   After success and transaction exit the reader still serves its captured prefix.
5. At real 4/40/400-segment stores with identical current state/suffix, capture
   performs ZERO segment payload reads, zero pending-chunk decodes and no old
   history iteration. Record reads/bytes, retained tail/pending/index state and
   projected identity counts remain independent of prefix length (allow only
   descriptor integer/text digit growth). Count SQL segment enumeration as a
   failure even if it avoids decoding; this is not just a cache-size assertion.
   Do not retain source fixture events during retention measurement.
6. First cold point access afterward reads one segment; repeat access uses the
   accepted bounded cache. Corrupt an unread cold segment and demonstrate lazy
   capture's stated limit: capture succeeds, checked access/full verification
   fails. Keep suffix/current-record corruption eager.
7. Legacy/current P2 and all accepted P3A/P3B tests remain green. No detached API
   returns a World whose borrowed store it already closed.

Memory/work is proportional to current World/current links plus resident suffix,
with O(1) prefix metadata and the accepted initially empty cold cache. Suffix
bootstrap may use temporary O(N-D) rows; no bound on all World records or an
arbitrarily unsaved backlog is claimed. Independent resumed simulation, public
close guards and all save/recovery cases remain later integration gates.

## Delivery

Implement this slice only. Run focused and affected tests, then one full
`simulation/tests` suite on stable final code. Record commands, exact SHA,
actual bounds and remaining limitations. If testing on an isolated CI branch,
prove product/test blob equality on landing. Commit to PR #14's existing branch
with `[skip ci]`; do not change workflows. Stop for architect review.

No millennium/endurance, balance/magic-progression changes, Stage 1, unrelated
work, normal checkpoint replacement or merge. GitHub authorization is standing.
