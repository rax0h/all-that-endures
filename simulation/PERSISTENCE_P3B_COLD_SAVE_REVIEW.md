# P3B cold save — architect review and bounded corrections

**Status: changes required; atomic cold save/recovery is not yet accepted.**
Reviewed PR #14 head: `0bbc7976904cad46a081a13d4e119238f52d37e7`.
Branch: `sim/stage-0-5-stabilization`. Date: 2026-10-04.

P3A and every previously accepted P3B slice, including live open/bind/sealing/
close at `2819391`, remain accepted. Preserve the implementation beneath these
findings. Do not restart the cold-save architecture or begin the next tranche.

## Latest candidate review — this is the next assignment

Candidate branch: `sol/p3b-cold-save-review-fixes`.
Reviewed candidate: `cff9d586874af3c4a420e731178bbb7943432ad1`.
PR #14 still points to `0bbc7976904cad46a081a13d4e119238f52d37e7` before
this documentation commit; the candidate product fixes have NOT landed there.

Completed candidate workflow `37238194403`, job `111541431263`:
**9 targeted tests passed in 7.37 s**. This is not an affected/full-suite gate
for the corrected candidate.

Independent review against the candidate: **4 passed, 1 failed in 1.52 s**.

- R1's original reproduction now passes: 100/300/1,000 unrelated groups each
  cause **0 persisted-key iterations, 3 membership probes, 3 record actions**.
  The touched-key implementation is correct for the reviewed bounded-count
  correction. Preserve it; do not redo it.
- R2's original post-journal/pre-baseline reproduction now passes.
- One closely related identity-deletion case below still blocks acceptance.
- The original required retained/peak allocation evidence remains outstanding.

### R2.1 — pending deletion is confused with already-applied deletion

In `_validate_acknowledged_journal(..., allow_applied=True)`, the code uses
`_pending_identity_current.get(target, _MISSING)`. But `_MISSING` is BOTH
the stored pending-deletion value and the default for an absent dictionary entry.

After entering the new bookkeeping phase, a failure before applying that
deletion leaves the target present with a deletion marker and the old committed
link still present. On retry the validator treats the target as absent/already
applied, requires the committed link to be gone, and raises:

`StoreIntegrityError: identity journal changed while cold save was guarded`

**Exact reproduction:** create a World whose wallet has `left` and `right`
pointing to the same `{"values": [1]}` object. Create/open its cold store;
assign `right = {"values": [2]}`, producing current-link deletions. Replace
`_apply_acknowledged_journal` with a one-shot raising helper and call save.
Assert the phase is bookkeeping and durable generation is G+1. Restore the real
helper; `resolve_save()` must return G+1 twice and reopen with distinct left/
right values. It currently fails on the first resolution.

This is a failure between bookkeeping phase selection and journal application,
not a manual alteration of the journal. Also cover a mixed batch interrupted
after an early identity action but before a later pending deletion.

**Required fix:** distinguish dictionary membership from the deletion marker
(or use a separate absence sentinel). If the target is still pending, validate
its pending action, including deletion, without requiring the committed action
to be finished. Only an actually absent pending entry may be checked as already
applied against committed identity state. Preserve initial strict validation,
foreign-token/corruption rejection and all mutation guards.

### Candidate completion instructions

Continue the existing candidate; preserve its working R1 correction and
bookkeeping phase. Add the R2.1 regression, correct the absence/deletion
distinction, and prove mixed insert/update/delete partial cleanup, repeated
resolution and a subsequent real save/reopen.

Complete the memory/allocation measurements and the affected/full validation
gate in the original assignment below. Do not claim the old 607-test candidate
validated the new source. Record exact new SHA/results and landed blob equality.

After validation, land only the corrected product/tests and validation
documentation on PR #14's branch, preserving this review and other documentation.
Do NOT land the candidate-only workflow. Use [skip ci]. Stop for architect review.
If long tests are pending, report their link and stop; the user will return.

## Original PR-head findings and required evidence

The remainder records the findings at `0bbc797`. R1 and the original R2 probe
are now corrected on the candidate as noted above; do not repeat completed work.
Their preservation tests, broader recovery cases and allocation evidence remain
the correction scope. The next product change is specifically R2.1.

