# P4.1 versioned storage foundation implementation plan

> For Sol: use the executing-plans workflow task by task. No additional agents
> are required. Implement the complete tranche and return one review package.

**Goal:** provide checked generation-consistent record/query/order storage with
bounded retention, atomic publication and explicit crash-safe recovery.
**Architecture:** extend the accepted SQLite transaction machinery in a separate
opt-in format; one head publishes legacy-style changes, immutable segments and
new versioned changes together. No World integration.
**Stack:** existing Python/SQLite/codecs; no new dependency.
**Spec:** PERSISTENCE_P4.md as corrected by PERSISTENCE_P4_REVIEW.md.
**Baseline:** PR #14 at `4a6e23feb52894b1298a5cc09914e77156446f12`, followed by
this documentation commit. Verify live head before editing.

## Global constraints

P1/P2/P3A/P3B remain accepted. Legacy format version 2 and default APIs keep
their behavior. Use a separate explicit P4 storage format version **3**;
unknown/mismatched modes fail before payload traversal. Do not change the
normal checkpoint default, World behavior, P3B session state machine or EventLog.
No millennium/endurance, balance/magic, Stage 1, unrelated work or merge.
Every commit uses `[skip ci]`. Do not launch the ordinary PR workflow.

## Review focus

- An opener racing reclamation must register a valid pin before any versions
  it needs can be reclaimed.
- A writer's own pin must advance atomically; ordinary repeated saves must
  neither block themselves nor accumulate revisions.
- Lost acknowledgement must be recoverable even if another writer advances
  once more; version reclamation and receipt retention must honor that need.
- Delete/reinsert, empty query results and unchanged old rows must survive
  visibility filtering and cleanup.
- Pin registration/release/copy failure must not create a mixed generation,
  require manual SQL repair or silently discard another session's history.

## 1. Files and interfaces

Create `simulation/ate_sim/persistence_lazy_store.py` for the P4 facade,
typed version changes, checked reads, pin/recovery operations and diagnostics.
A small `persistence_lazy_schema.py` is appropriate if DDL/checksum logic
obscures that module. Modify `incremental_store.py` only to reuse its checked
transaction/format plumbing; factor narrowly instead of cloning a second
independent commit protocol. Keep legacy public defaults and exceptions.

Create:
- `simulation/tests/test_persistence_lazy_store.py`
- `simulation/tests/test_persistence_lazy_store_failures.py`
- `simulation/PERSISTENCE_P4_1_VALIDATION.md`
- `simulation/persistence_p4_1_validation.json`

Public P4 facade names (typed result classes may be dataclasses):
- `LazyRecordStore.create(path, *, codec, simulation_schema, rules_id)`
- `LazyRecordStore.open(path, *, codec, expected_simulation_schema, expected_rules_id)`
- `capture_pin() -> GenerationPin`: random token + store identity + captured checked head.
- `release_pin(pin)`: idempotent for this token/store, no payload traversal.
- `read_version(pin, namespace, key, *, expected_record_schema)`
- `iter_keys(pin, namespace, *, page_size=128)`
- `query_keys(pin, namespace, index_name, value)`
- `commit(pin, *, commit_token, version_changes, changes, new_segments, metadata)`
- `resolve_commit(pin, commit_token)`
- `verify_all()`, `backup(destination)`, `close()`
- `copy_current_head(source, destination, *, codec, expected_simulation_schema, expected_rules_id)`

Use GenerationPin as an immutable token/store-id/captured-head value. CheckedVersion
returns value, record schema and validity interval; a legitimately absent key
raises KeyError, while membership without its required payload raises
StoreIntegrityError. Query/key methods yield typed keys in documented order.
Return commit/resolve results with an explicit committed/not-committed/conflict
outcome and updated captured pin/head; never infer acknowledgement from an
exception class alone. Preparation freezes caller-owned changes. The
`changes/new_segments/metadata` inputs reuse accepted P1 types/contracts.
No-op returns the existing generation and performs no payload/receipt write.

VersionChange describes namespace, typed key, value/delete, record schema,
and complete final memberships using existing typed Membership semantics.
Storage derives ordinal changes from row existence and explicit remove/reinsert
intent. A single final value cannot express delete-then-reinsert at the same
key; include an explicit validated reinsertion flag. This primitive changes
collection order only; future object-incarnation semantics remain P4.2.

## 2. Authority, schema and checked visibility

Use the record/order/query interval representation in the proposal:
`from <= G < to`, with NULL upper bound meaning still current.
Only declared lazy namespaces use these rows; never persist a second
authoritative payload in ordinary records for the same logical owner.
Versioned identity-link namespaces must be supported as typed records for later
integration; do not implement sharing groups now.

