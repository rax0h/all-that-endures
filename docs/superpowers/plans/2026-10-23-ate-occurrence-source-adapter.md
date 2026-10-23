# Owner/group Occurrence Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Authenticate complete raw owner/group placement pages without owner payloads.
**Architecture:** Existing occurrence table, pinned snapshots, explicit ordered source indexes and reviewed ordered proofs. No current World capability selects this adapter.
**Tech Stack:** Python3.12/SQLite/pytest.
**Spec:** `docs/superpowers/specs/2026-10-23-ate-occurrence-source-adapter.md`.

## Global constraints

- No World activation, decoding, alternate registry/publisher, main merge or endurance.
- Mandatory expected outer authority; test-only verified construction.
- Existing64-row operational metadata bounds; explicit1MiB metadata budget adjustable up to64MiB.
- Exact1..128 page limit; individual namespace/key/path fields <=4096 bytes fast path.
- Index creation explicit caller transaction, never ordinary read/open/save.
- Full successor suite in CI, no long-test polling.

## Review Focus

- Same placement can overlap with a DIFFERENT incarnation outside a group stream.
- Current-open/just-closed merge may hide duplicate neighbors behind LIMIT.
- Embedded-zero and prefix byte keys must sort exactly like SQLite tuples.
- Malformed UTF8 TEXT namespace must become integrity failure before object admission.
- A legacy/malformed index must fail instead of triggering unbounded sort or hidden migration.

### Task1: Closed physical source

**Files:** New `simulation/ate_sim/persistence_proof_occurrence.py`; `simulation/tests/proof_occurrence_fixtures.py`; `simulation/tests/test_stage_0_5_proof_occurrence.py`.
**Interfaces:** Exact types/functions/framing in spec; consume existing ProofMap/OrderRoot/verify_page and operational metadata preflight.

- [x] Write independent vectors, real-store pages/cursors, pin/context/allocator, same-relation agreement, corruption/overlap, missing-index, budget and transaction tests, including all Review Focus cases.
- [x] Run tests missing-module RED, implement minimal adapter/index seam; run all proof/store/identity regressions GREEN; commit.

### Task2: Work bounds, review, publication

**Files:** New `.github/tests/run_proof_occurrence_scaling.py`, `docs/performance/proof-occurrence-results.md`; extend existing CI and integration handoff.
**Interfaces:** Driver `--output PATH`, clean-source/runtime/driver/fixture hashes and immutable partial/per-size receipts;1k/10k/100k actual unrelated occurrence rows. Fixed8 group placements/4 owners/page4; fixed owner2paths. Exact values, zero payload work,<=512proof reads,<2MiB fixed heap, index plans no temporary sorting.

- [x] Commit driver, run bounded diagnostic. Retain setup/full construction separately from point timers and report limitations.
- [x] One fresh read-only whole-package review; Important/Critical RED/GREEN fix pass; affected tests and AST/YAML/bash checks.
- [x] Publish exact-tree expected-parent lease, launch successor suite/diagnostics and retain run link/pending status. Do not infer CI success from parent green.

## Ledger

Pre-flight: source rows and ordered certificates share exact scope/domain/position bytes; driver consumes test-only full-verified constructor, never mints production authority. Both owner/group views are physical projections of the same relation; full topology/payload/link/retirement consistency remains a separate publication gate.
Ruling: add explicit ordered source indexes during construction because existing expiry-leading indexes can require sorting full groups for pagination. Cost if wrong: additional copy/index construction; never hidden ordinary-open work or weakened completeness.
Baseline: local5a96c4f root24cbf3d equals published adf2d586; accepted CI39899113040 runtime12ab428b. No finished component is repeated.

Task1 implementation e51ddde:32 missing-module RED,37 source GREEN; three wrong partial/collation/DESC index cases separately reproduced RED and fixed. Initial346 affected GREEN28.95s; current-only diagnostic exact1k/10k/100k, no payload reads.
Final review: one fresh read-only gpt-6-astra high review5a96c4f..e51ddde. Two Important findings: inherited interval-index fallback can scan expired history; previous-pin filtering can scan unlimited newer candidates despite LIMIT. Supporting Minor: current-only SELECT/plan counters miss that VM work. No Critical findings.
Ruling: require actual and cached exact-placement/state interval indexes; forbid inherited legacy fallback. Cost if wrong: explicit construction/reopen may be required before the inactive reader can run; existing World paths unchanged.
Ruling: use bounded candidate fetch and explicit old-pin work-budget rejection when newer placements intervene, because the physical sorted stream cannot safely skip arbitrary new rows. Cost: general previous-pin selection remains unsupported in this fast path and MUST be completed before World activation. No unverified fallback or alternate publisher.
Review fixes in one pass: four missing-capability/index cases and two old-new frontier cases reproduced RED.43 source cases GREEN before added owner-frontier boundary coverage. Driver now measures old/current pages and newer frontier VM work; supporting diagnostic finding is addressed in this same pass. No second review.

Task1: complete.44 source cases GREEN;353 affected GREEN30.76s. Task2 diagnostic: clean7c922158, exact current/mixed-open-closed previous pages at1k/10k/100k, zero payload work, old-new frontier rejection2599VM upper bound each. Final review Important fixes complete; AST/YAML/bash and diff verified. Publication/CI launch to be recorded below; no candidate CI acceptance claim.

Task2: complete (exact-tree candidate3f57dfe4 published with expected-parent lease; successor39909955729 in progress; launch receipt retained). Candidate full-suite/scaling acceptance pending. General bounded old-pin selection remains a next mandatory implementation gate, alongside complete topology/manifests/publication; no World activation.
