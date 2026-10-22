# Proof runtime foundation — 2026-10-22

This candidate implements the first runtime package of the [approved architecture](../superpowers/specs/2026-10-21-ate-incremental-proof-design.md). It does **not** implement durable cross-generation proofs, a new persistent format, authenticated lazy action admission or background scrub. Interactive targets remain unproven: warm year <=1 s, incremental save <=2 s, open <=10 s.

## Source and behavior

Remote parent: `c2242b67afdf102228c7b067c376cabe3c8df193`, root tree `9d4340e9e81eccd99b7f02f28f5ea0eab862d503`. Local equivalent baseline: `b731d6d` with the same complete tree. The existing dirty checkout was preserved in a separate worktree.

Runtime commits: `9129916`, then hook hardening in `9c816c2`. Runtime tree before the final review fixes: `398ed4b750461db383395fdd626322b53af24a52`. Final reviewed/fixed runtime tree: `05262053faf0ed546290753b607a463725e48821`. Runtime baseline for the new comparison: `5521c094981c9a5f28f1d076453264291b534ff5`, runtime tree `48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a`, the candidate from the previous mature measurements.

Eligible scalar edits now reuse a checked ownership route and mark value dirt without repeatedly queuing structural reconciliation. Structural changes retain immediate reconciliation. Certificates bind the existing store/pin/codec/database/topology authority; raw SQL writes, external changes, save/pin changes and custom hooks force the conservative path. Canonical identity remains in the existing registry. Certificates use weak subject references and reserve at most 128 entries/64 KiB inside the existing coordinator budget. Retained metadata is charged; dirty-state memory is still separate.

Opt-in attribution adds exclusive/inclusive timings, checked read counts by namespace and reason, bounded recent-key reuse samples and process IO where available. This instrumentation is diagnostic and comparisons require matching instrumentation. Neither sample hits nor the 32-MiB clean cache describe total archive cardinality or total RSS.

The mature runner captures open IO before its finalizer. Both runners write immutable `phase-progress-<phase>.json` records after each phase, outside its measured interval. A later hard exit preserves completed phases; progress cannot pass final acceptance or authorize a saved checkpoint.

## Verification retained locally

- Initial baseline: 41 existing assignment/owner-witness tests passed in 17.71 s.
- Expected failures established redundant scalar routing, native routing, retained-memory undercharging, class-level callback invalidation and loss of completed evidence after a later hard process exit.
- Final runtime: **143 affected tests passed in 59.11 s**, [log](proof-runtime-foundation/final-affected.log). Coverage includes scalar/native assignments, unloaded/deleted aliases, SQL/rollback/external writes, group corruption, custom hooks, cache bounds, publication and existing scaling checks.
- Final diagnostic change: **20 attribution/runner tests passed in 9.59 s**, [log](proof-runtime-foundation/progress-receipts-tests.log), including child processes that hard-exit after successful open in each runner.
- Exact new CI driver smoke passed using an explicitly substituted empty `World(843000)` fixture. Both baseline/candidate imported their intended runtime and their freshly reopened year-1 outputs matched independently computed eager digest `0af8c8866d9f6c92f4222c74b5f1591719a09a0589083678410ab4045c403486`. This verifies launcher plumbing, **not populated performance**. The exact smoke also passed after the phase-progress change; a final post-review smoke follows before publication.
- Full simulation suite and authentic populated comparison: pending remote execution.
- Fresh whole-branch review through `186c7ec`: two Important findings, both reproduced and fixed in one pass. Instance/class `preflight_value` and `preflight_change` replacements now force conservative routing. Attributed receipts bind the helper SHA-256; comparison rejects missing/different helpers. No corruption was demonstrated by the custom-hook finding; the fix enforces the documented admission contract.
- Six review regressions failed first ([red log](proof-runtime-foundation/review-findings-red.log)); the combined final check then passed **176 affected tests in 74.06 s**, including packed actions and participant-abort/recovery coverage ([final log](proof-runtime-foundation/review-final-affected.log)). The full remote suite remains pending. No deferred minor findings were reported.
- The earlier review attempt failed on service usage limits and supplied no verdict; the replacement completed. No second review was requested after fixes; regressions and remote full-suite validation cover that pass.

Test environment: Python 3.12.14, SQLite 3.53.1. Commands use existing installed dependencies:

```sh
PYTHONPATH=/workspace/scratch/7905b656a1e1/review-venv/lib/python3.12/site-packages:.:simulation python -m pytest -q simulation/tests/test_stage_0_5_performance_attribution.py simulation/tests/test_stage_0_5_performance_runner.py
```

The 143-test run also covered `test_stage_0_5_value_topology_reuse`, indexed/assignment-route/owner-witness/publication-proof reuse, final identity-only headers/coordinator/catalog publication, and performance scaling. [Initial redundant-work red log](proof-runtime-foundation/task-2-red.log) is retained separately.

## Local populated diagnostic — incomplete evidence boundary

A generated populated year-0 complete-format source was 134,066,176 bytes; conversion took 69.137 s. The original workspace conversion error's cause remains unestablished. The raw temporary source/receipts disappeared between turns; only [baseline](proof-runtime-foundation/populated-attribution.log) and [candidate](proof-runtime-foundation/populated-candidate-attribution.log) console phase summaries remain. These are exploratory observations, **not an authenticated correctness/performance acceptance pair**.

| Instrumented phase | Baseline | Candidate |
| --- | ---: | ---: |
| Open | 0.505 s | 0.434 s |
| First year | 46.878 s | 44.836 s |
| Save | 10.534 s | 10.275 s |
| Warm year | timed out after 17.135 s; incomplete | 37.957 s; complete |

Budgets differed (75 s versus 105 s). Warm phases cannot be compared. These small first-year/save changes do not establish interactive performance or predict mature speed.

Previously observed baseline attribution, whose raw receipt is no longer retained: first year had 172,825 checked version reads, including 30,737 catalog and 30,737 retirement reads, nearly all recently repeated. Exclusive instrumented time included encode 10.059 s, group work 8.736 s, checked reads 7.046 s, agency 5.112 s, owner work 3.829 s and decode 3.566 s. This motivates durable proof reuse; it is not a mature profile.

## Remote validation contract

The dedicated `stage-0-5-proof-runtime-validation.yml` launches on `sol/incremental-state-proofs`. It records exact source/runtime identity, runs the whole simulation suite with a 135-minute process budget and uploads logs/JUnit even on failure. Its separate bounded workload generates a populated seed-843000 source, computes an eager year-1 digest, measures baseline/candidate open/year/save/warm phases with the common attributed harness, then freshly reopens each saved year-1 output to compare exact digest, year, generation and store identity. JSON receipts and logs are uploaded; no mature 30-GB download or endurance chain runs. Warm year-2 is timed but not separately saved/digested and is not a correctness acceptance claim.

## Next package

Define canonical immutable content/topology/query nodes, complete membership and absence, generation manifests, root retention and an explicit verified-copy upgrade before implementing a new capability. Publish changed rows and their successor proof roots atomically through the existing transaction/recovery protocol. Then consume those proofs in save/open and prove that a fixed point edit reads zero unrelated historical payloads at 1k/10k/100k archive sizes. The foundation alone must not be presented as reaching those gates.