## Evidence checked

The completed final workflow `37232510632`, job `111525013796`, tested
candidate `b46a77da020752c6e346e4ab17691f6b4aacf3b1`:

- affected persistence: **440 passed in 727.40 s**;
- full simulation suite: **607 passed in 974.21 s**.

All simulation Python blobs match the reviewed head. Local review Python files
also match the live tree, apart from a possible fetch-added terminal newline.

Four existing no-op/q=0/guard/uncertain-ack tests independently passed in 0.20 s.
Four added review cases failed in 1.31 s: three sizes of the R1 probe and the
R2 publication-phase probe. These are short deterministic structural fixtures.
No long test run was launched or waited on.

The green suite is valid evidence for its covered cases. It does not establish
the two missing guarantees below.

## R1 — count preparation scans unrelated persisted keys on every save

Location: `persistence_cold_save._expected_counts`.

The comprehension creating `presence` copies EVERY set in
`session._cold_persisted_keys` before processing the changed records. This
includes all unrelated current-link targets, current collection keys and
event_ids ordinals. A local wallet update therefore performs whole-population
work even though its I/O and changed-member counters appear constant.

The existing alias-scaling test measures record actions, I/O and
changed_member_work, none of which count these copies.

Independent measurement, with the existing shared-wallet shape and one nested
list append in wallet 0:

| Unrelated-group fixture size | Persisted keys iterated/copied | Final record actions |
| ---: | ---: | ---: |
| 100 | 331 | 3 |
| 300 | 931 | 3 |
| 1,000 | 3,031 | 3 |

Reproduce by wrapping each value in `_cold_persisted_keys` with a transparent
MutableSet proxy whose `__iter__` counts each yielded key, whose
`__contains__` counts membership probes, and whose add/discard/len delegate to
the original set. Open first, make the local edit, install the proxies, then
call prepare_cold_save. Assert zero iteration of unrelated key sets. All three
sizes currently fail; membership probes on the proxies remain zero because the
planner copies their contents first.

### Required correction

Compute count deltas from membership of only each final changed typed key in
the captured baseline, plus the <=4 selected segments. The action map already
rejects duplicate (namespace, typed key) actions, so there is no need to clone
every presence set to simulate sequential duplicate actions.

Reuse `_record_existed` or an equally narrow lookup. Event row existence remains
the arithmetic [D,N0) test; do not introduce an event-row key map. Updating the
fixed namespace-count dictionary is allowed. Do not substitute another global
set copy/scan, a full identity reconstruction or per-event cold reads.

Retain correct insert/update/delete counts, including absent deletes,
delete/reinsert reduced to final state, current-link insertion/removal and
a selected chunk straddling persisted N0. Checked successor counts must still
agree with P1. Update persisted membership only after confirmed publication.

### Required evidence

Add permanent tests that count actual key iteration and membership work during
ordinary save preparation and resolution/publication. For fixed local work,
iteration over unrelated key populations must be zero and membership work
bounded by changed record keys, independent of 100/300/1,000 unrelated groups.

Complete the memory evidence requested by the original assignment. The current
bounds tests report encoded plan bytes, caches and object counts, but contain
no retained/peak allocation measurement. Add a reproducible measurement (for
example tracemalloc started/reset after fixture creation and open) for save
preparation, publication and released-plan retention at fixed suffix/current
shape over 4/40/400 old segments. Report actual bytes and the method, including
selected-batch copies/evidence/adoption temporaries separately from reader cache.
Also measure the local-key fixture after the correction so the removed
whole-population allocation cannot hide behind flat I/O counts.
Do not count fixture construction as a save allocation or claim bounded total
World memory.

## R2 — interrupted journal cleanup cannot be resolved idempotently

Location: `publish_cold_save`, `_validate_acknowledged_journal`,
`_apply_acknowledged_journal`, `_apply_persisted_key_changes`.

Runtime publication records only "prepared" and "adopted". It then clears the
acknowledged journal BEFORE applying persisted-key baselines and finishing
generation/descriptor publication. If an exception occurs between these steps,
a later resolve rechecks that the plan's original dirty/deleted owners still
exist. They have already been cleared by this same successful publication, so
resolution raises:

`StoreIntegrityError: cold save dirty journal changed while publication was guarded`

The database contains the complete successor, but the live session remains
recovery-required and cannot finish through resolve_save. Closing/reopening
still recovers the durable state; that does not satisfy the specified
idempotent runtime-resolution contract.

### Exact short reproduction

1. Create/open an empty-history cold World with wallet 1 = {"values": [1]}.
2. Append 2 through its tracked list; record generation G.
3. Temporarily replace `_apply_persisted_key_changes` with a helper that raises
   StoreError. Call save and observe recovery-required.
4. Restore the original helper.
5. Assert `resolve_save() == G+1`, then repeat resolution and assert G+1.
   The first assertion currently fails with the journal error above.

This injection is between existing publication helpers, after adoption and
journal cleanup; it neither edits a private journal nor fabricates a corrupt
World. The original tests cover before_bookkeeping and after_adoption but miss
this later publication boundary.

### Required correction

Make publication progress explicit enough to resume after acknowledged journal
cleanup and each remaining bookkeeping phase. Prevalidate the plan's journal
against the live state before destructive publication work, then apply
acknowledged actions idempotently or retain bounded per-phase/per-action progress.
Do not require already-completed actions to look unperformed on retry.

Cover exceptions both BEFORE and AFTER an operation has taken effect: simply
moving the dirty clear to another fallible boundary is insufficient.
Do not suppress validation wholesale or treat arbitrary journal disagreement as
success. Preserve the invariant that unsupported mutations cannot occur while
the plan is pending. All additional preparation/progress data must be bounded
by the acknowledged plan, not a copy of all current owners/keys.

Maintain one durable generation, the same EventLog and untransferred tail
objects, exact event authority, correct current links and baselines, old-reader
cleanup, and release of plan payloads after success. Repeated resolution after
success is a no-op. A closed session must still release resources from every
intermediate phase.

### Required regressions

- The exact q=0 reproduction above, plus a q>0 transfer with a current-link
  change, selected persisted/new event rows and a remaining mutable tail.
- A wrapper that calls the real journal-apply helper and THEN raises once.
- Failure before and after persisted-key baseline updates, and before final
  generation/descriptor/old-reader cleanup completes.
- If a helper applies multiple acknowledged actions, inject after an early
  action so a partly applied batch is safe to retry.
- Remove the fault, resolve twice, then perform another real save and reopen.
  Check exact counts, row/segment partition, links, values and generation.
- During each unresolved phase, retained-alias mutation, emit, Simulation
  step/run and public partial-EventLog traversal remain blocked before changes.
- Recovery checks still reject corrupt changed records/new segments and foreign
  tokens; this correction must not bypass checked acknowledgement.

## Bounded Sol assignment and validation gate

Implement ONLY R1, R2 and their missing bounds evidence above.

Primary file: `simulation/ate_sim/persistence_cold_save.py`.
Tests: the existing three cold-save test files. Narrow session tracking changes
are allowed only where publication progress/state requires them.
Update `PERSISTENCE_P3B_COLD_SAVE_VALIDATION.md` with the actual corrected
candidate evidence and measurements. Preserve previous results as historical.

1. Add red permanent regressions for the review probes.
2. Fix the two bounded issues, retaining accepted P1/P2C/P3A/EventLog semantics.
3. Run focused cold-save, affected persistence/identity/EventLog/lifecycle tests.
4. Run one full simulation/tests suite after focused checks pass, using the
   established isolated safe workflow. Do not trigger millennium/endurance or
   weaken workflow gates.
5. Record exact candidate SHA, commands, pass counts, timings and measured
   key-work/allocation/I/O tables. Verify landed product/test bytes match it.
6. Commit to PR #14's branch with [skip ci], then stop for architect review.

Do not repeatedly poll long tests. If a run is pending, provide its run ID/link
and stop; the user will re-prompt when it finishes.

No detach/export expansion, default checkpoint replacement, P4, Stage 1,
balance/magic changes, millennium/endurance, unrelated work or merge.
Stage 0.5 remains decision B and is not ready to merge.

