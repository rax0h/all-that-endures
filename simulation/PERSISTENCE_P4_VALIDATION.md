# P4 validation — Stage 0.5 persistence architecture

**Implementation candidate SHA:** `14f178623a6ef6e0d915fb4fe061079f54b15c21`  
**Branch:** `sim/stage-0-5-stabilization`  
**Scope:** P4 versioned lazy current-state persistence and measured archive-family migration.  
**Non-goals preserved:** no balance/magic pacing changes, no checkpoint-default replacement, no Stage 1, no merge.

## Candidate/source equivalence

The integrated full-suite helper branch is created directly from the implementation
candidate and adds only `.github/workflows/p4-integrated-full-suite.yml`.
Therefore simulation source and test bytes are identical to the candidate SHA.
The final residual helper branches likewise add workflow files only.

## Foundation and identity

- P4.1 corrected focused run `37314495881`: **68/68 passed in 7.12s**.
- P4.1 corrected full `simulation/tests` run `37326902078`:
  **686/686 passed in 2034.19s (33:54)**; helper differed from the product
  candidate for that gate only by its workflow file.
- P4.2 standalone identity prerequisite run `37347927599`:
  **86 passed in 11.58s**.
- P4.2 owner-transfer affected gate `37385479617`: green.
- P4.2 cache-pressure/reactivation gate `37386284134`: green.

The accepted identity model uses versioned incarnation/occurrence authority,
weak runtime bindings, exact current sharing, generation pins, stale-session
rejection and atomic hybrid publication.

## Migrated archive families

P4 migrated the following history-growing/current-state families behind checked,
versioned lazy adapters while preserving their existing domain APIs:

- people;
- magic aspirations, resources and owner index;
- material lots/items and active/index buckets;
- currency wallets and treasuries;
- souls;
- advancement paths;
- institution magic records/notices/applications;
- transmissions and motives;
- social edges/adjacency/partnerships;
- skills;
- lineage nodes;
- genealogy parents/children;
- community memberships;
- sharded lineage children/child edges.

Representative final gates:

| Slice | Focused | Scaling / bounded proof | Affected |
| --- | --- | --- | --- |
| Souls P4.5 | `37396222483` — 20/20, 11.91s | 33 open reads at 1k/10k; 1 soul point read; 3 payload writes | `37397887371` — 187/187, 179.89s |
| Advancement P4.6 | `37400414548` — 33/33, 10.75s | `37400542367`: 33 open reads; 1 point read / 1,963B; 3 writes / 2,109B | later affected P4 matrices include advancement |
| Institutions P4.7 | `37403787799` — 9/9, 0.94s | `37403872554`: 33 open reads; fixed queries 5 reads; 3 writes | `37404013691` — 241/241, 207.02s |
| Scalar archives P4.8 | `37405892154` — 11/11, 2.70s | `37405979599`: 33 open reads; fixed work 3 reads; 3 writes | `37408783568` — 252/252, 212.94s |
| Social P4.9 | `37411175904` — 6/6, 1.08s | `37411269270`: 33 open reads; fixed work 4 reads; 3 writes | `37411415039` — 266/266, 145.29s |
| Skills P4.10 | `37412669585` — 8/8, 27.49s | `37412803730`: 33 open reads; 1 point read / 246B; 3 writes | `37413133031` — 279/279, 302.41s |
| Lineage nodes P4.11A | `37414711945` — 9/9, 38.09s | `37415118779`: 33 open reads; 3 ancestor reads; 3 writes | `37475477424` — 298/298, 346.98s |
| Genealogy P4.12 | A 9/9; B 12/12 | A/B both flat 1k→10k | `37496024723` — 306/306, 301.85s |
| Communities P4.13 | `37500040627` — 16/16, 35.91s | `37500284618`: 35 open reads; 1 person-query read; 3 writes | `37500470378` — 312/312, 379.90s |
| Lineage children P4.14 | `37507068538` — 10/10, 4.19s | `37507255485`: 33 open reads; bounded edge add/save | `37510836757` — 319/319, 351.07s |

P4.14 also has targeted overlay regression `37510624230`:
**13/13 passed in 6.72s**, proving pre-save reads of modified unloaded lineage
buckets use the current overlay count.

## Final residual eager inventory

Current-candidate residual run `37513319855` passed.

At 1,000 rows:
- **1,033 payload reads / 250,424 bytes**.

At 10,000 rows:
- **10,033 payload reads / 2,383,458 bytes**.

The only substantial eager family is `world.agency.actions`:
- 1,000 rows / 233,676 bytes;
- 10,000 rows / 2,366,678 bytes.

That family is explicitly capped at 50,000 records, so it is bounded rather than
an unbounded-history P4 blocker. Every other residual row is fixed metadata or
small current counters/snapshot descriptors. The prior unbounded
`world.lineage.children` payload is absent from the eager residual inventory.

Identity metadata remains versioned for lazy families and is intentionally not
counted as eager decoded payload. Ordinary open reported `identity_live=0` in
both residual fixtures.

## Recovery / lifecycle / compatibility evidence

The affected matrices above repeatedly include the accepted P1/P2/P3 storage,
identity, failure, lifecycle and session-open regressions. Covered behavior
includes:

- atomic old-or-new publication and lost-acknowledgement resolution;
- generation-pinned checked reads;
- stale writer/session rejection;
- interrupted-save recovery and source-preserving recovery copy;
- bounded clean caches and retained-alias reactivation;
- exact mutable sharing/incarnation preservation across lazy/lazy and
  lazy/eager ownership;
- materializing detach back to portable plain World state;
- checkpoint roundtrip after detach;
- exact existing gameplay/domain APIs and ordering.

## Integrated P4 closeout gate

Integrated full-suite run `37513490616` executed:

`PYTHONPATH=simulation:. python -m pytest -q simulation/tests`

Result: **834 passed, 1 failed in 2558.52s (42:38)**. The single failure was
`test_cross_boundary_aspiration_alias_mutates_without_payload_load`. It exposed
a real cross-lazy identity bug: an `IndexedRecord` first materialized through a
different lazy owner (an aspiration through a wallet alias) retained identity
but lacked the canonical lazy table's mutation callback, so a field edit could
be omitted from save planning.

The fix is frozen in product/test head
`e4752e306d30dcff41be1cc17ddc6e63004646a3`. It restores mutation routing
from the identity registry without forcing the canonical payload load and adds
the analogous Person-before-load regression.

Post-fix evidence:
- focused helper `37520218759`: **2/2 exact regressions** in 0.88s and
  **57/57 affected people/aspiration/currency/identity tests** in 49.32s;
- final landed-head gate `37520547147`: **2/2 regressions** in 0.91s,
  canonical 10-year smoke green, **138/138** recovery/lifecycle/compatibility
  tests in 113.71s, and P5 short integrated continuation green with the expected
  year-10 digest/event authority.

Per owner direction, the 42-minute 835-test suite was **not rerun merely to
recheck this localized fix**. The 834 previously passing tests remain evidence
on the immediately preceding product bytes; the localized affected/final-code
gates above are the post-fix substitution. Astra must decide at final review
whether this evidence substitution is sufficient for the literal final-full-
suite completion-plan bullet; do not represent a second 835-test green run.

## Remaining limitations / boundaries

- `world.agency.actions` remains eager but is capped at 50,000 rows.
- Explicit full iteration of a requested sharded lineage-child bucket may scale
  with that bucket, by design; point membership/add/remove and ordinary open are
  bounded.
- P4 does not itself provide long-horizon release evidence. That belongs to P5.
- No claim here authorizes merge, Stage 1, balance changes or checkpoint-default
  replacement.
