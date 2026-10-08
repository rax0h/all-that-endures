# P3B identity primitive validation

Baseline: `0cd7d6bb52322d1fb416dbb4762a9239e1d8e5a7`, the architect-reviewed
composite EventLog acceptance and `PERSISTENCE_P3B_IDENTITY.md` assignment.

Scope is intentionally limited to reusable identity-index primitives. Product
code changes only `ate_sim/persistence_identity.py`. No session, tracking,
adapter, restore, save, acknowledgement, detach, checkpoint or simulation-rule
integration is included.

## Focused evidence

Pre-final focused candidate `92dabde26015821ee920ccdd9e688532a2541845`:

```
PYTHONPATH=.:simulation python -m pytest -q -s \
  simulation/tests/test_persistence_event_identity.py
16 passed in 7.23s
```

The real P1/P3A fixtures use the same resident suffix: one pending sealed
2,048-event chunk plus four tail Events, one of which is individually sealed.
Pending-chunk decode is instrumented to raise if touched.

| disk segments | cold segment reads | disk cache | pending cache | indexed occurrences | indexed paths |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0 | 0 | 0 | 13 | 13 |
| 40 | 0 | 0 | 0 | 13 | 13 |

The 13 rows are the EventLog root plus three eligible mutable tail Events and
their mutable nested payload containers. Counts are independent of committed
history size. The helper preserves absolute logical indices and skips the
individually sealed tail Event without renumbering later occurrences.

## Retirement scaling

Each measurement contains one three-path local alias group and the requested
number of unrelated two-path alias groups. Only the one LOG owner is retired.

| unrelated alias groups | total owner rows | total paths | requested owners | removed owners | removed occurrences | affected groups | surviving local paths examined | removed links | added links |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 203 | 203 | 1 | 1 | 1 | 1 | 2 | 2 | 1 |
| 300 | 603 | 603 | 1 | 1 | 1 | 1 | 2 | 2 | 1 |
| 1,000 | 2,003 | 2,003 | 1 | 1 | 1 | 1 | 2 | 2 | 1 |

Thus retirement work is bounded by removed occurrences plus surviving paths in
the affected identity groups; the measured local work and patch sizes do not
change as unrelated groups increase.

## Behavioral coverage

Focused regressions cover empty/in-memory/disk EventLogs; pending history and
absolute-index holes; disk-backed default-scope rejection; EventLog root aliases;
shared mutable tail parent/descendant aliases; sealed Events retained under
non-log owners; invalid explicit links into excluded history; reader/store close
while enumeration is suspended; accepted chunk sealing followed by batched
retirement; old-anchor reanchoring; one/zero-survivor groups; individually
sealed tail retirement; pre-mutation owner-batch validation; weak-reference
release; idempotence; and repeated seal/retire cycles without index accumulation.

## Deliberate remaining boundary

This slice reclaims references owned by `IdentityOccurrenceIndex` only.
`_BINDINGS`, `_memo`, dirty-owner state, baseline ordinals and tracked-child
ownership are unchanged and remain future session-integration work. This
validation does not claim cold World restore, atomic save/recovery, format
conversion, detach, or bounded total World memory.


## Final validation

Final tested candidate: `3efc00b1cff4c922009c029e00f4121afea239ba`.
The product and test blobs in that candidate are the blobs landed on PR #14.

```
PYTHONPATH=.:simulation python -m pytest -q -s \
  simulation/tests/test_persistence_event_identity.py
16 passed in 13.51s

PYTHONPATH=.:simulation python -m pytest -q \
  simulation/tests/test_incremental_store.py \
  simulation/tests/test_persistence_adapters.py \
  simulation/tests/test_persistence_event_identity.py \
  simulation/tests/test_persistence_event_log.py \
  simulation/tests/test_persistence_events.py \
  simulation/tests/test_persistence_p2b_followup.py \
  simulation/tests/test_persistence_p2b_identity_review.py \
  simulation/tests/test_persistence_p2b_review_regressions.py \
  simulation/tests/test_persistence_p2c.py \
  simulation/tests/test_persistence_tracking.py \
  simulation/tests/test_cold_history.py \
  simulation/tests/test_event_year_queries.py \
  simulation/tests/test_canonical_digest.py \
  simulation/tests/test_history_archive.py
227 passed in 203.15s

PYTHONPATH=.:simulation python -m pytest -q simulation/tests
394 passed in 463.92s
```

No millennium/endurance run, balance probe, Stage 1 work, checkpoint replacement,
session integration or merge was performed.
