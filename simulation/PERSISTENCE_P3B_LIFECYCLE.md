# P3B lifecycle, explicit history operations and compatibility

> Bounded Sol implementation assignment. Implement task by task using the
> executing-plans workflow; Astra reviews the result. No new agents are needed.

**Status:** next assignment, 2026-10-04 America/Chicago.
**Baseline:** PR #14, `sim/stage-0-5-stabilization`,
`2fe72cb7b84a487b3c5adc0c8475be614e616816`.
Verify the live head; this documentation commit continues that baseline.
**Parent contract:** `simulation/PERSISTENCE_P3B.md`, principally sections 6,
9 and 10. Atomic cold save/recovery is accepted; do not reopen that design.
**Goal:** finish the explicit ownership/portability/history boundaries around
the accepted durable World session without replacing normal checkpoints.
**Architecture:** keep one session/store and the existing EventLog; materialize
history only on explicit detach, stream other full-history operations, and
reject incompatible legacy API calls before they scan history or touch output.
**Stack:** existing Python 3.12/SQLite/typed codecs; no new dependency or format.

## 1. Scope and file ownership

Add public cold-session methods:

- `detach(*, materialize_history=False) -> World`
- `verify_history() -> dict`

Finish cold behavior of existing World.digest, history_archive.export_archive,
checkpoint.dumps/save, direct EventLog pickle, and P2 read/write/bind entry
points. Preserve accepted save/resolve and close guards; extend them only for
these lifecycle operations.

Prefer new `simulation/ate_sim/persistence_lifecycle.py` for cold lifecycle
composition, with small session dispatch and guard changes in
`persistence_tracking.py`. Narrow changes are allowed in `event_log.py`,
`core.py`, `history_archive.py`, `checkpoint.py`,
`persistence_adapters.py`, and schema/cache classification only as needed.
Reuse canonical_stream and accepted P3A verification; do not replace their
formats or algorithms without a specific compatibility failure.

New tests: `tests/test_persistence_lifecycle.py` and
`tests/test_persistence_history_operations.py`. Add an integrated short scenario
to the existing cold-session tests if appropriate.
Evidence: `simulation/PERSISTENCE_P3B_LIFECYCLE_VALIDATION.md`.

No normal checkpoint-default replacement, automatic save/export, new history
format, background threads, P4, Stage 1, balance/magic changes, millennium/
endurance, unrelated features or merge. Total World-memory bounding is not
claimed by this slice.

## 2. Shared operation and lifetime contract

Use the existing cold lifetime marker and operation/state guards.

All new explicit operations require an open owned store, a completed simulation
step, no active current-people scope, and no concurrent/reentrant operation.
Check before allocating history, computing a digest, creating output directories/
temporary files, changing World fields or closing resources.

During a guarded history read or detach preparation, supported World/container/
EventLog mutations, save, resolve, close and simulation entry points must reject
before mutation. EventLog reads needed by the operation remain allowed.
Do not create a public "disable guards" option. Archive's internal digest pass
must use a narrow internal path under the same operation, not unrestricted
public reentrancy.

State policy:

| State | digest/archive/verify | explicit materializing detach | close |
| --- | --- | --- | --- |
| active, quiescent | allowed | allowed | existing behavior |
| preparing or another operation active | reject | reject | reject reentrant call |
| recovery-required | reject; resolve or close first | reject | allowed when no operation executing |
| stale | reject; use explicit detach for the local branch | allowed if store remains open | allowed |
| closed or directly closed store | reject before work | reject; never reopen by filename | idempotent resource cleanup |

Stale detach materializes this session's local World and fixed prefix. It does
not silently load the winner, resolve against it, save, or overwrite it.
A detached local branch may subsequently continue independently; its former
session remains closed and cannot save over the winner.

