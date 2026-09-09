# Millennium Simulation Result

Verified on seed `843000` using the current-standard simulation on `main`.

CI: 21 tests passed. The 1000-year run completed successfully with causal-integrity validation.

## Checkpoints

| Year | Alive | Total people | Living households | Practices | Institutions | Laws | Events | Max lineage depth |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 227 | 432 | 44 | 30 | 3 | 3 | 2,124 | 5 |
| 300 | 87 | 692 | 17 | 50 | 16 | 7 | 5,484 | 12 |
| 500 | 63 | 864 | 13 | 92 | 17 | 9 | 7,643 | 19 |
| 750 | 33 | 956 | 4 | 233 | 19 | 12 | 9,329 | 28 |
| 1000 | 15 | 1,006 | 3 | 474 | 20 | 15 | 10,746 | 35 |

Final population by settlement: `{1: 3, 2: 4, 5: 8}`. Settlements 3 and 4 had no living residents.

Final living species population: `elf: 12`, `leonid: 3`. Other seeded species had no surviving members by year 1000 in this run.

Final digest: `6dab2ca4bf2d47d99933884883195301b292c01b17b35bef43786acb401409da`.

## What the test demonstrated

The kernel remains deterministic and causally valid over 1000 simulated years. Genealogy reached 35 generations. Households split, property was inherited, migration occurred, trade transmitted knowledge/practices, institutions formed, laws accumulated, and cultural practices branched historically.

## Calibration failures exposed

This run is not a healthy long-history equilibrium. Population declines from 227 alive at year 100 to 15 at year 1000, living households fall to 3, and two settlements depopulate. Species diversity collapses to two surviving species. This must be treated as a demographic/ecological calibration failure, not a desired result and not patched with a population floor.

Cultural diffusion also becomes too homogenizing: by late history many settlements have the same high-adoption practices. At the same time practice branching accelerates strongly, reaching 474 practices from 25 initial seeds. The current innovation/transmission rules therefore need stronger costs, loss, specialization, compatibility, local utility, institutional capacity and transmission bottlenecks.

Trade and migration are too rare for the intended civilization model: only 7 trade exchanges and 4 household migrations occurred in 1000 years. Knowledge claims remain correspondingly sparse at 7.

## Required next calibration tranche

1. Replace crude birth replacement assumptions with age-structured partnership/reproductive opportunity, household formation, childcare burden and species/rank longevity-aware fertility windows.
2. Add settlement carrying capacity, resource depletion/recovery, disease and food-buffer behavior so population dynamics arise from ecology rather than a single scarcity scalar.
3. Make migration respond strongly to demographic, economic, kinship, climatic and security gradients; support individual and household migration.
4. Make trade routes persistent relationships with repeated traffic, capacity, goods, distance and infrastructure instead of rare isolated exchanges.
5. Give practices maintenance cost, prerequisite knowledge, local utility, institutional support, forgetting/loss and adoption friction.
6. Make cultural transmission person-to-person and institution-to-person, with migrants/traders as carriers rather than settlement-wide copying.
7. Add extinction and settlement-abandonment history explicitly while allowing later recolonization from real surviving populations.
8. Re-run multi-seed 1000-year calibration before attempting the target ~10,000-year history.
