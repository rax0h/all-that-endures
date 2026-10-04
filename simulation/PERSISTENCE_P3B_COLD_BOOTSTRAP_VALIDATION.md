# P3B cold bootstrap — validation and Astra acceptance

Status: accepted within the bounded cold-bootstrap scope, 2026-10-04 UTC.

Reviewed green candidate: `5f6429eb774b0d426081f1038d42f64e305a6011`.
Green isolated workflow: `37218223612`.
Landed implementation/test parent: `31212c5fd2fe49392199be6eab2400f978104d1f`.

## Acceptance decision

The P3B cold-bootstrap slice is accepted.

The implementation provides the two specified entry points:

- `write_cold_snapshot(world, destination, *, rules_id)`
- `convert_event_storage(source, destination, *, rules_id)`

It keeps this slice deliberately separate from live session binding, incremental saves, acknowledgement recovery, close/detach APIs, engine integration, default checkpoint replacement and Stage 1.

The temporary validation workflow used on the candidate branch is intentionally **not** landed on PR #14.

## Candidate/landing identity

The accepted source and test files were copied byte-for-byte from the green candidate onto `sim/stage-0-5-stabilization`.

- candidate `simulation/ate_sim/persistence_session.py` blob:
  `db7b2495e8028700783399ecf728a80cb1001643`
- landed source blob:
  `db7b2495e8028700783399ecf728a80cb1001643`
- candidate `simulation/tests/test_persistence_cold_bootstrap.py` blob:
  `0cb5368917187d072a9554a6f0c4a2a3d817933b`
- landed test blob:
  `0cb5368917187d072a9554a6f0c4a2a3d817933b`

Thus the product/test bytes on PR #14 are the exact bytes exercised by the final green validation run.

## Validation results

Final candidate workflow `37218223612` on
`5f6429eb774b0d426081f1038d42f64e305a6011`:

- focused bootstrap + cold capture + identity/EventLog set:
  **170 passed in 345.52 s**
- affected persistence set:
  **358 passed in 506.64 s**
- full `simulation/tests` suite:
  **525 passed in 756.60 s**

No millennium/endurance run was part of this bounded validation.

## Reviewed representation

The final cold snapshot uses the accepted cold representation:

- `identity_storage="current-links/v1"`
- `event_storage="sealed-prefix-tail/v1"`
- `world.events=("EventLog-disk/v1", N, F/C)`
- immutable P3A segments for `[0,F)`
- individual canonical `world.events` rows only for `[F,N)`
- explicit P3A descriptor, session-tail descriptor and session-commit descriptor
- current-link authority only; no identity-delta authority in the published cold store

The writer removes the temporary collection-layout overlay at finalization so it
cannot mask the cold EventLog description.

## Source preservation and compatibility

Coverage includes:

- empty, list-backed, tail-only, prefix-only and mixed histories
- six sealed chunks with transfer across more than one bounded batch
- individually sealed tail Events
- preservation of source Event/EventLog flags, chunk bytes, logical indices,
  query caches and container identity
- list normalization without replacing the caller's list
- current mutable aliases crossing event/non-event state
- surviving non-log aliases to a sealed Event while the log occurrence remains
  value history rather than current identity authority
- explicit rejection of a canonical event list whose list container is aliased
  elsewhere, which remains the documented compatibility boundary
- bound World rejection, foreign bound-record rejection, active-step rejection
  and disk-backed EventLog rejection
- exact integer ID/year/counter validation
- current P2C conversion
- genuine P2A legacy conversion
- genuine P2B conversion with 13 identity deltas and collections overlay
- source-byte preservation during conversion
- bad rules, malformed source, already-cold source, existing destination,
  dangling symlink, same path and hard-link alias rejection

Cold-source relocation remains a P1 backup operation rather than conversion.

## Publication and failure boundary

The accepted implementation builds in a private same-parent directory, validates
the complete private cold database, closes the store, then publishes with an
atomic no-overwrite hard link followed by directory fsync.

Coverage proves:

- failures before publication leave the destination absent
- failures after private transfer/final commits still leave no public partial
  destination
- a competing destination created after preflight is preserved
- after-link failure leaves a complete validated destination
- directory-fsync failure propagates while preserving the complete destination
- retry never overwrites an existing destination
- subprocess death before publication leaves no destination
- subprocess death after publication leaves a complete destination

The source remains unchanged across tested success/failure boundaries.

## Continuation

An independently constructed unbound control and the restored cold World were
continued for ten years. Canonical digests, next-event values, event counts,
encoded event values and relevant aliases matched exactly.

This is intentionally **not** evidence for live bound-session saves; that remains
a later P3B slice.

## Measured bounds

Synthetic histories were measured at 4, 40 and 400 sealed segments with fixed
current graph/tail.

| Metric | 4 segments | 40 segments | 400 segments |
| --- | ---: | ---: | ---: |
| source compressed bytes | 53,193 | 542,213 | 5,804,826 |
| staging payload writes | 8,226 | 81,954 | 819,234 |
| staging payload bytes | 3,193,965 | 32,089,932 | 323,261,307 |
| transfer payload reads | 0 | 9 | 99 |
| transfer payload writes | 5 | 50 | 500 |
| transfer payload bytes | 2,971,745 | 29,881,360 | 300,452,235 |
| validation payload reads | 91 | 163 | 883 |
| validation read bytes | 5,975,276 | 59,793,135 | 600,920,386 |
| final file bytes | 4,591,616 | 45,404,160 | 454,664,192 |
| transfer commits | 1 | 10 | 100 |
| largest transfer batch | 4 | 4 | 4 |
| deleted old event rows | 8,192 | 81,920 | 819,200 |
| written sealed segments | 4 | 40 | 400 |
| segment reads on reopen | 0 | 0 | 0 |
| retained tail events | 3 | 3 | 3 |
| pending cache segments | 0 | 0 | 0 |

Tenfold history growth from 40 to 400 stays approximately linear in all
history-sensitive write/read/file-byte measures. Transfer batches remain capped
at four chunks and transfer transactions equal `ceil(H/4)`.

These figures describe explicit full bootstrap/conversion cost. They are **not**
a claim that normal gameplay open/save is O(1) or four-chunk total memory.
Bootstrap still includes the accepted P2 full audit/export cost and full
validation cost.

## Remaining boundary

P3B cold bootstrap is now complete and accepted.

Still not implemented by this acceptance:

- public live cold-session binding/open
- incremental live saves into cold storage
- acknowledgement/lost-ack recovery for a live session
- detach/close lifecycle
- engine/checkpoint integration
- bounded live-save measurements
- long-horizon integrated continuation through repeated cold saves
- default checkpoint replacement
- Stage 1

The next architectural step is the bounded **live cold-session binding/save
slice**, specified separately before implementation.
