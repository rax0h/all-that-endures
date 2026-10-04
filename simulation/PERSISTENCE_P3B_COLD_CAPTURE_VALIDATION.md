# P3B cold World capture validation

Status: implementation evidence for `PERSISTENCE_P3B_COLD_CAPTURE.md`,
2026-10-03.

Accepted starting head:
`21a1bc217d7e73e03c4ce55e1daa47220bf017a4`.

Fully tested candidate:
`bbbd1d727ca95918d51c35c3bc1219fde01d9569`.

This slice captures one complete **unbound** World from the specified P3B cold
format while borrowing an already-open `TransactionalStore` and one
caller-owned read transaction. It does not expose a public session API and does
not implement binding, save/recovery, conversion, detach or checkpoint
integration.

## Implemented boundary

### Checked bounded head access

`TransactionalStore.checked_head()` reads one save-head row and verifies its
existing checksum before returning:

- generation and parent generation;
- decoded head metadata;
- committed namespace record/segment counts.

It validates canonical decoded metadata and that all nonzero namespace counts
belong to the published inventory. It does not enumerate records or segments,
run `integrity_check`, scrub payloads or open/close a transaction.

### Cold-format capture

New internal `ate_sim.persistence_session._capture_cold_world(store)`:

- requires an active caller-owned `read_transaction()`;
- accepts only the explicit cold manifest mode with
  `identity_storage="current-links/v1"` and
  `event_storage="sealed-prefix-tail/v1"`;
- validates canonical namespace inventory, committed counts, effective
  collections layout, P3A descriptor, `session-tail/v1` and
  `session-commit/v1`;
- requires a 32-character lowercase hexadecimal commit token;
- captures the P3A reader with
  `SealedEventPrefix.from_active_read_transaction(store)`;
- requires reader/head/commit generation agreement;
- restores all non-event canonical collections through the accepted checked
  adapter paths;
- reads only `world.events` rows in the resident suffix `[D,N)`, orders them
  numerically by absolute index and validates exact keys, ordinals, IDs,
  chronology, sealed flags and frozen sealed values;
- constructs the accepted composite `EventLog` with the immutable disk prefix
  left lazy and exactly `F-D` persisted sealed events packed into pending
  chunks;
- validates World seed/year/next-ID counters, including
  `next_event == N + 1`;
- restores P2C current identity links using the accepted cold preflight/relink
  helpers and verifies the projected current graph before returning.

The returned internal `ColdWorldCapture` contains the reconstructed World,
borrowed prefix reader, captured generation, checked head, effective manifest,
current identity links and validated prefix/tail/commit descriptors. It does
not retain raw suffix rows or expanded pending-event rows separately.

On failure, any created prefix reader is closed while the caller-owned store and
read transaction remain untouched. On success, the caller owns the returned
reader lifetime.

## Validation

Isolated candidate workflow run: `37168195017`  
Job: `111335498658`

| Gate | Result |
| --- | --- |
| focused cold capture + accepted P3B identity/EventLog | **76 passed in 75.17s** |
| affected persistence/EventLog | **264 passed in 227.16s** |
| full `simulation/tests` | **431 passed in 472.06s** |

Commands:

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

## 4 / 40 / 400-segment bounds

Each fixture has the same current World shape, one resident pending sealed
chunk and three resident tail Events. Capture is measured before any cold point
access.

| Disk segments | Checked payload reads | Checked payload bytes | Segment payload reads | Disk cache | Pending cache | Pending bytes | Tail events | Projected groups | Projected paths |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 2,084 | 704,473 | **0** | **0** | **0** | 10,410 | 3 | 87 | 87 |
| 40 | 2,084 | 709,904 | **0** | **0** | **0** | 10,707 | 3 | 87 | 87 |
| 400 | 2,084 | 716,070 | **0** | **0** | **0** | 10,707 | 3 | 87 | 87 |

The checked record-read count, tail size and projected identity size are
identical as immutable prefix history grows from 4 to 400 segments. The small
payload-byte increase is attributable to larger descriptor/index integer text,
not history payload reads. Capture performs zero P3A segment payload reads and
starts with an empty disk cache and pending decode cache.

After capture, first point access to an old event reads exactly one cold
segment; repeated access to the same event uses the accepted bounded prefix
cache without another checked segment read.

A fixture with an unread cold segment checksum corrupted after publication
still captures successfully, demonstrating the deliberately lazy guarantee;
the first checked access to that segment then raises integrity failure. Current
suffix/record corruption remains eager because those records are read during
capture.

## Behavioral evidence

Focused coverage establishes:

- empty, prefix-only, tail-only, >4 pending-chunk and mixed partition capture;
- exact World seed/year/next-ID restoration and composite EventLog boundaries;
- current tail parent/descendant identity relinking across independently
  persisted payload copies;
- an identity endpoint into excluded pending history fails without reading a
  cold segment;
- use outside a caller-owned read transaction fails before capture work;
- a save-head corrupted after opening the connection is caught by the new
  checked-head checksum accessor;
- successful capture preserves a reader that remains usable after the caller
  exits the capture transaction while the store stays open;
- failed capture leaves the borrowed store and outer read transaction under
  caller control;
- first cold access is lazy and then obeys accepted cache behavior.

The accepted P2/P3A/P3B persistence suites remain green in the affected and full
suite runs.

## Remaining boundary

This is an internal, unbound capture helper only. It does not create a public
World/session API, bind tracking hooks, publish saves, recover acknowledgements,
retire tracking/binding ownership, detach Worlds, convert formats, integrate
checkpoints/exports or prove independent resumed simulation. The returned
EventLog continues to borrow the caller-owned store through the P3A prefix
reader.

No millennium/endurance run, balance or magic-progression change, Stage 1 work,
normal checkpoint replacement, workflow change or PR merge was performed.
