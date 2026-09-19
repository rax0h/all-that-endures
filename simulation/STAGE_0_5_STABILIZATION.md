# Stage 0.5 continuation from preserved PR #5

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
