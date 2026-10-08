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


## Focused implementation evidence

Product implementation head:
`eeb7f474d1a7bb5c0836e20341d3f88f43cdaf87`.

Focused run `37405753215` passed **12/12 in 1.55s**, covering the new
scalar-archive persistence proofs plus agency and institution integration.

Scaling run `37405836051` passed the 1,000/10,000 fixed-work proof:

| Measure | 1,000 rows/family | 10,000 rows/family |
| --- | ---: | ---: |
| ordinary-open payload reads | 33 | 33 |
| ordinary-open payload bytes | 16,667 | 16,672 |
| fixed history + motive point payload reads | 3 | 3 |
| fixed query payload bytes | 1,180 | 1,180 |
| one-motive save payload writes | 3 | 3 |
| one-motive save payload bytes | 528 | 528 |
| resident transmissions | 2 | 2 |
| resident motives | 1 | 1 |

The fixed transmission history returned IDs `[1,2]` at both sizes.

Affected P4 regression evidence is still required before this tranche is
accepted closed.


## Final validation evidence

P4.8 is accepted closed on product head
`7d07ca3035882b3c1f0b46ce6782dd7c7abb926c`.

- Focused run `37405892154`: **11/11 passed in 2.70s**.
- Scaling run `37405979599`: 1,000 and 10,000 rows both opened at
  **33 payload reads** (~16.7 KB), fixed transmission-history + motive point
  access used **3 payload reads / 1,180 bytes**, one motive save used
  **3 payload writes / 528 bytes**, and residency stayed at
  **2 transmissions / 1 motive**.
- Motive real-step regression run `37408711813`: **2/2 passed in 3.00s**.
- Corrected affected P4 run `37408783568`: **252/252 passed in 212.94s
  (3:32)**.

The earlier affected failures were resolved by excluding persistence binding
metadata from Agency motive selection; no gameplay balance or simulation rule
changed.

Next action: rerun the residual eager inventory from this validated head and
select the next family strictly by measured remaining cost.
