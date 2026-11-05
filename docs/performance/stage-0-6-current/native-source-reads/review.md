# Native source integration consolidated register

One independent whole-package review (`native_source_review`, Astra/high) against
green df624e9. Raw review/probes are retained under `review-raw/`; all findings,
including Minor, belong to this group. No second independent review or CI cycle
per finding is used. Author corrections are verified by failing regressions and
the final combined test run, recorded in closure.md.

| ID / origin | Finding | Action and verification |
|---|---|---|
| R1 Important, independent | Ambient publisher guard let a before-commit callback expose staged child bytes; an unrelated guard bypassed source proofs. | Match the exact authority-owned guard; reject native source access from read-only/SQLite callbacks. Real phase rollback and foreign-guard regressions in review-red.log fail before the correction. Final regression verifies exact retry/recovery and no staged value exposure. Closed. |
| R2 Important, independent | Epoch checks ran before SQLite began the source snapshot. | Check within admitted snapshot entry as well, before inherited reads and after pinning its small fixed head view. The review's no-op UPDATE is elided by SQLite3.53.1, so the retained test uses a real independent checksum mutation of an unrequested source. Disabling the in-snapshot check fails in epoch-disabled-red.log1.64s; enabled passes epoch-fixed.log1.76s. Closed. |
| R3 Important, independent | Outer lazy snapshot could transfer oversized operational head/pin/receipt/attempt fields before the source guard. | Guard admitted legacy snapshot entry before inherited metadata access and use the existing bounded operational metadata preflight inside the snapshot. Actual poisoned-head transfer sentinels cover both normal epoch rejection and isolated budget rejection. Both fail in review-red.log. Closed. |
| R4 Important, independent | Per-field SQL bounds transferred a large body despite already-invalid scalar/locator/event-ID metadata. | Row-wide version/segment metadata preflights and ordinary CASE body predicates reject fixed metadata/size/type errors before body transfer. Five real SQLite row-factory transfer sentinels fail in review-red.log; final regression covers all five source variants. Closed. |
| R5 Important, independent | Checksum-consistent future valid_to could be returned although immutable content deliberately excludes interval closure. | Current accepted native source versions must be physically open. Reject impossible future closure in the bounded metadata preflight; no content framing changes. Future-interval regression fails in review-red.log. Closed. |
| R6 Important, independent | A checked generation-0 snapshot could expose generation-1 ordinary bytes. | Track checked outer generation and require native snapshot/pin context to match the accepted generation before borrowing. Genuine retained-pin regression fails in review-red.log; current-generation nesting remains allowed. Closed. |
| R7 Minor, independent | No-unrelated-body metric only watched one helper. | Retain actual source locators/counts and instrument physical SQL body selections across lazy versions, ordinary records and segments. Rename the helper-specific metric to unrelated_version_body_reads and report observed unexpected physical selections separately. Final 1k/10k cases assert both counts and no off-path physical body selects. Closed. |
| R8 Minor, independent | Tuple reconstruction rehashed already-verified version/segment bodies solely to recreate checksum fields. | Carry bounded original checksum fields from metadata preflight in the same snapshot after raw-source validation. Keep canonical native defensive validation. Remove two version and one segment reconstruction hash passes; no cache/clean flag or new trust authority. Source and mutation regressions remain green. Closed. |
| A1 author | First overlap test attempted a forbidden negative valid_from. | Use a real generation-1 overlap, preserving the SQLite CHECK constraint. Initial work.log failure retained; source-tests.log35pass confirms corrected test. Closed. |
| A2 author | First race test used an UPDATE that does not change data_version on this SQLite build. | Use an actual independent write and verify RED with the in-snapshot guard disabled, GREEN with it enabled. Original failures remain raw history; no blind success claim. Closed. |
| A3 author / broad regression | Existing no-op race injection assumed the second epoch call occurred outside a transaction. Extra in-snapshot checks moved it into a locked reader and its external commit failed. | Trigger once at the first real transaction boundary after an epoch capture, preserving the original assertion: no-op returns0, generation remains0 and subsequent manifest access rejects stale authority. noop-red.log retains the lock; noop-fixed.log passes2.74s. No runtime exception is swallowed or guard weakened. Closed. |

Early test outputs are observations of earlier source. Only final combined and
clean-source checks in closure.md establish publication readiness. Full audited
admission remains mandatory; source bytes alone do not establish relation or
ordinary roster completeness. Direct raw SQL consumers remain a next admission
coverage gate, not a claimed capability of this adapter.

A4 author: the clean-source probe exposed avoidable repeated epoch SQL. Two physical-query-count tests fail before deduplication (6/8data_version calls instead of at most3). Entry checks now live in the common snapshot-start seam, with one pinned-view check, compatible nested checks and explicit uncertainty rejection. No caching or trusted-read bypass. Final security/session tests and clean year rerun verify the correction; the initial slower probe is retained as historical measurement.

Final closure evidence:77native-source/session cases131.07s,29clean launcher21.65s, two stronger physical-column selection cases7.16s and final clean raw/diagnostic eager/fresh canonical year all pass. The authoritative final runtime and exact source mapping are in closure.md/source-map.json. No second independent review or deferred finding.
