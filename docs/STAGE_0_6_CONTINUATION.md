# Stage 0.6 current state

Repository: `rax0h/all-that-endures`, branch `sol/durable-proof-map`.

## Current repair and last qualification

The current qualified engine is **0d9dab5d4b36c89814dac6cb5904d589db4b8902**. Its change replaces a namespace-scanning private rebase point read with a unique rowid lookup, preserving keyset pagination, bounded retention and logical output. Regression, affected integrity/recovery checks and independent review are recorded under `performance/stage-0-6-current/rebase-locator-repair/`.

The preceding qualified engine was **84626841aa84b87a0564eda15200d83ea1478bb4**, public `4eadb668`, hosted run **43735593694**: 5,123 full-suite tests plus 2 subtests, 1,968 proof cases and 330 harness cases passed. Its compatible small smoke **43778758497** passed all 359 harness tests, interrupted-worker recovery and exact year-2 fresh restore. The hosted runtime is Ubuntu 26.04.1, Python 3.12.16 and SQLite 3.46.1.

The repaired engine passed [hosted qualification43877554746](https://github.com/rax0h/all-that-endures/actions/runs/43877554746) at public1de9adc6:5,125full-suite tests+2subtests,1,968proofcases and359harnesscases. Exact ZIPs and source/software/producer receipts are authenticated and retained under performance/stage-0-6-current/catalog-admission/. Current launch pins now bind this actual green engine.

The explicit retained-catalog handoff is implemented and reviewed. A new rebase receipt retains its original old-context catalog parent and complete chain verbatim; a pinned contract and attestation bind both contexts and exact bytes. Every consumption checks original producer/publication/expiry again. Local helper391pass and post-review38admission cases pass; independent review has no remaining findings. Complete hosted helper gate and actual admitted small recovery/fresh restore still precede mature activation.

## Mature run and retained checkpoint

[Mature run 43780946218](https://github.com/rax0h/all-that-endures/actions/runs/43780946218), public `6f3d0a88`, **failed in rebase** at the 9,000-second compute cap. Source verification, capture and catalog passed. The traceback and scaling probe establish an expensive logical-key lookup in `lazy_order_versions`; operational timings were never reached. The previous request is historical and has not been retriggered.

The last completed restart point is **catalog**, metadata **14197005279**, closed database **14195829058**. Its exact original receipt/control chain and producing job/upload timestamps were authenticated. The closed database is year 1001, seed 843000, generation 126, 29,389,029,376 bytes, SHA256 `8cc3dd2cd49ec143dd318a2ae6928f90b168ea06862c3939bec4aa32d6022562`. Its artifact expires December 16, 2026. Source/capture/catalog do not need a blind replay.

The original context remains attached to the old catalog. The narrowly scoped handoff supports exactly the admitted small/mature catalog inputs; ordinary compatibility is unchanged. After helper qualification, resume the old small catalog through the real crash/retry and fresh restore path. A successful compatible admitted smoke is required to resume mature rebase; source/capture/catalog are skipped. Rebase remains the first incomplete expensive mature stage.

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

**Next:** pass the hosted helper gate and admitted small recovery/fresh restore, then activate the retained mature-catalog resume. Preserve existing outputs and original control digests throughout.