Do not change durable generation, journal contents, current aliases, D/F/N,
event values, RNG behavior or ownership during successful read-only operations.
Reader-cache occupancy/read diagnostics may change. Restore operation guards on
failure so an otherwise active session remains usable for inspection/close and
unaffected operations. Corruption is reported, never repaired silently.

Cold close still performs no save, materialization or prefix traversal.
After close, loaded ordinary values remain inspectable and already returned
frozen Event values remain frozen/readable, but the World cannot emit/step/run
and its retained disk log cannot even serve cached/tail-only reads.
Keep direct store.close and all existing recovery-state cleanup tests green.

## 3. Explicit detach

`detach()` with the default False raises StoreError explaining that cold history
requires `materialize_history=True`; leave state and resources unchanged.

With True, preserve logical D/F/N values through conversion to a standalone
in-memory EventLog: after detach its disk count is zero, its compressed sealed
count is F, and its tail is exactly the previous [F,N) tail.
No save or new sealing occurs. Preserve IDs/order/years/causes/values, each
Event's exact sealed flag/frozen semantics, and unsaved edits.

Build the complete replacement before publishing it:

1. Stream committed prefix Events into complete compressed chunks using the
   existing in-memory EventLog representation. Decode only a bounded chunk
   window at a time; do not create list(old_log) or a second whole-history
   Event list. Existing pending compressed chunks may be reused as immutable
   bytes after their boundaries are validated.
2. Build the standalone count/year index without changing the source. Preserve
   the existing logical F even if additional tail Events happen to be old enough
   or individually sealed; do not call seal_before to reconstruct the boundary.
3. Preserve the SAME World and resident tail Event objects. Prepare unbinding/
   current-graph rewiring with a shared memo so parent/child aliases survive.
   Historical decoded copies do not become current identity owners.
4. Publish the standalone log and prepared current graph, remove the World/new
   log's cold-only lifetime state, release tracking, and close the old borrowed
   reader(s) and owned store. Close remains idempotent afterward.

Construction/decoding/validation failure must leave the original World, log,
current references, bindings, pending edits and session/store usable; discard
only the private replacement. Existing _unwrap_value mutates dataclass fields
in place, so do not call it destructively during supposedly reversible staging.
Use staged field replacements or an undoable current-graph transition.
Do not close the store before the standalone World is complete.

A retained reference to the old disk EventLog becomes closed after success.
A retained tail Event remains the same object visible in the detached World.
Aliases among current fields and tail payloads must survive. If existing unbind
semantics replace tracked container wrappers with plain containers, preserve
that documented boundary: the returned World has the shared plain graph;
old separately retained tracked wrappers remain tied to the closed session.
Do not claim those obsolete wrappers have become detached mutation handles.

If the current graph contains an alias to the canonical EventLog root, remap
that occurrence to the new log using the shared memo without traversing history
for identity discovery. This does not add a new on-disk whole-EventLog codec.

The returned World supports ordinary simulation, schema-8 checkpoint
dumps/loads, digest and explicit fresh snapshot creation. No store, reader,
weak session reference or cold lifetime marker may leak into its serialized
form. A cold source copied this way incurs O(total compressed history plus
legacy in-memory index size) resident cost; this is deliberate and opt-in.
Report it honestly, separately from bounded streaming decode memory.

## 4. Explicit full-history verification

verify_history is a read-only active-session operation. Call the captured
prefix's accepted verify_full: it must reread every captured disk segment
through checked storage even when its four-segment cache is warm.

Validate the resident suffix in streaming/chunk order: contiguous absolute IDs,
nondecreasing years across disk/pending/tail boundaries, frozen sealed pending
chunks, exact tail flags/types, counts, last year, next_event=N+1, and the
accepted event-value validation. Unsaved live suffix edits are legitimate; do
not require live N/F to equal the last saved descriptor.

This verifies the session's captured immutable prefix plus its current resident
suffix, not a newly loaded/latest World. Do not recapture another writer's
descriptor or rebind identities. Do not call store.verify_all, which has a
different full-store scope.

