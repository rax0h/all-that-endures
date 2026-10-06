# P4.8 — scalar residual archives plan

**Date:** 2026-10-05
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and accepted P4 behavior through P4.7.

## Residual evidence after P4.7

Run `37404867361` on product head
`e87009f05c7267d8ffb290f04d7780d07095591e` measured the post-institution
residual eager graph.

At 10,000 synthetic rows:

- `world.transmission.records`: 4,403,364 payload bytes;
- `world.agency.motives`: 4,088,890 payload bytes;
- social family combined: 5,682,246 payload bytes;
- `world.skills.skills`: 2,815,568 payload bytes.

Ordinary residual open still scaled from 23,035 reads / 4.39 MB at 1k to
230,035 reads / 44.4 MB at 10k.

Transmission + motives together remove about **8.49 MB** with no nested mutable
record graph, so they are the next lowest-risk/highest-impact tranche. Social is
remeasured immediately after this tranche.

## Scope

Migrate only:

- `world.transmission.records`;
- `world.agency.motives`.

Keep `world.agency.actions` eager because it is explicitly capped at 50,000
rows and therefore is not unbounded history.

## Transmission behavior

`Transmission` becomes tracking-aware without changing stored fields or
simulation semantics. Persist a checked membership index for
`(item_kind,item_id)`; `TransmissionState.history()` must use that index
rather than scanning the entire archive.

Required ordering remains record insertion/ID order, matching the current
append-only behavior.

## Motive behavior

`MotiveState` becomes tracking-aware without changing stored fields or
simulation semantics. Motives remain keyed by person ID. Point lookup, direct
field mutation and annual replacement through `assess()` must remain exact.

## Shared persistence contract

- zero transmission/motive payload decodes on ordinary lazy open;
- one point read loads one row;
- one fixed transmission-history query loads only matching rows;
- clean caches <=256 rows/table;
- exact dict order and delete/reinsert behavior;
- no-op save writes zero payloads;
- one changed row writes one row version plus exact identity/query/head deltas;
- direct field edits are save-visible;
- stale/lost-ack/failure behavior uses the accepted hybrid save contract;
- materializing detach restores ordinary RecordTable-compatible mappings and
  portable checkpoint state;
- 1k -> 10k history keeps open/query/save work bounded.

After focused + affected gates, rerun residual inventory and choose the next
family from measured remaining cost.
