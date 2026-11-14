# Independent whole-package review: coordinator publication read scope

Repository: /workspace/scratch/d88f8db353e8/ate, branch sol/durable-proof-map. Base c26684ed30a15a3df353895937e49d0ec5f2caea. Review covers the one-line production context substitution, new native acknowledgement regression, design/plan, and affected scope/catalog/coordinator/publication-proof/store/native-source custody paths. Previous W13 batching is outside this active change.

## Source fence

Initial reviewed SHA256:
- persistence_lazy_participants.py: 8bbd24682cf63aeacfddbfd8a0d25715944b87635a0bfb037a4b4dc3ed2c1301
- persistence_validation_scope.py: 998a91ebed682a88fbef38cab3e7842983412e11221185cd5dfebf1a49fa6a3f
- persistence_publication_proof.py: f3c9693c820678b8023d7d2247b04152a7ff5df5580023346f8650989fdb4fd5
- test_stage_0_6_publication_read_scope.py: 8e82102b9b49dbaad0283a30e3c9eda6ac5f53af8b273c58eff1e5996110594a

## Consolidated findings

R1 — Minor, OPEN: preserve the configured catalog transient budget. CoordinatorSaveParticipant.validate_publication creates a default 262144-byte scope irrespective of coordinator.catalog.byte_limit. Nested read_identity_group reuses this outer scope, bypassing its requested min(256KiB, catalog.byte_limit//6); it then computes spool portions from catalog.byte_limit minus the oversized outer allowance. The tiny real prepared-coordinator probe with catalog.byte_limit=128 retains 2026 bytes in this scope. This is a new budget regression compared with the old outer read_snapshot, whose nested scopes were ineligible. Pass the catalog-derived allowance to the new outer context and add a low-budget regression. This does not require another independent review cycle; verify in this report.

## Evidence and safety reasoning

probe.py and original probe.log are adjacent. Six bounded independent cases used the tiny existing generic prepared-coordinator fixture, without rerunning selected test files or building a mature fixture. Full qualified runtime fingerprint was checked: Python/compiler/SQLite/source ID/compile options, executable, extension, and loaded SQLite library hashes matched the recorded qualification. Probe process exited 0.

Passed: normal participant proof is standalone only after closing the owned read; borrowed checked snapshot produces no reusable PublicationProof; validation exception clears scope and leaves no row-proved pin; source corruption after validation invalidates the proof and acceptance rejects it; write then savepoint rollback after validation invalidates the proof; no probe returns with an active scope or transaction.

Static custody review: _check retains frozen delta identity and exact successor token/store/generation checks. Outer read_snapshot remains inside checked_read_operation and validates pin/head/retention before installing the scope. All catalog frozen versions, physical owner source rows, ordinary owner bodies/projections, and placement rows still execute their original checks. Native snapshot preflight still precedes reuse, and native source reads compare accepted root commitments. Scope cleanup invalidates cached metadata in a finally block and restores prior scope. PublicationProof.finish_owned_read remains after scope exit; confirm_cold_publication and accept_delta are outside it. PublicationProof.matches and accept_delta retain epoch/overlay/frozen-plan checks and the final registered-pin check. Accepted/recovery branch retains coordinator.accept_delta and lease checking.

Native fast custody explicitly rejects callbacks, custom row/text factories, authorizers, native write guards, changed phase hook, authority/pin/root/epoch identity drift and transaction/schema generations. The save path can instead use generic scope checking while publisher authority is busy: this path still compares connection, codec identity, pin, transaction/depth, total_changes, data/schema versions and phase-hook identity. It is therefore important not to describe every publication scope as possessing native fast-custody authority. Immutable scope entries are bounded and do not themselves grant acceptance.

## Limits / declined to judge

No whole-save speedup, latency acceptance, mature/endurance suitability, CI green state or future benchmark result is inferred from fewer head checks or instrumented phase attribution. Parent owns raw pinned A-B/B-A and selected focused tests. No raw benchmark ran concurrently with these probes.

No separate exhaustive adversarial callback/codec-registry/root mutation or recovery fault matrix was run here. These paths received source review; parent-selected existing suites supply broader dynamic coverage. Existing generic-scope callback/codec behavior was not redesigned. This report does not claim proof against arbitrary monkeypatching of private internal authority objects.

The sole actionable finding is R1; review remains open pending its closure. No repository files were modified by the reviewer.

## R1 closure / final same-package disposition

R1 — CLOSED. The participant now supplies byte_limit=min(256*1024, self.coordinator.catalog.byte_limit//6). The permanent test test_publication_scope_respects_configured_small_catalog_budget observes every remember call and requires both allowance and retained bytes to respect the configured one-sixth share, plus scope cleanup. Its source assertions were independently inspected; parent owns execution of that selected test file.

The unchanged independent probe.py was rerun against amended code, preserving initial probe.log and recording probe-after-r1.log. Process exited 0; qualified runtime full fingerprint passed again. All six cases passed. The 128-byte catalog now receives a 21-byte scope allowance and retains 0 bytes, while the default catalog retains its previous bounded 2026-byte metadata peak. Borrowed/exception cleanup and post-validation corruption/rollback protections still passed.

Final source fence:
- persistence_lazy_participants.py: 8141af3036d9e1e7a312eb1c65b04a67103308b8af877b2395c425d8b58b6c1e
- test_stage_0_6_publication_read_scope.py: 92cb646ca17daed2b23a5018faf5d64fd32e51b953d708631ecae9cc2aa238b0
- Unmodified scope/proof hashes remain as initially recorded.

This completes the single independent whole-package review and routine amendment verification. No actionable findings remain open. Performance/hosted/full-suite acceptance remains explicitly outside this review's claims. Reviewer is CPU-idle.
