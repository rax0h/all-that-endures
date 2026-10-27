# SDD ledger — plan: docs/superpowers/plans/2026-10-27-ate-native-proof-session.md

Baseline032af75, run40413908172 authenticated4247 full/1151 proof/27 complete matrices.
Pre-flight: native frozen plan already contains a session descriptor, while public manifest publication owns that descriptor. The bridge must check exact frozen generation/token/schema and remove only that exact descriptor before invoking the producer.
Ruling: expose an explicitly audited native session API, preserve default format7 admission fence — canonical native restoration must be proven before any repeated-audit bypass — admission/save remain expensive until affected-owner integration.
Ruling: keep the existing canonical registry and native acknowledgement, retaining original manifest parent separately through recovery — a new wrapper object graph would risk duplicate aliases — conservative epochs may require reopen after direct SQL/external writes.

Development RED→GREEN: missing native API; fresh-connection audit lacked transient ordered-seek builders; audit resynchronization required an owned writer transaction; recovery originally acknowledged native journals before the final full audit. A dedicated corruption regression demonstrated that pending state was lost, then moved authentication before commit/recovery acknowledgement. Initial19 native cases plus35 existing manifest cases passed54/54 in61.35s. Related native participant/catalog/recovery/copy regression suite120/120 passed36.93s.
New public manifest visibility regressions RED: closed sessions leaked SQLite errors and active publication exposed an unsettled manifest. Added existing native lifetime/state checks; focused21-case rerun in progress.
Ruling: explicit audited integration performs full audit before native admission and before committed/recovered native acknowledgement, plus post-operation resynchronization if SQL work occurred — epoch changes cannot serve as new authority by themselves — repeated history cost remains until the next affected-owner performance integration.

Task1: complete —21/21 native session tests passed29.70s, including both manifest-visibility RED→GREEN regressions;54/54 initial native+manifest checks and120/120 related native/copy regressions also green. All actual aliases, scalar/history/event edits, digest agreement, frozen token validation and recovery seams exercised. Final all-proof suite and one fresh whole-package review are pending.

Final review790c62a:0 Critical,3 Important,1 Minor. Single fix pass: epoch resampling
race, exact frozen token/generation disagreement, main/TEMP schema epoch invalidation.
All5 Important variants reproduced RED; closed lifecycle's2 RED probes document the
Minor and were removed from the permanent suite because the Minor is deferred.
Ruling: capture accepted epoch inside authenticated writer transaction; unchanged
operations retain the exact original sample — resampling outside validation accepts
racing external commits — guard costs remain fixed metadata reads.
Ruling: bind main/TEMP schema plus DB/codec identity; normalize only the known opener
TEMP-workspace rollback to its captured initial schema — full audit writes scratch DDL
inside the restore transaction — data/main-schema epochs are never freshly sampled.
Final: minor (deferred): closed proof-session save/resolve error type is SQLite's
ProgrammingError rather than native StoreError; no write is performed.
Every declined review area and cost is ruled on in native-proof-session/review.md.

Final: fixed all3 Important findings —5 focused regressions RED→GREEN; complete
native-session suite26/26 passed33.28s. Final unchanged-source proof/native regression
suites and checkpoint controls follow; no second review or new hosted run yet.

Task2 local verification:1177/1177 proof tests,120/120 native/copy regressions,26/26
focused native cases GREEN on corrected runtime40c93ec2522f2a434ab705189480f011399fd91f. All3 checkpoint controls
complete with0 history bodies. All3 Important findings fixed by5 RED→GREEN variants;
1 closed-error-type Minor deferred. One bundled candidate publication/hosted acceptance
follows; no main merge, automatic activation, endurance run or CI polling.
