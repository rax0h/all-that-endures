# P3B cold capture acceptance-gate implementation plan

Status: completed and accepted at `c5d827fe` on 2026-10-04 UTC. See
`PERSISTENCE_P3B_COLD_CAPTURE_REVIEW.md`. This plan is historical; the next
authorized assignment is `PERSISTENCE_P3B_COLD_BOOTSTRAP.md`.

> **For agentic workers:** Use superpowers:executing-plans to implement this
> bounded plan task-by-task. This is the next manual Sol handoff, not authority
> to implement later P3B slices or dispatch a large implementation team.

**Goal:** finish the missing evidence for the existing cold capture contract.

**Architecture:** keep `_capture_cold_world(store)` and its caller-owned read
transaction/borrowed reader unchanged. Exercise persisted records through real
P1 commits and checked reads; fix only defects demonstrated by those tests.

**Tech stack:** existing Python 3.12, pytest, SQLite and accepted persistence code.

**Spec:** `PERSISTENCE_P3B_COLD_CAPTURE.md`; review findings are in
`PERSISTENCE_P3B_COLD_CAPTURE_REVIEW.md`. The parent `PERSISTENCE_P3B.md` remains
the architectural authority, not permission to implement all its remaining work.

## Global constraints and exact scope

Verify PR #14's live head on `sim/stage-0-5-stabilization` before editing.
Start from the review/fix commit containing this plan. It already fixes six
typed-metadata regression cases; preserve those tests and do not redo the fix.

Primary files: `simulation/tests/test_persistence_cold_capture.py` and
`simulation/PERSISTENCE_P3B_COLD_CAPTURE_VALIDATION.md`. A separate test utility
is allowed if needed. Product changes are permitted only for newly demonstrated
violations of the existing capture spec, in `persistence_session.py` and narrow
shared adapter/head-accessor helpers. No EventLog/P3A/identity redesign.

No public session, binding, save/recovery, cold writer/conversion, engine guard,
detach, checkpoint/export integration or default checkpoint replacement.
No millennium/endurance, balance/magic changes, Stage 1, unrelated work,
workflow changes or PR merge. Keep `[skip ci]` on landing commits. GitHub
authorization is standing. This is a tests-first acceptance gate, not a new
architecture tranche.

## Review focus

1. Valid-checksum but semantically malformed records must fail closed.
2. Independently decoded non-event values and event values must remain exact.
3. Forbidden historical identity paths must fail before any cold I/O.
4. Capture failure must release its reader without taking the caller's store
   or transaction; successful capture must remain fixed to its generation.
5. Larger disk history must not add SQL scans, pending decodes or retained
   decoded Events. Printed cache metrics alone do not prove these properties.

## Task 1 — complete the capture validation matrix

**Files:** `simulation/tests/test_persistence_cold_capture.py`; product fixes only
under the narrow allowance above.

**Interface:** consume `_capture_cold_world(store)` inside a real
`TransactionalStore.read_transaction()`. Produce table-driven regression tests;
no new public API or production fixture writer.

- [ ] Extend the test-only fixture/mutation utilities. Keep expectations
  independent of capture. When damaging an otherwise valid store through P1,
  also advance `session-commit/v1` correctly so an unrelated generation mismatch
  cannot mask the intended failure. Use checksum damage only in checksum tests.
- [ ] Add `test_cold_capture_rejects_malformed_suffix` cases: missing/extra row,
  below-D row, boolean key, wrong/boolean envelope ordinal, wrong/boolean ID,
  non-integer year, decreasing suffix years and first suffix year below prefix
  last year. Exercise numeric ordering with at least twelve suffix positions.
- [ ] Add `test_cold_capture_rejects_invalid_sealing`: unsealed pending Event,
  sealed Event containing mutable data, malformed sealed flag, including an
  individually sealed tail Event. Where WorldCodec already rejects an invalid
  flag, show that fail-closed boundary explicitly; do not pretend capture ran.
- [ ] Add `test_cold_capture_rejects_descriptor_and_layout_damage`: missing empty
  prefix descriptor; missing/extra descriptor; invalid D/F/N types/order/chunk
  alignment; last-year mismatch; invalid token/version/generation; prefix/head
  segment count disagreement; suffix/head count disagreement; unexpected record
  or segment namespace kinds; malformed effective collections overlay. Preserve
  the existing bool/float layout and typed head-metadata regressions, and exercise
  the same event-description validation through `collections/v1`.
- [ ] Add `test_cold_capture_rejects_wrong_modes`: legacy/current non-cold input,
  unknown event/identity mode, mixed manifest keys, unknown/missing roots and
  identity-delta namespace authority. Assert conversion-required behavior for
  supported non-cold input and specific format/integrity failures elsewhere.
- [ ] Add eager suffix/current-record checksum failures and real World/head
  counter disagreement, distinct from the existing post-open head checksum test.
- [ ] Run the new cases. Tests of already implemented behavior should pass;
  any discovered defect must have a reproducible failing test before a minimal
  fix. Do not broaden generic P1's metadata contract with World-specific rules.
