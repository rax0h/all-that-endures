# Stage 0.6 current state

Repository: `rax0h/all-that-endures`, branch `sol/durable-proof-map`.

## Current repair and last qualification

The current qualified engine is **0d9dab5d4b36c89814dac6cb5904d589db4b8902**. Its change replaces a namespace-scanning private rebase point read with a unique rowid lookup, preserving keyset pagination, bounded retention and logical output. Regression, affected integrity/recovery checks and independent review are recorded under `performance/stage-0-6-current/rebase-locator-repair/`.

The preceding qualified engine was **84626841aa84b87a0564eda15200d83ea1478bb4**, public `4eadb668`, hosted run **43735593694**: 5,123 full-suite tests plus 2 subtests, 1,968 proof cases and 330 harness cases passed. Its compatible small smoke **43778758497** passed all 359 harness tests, interrupted-worker recovery and exact year-2 fresh restore. The hosted runtime is Ubuntu 26.04.1, Python 3.12.16 and SQLite 3.46.1.

The repaired engine passed [hosted qualification43877554746](https://github.com/rax0h/all-that-endures/actions/runs/43877554746) at public1de9adc6:5,125full-suite tests+2subtests,1,968proofcases and359harnesscases. Exact ZIPs and source/software/producer receipts are authenticated and retained under performance/stage-0-6-current/catalog-admission/. Current launch pins now bind this actual green engine.

The explicit retained-catalog handoff is implemented and reviewed. [Admitted smoke43916382557](https://github.com/rax0h/all-that-endures/actions/runs/43916382557) at public43b9fbb2 passed399quicktests, actual exit77 crash/unchanged-parent retention, ordinary retry, rebase, exact after_digest, proofs, measurement, fresh restore and acceptance. Source/capture/catalog were skipped. All checkpoint/database producer timestamps, ZIP hashes, three raw database hashes, exact old parent chain,50criticalpaths and hosted-runtime signature were independently authenticated. Exact fresh year2/gen1/digestcebc2fcd matched. This is functional smoke evidence, not mature timing acceptance.

## Mature run and retained checkpoint

[Mature run 43780946218](https://github.com/rax0h/all-that-endures/actions/runs/43780946218), public `6f3d0a88`, **failed in rebase** at the 9,000-second compute cap. Source verification, capture and catalog passed. The traceback and scaling probe establish an expensive logical-key lookup in `lazy_order_versions`; operational timings were never reached. The previous request is historical and has not been retriggered.

The last completed restart point is **catalog**, metadata **14197005279**, closed database **14195829058**. Its exact original receipt/control chain and producing job/upload timestamps were authenticated. The closed database is year 1001, seed 843000, generation 126, 29,389,029,376 bytes, SHA256 `8cc3dd2cd49ec143dd318a2ae6928f90b168ea06862c3939bec4aa32d6022562`. Its artifact expires December 16, 2026. Source/capture/catalog do not need a blind replay.

[Mature resume43918798385](https://github.com/rax0h/all-that-endures/actions/runs/43918798385), public71967a3d, was activated by request admitted-mature-catalog-2026-11-16-1 and selects the retained mature catalog through this successful smoke. It uses resume43780946218,smoke43916382557 and the reviewed mature budgets. The original context/chain stays attached to the old catalog; only the new rebase receipt uses the current context. Ordinary compatibility stays strict. Entry gate133480139824passed399tests; raw output confirms exact mature catalog14197005279/run43780946218. Source/capture/catalog are actually skipped and rebase133482798633is active (disk/restore preparation at observation). Rebase is first incomplete. Later retries prefer their own completed checkpoints and fail closed if none is usable.

## Preserved original input

Private draft **446184821** retains both original fixture ZIPs independently of Actions expiry. Preservation run **43734650623** reconstructed both originals and matched their exact hashes; live consumer hop **43776600177** verified real access. The original mature database hash `4a39288b...`, archive hash `4f040569...`, year-1001 authority and expected year-1002 digest `2a9b53ed...` are unchanged.

## Acceptance remains open

| Mature operation | Target | Current engine |
|---|---:|---|
| Open | <=10 seconds | Unmeasured |
| Save | <=2 seconds | Unmeasured |
| Warm year | <=1 second | Unmeasured |
| Exact year-1002 continuation | Unchanged accepted digest | Unmeasured |

New SQLite probes are synthetic locator-only data, not mature performance measurements. A timing miss or green engine badge does not complete Stage 0.6. The broader forensic closure register remains at `performance/stage-0-6-current/forensic-repair/closure-register.md`; owner-deferred and missing-review-001 items remain explicit. No main merge, default-format activation, gameplay migration or endurance run is included.

## Latest proof-construction failure and repair candidate

Mature resume **43918798385 failed in proofs at its 12,600-second compute cap**. Rebase **133482798633** and after-digest **133544470271** completed successfully; the canonical baseline remained exact. The earlier observation that rebase was active is historical. Measure, fresh-restore and acceptance were skipped; all mature operation timings above remain unmeasured.

The last completed restart point is now **after_digest**, metadata **14267625292**, sharing closed rebase database **14261110486**. This is year 1001, generation 0, seed 843000, 29,409,034,240 bytes, SHA256 `b1c7ffcd9379d246002d9052065a44d5de539606bb00c43ef7997785962521a5`. Original chain, contract, producer/runtime and 50 critical paths are authenticated under `performance/stage-0-6-current/proof-source-audit-repair/`. These completed stages must be preserved.

The manifest audit repeatedly checked the same shared proof-tree paths for each physical source. A candidate replaces these point traversals with an exact temporary locator/commitment spool and one checked traversal of every reachable node, preserving physical validators, counts and two-way completeness. Synthetic profiling and real World regression establish reduced work; remaining mature audit costs are still unmeasured.

Candidate engine **5464caa49acc4c27f24c247b60ee639afd9d150d** requires new hosted qualification. Previous engine0d9/public1de9 remains the qualified baseline. Ordinary compatibility and launch pins remain strict; the new engine is **not admitted** to the retained after-digest. A separate exact transition must preserve the inherited catalog cut. See the repair README for evidence, limits, restart unit and budgets.

Independent review is complete with all findings closed, including cleanup diagnostics, exact publication authentication and the historical qualified test fixture. Local affected171, post-review61, clean helper403 and final evidence5 checks passed in the documented sequence; these groups overlap. The final hosted helper gate includes404cases.

[Hosted qualification43991230104](https://github.com/rax0h/all-that-endures/actions/runs/43991230104) is active at public **24c0c612ab51908826f35e867413c86a83b01db6**, engine5464caa. Request classifier133732018194passed; harness133732017719is running. This is engine qualification, not a mature simulation. Exact source tree and observed jobs are recorded in the repair's `qualification-launch.json`. No new mature request was activated.

**Next:** inspect this qualification result and authenticate actual new green evidence, then prove the explicit retained-after-digest recovery boundary on a small hosted case. Measure the remaining proof audit before any long retry. Preserve original control digests and exact year1002acceptance.

## Qualified proof audit engine and after-digest recovery

Qualification43991230104 completed successfully. Actual full log5142passed+2subtests/9481.56s, proof1968cases and helper404cases; exact ZIP/job/source/runtime evidence is retained under `performance/stage-0-6-current/after-digest-admission/qualified/`. Engine5464caa/public24c0c612 is now the qualified baseline. The earlier pending-qualification observations are historical.

A separate exact after_digest->proofs boundary is implemented, preserving the full nested catalog cut under its historical contract and reauthenticating all four old refs on later consumption. Local real-receipt/producer/expiry checks and real proof/crash/retry checks pass; helper/workflow composition is under complete quick validation and independent review. Existing engine code and targets are unchanged, and no mature request has been activated.

The complete committed-clean helper suite passed432cases/179.02s. Independent whole-package review found no actionable findings, includingMinors:86targeted and22additional adversarial cases passed using the actual current source fence. Four-ref expiry/publication/hash/duplicate-producer checks and engine/helper/runtime rebinding all rejected. Exact33fingerprints/52criticalpaths and unchanged engine/old catalog contract were independently verified. Raw evidence is retained under the admission package.

Request `admitted-small-after-digest-2026-11-17-1` selects old small after-digest14252280082/run43916382557, skipping source through after-digest and running only proofs onward with a real exit77 recovery drill. This is explicitly a **small functional recovery run**, not a mature simulation or performance acceptance. Engine/full-proof green is reused; no new engine validation is required for these helper-only changes.

**Next:** authenticate actual hosted small crash/retry/fresh-restore completion, then attribute remaining mature proof-audit work before a new long retry. Do not replay completed rebase or canonical after-digest.
