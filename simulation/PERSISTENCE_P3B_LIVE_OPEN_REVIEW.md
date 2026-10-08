# P3B live cold open — architect review and bounded corrections

Status: **live open/bind/close and semantic sealing retirement accepted** at
`2819391359fa3e2e16f9c8e3151e99ce06d8a373`, 2026-10-04.

## Acceptance of the correction

The six original review failures are corrected. Retirement handles newly appended
Events, replaced children, individual sealing and tracked sets without stale LOG
ownership or memo retention. Append preflight rejects foreign bindings before
changing the destination log. Current non-log owners remain authoritative.

Completed CI workflow `37225707267`, job `111504795251`, at candidate
`b07146803f27a1ae33be58c448d068d37e651ae2` was independently checked:
297 focused passed in 188.93 s; 394 affected passed in 394.17 s;
561 full-suite passed in 577.05 s. All simulation Python blobs match the accepted
head. Independent review also ran the original six probes and Sol's 17 new cases:
**23 passed, 19 deselected in 25.49 s**. Local reviewed Python sources were checked
against the live tree (allowing only a fetch-added terminal newline).

No additional blocker was found in this correction scope. P3A and all earlier
accepted slices remain accepted. No long test run was started or polled in this
review. The next assignment is `PERSISTENCE_P3B_COLD_SAVE.md`; no detach/export
work, checkpoint-default replacement or merge is authorized by this acceptance.

## Historical review and correction assignment (completed)

The findings and assignment below describe the pre-correction state and are
retained as evidence. Their not-accepted status and cold-save block are superseded
by the acceptance above and the new cold-save assignment; do not repeat them.

Reviewed PR #14 head: `d3017a8394ceb8b47e7b8daa62cb527850ecca4a`.
Date: 2026-10-04. Branch: `sim/stage-0-5-stabilization`.

P3A and previously accepted P3B slices remain accepted. This review does not
restart persistence architecture. Cold save/recovery remains blocked pending
acceptance of this foundation and a separate bounded assignment.

## Evidence

The completed isolated CI workflow `37222438702`, job `111495335683`,
tested candidate `a5029ff7b5a60e7ab5cdfcdfe6914e17f74ec819`:

- focused: 182 passed in 87.27 s;
- affected: 377 passed in 361.33 s;
- full simulation suite: 544 passed in 485.85 s.

All simulation Python blobs match the reviewed head. These are valid completed
test results, but the suite misses the lifecycle cases below.

Independent review reran four existing sealing/mutable-tail/legacy-save cases:
4 passed, 15 deselected in 0.58 s. Six additional adversarial probes all failed
in 0.67 s, each at its stated behavior assertion. No long run was started.

## Blocking findings

### 1. Retirement depends on an out-of-date occurrence index

`_event_appended` binds the new Event and marks its owner dirty, but does not
immediately populate its occurrence-index rows. `_event_chunks_changed`
collects objects only from those rows and removes retired owners from the dirty
set before refresh. A full chunk appended and sealed without an intervening
identity refresh leaves its Events bound and retained.

Replacing an indexed Event's payload before sealing creates another gap:
the newly wrapped child can lose its LOG owner tag during freezing yet remain
retained by the session memo, because retirement only sees old indexed objects.

Required: sealing must retire the actual current mutable ownership graph and
any stale indexed occurrences for the retiring owners. It must work before or
after an identity refresh, including append, nested replacement and sharing.
Freezing may replace the graph, so cleanup cannot recover everything by walking
only the already-frozen Event afterward. Use the existing tracking machinery;
do not fix this with a whole-World scan, full-history walk or global memo sweep.

### 2. Individual sealing does not retire LOG identity

Calling `Event.seal()` on a bound tail Event leaves its LOG binding and
occurrence-index owner alive. Appending an already individually sealed Event
also registers it as a mutable LOG owner.

Required: a tail Event is mutable LOG identity only while unsealed. Individual
sealing must retire that authority immediately without moving F or D. Appending
a sealed Event must record the new event/layout as dirty for future persistence,
but must not grant it mutable LOG ownership. Preserve current non-log owners
and identity when the same object has surviving current-state occurrences.

All identity refresh paths must honor this boundary and must not resurrect a
retired LOG owner, including dirty event rows that still need future persistence.

### 3. Tracked sets bypass reverse memo registration

The set branch of `_bind_nested` writes `_memo[id(value)]` directly instead of
using `_remember_memo`. Thus `_drop_memo_if_unowned` cannot find and release it.
A set in a sealed, otherwise unreferenced payload remains retained after all
owners are removed.

Required: cover every memoized mutable type, including sets and newly replaced
children. Release unowned raw-source/wrapper pairs and empty global bindings,
while preserving genuinely shared current objects. Use weak references/GC tests
for reclamation, not only empty owner-set assertions.

### 4. Rejected cross-session append already mutates the EventLog

The installed append hook calls the original EventLog append before tracking
validates foreign ownership. Appending another live session's Event raises
`StoreError("cross-session ...")`, but the destination log already contains it
and its length has increased. The rejected operation changes authoritative state.

