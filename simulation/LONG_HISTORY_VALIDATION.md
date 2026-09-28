# Continued-world validation — 2026-09-27

**Decision B: Stage 0.5 is not yet structurally ready to freeze.** Current-state
indexes and cold event storage are implemented; inventory-query growth and
whole-world checkpoint costs remain measured architectural blockers. No merge.
No Stage 1 work, rank quotas, prices, progression or recruitment retuning.

## Current tested candidate

Implementation: `ea2f6125bb9f4bd5e8e20b020a0da88543822160`.
[CI 36278414000](https://github.com/rax0h/all-that-endures/actions/runs/36278414000)
is green: **180 tests passed in 254.08 seconds**, both smoke checks passed,
and the full canonical chronological progression/currency audit passed with
zero violations. Local full suite: 180 passed in 215.23 seconds.

Canonical seed 843000, mature initialization, 1,000 years:

| Measure | Result |
|---|---:|
| Simulation | 248.281146118 s |
| Living / essence users / complete paths | 1,500 / 691 / 209 |
| Iron / Bronze / Silver / Gold / Diamond | 42 / 3 / 43 / 121 / 0 |
| Resources / unused | 94,850 / 17,986 |
| Society notices resolved / assigned / open | 3,029 / 6 / 3 |
| Diagnostics / hashing / causal validation | 105.865 / 66.219 / 18.392 s |
| Archive export / bytes | 257.119 s / 1,567,444,992 |

World digest:
`d2e8c476174d5497da24dfe6fa79ed6ad94fb22b3b3b2e1b15f9f5064a630584`.
Archive logical digest:
`6e70d81037460d67c5c5abc69bd35f192b18dc310ee518f239cdc4813a435d55`.
Both match the preceding `1eb8733...` candidate, whose CI millennium took
283.983 seconds. Runner variation prevents attributing that timing difference
solely to the follow-up. This is not a claimed improvement over the older
accepted 131.74-second cohort run. The owner's revised 120-second goal is
reported as a warning; all correctness failures remain fatal.

Zero living Diamonds in this canonical seed is reported, not tuned away.
The fixed-seed history changed from the earlier cohort candidate because a
pre-existing checkpoint/set-order defect was corrected, not because progression
probabilities or constraints were changed.

## Implemented architecture and determinism

Mutation-aware, rebuildable indexes separate routine living/current queries
from historical people, households, applications, notices, threats, wars,
inquiries and estate ownership. Lossless compressed event segments retain
stable IDs, payloads and cause links with bounded resident event objects.
Canonical hashing and archive export stream history. No causal truth is deleted.
See [LONG_HISTORY_ARCHITECTURE.md](LONG_HISTORY_ARCHITECTURE.md).

The unchanged baseline diverged at year 121 after saving at 110: low-skill
crafting sampled Python set iteration order. Stable-ID order-statistic
selection fixes that while preserving eligibility, uniform probabilities and
RNG draws. The candidate passed a 500-to-520 checkpoint replay with digest
`073c19ae709e5906293e15e6b4c005c13ee6f0e2f0da97c87df1189c0ac73d35`.
A sparse-ID church fixture exposed another set-order RNG defect; stable
follower order, material summation and archive member ordinals now have
regression tests. Compressed/plain archive equivalence is also tested.

Before the material ordering correction, storage/index-only replay of the
saved seed-843010 world through year 1020 exactly matched the baseline digest:
`db0537187e6099c77e8cd39ad4e1cb914e9f01e31fe0d9a629f8e8f6eb9f4dfc`.

## Long continuation

The retained seed-843010 year-1000 world from `13e9e5a...` was continued with
`1eb8733...`. This is not a fresh canonical run of the follow-up implementation.
No SQLite archive was generated at milestones. The first execution reached
2750 before interruption; its year-2000 checkpoint was restored with integrity
verification. All 16 semantic snapshot fields matched at 2250, 2500 and 2750;
this is not a full-world digest comparison at those milestones.

| Years | Simulation seconds | Living at end | Unused resources |
|---|---:|---:|---:|
| 1001–1250 | 74.698 | 1,425 | 27,116 |
| 1251–1500 | 82.056 | 1,407 | 33,285 |
| 1501–1750 | 82.845 | 1,399 | 39,537 |
| 1751–2000 | 86.550 | 1,436 | 45,839 |
| 2001–2250 | 111.854 | 1,418 | 52,479 |
| 2251–2500 | 120.327 | 1,422 | 59,119 |
| 2501–2750 | 122.418 | 1,428 | 65,637 |
| 2751–3000 | 122.526 | 1,462 | 71,959 |

Years 1001–2000: **326.148 seconds**. Years 2001–3000: **477.125 seconds**.
Rows span original and resumed executions; contention/scheduling was not
controlled. These exclude inspection, restore, hashing and profiling. They do
not establish flat continued-world cost. No 10,000-year run was attempted.

At 3000: 748 living essence users, 248 complete paths, **28 Iron / 6 Bronze /
52 Silver / 135 Gold / 27 Diamond**. The final 250 years produced 343 actual
Iron transitions and 340 Society graduations; 61 years had no new Iron.
All milestone state/configuration/ability, denomination conservation and
new-event cause-link checks passed. These lightweight checks are distinct
from the full chronological CI audit.

All **3,618,351 events** remained available; **13,871 event objects** were
resident including the read cache. Sealed segments held 3,612,672 events in
159,481,338 compressed bytes. Non-event historical records still reside in RAM.

## Measured remaining blockers and smallest correct next action

1. **Growing available-stock queries.** Years 2751–3000 spent 30.223 seconds in
   Society careers, 22.110 in magic ecology, 21.832 in magical civilization and
   19.743 in agency. The 3001–3010 profile spent 2.701 seconds in trainee resource
   purchasing (150 calls), 1.543 in circulation, and called `_wants` 478,010
   times. Cumulative times overlap. Society rebuilds/sorts its shared offer list
   every branch/year; available stock is genuine property, not disposable history.
   Next: incremental ordered offers by owner/location, compatibility and price,
   updated through existing creation/transfer/consumption authorities. Preserve
   exact tie ordering, paid transactions and outcomes with differential tests.
   Dead-owner inventory accumulation is not the demonstrated cause.
2. **Whole-world persistence and resident non-event archives.** The year-2000
   checkpoint was 421,493,693 bytes; save took 127.323 seconds and integrity-checked
   restore 156.841 seconds. At 3010, hashing alone took 188.563 seconds and the
   checkpoint was 646,149,733 bytes. The ten-year profile also incurred a 5.114-second
   full collection after 10.449 seconds in annual steps. Next: paged archival
   payloads and incremental checkpoint pages/manifests, preserving stable identity,
   canonical recovery and legitimate later updates. Do not freeze records just
   because they are old. This is not yet an interactive autosave architecture.

Final observed year-3010 digest:
`e031feb5546be11e29f5ec2fac7dd6051e21abdea2d82879cdb7128e9d87a923`.
The local logs/checkpoints were subsequently lost in a workspace reset; their
observed measurements are transcribed in `long_history_scaling_validation.json`.
Canonical CI evidence remains independently accessible at the linked run.
Do not claim those lost checkpoints are still available for replay. Future work
should retain a durable trusted late-world fixture before further long runs.

Main, PR #5 and discarded experimental branches were not modified. The
material-life design updates on the true branch head were preserved. Stage 1,
real-time scheduling and a separate gameplay world were not introduced.
