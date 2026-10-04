# P3B cold World capture — completed acceptance-gate validation

Status: bounded follow-up evidence for
`PERSISTENCE_P3B_COLD_CAPTURE_FOLLOWUP.md`, 2026-10-04 UTC.

Accepted review/fix baseline:
`af85515f71ae54860b15fade27861b3dcb0330e5`.

Fully tested follow-up candidate:
`4707d008e36331593b815087f9583db7589a41c1`.

The candidate preserves the six typed-metadata regression fixes already landed
by the architect review. The expanded acceptance suite demonstrated **no
additional product defect**, so no product Python file changed in this follow-up.
The only tested repository content change is
`simulation/tests/test_persistence_cold_capture.py`. The pre-existing isolated
candidate workflow was reused unchanged and is not part of the PR landing.

## Final test results

Isolated candidate workflow run: `37177047684`  
Job: `111361740420`

| Gate | Actual result |
| --- | --- |
| focused cold capture + accepted identity/EventLog suites | **140 passed in 128.46s** |
| affected persistence/EventLog suite | **328 passed in 287.84s** |
| full `simulation/tests` suite | **495 passed in 538.72s** |

Commands were the unchanged bounded candidate commands:

```sh
PYTHONPATH=.:simulation python -m pytest -q -s \
  simulation/tests/test_persistence_cold_capture.py \
  simulation/tests/test_persistence_cold_identity_restore.py \
  simulation/tests/test_persistence_event_identity.py \
  simulation/tests/test_persistence_event_log.py

PYTHONPATH=.:simulation python -m pytest -q \
  simulation/tests/test_incremental_store.py \
  simulation/tests/test_persistence*.py \
  simulation/tests/test_cold_history.py \
  simulation/tests/test_event_year_queries.py \
  simulation/tests/test_canonical_digest.py \
  simulation/tests/test_history_archive.py

PYTHONPATH=.:simulation python -m pytest -q simulation/tests
```

No millennium/endurance, calibration, gameplay, balance, Stage 1 or checkpoint
workflow was invoked.

## Enforced 4 / 40 / 400 bounds

The follow-up converts the earlier printed observations into assertions. Each
real P1/P3A fixture has the same current World, exactly one compressed pending
chunk and three resident mutable-tail Events. The test fixture no longer returns
or retains its expanded decoded suffix.

During **capture only**:

* SQLite authorizer access to the `segments` table is denied. Any segment
  payload/header/count enumeration would make the test fail.
* `EventLog._chunk` is replaced with a failing guard, so pending decode during
  capture would fail.
* `SealedEventPrefix.__iter__` is replaced with a failing guard, so historical
  prefix iteration would fail.
* cold point access is performed only after those guards are removed.

Actual enforced measurements:

| Disk segments | Checked record reads | Checked bytes | Segment reads | Disk cache | Pending segments | Pending cache | Pending compressed bytes | Tail Events | Year entries | Offset entries | Projected groups | Projected paths |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 2,084 | 704,473 | **0** | **0** | 1 | **0** | 10,410 | 3 | 1 | 1 | 87 | 87 |
| 40 | 2,084 | 709,904 | **0** | **0** | 1 | **0** | 10,707 | 3 | 1 | 1 | 87 | 87 |
| 400 | 2,084 | 716,070 | **0** | **0** | 1 | **0** | 10,707 | 3 | 1 | 1 | 87 | 87 |

Assertions require equal checked-record read count, pending/tail cardinalities,
resident year/index cardinalities and projected identity graph size across all
three prefix lengths. The byte count is deliberately not required to be equal:
absolute IDs/indices and descriptor integer text grow with history size.

After capture, first access to event 0 reads exactly one checked disk segment.
Repeating the same access reuses the accepted bounded cache without another
payload read.

## Retention evidence

`test_capture_does_not_retain_decoded_pending_events` intercepts the independently
decoded suffix at the loader boundary and keeps **only weak references** to its
Events. After `_capture_cold_world` returns and collection runs:

