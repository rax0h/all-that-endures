# P3B — cold EventLog integration with a durable World session

Status: architecture and bounded Sol implementation assignment, 2026-10-03.
Baseline: PR #14, `sim/stage-0-5-stabilization`, verified implementation head
`1093dfac2d395424fb148562d504c008855e6a0f`. Verify the live head before starting;
the documentation commit containing this specification is its continuation.
P3A is accepted completely; see `PERSISTENCE_P3A_VALIDATION.md`.

**Goal:** restore and continue a live World with an immutable disk EventLog
prefix, preserving exact simulation behavior and P2C identity while atomically
saving current state and transferring bounded amounts of sealed history.

**Architecture:** reuse P1 transactions, P2C current links and P3A segments.
Extend EventLog with an opt-in disk backend and compose one save transaction in
the existing session machinery. Keep detached/in-memory and legacy persistence
paths distinct and supported. Python 3.12, SQLite and existing dependencies only.

**Execution:** This remains the full architecture. Work is assigned in
smaller reviewed slices: the composite EventLog is reviewed in
`PERSISTENCE_P3B_EVENTLOG_REVIEW.md`; identity primitives are accepted in
`PERSISTENCE_P3B_IDENTITY_REVIEW.md`; cold identity restoration is accepted in
`PERSISTENCE_P3B_IDENTITY_RESTORE_REVIEW.md`; cold World capture is accepted in
`PERSISTENCE_P3B_COLD_CAPTURE_REVIEW.md`; and explicit cold bootstrap/conversion
is accepted in `PERSISTENCE_P3B_COLD_BOOTSTRAP_VALIDATION.md`. Live cold
open/bind/close and semantic sealing-owner retirement are accepted at
`2819391359fa3e2e16f9c8e3151e99ce06d8a373`; see
`PERSISTENCE_P3B_LIVE_OPEN_REVIEW.md`. The ONLY next authorized Sol slice is
`PERSISTENCE_P3B_COLD_SAVE.md`: atomic cold save/recovery and the mutation guards
needed for its failure states. Detach/export/checkpoint integration remains
separate. Test and commit that bounded slice, then stop for Astra review.

## 1. Scope and decisions

Decision B remains in force: finish durable continued-world architecture before
long-horizon calibration. This tranche is opt-in session integration only.

Selected approach: one logical EventLog, with a cold immutable prefix and a
resident suffix. P1 publishes all components in one transaction. A separate
history-file transaction would introduce a two-authority recovery problem;
materializing all history at bind/restore would defeat P3. Neither is selected.

Do not change simulation rules, RNG consumption, event creation or sealing
eligibility. Do not restart or redesign P1/P2/P3A, replace the normal checkpoint
default, evict other World records, add background writers, introduce WAL or a
new database, perform Stage 1 work, edit main/PR #5, run millennium/endurance
experiments, or merge PR #14. P4 resident-state work and later integrated
validation remain separate. No new automatic save cadence is part of P3B.

## 2. The authority invariant

Let C = 2,048, D = committed disk-prefix event count, F = total number of events
sealed by the existing EventLog rule, and N = total event count. At every usable
session boundary, `0 <= D <= F <= N`, D and F are multiples of C, and logical
index i always has event ID i + 1.

| Logical indices | Runtime representation | Durable authority after save |
| --- | --- | --- |
| `[0, D)` | P3A fixed-prefix reader | `world_sealed_events`, ordinals `[0, D/C)` |
| `[D, F)` | pending sealed chunks | individual `world.events` records |
| `[F, N)` | live EventLog tail, preserving each event's sealed flag | individual `world.events` records |

Pending chunks are already semantically sealed, but not yet transferred to disk
segments. This distinction is mandatory. A caller may also explicitly seal an
individual event in the tail; preserve that flag without increasing F or making
a partial chunk transferable. Pending chunks may retain the existing compressed
in-memory representation, but committed disk chunks must have no mirrored bytes,
per-event owner map, or full-history year/offset index in the session.

