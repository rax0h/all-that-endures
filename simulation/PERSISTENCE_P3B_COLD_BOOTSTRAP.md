# P3B — cold snapshot creation and explicit conversion

Status: next bounded Sol implementation specification, 2026-10-04 UTC.
Accepted implementation baseline: `c5d827fe248f88b4825d9b51fe2ed9d65495be85`.
Verify the live PR #14 head before editing; this specification's commit follows
that baseline. Read `PERSISTENCE_P3B.md` and the cold capture review first.

**Goal:** produce fully validated cold-format snapshots from an unbound in-memory
World or supported P2 record snapshot, without changing the source. The accepted
capture helper must restore them exactly and continue short simulation while its
borrowed store remains open.

**Architecture:** reuse the accepted P2C full snapshot exporter to build a private
staging database, then move its already-sealed event chunks to P3A segments in
batches of at most four. Publish only the completed cold database. This chooses
reuse over a second record exporter; a direct cold exporter could reduce initial
writes but is not required or authorized here. Full bootstrap cost is explicit.

## 1. Scope and files

Implement in `ate_sim/persistence_session.py`; a small private bootstrap helper
module is allowed if it keeps the capture module readable. Narrow factoring of
`persistence_adapters.py`/`persistence_identity.py` is allowed for projected
current links or publication reuse. Do not copy dirty tracking, codecs, P1 or P3A.
Add `tests/test_persistence_cold_bootstrap.py` (failure tests may be separate) and
`PERSISTENCE_P3B_COLD_BOOTSTRAP_VALIDATION.md`.

No public `open_world_session`, binding, incremental session save, acknowledgement
recovery, close/detach API, engine guard, history export or checkpoint changes.
No simulation/sealing/RNG/rules change; no default checkpoint replacement.
No millennium/endurance, balance/magic changes, Stage 1, unrelated work,
workflow landing or PR merge. Commit with `[skip ci]` and stop for review.

## 2. Public API and compatibility

Expose from `ate_sim.persistence_session`:

* `write_cold_snapshot(world, destination, *, rules_id) -> dict`
* `convert_event_storage(source, destination, *, rules_id) -> dict`

The first accepts a complete, unbound in-memory World at a completed simulation
step. Refuse a bound World, tracked containers/records from another session,
active-step state, disk-backed EventLog input, unsupported types/hidden state,
cycles or invalid counters/events. Reuse accepted schema/audit safeguards. Never
silently detach, unwrap bound input, repair bad IDs/indices, or seal more events.
Retained caller objects, aliases, values, frozen flags, event containers and
EventLog query caches must remain unchanged on both success and failure.

The second accepts current P2C and genuine legacy P2A/P2B record snapshots,
including identity-delta replay and effective `collections/v1` overlays. Use the
accepted checked, pinned full `read_snapshot` path; do not reconstruct legacy
identity from equal values or discard malformed links. Reject cold sources with
an explicit already-cold/backup instruction. Read source only and validate rules
identity. No in-place conversion, source deletion, format guessing or overwrite.
The existing `convert_legacy_snapshot`, normal snapshot APIs and checkpoints keep
their present meanings. Cold-source backup remains P1 backup, not conversion.

Preflight destination existence (including a dangling symlink), source/destination
path identity and existing-file same-inode aliases. Atomic no-overwrite publication
is still mandatory because the destination can appear after preflight. Do not
create destination parent directories until basic input/path checks succeed.

### List-backed legacy input

An unaliased canonical event list is normalized in a temporary export view to
EventLog with F=0. Preserve every Event instance/value/flag; do not infer whole
sealed chunks from individually sealed entries. Do not replace the caller's list.

Compatibility limit: a legacy World whose canonical event LIST is itself shared
as a container elsewhere remains legacy-only in this slice. Normalizing one
occurrence to EventLog cannot preserve that list's container identity with the
accepted cold codec/relink contract. Detect and reject this case explicitly
before publication, leaving source intact; never silently duplicate the list.
Sharing of Events or their mutable children across ordinary current owners is
supported. Do not invent nested EventLog serialization or a new reference format
to extend the accepted codec. Existing unsupported nested EventLog values still
fail closed. Document this precise limit in API docstrings and validation.

## 3. Exact final representation and authority

Let C=2,048. For an in-memory EventLog, F is its existing whole sealed-chunk count
times C, N its exact logical count. For a normalized event list, F=0. Validate
`next_event == N+1`, exact integer IDs/years, chronological order, source indices
and sealed/frozen semantics using accepted checks. Do not trust Python numeric
equality for typed counts or IDs.