* every decoded Event belonging to the pending sealed range is unreachable;
* all three mutable-tail Events remain reachable through the returned World;
* the EventLog retains one compressed pending segment, zero decoded pending
  cache segments and three tail Events.

The fixture itself no longer returns its expanded suffix, so source fixture
Events are not a hidden retention root during the measurement. This proves the
specified resident suffix boundary; it does not claim O(1) memory for the entire
World or for an arbitrarily large unsaved pending backlog.

## Completed malformed-input matrix

The follow-up publishes valid-checksum damage with real P1 commits and advances
`session-commit/v1` unless commit-descriptor corruption is the subject under
test.

`test_cold_capture_rejects_malformed_suffix` covers:

* missing and extra suffix rows;
* a below-D row while keeping record cardinality stable;
* boolean typed key;
* wrong and boolean envelope ordinals;
* wrong and boolean Event IDs;
* non-integer Event year;
* decreasing suffix chronology;
* first suffix year below the captured prefix boundary;
* a twelve-position suffix so numeric ordering is exercised independently of
  encoded/SQLite lexical key order.

`test_cold_capture_rejects_invalid_sealing` covers:

* an unsealed Event in `[D,F)`;
* an Event claiming sealed state while retaining mutable data;
* malformed sealed-flag representation rejected by WorldCodec before
  publication.

`test_cold_capture_rejects_descriptor_and_layout_damage` covers:

* missing empty/required prefix descriptor and an extra descriptor;
* boolean D/F/N values;
* D > F, F > N and non-chunk-aligned D/F;
* last-year mismatch;
* invalid commit token, descriptor version and captured generation;
* prefix/head segment-count mismatch;
* suffix/head record-count mismatch;
* records in the segment namespace and segments in a record-only namespace;
* malformed `collections/v1` overlay;
* typed boolean/float EventLog description damage through the effective overlay.

The six architect-added typed metadata/layout regressions remain present:
boolean/float EventLog totals/chunk counts plus float head year and boolean
head next-person counter.

`test_cold_capture_rejects_wrong_modes` covers:

* supported non-cold P2C input with explicit conversion-required failure;
* unknown event-storage and identity-storage modes;
* mixed manifest authority;
* missing and unknown canonical roots;
* legacy identity-delta namespace authority.

`test_cold_capture_eagerly_rejects_current_record_checksum_damage` proves
checksum corruption in both the resident event suffix and an ordinary current
World record is eager. The checksum mutation always changes a hex character.

`test_cold_capture_rejects_real_world_head_counter_disagreement` separately
proves a correctly typed, correctly checksummed but semantically wrong head
counter fails against the reconstructed World.

## Exact values and identity

`test_capture_restores_every_declared_non_event_root_field_exactly` compares
**every declared non-event root field** from an independent source World to the
captured World through `WorldCodec(identity_links_recorded=True).encode`.
Representative nested wallet/genealogy values and nontrivial dictionary/set
order are included; dictionary insertion order is asserted directly.

`test_capture_restores_exact_event_values_flags_and_boundaries` independently
constructs expected disk, pending and tail Events and compares their accepted
typed representation after capture. It covers exact:

* IDs and order;
* equal-year partition boundaries plus a later tail year;
* kind/layer;
* actors and location Refs;
* causes;
* nested typed data including bool/int/float distinction, signed zero and a
  fixed NaN bit pattern;
* sealed-flag presence/value, including an individually sealed tail Event.

The existing parent/descendant alias test remains green and verifies current
tail identity restoration with Python `is`.

The historical-link test is now parameterized over disk prefix, pending history
and an individually sealed tail occurrence, in both target and owner directions.
It requires a specific format/integrity failure while the SQL segment guard is
active; no cold segment access is permitted.

## Reader, transaction and generation ownership