`world.events` keys and envelope ordinals remain absolute zero-based logical
indices, never tail-relative indices. Its rows must be exactly `[D, N)`.
There is no row for an index below D and no segment for an index at or above D.
The descriptor and suffix records never compete as authorities.

A save transfers `q = min((F-D)/C, 4)` leading pending chunks, including when no
other World field is dirty. D becomes D + q*C; F and N do not change merely
because storage changed. In the SAME transaction insert q immutable segments,
delete their formerly persisted event rows, and update all descriptors/layout.
For events created since the previous save, omit their selected-segment upserts;
do not invent rows just to delete them. Coalesce each key to one final action,
since P1 rejects duplicate record changes. Never drop a source chunk before
confirmed publication. Never split one save's World and identity edits from
its event publication into separate transactions.

If more than four chunks await transfer, save all outstanding World/suffix edits
and leave the remaining sealed events as suffix rows. Subsequent explicit saves
drain at most four chunks apiece, even without additional simulation. One save
is one generation, not a hidden loop of generations. A true no-op with no pending
transfer writes nothing and does not advance the head.

## 3. Explicit storage mode

Keep the existing simulation schema and P1 format. New opt-in cold snapshots
extend the P2C manifest with `event_storage = "sealed-prefix-tail/v1"` and still
require `identity_storage = "current-links/v1"`. Existing manifests without the
event mode retain their current meaning. Reject unknown modes, identity-delta
authority in cold mode, and incompatible mixtures; do not guess a migration.

The effective `collections/v1` description for `world.events` is
`("EventLog-disk/v1", N, F // C)`. This is a logical collection count, not the
number of record rows. All other collection descriptions keep their accepted
meaning and stable insertion ordinals.

Use P3A's descriptor and segment namespace unchanged. Add two schema-1 records
to its existing `world_event_storage` namespace:

* `session-tail/v1`: typed tuple `(1, D, F, N, last_event_year)`, where the year
  is None iff N is zero. No event objects or per-year arrays in this record.
* `session-commit/v1`: typed tuple `(1, target_generation, commit_token)` for
  acknowledgement identity. Its concrete representation is a 32-character
  lowercase hexadecimal string, as specified by `PERSISTENCE_P3B_COLD_CAPTURE.md`.
  Use a fresh opaque token from outside simulation
  RNG for each prepared transaction; retries of that frozen transaction retain
  its token. Never use only equal values/counters as proof of writer identity.

Declare both P3A namespaces and current-link namespace even when empty. Cold
creation must explicitly write the empty P3A descriptor: P3A's empty append is
a no-op and does not initialize one. Manifest/layout, tail state, P3A descriptor,
head metadata and counters must agree. Require `next_event == N + 1`, prefix
count D, suffix IDs D+1 through N, nondecreasing years, and sealed flags/frozen
values throughout `[D,F)`. Validate the first suffix year against the prefix
descriptor's last year and the suffix's final year against session state.

Lazy opening is not a cold-data scrub. It must validate every loaded current
record and all suffix records, their exact key set/count and current identity
graph, plus checked bounded descriptor/head metadata. It must reject missing or
extra suffix rows, including a duplicate row below D. It must not call
`store.verify_all()` on ordinary cold open/bind, because that reads all segments.
Missing/corrupt cold payloads fail when accessed or explicitly scrubbed, as in
P3A. If a narrow checked head/count accessor is needed, add it to P1 rather than
scattering raw SQL validation through adapters; do not weaken P1 validation.

## 4. EventLog behavior and sealing

Keep EventLog as the object seen by `Simulation`, `World.events_between`, the
canonical digest and archive export (`isinstance(..., EventLog)` must continue
to select their streaming paths). Extend its existing class with explicit
backend state; do not implement an alternative simulation EventLog.