- [ ] Run the focused capture tests again. Commit the coherent change with
  `[skip ci]`; record any new product correction and its red/green result.

## Task 2 — prove exact values, identity and snapshot ownership

**Files:** the same test file/optional test helper. Interfaces remain unchanged.

- [ ] Strengthen `test_capture_partition_shapes_and_exact_world`, or add a
  separate comprehensive fixture: populate non-event roots with representative
  records, nested values, nontrivial insertion/stable-ordinal order and current
  aliases. Compare every declared root field to an independent source/oracle,
  not just seed/year/next_event. Reuse existing test fixtures where suitable;
  synthetic events avoid any need for a long simulation.
- [ ] Compare exact Event payloads/IDs/order/years/actors/causes/location and
  sealed-flag presence/value across empty, prefix-only, tail-only, mixed and
  >4 pending-chunk shapes. Include equal-year boundaries, individually sealed
  tail Events and special typed values where supported. Use typed encoding for
  value comparison rather than Python equality where bool/int or float bits
  matter. Keep these deliberate full-value comparisons OUTSIDE measured capture.
- [ ] Parameterize the existing forbidden-link test for disk prefix, pending
  history and individually sealed tail, in both target/owner positions where
  valid setup permits. Preserve the healthy tail parent/descendant alias case.
  Assert a specific failure category and instrument zero segment reads; replace
  `pytest.raises(Exception)` and the unasserted zero-read comment.
- [ ] Prove failure after reader creation closes that reader; outer transaction
  remains active and usable, store stays open. Prove successful caller exit
  leaves the reader usable; explicit reader close and store close give accepted
  EventLog failure behavior. Do not add a World pre-step guard in this slice.
- [ ] Add a pinned-generation scenario using two connections and real P1
  publication. Respect rollback-journal locking: a competing writer may have to
  wait or retry after the reader exits. All capture components must come from
  one generation; after a later publication the old capture keeps its original
  prefix descriptor/length. Detect nested transactions/hidden commits without
  changing P1 transaction semantics.
- [ ] Verify legacy `read_snapshot`/binding APIs still reject cold input and
  supported non-cold paths retain their existing behavior.
- [ ] Run focused tests, correct only demonstrated defects and commit with
  `[skip ci]`.

## Task 3 — turn reported bounds into enforced evidence

**Files:** capture tests and `PERSISTENCE_P3B_COLD_CAPTURE_VALIDATION.md`.

- [ ] Keep real 4/40/400-segment fixtures with identical current graph and fixed
  pending/tail cardinalities. Release fixture suffix Events/source Worlds before
  measurement; the current fixture dictionary contains an expanded `suffix` and
  must not remain a retention root. Keep only scalar expected counts.
- [ ] Measure each capture and assert cross-size equality of checked record-read
  counts, projected identity groups/paths and retained tail/pending/index
  cardinalities. Allow byte differences from absolute index/ID/descriptor digit
  growth; document the bound/observed values rather than demanding equal bytes.
- [ ] Instrument SQL (trace/authorizer) during capture to fail on access to the
  `segments` table, including header/count enumeration. Guard cold traversal and
  pending-chunk decoding during capture, not only final cache occupancy. Remove
  those guards for the subsequent one-segment point-read/cache test.
- [ ] Prove decoded pending Events are not retained by the returned capture,
  using weak references/collection or an equivalent independently observed
  retention check. Assert the bounded retained state; do not claim O(1) total
  World memory or bound arbitrary unsaved backlog. Report current graph,
  compressed pending bytes/index entries, mutable tail and cold cache separately.
- [ ] Make cold checksum corruption deterministic: replacing one hex character
  with '0' can accidentally leave a valid checksum unchanged. Also test missing
  unread segment. Capture remains lazy; checked point access and explicit
  `verify_full()` must fail. Include a healthy explicit verification control.
- [ ] Run focused capture + accepted P3B tests, then the affected persistence
  tests, then ONE full `simulation/tests` suite on stable final code:

```sh
PYTHONPATH=.:simulation python -m pytest -q -s \
  simulation/tests/test_persistence_cold_capture.py \
  simulation/tests/test_persistence_cold_identity_restore.py \
  simulation/tests/test_persistence_event_identity.py \
  simulation/tests/test_persistence_event_log.py
PYTHONPATH=.:simulation python -m pytest -q \
  simulation/tests/test_incremental_store.py simulation/tests/test_persistence*.py \
  simulation/tests/test_cold_history.py simulation/tests/test_event_year_queries.py \
  simulation/tests/test_canonical_digest.py simulation/tests/test_history_archive.py
PYTHONPATH=.:simulation python -m pytest -q simulation/tests
```

- [ ] Update validation with exact commands/results, tested SHA, bounds, ownership
  and corruption evidence, and honest limitations. Map requirements 1-7 of the
  capture spec to test names. If using isolated CI, prove product/test blob equality
  on landing; do not land a temporary workflow or run default millennium CI.
- [ ] Commit to the existing PR branch with `[skip ci]` and stop for review.
  Do not claim complete P3B or start session/save integration automatically.
