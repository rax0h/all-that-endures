# SDD ledger — plan: docs/superpowers/plans/2026-10-23-ate-group-consistency.md

Recovery: the temporary checkout was removed before three local commits were published. Restored GitHub baseline c4cfe473db93090ddabf25762fc26740846a6149. Old local test/scaling output is unavailable and will not be reused as current verification.

Ruling: reconstruct from the recorded contract and current accepted interfaces — no recoverable patch or Git objects were found — costs additional implementation/verification time and requires fresh review.

Pre-flight: tasks 1/2 share QueryScope/root reader and closed snapshot/codec helpers; task 3 consumes both readers and test-only full-verified constructors. Preserve existing certificate types and no production authority construction.

Prior independent reviewer failed on a usage limit without producing a review. No independent-review approval is claimed.

Task 1: complete — reconstructed root-selected query source and shared closed metadata preflight; 20 missing-module RED cases, followed by 63 query/projection tests GREEN in 9.39s. Tests cover actual newer populations 1k/10k, closed old intervals and empty roots. A local registry attribute naming error was corrected before the final green run.

Task 2: complete — 41 missing-module RED cases followed by 41 group cases GREEN in 9.14s. Selected owner TEXT/BLOB interval rejection is included. Retained reanchor, live-empty versus range-retired absence, coherent cross-root inconsistencies, canonical links, exact owner paths and byte/member budgets are covered.

Author verification: first affected run510 passed in54.77s. Initial1k/10k/100k scaling passed with zero owner/archive bodies and constant8/8/5 metadata bodies, old nonempty/empty query VM<=999/799. Those receipts use pre-hardening runtime ab90b00 and are superseded by the final matrix below.

Author fix: Python equality aliases bool/int in decoded link IDs, group anchors and owner-radix leaf paths. Three coherent-corruption tests failed (DID NOT RAISE), then the join was hardened with exact typed encoding and exact leaf path hash. Focused107 cases passed in16.89s before the final extra capability/ordinary tests.

Parent acceptance restored: authenticated run39981711210 succeeded for5da5505, runtime c7c8721. Both artifact ZIP SHA256 digests matched; XML has3450 testcase elements and3452 declared cases including2subtests, no errors/failures;356 dedicated proof cases. This accepts only the prior package.

Task 2 extended verification:68 query/group tests passed in14.04s after the three typed-alias RED reproductions and hardening. Includes explicit selected/lookahead large-key budget, nested checked snapshot, coherently checksummed native head metadata rejection, and ordinary current/retained metadata without old-body admission. Fresh matrix will bind this hardened runtime.

Final review: independent fresh-context review c4cfe473..53fa319. No Critical/Minor findings; one Important embedded retirement-header typed alias. Four regression cases failed before the fix. Final affected run521 passed in53.71s after strict checked_header + encoded comparison. Full suite is delegated to candidate CI and remains pending until that run is authenticated; no full-suite-green claim for this package.

Final: fixed embedded retirement-header aliases — test_embedded_retirement_header_rejects_bool_aliases (directory/root count, height and population)4 RED→GREEN cases within affected521/521.

Final: Ruling: World admission, target existence/kind, full topology remain gated — this component returns raw checked metadata only — cost if misread is unsafe object admission; no production World caller selects it.
Final: Ruling: production authority/publication/fencing/manifests/collection remain subsequent integration — expected commitments must come from existing verified outer authority — cost if ignored is accepting unauthoritative roots or unsafe collection.
Final: Ruling: unselected physical inventory remains separate full audit — accepted roots select logical results — cost if ignored is treating bounded reads as a physical corruption scrub.
Final: Ruling: descriptor/range counts do not prove complete allocator inventory — complete inventory/publication checks remain required — cost if ignored is missing global topology inconsistencies outside the requested group.
Final: Ruling: historical ordinary bodies remain unavailable — retained group metadata cannot admit overwritten ordinary payloads — cost if ignored is restoring the wrong generation's object body.
Final: Ruling: final scaling/full CI require their own exact-source receipts — independent focused review is not performance or full-suite acceptance — cost if ignored is overstating unmeasured World behavior.

Scaling investigation: two hardened repeats failed during fixture construction under primary Python's SQLite3.53.1 (SQLITE_READONLY; later SQLITE_CORRUPT invalid rootpage). The first database reopened with quick_check OK and accepted a rolled-back write probe. The second persisted a seek-table rootpage beyond its file page count. Neither failed run is accepted performance evidence. System /usr/bin/python3 has SQLite3.45.1, matching hosted CI. Next matrix uses that interpreter; root cause of the primary-runtime database failures remains unresolved, with no speculative production fix.

Task 3 evidence: final complete1k/10k/100k matrix under system SQLite3.45.1 (same version as hosted CI), measured local headacc0814/runtime985952d. Current/retained/successor group metadata bodies8/8/5, unrelated owner/archive bodies0 at all sizes. At100k instrumented reads29.67/28.67/18.71ms. Old nonempty/empty queries VM<=999/799 with0payloads and actual newer populationsN/N+1. Source/runtime/driver/fixture hashes and all exact-size receipts verified. Failed3.53.1 repeats excluded, root cause remains unresolved.

Task 3 publication: proof-job source receipt added to authenticate the immutable CI candidate alongside existing driver and full-suite source receipts. Final candidate publication/launch below; full-suite acceptance pending.

Task 3: implementation, review fix, local affected tests and exact-source scaling complete; candidate 09b8dc251fe9c0073de2c0e7cd88be727c1db6fe published with tree 2159b9e10b4071c868e2145471a7a52958fe32eb. CI 40013683423 queued; full-suite acceptance pending. No main merge/endurance/long polling. Launch receipt records equivalent local candidate and measured runtime.