Persist counts and next ordinal per namespace with generation visibility.
Assignment preserves ordinal; deletion closes membership; reinsertion takes
a fresh ordinal. Empty namespaces and legitimate absent keys are distinguishable
from a member whose required payload is missing. Iteration uses keyset paging,
not repeated OFFSET rescans; page size is positive and capped at 128.

Checksums frame row kind, namespace, typed key/index value, schema/codec version,
ordinal where applicable, validity interval and payload. Closing an interval
updates its checksum in the same transaction. Reject overlapping visible
versions, invalid intervals/types, duplicate ordinals, wrong namespace/schema,
membership pointing to an absent owner, and inconsistent per-namespace counts.

Add indexed lookups for typed record keys, query key/value, collection order,
expiry generation and pins by generation. State/measure any sorting of returned
eligible keys; do not scan or sort the whole unrelated archive for current queries.

Ordinary reads check every row/metadata they use; they are not a full scrub.
Full scrub recomputes counts, collection/query completeness from record metadata,
checksums, overlaps and all retained snapshot invariants. A deleted membership
must fail that scrub even when every remaining row has a valid checksum.
For generic storage, the submitted membership set must be retained in checked
owner-version metadata so completeness can be verified without a World adapter.

## 3. Exact pin/retention/publication contract

### Capture

Capture/check head and insert the pin in the same short write transaction.
A captured pin may name only the current head at registration; no arbitrary
repinning of an already reclaimed generation. Failure rolls back registration.
Store identity/token/generation are checked on use. Pin release and reclamation
serialize with capture and commits.

### Commit and acknowledgement

Validate expected generation and writer token under the same write lock as
publication. A non-no-op commit advances exactly once. The transaction publishes
version intervals, memberships/order/counts, ordinary P1 changes, immutable
segments, metadata/counters, receipt, head **and the writer's pin from G to G+1**. Checked head namespace
counts combine current visible versioned owners, non-lazy records and segments
without double-counting; format-3 verification must understand that inventory.
Publication may not require a second transaction to make the writer safe.

Keep a checked per-pin most-recent commit token/outcome, bounded to one receipt
per pin, sufficient to resolve an interrupted acknowledgement. An unresolved
writer at G+1 pins G+1, so a competitor can advance to G+2 but cannot advance to
G+3 until the required prior generation is released. Its receipt must not be
evicted by an unrelated global receipt cap. On resolution, return committed G+1
with a stale indication if head is now G+2; never retry the already committed
write. A token mismatch/conflicting result fails explicitly.

A failed pre-commit operation leaves pin/head at G. A post-commit exception keeps
the facade recovery-required: block subsequent writes or pin release until
explicit resolve, or close conservatively leaving its durable pin for explicit
recovery. Do not discard the information needed to distinguish those outcomes.

### Two visible snapshots

When head is G, a commit to G+1 is allowed only if, after advancing the writer's
own pin, no other pin requires a generation less than G. A pin at G may remain
and becomes the one prior visible generation. Otherwise raise a distinct
GenerationPressureError with head/minimum pinned generation; no changes publish.
This check includes all durable tokens, not just in-process sessions.

Head retention floor is the oldest required pin, or head when no older pin is
needed. A version whose end is <= floor is obsolete; unchanged open intervals
remain regardless of old creation generation. Reclaim via the expiry index in
the same transaction as a successful commit or explicit maintenance. A no-op
save is not an implicit maintenance scan. Report retained obsolete work if
cleanup is batched; no unbounded accumulating backlog is acceptable.

Pin bookkeeping costs O(number of registered sessions), not world history.
Use one row per live/abandoned session and a fixed maximum of **64 registered
pins per store**. Capture beyond capacity fails without mutation; explicit
close/release or source-preserving copy frees capacity. Do not retain an
ever-growing pin/receipt audit trail. This conservative cap is opt-in P4 policy.

### Stale and orphan behavior

A save with a non-current expected generation is a conflict, never a merge.
Historical checked reads remain available while its pin exists.
World-level detected-stale mutation restrictions remain unchanged for P4.2.

No timeout/PID guess clears an orphan. Implement `copy_current_head`:
capture a consistent source view; check current required data; build a private
new format-3 store containing the same current logical values/order/query state,
immutable segments, counters and head generation; assign a new store identity;
start with zero pins/operational receipts and retention floor equal to that head.
Fully verify before atomic no-overwrite publication. Source remains unchanged.
Do not copy old-only versions or bypass current corruption. Failures leave no
partial final destination. The API returns the new path/identity and explains
that callers must explicitly choose it; never swap a file underneath old handles.

This explicit O(total current data) operation may use a consistent backup/staged
copy and a long read window, unlike ordinary reads. Record that cost separately.
It also solves copied orphan pins after exact backup. Exact backup itself
preserves all operational metadata and never claims to compact.

