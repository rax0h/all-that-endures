# P3B atomic cold save and recovery — bounded implementation plan

> For Sol: implement this plan task by task using the executing-plans workflow.
> The user hands this assignment to Sol for native implementation; Astra reviews
> the result. No additional agents or architectural restart are required.

**Status:** next bounded assignment, 2026-10-04.
**Baseline:** PR #14, `sim/stage-0-5-stabilization`,
`2819391359fa3e2e16f9c8e3151e99ce06d8a373` (live open accepted).
Verify the live head; this design commit continues that baseline.
**Spec:** `simulation/PERSISTENCE_P3B.md`, especially sections 2, 3, 5, 7, 8, 10.
**Goal:** a cold session can save, reopen and continue identically, publishing
current World state and a bounded event transfer in one P1 transaction.
**Architecture:** reuse the accepted session, P2C current links, P1 checked
transactions, P3A append preparation and EventLog prefix adoption. Freeze one
private save plan; identify its publication by generation plus an opaque token.
**Stack:** existing Python 3.12/SQLite/typed codecs; no new dependency or format.

## 1. Scope and files

This assignment enables cold `save() -> int` and
`resolve_save() -> int`, with the minimum guards that make their failure states
safe. It includes stale detection, lost acknowledgement, runtime publication,
writer death, short independent continuation and measured save bounds.

Primary changes:

- New `simulation/ate_sim/persistence_cold_save.py`: private preparation,
  checked resolution and publication helpers. Keep transaction composition out
  of the already large tracking module.
- `persistence_tracking.py`: cold dispatch, captured baselines, state machine,
  affected-owner projection and pre-mutation guards; reuse legacy machinery.
- `persistence_session.py`: transfer the captured head/descriptors to the live
  session and remove the obsolete public docstring saying cold saves are absent.
- Narrow `core.py`, `engine.py`, `event_log.py` changes: lifecycle/operation
  guards needed below. Preserve accepted EventLog adoption and checked reads.
- `persistence_adapters.py` only if a named, excluded runtime guard field needs
  explicit classification; no persisted schema expansion for that guard.
- New `tests/test_persistence_cold_save.py`,
  `tests/test_persistence_cold_save_failures.py`,
  `tests/test_persistence_cold_save_bounds.py`; extend live-open tests only
  where cold-save refusal is deliberately superseded by this assignment.

Do not implement detach, archive/digest changes, public verify_history, normal
checkpoint replacement, automatic save cadence, P4, balance/magic changes,
Stage 1, millennium/endurance, or merge. Legacy in-memory/P2/P2C paths retain
their existing meaning. Existing cold create/convert/open and P3A checked
storage are accepted; do not redesign them.

## 2. Exact authority and plan boundary

C=2,048. Capture committed baseline D0, F0, N0, head metadata/counts and generation
G when opening (from the SAME accepted capture transaction). Do not reconstruct
that baseline by enumerating old event rows on every save.

At preparation, let D=D0, F=D+C*len(log._chunks), N=log._count. Validate counts,
captured descriptor agreement, last year, next_event=N+1 and changed Event
ID/year/type/frozen semantics. Validate touched boundaries and selected chunks;
do not scrub untouched history or rescan all unchanged suffix records.
Reject corrupted/inconsistent input before P1 commit.

Select q=min((F-D)/C,4), D1=D+q*C. F and N do not change because of storage.
Individually sealed tail Events remain in [F,N); they are not eligible partial
segments. Save must not call seal_before or seal any additional Event.

Use a private immutable-plan container, `ColdSavePlan`, holding:

- expected and target generations G/G+1; fresh 32-character lowercase hex token,
  generated outside simulation RNG;
- captured before/after prefix and tail descriptors, committed N0;
- final record changes, <=4 NewSegments, exact head metadata and expected
  namespace count changes;
- independent encoded/typed expected values for acknowledgement comparison;
- transfer count and the acknowledged journal/link/layout state needed for
  publication. No mutable payload may alias live World state.

Use `prepare_cold_save(session) -> ColdSavePlan | None` in the new module.
The caller owns the preparing guard. Preparation does no persistent writes and
does not advance D, remove chunks, clear dirty state or replace Event objects.
Identity refresh may reduce the pending links to their final state; that work
must remain retryable and must not become a committed baseline on failure.

Reuse `prepare_sealed_append` with a bounded view of the leading pending chunks.
Its expected generation must equal G, and its before descriptor must equal the
captured descriptor, including last year. Never rebase a stale session.
Do not call it inside another P1 read transaction.

Compose ONE action per (namespace, typed key):

