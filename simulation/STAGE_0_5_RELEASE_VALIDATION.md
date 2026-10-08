# Stage 0.5 release validation

> Final architect review (2026-10-08): **blocked; do not merge**. See
> [STAGE_0_5_FINAL_ARCHITECT_REVIEW.md](STAGE_0_5_FINAL_ARCHITECT_REVIEW.md)
> for three reproduced architectural defects, verified final CI evidence,
> the late-fixture retention gap, and the bounded Sol repair assignment.
> Bounded R1/R2 repairs and **unresolved R3** are documented in
> [STAGE_0_5_FINAL_REPAIR_CLOSEOUT.md](STAGE_0_5_FINAL_REPAIR_CLOSEOUT.md).
> The earlier candidate/status below is historical, not final acceptance.

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

## Final-code short closeout evidence

Run `37516101856` passed on helper head
`db296bf9c90314c537636e3c236f666679ecef96`, branched directly from
Stage 0.5 head `6a1990754c777dcb11b1aa8985754359bf2ee803`.
No material simulation product/test bytes changed between implementation
candidate `14f178623a6ef6e0d915fb4fe061079f54b15c21` and that tested head.

The required targeted smoke passed:

`PYTHONPATH=.:simulation python simulation/specific_test.py --seed 843000 --years 10 --section all`

It produced year 10 with **439 events**, last event ID **439**, and canonical
digest `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`,
matching the P5 short continuation digest.

The compact final-code failure/lifecycle/compatibility battery passed
**138/138 in 103.70s**, covering:

- `test_persistence_lazy_store_failures.py`;
- `test_persistence_lifecycle.py`;
- `test_persistence_session_open.py`;
- `test_persistence_cold_save_failures.py`;
- `test_persistence_lazy_identity.py`;
- `test_persistence_p2c.py`.

This reruns the accepted atomic failure/recovery, stale session/writer,
generation-pinned read, close/reopen, detach, identity, corruption/refusal and
legacy/current compatibility boundaries on final product/test bytes without
repeating the entire P4 affected matrix.

PR #14's previous dirty merge state was traced to overlapping
`docs/LIVING_DESIGN.md` edits. The Stage 0.5 branch now preserves main's newer
living-design document and its README/visual-constitution updates while retaining
the Stage 0.5-only **Material life and quiet economic pressure** section.
GitHub now reports PR #14 **mergeable / clean**. These reconciliation commits
are documentation-only and do not change simulation product/test bytes.

The remaining execution gate before authorized long-horizon evidence is the
already-running integrated P4/full-suite run `37513490616`. Do not launch a
redundant full suite unless material product/test bytes change.

## Cross-lazy alias closeout correction

The integrated full suite `37513490616` completed with **834 passed / 1 failed**
in **2558.52s**. The sole failure exposed a real dirty-tracking defect for an
`IndexedRecord` materialized through another lazy owner before its canonical
payload was loaded.

Frozen product/test head after correction:
`e4752e306d30dcff41be1cc17ddc6e63004646a3`.

Validation of the correction:
- `37520218759`: 2/2 exact regressions and 57/57 directly affected lazy
  people/aspiration/currency/identity tests;
- `37520547147`: 2/2 exact regressions, canonical seed-843000 10-year smoke,
  138/138 final-code recovery/lifecycle/compatibility tests, and the P5 short
  integrated continuation. The year-10 digest remains
  `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`
  with 439 ordered events and last event ID 439.

The owner explicitly directed that another 42-minute full-suite run not be used
solely to recheck this localized correction unless it proves necessary. This
release record therefore preserves the exact evidence boundary: there is no
claim of a second post-fix 835-test full-suite pass. Final architecture review
must decide whether the 834 prior passes plus the focused/affected/final-code
substitution satisfy the completion-plan full-suite intent.

The dedicated P5 long-horizon harness was dry-run successfully in
`37521427781` at years 4/7/10, including independent-control digest equality,
incremental save/reopen, checked durable backup/restore and uploaded artifact
`11439363432`. The harness itself is validation-only and does not change
simulation product semantics.

