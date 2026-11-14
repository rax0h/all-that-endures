# Coordinator publication read scope implementation plan

> Execute inline via superpowers:executing-plans; one whole-package independent review.

**Goal:** avoid repeated metadata proof work during one closed coordinator acknowledgement validation.
**Architecture:** replace its outer read_snapshot with existing checked_read_operation; preserve exact frozen plan, per-row checks and PublicationProof lifecycle.
**Tech Stack:** existing Python/SQLite, qualified313.
**Spec:** docs/superpowers/specs/2026-11-13-publication-read-scope-design.md

- [x] RED real native acknowledgement checked-head work bound.
- [x] Minimal context change; GREEN exact save/reopen, no scope survives return.
- [x] Existing validation-scope/publication-proof, callback/corruption/lease/
  borrowed-read/rollback/partial-ack recovery checks; preflight prior durations.
- [x] Fresh actual phase-work comparison and same-engine controls, then pinned
  raw A-B/B-A with tests/probes idle. Preserve compatible completed trials.
- [x] One independent review, close all findings, promote only measured benefit.
- [x] One bundled proof/full hosted gate only if retained; no per-finding CI.

Restart unit one small fixture/file or120s disposable input trial. Same input
archive expires December11; reserve15minutes publication. Reuse prior green for
unchanged scopes; no expensive constructor prerequisite or automatic full restart.

Implementation/local verification/review are complete. Exact-source hosted gate
status is authoritative in save-phase-attribution/report.md; these checkboxes do
not claim the hosted run or Stage0.6 has passed.
