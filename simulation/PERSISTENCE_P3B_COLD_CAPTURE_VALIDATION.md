# P3B cold World capture — completed follow-up validation

Status: bounded acceptance evidence for
`PERSISTENCE_P3B_COLD_CAPTURE_FOLLOWUP.md`, 2026-10-04 UTC
(2026-10-03 America/Chicago).

Architect review/fix baseline:
`af85515f71ae54860b15fade27861b3dcb0330e5`.

Final fully tested follow-up candidate:
`f87d18c23a78f39a635b9b91e06db964b5bd84a9`.

While the final candidate was running, an earlier evidence-only landing
(`4fa8e02a34218063d38446ae249d7c5388ea427b`) reached PR #14. That commit changed
only this validation document and the cold-capture test file; no product Python
blob changed from the architect-reviewed baseline. The final landing supersedes
those two evidence files with the stricter tested candidate described here.

The six typed-metadata regressions fixed by the architect review remain present
and green. The expanded follow-up demonstrated **no additional production
defect**, so no product code is changed by this follow-up.

## Final stable test gates

Isolated candidate workflow run: `37178295840`  
Job: `111365447482`

| Gate | Actual result |
| --- | --- |
| focused cold capture + accepted P3B identity/EventLog | **141 passed in 74.44s** |
| affected persistence/EventLog | **329 passed in 178.52s** |
| full `simulation/tests` | **496 passed in 313.43s** |

Commands:

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

The first expanded test candidate exposed only a test-fixture mistake
(an invalid enum member), not a persistence defect. After correcting that fixture,
the final hardening added exact typed comparisons across every required partition
shape, explicit empty-prefix-descriptor evidence, and a real blocked-writer/retry
generation test. The stable candidate above is the one used for landing.

## 1. Exact complete World and Event restoration

Evidence:

- `test_capture_partition_shapes_and_exact_world`
- `test_capture_restores_all_non_event_root_values_and_order`
- `test_capture_restores_exact_event_values_flags_and_special_types`

The partition test covers empty, prefix-only, tail-only, mixed and more-than-four
pending-chunk forms. After the measured lazy-capture boundary, every Event is
compared through `WorldCodec` typed encoding, including ID, year, payload,
ordering and sealed-flag presence/value.

A separate configured World fixture compares every declared non-state/non-event
root field to an independent source oracle through typed encoding and asserts
representative insertion order.

The special Event fixture covers actors, causes, location, layer, nested values,
individually sealed tail Events, equal-year boundaries, signed zero,
bool/int/float distinctions and a fixed NaN payload bit pattern.

## 2. Current identity and excluded historical identity

Evidence:

- `test_capture_restores_tail_parent_and_descendant_aliases`
- `test_forbidden_history_identity_paths_fail_before_cold_io`

Healthy current parent/descendant aliases restore across independently persisted
copies. Forbidden identity paths are exercised for immutable disk history,
resident pending sealed history and individually sealed tail history, in both
target and owner positions. They fail through the accepted cold identity format
boundary without any cold segment read or pending-history decode.

## 3. Malformed checked input fails closed

Evidence:

- `test_cold_capture_rejects_typed_metadata_mismatch`
- `test_cold_capture_rejects_malformed_suffix`
- `test_cold_capture_rejects_invalid_sealing`
- `test_world_codec_rejects_malformed_sealed_flag_before_capture`
- `test_cold_capture_rejects_descriptor_and_layout_damage`
- `test_cold_capture_rejects_wrong_modes`
- `test_cold_capture_eagerly_rejects_current_record_checksum_damage`
- `test_cold_capture_rejects_integer_world_head_counter_disagreement`
- `test_cold_capture_requires_published_empty_prefix_descriptor`
- `test_checked_head_detects_post_open_corruption`

Semantic damage is normally published through real P1 commits while advancing
`session-commit/v1`, so an unrelated generation mismatch cannot mask the
intended failure. Raw SQL is reserved for explicit checksum/head corruption or
missing-unread-segment tests.

The matrix includes missing/extra/below-D suffix rows; bool keys; wrong/bool
ordinals and IDs; non-integer/decreasing years; first suffix year before the
prefix boundary; unsealed pending Events; sealed mutable payloads; malformed
sealed-flag representation; individually sealed tail validation; missing/extra
descriptors including the required empty prefix descriptor; bool/float/order/
alignment partition damage; last-year mismatch; bad token/version/generation;
prefix/head and suffix/head count disagreement; record-vs-segment namespace
misuse; malformed effective overlays; supported non-cold conversion-required
input; unknown/mixed modes; missing/unknown roots; identity-delta authority;
eager suffix/current checksum damage; integer World/head counter disagreement;
and post-open head checksum corruption.

## 4. Caller transaction, generation and lifetime

Evidence:

- `test_capture_requires_caller_owned_read_transaction`
- `test_capture_failure_after_reader_allocation_closes_reader_only`
- `test_successful_capture_reader_and_store_lifetime_boundaries`
- `test_capture_generation_is_fixed_across_later_publication`