After complete bootstrap, D=F: every existing whole sealed chunk is on disk and
there are no pending chunks. `[0,F)` exists ONLY as immutable P3A segments;
`[F,N)` exists ONLY as individual `world.events` rows at absolute integer keys
and envelope ordinals. Individually sealed tail Events stay in the tail with
their exact flags/values. Never drop, duplicate, renumber, thaw or reseal Events.

The final manifest and inventory are exactly those accepted by cold capture:
`identity_storage="current-links/v1"`, `event_storage="sealed-prefix-tail/v1"`,
`world.events=("EventLog-disk/v1",N,F//C)`, and the canonical namespaces plus
current links and both P3A namespaces, even when empty. No legacy identity deltas.
Publish an explicit empty P3A descriptor when F=0 (empty append is a no-op).
Exactly three event-storage records: P3A prefix descriptor, session-tail
`(1,F,F,N,last_event_year)`, session-commit `(1,final_generation,commit_token)`.
Token is fresh 32-character lowercase hexadecimal, generated outside simulation
RNG. Seed/year/next IDs, descriptors, layout and checked head must all agree.

Non-event values, collection types and insertion order retain P2 semantics.
Fresh bootstrap may assign fresh accepted ordinals while preserving order; do
not mistake historical storage ordinals for simulation values.

## 4. Current identity projection

The staging P2C snapshot may contain log identity paths that cold storage excludes.
Do not merely delete rows with historical endpoints: surviving groups may need
new anchors. Recompute the cold current-link projection from the validated source
graph, using accepted mutable-tail traversal and occurrence/group helpers.

The projection includes all supported current non-log owners, even references to
an individually sealed Event retained elsewhere. Exclude LOG descendants in
`[0,F)` and individually sealed tail occurrences. Frozen value containers are
values, as in accepted cold identity restoration. Preserve shared parent/child
objects and cross-record/current-tail sharing; no identity index owns historical
log Events after bootstrap. A temporary list normalization must preserve aliases
among surviving Events/children and must not mutate source state.

Use deterministic, type-aware paths and the accepted cold restoration/verifier
to check the resulting graph. Linear spanning links for each projected identity
group are sufficient; do not generate pairwise links. Replace the private staging
link namespace with the complete projected authority, deleting obsolete rows.
No persistent identity-delta trail or old sealed-log anchor may survive.

The existing full `_audit` is permitted during this explicit in-memory bootstrap
and may temporarily retain O(history) decoded values. Release its temporary
historical ownership before segment transfer. Do not claim its full-state cost
is a bounded normal-open/save operation. Do not call legacy full `_audit` on the
restored disk-backed World; use accepted cold verification there.

## 5. Private construction and publication

1. Preflight/audit the source without mutation; prepare the normalized view if
   necessary. Generate a fresh private directory under destination's parent.
2. Use accepted P2C full snapshot export into a private filename. This deliberately
   writes all initial event records once and has the existing full-export memory
   cost. It is not externally resumable cold state.
3. Open the private P1 store with WorldCodec. Stream existing sealed chunks using
   the accepted cache-preserving source iterator. At most four chunks go to each
   `prepare_sealed_append`; compose its descriptor and new segments with exact
   deletions of those absolute event rows in ONE P1 commit. Preserve checked
   storage APIs and generation expectations. Release each batch before the next.
   Never gather all decoded sealed history for transfer. Extend private namespace
   inventory as required. These intermediate private generations need not satisfy
   final cold-capture semantics and must never be published or exposed as sessions.
4. Finalize projected identity links, cold manifest/effective layout, explicit
   descriptors and final commit token/head in one P1 transaction. Do not leave a
   stale collections overlay masking the final EventLog description. Validate
   the exact remaining event-key set `[F,N)` and segment coverage `[0,F)`.
5. Fully validate the private database BEFORE publication: P1 full scrub for
   checked storage, accepted cold capture for current state/identity, and P3A
   `verify_full()` for every segment's event semantics. Close reader and store.
   Full validation is intentional here; ordinary lazy capture stays lazy.
6. Publish using the accepted same-filesystem atomic no-overwrite hard-link
   strategy and directory fsync. Close all database handles before publication.
   Return plain diagnostics, never a World/reader backed by an already closed
   private store. Remove private files on ordinary completion/failure.