The disk backend routes indexed/sliced/negative access and iteration across the
three ranges above. Preserve equality, append ID/order checks, slice steps,
inclusive year queries, repeated/negative years, empty/reversed ranges, exact
Event/Layer/Ref types, values, causes and frozen semantics. Returning a requested
list may allocate that list; iteration must stream. Recent year queries that
start strictly after the disk descriptor's last year must not read disk payloads.
Other year queries use P3A's bounded search plus the suffix's local search.
Prune year/offset entries for transferred history; do not rebuild a disk-sized
Python index. Overlapping equal-year boundaries must neither skip nor repeat an
event. An event-ID lookup remains arithmetic, not a history scan.

`seal_before(year)` keeps the current rule exactly: seal each leading full tail
chunk whose final event year is strictly less than year. Keep the engine's
existing `world.year - 2` threshold and timing. Sealing freezes caller-visible
Events at that same point and creates pending chunks. It does not perform I/O,
advance the store generation or implicitly save. Save never calls `seal()` on
a mutable tail merely to meet a storage budget. Data alias changes caused by
`Event.seal()`/`freeze()` are authoritative behavior, not a storage invention.

Extend `storage_stats()` to report disk events/segments, pending sealed events
and bytes, tail events, resident decoded segments/events. Compute these from
counters/cache state, never by visiting the prefix. Keep existing legacy keys
meaningful and document any additional keys. Do not label on-disk bytes as
resident bytes or omit pending compressed bytes from the memory accounting.

## 5. Current identity, freezing and retirement

P2C remains the only authority for shared current objects. Keep its typed absolute
paths, final-state link coalescing, copied-payload checks, parent/descendant
restoration and incremental reverse-ownership work. A tail offset shift must not
rename logical event paths.

Cold and pending sealed LOG occurrences are immutable value history, not mutable
identity owners. The log must not register, index or retain their decoded Events
in `_BINDINGS`, `_bound_ids`, `_memo`, baseline ordinals, occurrence indexes,
current-link maps, dirty journals or query caches beyond the bounded reader.
This is the P3A value-equivalence boundary: repeated cold reads need not return
the same Python object. Current non-log World occurrences still preserve their
sharing, even if they refer to a sealed Event retained elsewhere. Do not drop
their sharing merely because the same value appears in history.

At the semantic sealing transition, use the affected event owners and their
reverse dependencies to retire LOG occurrences, refresh links for actual
surviving owners, and unbind obsolete event ownership. Preserve aliases between
current World fields and still-mutable tail data; preserve aliases between
current fields after a shared source value is copied/frozen into an event.
Reanchor a surviving group before dropping a retired log anchor. Do not delete
all ownership for an object still owned by another current record.

An Event object retained by a caller must become frozen as before; a retained
old mutable child detached by `freeze()` must no longer dirty the log. If that
child is still part of current World state, mutations must dirty its surviving
owner. Already sealed tail objects are treated as immutable values for LOG
identity ownership, without stripping sharing among their non-log occurrences.

Cold-mode identity paths may address the log root and mutable-tail occurrences;
they must not descend into `[0,F)` or an individually sealed tail Event. Reject
such malformed saved paths before resolving them, without disk reads. During
creation/conversion explicitly retire/reanchor the corresponding old paths.
Do not discard arbitrary identity rows as a corruption workaround.

`_restore_identity` currently permits sequence-target assignment only into a
plain list. Add a narrow internal EventLog tail-relink operation for validated
mutable-tail target paths: retain the absolute index and Event type/ID/order,
compare copies before relinking, and never assign into a sealed occurrence.
This is restoration-only, not a new public mutation API for historical events.

Audit and adapt ALL entry points, not just the obvious root loop:
`_audit`, `_complete_identity_groups`, `_verify_identity_graph`,
`IdentityOccurrenceIndex._scan`, `_validate_baseline`, `_bind_root_collection`,
`_iter_identity_owners`, `_current_identity_links`, `_owner_value`, `_plain`,
`_unwrap_value`, and mutation/sealing hooks. Reuse a small consistent event-owner
iteration boundary with absolute indices. Traversal through an alias to the
EventLog root must use that boundary too. Preserve cross-session rejection.
Cold open must construct from the captured store, not compare an arbitrary live
World by iterating its prefix. Legacy `bind_snapshot` keeps its full comparison.