| Event interval/action | Final transaction action |
| --- | --- |
| i < D | no world.events action |
| D <= i < D1 and i < N0 | delete its existing suffix row |
| D <= i < D1 and i >= N0 | omit suffix upsert AND deletion; segment alone stores it |
| D1 <= i < N | upsert only new/dirty rows, including changed sealed flags |
| unchanged suffix row outside transfer | no write |

Envelope ordinal and key remain absolute i; Event ID remains i+1.
No suffix row may coexist with its newly committed segment. At successful
reopen, world.events rows are EXACTLY [D1,N), sealed segments EXACTLY [0,D1).
Deletion membership follows the captured contiguous baseline, not an O(H)
per-event presence map or a query for every new Event.

The same transaction contains affected non-event records/deletions, final P2C
link upserts/deletions, necessary collections/v1 layout, P3A descriptor change,
session-tail/v1=(1,D1,F,N,last_year), session-commit/v1=(1,G+1,token), new segments,
and head metadata/counters. Preserve complete namespace inventory, including
empty cold and current-link namespaces. No identity-delta namespace.

A q=0 save with other changes still writes the tail/commit records. A transfer
with no World edits still commits once. A true no-op has no dirty/deleted/layout/
current-link work and q=0: check session/store/generation validity, then return G
with zero writes/deletes and no fresh commit token. Never secretly drain a
backlog in multiple commits.

## 3. Identity and serialization

Keep storage dirtiness separate from mutable identity ownership.
`_owner_value` deliberately returns None for sealed LOG occurrences; it is
NOT the event-value serializer. Serialize necessary suffix rows from their
absolute EventLog positions using the storage path, without re-registering
their identity. Coalesce transfer omissions before decoding dirty event rows
so selected events are not redundantly serialized as individual records.

Refresh only affected current owners. Reuse P2C final-state link coalescing and
the accepted sealing retirement. New/replaced/shared payloads sealed before
their first save must preserve current non-log aliases while historical values
remain frozen copies. Tail paths retain absolute indices as D advances.

Do not retain transferred event IDs in baseline ordinals, dirty journals,
occurrence indexes, memo maps or save plans after acknowledgement. The plan is
temporary; release it on successful publication or proven non-publication.
Existing total World structures such as event_ids are outside this event-backend
memory claim.

Keep existing codec support boundaries. In particular, do not invent a persisted
whole-EventLog alias codec or encode a disk reader as a nested payload; unsupported
payload shapes must fail before commit without traversing the prefix.

## 4. Publication and checked acknowledgement

Use `save_cold(session) -> int`, called only from the cold branch of
IncrementalWorldSession.save. It prepares, then calls
`store.commit(G, changes, new_segments, metadata)` exactly once.

After a normal successful return, capture the successor's checked head,
commit/tail/prefix metadata and replacement reader in ONE short read transaction.
Require G+1 and this plan's token/boundaries. Construct the reader using
SealedEventPrefix.from_active_read_transaction. End that transaction before
runtime adoption. If another writer already advanced further, mark stale;
never install its prefix onto this World.

After an ambiguous commit exception, use
`resolve_cold_save(session) -> int` / public `resolve_save()` with the retained
plan. In ONE read snapshot:

- At G: check the captured old head/descriptors/token still match. Non-publication
  is proved; return active at G with all unsaved changes/chunks intact. Release
  prepared encodings if desired; a subsequent save may prepare a new token.
- At G+1 with this token: require exact expected checked metadata, parent G,
  tail/prefix descriptors and namespace counts. Checked-read all planned changed
  records; verify deletions are absent. Check every new segment through
  read_segment_checked, including namespace/ordinal/count/first+last ID and typed
  payload equality. Never compare only year/counts, Python equality or cache hits.
  Capture the replacement reader in that same snapshot, then finalize once.
- Different/later generation or a different token: conflict, mark stale.
- Unreadable/corrupt/mismatched publication evidence: do not finalize; remain
  recovery-required (or stale for an established competing head), raise clearly.

A matching token alone is insufficient if the planned record/segment evidence
is wrong. An old expected generation alone is insufficient if its checked
baseline descriptors have changed. No raw SQL from session code; use checked P1
APIs. A missing accessor may be added narrowly to P1 with its own tests.

After either proven normal success or matching resolution, publish via a
shared `publish_cold_save(session, plan, prefix) -> int` helper.
Use accepted EventLog._adopt_committed_prefix, preserving the SAME log and
untransferred tail objects. It checks transferred values via checked new-segment
reads before trimming. Preserve its typed equality and non-regression checks.
No old cold payload read is allowed.

Install new descriptors/counters/current-link baseline and clear only this
plan's acknowledged journals. Close only the old internal reader after the
replacement is installed. Caller-created readers retain their captured prefix
until their store closes. Do not rebind or reconstruct the World.

