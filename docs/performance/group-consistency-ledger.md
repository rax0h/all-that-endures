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
