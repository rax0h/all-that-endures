# Family publication scope Implementation Plan

> Execute inline via superpowers:executing-plans; one independent whole-package review.

**Goal:** reduce repeated metadata proof work during closed family/dependency acknowledgement.
**Architecture:** reuse existing checked_read_operation at two current read_snapshot boundaries, without removing row validation or changing acceptance state.
**Tech Stack:** existing Python/SQLite, qualified313.
**Spec:** docs/superpowers/specs/2026-11-14-family-publication-scope-design.md

## Global Constraints
- Exact frozen rows, dependencies, state, leases and deterministic continuation.
- Existing256KiB scope bound, no authority/cache lifetime beyond the closed read.
- No mature/default/main/endurance action; full suite once only if retained.

## Review Focus
- Wrong frozen delta/pin rejected before acknowledgement.
- Borrowed transaction grants no reusable metadata authority.
- Exception/corruption leaves no live scope or premature accepted state.
- Write/rollback or changed source after one operation is rechecked next time.
- Partial acknowledgement/retry retains the original recovery contract.

### Task 1: existing closed contexts and performance acceptance

Files: persistence_lazy_participants.py, persistence_history_dependencies.py,
tests/test_stage_0_6_family_publication_scope.py and family-publication-scope evidence.
Interfaces unchanged: validate_publication(delta, pin) returns None or raises.

- [x] Native32person RED checked-head bound<=10per family/dependency operation.
- [x] Replace exactly two read contexts; GREEN exact save/reopen and scope cleanup.
- [x] Related family/dependency/scope/corruption/recovery suites with prior hosted durations checked; retain compatible completed files.
- [x] One independent whole-package review; fix all findings within this group.
- [x] Preserve exact engine/input/runtime fences and state; raw A-B/B-A120s trials with CPU tests/probes idle, full instrumentation separate.
- [x] Promote only credible whole-save benefit; otherwise archive experiment and restore engine.
- [ ] One bundled hosted proof/full gate only for retained engine change.

Restart unit one test file (300s cap) or independent120s raw trial. No expensive
constructor prefix. Keep15minutes publication budget and original input bytes.

Ledger: family-publication-scope/progress.md. No shared task interfaces. Standing
user authorization selects inline execution without routine approval pauses.