## 6. Session APIs, opening and ownership

Add `ate_sim/persistence_session.py` for the cold entry points and composition,
reusing/factoring `IncrementalWorldSession` rather than copying its identity or
dirty-tracking implementation. Public entry points:

* `write_cold_snapshot(world, destination, *, rules_id) -> dict`: explicitly
  create a cold-format snapshot from an unbound in-memory World; return measured
  creation diagnostics. Refuse existing destination and bound/cold input.
* `open_world_session(path, *, rules_id) -> IncrementalWorldSession`: restore
  cold format into an owned session; expose the restored World as `.world`.
  Refuse legacy event mode with an explicit conversion instruction.
* `convert_event_storage(source, destination, *, rules_id) -> dict`: explicitly
  read an existing supported P2 record snapshot and publish a cold destination.
  Accept P2C and genuine legacy P2A/P2B identity modes; refuse cold source,
  existing destination and source/destination identity. Source remains unchanged.
* Cold sessions retain `save() -> int`, diagnostics and context-manager support;
  add `detach(*, materialize_history=False) -> World` and
  `verify_history() -> dict`, plus `resolve_save() -> int` for an uncertain save,
  with the behavior below. Existing legacy session
  APIs/close behavior remain compatible.

Open owns exactly one store connection and a borrowed P3A reader. Capture head,
manifest/layout, tail state, current records/links and prefix descriptor in one
bounded-lifetime read transaction. Release it before returning the session.
P3A's constructor currently starts its own transaction; do not nest it inside
P1's read transaction. Add a narrow
`SealedEventPrefix.from_active_read_transaction(store)` factory which requires
an active caller-owned read transaction and shares the constructor's checked
descriptor initialization. It neither begins nor ends that transaction. Preserve
the standalone constructor's accepted behavior. This factory may also capture
the confirmed new prefix while resolving acknowledgement.

Restore non-event World state with the accepted codecs/adapters. Load only the
suffix event rows, reconstruct pending chunks and exact tail flags, restore
current aliases, then bind that captured graph. Do not route through the old
full-history `read_snapshot`/baseline validation and then swap a cold reader in.
No read transaction remains pinned during gameplay. Another writer may advance
the head afterward; this session's captured immutable prefix stays valid and
its next save must encounter the existing stale-generation protection.

Create/conversion is an explicit, potentially full-state bootstrap operation.
The source in-memory/legacy read may have the existing O(history) cost; document
it. Reuse full record export and P2C conversion rules, never a World-sized blob.
Build in a private destination file, retire/reanchor sealed-log identity links,
and transfer all eligible chunks in batches of at most four. Intermediate
private bootstrap generations are not a resumable published session. Do not
read an existing disk prefix into identity discovery. Finish full validation
before P2A-style atomic no-overwrite publication and directory fsync. Failure
leaves the source untouched and destination absent, except an acknowledgement
lost after successful publication may leave one complete destination. Document
that case; never overwrite/reconvert it blindly. Initial creation does not seal
additional events. A list-backed source is normalized without inventing sealed
chunks. Cold-source backup uses P1 backup, not this full-state conversion path.

## 7. One save, one publication

The API is synchronous, single-owner and non-reentrant. Save/open/detach/export
operate at a completed simulation step. Reject active scope/reentrant operations
before mutating source state. No concurrent simulation mutation during preparation
or acknowledgement is supported; enforce an operation guard on supported session,
World and EventLog entry points. Do not hold a read transaction through commit.

1. Check session/store availability and generation. Freeze a save plan against
   the current generation without changing D or discarding pending data. Refresh
   only affected identity owners. Select up to four pending chunks.
2. Call accepted `prepare_sealed_append` for those chunks. Its expected generation
   must equal the session's expected generation; do not silently rebase a stale
   World onto the latest descriptor. Require its `before` to match D.
3. Compose one final action per record: changed/deleted World records, P2C link
   edits, suffix upserts/deletions, layout, session-tail, commit token and P3A
   descriptor. Include new immutable segments and exact head metadata/counters.
   A suffix event moved to a segment cannot also be upserted as a record.
