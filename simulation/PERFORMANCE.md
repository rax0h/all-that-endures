# Millennium performance and stabilization pass

The normal seed-843000, 1,000-year simulation first passed the 120-second gate on
commit `94302a3df66525fc7e4063b6e24143016fdbe2e8`: **87.61 seconds of simulation,
101.07 seconds for the entire process** on GitHub Actions. This preserves the
original world's complete canonical digest and all 60 shared year-1000 diagnostic
fields. No population, years, causal systems, environmental manifestation rules,
advancement constants, or historical archives were removed or reduced.

The starting branch head was `216c2660d258a95c67b811023dd3cce73b2d18ef`;
main was `445699aa8e6d881d5543128f31e5bad785ea2043`. The requested starting
measurement was 670.82 seconds overall. An instrumented, unprofiled baseline
on the same GitHub runner class measured 653.80 seconds overall, of which
623.92 seconds was simulation and 28.80 seconds was final digest generation.
Hosted runner speed varies, so compare both timings and preserved outcomes.

## Measured scaling

All times below are simulation wall seconds, including the same subsystem timer
wrappers. The first accepted run excludes cProfile overhead.

| Years | Instrumented baseline | First accepted run |
|---|---:|---:|
| 1–100 | 2.76 | 1.72 |
| 101–250 | 19.29 | 8.04 |
| 251–500 | 92.93 | 19.35 |
| 501–750 | 204.59 | 27.29 |
| 751–1000 | 304.34 | 31.20 |
| Total | 623.92 | 87.61 |

The final bucket became approximately 9.75 times faster. Its population remained
1,323; the archive still contains 12,368 people, 306,184 events, 72,014 relationships,
99,691 material lots, 8,784 crafted items, and 26,565 magical resources.

| Subsystem, all 1,000 years | Baseline seconds | First accepted seconds |
|---|---:|---:|
| Magic ecology | 333.17 | 17.09 |
| Magical civilization | 76.88 | 10.58 |
| Agency | 47.17 | 24.98 |
| Demography | 41.44 | 3.18 |
| Material economy | 33.39 | 3.53 |
| Civilization | 22.91 | 4.20 |
| Institutions | 19.27 | 1.44 |
| Accountability | 12.09 | 0.02 |

