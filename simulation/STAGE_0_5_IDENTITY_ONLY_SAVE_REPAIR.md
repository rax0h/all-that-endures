# Stage 0.5: identity-only save repair

The mature continuation run [38920910304](https://github.com/rax0h/all-that-endures/actions/runs/38920910304)
failed before committing year 1001. Year simulation completed in 4387.63 seconds;
save preparation then failed with `hybrid save omits a touched identity owner payload`.
This was an integrity rejection, not a timeout. No continued checkpoint uploaded.

The published year-1000 checkpoint remains available from run 38907665230,
artifact 12049884660 (`construction-mature-published`). Its authenticated input
database is 29601284096 bytes, SHA256
`0d884e52a012ab55325c7111bfc1d054fa7c27aaf0947cf9ab8de4423c213e1c`.
Do not repeat preparation, commit, ordering, verification, or publication to advance.

## Cause and correction

Normal `AgencyState.assess` replaces a person's `MotiveState` every step. In an
older world, a replacement can have exactly the previous serialized values.
The lazy family suppresses the unchanged value header but correctly emits a new
identity placement. The central publisher rejected that incomplete combination.

A generated 6x6, one-settlement seed-843000 world simulated to year 60 reproduced
the same exception during ordinary continuation: the missing payloads were
`world.agency.motives` owners 7 and 12. Equal-value Person replacement independently
reproduced the same defect. The mature run's original error does not name its
missing owners, so the exact mature owner set remains unobserved.

Runtime repair: `f312cc288ec5f583d34e16f63aa58d3093ca6b7c`.
Runtime tree: `e2142c50e54ece5495312860094052e09338497a`.

The identity coordinator now captures existing checked unchanged-header witnesses
for explicit World-family placement changes. Each witness compares current bytes
with the checked saved source and preserves schema and query memberships. Coverage
is checked after witness capture. This changes no persistence format, simulation
rules, or source checkpoint.

Physical recursive owners retain the original early coverage rejection: their
references encode incarnation IDs, so a placement edit requires an explicit
changed payload. They cannot use the new placement-only fallback. This restriction
also rejects deliberately omitted pages and new child bodies before commit.

## Verification

- Seven new regressions first failed at the original integrity guard.
- Ten final regression cases cover five record families, normal agency assessment,
  shared-peer separation, precommit recovery, lost acknowledgement, rejected
  omitted changed records, and rejected omitted recursive pages/child bodies.
- Corrected core gate: 43 passed in 24.38 seconds.
- Corrected affected gate: 101 passed in 173.34 seconds. Three JUnit-format warnings
  concern existing `record_property` measurements; there were no test failures.
- Independent review cleared the corrected runtime. Independent omission probes
  reject both page-only and page-plus-child omissions before commit, leave
  coordinator/dependency freezes clear, and permit a correct retry and reopen.
- A probe of the World-header witness repair made the failing normal year-60
  fixture save/reopen years 61 and 62
  with exact digests matching independently simulated eager controls. The complete
  two-year probe finished in 344.24 seconds. A checked-in full-suite regression
  repeats that probe against the final candidate after the auxiliary-coverage
  restriction. This is bounded correctness evidence, not a mature runtime estimate.

## Continuation provenance and remaining gates

`construction_mature_continue.py` retains the original runtime and all original
producer, artifact, receipt, database, and control checks. It uses P5's existing
`checkpoint_product_sha` resume option to distinguish the repaired execution
runtime from the saved checkpoint's producer. The executing runtime tree and
environment pin are checked before downloads; results must retain the original
checkpoint/source/control lineage while reporting the repaired execution SHA.
The provenance regression was observed failing before this wiring correction.
The complete continuation/transport gate then passed 57 tests in 297.76 seconds;
its only warning is the intentional duplicate-ZIP-member rejection case.
Independent review also cleared the wrapper and all three workflow failure paths.

The repair workflow runs only focused tests, the full suite, and recovery checks.
It does not launch mature continuation. The existing mature launch workflow has
not been repinned or restarted. Fresh full-suite/recovery results are required
because the runtime changed; the earlier unchanged-runtime shortcut does not apply.

After those gates pass, inspect runtime/upload headroom and repin the continuation
launcher to the reviewed repaired source and runtime. Resume from the retained
year-1000 publication. The failed year-1001 simulation must be repeated because
its save never committed. Both exact mature milestones, an independently
downloaded mature restore, and the final Astra handoff remain required. No Stage
0.5 completion or mature-runtime guarantee is claimed.