4. Call P1 `commit(expected_generation, changes, new_segments, metadata)` once.
5. After confirmed success, publish the new runtime prefix and suffix partition,
   release selected pending bytes/cache entries/owner bookkeeping, install new
   baselines, and clear only the acknowledged dirty/link changes. Keep the SAME
   EventLog object and untransferred mutable Event objects; references and aliases
   retained by callers must remain useful. Close the old internal reader after
   the replacement is ready. No decoding of older segments is needed.

Construct the post-commit transition so it is small and prevalidated. If a new
reader cannot be installed or acknowledgement cannot be determined, enter
recovery-required state; do not allow continuation with a partially published
in-memory boundary. A process dying here is safe because reopening uses the
committed descriptor and suffix exclusively.

## 8. Failure and recovery contract

States are active, preparing, recovery-required, stale and closed. Recovery is
about an exact frozen save plan, not replaying simulation or emitting events.

| Situation | Durable state | Required session behavior |
| --- | --- | --- |
| Validation/encoding failure before commit | old | retain World changes, pending chunks and dirty/link state; no boundary advance |
| Proven rollback/before-commit failure | old | retain plan/source ownership; allow corrected retry; no early trimming |
| Process death during writes/before commit | old | reopen old complete World and event partition |
| Commit succeeds but acknowledgement is lost | new | recognize exact plan and finalize once, without another generation |
| Process death after commit/before runtime publication | new | reopen new complete partition; no duplicate events |
| Stale writer / another writer wins | winner's complete state | raise conflict; never graft losing World/tail onto it |
| Outcome cannot be read, or head advanced past the expected successor | unknown to caller | recovery-required/stale; block further simulation and saves; close/reopen latest explicitly |

Resolve a lost acknowledgement in ONE read snapshot: require successor generation
`expected + 1`, matching commit token, metadata and tail/prefix state, and checked
matching changed records/deletions and newly written segments. Extend P2's
record-only acknowledgement check to cover these segment writes. Compare only
the plan's at-most-four segments; never verify the whole prefix implicitly.
Only this session's token can confirm its save. If still at expected generation,
the old commit remains authoritative and the same plan can retry. If unreadable,
do not guess based on a cached generation or a matching year/event count.

`resolve_save()` performs that checked resolution without committing or running
simulation. A matching successor finalizes the retained plan and returns its
generation; an unchanged expected head returns to active state with all unsaved
changes intact. In the latter case it may discard the prepared encoding, because
non-publication was proved; a later save is a new preparation. A different or
later head raises conflict and marks the session stale. An unreadable outcome
leaves recovery-required state and raises. In active state with no unresolved
plan it returns the captured generation without writing.

Before-commit failure does not roll back the user's live simulation edits; it
leaves them unsaved, exactly as accepted P2 behavior. No automatic simulation
retry, event renumbering, event re-emission or discarded dirty state. A stale
World may be explicitly detached for inspection, but cannot overwrite the newer
save. A recovery-required session must be resolved or closed before detach.

## 9. Close, detach, retained references and exports

Cold `close()` is idempotent and does not save. It closes owned readers, clears
tracking ownership without walking the disk prefix, closes the store and marks
the disk-backed log unusable. It does not implicitly materialize history. Cached
hits, tail-only reads, len/iteration, append and sealing on that closed log must
fail explicitly; no silent reopening by filename. Already returned frozen Event
values remain readable and frozen. Other already loaded World values can be
inspected, but the closed World is not a continuing simulation.

Guard `Simulation.__init__`, `step`/`run` and `World.emit` so closed or unresolved
cold state fails BEFORE year/counters/current records change, even if a step
would emit no events. A caller closing `session.store` directly must produce the
same fail-before-mutation behavior. Do not leave a global binding retaining an
entire World after close. Caller-owned extra P3A readers retain fixed-prefix
semantics while their store is open; closing the store invalidates them.

