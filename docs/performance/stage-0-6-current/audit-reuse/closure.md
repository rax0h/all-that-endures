# Conditional postcommit audit reuse: review and evidence

Base:82d8af6f55c2b2302add869d88d14316611847be. This package consolidates the
scheduled task's measured audit-reuse optimization with its independent review
closures. It does not enable proof defaults, merge, delete history or claim
mature performance acceptance.

## Measured origin

Authenticated focused run40995017291 at95b27c5d7ced850beb7213f5eec91851acfffd9f
passed12cases207.80s. Downloaded artifact12951096935 ZIP SHA256
f2ebf105a4fd91bbaf5aede51aa217ac26036c9fdb69b6f1a6045dd6eba0ef1b matched
GitHub metadata; the source receipt matches exact producer SHA/runtime.
Original receipts are preserved under hosted-40995017291/.

The small structural fallback reduced3World/2authority audits to2World/1authority.
Profiled save6.476365s vs preceding11.0013s (-41.1%); this is instrumented,
different-runner small-fixture evidence. It is not a controlled mature speedup.
Current boundary checks preserve the existing matching-receipt test's one
postcommit authority audit, while epoch mismatch retains the extra audit.
Initial audited admission and general structural fallback remain history-wide.

## One consolidated closure register

One independent whole-package review:0Critical,2Medium/P2,2Minor/P3. The original
review against82d8af6 is preserved in review.md. All findings were fixed in one
author pass; this records author verification, not a second independent approval.

| ID | Origin | Concrete action | Evidence/status |
|---|---|---|---|
| R1 | Medium: codec object identity fails to detect in-place decode hooks | Recheck existing closed-codec contract before receipt reuse | Real post-audit delegating hook admitted RED, rejected GREEN; recover and reopen after hook removal. Closed |
| R2 | Medium: read-only acknowledgement transaction leaves epoch equal | Reject open transaction before reuse; avoid attempting exception-settlement audit inside leaked transaction, retain uncertainty for explicit rollback/recovery | Real acknowledgement BEGIN admitted RED, rejected GREEN; rollback/public recovery/reopen pass. Closed |
| R3 | Minor: timeout loses completed-case attribution | Atomic initial/case-start/case-end checkpoints; running status/null exit code until pytest finishes; workflow preserves numeric process exit and timeout flag | Actual subprocess TERM and KILL during second case preserve finished first case and active selector. Closed |
| R4 | Minor: recovery epoch counts include prior admission | Slice audit epochs from each execute entry; retain bucket totals separately | Admission followed by two recovery executions each reports only its one matching audit. Closed |

Actual separate-connection post-audit schema change forces a new audit; actual
checksum corruption rejects save and supports public recovery after restoring
only the injected new checksum. The optimization does not trust the spoofed
receipt test as evidence of actual external-write detection.

Seven boundary/diagnostic regressions passed8.86s. The86-test affected gate
passed195.07s, including complete generated-world years3/4, fresh-process digest
restores, ordinary/proof insertion order, matching/stale receipt paths, frozen
manifest faults, recovery, corruption, SQL guards and native value/tail paths.
The generated-world test104.49s is a correctness test runtime, not a mature
latency receipt. YAML/bash and source fingerprints are checked separately.

The first external-corruption test attempt repaired a pre-save checksum instead
of the newly committed checksum and therefore correctly failed recovery. That
fixture bookkeeping was corrected; it is not counted as a product defect or
successful evidence. Early setup lacked pytest; dependencies were restored.

## Remaining acceptance work

Full correctness at the final candidate requires the bundled hosted run. The
last full green29751bd predates audit reuse. No prior full green is inherited
across this runtime change. A full run is justified by the changed native
acknowledgement/recovery boundary, not by the diagnostic/documentation edits.

Mature open10s,incremental save2s,warm step1s remain open. The current mature
fixture has not been measured through this new runtime. General save fallback
still audits unchanged history; extending authenticated changed-owner,
query/order, identity/backing and retirement transitions is the next
architectural optimization. Open requires separate attribution of admission and
restoration. Existing lower-level proof primitives should remain the authority;
skipping audits without equivalent authenticated transition coverage is not an
acceptable repair. A later mature measurement must preserve exact source,
fixture provenance, phase-specific budgets and fresh-process continuation.

## Harness reconciliation

The first clean-checkout harness gate passed28tests and failed the old rule that
only one Stage0.6 workflow may exist. The scheduled task added a separate bounded
audit diagnostic. C1: clarify that contract to require exactly one mature workflow
and the explicitly bounded diagnostic lane, with no mature transport/measurement
commands in the diagnostic. Full measurement remains manual-only. The exact
source fingerprint is updated for this test change. This compatibility finding
is closed by the subsequent clean-checkout29test result; it is not deferred.

Final clean-checkout harness gate:29passed19.85s (harness.log/harness.xml). Exact
runtime pin fe7467eb2047aaee4debc48c5cad24a917895acd; original authenticated
fixture and green-ancestor checks remain intact. Total focused gates:7boundary,
86affected and29harness checks. All four independent findings and C1 compatibility
finding closed; hosted final-candidate correctness remains pending.
