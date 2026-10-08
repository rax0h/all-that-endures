# Stage 0.5 final architect review and bounded Sol closeout

## Decision: blocked; do not merge

Review date: 2026-10-08. Three reproduced architectural blockers remain.
The accepted P1/P2/P3 machinery is not reopened by this review. Do not restart
family migrations or replay every intermediate tranche.

Verified live PR #14 head: `a9a8e5811df48ef0da506ca72548bd0896aebf9d`.
Frozen candidate: `5dd5c71d7c52ef9f7dbbae0c64940b378711745a`.
Both have tree `026201bca2db2d16fa1cffe0583beba34f1e74b4`.
The integration head adds current main
`5cb2a9cc9832d8e23ce48dd5207cf31efd9680f2` as its second parent.
GitHub reports mergeable; the PR is still draft and unmerged. Mergeability is
not architectural acceptance.

Review scope: delta from `9fda3ff138b44824cd7b29b3b95d6c69733195e8`
to the frozen candidate, with selective inspection of current shared machinery.
All local `simulation/ate_sim/*.py` used for the probes were checked against the
frozen Git tree (accounting for fetch-added terminal newlines).

## R1 — HIGH: clean eviction retains historical payloads and sidecars

At the frozen candidate, `persistence_lazy.py:2942` caches an encoded baseline
payload on each people load. `_evict_clean` (2996) and
`_finish_simulation_step` (3012) remove the resident dict record but leave its
baseline payload and associated metadata behind. `accept_save` does not prune
all previously read clean records. In `persistence_lazy_identity.py:127`, weak
object cleanup removes the object maps but not occurrence indexes. The people
binding path registers occurrences for these loads.

Short reproduction: build independent `people_world(n)` stores, cold-bootstrap,
convert to lazy, open, read each person once without edits, discard loop
references and collect garbage. No historical aliases are retained by the caller.

| People read | Resident people | Dirty | Baseline payloads | Encoded baseline bytes | Presence / incarnation / occurrence entries |
| --- | --- | --- | --- | --- | --- |
| 300 | 256 | 0 | 300 | 187,084 | 300 each |
| 900 | 256 | 0 | 900 | 561,484 | 900 each |

This is historical retained memory outside the advertised resident-record cap.
Zero-decode open and a 256-object LRU do not establish bounded session memory.

Bounded repair:

- Repair shared clean eviction and runtime identity metadata lifetime, including
  family overrides using the same pattern. Drop/reload clean baselines safely;
  do not merely hide the counters or clear metadata required by live aliases.
- Preserve dirty owners, externally retained top-level and nested aliases,
  cross-lazy/eager sharing, incarnation separation and reactivation routing.
  Runtime pruning must not delete persisted current-link authority.
- Check baseline presence/ordinal/incarnation maps, negative membership entries,
  occurrence reverse indexes and query caches, not only encoded payloads.
- Regress at 1k/10k history with a fixed active/dirty/externally-held set:
  traversal, eviction, GC, repeated traversal, membership misses, no-op save,
  actual save, and explicit digest/archive followed by GC. Measure retained
  bytes and sidecar counts after each boundary, not just record count.
- Retain top-level and nested aliases through eviction, then mutate/save/reopen;
  prove exact sharing and values, including cross-owner dirty routing. Explicit
  caller retention and unsaved dirty work may account for additional memory;
  previously visited, unheld, clean history may not.

## R2 — HIGH: public lazy digest/archive operations bypass lifecycle guards

`_LazyLifetime.begin_operation` in `persistence_lazy.py:9179` checks session
state but never calls `_begin_lifecycle_operation` or sets its guard.
`end_operation` is also a no-op with respect to that guard. `World.digest`
and archive export use these marker methods, so the real session preflight
and mutation exclusion are bypassed. `LazyWorldSession.close` (15505) also
does not check an active lifecycle operation or simulation step.

Short reproduction: on a 300-person lazy World, retain a person and temporarily
replace `core._digest_world_unchecked` with a callback that changes that person's
wealth and returns a sentinel. `world.digest()` returns the sentinel and wealth
changes. Inside `world.current_people_scope()`, the same public digest executes
the callback instead of rejecting before work. This violates the accepted
adversarial lifecycle contract; deterministic runs do not exercise the guard.

Bounded repair:

- Wire the lazy lifetime marker into the real session operation guard; preserve
  finally-based release on success and exceptions. Reuse the accepted P3B
  operation semantics rather than inventing a second guard policy.
- Exercise public digest and archive, including supplied-digest archive,
  scope/step rejection before callbacks, nested operations, save/resolve/detach/
  close attempts, lazy and eager mutation callbacks, and directly closed-store
  preflight. Internal archive digest must not cause false public reentrancy.
- Parameterize/reuse P3B lifecycle regression cases for the lazy backend.
  Assert rejected operations perform no mutation/publication and valid later
  operations still work. Include resource/pin cleanup on exceptional paths.

## R3 — HIGH: eager household membership is an unbounded history

`open_lazy_world_session` (`persistence_lazy.py:15553` onward) still restores
`world.households` eagerly, including each `Household.members` list.
`engine.py:111` appends births to an existing household's members. There is no
historical-member cap/removal corresponding to the claimed fixed eager bound.
A fixed number of households does not bound their nested lifetime payloads.

Short reproduction: one household, eight active people, all other people
inactive, and the household member list containing all historical person IDs.