Capture does not open, commit or close the caller's transaction. A failure after
reader allocation closes only the reader; the outer transaction and borrowed
store remain usable.

Successful capture remains usable after the caller exits the read transaction
while the store is open. Explicit reader close and store close retain the
accepted EventLog failure behavior.

The generation test uses two real P1 connections. With rollback-journal mode and
the writer's busy timeout set to zero, the second writer cannot publish while the
capture read snapshot is pinned; P1 rolls back the failed attempt and its
generation remains unchanged. After the caller releases the read transaction,
the same publication succeeds. The old capture remains fixed to its original
generation/prefix while a fresh capture sees the new generation.

## 5. Enforced 4 / 40 / 400 read and retention bounds

Evidence:

- `test_capture_bounds_are_enforced_across_4_40_400_segments`
- `test_capture_releases_decoded_pending_events_but_retains_tail`

Before measurement the test drops the fixture's expanded suffix reference and
forces collection. During capture:

- SQLite's authorizer denies **any read of the `segments` table**, including
  header/count enumeration;
- `EventLog._chunk` is replaced with a failing pending-decode guard;
- `SealedEventPrefix.__iter__` is replaced with a failing cold-history
  traversal guard.

All three real stores pass those guards.

| Disk segments | Checked payload reads | Checked payload bytes | Segment reads | Disk cache | Pending cache | Pending chunks | Pending bytes | Tail events | Year entries | Offset entries | Projected groups | Projected paths |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | **2,084** | 704,473 | **0** | **0** | **0** | **1** | 10,410 | **3** | **1** | **1** | **87** | **87** |
| 40 | **2,084** | 709,904 | **0** | **0** | **0** | **1** | 10,707 | **3** | **1** | **1** | **87** | **87** |
| 400 | **2,084** | 716,070 | **0** | **0** | **0** | **1** | 10,707 | **3** | **1** | **1** | **87** | **87** |

The test enforces equality across history sizes for record-read count,
segment/cache counts, pending chunk cardinality, mutable-tail cardinality,
year/offset index cardinality and projected identity groups/paths. Payload bytes
are recorded rather than required equal because absolute indices/IDs/descriptors
gain digits.

A separate weak-reference retention test observes expanded pending Events during
construction. After capture and collection, the pending Event objects are no
longer retained while mutable tail Events remain live; compressed pending chunks
remain, with zero decoded pending-cache entries and zero cold-prefix cache
entries. This is a bound on retained cold history, not a claim of O(1) total
World memory or a bound on arbitrary unsaved resident backlog.

## 6. Lazy damage, point reads and explicit verification

Evidence:

- `test_lazy_capture_defers_unread_segment_damage_to_access_and_full_verify`
- `test_healthy_capture_explicit_full_verification_control`
- point-read/cache assertions in the 4/40/400 bound test.

Checksum damage deterministically changes a checksum digit. Missing unread
segment rows are tested independently. Both damaged stores still capture lazily
with zero cold segment reads, while subsequent checked point access and
`verify_full()` fail.

A healthy control starts with zero cold reads and successfully rereads all four
captured segments through `verify_full()`. The bound test proves the first cold
point access adds exactly one checked payload read and repeat access is served by
the accepted bounded cache. Current suffix/current-record checksum damage fails
eagerly during capture.

## 7. Legacy compatibility and accepted regression coverage

Evidence:

- `test_legacy_snapshot_and_binding_apis_reject_cold_but_noncold_still_work`
- affected gate: **329 passed**
- full suite: **496 passed**

Legacy detached reading and incremental binding reject cold input, while
ordinary non-cold read/bind paths remain usable. All accepted P2/P3A/P3B tests
included by the affected and full gates remain green.

## Exact landing identity

The final candidate's only repository changes relative to
`af85515f71ae54860b15fade27861b3dcb0330e5` are:

- `simulation/tests/test_persistence_cold_capture.py`;
- a temporary candidate-only workflow.

No product blob differs from the architect-reviewed baseline. The exact tested
test blob is:

`6d10e374865fd1a9613d3bc1e8d8b52dcbbc31fe`.

The PR landing uses that exact test blob and this validation document, and does
**not** land the candidate workflow. The concurrent earlier evidence commit
`4fa8e02a...` also changed only these evidence files, so superseding them does
not discard any product change.

## Remaining boundary

Cold capture remains an internal **unbound** World reconstruction helper. This
follow-up does not implement or prove public session ownership/binding, atomic
cold save publication, acknowledgement recovery, event-transfer save
integration, detach/close guards for a public session, conversion/checkpoint/
export integration, or independent resumed-simulation equivalence.

No millennium/endurance run, calibration, balance or magic-progression change,
Stage 1 work, normal checkpoint replacement, PR workflow change, unrelated work
or merge is part of this follow-up.
