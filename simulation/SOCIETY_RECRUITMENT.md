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
with the reason recorded in the test. Both normal smoke checks passed. CI will
rerun the full suite and perform one canonical millennium/archive audit.