| Historical members | Eager member IDs after open | Decoded lazy people | Open bytes |
| --- | --- | --- | --- |
| 100 | 100 | 0 | 19,847 |
| 1,000 | 1,000 | 0 | 45,052 |

Bounded repair:

- Give household membership a bounded storage/access boundary, reusing existing
  indexed/segmented sequence mechanisms where suitable. Making the outer
  household table lazy alone does not bound one household's growing payload.
- Preserve exact ordered mutable sequence semantics, duplicates where allowed,
  aliases, digest/checkpoint representation, and atomic owner/index publication.
  Do not delete historical IDs, cap history, or change simulation behavior.
- At fixed household/active-population count, compare 1k/10k historical members:
  ordinary open, current-household gameplay access, one birth/append, save,
  reopen and short independent continuation. Normal append must not rewrite
  the whole historical list. Explicit whole-list operations may do work
  proportional to the requested operation, with that cost documented.
- Test list mutations and retained aliases, failed commit, stale writer and
  lost acknowledgement across the new boundary. Preserve order and identity.
- Correct the residual inventory by inspecting canonical nested fields, not
  only top-level family counts. Classify each remaining eager field by an
  enforced bound or a demonstrated fixed size. Do not claim completeness from
  fixtures that do not grow that field. `agency.actions` has a 50,000-record
  cap; that does not establish a cap for unrelated nested histories.

## Evidence judgment and release-artifact gap

The completed evidence is useful and is not discarded:

- Run `37675455841`, job `112977670264`: **62 passed in 65.27s**.
  Helper head `7954722357739a7fdff1a836fb75157c2b5f5948` differs from the
  frozen candidate only by its targeted workflow file.
- Run `37679777350`, job `112992483949`: seed 843000; years
  100/250/500/1,000 all report `matches_control True`, with save/reopen/digest
  at each checkpoint and final `PASSED True`. Helper head
  `4352c9acbfe381075370b2b8e73c0413bee7def6` differs only by the endurance
  workflow. Final restored digest:
  `004ebc6ef7a62e39f867d7a3f96ccf9e88f1c7362fe73fe78a1e8dfb29d02725`.
- The owner reports the preceding full suite as 848 passed / one obsolete
  ActionRecord-frozen assertion. That particular full-suite job was not
  independently re-fetched in this review. The final contract correction and
  targeted job were inspected; mutable ActionRecord strength is accepted P2B
  behavior, not a reason to change production behavior to satisfy the old test.

Architectural judgment: a literal final all-green rerun is **not required solely
for that localized test-contract correction**. Accumulated full-suite, affected,
final targeted and independent-control evidence is sufficient for that evidence
boundary. It cannot override the three new reproduced defects above.

Separately, durable retention of the late restore fixture is not established.
The endurance workflow has no artifact-upload step and its run artifacts API
returned zero artifacts. Its locally verified SQLite backup was:

- `stage-0-5-final-endurance/p5-long-restore.sqlite`, year 1,000, generation 6;
- 5,124,976,640 bytes;
- SHA-256 `b775264dce1a202fdddfba4fa696455192906866bd9912673c9d26abcc797d63`;
- rules ID `stage-0.5-p5-long-v1`, schema `ate-world-p2a/1`.

A runner path and a logged checksum are not a retained World. First locate any
existing separately retained copy; verify its downloaded hash, provenance,
restore digest and a short independent continuation. Do not claim no copy can
exist elsewhere. If none exists, document the missing release deliverable and
prepare a scoped capture/upload proposal with capacity and retention for the
actual multi-GB file. Do not launch a replacement long run without owner
authorization. This gap does not invalidate the completed deterministic run.

## Executable Sol assignment and stop conditions

1. Verify live PR head, preserve concurrent work, and read this report plus the
   accepted execution handoff. Do not replay the PR history. Reproduce R1/R2/R3
   with failing focused tests before product changes.
2. Fix R1 and R2 in separate bounded commits, then R3 and its truthful residual
   inventory. Shared machinery fixes require affected family/identity matrices,
   not mechanically rewriting every adapter. Preserve all accepted semantics.
3. Run the new regressions and affected persistence/identity/lifecycle tests,
   the corrected ActionRecord compatibility tests, and the existing P5 short
   independent eager/lazy/restored continuation harness. Record exact commands,
   heads, results, measured bytes/reads/writes and test-to-change coverage.
4. Search for the durable late fixture and resolve/document the artifact gap.
   Consolidate current evidence in P4/release validation docs; their previous
   summaries stop before the final jobs. Update the stale PR summary when the
   evidence and actual candidate are coherent; do not mark it accepted yet.
5. A full-suite rerun is justified only by a concrete uncovered impact of these
   product repairs, not by ritual or the old test correction. State that impact
   and choose the gate once. Do not rerun the millennium for bookkeeping.
   If a long job is needed, hand off its command/run link and stop; no polling.
6. Deliver a frozen repair head, regression evidence, residual inventory and
   artifact status for a narrow review of these closures. Stage 0.5 remains
   blocked until all three defects and the required retention deliverable are
   resolved. Do not self-assert that old passing runs validated new code.

No Stage 1, balance/magic changes, new features, unrelated cleanup, checkpoint
default replacement, newly launched endurance run, or PR merge is authorized.
This review adds documentation only; it does not implement the repairs.
