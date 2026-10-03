# P3B cold identity restore validation

Status: implementation evidence for `PERSISTENCE_P3B_IDENTITY_RESTORE.md`,
2026-10-03.

Accepted starting head:
`4629a309868720064e71d13e82954e8752de9152`.

Tested candidate:
`025d728fa65157a601ee0f6863be8253de317d8a`.

This slice adds cold-safe identity path resolution, projected identity graph
verification and restoration-only mutable EventLog tail relinking. It does not
implement a cold World/session loader, save/recovery, conversion, detach,
checkpoint integration or any persistence format change.

## Product changes

`persistence_adapters.py` extends the existing internal helpers with explicit
`mutable_event_tail_only=False` mode:

- `_at_path` checks EventLog borrowed-backend lifetime, resolves mutable-tail
  absolute indices directly from resident metadata/tail storage, and rejects
  disk history, pending sealed chunks, individually sealed tail Events,
  malformed/bool/negative/out-of-range indices before history access.
- `_complete_identity_groups` uses the accepted mutable-tail enumeration
  boundary for every EventLog occurrence and the same frozen-container stopping
  rule as the accepted occurrence index.
- `_verify_identity_graph` validates explicit endpoints through that resolver
  before projected graph traversal while retaining conflict, cycle and
  unexplained-sharing checks.
- `_restore_identity` validates the complete batch, assignment boundaries and
  exact typed payload copies before any relink, then applies the accepted
  ancestor-before-descendant ordering and re-resolves owners after ancestors.
  Whole EventLog endpoints are compared only by object identity; distinct logs
  are rejected without value/history traversal.

`event_log.py` adds the private restoration-only
`_relink_mutable_tail(index, replacement)` primitive. It preserves the
EventLog object and all prefix/pending/count/year boundaries while requiring an
absolute mutable-tail index, exact Event type, unsealed current/replacement
Events, stable ID `index + 1` and unchanged year.

## Validation

Isolated candidate workflow: `37161776401`, job `111316527583`.

| Gate | Result |
| --- | --- |
| focused restore + accepted identity/EventLog suites | **61 passed in 35.40s** |
| affected persistence/EventLog suite | **249 passed in 155.62s** |
| full `simulation/tests` suite | **416 passed in 356.46s** |

Commands:

```sh
PYTHONPATH=.:simulation python -m pytest -q -s \
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

## Zero-history-read measurements

Real checked P1/P3A stores used the same one-pending-chunk/four-tail-event
resident suffix. The EventLog's logical iterator and pending-chunk decoder were
instrumented to fail if used by cold identity resolution/verification.

| Disk segments | Projected identity groups | Projected paths | Segment payload reads | Disk cache | Pending decodes | Pending cache |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 14 | 27 | **0** | **0** | **0** | **0** |
| 40 | 14 | 27 | **0** | **0** | **0** | **0** |

The projected counts are identical as committed history grows. Tail lookup uses
the absolute index and resident tail offset directly; it does not enumerate the
tail or logical EventLog.

## Behavioral evidence

The maintained restore regressions establish:

- default helpers fail closed on disk-backed EventLogs before history reads;
- cold paths reject disk history, pending sealed history, individually sealed
  tail Events, descendants of excluded occurrences and paths through log aliases;
- malformed components, bool/negative/out-of-range indices and closed
  reader/store state fail before relinking;
- parent and descendant mutable aliases restore across EventLog/current-state
  copies in both link directions and verify afterward;
- a whole mutable tail Event can be relinked to an independently decoded current
  Event without changing log identity, prefix reader, pending bytes, counts,
  IDs, years, ordering or year indexes;
- the private relink rejects non-Event replacements, wrong IDs, changed years
  and sealed replacements without changing the tail;
- a sealed Event independently reachable through non-log current state remains
  part of the projected identity graph even though its log occurrence is excluded;
- typed-codec equality accepts matching NaN bit patterns and rejects different
  NaN payload bits, bool/int, int/float and positive/negative-zero mismatches;
- a late missing endpoint or unsupported assignment boundary leaves all earlier
  valid targets untouched;
- cycle, conflicting-target and unexplained-sharing rejection remain intact;
- distinct whole EventLog copies are rejected without payload reads, while an
  already-shared log root is restored/verified without encoding or iterating
  history.

## Remaining boundary

This helper-level slice does not create or open a cold World session and does
not prove restored simulation continuation, durable identity publication,
binding/`_memo` reclamation, atomic save/recovery, conversion, detach,
checkpoint/export integration, or bounded total World memory. Those remain
later P3B gates.

No millennium/endurance, balance/magic-progression change, Stage 1 work,
checkpoint replacement, workflow weakening or merge was performed.
