# Proof placement read implementation plan

Disposition: experiment completed; proposal retained as patch/tests, no production
landing or fullCI. Raw latency did not justify it. See identity-point/report.md.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Reduce repeated owner-wide identity validation in proof-only recursive reads.
**Architecture:** Reuse the existing native exact occurrence proof, then apply current coordinator overlay; retain full owner fallback elsewhere.
**Tech Stack:** Python and SQLite, existing persistence APIs only.
**Spec:** docs/superpowers/specs/2026-11-11-proof-placement-read-design.md

## Global constraints

Keep all physical/owner/group/allocator/pin/head/epoch checks. No certificate or
cache retained across callbacks, transactions, steps or yields. Preserve ordinary
audited complete-owner semantics and all mutation/save/recovery closures. Use the
full qualified local fingerprint; no mature launch or old authority update.

## Review focus

Overlay hits must not hide physical SQL drift. New/private descendants retain
canonical identity. Default/audited readers keep full completeness checks. Point
absence is authenticated and never suppresses a non-KeyError failure. Mutation
rollback/recovery still authenticates the complete affected closure.

### Task1: Exact placement read boundary and recursive consumer

Files: modify persistence_lazy_identity_coordinator.py and persistence_history_runtime.py;
create simulation/tests/test_stage_0_6_proof_placement_reads.py.
Interface: IdentityCoordinator._placement_for_read(owner,path)->int|None;
decode calls it only where it currently extracts one incarnation from _owner_changes.

- [ ] Add real proof-only recursive reads and assert no decode->whole-owner calls
  with cProfile; positive/negative native occurrence checks and overlay cases.
- [ ] Observe RED work-count behavior before production edits.
- [ ] Implement point-path boundary with exact native proof-only selection and
  unchanged full-owner fallback. Change only decode's placement comparison.
- [ ] Run new tests plus existing native identity, proof opening/session,
  recursive alias/replacement/cycle/rollback controls. Expected: all pass.

### Task2: Measurement, review and evidence

Files: small-operation-profile/identity-point/*; same bounded-genesis/closure.md;
include new fast controls in existing proof-map CI primitive step.
Interface: existing factorization/compare.py consumes immutable small input and
emits actual source/import-fenced raw/profile phase reports and fresh continuation.

- [ ] Measure sequential raw baseline/candidate and separate candidate profile.
- [ ] Compare exact saved year2/year3 semantics, raw latency and owner/SQL work.
- [ ] One independent whole-package review; fix all findings in this group.
- [ ] Commit/publish exact tested source; one bundled full/proof validation only
  after focused correctness and measurements justify the candidate. Old greens
  apply only to the old engine. Keep mature acceptance open.
