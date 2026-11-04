# Existing Sequence Append Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Certify existing counted-sequence appends through bounded authenticated predecessor reads and the existing central transaction.

**Architecture:** Replay the existing sequence mutator against a read-only accepted-content view. Compare the exact frozen delta, then compose semantic facts, physical scopes and leaf-owner witnesses with existing value/tail/insertion proofs.

**Tech Stack:** Python 3.12, SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-10-31-ate-sequence-append-design.md`

## Global Constraints

- Preserve 512 semantic input rows / 4 MiB; no original publication row omitted.
- At most 16 backings, 128 appended values, 512 predecessor reads and 4 MiB old-plus-new bytes per replay request.
- Replay is private, read-only, unregistered and never a publishing authority.
- Preserve checked fallback for empty/reference-bearing/nonappend/over-budget shapes.
- One independent package review; close every finding including Minor.
- No main merge, default activation, endurance or mature benchmark launch.

## Review Focus

- Missing or altered sequence sidecars and descriptors must not receive a certificate.
- New and rewritten scalar-leaf sources require exact catalog owner witnesses.
- Pure-type incoming policies and scalar/reference distinctions remain exact.
- Partial or over-budget replay must not contaminate accepted semantic facts.
- Failed commits and lost acknowledgements preserve the original atomic attempt.

### Task 1: Certify and compose the existing append frontier

**Files:**
- Create `simulation/ate_sim/persistence_proof_world_sequence.py`.
- Modify `persistence_proof_manifest_publish.py`, `persistence_proof_world_value.py`, `persistence_proof_world_backing_value.py`, `persistence_proof_world_tail.py`, `persistence_proof_world_insert.py` under `simulation/ate_sim/`.
- Test `simulation/tests/test_stage_0_6_proof_world_sequence.py`.

**Interfaces:** `prepare(store, request, versions)` updates private request sequence certificates, expected locator roots and tail facts only after exact validation. `certified(request, namespace, typed_key)` identifies exact frozen rows for the existing validators.

- [x] Reproduce a real native existing-sequence append invoking the full World audit.
- [x] Build bounded read-only replay and exact frozen-row equality; compose facts/scopes/source witnesses.
- [x] Verify 128-value leaf split, 4,096-value root split, duplicates, multi-call append and extend, mixed fresh owners, checked unsupported fallback and corruption/recovery.
- [x] Run affected tests and complete generated-year/fresh-process controls; measure the complete-year workload and preserve explicit limits.
- [x] Obtain one independent package review; resolve all findings with targeted validation.
- [x] Refresh exact runtime pin, verify harness/source fences, preserve receipts and publish one bundled full/proof validation.

Local package complete; publication starts one bundled full/proof workflow. Hosted completion and whole-year/mature targets remain open.
