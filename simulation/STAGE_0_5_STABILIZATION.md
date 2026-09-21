# Current scope: Society recruitment (2026-09-21)

The owner now accepts that two Diamonds may be reasonable and asks to hold
progression fixed while supporting recurring new Irons. Runtime should be
assessed against character-creation time; no new numeric CI limit is specified.
See SOCIETY_RECRUITMENT.md for the focused cohort implementation and validation.
The prior results below are historical, not measurements of the new candidate.

# Prior validation: Stage 0.5 remained unfinished (2026-09-21)

Tested implementation: `0147717a773f412fd356cf583ef870c137d8a1e8`.
[Actions run](https://github.com/rax0h/all-that-endures/actions/runs/35529400618).
This report supersedes the historical candidates below. No merge is authorized.

- **165 tests passed in 168.68 seconds**; both normal smoke checks passed.
- Canonical seed 843000 / 1,000 years: **194.300367483 seconds**.
  The unchanged 120-second performance gate **failed**.
- Living population **1,488**; essence users **733**; completed four-essence,
  twenty-ability paths **175**. Body ranks: **37 Iron / 8 Bronze / 26 Silver /
  102 Gold / 2 Diamond**. The other 558 essence users remain unranked.
- Chronological archive audit: **valid, zero violations**, including all 104
  living Gold/Diamond histories and wallet/treasury reconciliation.
- Resources **95,863 total / 17,045 unused**. Society notices: **3,046 resolved /
  12 assigned / 5 open**. Treasury retains **302 Iron**; 13,934 paid apprentice
  jobs occurred. Adult magical participation is **60.63%**, below the mature
  observational expectation; lower-rank populations also remain thin.
- Digest: `480d44a9b1eff0bfd6d160cb399e094683a87d408fdc1485054960bdd36f1122`.
  This intentionally differs because the Gold workload changed; no golden
  digest was refreshed to conceal a discrepancy.
- Archive: **1,589,997,568 bytes**, **230.972650663 seconds** separately timed.
  Logical checksum:
  `620b116da2d54a87c80c1097b004e92b07abc9f3cb62cc99d18e55e6cb75f51b`.

## What the final measurement establishes

The intermediate workload does **not** meet the requested roughly 20–25 living
Diamonds. It produces two legitimate Diamonds, not a validated population
calibration. The observed sensitivity (65 at 12–18 sessions, zero at 6–10, two
at 9–14) reflects the interaction of whole-path development time, mortality
and subsequent ageless survival. These different histories are not a controlled
linear interpolation of rank populations.

Both current Diamonds have all twenty Diamond abilities and complete permanent
configurations. Person 4337 reached Gold in year 397 (age 136), then Diamond in
733 (age 472): 336 Gold years. Person 5030 reached Gold in 440 (age 144), then
Diamond in 762 (age 466): 322 Gold years. Their final wallets respectively
contain 3,162 and 2,531 Diamond coins; those balances are recorded history,
not rank-granted bonuses. Full event-linked transitions are in the JSON report.

Exact query reuse reduced runtime from 208.60 to 194.30 seconds between the
latest candidates, but the workload change also changed the history; only the
shared-checkpoint comparison below isolates the optimization's equivalence.
There is no evidence that the existing gate is impossible, and it has not been
raised. Stage 0.5 is **not ready for freeze/merge**: runtime, Diamond calibration,
participation and rank distribution remain open. No additional millennium or
calibration loop was launched after this result. Original PR #5 and main remain
untouched; implementation and measured failures are retained on draft PR #14.

# Measured workload correction and exact computation reuse (2026-09-20)

The isolated restoration at `955173af257d6c488edd1b6f77d85b044f9092e6`
passed 164 tests and both smoke checks. Its canonical run took 208.6005498
seconds, with 35 Iron, 2 Bronze, 41 Silver, 91 Gold and zero Diamond.
The chronological archive audit was valid with zero progression/currency
violations. Digest: `c687072d08c2a1056610976192cc49e49ba0740dc7ed9fb28add70cbd161be76`.
This disproves the claim that corrected selection alone makes 6–10 sufficient.

Year-500 inspection found old Gold users with all twenty mastery gates ready
but only roughly six of ten levels accumulated after about 300 Gold years.
A constant-effort diagnostic across 36 established Gold users projected a
median Diamond age of 645.5 with the lower allocation, versus 503.5 at the
intermediate `9 + int(5 * ambition)` allocation. Existing Gold senescence starts
around age 406.25; no mortality change is made. The intermediate 9–14 allowance
is a documented workload approximation, not a population controller or canon.

Exact optimizations skip practice only when every ability is already at its
body-imposed ceiling; these calls previously returned without changing state.
Annual body-rank queries cache their validated result and invalidate on every
normal configuration/rank mutation; caches do not enter checkpoints. Society
application queries are shared across settlements. Service matching rejects
unpayable requests and irrelevant abilities before repeating identical checks.
Resource matching reuses current eligibility and stock state.

A replay of years 501–510 from the same saved world retained the full digest
`b853a78edafc3e5abad0cd72fdc10509f8362cddc99f1a243145c35af4a48ac5` and
415,422 events, taking 4.57 seconds versus 5.14 in the reference. These short
measurements include final collection and are not canonical gate results.
42 focused source tests passed; a compiled-module probe also preserved the
digest and passed 16 tests, but showed too little additional speed to justify
a new build dependency. No compiler dependency or generated binary is shipped.
Final validation of the combined candidate is recorded above; it did not pass.

## Historical isolated Diamond workload restoration

The historical isolated candidate restored only the Gold professional session allowance
from `12 + int(6 * ambition)` to `6 + int(4 * ambition)`. Corrected weakest-first
selection and missing-evidence scheduling remain intact. Ability rates,
mastery requirements, economy and performance implementation are unchanged.
Targeted tests preceded its canonical validation; the measured result is recorded above.

The earlier zero-Diamond result did not isolate workload from the scheduling
bug, so it did not justify increasing the allowance. The 65-Diamond experiment
and its measured failures below are historical, not this candidate's results.

# Prior Stage 0.5 validation: not ready

Tested implementation: `820241efe748f29f2d0c827a70487fb8391bb2dc`.
[Actions run](https://github.com/rax0h/all-that-endures/actions/runs/35512882584).
The code is preserved for review on PR #14; PR #5 and main remain unchanged.
This is a failed candidate, not a completed stabilization or baseline freeze.

- **164 tests passed in 169.72 seconds**, including checkpoint/resume,
  environmental selection, progression, currency and cache equivalence tests.
  Both normal smoke checks passed; causal integrity passed.
- Canonical seed 843000 / 1,000 years: **218.470726270 seconds**;
  the unchanged 120-second gate failed. Digest:
  `18faf1646c7f81905d69c2a1ccd8df5688db61ee5d2861945d69870b6f0c025c`.
- Living population 1,514; essence users 773; complete 20-ability paths 243.
  Body ranks: **41 Iron, 7 Bronze, 42 Silver, 88 Gold, 65 Diamond**.
  Incomplete users remain unranked. No assigned rank quotas were used.
- Resources: **96,556 total / 19,768 unused**. Society: 3,075 resolved,
  6 assigned, 4 open notices. Paid apprentice jobs: 13,934; final treasury
  retains 100 Iron coins. Low-denomination renewal now works in this run.
- Full chronological archive audit: **valid, zero violations**, including
  every living Gold/Diamond and all wallet/treasury reconciliations.
- Archive export: **230.494510852 seconds**, **1,569,394,688 bytes**,
  outside the simulation timer. Logical checksum:
  `c72adefc954a3843050563f0330bb6d511afec6bdcc77d347f39fa60c872be41`.

| Seed / years | Living | Users | Complete | Iron / Bronze / Silver / Gold / Diamond | Resources / unused | Resolved / assigned / open notices | Simulation seconds |
|---|---:|---:|---:|---|---|---|---:|
| 843001 / 300 | 1,462 | 498 | 136 | 56 / 7 / 39 / 34 / 0 | 15,224 / 1,437 | 527 / 0 / 2 | 26.725458720 |
| 843002 / 300 | 1,369 | 479 | 145 | 63 / 11 / 31 / 40 / 0 | 18,273 / 2,114 | 584 / 4 / 2 | 23.801479974 |

The shorter runs passed causal-integrity checks; they did not export archives
and therefore do not constitute separate chronological currency audits.

## Remaining measured failures

Focused training fixed an actual scheduling defect: sorting weakest abilities
and then shuffling the whole list discarded the priority, allowing already
advanced abilities to consume scarce sessions. Solved response experiments also
repeated while waiting for reflection. The corrections retain every mastery gate.
However, increasing the session budget before isolating that defect was not
justified as final calibration. Under the tested 12–18-session approximation,
the 65 living Diamonds completed Gold→Diamond in 251–315 years and accumulated
as ageless survivors. This exceeds the intended rarity. The approximation is
not accepted as final; no further blind constant tuning was performed.

Measured canonical subsystem totals are approximately 63.0 seconds agency
(including rank training), 49.6 magical civilization, 27.2 magic ecology and
20.8 Society careers. A separate 500-year diagnostic profiled its final ten
years: 10.24 million calls in 5.65 profiler seconds, including 1.21 seconds
final cyclic collection; leading step costs were agency 1.30, magical
civilization 1.16, magic ecology 0.68 and Society careers 0.40 seconds.
Current-state queries and training still cost too much at the larger practitioner
population. The profile is not a performance-gate result or another millennium.

The audit proves progression legality, not desired rarity, sustained initial
75–80% participation, differentiated occupations, or sufficient performance.
The initial participation still falls sharply by year 100 before recovering to
62.3% of eligible adults at year 1000. Stage 0.5 remains unfinished. Do not merge.
Machine-readable measurements and real linked progression examples are in
`stage_0_5_validation.json`; earlier experiments below are historical.

# Earlier stabilization repair

This section records the repair rationale before the completed validation above.

- Coin farms allocate their existing value-limited annual cultivation capacity
  to actual outstanding Society contracts and two payrolls for eligible
  apprentice places before using remaining capacity for native-tier coins.
  Output is physical cultivated supply, not conversion of existing coins or a
  rank wealth grant. Its denomination mix, production ceiling and half-harvest
  protection levy are recorded. Rank-tier value equivalence for cultivation
  yield is an explicit ATE economic approximation, not asserted source canon.
- Gold training has twelve to eighteen focused sessions per annual career allocation,
  varying with existing commitment. The earlier twenty full allocations let a
  single professional develop twenty advanced abilities in parallel without a
  finite workload. Ability rates, readiness, all-twenty body gates and genuine
  mastery proofs remain intact. This is a pacing approximation, not a rank quota.
- Exact derived inventory/selection caches invalidate on ownership, consumption
  and demand changes. They are excluded from checkpoints. Paid-demand heaps
  replace repeated buyer scans; ties and transaction semantics are unchanged.
- Disposable training sessions validate configuration once and incrementally
  track ability ranks, including body advancement mid-session. Direct practice
  remains independently authoritative; differential histories compare both.

The previous candidate also ran in GitHub Actions: **135.194282791 seconds**,
with 154 unit/integration tests passing. Its local 248.881-second measurement
below came from a slower execution environment. Both failed the unchanged gate.

## Revision after the first repair validation

Commit `8003e356` passed 160 tests and smoke checks, but measured
171.321866434 seconds in Actions. Its final ranks were 42 Iron, 5 Bronze,
44 Silver, 76 Gold and zero Diamond, with 167 complete paths. It did fix
renewal: 13,934 paid apprentice jobs, 3,068 resolved notices, 108 Iron in
treasury. The six-to-ten-session Gold limit was too restrictive for actual
lifespans; it is superseded by twelve to eighteen focused sessions.

Focused sessions now select the weakest unfinished abilities before shuffling.
Already advanced abilities cannot waste these sessions. Controlled experiments
stop once their needed evidence exists or a fitted, fully sampled model is
waiting for integration; this grants no reflection, proof or progression.
Actual practice/reflection must still make the next experiment meaningful.

Performance corrections remove duplicate rank/configuration checks and repeated
market queries. Cyclic collection runs on a bounded 25/250-year schedule rather
than repeatedly traversing the live archive after allocation thresholds; reference
counting stays active. Final collection is included in simulation timing and the
caller GC state is restored, including after exceptions. History is preserved.

CI now performs the archive audit even after a performance failure and fails
if either check fails. The 120-second gate is unchanged.

## Earlier continuation from preserved PR #5

Authority: `docs/IMPLEMENTATION_ROADMAP.md` and `docs/ASTRA_STAGE_0_5_UPDATE.md`.
Production code starts at `fbfbe58ef1e18fa35eb4d63af98cd66e00f64c4f`.
Current design-only main `3cca62055f291f76c221cdf8f280cd3b4c46777b` was merged
into this separate continuation branch. No implementation from PRs #6–#12 was
imported. The original PR #5 branch remains unchanged.

## Classification and implementation

- KEEP: all twenty independent ability gates, mastery/taint rules, progression
  rates, ordinary income, prices, resource ownership, provenance and coin tiers.
- EXTEND world generation: opt-in `generate_world(..., mature=True)` initializes
  inherited magical education/property through real resource creation,
  absorption and awakening. Roughly 78% adult participation is an initial
  probability, never a yearly controller. Three base essence choices are not
  guaranteed distinct: duplicates stay owned property. Training years since
  adulthood bound inherited stones. No rank is assigned; the same authority
  derives Iron from four essences/five abilities each. No unsupported Gold or
  Diamond founder mastery is invented.
- EXTEND existing field work: a successful annual expedition records up to six
  actual willing participants, each collecting one physical resource. Workers
  participate at most once per settlement/year. Resource identity still comes
  from ecological/resonance selection; no desired item is fabricated and no
  automatic monster-looting ability is granted. Party size and yields are ATE
  approximations. Existing expedition attempt/success rates remain unchanged.
- EXTEND Society economy: a bounded current-person pass buys actual Iron coins
  using funded higher-denomination treasury reserves at par. Sellers retain
  twenty Iron; the Society seeks two annual branch payrolls of working change.
  No denomination is minted or destroyed. No counterparty inventory means no
  exchange. These reserve preferences are explicit economic approximations.
- EXTEND resource-market query implementation: paid-demand heaps reused across
  circulation rounds; updates track absorption, awakening, wealth and transfers.
  Personal gifts still require actual strong attachment. Differential testing
  compares complete histories with the independent full scan.
- EXTEND validator: the explicit 20-ability chronology check now includes Iron.
- DERIVED checkpoint diagnostics: adult participation, path funnel, completion
  within the last fifty years, deceased incomplete users, stock ownership,
  treasury/supply and paid work. No diagnostic controls the simulation.

## Evidence before the changes

PR #5's latest CI: 147 tests passed; canonical 91.5478 seconds; 15 living complete
paths (1 Iron, 2 Bronze, 3 Silver, 6 Gold, 3 Diamond). PR #5's older narrative
report still describes a superseded world; do not use its counts as this baseline.

A local initialization-only diagnostic started with 57 magical adults of 74.
By year 100 it had 16 of 612 and zero unused stock: the first bottleneck was
physical replenishment, not simply access to existing stock. By year 500 it had
30 magical adults of 1,098, six completed paths and 138 unused resources.

The party-harvest diagnostic, before the coin-exchange addition, reached 376
magical adults of 1,001 at year 300, with 36 complete paths and 1,603 unused
resources. This exposed repeated buyer scans in existing circulation; their
replacement is a semantic-preserving index, not a change in buyer selection.

## Compatibility and execution

`generate_world` retains the legacy founding scenario by default for explicit
comparison and existing fixtures. The long-history CLI now defaults to mature
initialization; `--initialization founders` selects the old scenario. Both are
reported explicitly. Initial inherited property is marked as pre-observation
state at archive boundary year zero, not invented intervening history.

Checkpoint schema remains 7: no persistent type was added. Initial state and
later field-work/exchange semantics intentionally change the digest. Replay
requires the same revision and initialization mode. No old golden is silently
reinterpreted as the mature reference.

Stage 1/personhood/language remains deferred. No merge or gold-baseline freeze
is authorized merely by passing the unit suite. Final measurements follow below.


## Canonical continuation result — NOT READY FOR MERGE

Seed 843000, mature initialization, Python 3.12.14. The earlier interrupted
run lost its temporary output when the execution environment reset; this is
the one completed replacement validation, not a calibration sweep.

| Year | Adults | Essence users | Complete paths | Iron | Bronze | Silver | Gold | Diamond | Total / unused resources |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| 0 | 74 | 57 | 11 | 11 | 0 | 0 | 0 | 0 | 550 / 8 |
| 100 | 604 | 73 | 17 | 7 | 1 | 9 | 0 | 0 | 1207 / 19 |
| 250 | 1121 | 422 | 70 | 31 | 2 | 24 | 13 | 0 | 8307 / 376 |
| 500 | 1136 | 548 | 88 | 4 | 0 | 12 | 67 | 5 | 34687 / 6377 |
| 750 | 1133 | 606 | 84 | 2 | 1 | 15 | 16 | 50 | 61626 / 12443 |
| 1000 | 1151 | 649 | 90 | 1 | 0 | 4 | 18 | 67 | 88695 / 19025 |

Simulation: **248.881102717 seconds; 120-second gate FAILED**.
Diagnostics: 0.645 seconds; digest: 44.818 seconds.
Digest: `a561c9039a7096e9746f10bc6bbe36a5200d741ecc7abbe5c8922d5164615c95`.

The digest intentionally changes with mature initial conditions, physical party
harvesting and funded currency exchange. No golden was refreshed.

The full suite previously passed **154 tests in 213.48 seconds** before the
workspace reset. After the final gift-query optimization, the 100-year full
scan/indexed differential test passed. The replacement environment also passed
**12 focused tests in 8.80 seconds**, covering mature initialization, archive
legality, checkpoint replay, exact transfer equivalence, funded exchange and
environmental manifestation; the ten-year all-section probe passed causal
integrity. No progression gate or performance limit was weakened.

### What the run demonstrates, and what it does not

- Replenishment reaches real people: 649 living users and 90 complete paths;
  participation is 56.4% of eligible adults at year 1000. It is not sustained
  at the initial 77% and there is no correction towards that percentage.
- The inherited progression pacing produces **67 Diamonds / 18 Golds** once
  completion is less suppressed. That is not the intended rarity distribution.
  All twenty abilities remain mandatory even for Iron. No quota was applied.
- The Society performed 748 funded change exchanges, but its final Iron balance
  is still **3**. Iron supply stops at 3,086 coins (already reached by year 500).
  Existing farms always select the maximum feasible denomination; exchange can
  relocate finite Iron coins but cannot reproduce them. Paid apprentice work
  barely grows after year 500 (2,404 to 2,450 jobs). There are 2,453 assigned,
  398 resolved and one open notice. This is not a solved renewal economy.
- Party harvesting creates 88,695 resources and leaves 19,025 unused. Every
  collected object has a real participant and provenance, but the six-person
  yield approximation is not yet justified as final calibration.
- Measured simulation costs: magical civilization about 88.42 seconds, agency
  about 49.11 seconds, magic ecology about 36.04 seconds. Late-year cost still
  grows. The new query index preserves semantics but does not restore the gate.
- Initial state does not yet seed higher-rank founders, inherited mastery,
  differentiated magical occupations or a mature stock of tiered money. All
  living users still report the ordinary `labor` occupation. Initial essence
  prevalence alone is not a complete mature civilization.

This isolated candidate is a reproducible checkpoint and diagnosis, **not a
Stage 0.5 completion claim**. Keep PR #5 unchanged. The next bounded decision is
how existing productive institutions maintain low-denomination supply while
producing higher-tier value; counterparty exchange alone is demonstrably
insufficient. Correcting that and measuring progression pacing at sustainable
access must precede a production freeze. Stage 1 remains blocked. Do not merge.

### Completed archive audit

Archive export: **158.971716334 seconds**, **1,337,765,888 bytes**,
separate from the simulation timer. Logical checksum: `4a2332efaf984f9b9459a9f64cfe5e316db7d68514547f09ed7b815c5d5b9f68`.
Chronological validator: **valid=True, 0 violations**, including
every living Gold/Diamond, complete Iron prerequisites, wallet histories and
institutional treasury reconciliation. Causal-integrity validation passed.
Correct chronology does not remedy the calibration or runtime failures above.
