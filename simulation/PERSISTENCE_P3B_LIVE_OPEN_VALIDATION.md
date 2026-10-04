# P3B live cold open — validation

Status: green candidate reviewed; corrections required before architect acceptance,
2026-10-04 UTC. See `PERSISTENCE_P3B_LIVE_OPEN_REVIEW.md` for six independently
reproduced failing lifecycle probes at `d3017a8`. The completed CI evidence below
remains valid but does not cover those failures.

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