Required: preflight foreign Event bindings and foreign tracked descendants
before authoritative append or binding/dirty-state mutation. Preserve normal
EventLog ID/year checks, exception behavior and valid append semantics. Rejection
must leave both sessions' values, counts, year-query results, ownership,
aliases and dirty/identity state unchanged. Closing the destination afterward
must not disturb the source session. Do not introduce a broad transactional
mutation framework.

## Exact regression seeds

Use the existing `build_cold_path`, `event` and `RULES` helpers from
`test_persistence_session_open.py`; C is 2,048. Each session must close in a
`finally` block. These six cases reproduce failures at the reviewed head:

1. **Newly appended chunk:** open D=0, tail=0; append C Events, IDs 1..C,
   each with `data={"child": []}`; retain the first Event, its child and an
   Event weakref; call `seal_before(11)` without refreshing identity. With no
   non-log alias, assert `_binding(first) is None`, its child's LOG owner is
   absent, and the Event weakref dies after dropping caller references.
   The first binding assertion currently fails.
2. **Replaced child:** open D=0, tail=C; replace the first Event's data with
   `{"replacement": []}`; retain a weakref to the new tracked list; seal
   before year 11 without identity refresh; drop the caller's child reference
   and collect. The weakref currently remains live.
3. **Individual seal:** open D=0, tail=1; call the first Event's `seal()`.
   Assert it has no binding when there is no non-log owner, and that
   `("world.events", 0)` is absent from `owner_occurrences`.
   The binding assertion currently fails. D and F must stay zero.
4. **Tracked set:** open D=0, tail=C with first payload `{"items": {1, 2}}`;
   keep a weakref to the tracked set, seal before year 11, assert its owner
   set is empty, drop the caller reference and collect. The weakref currently
   remains live.
5. **Already sealed append:** open D=0, tail=0; append
   `event(1, sealed=True)`; assert no LOG binding. It currently gains one.
   The event must remain present, sealed, in order, and marked for persistence.
6. **Foreign append:** open independent left D=0/tail=0 and right D=0/tail=1
   stores; attempt `left.world.events.append(right.world.events[0])`.
   It raises cross-session StoreError, then `len(left.world.events) == 0`
   currently fails. Also test a fresh Event containing a foreign tracked child.

Extend these seeds to prove:

- no-refresh and already-refreshed retirement produce the same final current
  links; surviving non-log parent/child aliases reanchor correctly;
- an individually sealed tail Event later entering a full sealed chunk is
  retired idempotently; current non-log ownership remains usable;
- detached former payload mutation cannot dirty or re-register the retired
  LOG owner, and repeated refresh cannot resurrect it;
- invalid ID/year append rejects without partial tracking or source changes;
- cold segment payload reads remain zero for append/seal/retirement/close;
- per-owner retirement cost depends on retiring/touched owners and their graph,
  not 4/40/400 historical segments or 100/300/1,000 unrelated alias groups;
- repeated append/seal batches release retired Events and wrapper objects:
  identity/memo/global-binding retention does not grow with sealed history.

These are focused unit/structural fixtures, not endurance simulation.

## Bounded Sol assignment

Implement only the corrections above. Primary file:
`simulation/ate_sim/persistence_tracking.py`. Add focused regressions in
`simulation/tests/test_persistence_session_open.py` and affected tracking tests.
A minimal hook in `core.py` / `event_log.py` is allowed only if necessary to
observe the real sealing boundary safely; explain why, preserve unbound/legacy
semantics, and test it. Do not change sealing eligibility, event values, IDs,
years, causes, frozen representation, simulation rules or RNG behavior.

Preserve the accepted cold-capture/bootstrap implementation, P1 checked storage,
P2C current-link authority and P3A reader/storage. Preserve live-open generation
pinning, cleanup and no-history traversal. Cold `save()` must remain explicitly
blocked. No cold-save implementation, recovery API, detach, checkpoint default
replacement, P4, Stage 1, balance/magic changes, millennium/endurance, or PR merge.

Validation sequence:

1. Reproduce the six failures with permanent focused tests, then fix them.
2. Run the expanded live-open tests and affected EventLog/identity/tracking
   regressions, including legacy session save and independent bound/unbound
   continuation already required by the live-open specification.
3. Run the affected persistence set and one full unit/integration suite once
   the focused checks are green, using the established isolated safe workflow.
   Do not trigger a workflow that runs millennium/endurance. Do not weaken
   existing workflow gates.
4. Record exact candidate SHA, commands, counts, timings and measured bounds in
   `PERSISTENCE_P3B_LIVE_OPEN_VALIDATION.md`; preserve earlier evidence as
   historical. Verify landed product/test blobs equal the tested candidate.
5. Commit to PR #14's branch with `[skip ci]`, then stop for architect review.
   Do not mark this slice architect-accepted yourself.

Do not poll long-running tests repeatedly. When a long test run is pending,
give the user its run ID/link and stop; the user will re-prompt when it finishes.
The next architecture tranche remains atomic cold save/recovery after this
correction is accepted. Stage 0.5 is not ready to merge.
