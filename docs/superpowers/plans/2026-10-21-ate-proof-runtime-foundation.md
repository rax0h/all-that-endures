# ATE Proof Runtime Foundation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. The user selected Sol 6.1 inline implementation and authorized Astra's full direction. Continue without routine approval checkpoints.

**Goal:** Attribute persistent simulation work and eliminate repeated ownership reconstruction during eligible value-only assignments, preserving exact continuation.

**Architecture:** Add opt-in diagnostics outside the product hot path. Reuse the existing binding/coordinator authorities for topology-stable mutation certificates; keep content dirt distinct from structural dirt. Durable committed-state proofs, authenticated open and scrub integration follow as separate packages once the runtime boundary is measured.

**Tech Stack:** Python 3.12, SQLite, pytest, existing checked lazy persistence.

**Spec:** `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`.

## Global Constraints

- Preserve current exact canonical state, identity, causal history, RNG inputs, order, counters and recovery behavior.
- No whole-year transaction, clock reset, second canonical registry or unbounded clean cache.
- Existing stores remain readable; this foundation changes no persistent format.
- Working targets: warm year <=1 second, ordinary incremental save <=2 seconds, open <=10 seconds. A small fixture is not mature timing acceptance.
- No endurance chain or repeated polling. Long jobs require bounded phases and retained partial receipts.

## Review Focus

- Raw SQL writes, rollback and external commits invalidate runtime evidence.
- A scalar assignment with a reentrant/custom callback must use the conservative existing route.
- Aliases in unloaded or deleted owners remain exact and deletions never resurrect.
- Diagnostic timeouts/exceptions retain partial evidence and restore every instrumented method.
- Diagnostic key tracking is bounded; its distinct/repeat observations are samples, not exact archive cardinalities.

## Task 1: Opt-in attribution and complete phase receipts

**Files:** Create `simulation/performance_attribution.py`; modify `simulation/stage_0_5_mature_step_save.py` and `simulation/profile_stage_0_5_performance.py`; create `simulation/tests/test_stage_0_5_performance_attribution.py`; extend performance-runner tests.

**Interfaces:** `PerformanceAttribution(key_limit=2048)` is an optional context manager. `phase(name)` resets its bounded phase counters; `snapshot()` returns JSON-safe records. It wraps the imported runtime only inside its context, restores methods on every exit, and labels diagnostic evidence. Both runners accept `attributed=False` and CLI `--attributed`; comparison rejects different instrumentation. Existing defaults remain uninstrumented.

- [x] Write failing tests for real namespace read/repeat counts, disjoint primary subsystem time, bounded key tracking, exception cleanup and partial phase snapshots.
- [x] Write a failing regression requiring open IO in the mature runner; its session must be assigned before the measurement finalizer.
- [x] Run those tests and retain the expected red output.
- [x] Implement attribution with bounded encoded-key sampling, namespace/reason counts, nested exclusive wall/CPU accounting and opt-in wrappers. Include engine subsystems, save preparation/commit/publication, routing, group/owner checks, row checks and codec costs as separately identified overlapping call families.
- [x] Integrate runners, preserving authenticated source bindings, streaming hashes, time budgets and partial output.
- [x] Run attribution/runner/launch regressions; commit code and exact evidence.

## Task 2: Value-only mutation proof reuse

**Files:** Create `simulation/ate_sim/persistence_value_routes.py` and `simulation/tests/test_stage_0_5_value_topology_reuse.py`; modify native/indexed binding, bridge and coordinator integration only as required.

**Interfaces:** A private bounded route certificate binds exact object identity, full store/pin/codec/schema/database epoch, current topology revision and known notification hooks. The existing registry remains the only object authority. A successful scalar assignment marks value dirt without adding structural pending owners. Repeated eligible assignments reuse routes; structural and invalidated paths fall back.

- [x] Write failing real-fixture work regressions: repeated person/motive/skill and nested native scalar edits perform one initial topology resolution, mark all owners, save and reopen exactly.
- [x] Add alias replacement/deletion, raw SQL/rollback/external writes, hook changes, reentrant edits, nonfinite/custom values, save/pin transition and bounded-residency tests.
- [x] Run new tests to establish expected redundant-work failures before changing production code.
- [x] Implement narrowly proven scalar admission and value-only notification; retain existing structural journals and immediate reconciliation.
- [x] Run the new cases and existing indexed/native assignment, owner-witness, publication, corruption and recovery regressions. Fix every new failure before measuring speed.
- [x] Run a bounded populated first/warm/save profile. Compare actual work and exact output with the unchanged checked path; no extrapolated mature speed claim.
- [x] Commit the implementation and measured evidence.

## Task 3: Whole-package verification and durable-proof handoff

**Files:** Update this checklist and `docs/performance/proof-runtime-foundation-results.md`; add a bounded CI workflow only if local full-suite runtime cannot complete in-session.

- [x] Run the full simulation suite on the final runtime, retaining JUnit/log evidence. Do not repeat the 30-GB comparison before the attributed work warrants it.
- [x] Obtain a fresh-context final code review as required by executing-plans; fix important findings with red/green checks.
- [x] Publish only task-owned changes over the current remote head using a nonforced lease; leave unrelated handoffs intact.
- [x] Continue to a separate durable-transition-proof plan: exact immutable node/manifest format, copy upgrade, atomic data/root publication, complete index/absence proofs, old-pin retention and recovery. This foundation must not be called the durable proof system or target completion.

## Initial baseline and decisions

- Remote baseline `c2242b67afdf102228c7b067c376cabe3c8df193`, tree `9d4340e9e81eccd99b7f02f28f5ea0eab862d503`.
- Isolated local baseline `b731d6d` has the exact same tree; it preserves the earlier dirty checkout untouched.
- Baseline targeted assignment/owner-witness suites: 41 passed in 17.71 seconds.
- Test command prefix: `PYTHONPATH=/workspace/scratch/7905b656a1e1/review-venv/lib/python3.12/site-packages:.:simulation python -m pytest` (existing environment packages; no dependency installation).
- Ruling: execute inline after writing/self-reviewing this plan because the user's current instruction explicitly authorizes Sol to implement Astra's outline efficiently; do not ask them to reauthorize routine preparation.

Published candidate `848ebf4bb14bd14ace00ba604f23a61acd967ea4`; full suite/populated validation [39728517108](https://github.com/rax0h/all-that-endures/actions/runs/39728517108) is pending. Next: [durable proof map foundation](2026-10-22-ate-durable-proof-map-foundation.md).

Final checkpoint: run 39810513221 green, 3094 tests + 2 subtests; populated fresh restores passed. See acceptance receipt in docs/performance/run-39810513221/.
