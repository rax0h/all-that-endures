# Version Source Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Authenticate raw fetched retained-version bytes against accepted content roots.

**Architecture:** Reuse exact content bindings, immutable ProofMap, existing store snapshots and expiry-aware exact-key selection. Certificates stay inactive in World.

**Tech Stack:** Existing Python3.12/SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-ate-version-source-adapter.md`.

## Global Constraints

- No World activation, format selection, decoding, main merge or endurance run.
- No production certificate constructor; expected commitment is mandatory.
- Own/join only existing explicitly owned bounded snapshots.
- Type/byte guards run in SQL before body transfer; default1MiB, explicit max64MiB.
- No full Python content map, no retained clean-node cache, no second registry.
- Full suite runs separately in successor CI; do not wait/poll long tests.

## Review Focus

- A coherently rechecksummed row must still fail its accepted content leaf.
- Interval overlap cannot hide behind the current-row optimization.
- An oversized TEXT checksum with early NUL cannot bypass byte-length guards.
- Delete/mutate must preserve exact previous-pin bytes without trusting current roots.
- Exceptions inside an explicitly owned read transaction must leave ownership intact.

### Task 1: Closed physical version reader

**Files:** Create `simulation/ate_sim/persistence_proof_version.py`, `simulation/tests/test_stage_0_5_proof_version.py`, `simulation/tests/proof_version_fixtures.py`.

**Interfaces:** Exact VersionCertificate/RawVersion/domain/commitment/read_version_bytes and VersionProofBudgetError in spec. Consume content preimages, Root/ProofMap, ProofNodeStore and actual LazyRecordStore.

- [x] Write independent framing vectors and real-store present/absent/raw-byte assertions; corruption, pin/generation/schema/context and all Review Focus cases. Test malformed2MiB SQL bodies fail under128KiB traced heap. Use full-verified test construction with SQL locator spill.
- [x] Run new test module; expected missing module RED, then implement exact interface and guarded interval query.
- [x] Run new module and all proof/store/failure regressions; expected all pass. Commit implementation.

### Task 2: Fixed access diagnostic, review and publication

**Files:** Create `.github/tests/run_proof_version_scaling.py`, `docs/performance/proof-version-results.md`; extend proof CI workflow and next integration handoff.

**Interfaces:** `--output PATH`, clean committed source/runtime/driver/fixture hash receipts;1k/10k/100k actual version rows. Fixed key0 presence and fixed missing key; literal exact result, single payload check/zero absence checks, <=256 proof reads,<2MiB heap. Separate full-verified construction and lifetime RSS; immutable partial receipts before each later size.

- [x] Commit driver, execute bounded diagnostic; expected exact1k/10k/100k with bounded work.
- [x] Validate AST/YAML/bash, run affected suite; expected all pass. One fresh whole-package reviewer; fix Important/Critical RED->GREEN once, ledger all rulings/minors.
- [x] Publish exact-tree leased branch update and launch separate successor full suite/scaling CI. Retain source/link and pending status. No wait for long suite; no performance target claim.

## Execution ledger

Pre-flight: Task2 consumes Task1's exact certificate/read interface; test constructor remains test-only. Existing root content bindings exclude valid_to; physical interval checks remain mandatory. Ruling: implement retained versioned data first because ordinary overwrites cannot preserve old-root payload availability. Cost if wrong: more integration work, never weakened World integrity.

Recovered baseline: local41962d2 root1474af84 equals published a0e6acf; runtime de69bd0717240beb09b8d25bafda150cb8228497. Query CI39890667390 authenticated green;3258 full tests,162 proof cases. No completed task is repeated.

Task1: complete (commit2bd0d3c; initial missing-module RED36cases; source39 GREEN; affected279 GREEN21.42s).
Task2: diagnostic complete on clean2bd0d3c, exact1k/10k/100k; presence/absence payload checks1/0, node reads4/3,5/3,5/5, heap<=13,083B. Review/publication/CI pending.

Final review: one fresh gpt-6-astra high read-only review,41962d2..2bd0d3c. One Important operational-metadata materialization issue; no Critical/Minor findings.
Ruling: accept bounded-memory finding despite inherited snapshot source. Add private optional snapshot preflight after BEGIN/before checked pin/head fetch, guarding existing64-row inventories and caller-budgeted legitimate metadata. Cost if wrong: shared snapshot regression; affected and validation-scope tests cover default and guarded callers, full successor suite required.
Review fix: eight cases independently reproduced RED (one capacity case already rejected); constant-only snapshot guards added,48 source cases GREEN before legitimate-large-metadata and invalid-budget coverage. No second review pass.
Final review exclusions ruled: no World activation/canonical admission/manifests/writer fencing; ordinary/segment retention unresolved; no mature speed claim; prior CI separate; unread corruption remains full-scrub/fetched-data responsibility. Publishing only an inactive raw-source adapter preserves each gate; cost if wrong is additional required integration, no release/format acceptance.

Final affected306/306 GREEN22.50s; source54cases included. Post-repair clean9f26548 diagnostic exact1k/10k/100k, presence node4/5/6, absence3/4/5, payload checks1/0; all bounds passed. AST/YAML/bash and diff checks verified. Publication/CI launch to be recorded below; checked boxes describe the concrete deliverables and must not imply candidate CI passed.

Task2: complete (exact-tree published cd50a80a, expected-parent branch lease, run39899113040 queued; raw launch receipt retained). Candidate full-suite/scaling CI acceptance pending; resume by inspecting this run/artifacts. No World activation or speed acceptance.