All operations are synchronous and require caller-quiescent source state. Do
not implement background writers or a new concurrency protocol. Bound/active-step
input rejection is required; concurrent arbitrary mutation of an unbound source
by another thread is outside this API contract.

### Failure boundary

Before publication, any preparation/commit/validation failure leaves destination
absent and source unchanged. A failed private commit with an uncertain result can
discard the entire unpublished private build; no live-session recovery is needed.
If a competing destination appears, preserve it and fail without overwrite.

After successful hard-link publication, a lost acknowledgement or directory-fsync
error may leave a complete, validated destination. Never delete or overwrite it
as rollback. Propagate failure/uncertainty; an fsync failure does not establish
crash durability. Retrying the same destination must refuse its existence. A
subprocess death may leave private orphan files; never treat them as published
or resumable saves. At the public destination the observable result must always
be absent or a complete validated cold database, never a partial transfer.

## 6. Diagnostics and bounds

Return a plain dict documenting at least final generation/token, event count,
disk segments/events, remaining suffix records, transferred/deleted event rows,
transfer commit count, largest transfer batch, checked payload reads/writes and
bytes (separate staging/transfer/final validation phases), and final file bytes.
Account for initial full staging I/O; do not report only the cheaper transfer.

This API is O(current World + full source history) in total bootstrap work and
may have existing P2 full audit/export/restore peak memory. Legacy conversion
loads a full source World. It is not the bounded gameplay/save API. Transfer
adds at most four decoded input chunks per batch plus codec/P1 encoded buffers
and iterator temporaries; validation has its own streaming/cache temporaries.
Measure those separately instead of claiming a four-chunk total memory peak.
After reopening via capture, the accepted zero-cold-read/current-suffix retention
bounds apply. Other World history collections can still grow.

## 7. Implementation tasks and acceptance evidence

Use tests-first for newly implemented behavior. Keep expected state independent
of the writer/loader. The public writer replaces the test-only assembler for
these tests; do not expose that assembler as production conversion.

- [ ] Implement creation and exact final partition checks. Test empty, list-backed,
  tail-only, prefix-only, mixed, individually sealed tail and at least six sealed
  chunks. Assert source references/flags/cache/index state unchanged; no new seals
  or RNG consumption. Verify all IDs/order/years/causes/typed values and current
  shared parent/child identity after accepted capture. Include surviving non-log
  aliases to sealed Events and the explicit aliased-list rejection boundary.
- [ ] Implement conversion for P2C and genuine P2A/P2B fixtures with at least 13
  legacy identity deltas and a layout overlay, reusing existing legacy tests.
  Assert full source file bytes and logical state unchanged; cover bad rules,
  malformed source, cold source, existing destination, dangling symlink, same
  path and hard-link aliases. Preserve the ordinary APIs' existing behavior.
- [ ] Inject private-build, before-commit, after-private-commit, validation,
  before-publication and after-link/fsync failures. Include subprocess death
  before and after publication, and a destination created between preflight and
  hard link. Assert absent-or-complete result and source preservation; retry
  never clobbers an existing destination. No long simulation needed.
- [ ] Prove independent short continuation: construct an independent unbound
  control from before bootstrap (no retained shared objects), capture the cold
  destination while keeping its store open, continue both 10 years and compare
  exact canonical output and relevant aliases/events. This is unbound restored
  continuation only; future bound-session/save continuation remains a later gate.
- [ ] Measure 4/40/400 synthetic sealed segments with fixed current graph/tail.
  Assert transfer batches never exceed 4, transfer transactions are ceil(H/4),
  each old event row is deleted once, final rows are exactly `[F,N)`, and reopen
  reads zero segment payloads. Report initial staging, transfer, verification I/O
  and memory separately; bootstrap total work must grow linearly, not quadratically.
  Release fixture-only decoded histories before measuring transfer retention.
- [ ] Run focused bootstrap + capture + identity/EventLog tests, the affected
  persistence suite, then one full `simulation/tests` suite on stable final code.
  Record commands, actual results, exact tested SHA, metrics and compatibility
  limits. If isolated CI is used, prove product/test blob equality on landing;
  do not land workflows or run automatic millennium CI.
- [ ] Commit implementation/tests/validation to PR #14's existing branch with
  `[skip ci]`, report exact head, then stop for architect review. Do not proceed
  automatically to session binding, live saves or recovery.