`detach()` without `materialize_history=True` raises an explicit error, leaving
the cold session active. `detach(materialize_history=True)` streams the prefix
into the existing portable in-memory compressed EventLog representation, adds
pending chunks/tail, and preserves current aliases and exact values. This is an
explicit O(total history bytes) resident-memory operation. Construct and check
the replacement before switching the World; on failure keep the session and
original log usable. On success return the same World with a standalone log,
unbind it, and close the session/store. No save is implied: unsaved live changes
are included. Preserve current tail Event identities through detach and document
that the old retained disk-log reference is closed after replacement.

`World.digest()` and `history_archive.export_archive()` remain explicit full
history passes, streaming the logical sequence with bounded cold decoding. Keep
canonical bytes/digests/archive values equal to the unbound control. The existing
archive's separate event/causal passes are allowed; a sorted/list copy of the
whole cold log is not. Export never rebinds, detaches or mutates the World. A save
or regular open must not call digest/archive as a validation shortcut. Failed
export leaves no partial final archive and keeps the session usable.

`verify_history()` calls P3A `verify_full()` (including warmed-cache bypass),
validates the loaded suffix and boundary, and reports counts/bytes separately
from lazy-open guarantees. It requires a quiescent World. It must not grow the
ordinary cache above four or retain decoded history in identity structures.

Normal `checkpoint.dumps/save` remain legacy in-memory operations. Detect a cold
World and raise a clear instruction to use the session or explicitly detach,
before digesting or opening/truncating a target file. Direct pickle of a cold log
also fails deliberately; no connection, path or reader is serialized. Keep
existing schema-8 checkpoints, accepted P2 reads/bind/save and legacy conversion
tests intact. `read_snapshot` and `bind_snapshot` must reject cold mode clearly,
rather than returning a World backed by a store they have already closed.
`write_snapshot` rejects cold input; users choose explicit detach or store backup.
Importing a normal trusted checkpoint is explicit load followed by
`write_cold_snapshot`; no automatic checkpoint conversion or schema bump here.

## 10. Measurable bounds and honest limitations

Let H be committed cold events, P pending sealed events, T tail events, A affected
current owners/links, and W the other current World state. All counts below refer
to actual checked I/O and retained structures, not helper invocation counts.

| Operation | Required event-history bound |
| --- | --- |
| cold open / current-identity bootstrap | 0 cold segment payload reads; O(P+T) event values, no O(H) event bookkeeping |
| len / append / stats / close | 0 cold payload reads |
| cold point then immediate repeat | 1 payload read then 0 additional reads |
| ordinary cold cache | at most 4 decoded segments = 8,192 events |
| recent query strictly beyond disk last year | 0 cold payload reads |
| general year range | logarithmic search plus returned data; no copied global year index |
| save one eligible chunk | 1 new segment, at most C old suffix-row deletions, bounded metadata + affected World/link writes; 0 old cold payload reads |
| save with large transfer backlog | at most 4 new segments / 8,192 transferred events; no implicit draining loop |
| no-op after backlog drained | 0 payload writes/deletes, no generation change |
| failure acknowledgement | checked reread of changed records and at most 4 NEW segments, not old history |
| digest/archive/full history verification | explicit O(H+P+T) traversal, bounded decoded prefix/cache; no retained O(H) list |

P1 encoding/preparation temporarily holds the selected batch, and a verification
pass can hold a streaming chunk in addition to an already warm cache. Report
these temporaries separately; do not misstate four cached chunks as a four-chunk
total peak. Bytes depend on event sizes, so report actual bytes as well as counts.
Bound save work by changed suffix data + A + at most four transfer chunks, not
by H. Do not rescan all untouched suffix records on every save.

Use synthetic fixtures at 4, 40 and 400 disk segments with the SAME suffix and
comparable current-owner shape. Assert zero cold opens, identical local-save I/O
counts and zero cold history ownership entries. At 100, 300 and 1,000 unrelated
current alias groups, local alias work must remain affected-owner-only. Report
encoded payload bytes, row deletions, segment reads/writes, identity occurrences,
session event bookkeeping, cache occupancy and retained/peak memory using a
reproducible method. Measure event-backend memory separately from W; for fixed
suffix/cache it must not grow with H. Provide actual tables, not just big-O claims.