`test_capture_failure_after_reader_creation_closes_reader_and_preserves_owner`
forces suffix failure **after** prefix-reader allocation. It observes the exact
reader created by the loader and proves:

* the reader is closed on failure;
* the caller's read transaction remains active and checked-head access works;
* the borrowed store remains open.

`test_capture_success_reader_and_store_lifetime_boundaries` proves:

* after the caller exits its successful capture transaction, the reader and
  disk EventLog remain usable while the store is open;
* explicit reader close produces the accepted reader-closed failure;
* store close produces the accepted borrowed-store-closed failure.

`test_capture_generation_remains_fixed_across_later_publication` uses two
real store connections. All captured components agree on one generation inside
the caller transaction. After that transaction exits, the second connection
publishes a new P1 generation. The prior capture retains its original
generation, prefix descriptor/length and readable old prefix.

`test_legacy_apis_reject_cold_input` confirms legacy detached snapshot reading
and incremental binding still reject cold-format input; their ordinary modes
remain covered by the existing P2 full suite.

## Lazy-corruption boundary

The unread-segment damage tests are deterministic:

* one case always changes the stored checksum;
* one case physically removes an unread segment.

In both cases capture succeeds because normal capture is intentionally lazy.
The first checked point access fails, and explicit `verify_full()` also fails.
A separate healthy control captures the same four-segment shape and
`verify_full()` succeeds with the expected segment/event counts.

## Capture-spec requirement map

1. **Complete exact World / partition shapes** —  
   `test_capture_partition_shapes_and_exact_world`,
   `test_capture_restores_every_declared_non_event_root_field_exactly`,
   `test_capture_restores_exact_event_values_flags_and_boundaries`.
2. **Current aliases + forbidden sealed LOG paths** —  
   `test_capture_restores_tail_parent_and_descendant_aliases`,
   `test_forbidden_historical_identity_links_fail_before_cold_io`.
3. **Malformed suffix/descriptors/modes/counts/head** —  
   `test_cold_capture_rejects_malformed_suffix`,
   `test_cold_capture_rejects_invalid_sealing`,
   `test_cold_capture_rejects_descriptor_and_layout_damage`,
   `test_cold_capture_rejects_wrong_modes`,
   `test_cold_capture_eagerly_rejects_current_record_checksum_damage`,
   typed-metadata regressions and checked-head corruption tests.
4. **One caller transaction / failure and generation ownership** —  
   `test_capture_requires_caller_owned_read_transaction`,
   `test_capture_failure_after_reader_creation_closes_reader_and_preserves_owner`,
   `test_capture_success_reader_and_store_lifetime_boundaries`,
   `test_capture_generation_remains_fixed_across_later_publication`.
5. **4/40/400 lazy bounded capture + retention** —  
   `test_capture_enforces_4_40_400_read_and_retention_bounds`,
   `test_capture_does_not_retain_decoded_pending_events`.
6. **First cold read/cache + lazy corruption/full scrub** —  
   the enforced-bounds point-read assertions,
   `test_lazy_capture_defers_unread_segment_damage_but_access_and_scrub_fail`,
   `test_healthy_capture_explicit_full_verification_control`.
7. **Legacy/current P2 + accepted P3A/P3B regressions** —  
   `test_legacy_apis_reject_cold_input` plus the 328-test affected and
   495-test full-suite passes.

## Remaining boundary

This completes evidence for the internal **unbound cold capture** slice only.
It does not implement or prove:

* a public owned World/session API;
* tracking/binding of the captured World;
* atomic incremental cold save/publication or acknowledgement recovery;
* ownership retirement, detach or public close guards;
* checkpoint/export integration or conversion;
* independent resumed simulation equivalence;
* a bound on total current-World memory or arbitrary unsaved backlog.

No public/session/save integration, EventLog/P3A redesign, persistence format
change, workflow landing, millennium/endurance run, balance change, Stage 1,
checkpoint replacement or merge was performed.
