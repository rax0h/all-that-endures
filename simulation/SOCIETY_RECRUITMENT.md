# Society recruitment through real Iron completion

## Scope and authority (2026-09-21)

The owner accepts that very few Diamonds may be appropriate and requests
recurring new Irons rather than further upper-rank tuning. Gold/Diamond
progression is unchanged in this revision. Startup time is to be assessed
against character creation; no replacement numeric deadline was specified.
The existing 120-second CI guard is retained and failures remain visible.

EXTEND the existing paid-apprenticeship authority, not a parallel school or
annual population controller. Prior research-branch implementations were not
imported. The original PR #5 and main remain untouched.

## Behavior

- Each existing Society branch retains up to its existing three funded
  public-work trainee places. Intake uses existing commitment/preparation
  priorities; enrolled people retain their place rather than being reselected
  against everyone every year. Enrollment needs actual funding and useful work.
- Existing four-Iron wages require a positive infrastructure-maintenance
  result. No wage or production rate changes. A funding interruption stops
  wages, not ownership or use of resources already acquired.
- The Society helps willing trainees use their own resources and buy real
  local public stock or another resident's surplus. The existing public sale
  and private transfer authorities own transactions; normal prices, funds,
  relationship gifts and provenance apply. No desired item is generated.
- Existing compromise/selectiveness controls willingness through a separate
  deterministic stream. An accepted session may consume every suitable owned
  or affordable resource required by the path; there is no annual stone cap.
- Canonical Unranked-to-Iron advancement emits graduation linked to enrollment
  and the actual body transition. All four essences and twenty abilities must
  exist. Course time, wages and attendance cannot confer rank. Graduation
  releases a place; normal Society membership assessments remain separate.
- Death, migration and withdrawal release active places with a departure
  record. No automatic successful graduation, minimum class size or yearly
  population target exists. This is local procurement, not remote delivery.

## State, archive and cost

Only active person-to-enrollment-event mappings are retained on each branch.
Historical enrollments, work, departures and graduations remain ordinary
causally linked events. They survive archive export; inactive trainees are
removed from the hot state. Checkpoint schema 8 explicitly rejects older
schemas rather than silently altering checkpoint digests.

Procurement builds one ephemeral local offer list per branch/year, lazily when
a funded trainee needs it. It uses owner/inventory/selection indexes, shares
offers among at most three trainees and rechecks ownership and need at sale.
There are no per-person history scans. Annual recruitment counts are computed
after simulation and include people who later advanced or died; final living
Iron counts alone cannot measure renewal.

## Short validation

Seed 843000, mature start, 300 years. Baseline is
`ec71dfe967edb863159420540e623148ff9714c1`.

| Measure | Baseline | Cohort implementation |
|---|---:|---:|
| Simulation seconds | 20.138353931 | 19.082621979 |
| New Irons, years 201–300 | 123 | 134 |
| Years with no new Iron, years 201–300 | 30 | 25 |

The changed run has 76 new Irons in the final fifty years, including six years
without a new Iron. Runtime is a short local observation, not an isolated
speedup claim or millennium result. Funding, local stock and willingness still
limit throughput; the program does not yet produce a class every calendar
year. No further capacity/price/progression calibration was made to force that.

Targeted tests cover paid real work, unfunded intake, persistent places,
death release, real twenty-ability graduation, next-generation intake,
private/public payments and conservation, sixteen-stone use in one session,
archive causal links and checkpoint replay. Full validation is recorded below
when complete. The deterministic world changes intentionally through these
transactions, completions and subsequent lives, as well as new branch state.

Local focused validation: 28 tests passed. The full suite initially passed 169
tests with only the expected previous digest assertion failing; indexed and
archival population-query histories agreed with each other. The 100-year
founder golden was deliberately updated to
`b061f5632124348ce953d644c7c0926abfca1f4e9313c1b5f74f8078c7611494`,
with the reason recorded in the test. Both normal smoke checks passed.

## Final canonical validation

Implementation `887ba8b2caf7962e28a36114d16ad952849cb48f`,
[Actions run](https://github.com/rax0h/all-that-endures/actions/runs/35550906817).

- **170 tests passed in 118.14 seconds**; both smoke checks passed.
- Seed 843000 / 1,000 years: **131.737358910 seconds simulation**.
  The unchanged 120-second CI guard failed; all correctness/audit steps passed.
  The owner has relaxed the original cap in principle, but no new numeric
  character-creation budget has been specified.
- Living population **1,525**; essence users **732**; complete paths **208**.
  Body ranks: **33 Iron / 4 Bronze / 37 Silver / 132 Gold / 2 Diamond**.
  Gold/Diamond progression rules were not changed.
- **1,305 actual Society graduations**, from 1,900 enrollments, with 580
  departures and 15 current trainees. This reconciles active course state.
- Years **901–1000: 148 new Irons, 18 years with none**. Final fifty years:
  **68 new Irons, nine years with none**. This is recurring renewal, not yet
  a graduating class in every calendar year. No guaranteed class was forced.
- Resources **95,530 total / 17,635 unused**. Society notices **3,064 resolved /
  9 assigned / 1 open**. Treasury retains 3,963 Iron; 13,934 paid work events.
- Chronological audit **valid, zero violations**, including all 134 living
  Gold/Diamond histories and currency/treasury reconciliation.
- Digest `8dd36dec4d5dfd3b0f1e8d5c2b716b4547f51c4765e7fa0e98e18823145175dd`.
- Archive export **120.471793382 seconds**, **1,594,798,080 bytes**, outside
  simulation time; logical checksum
  `2044fca276331b90ded9f8ecf8a118c41cbc7622bf622bc59ec9303871dc7ba0`.

Runtime is lower than the prior 194.30-second run, but both history and runner
performance differ; do not attribute the full difference to this feature.
The complete year-by-year counts and machine-readable results are in
`society_recruitment_validation.json`. This completes the bounded cohort
implementation, not all Stage 0.5 calibration: participation is 58.70%, the
lower-rank population remains thin, and recruitment still has empty years.
The old report remains historical. No additional millennium or tuning loop
followed this result. Original PR #5 and main were verified unchanged.