P and T can grow when saves are delayed, transfer throughput is insufficient or
the existing age rule keeps events mutable. This tranche does NOT bound them
independently of workload; it must expose them, support explicit drain saves,
and reclaim them after transfer. Other World collections (including event_ids,
people and nested provenance) can also grow. Do not claim bounded total World
memory, indefinite playability or Stage 0.5 completion from P3B.

## 11. Implementation tasks and review gates

Use focused red/green tests for each behavioral task. Preserve accepted tests;
do not rewrite their expectations to conceal changed simulation behavior.

### Task 1 — composite EventLog and sealing boundary

Files: `ate_sim/event_log.py`, narrow `ate_sim/persistence_events.py` factory;
new `tests/test_persistence_session.py` (may split failure/scaling tests later).

- [ ] Add tests for counts 0, C-1, C, C+1 and multiple chunks; strict sealing
  threshold, same-year boundaries, negative years, all slice directions, frozen
  tail flags and retained references. Compare each operation to independent
  existing in-memory EventLog behavior.
- [ ] Implement the three ranges and bounded reader lifecycle, same EventLog type,
  unchanged sealing eligibility, local suffix indices and explicit backend stats.
- [ ] Verify source remains authoritative on uncommitted transfer preparation;
  transferring exactly four chunks leaves a fifth chunk pending and accessible.

### Task 2 — mode, restore and explicit creation/conversion

Files: new `ate_sim/persistence_session.py`; narrow changes to
`persistence_adapters.py`, `persistence_schema.py` only if classification needs it,
and the session constructor in `persistence_tracking.py`.

- [ ] Implement the APIs and versioned records in sections 3/6. Restore one pinned
  generation, with no nested transactions or P1 full scrub on lazy open.
- [ ] Test empty prefix, empty tail, pending sealed suffix, malformed/mixed modes,
  gaps/overlaps, bad counters, corrupt descriptor/suffix/current links, prefix
  corruption deferred to access, and concurrent head advance around opening.
- [ ] Test explicit P2C and genuine P2A/P2B conversion, source preservation,
  destination refusal, failed private build, backup/relocation, and post-conversion
  values/types/identity. Creation/conversion full-state cost must be explicit.

### Task 3 — identity integration and reclamation

Files: `persistence_tracking.py`, `persistence_identity.py`, the adapter graph
walkers. Reuse the accepted occurrence index and current-link final-state reducer.

- [ ] Test a shared dict and shared parent+child across World fields and tail
  data; mutate through retained aliases before and after sealing, save/restore,
  reanchor/delete a canonical owner, and test cross-session rejection.
- [ ] Test explicit individual Event.seal in the tail, an Event retained outside
  the log, and a shared mutable child detached by freeze. Check frozen status,
  surviving current identity and which owner becomes dirty.
- [ ] Implement logical-owner traversal, sealed-log retirement and memo/binding
  cleanup. Guard malformed cold identity paths without reading cold segments.
- [ ] Instrument every graph-walker entry to prove cold open/bind/save/close do
  not enumerate or pin the prefix, including aliases of the log root. Verify
  after repeated seal/save cycles that retired owners and original source
  objects are not retained by session internals (use weakrefs where supported
  and inspect retained reference maps). Caller-retained values are excluded.

### Task 4 — atomic save and recovery

Files: `persistence_session.py`, `persistence_tracking.py`; add
`tests/test_persistence_session_failures.py`. P1 changes only for a narrow checked
metadata accessor if needed; no transaction/storage-format redesign.

- [ ] Implement bounded preparation, one coalesced transaction, commit tokens,
  segment-aware acknowledgement and post-commit partition installation.
- [ ] In the SAME save, change a World value and parent/child alias, edit a tail
  event, append events, and move existing suffix rows into at least one segment.
  Assert exact event namespace key set `[D,N)`, segment IDs `[1,D]`, F/N/counters,
  current links and continued simulation after reopen.
