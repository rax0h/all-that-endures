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
- Exact new CI driver smoke passed using an explicitly substituted empty `World(843000)` fixture. Both baseline/candidate imported their intended runtime and their freshly reopened year-1 outputs matched independently computed eager digest `0af8c8866d9f6c92f4222c74b5f1591719a09a0589083678410ab4045c403486`. This verifies launcher plumbing, **not populated performance**. The exact smoke also passed after the phase-progress change; the final post-review smoke also passed with both freshly reopened outputs matching the same eager digest.
- Full simulation suite and authentic populated comparison: [run 39728517108](https://github.com/rax0h/all-that-endures/actions/runs/39728517108), launched on `848ebf4bb14bd14ace00ba604f23a61acd967ea4` (root tree `24e8aaa0297026013793282cad31a7d274cabab8`). This published root exactly matches local tested source `74eef555e7e7358986d5bacbfff8404fd4ab71db`. **Populated job passed; full suite failed (189 failed, 2904 passed, 2 subtests passed, 1 warning; 5108.84 s). The candidate is not accepted.** See the results and repair section below.
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

The next bounded work package now has a [canonical node contract](../superpowers/specs/2026-10-22-ate-proof-node-contract.md) and [implementation plan](../superpowers/plans/2026-10-22-ate-durable-proof-map-foundation.md). These specify immutable map production first and explicitly withhold format-7 authority until content/topology/query manifests, migration and recovery are integrated.

## Run 39728517108: authenticated populated result and full-suite regressions

The downloaded [artifact manifest](run-39728517108/artifact-manifest.json) records GitHub artifact IDs and exact ZIP SHA-256 values. Both downloaded archives matched those digests before extraction. [Source authority](run-39728517108/populated/source-authority.json), complete final receipts, both fresh-restore receipts and [comparison](run-39728517108/populated/comparison.json) are retained in the repository. Per-phase snapshots remain in the original artifact; final receipts already contain all phases.

The populated year-0 input was 134,066,176 bytes. Baseline/candidate imports used runtime trees `48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a` and `05262053faf0ed546290753b607a463725e48821`, respectively. Each saved year-1 output freshly reopened to eager canonical digest `6c4b0344ec250e32f812d252a3b0163f36a93c259905a1f7ef1ba8de06d2bec3`. This is exact equivalence for this workload, not proof of all supported stores or of the timed unsaved warm year-2.

| Attributed phase | Baseline | Candidate | Baseline/candidate |
| --- | ---: | ---: | ---: |
| Open | 0.876 s | 0.893 s | 0.981x |
| First year | 81.798 s | 81.041 s | 1.009x |
| Save | 18.138 s | 18.793 s | 0.965x |
| Warm year | 73.905 s | 72.484 s | 1.020x |

There is no substantial speed improvement. This single attributed pair does not establish a statistically meaningful save regression. It does establish that the scalar-route package alone leaves almost all checked work intact: first-year payload reads fall from 163,913 to 162,914 (0.61%); warm reads fall from 143,497 to 142,102 (0.97%). Save counts are identical: 31,007 payload reads, 43,686 checked reads, 158,160 pin rows and 11,632 writes. Group validation calls slightly increase (first year 16,707 to 16,893; warm 16,541 to 16,677), because conservative route misses still revalidate groups. Global database/topology epochs also limit reuse across interleaved structural edits. The deterministic repeated-scalar-edit gate is useful, but does not eliminate this broader validation amplification.

The full-suite [failed node inventory and representative traces](run-39728517108/suite-failures.json) identify two root causes in the new optimization:

1. **184 legacy-format failures:** scalar admission dereferenced `_recursive_histories` before checking whether the session had an identity coordinator. Older checked stores deliberately have no such runtime. Admission must return the established conservative route before reading new-runtime attributes.
2. **Five native-header publication failures:** skipping structural backing reconciliation also omitted an already existing physical record-header source from the catalog participant. The native header's bytes advanced while its owner witness stayed old. Four native Event tests report the mismatch directly; the checked-current-copy recovery case first hits the same mismatch and then reports unresolved close while unwinding.

Repair scope: preserve scalar topology reuse, but select actual changed native headers into the frozen catalog publication whenever they contain references or already have a physical owner witness. This checks only frozen changed headers and one relevant metadata presence, never unrelated historical payloads. Existing scalar-only archives without a witness are not silently bootstrapped. Existing catalog validation still rejects missing/corrupt required witnesses. Data and witness continue through the same commit and recovery protocol.

Local reproduced failures and repaired-suite results follow in a separate verification receipt; the next remote run must pass the complete suite before this package is accepted. The unfinished proof-map package remains isolated and paused while these regressions are repaired.

### Repair verification before a new full-suite run

The repaired runtime tree is `6f00a6d68bafba1a371e470bfd70024237d8f79a`. Existing regressions reproduced the legacy crash and both native Event restore failures before code changes ([red log](run-39728517108/ci-regressions-red.log)). Then 16 legacy record-budget tests passed (8.64 s), 43 native Event/checked-copy/value-route tests passed (69.20 s), and 72 publication/participant-abort/proof/harness tests passed (71.52 s). Counts are separate runs and overlap; do not sum them as distinct coverage.

The complete failed-node local rerun passed 77 cases before reaching expensive 10k-record fixture builds. Its remaining cases are not claimed green; the full remote suite is the completion gate. The background local rerun, if it finishes, is supplementary evidence. No missing-history checks were disabled.

The first performance artifact omitted coordinator diagnostics from the phase working-set snapshot, even though the coordinator already exposed them. A new reproducing regression failed on the missing snapshot key. The common harness now retains route-cache hits/misses, residency and group-work counters after a phase, including correct fallback for older runtimes. All 23 final harness checks passed (38.87 s), [log](run-39728517108/ci-harness-green.log). This diagnostic-only change does not run in ordinary simulation.

The [repair verification receipt](run-39728517108/repair-validation.json) explicitly leaves full-suite acceptance pending. The new CI run will measure the repaired runtime and freshly verify both saved successors again.