Prevalidate post-adoption bookkeeping before destructive changes. Publication
must be resumable/idempotent if a failure occurs after commit or between runtime
publication phases: retained phase state distinguishes adoption already done
from adoption still pending. Never transfer the same chunk twice, increment
generation twice, or clear pending edits prematurely. A publication failure
blocks continuation until resolve succeeds or the session closes.

Normal publication may reread its q NEW segments for adoption; ambiguous
resolution may read q for evidence plus q for adoption. Report these separately
and keep <=2q new-segment reads per successful resolution attempt, zero old
segment payload reads. Do not weaken checked adoption just to report fewer reads.

## 5. State machine and fail-before-mutation guards

States: active, preparing, recovery-required, stale, closed. Keep legacy state
semantics compatible. This is synchronous single-owner/non-reentrant operation;
thread-safe concurrent World mutation is not a new feature.

- Active save begins only at a completed simulation step with an open store.
- Preparation/encoding failure before any commit attempt returns active with
  edits intact. A detected generation conflict marks stale.
- On commit exception, attempt ONE checked resolution. If old state is proved,
  leave active and re-raise the original save error. If this successor is proved,
  finish and return G+1. If outcome is unreadable, retain plan and require recovery.
- resolve_save never commits or reruns simulation. Active/no-plan returns G after
  availability checks. Stale raises conflict; closed raises a closed error.
- close remains idempotent, performs no save/resolution, and releases owned
  resources and bindings in every state. A new open recovers durable authority.

Guard before mutation, not in a trailing dirty-mark callback. Cover tracked
container insertion/deletion/update paths, owned dataclass assignment, Event
seal/append/seal_before, World.emit BEFORE next_event changes, and
Simulation.__init__/step/run BEFORE normalization/year/RNG/gameplay changes.
A directly closed session.store must fail before those changes too.
A cold closed World must keep a lightweight runtime-only lifetime marker after
bindings are removed; no global binding may keep its entire World alive.
Loaded values remain inspectable after close, but simulation cannot continue.

The preparing guard blocks reentrant save, resolve, close or simulation/mutation
from test hooks. Use a narrow internal capability/context for the actual
planner/publication and close teardown, not a public guard-disable flag.
Track full step activity through the final sealing operation; reject save
inside a step or an active current-people scope before preparation. Do not rely
only on the current_people_scope block, which ends before engine sealing.

A recovery-required/stale session must reject supported mutations before any
value, alias, dirty journal, counter or year changes. Read-only inspection of
already loaded values is allowed; EventLog access must not expose a partially
published partition. Block public log traversal while runtime publication is
incomplete, while allowing the resolver's narrow internal access. No new broad
freeze/copy of the World is required. Python low-level bypasses such as explicit
object.__setattr__ or raw dict base methods are not supported mutation APIs.

## 6. Implementation tasks and tests

Each task: add red tests, implement only its contract, run its focused tests,
then commit with [skip ci]. Internal task commits may retain cold-save refusal
until composition/guards are ready; do not present an unsafe half-save as done.

### Task 1 — immutable preparation and authority partition

Files: persistence_cold_save.py, captured-session baselines in tracking/session;
test_persistence_cold_save.py.
Interfaces: ColdSavePlan and prepare_cold_save(session) above.

- [ ] Add tests for empty/no-op, q=0 dirty save plan, one chunk, four chunks,
  five pending chunks, and mixed persisted/new selected Events.
- [ ] Assert one action per typed key, correct delete/omit/upsert partition,
  untouched suffix no writes, exact types/frozen flags, and next_event=N+1.
- [ ] Test individual sealing and new/shared/replaced payload sealing before any
  save; keep surviving non-log current links and unchanged tail object identity.
- [ ] Implement bounded preparation, preserving dirty state and boundaries on
  invalid ID/year/frozen payload, encoding failure and stale descriptor.
- [ ] Run:
  PYTHONPATH=simulation python -m pytest -q simulation/tests/test_persistence_cold_save.py

### Task 2 — single commit and runtime publication

Files: new helper module, tracking cold dispatch, existing EventLog adoption;
same test file.
Interfaces: save_cold(session), publish_cold_save(session, plan, prefix).

- [ ] Prove one P1 commit publishes World edit + current-link edits + suffix
  changes + selected segments + all descriptors/head together.
- [ ] Reopen after each save; enumerate authority only in tests and assert exact
  [0,D1) / [D1,N) coverage with no duplicate or missing Event.
- [ ] Drain five pending chunks in 4 then 1, one generation each; third save is
  a write-free no-op. Verify remaining bytes/rows and boundary-year queries.
- [ ] Test an unrelated current-owner edit, tail-only edit, metadata-only change,
  deleted/reanchored alias, and same-year transfer boundary.
