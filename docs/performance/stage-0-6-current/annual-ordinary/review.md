# Annual ordinary save package: consolidated closure register

One independent whole-package review, `annual_ordinary_review` (Astra/high),
against parent `eefcd63062298478a15bedf41cc77ed2d723bb20`. The reviewer found
the five items below. This register includes all findings, including Minor.
No second review or separate CI run per finding is used.

| ID / origin | Finding | Concrete correction | Evidence / status |
|---|---|---|---|
| R1 P1, independent review | Declined adoption proof and full audit both allowed omitted derived threshold counters to commit. | Certify source markers and all counter markers together; require coverage of every source/bucket/scope edit before either incremental route. Full audit recomputes exact global and settlement counts, preserving declared empty scopes. | `review-raw/adoption_budget_probe.*`, `adoption_full_audit_probe.log`; `r1-red.*` reproduces both publication defects. `r2-green.*`: both defects and valid exhausted-budget/new-scope/deletion fallbacks pass. Closed. |
| R2 P1, independent review | Empty identity projection was treated as primitive authority; invalid genealogy tuple plus matching header committed. | Limit primitive value admission to explicitly registered scalar-map families. Shared full/incremental genealogy validation requires exact integer keys and exact integer tuple members. | `review-raw/genealogy_scalar_probe.*`; `r2-red.*` records corrupt durable generations in both routes; `r2-green.*` rejects both inside the transaction and verifies valid retry/reopen. Closed. |
| R3 P2, independent review | Ordinary metadata could exceed the budget before integrity rejection; the earlier value reader fetched overlapping predecessor bodies. | SQL bounds checksum text and projects numeric columns only as integers in both ordinary readers. Retirement query endpoints use typed SQL and interval validation. Reject overlapping value predecessors before any source body read; retain aggregate byte allowance. | `review-raw/ordinary_metadata_probe.*`; `r3-red.*`: nine failures (eight metadata cases and value overlap), one existing insertion pass. `r3-green.*`: 13 passes including both reader paths and catalog retirement. Closed; final combined verification below. |
| R4 P2, independent review | Packed append reprojected the old prefix; ordinary plans and singleton recognition materialized projections before checking limits. | Value classifier routes changed packed lengths before projection. Project only new actions at absolute owner paths. Forest collection stops at remaining cumulative limit plus one sentinel; ordinary plans reserve the budget during production. Scalar singleton recognition stops after two projections. | `review-raw/r4-red.*`: all three bounded-work tests fail. Initial `r4-green.*` exposed a local helper-name collision; corrected before final ordinary/regression runs. `ordinary-final-verified-tests.*`: all60cases pass. Closed. |
| R5 Minor, independent review | Unused imports, local and row constant remained after owner-edit extraction. | Removed `_digest`, `OrderedSeekMap`, the unused stage `codec` local and `MAX_ROWS`; component module remains the row-limit authority. | Source diff and final static checks. Closed. |
| A1, author supplemental fresh-process test | Two ordinary event-data paths had one catalog incarnation but reopened as separate inline objects. Reproduced on the green parent as well. | Explicit proof open stitches only resident mutable event paths using accepted catalog owner labels and the existing registry/family binder; compare bytes before installing a canonical peer. No sealed archive body read or new identity authority. | `supplement-tests.*` retains the failure; `review-raw/event-alias-parent.log` proves pre-existing behavior; `supplement-green-tests.*` passes fresh-process digest, sharing and detached motive roots. Same review's closure probe also passes cross-event sharing, mutation, save and reopen. Closed. |
| A1.C1, same independent review closure | An injected alias admission failure closed the store while leaving its durable publisher pin. | Run normal session teardown when repair fails, preserving the original exception. | `review-raw/alias-cleanup-red.*` reproduces the leak; `alias-cleanup-final.*`: real pin release passes. Closed. |
| A1.C2, same independent review closure | Sorting a caller-owned occurrence spill rematerialized it and did not close it. | Keep bounded tuple sorting; stream spilled occurrences in parent-before-child depth passes and close them in finally on success and failure. | `review-raw/alias-cleanup-red.*` reproduces the unclosed success spool. Failure-case test initially used an incorrect class import and then assumed an install on already canonical genesis data. The final test injects a streamed-walk failure. `alias-cleanup-final.*`: success/failure spill cleanup and pin release, 3 passed6.81s. Closed. |

Raw review scripts and logs are preserved under `review-raw/`. The initial
`r1-green.log` is a collection error caused by a missing `PYTHONPATH`, not a
runtime verification; the corrected `r1-green-verified.*` is retained separately.
The first fallback-positive tests expected one audit, while the publisher
checks parent and successor; `r2-red.*` retains that test-assumption error.
Final tests require the audit route without imposing that incorrect count.

Final ordinary, affected persistence, clean-source year, launcher and hosted
results are recorded in `closure.md`. Hosted completion remains a separate
gate until both jobs for the published commit finish.
