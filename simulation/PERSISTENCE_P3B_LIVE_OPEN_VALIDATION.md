# P3B live cold open — validation

Status: bounded live-open review corrections implemented and green; ready for
architect review, 2026-10-04 UTC. The original live-open evidence remains below
as historical evidence. The six blocking lifecycle/atomicity findings from
`PERSISTENCE_P3B_LIVE_OPEN_REVIEW.md` were reproduced before the fix and are
covered by the correction validation recorded later in this document.

Green candidate head: `a5029ff7b5a60e7ab5cdfcdfe6914e17f74ec819`.
Green isolated workflow: `37222438702`.

## Scope exercised

This slice implements only the bounded live cold-open foundation from
`PERSISTENCE_P3B_LIVE_OPEN.md`:

- `open_world_session(path, *, rules_id)`
- one owned `TransactionalStore` and one captured cold generation
- binding through the existing `IncrementalWorldSession`
- current-state plus mutable EventLog-tail identity tracking
- semantic sealing-owner retirement/reanchoring in memory
- cold `save()` refusal before persistence mutation
- close without cold-prefix traversal
- legacy P2/P2C `bind_snapshot` behavior retained

It does **not** implement cold incremental save, acknowledgement recovery,
detach/materialize-history, checkpoint replacement, P4, Stage 1, balance work
or millennium calibration.

The temporary candidate CI workflow is intentionally not landed on PR #14.

## Candidate/landing identity

The source and tests landed on `sim/stage-0-5-stabilization` are byte-for-byte
the files exercised by the final green candidate workflow.

- `simulation/ate_sim/persistence_session.py`
  - candidate blob: `cfa0c5e482cd9db4269cf7889f6e4004e458f06f`
  - landed blob: `cfa0c5e482cd9db4269cf7889f6e4004e458f06f`
- `simulation/ate_sim/persistence_tracking.py`
  - candidate blob: `957534f82753e13ebed5734f441fd97ab2a1b1bb`
  - landed blob: `957534f82753e13ebed5734f441fd97ab2a1b1bb`
- `simulation/tests/test_persistence_session_open.py`
  - candidate blob: `c9b891f1d53e2977e0967e042705c826918d84b1`
  - landed blob: `c9b891f1d53e2977e0967e042705c826918d84b1`

## Validation results

Final candidate workflow `37222438702`:

- focused live-open/cold identity/EventLog set:
  **182 passed in 87.27 s**
- affected persistence set:
  **377 passed in 361.33 s**
- full `simulation/tests` suite:
  **544 passed in 485.85 s**

No millennium/endurance run was part of this bounded slice.

## Live-open behavior covered

Coverage proves:

- empty, tail-only, prefix-only, mixed and pending cold partitions open cleanly
- wrong rules and legacy non-cold stores reject explicitly
- old sealed-segment payload corruption is deferred at open and fails on access
- open begins with no dirty/deleted/pending-link state
- parent/child aliases spanning current state and mutable EventLog tail restore
- legal current-state aliasing to a mutable tail Event restores
- cold EventLog binding never walks committed or pending sealed history
- mutations through retained aliases dirty the actual current owners
- `save()` on a cold session raises before generation or dirty state changes
- context-manager close and direct close perform no save
- partial-open failure clears global bindings
- direct store close makes cold history access fail rather than reopening

Legacy incremental session save has a dedicated regression proving it still
advances generation normally.

## Semantic sealing retirement

When a leading mutable tail chunk becomes sealed, the live session:

- retires the exact absolute `world.events` owners
- removes those owners from the occurrence index
- applies the final-state identity-link reanchor/remove patch
- removes only retired LOG ownership from tracked objects
- preserves surviving current-state ownership
- stops old detached mutable descendants from dirtying LOG owners
- performs zero disk-segment reads
- does not persist anything in this slice

## Measured open/close bounds

The same suffix/current-state shape was measured over 4, 40 and 400 committed
cold segments.

| metric | 4 | 40 | 400 |
| --- | ---: | ---: | ---: |
| segment reads during open/bind | 0 | 0 | 0 |
| resident disk cache segments | 0 | 0 | 0 |
| mutable LOG owners | 3 | 3 | 3 |
| mutable LOG occurrences | 6 | 6 | 6 |
| pending sealed events | 2,048 | 2,048 | 2,048 |
| mutable tail events | 3 | 3 | 3 |
| segment reads after close | 0 | 0 | 0 |

Thus history growth from 4 to 400 committed segments does not grow cold payload
reads, EventLog mutable-owner bookkeeping, or the disk reader cache at
open/close.

## Alias-scaling bound

With 100, 300 and 1,000 unrelated alias groups, mutating one local alias dirtied
exactly one persistence owner in every case:

| unrelated alias groups | dirty owners |
| --- | ---: |
| 100 | 1 |
| 300 | 1 |
| 1,000 | 1 |

This preserves the affected-owner scaling requirement instead of rescanning
unrelated aliases.

## Review-correction reproduction and validation

Architect review at live head
`964d63ba2cab3e1cc2448969d54d5bdac30dce9b` required bounded corrections for
LOG-owner retirement, memo cleanup and rejected-append atomicity.

The six exact review seeds were first added as permanent tests and run before
the corrections. Isolated reproduction workflow `37225428737` failed all six
at their stated behavioral assertions:

1. newly appended full chunk retained its first Event binding;
2. replaced child remained retained after sealing;
3. individually sealed tail Event retained LOG identity;
4. tracked set remained retained after its LOG owner disappeared;
5. already-sealed append incorrectly gained LOG identity;
6. rejected cross-session append had already increased the destination log.

That run is preserved as failure-reproduction evidence rather than a green
validation result.

After the bounded corrections, focused review workflow `37225613443` ran the
review-only cases:

- **17 passed, 19 deselected in 24.50 s**.

The final tested correction candidate was
`b07146803f27a1ae33be58c448d068d37e651ae2`.
Final isolated workflow: `37225707267`.

Commands:

```text
python -m pytest -q -s   simulation/tests/test_persistence_session_open.py   simulation/tests/test_persistence_tracking.py   simulation/tests/test_persistence_p2b_followup.py   simulation/tests/test_persistence_p2b_identity_review.py   simulation/tests/test_persistence_p2b_review_regressions.py   simulation/tests/test_persistence_p2c.py   simulation/tests/test_persistence_event_identity.py   simulation/tests/test_persistence_event_log.py   simulation/tests/test_persistence_events.py   simulation/tests/test_persistence_cold_capture.py   simulation/tests/test_persistence_cold_identity_restore.py

python -m pytest -q   simulation/tests/test_incremental_store.py   simulation/tests/test_persistence*.py   simulation/tests/test_cold_history.py   simulation/tests/test_event_year_queries.py   simulation/tests/test_canonical_digest.py   simulation/tests/test_history_archive.py

python -m pytest -q simulation/tests
```

Results:

- expanded live-open / tracking / EventLog / identity set:
  **297 passed in 188.93 s**
- affected persistence set:
  **394 passed in 394.17 s**
- full unit/integration `simulation/tests` suite:
  **561 passed in 577.05 s**

No millennium/endurance workflow was run.

### Correction behavior covered

The permanent regressions now prove:

- sealing retires the actual current mutable LOG graph even when the occurrence
  index is stale from a just-appended Event or replaced nested payload;
- no-refresh and already-refreshed retirement converge to the same current-link
  result and surviving non-LOG aliases remain usable;
- individual `Event.seal()` immediately retires mutable LOG authority without
  changing D or F;
- a later full-chunk seal retires an individually sealed tail Event
  idempotently while preserving surviving current-state ownership;
- appending an already sealed Event records its value/layout as dirty for future
  persistence but grants no mutable LOG ownership;
- tracked sets use reverse memo registration and retired raw/wrapper pairs are
  reclaimable;
- detached former payload mutation cannot dirty or resurrect a retired LOG
  owner, including across repeated identity refresh;
- cross-session Event and foreign-descendant appends are rejected before
  authoritative EventLog or tracking mutation;
- invalid ID/year append rejection leaves tracking and authoritative log state
  unchanged;
- closing the rejected destination session does not disturb the source session;
- repeated append/seal batches release retired Events/wrappers instead of
  growing session memo/global-binding retention;
- cold `save()` remains explicitly blocked.

### Measured correction bounds

The original 4/40/400 open/close measurements remain unchanged in the final
candidate:

| metric | 4 | 40 | 400 |
| --- | ---: | ---: | ---: |
| cold segment reads | 0 | 0 | 0 |
| resident disk cache | 0 | 0 | 0 |
| mutable LOG owners | 3 | 3 | 3 |
| mutable LOG occurrences | 6 | 6 | 6 |
| pending sealed events | 2,048 | 2,048 | 2,048 |
| mutable tail events | 3 | 3 | 3 |

Appending/sealing/retiring/closing over 4, 40 and 400 committed cold segments
also performs **0 cold segment payload reads**.

Unrelated alias mutation remains affected-owner bounded:

| unrelated alias groups | dirty owners |
| --- | ---: |
| 100 | 1 |
| 300 | 1 |
| 1,000 | 1 |

Retiring one LOG owner remains independent of 100/300/1,000 unrelated alias
groups:

| unrelated alias groups | owners requested | occurrences removed | affected groups |
| --- | ---: | ---: | ---: |
| 100 | 1 | 4 | 4 |
| 300 | 1 | 4 | 4 |
| 1,000 | 1 | 4 | 4 |

Thus retirement work is tied to the retiring/touched owner graph rather than
historical segment count or unrelated alias population.

### Correction candidate/landing identity

The final correction product/test bytes landed on
`sim/stage-0-5-stabilization` are the exact bytes exercised by workflow
`37225707267`:

- `simulation/ate_sim/persistence_tracking.py`
  - candidate blob: `4883050743032e0ed79082df5453995b60887d51`
  - landed blob: `4883050743032e0ed79082df5453995b60887d51`
- `simulation/tests/test_persistence_session_open.py`
  - candidate blob: `11b8115980b42e22e687456129fa70487f3637a3`
  - landed blob: `11b8115980b42e22e687456129fa70487f3637a3`

The temporary isolated validation workflow is intentionally not landed on
PR #14.

## Remaining boundary

This green result establishes the live **open/bind/in-memory-sealing/close**
foundation only.

Still intentionally pending for later P3B slices:

- atomic cold incremental save
- bounded transfer of pending sealed chunks during save
- lost-ack/ambiguous-commit recovery
- stale-writer handling
- detach/materialize-history and explicit full-history verification
- engine/checkpoint lifecycle guards
- integrated repeated-save continuation/scaling
- final P3B validation and Stage 0.5 completion