## 4. Bounded read and write accounting

Keep rollback journaling and synchronous FULL. A checked version/query read
uses one operation-scoped SQLite snapshot, validates the pin/head/floor and reads
at captured G within that transaction. Do not yield a raw live cursor whose
lifetime can hold an unbounded caller-controlled transaction. Key iteration
buffers <=128 keys, ends the transaction and resumes under the durable pin.
No write transaction waits on arbitrary user code during decoding/publication.

Count payload reads/writes/bytes plus metadata/query/pin/maintenance rows.
For fixed requested/edited owners, work must be independent of unrelated H
apart from indexed O(log H) navigation. An unshared point read decodes one
payload. Zero-row queries must not secretly scan historical rows. Test both
current and previous snapshots with large irrelevant closed/newer memberships.

Two retained generations is a logical bound, not a promise that SQLite's
physical file shrinks after deletion. Report live versions/bytes and reusable
file space separately. New revision work may depend on actual changed owners K,
their membership count and required expired rows; never conceal O(H) work in
“metadata” or “cleanup.”

## 5. Task sequence and tests

For each task: write meaningful failing tests, implement narrowly, run the
focused tests and commit with [skip ci]. These are internal steps of one
assignment, not requests for permission.

### Task A — format/rows/checked access
- [ ] Build isolated format-3 create/open and legacy rejection tests.
- [ ] Implement checked version/order/query rows and full-scrub invariants.
- [ ] Test wrong keys/schema/intervals, missing payload/membership/order,
      overlapping versions, empty collections and delete/reinsert order.
- [ ] Test current vs older point/query results and 128-key iteration boundaries.

### Task B — atomic pins and combined publication
- [ ] Implement capture/release and complete commit/resolve state transitions.
- [ ] Prove 100 successive single-writer saves never self-block and retain
      bounded versions/one receipt; unchanged ancient rows survive cleanup.
- [ ] Prove loser G pin permits winner G+1, blocks G+2, and release permits it.
- [ ] Race pin capture with commit/cleanup using independent connections/processes.
- [ ] Inject failures before transaction, during each row family, before commit
      and after commit. Include ordinary P1 records plus immutable segments in
      the same transaction to prove a single old-or-new head.
- [ ] Kill writers before/during/after commit and resolve after reopen; test
      competitor advancement before lost-ack resolution and repeat resolution of the latest token. After a subsequent acknowledged
      commit, older tokens are outside the one-receipt contract and reject;
      never claim unbounded idempotency history.
- [ ] Test duplicate/foreign/stale token, registration capacity and release faults.

### Task C — recovery copy, scrub, backup and relocation
- [ ] Implement current-head copy and exact backup with distinct contracts.
- [ ] Prove abandoned pins cannot corrupt data; copy clears pins only in a new
      file, restores write availability and leaves original bytes/state usable.
- [ ] Cover existing destination, injected publication failure, corrupt current
      rows, old-only revisions, relocation and complete metadata/value equality.
- [ ] Run all new storage tests plus existing P1 storage/codec failure tests.

### Task D — scaling and final evidence
- [ ] Fixed active/requested/edited sets with 1k and 10k irrelevant records;
      exercise current and previous queries, repeated generations and cleanup.
- [ ] Record reads/writes/bytes, metadata/maintenance work, versions, pins,
      receipts, query plans/work and peak/retained allocation. No World-memory
      claim belongs to this foundation.
- [ ] Run affected tests then one full simulation/tests suite on stable bytes.
      Reuse matching completed evidence; avoid redundant broad reruns.
- [ ] Commit actual evidence, tested/candidate SHAs and limitations.

Start a long unit-only gate once if necessary, return its ID and let the owner
re-prompt. Do not wait/poll repeatedly or run the regular millennium workflow.

## 6. Batch the next design decision with this implementation

Include a concise proposed P4.2 addendum in PERSISTENCE_P4_1_VALIDATION.md:
- stable object incarnation vs owner key/group projection;
- replace/delete/reinsert with a retained old alias;
- nested alias surviving owner eviction, then mutation and reload;
- versioned authoritative current links and derived group merge/split;
- removal of strong binding/memo retention and dead weak-entry cleanup;
- no hidden whole-archive load through mapping/codec/query compatibility.

Support it with small isolated experiments where useful, not production World
changes. This lets the P4.1 implementation review settle the next architectural
choice in the same visit. No large prototype framework is requested.

**Stop after P4.1 and that addendum.** Do not implement P4.2, resource/material
migration, compact event_ids or public lazy World sessions yet. Report one exact
head, completed validation, measured bounds and the remaining design decision.
