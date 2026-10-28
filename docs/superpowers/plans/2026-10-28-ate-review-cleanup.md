# Close accumulated persistence review findings

> Execute inline with superpowers:executing-plans; one independent whole-package review. User requires Minors closed within their work group, superseding generic defer-Minors guidance.

Goal: reconcile and close all older recorded Minor findings in the persistence proof work, with evidence, and install the standing no-carryover rule.
Spec: docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md plus user's explicit cleanup instruction.
Architecture: preserve accepted authorities/publisher/recovery; lifecycle guard before closed DB access; operation-local reuse of authenticated Event-ID raw body, preserving schema/revision/checksum and budgets. Retain missing tests in owning test modules. Clarify existing128page per-backing/global512row/4MiB contracts and test composition. Keep original review logs as history with linked closure register.
Constraints: no main/default/endurance; do not poll long CI. Latest shrink candidate7ba221c is awaiting hosted acceptance; cleanup does not assume it green.
Review focus: cache schema/revision/budget safety and lifetime, closed-session no writes, corruption probes not merely malformed setup, retained parent+child certification/recovery, complete reconciliation of historical Minor notes.

- [x] Inventory all recorded deferred Minors; record origin and exact closure evidence in docs/performance/review-cleanup/register.md.
- [x] RED closed save/resolve exception and duplicate Event-ID body read tests; fix, GREEN.
- [x] Retain rollback/callback, raw-target corruption, owner dedup/shared-budget/late kind, nested/map/branch negative, frozen parent+child certification and fixed-shape classifier boundary regressions. Existing-correct behavior may pass on first run; do not fabricate failures.
- [x] Refresh native header; clarify/test per-backing cap; classify raw-log whitespace as preserved evidence, not open product work.
- [x] Run relevant tests, native regressions and affected bounded matrix; one independent review, close all actionable findings, record source hashes.
- [ ] Publish one reviewed candidate; full/proof/all28 matrices remain hosted gates, no long polling.