Return a plain diagnostics dict with documented keys for captured generation,
disk events/segments, pending sealed events, tail events, checked segment-read
count/bytes and inspected suffix event count. Derive I/O from before/after
diagnostics rather than cumulative counters disguised as operation cost.
Any reported encoded-byte metric must state its representation.

Successful verification advances no generation and leaves values/aliases/
journals unchanged. Failure leaves operation guards released, no trimming and
no partial identity retirement. Cache remains <=4; verification temporaries
are measured separately. A warmed-cache corruption/deletion must fail.

## 5. Digest and archive

World.digest remains the established canonical streaming digest. Cold
World.digest acquires the operation guard before traversing any current state.
Preserve canonical bytes for identical unbound/cold/detached Worlds.

history_archive.export_archive keeps its current API and SQLite schema 1.
Preflight the cold session before opening a temporary/output path, including
when the caller supplies digest=. Preserve exclusive no-overwrite publication,
cleanup on pre-publication failure, causal-link validation, logical SHA256 and
existing deterministic output rules. An exception after final publication may
leave a complete archive; never a partial final archive.

Keep EventLog iteration streaming. Existing separate event-node and causal-edge
passes are allowed; do not sort or copy the full cold log. Do not bind decoded
history or alter the World to export it. If no digest is supplied, compute it
under the export's internal operation guard; supplied digest keeps its existing
caller-responsibility semantics and must not bypass state/lifetime checks.

Do not turn ordinary save/open/close/gameplay into implicit digest/archive/
verification operations. Small explicitly requested history slices remain
ordinary bounded-access behavior.

## 6. Deliberate legacy compatibility gates

- checkpoint.dumps and checkpoint.save reject cold Worlds clearly BEFORE
  world.digest, pickle traversal or destination creation/truncation. Point users
  to session.save or explicit materializing detach. Empty-prefix cold sessions
  count as cold too. Do not change CHECKPOINT_SCHEMA=8.
- EventLog.__getstate__ rejects a disk-backed log deliberately and immediately.
  Do not serialize its connection/path/reader/lifetime marker. Preserve loading
  and round-tripping existing portable in-memory EventLogs.
- P2 read_snapshot must recognize a cold manifest using bounded checked metadata
  BEFORE its current store.verify_all call; otherwise a rejection needlessly
  scrubs the archive. Raise an instruction to use open_world_session.
- Legacy bind_snapshot similarly rejects cold storage before full baseline
  comparison/binding, without touching historical payloads.
- P2 write_snapshot rejects cold input before full audit/export or destination
  side effects. Explicit detach or store backup remain the supported choices.
- Preserve genuine P2A/P2B/P2C read/bind/save, explicit convert_event_storage,
  cold bootstrap, backup/relocation and old schema-8 checkpoint behavior.
  No schema bump, silent migration, weakening of legacy full validation or
  replacement of the normal checkpoint default.

## 7. Bounded task sequence and review tests

For each task add the failing tests first, implement narrowly, run focused
tests, and commit with [skip ci]. Do not mark architect acceptance yourself.

### Task 1 — operation guards and early compatibility rejection

- [ ] Implement shared lifecycle guard dispatch and archive internal-digest path.
- [ ] Test active-step/current-scope/reentrant calls, stale/unresolved/closed/
  directly closed store behavior, and guard release after injected failure.
- [ ] Test checkpoint rejection before a monkeypatched digest is called and
  before absent/existing target paths change; pickle rejection must read zero
  segments. Test zero-segment and populated cold sessions.
- [ ] Test legacy read/bind/write refusal with segment reads/verify_all/full
  identity audit patched to fail if reached. Preserve valid legacy round trips.
- [ ] Run new lifecycle tests plus existing checkpoint and cold-session guards.

### Task 2 — streaming detach and ownership transfer

