# SDD ledger — plan: docs/superpowers/plans/2026-10-23-ate-group-consistency.md

Recovery: the temporary checkout was removed before three local commits were published. Restored GitHub baseline c4cfe473db93090ddabf25762fc26740846a6149. Old local test/scaling output is unavailable and will not be reused as current verification.

Ruling: reconstruct from the recorded contract and current accepted interfaces — no recoverable patch or Git objects were found — costs additional implementation/verification time and requires fresh review.

Pre-flight: tasks 1/2 share QueryScope/root reader and closed snapshot/codec helpers; task 3 consumes both readers and test-only full-verified constructors. Preserve existing certificate types and no production authority construction.

Prior independent reviewer failed on a usage limit without producing a review. No independent-review approval is claimed.

Task 1: complete — reconstructed root-selected query source and shared closed metadata preflight; 20 missing-module RED cases, followed by 63 query/projection tests GREEN in 9.39s. Tests cover actual newer populations 1k/10k, closed old intervals and empty roots. A local registry attribute naming error was corrected before the final green run.
