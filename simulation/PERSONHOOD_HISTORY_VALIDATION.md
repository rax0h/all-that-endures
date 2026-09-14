# Personhood/history foundations: validation and real inspection examples

Base main was verified as `69772ca67858b8660555b4907350443c0f259d79`.
No simulation-semantic or balance changes were made. Existing golden digests were not edited.

## Verification

- Complete existing + new suite: **118 passed in 75.26 seconds** locally.
- New archive/personhood suite after final read-only listing addition: **5 passed in 6.83 seconds**.
- `specific_test.py --seed 843000 --years 10 --section all`: passed.
- 100-year smoke with archive: simulation **1.540294898 s**; expected digest `f6e25615b33e2203af1f9dda4c05079ec880c92fe3a418685ccc86e78d54d42e`.
- 150-year cProfile: before **7.510 s**, after **7.300 s** cumulative `Simulation.run`; identical **19,698,330 calls** (19,698,326 primitive). Timing differences are measurement variation, not a claimed optimization.
- Exactly one canonical millennium run for this implementation, seed 843000, Python 3.12.14, Linux x86_64; `--max-seconds 120 --archive /tmp/ate-personhood-843000-1000.sqlite`.

| Canonical measurement | Result |
|---|---:|
| Timed simulation | 95.919121241 s — PASS |
| Diagnostics | 0.308115898 s |
| Whole-world digest | 14.727314064 s |
| Causal validation | 0.065163074 s — PASS |
| Archive export including index creation/validation | 56.390615043 s |
| SQLite archive size | 638,763,008 bytes (609.17 MiB) |
| People / objective event records | 13,333 / 286,048 |
| Magical resources total / unused | 14,068 / 7,582 |
| Living Diamonds | 18 |
| Adventure Society notices | 2,579 |
| Completed loadouts / living essence users | 40 / 261 |

Canonical digest is unchanged:
`1015bf0f8b0f4d38a376b5d18f2a9299259c400bb745b776eaecc48c743697a4`.

Archive logical SHA256:
`d81a3177c0ac81996c2642bd0327be03e52f48955734c153137747943cafed8e`.

SQLite indexes trade storage for direct queries; the archive includes retained non-aggregate records and avoids repeating full event bodies in each biography. Export cost is not hidden inside the 120-second simulation gate. No additional millennium tuning runs were performed. CI results on the committed head are recorded in the PR.

## An actual life: Person 144

These are recorded facts, not generated biography or inferred emotions. The archive provides no personal name or gender here.

| Year | Evidence | Recorded fact |
|---|---|---|
| 3 | Event 180 | Person 144 born, draconian, Settlement 3, Household 18; parents 80 and 88. Cause: event 85. |
| 21 | Event 842 | Person 73 teaches Person 144 construction. |
| 24 | Event 946 | Partnership formed between Persons 72 and 144. |
| 33 | Event 1430 | Child 334 born to Persons 72 and 144, with partnership event 946 as cause. |
| 35, 36, 44, 50 | Events 1544, 1594, 2104, 2506 | Further recorded children 346, 352, 421 and 483, with the same partnership cause. |
| 52 | Event 2653 | Person 144 inherits following Person 88's death event 2649. Event records wealth 42.463171510988886; do not assume this is a transfer amount rather than the producer's recorded wealth field. |
| 80, 92 | Events 5881, 7864 | Later partnerships with Persons 200 and 741. |
| 107 | Event 10659 | Person 144 dies of natural causes at age 104. |
| 107 | Event 10663 | Child 334 inherits; explicit cause is death event 10659. |

The skill record independently names teacher 73 for construction. Retained craft practice is 31.621073561817475 and level 0.6888056997852268. These are recorded achievements, not intelligence or literacy assessments. Final household 78 must not replace birth household 18 in the reconstruction.

```
python simulation/history_inspect.py ARCHIVE.sqlite person 144 --limit 100
python simulation/history_inspect.py ARCHIVE.sqlite causes 10663
python simulation/history_inspect.py ARCHIVE.sqlite event 1430
```

## Actual material provenance: Item 1

Person 163 produced timber lot 1349 in Settlement 5, year 53 (event 2800). Its retained transfer list records purchase event 3703. Person 114 created woodwork item 1 in year 63 (event 3704), explicitly using lot 1349; crafting cause 2800 points back to production. This example is a mundane object: `magical=false`.

The purchase is retained through the lot's transfer list, not an invented causal edge on the crafting event. The inspector can distinguish “recorded ownership transfer” from “explicit event cause.”

```
python simulation/history_inspect.py ARCHIVE.sqlite provenance item 1
python simulation/history_inspect.py ARCHIVE.sqlite provenance material_lot 1349
python simulation/history_inspect.py ARCHIVE.sqlite causes 3704
```

## Expedition → resource → purchase → use

In year 241 at Settlement 3:

- Event **43679**: Person **384** undertakes a magical expedition.
- Event **43680**, caused by 43679: discovers resource **1000**, an Uncommon Adventure awakening stone.
- Event **43685**, caused by 43680: Person 384 transfers it to Person **1316**, with reason `aspirant purchase` and price **4.0**.
- Event **43688**, caused by 43680: Person 1316 actually uses the stone. The resource's consumed event/person/year fields agree.

```
python simulation/history_inspect.py ARCHIVE.sqlite provenance magic_resource 1000
python simulation/history_inspect.py ARCHIVE.sqlite causes 43680
python simulation/history_inspect.py ARCHIVE.sqlite person 1316 --limit 100
python simulation/history_inspect.py ARCHIVE.sqlite settlement 3 231 251 --limit 100
```

No inference about private memory, affection, literary talent, or the expedition's historical importance follows from these facts. Those require later subjective and interpretive systems.