- [ ] Inject failures before commit, during writes, after commit, and before
  runtime partition installation; include subprocess death on both sides of
  commit, stale writer, unavailable acknowledgement reads, and a second writer
  advancing after a lost acknowledgement. Assert complete old-or-new states,
  retained unsaved state where applicable, no duplicate/absent events, and no
  second generation for a resolved acknowledgement. Equal values from another
  writer's token must not acknowledge this writer.
- [ ] Exercise persisted versus newly appended selected events, residual backlog,
  identity-only changes, metadata-only changes, pending-only drain, repeated save,
  and a true no-op. No duplicate record actions or rewrites of old segments.

### Task 5 — lifecycle, compatibility and explicit full-history operations

Files: session/log/tracking modules; narrow guards in `core.py`, `engine.py` and
`checkpoint.py`; `canonical_stream.py`/`history_archive.py` only if adaptation
is needed to retain their existing streaming behavior.

- [ ] Implement close, explicit detach and verify_history. Test store closed under
  session, warmed cache after close, double close, extra borrowed reader, failed
  detach, unsaved detach, and attempts to emit/step/run after close or uncertain
  save. World year/counters/values must be unchanged by rejected operations.
- [ ] Compare digest and archive logical outputs to an independent in-memory
  World; run both with cold caches and during cache eviction. Corrupt a warmed
  segment and require explicit verify_history failure. Fail export midstream
  and prove no partial destination and continued session usability.
- [ ] Keep all legacy snapshot/session/checkpoint tests green. Cold checkpoint
  serialization and old detached APIs fail early with usable instructions,
  leaving any destination file unchanged. Explicit detach restores legacy
  checkpoint round-trip and continued simulation.

### Task 6 — independent continuation and scaling evidence

Files: `tests/test_persistence_session.py`, optional
`tests/test_persistence_session_scaling.py`, new
`PERSISTENCE_P3B_VALIDATION.md` and `persistence_p3b_validation.json`.

- [ ] Use independently generated Worlds with the same seed/configuration: one
  never bound, one newly opened cold session, and one restored after multiple
  saves. Do not derive the control from the serializer under test. Run short
  real continuations (about 10-20 years) plus synthetic chunk-crossing fixtures;
  compare digest, exact ordered event values/IDs/years/causes/sealed flags,
  counters and current aliases at each checkpoint and after further steps.
- [ ] Vary save cadence and chunk-transfer backlog without varying simulation
  input; prove identical continuation and no RNG consumption by persistence.
- [ ] Produce section 10's 4/40/400-segment and 100/300/1,000-alias measurements.
  Include a local wallet deletion as well as an append/transfer, and enough
  drain cycles to establish actual reclamation. Do not replace this with a
  millennium, wall-time-only assertion or total-process memory claim.

## 12. Validation commands, delivery and stop

From repository root, run the affected suite during development:

```sh
PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_incremental_store.py simulation/tests/test_persistence*.py simulation/tests/test_cold_history.py simulation/tests/test_event_year_queries.py simulation/tests/test_canonical_digest.py simulation/tests/test_history_archive.py
```

Then run one complete unit/integration suite on stable final code:

```sh
PYTHONPATH=.:simulation python -m pytest -q simulation/tests
```

No `run_long_history.py`, canonical/endurance workflow or balance probe. The
normal PR workflow currently includes a millennium: use `[skip ci]` on commits
to this PR to avoid invoking it. Do not weaken/delete that workflow. If local
execution is unavailable, use an isolated targeted/full-suite-only candidate as
earlier tranches did, and prove exact product/test blob equality on landing;
do not land the temporary workflow or claim candidate evidence for changed code.

Commit implementation/tests/evidence to PR #14. Report the exact landed SHA,
exact tested source, commands/results, measured read/write/deletion/memory tables,
failure matrix, compatibility behavior and remaining limitations. Stop for
Astra review. P3B acceptance, P4, default checkpoint changes, long-horizon runs,
calibration, Stage 1 and PR merge require later instructions.