Evidence and full collection/subsystem measurements are retained in
[performance/millennium-pass.json](performance/millennium-pass.json).
The baseline is [Actions run 34714441469](https://github.com/rax0h/all-that-endures/actions/runs/34714441469).
The first accepted benchmark is [Actions run 34740952934](https://github.com/rax0h/all-that-endures/actions/runs/34740952934),
with [103 tests and both smoke checks passing](https://github.com/rax0h/all-that-endures/actions/runs/34740954541).
Intermediate simulation measurements were 328.64, 200.56, and 132.49 seconds;
the 132.49-second run correctly failed the new performance gate.

## Architectural changes and validity rules

- Magic demand is evaluated once per semantic demand type, not once per duplicate
  held resource and every possible recipient. Settlement markets group fixed
  urgency/drive/preparation priorities and reevaluate wealth at each purchase.
  Two demand heaps hold current essence/stone eligibility; actual essence identity
  remains an exclusion at lookup. Refresh follows path/preparation changes and
  transfers, preserving the original aspiration initialization and RNG order.
- Material selection uses settlement heaps and incremental magical-lot counts.
  An integer lower bound proves when crafting capacity is saturated; near the
  threshold the exact original ordered floating-point sum is retained. Random
  selection caches IDs in the original active-set iteration order. Creation and
  exhaustion invalidate selection pools. Lot quality/properties are creation-time
  data; explicit data repair must call `rebuild_active_index()`.
- Community membership lookup uses a persistent person index. Strengths still
  come from authoritative membership data, and new memberships go through `join`.
  Historical insertion order is preserved for inheritance and tie decisions.
- Current partnerships are found through living endpoints, while historical
  partnerships remain in the social graph. `partner` maintains the endpoint index;
  old checkpoints build it lazily. Demography still sorts candidate pairs exactly.
- Agency traverses a person's adjacent relationships, including relationships with
  dead people. Cached adjacency holds references to the actual Relationship
  objects, so mutable weights remain visible. `get` maintains it when edges appear.
- The engine shares a living-person view within each simulation step. Birth,
  death, and resurrection events invalidate it. It is cleared even on exceptions;
  direct scenario edits between steps therefore remain visible. New in-step life
  mutations must emit their corresponding causal event. Settlement grouping reads
  current person fields, including migration and newly formed households.
- Current-year event queries use binary search on the chronological event archive.
  No old event payloads are traversed to answer routine current-year questions.
- Environmental essence weights are cached by the exact composed environment tag
  tuple, with a bounded 512-entry cache. Candidate order and weights are identical;
  current context is recomputed for every manifestation. The semantic dictionary
  is simulation-version data; an explicit hot reload must clear `_environment_weights`.
- Biology composition is cached by immutable species/rank rule profiles. Actual
  rank or species changes select a new composition; live health/age are not cached.
- Canonical hashing traverses dataclass fields without `asdict`'s full deep copy,
  and caches field metadata. Intermediate snapshots do not hash the accumulated
  world. Final hashing still covers the complete original canonical archive.

Derived caches are private runtime attributes, excluded from canonical dataclass
history. Tests cover lazy rebuilds, checkpoint/resume, index mutation, mutable
relationship references, ordering/ties, no-archive-scan queries, and differential
comparison with the original magic/agency algorithms. The 100-year golden hash
also protects full-engine equivalence. The original millennium digest is:

```
915303bde48ecbaffb6f954f6c9513032e54b9770692ee3200c894c72072d412
```

## Running and enforcing the benchmark

From the repository root, with Python 3.12:

```sh
PYTHONPATH=.:simulation python -m pytest -q simulation/tests
PYTHONPATH=.:simulation python simulation/run_long_history.py 843000 1000 --max-seconds 120
PYTHONPATH=.:simulation python simulation/profile_simulation.py 843000 150
```

For a late-history investigation:

```sh
PYTHONPATH=.:simulation ATE_PROFILE_TAIL=10 python simulation/run_long_history.py 843000 1000
# Alternatively warm up 990 years, then profile the final 10:
PYTHONPATH=.:simulation python simulation/profile_simulation.py 843000 10 990
```

The JSONL benchmark emits per-bucket subsystem times and archive/current collection
sizes, then separate simulation, diagnostics, digest, and validation timings.
`--max-seconds` fails after printing evidence when actual simulation wall time
exceeds the limit. It rejects cProfile-enabled measurements. It includes all
1,000 years and retains final digest and causal-integrity validation.

Normal CI runs unit/integration tests, a targeted probe, and a deterministic
100-year smoke. The performance workflow runs one unprofiled 1,000-year benchmark
with the 120-second gate; `pipefail` propagates failures through `tee`, and
artifacts upload even if the gate fails. Multi-seed calibration remains
scheduled/manual. The separate canonical endurance workflow remains manual.

## Calibration observations deliberately left unchanged

The matched millennium snapshots have 341 living essence users and 70 completed
20-ability paths. Both standard and long-history diagnostics now separate complete
and incomplete users:

| Rank | All living users | Completed paths | Incomplete paths |
|---|---:|---:|---:|
| Iron | 65 | 3 | 62 |
| Bronze | 60 | 0 | 60 |
| Silver | 79 | 3 | 76 |
| Gold | 79 | 9 | 70 |
| Diamond | 58 | 55 | 3 |

58 living Diamonds remains above the requested causal target of roughly 10–15,
with up to 20 acceptable. There are still 20,589 available magical resources out
of 26,565 created and only 37 society notices. These are real calibration issues,
not performance fixes or newly introduced regressions. No quota or constant
retuning was used in this pass.
