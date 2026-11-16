# Stage 0.6 current state

Repository: `rax0h/all-that-endures`, branch `sol/durable-proof-map`.

## Current repair and last qualification

The current engine candidate is **0d9dab5d4b36c89814dac6cb5904d589db4b8902**. Its change replaces a namespace-scanning private rebase point read with a unique rowid lookup, preserving keyset pagination, bounded retention and logical output. Regression, affected integrity/recovery checks and independent review are recorded under `performance/stage-0-6-current/rebase-locator-repair/`.

The last fully qualified engine remains **84626841aa84b87a0564eda15200d83ea1478bb4**, public `4eadb668`, hosted run **43735593694**: 5,123 full-suite tests plus 2 subtests, 1,968 proof cases and 330 harness cases passed. Its compatible small smoke **43778758497** passed all 359 harness tests, interrupted-worker recovery and exact year-2 fresh restore. The hosted runtime is Ubuntu 26.04.1, Python 3.12.16 and SQLite 3.46.1.

The successor requires a new bundled hosted engine qualification. Production launch constants still bind the previous actual qualification and correctly refuse an unqualified engine. They have not been changed to pretend that old green evidence covers the successor. The quick harness now supports this qualification state while explicitly testing that mature admission stays closed.

## Mature run and retained checkpoint

[Mature run 43780946218](https://github.com/rax0h/all-that-endures/actions/runs/43780946218), public `6f3d0a88`, **failed in rebase** at the 9,000-second compute cap. Source verification, capture and catalog passed. The traceback and scaling probe establish an expensive logical-key lookup in `lazy_order_versions`; operational timings were never reached. The previous request is historical and has not been retriggered.

The last completed restart point is **catalog**, metadata **14197005279**, closed database **14195829058**. Its exact original receipt/control chain and producing job/upload timestamps were authenticated. The closed database is year 1001, seed 843000, generation 126, 29,389,029,376 bytes, SHA256 `8cc3dd2cd49ec143dd318a2ae6928f90b168ea06862c3939bec4aa32d6022562`. Its artifact expires December 16, 2026. Source/capture/catalog do not need a blind replay.

**A new-engine retry is not yet admitted.** The original catalog context pins the old engine and helpers, and recursive parent contexts must match. The next package must provide an explicit reviewed catalog-to-successor transition, preserving and authenticating original receipts and bytes, binding the exact code delta, and passing small recovery/corruption/equivalence tests after new engine qualification. Do not generally relax `compatible()` or relabel old receipts. Rebase remains the first incomplete expensive stage.

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

**Next:** authenticate the repaired engine's hosted qualification, then implement and validate the narrowly scoped retained-catalog admission before retrying rebase. Preserve existing outputs and original control digests throughout.