- [ ] Implement detach using staged standalone history and current graph.
- [ ] Test empty, prefix-only, mixed, pending and individually sealed-tail
  partitions, recent unsaved edits and a multi-chunk prefix.
- [ ] Keep same World/tail Event identities and current parent/child sharing;
  reanchor current log-root aliases where supported in memory.
- [ ] Inject early/middle/final history-read/compression and current-unbind
  staging failures: original references/journals/store remain usable and no
  output is published. Verify stale detach leaves winner's store unchanged.
- [ ] After success, old log/old session reject use, returned World continues
  against an independent unbound control, and checkpoint roundtrip preserves
  sharing/values. Check weak-reference cleanup after caller references drop.
- [ ] Run lifecycle, EventLog, identity, bootstrap/conversion and checkpoint tests.

### Task 3 — explicit verification, digest and archive

- [ ] Implement verify_history and guarded streaming digest/archive.
- [ ] Warm the cache, corrupt/delete a captured disk segment, and prove
  verify_history fails through checked reads. Healthy warmed verification
  rereads exactly the captured segment count and reports suffix inspection.
- [ ] Compare digest and archive logical contents/causes/links/metadata against
  an independent unbound control; preserve supplied-digest behavior.
- [ ] Inject archive mid-read/encoding/SQL/publication failures: no partial final
  archive, existing destination untouched, resources released, session state
  and unsaved changes unchanged. No automatic save.
- [ ] Test export callbacks cannot mutate/save/detach/close the World during
  export, while internal digest works without opening general reentrancy.
- [ ] Run history-operation tests plus canonical digest/archive/P3A verification.

### Task 4 — short integration matrix and evidence

- [ ] Independent control versus cold session: real short simulation, append/
  seal, atomic save, close/reopen, continue, explicit verification/digest/archive,
  unsaved edit, detach, checkpoint roundtrip, then independent continuation.
  Compare typed events, exact digests, flags, causes, counters and current aliases.
- [ ] Keep existing stale/rollback/writer-death/lost-ack save tests unchanged.
  Add a resolve-then-detach/export check; neither operation implicitly resolves.
- [ ] At 4/40/400 cold segments and fixed suffix/current shape, count streaming
  reads, max reader cache, decoded temporaries, retained identity/memo entries,
  encoded/compressed bytes and retained/peak allocations. Fixture construction
  is excluded. Full traversal time/I/O grows with history by design.
- [ ] For verify/digest/archive, decoded Event retention stays a bounded window,
  independent of old history; do not mislabel full World/SQLite buffers as
  EventLog cache. For detach, report growing compressed output/index memory
  separately from bounded decoded working state; no bounded-total-memory claim.
- [ ] Record an honest requirement matrix against parent sections 2-10:
  accepted implementation/test evidence versus remaining limitations.
  This is an integration review input, not permission to declare Stage 0.5 done.
- [ ] Run focused lifecycle/history tests, affected persistence/EventLog/
  checkpoint/digest/archive tests, then ONE full simulation/tests suite.
  Record exact SHA, commands, pass counts, timings and actual measured tables;
  verify landed product/test blobs equal the tested candidate.

## 8. Review focus and handoff gate

Pay particular attention to: failed detach accidentally mutating live dataclasses;
a stale/closed lifetime marker surviving successful detach; a caller-supplied
archive digest bypassing preflight; legacy read_snapshot scrubbing cold segments
before rejection; and a partial/individually sealed tail being resealed during
materialization. Each is explicitly covered by the owning tasks above.

Use the established isolated safe workflow, never the normal millennium job.
Do not weaken existing gates or land temporary candidate workflows.
For a long pending test run, provide its run ID/link and stop; the user will
re-prompt after completion. Do not repeatedly poll or wait out the run.

Land only this slice and validation evidence on PR #14's branch with [skip ci],
report the exact head, then stop for Astra review. No PR merge, Stage 1 or
long-horizon calibration. Stage 0.5 remains decision B.
