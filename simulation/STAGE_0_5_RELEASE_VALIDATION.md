# Stage 0.5 release validation

**Status:** P5 short integrated validation preparation.  
**P4 implementation candidate:** `14f178623a6ef6e0d915fb4fe061079f54b15c21`.

This file is the reproducible release-validation authority required by
`STAGE_0_5_COMPLETION_PLAN.md`. The persistence backend remains opt-in;
checkpoint defaults are unchanged.

## Short integrated harness

Use:

`PYTHONPATH=simulation:. python simulation/persistence_p5_validation.py --seed 843000 --pre-years 3 --continuation-years 4 --reopen-years 3 --output p5-short.json`

The harness compares:

1. an independent unbound simulation control;
2. a schema-8 checkpoint roundtrip followed by identical continuation;
3. a cold snapshot converted explicitly into the P4 lazy store;
4. lazy continuation + save;
5. close/reopen + a second continuation + save;
6. store backup/relocation;
7. explicit materializing detach;
8. checkpoint roundtrip after detach.

Every comparison requires the exact canonical World digest, seed/year,
top-level and subsystem next-ID counters, and full ordered event projection:
ID, year, kind, layer, actors, location, causes, values/data and sealed flag.

The harness records fixture-creation time separately from continuation, save and
full-audit IO. Full digest/event audits are intentionally allowed to materialize
history and are not ordinary-working-set measurements.

Before the first continuation it warms representative read/query paths for
social relationships/neighbors, community membership, transmission history and
material availability without mutating simulation state.

## Required short gates

Before requesting long-horizon evidence, record:

- integrated P4 full suite on source/test bytes equal to the P4 candidate;
- this short P5 harness on final code;
- the existing targeted simulation smoke:
  `PYTHONPATH=.:simulation python simulation/specific_test.py --seed 843000 --years 10 --section all`;
- failure/lifecycle/compatibility coverage on final code;
- one final full `simulation/tests` suite after the last material product
  change;
- final PR mergeability/base-drift status as an integration concern only.

Existing P4 affected matrices already cover atomic old-or-new save behavior,
lost acknowledgement, stale writers, recovery, source-preserving conversion,
identity alias semantics, detach failure rollback and lifecycle guards. P5 must
rerun a compact final-code subset rather than inventing weaker replacements.

## Long-horizon gate

Long-horizon evidence is owner-authorized for this project, but execute it only
after all short gates are green on one frozen candidate. Use seed 843000 and
capture representative 100/500/1,000-year milestones in one instrumented
canonical run where possible. Record simulation time separately from digest,
scrub, archive, save and restore costs.

The run must audit chronological progression, currency/resources, recurring new
Irons, rank/path funnels, lineages, institutions, economy/threat coupling and
growth/provenance using existing definitions. Do not introduce balance changes
or resurrect historical rank quotas to make the run green.

A green legacy-only millennium is insufficient: the final evidence must exercise
the opt-in P4 backend and its independent control where required.

## Acceptance boundary

Stage 0.5 may be proposed for acceptance only after the final report identifies
the frozen SHA, exact short/full/long evidence, durable restore artifact
provenance, measured working-set costs, recovery/lifecycle proof, honest
limitations and PR integration status.

No green validation result implies merge, tagging or Stage 1 authorization.


## P5 short integrated evidence

Run `37514431256` passed on the final-code validation head.

Seed `843000`, split `3 + 4 + 3` years:
- year-7 control digest: `b31c2272d220a1624ff5ee204e229ccaf95adf9a7eaff86643b350567b5e9387`;
- year-10 control/final digest: `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`;
- final ordered event count: **439**, last event ID **439**;
- schema-8 checkpoint lane matched exactly after continuation;
- cold -> lazy lane matched after first continuation/save;
- close/reopen matched and a second continuation/save matched;
- byte-for-byte store backup/relocation opened to the same year-7 authority;
- materializing detach matched year-10 authority;
- checkpoint roundtrip after detach matched year-10 authority.

The explicit lazy conversion reported `source_preserved=true`.

Measured first continuation: **3.058s**. First incremental save:
**102 payload reads / 36,805 bytes; 2,143 writes / 642,542 bytes**.
Second continuation: **2.314s**. Second save:
**7 payload reads / 516 bytes; 1,713 writes / 549,086 bytes**.
Full digest/event audits are reported separately and intentionally materialize
history.

Durable machine-readable summary:
`simulation/p5_short_validation.json`.
