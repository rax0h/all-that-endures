# Stage 0.5 performance repair — recovered validation handoff

Status on 2026-10-21: implementation candidate, not mature acceptance or interactive completion.

## Recovery boundary

This workspace resumed at `fca8f16d800754434f5a2aa9d05f822aa655bdbe`. Later locally reported commits, year-62 paired measurements, digest/restore logs and full-suite shards were absent from both this checkout and the checked remote. They are historical conversation claims, not fresh evidence for this candidate. The surviving Tasks 1–7 and scaling tests were preserved; reviewed corrections and the indexed-record follow-up were reconstructed and tested again. Unrelated dirty Astra/Luna handoffs were left untouched and unstaged.

## Recovered corrections

- Material rebuild shares active-only, identity-free scalar projections, not lot bodies. Selection does not instantiate unused rank/capacity heaps. Exhausted projections are removed. Rank construction retains ordered `heappush`, including NaN behavior; capacity arithmetic remains demand-driven. Failed rank construction does not publish a partial cache. Projection cache is excluded from persistence.
- Frozen identity overlays bind complete encoded placement values, not dictionary keys alone. Changed owner namespace/key/path/incarnation/delete fields reject before acknowledgement, with dirty/prepared state retained.
- Measurement provenance follows the actual imported engine and persistence modules; mixed roots reject. Comparisons require identical source, harness, instrumentation, machine and workload. First and warm steps are recorded separately.
- Indexed scalar assignment reuses routes only after full pending-placement reconciliation, exact DB/topology checks, unchanged hooks and exact assigned value. Reentrant callbacks, rolled-back writes, structural/nonfinite values, synchronizing runtimes and custom hooks retain full routing. No persistent format, game rules, clock, RNG or memory-budget contract changes.
- The synthetic fresh-process transport fixture binds its fake authority to the tested checkout. Production mature runtime pins and source checks remain unchanged; a regression explicitly requires rejection of an unreviewed runtime.

## Fresh local evidence

Environment: Python 3.12.14, SQLite 3.53.1, `review-venv`, `PYTHONPATH=.:simulation`.

| Check | Actual result |
| --- | --- |
| Review regressions before correction | 20 failed, 22 passed; failures reproduced all five reviewed categories |
| Same review/runner suites after correction | 42 passed in 14.67s |
| Indexed routes before follow-up | 4 failed, 12 passed; redundant route check reproduced |
| Indexed routes plus existing native assignment cases | 23 passed in 15.84s |
| Fresh-process continuation transport and source guards | 13 passed in 60.28s |
| Broad affected suites, 20 files | 204 passed in 133.96s |
| Additional partial-rank-cache regression before correction | Failed on second call, which incorrectly suppressed TypeError |
| Final material rebuild/selection/gameplay/persistence rerun | 32 passed in 26.60s |
| Post-commit broad affected rerun on final runtime | 205 passed in 126.99s |
| Workflow static validation | YAML, 10 shell blocks and 4 embedded Python blocks valid |
| Actual baseline/candidate CLI smoke | Both complete; same harness/source; actual import roots verified; comparison accepted |
| Whitespace validation | `git diff --check` clean |

The initial broad run had already imported the material module before the final exception-atomic rank-cache correction. Both the 32-case material rerun and the post-commit 205-case broad rerun cover the final runtime. Test logs currently reside in the task environment; the clean CI job will retain its own logs and JUnit evidence.

Memory observation on the 400-active-lot fixture: the added scalar projection dictionary recursively occupies 84,220 bytes including its referenced scalars (not incremental process RSS). No rank or capacity index is allocated by selection alone. This is active-set-proportional derived metadata, not a constant-size cache or retained archive of lot bodies; mature RSS still needs measurement.

The CLI smoke uses the retained 16-action fixture and is only a wiring/provenance check, not mature speed evidence. Its baseline runtime tree is `76dee76973928dbce72860156feb32f2d7f02f86`. The workflow checks out durable remote ancestor `fb75f1c49edda0731287acbf0054a1151ec318c9`, whose runtime is exactly that tree; the later local baseline harness-only commit is not needed when both lanes use the candidate harness.

## Remote validation boundary

`.github/workflows/stage-0-5-performance-validation.yml` has two bounded jobs:

1. Clean full simulation suite on Python 3.12; 135-minute command / 150-minute job limits, retained source identity, log and JUnit output.
2. Mature **open only**: authenticate retained year-1001 source and acceptance through the existing artifact protocol; compare accepted baseline and candidate on the exact same closed DB with the same harness and machine. Per-open budget 1,800s and hard command limit 40 minutes; job limit 100 minutes. Only one disposable measurement copy is retained at a time. Comparison requires both complete receipts; timeout/error is not a pass. No year advancement, audit acceptance or promotion occurs here.

Source DB: 29,922,463,744 bytes, SHA-256 `4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`, year 1001, generation 126. Save artifact `12129336378` / run `39098313631`; acceptance artifact `12165934374` / run `39207586140`. Both were checked live and were unexpired on 2026-10-21. Full source/producer/archive binding is reauthenticated by CI before measurement. Local disk is insufficient for this DB plus its disposable copy; it was not downloaded here.

The attempted independent workflow review ended at the reviewer's usage limit. This gap remains explicit; static checks and real CLI smoke are not a substitute for independent protocol review.

## What remains unproven

No clean full-suite pass, fresh paired mature elapsed time, exact year-1002 digest, independent mature audit or downloaded mature restore has been established for this recovered candidate. Do not merge or promote on the local affected tests alone. The proposed 1-second warm step / 2-second save / 10-second open targets remain unverified.

Eager action stitching still scales with retained actions; this repair batches required proofs but does not skip groups. Scalar assignments still perform placement synchronization before reusing routes. Save preparation, encoding and exact publication checks remain required. The CI open comparison establishes only the cold-open part of the remaining gap; bounded matched first/warm-step/save and exact continuation/restore checks are subsequent gates, not an automatic endurance chain.

Publishing uses the configured GitHub connection because the shell has no HTTPS credentials. The remote candidate will be a single atomic source snapshot over the durable reviewed ancestor; local granular implementation commits remain available in this checkout. No main-branch write or merge is authorized.