- [ ] Preserve independent readers and retained live Event/child references.
  Verify index pruning and successful plan reclamation.
- [ ] Run Task 1 command plus test_persistence_event_log.py and
  test_persistence_event_identity.py.

### Task 3 — recovery, guards and process death

Files: helpers/tracking plus narrow core/engine/EventLog guards;
test_persistence_cold_save_failures.py.
Interfaces: resolve_cold_save(session), public resolve_save and state gates.

- [ ] Inject during-writes and before-commit failures: reopened old state,
  unchanged live boundary/chunks, dirty/link edits retained; corrected retry
  produces exactly one complete new state.
- [ ] Inject after-commit lost acknowledgement: recover exact successor once,
  return its generation, then no-op without duplicate rows/events/segments.
- [ ] Make initial acknowledgement reads fail; prove blocked mutations (including
  delete/pop/clear, retained aliases, emit and an event-free step), then restore
  reads and resolve. Test both durable-old and durable-new outcomes.
- [ ] Inject failure before adoption and after adoption/before bookkeeping;
  resolve twice and prove idempotence, same log/tail objects and complete state.
- [ ] Use two sessions: stale loser cannot save over winner, including competing
  equal World values with another token and a head advanced by two generations.
- [ ] Corrupt/delete a newly committed segment, alter segment metadata, or alter
  a changed record during lost-ack resolution (including warmed cache).
  Checked resolution must fail without runtime trimming or a new commit.
- [ ] Subprocess writer death during writes/before commit and after commit/before
  adoption: reopen proves complete old/new World, links and event partition.
- [ ] Test direct store.close, session.close, constructor/emit/step/run guard
  timing, active-scope/reentrant calls, and cleanup from every state.
- [ ] Run:
  PYTHONPATH=simulation python -m pytest -q simulation/tests/test_persistence_cold_save_failures.py simulation/tests/test_persistence_session_open.py

### Task 4 — independent continuation and measured bounds

Files: test_persistence_cold_save_bounds.py and
simulation/PERSISTENCE_P3B_COLD_SAVE_VALIDATION.md.

- [ ] Build an independently initialized, never-bound control. Continue a cold
  live session through several short save/reopen cycles with real Simulation
  steps. Compare canonical digest, exact typed events, causes, frozen flags,
  ordering, counters, selected aliases and subsequent simulation.
  Explicit test-only digest passes are excluded from normal-save I/O measures.
- [ ] Use structural fixtures for 4/40/400 cold segments, with fixed current
  owners and fixed suffix. Measure no-op, local current edit, one-chunk transfer,
  and four-chunk transfer with a fifth pending. Zero OLD segment payload reads.
- [ ] Measure fixed local alias change at 100/300/1,000 unrelated groups:
  owner/link work and writes depend on affected owners, not unrelated groups.
- [ ] Report actual segment reads/writes, record upserts/deletes, payload bytes,
  retired/remaining suffix rows, pending bytes, event identity/memo entries,
  cache occupancy, and reproducible retained/peak event-backend allocation.
  Count preparation encodings and adoption temporaries separately from cache.
- [ ] Prove acknowledged transfer releases plan payloads/retired metadata;
  a short fixed sequence of structural append/seal/save batches must not retain
  O(H) event objects or bookkeeping. No long-running endurance simulation.
- [ ] Run new tests, affected persistence/EventLog/identity/lifecycle tests,
  then ONE full simulation/tests suite after focused checks pass. Record
  commands, exact SHA, counts, timings and measured tables; verify landed
  product/test blobs match that candidate.

## 7. Review focus and handoff gate

Review these five cases explicitly through the tasks above:

1. A selected chunk straddles N0: delete only persisted rows and never also
   upsert new selected events (Task 1/2).
2. A sealed-but-untransferred row needs serialization without mutable LOG
   ownership, including an individually sealed tail Event (Task 1/2).
3. Another writer wins with equal values: token/generation, not value coincidence,
   establishes acknowledgement (Task 3).
4. Disk commit succeeds but runtime adoption/bookkeeping fails halfway:
   resolution is idempotent and simulation remains blocked (Task 3).
5. A retained alias mutates while recovery is required, or store is directly
   closed: reject BEFORE mutation, not merely when marking dirty (Task 3).

Use the established isolated safe CI workflow; do not trigger the normal
millennium workflow or weaken gates. Do not repeatedly poll long tests:
provide the pending run ID/link and stop; the user will re-prompt when done.

Land only this slice on PR #14's branch with [skip ci]. Report exact head and
validation evidence, then stop for Astra review. Do not mark architect acceptance
yourself. Detach/export/checkpoint compatibility integration and final P3B
validation remain later work; Stage 0.5 is not ready to merge.
