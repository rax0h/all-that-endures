# Root-ordered Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return exact old-pin ordered pages without scanning/rejecting newer rows.
**Architecture:** Immutable exact-byte radix seek index in existing SQLite transaction; root-selected positions plus checked exact physical rows. Existing World paths unchanged.
**Tech Stack:** Python3.12/SQLite/pytest.
**Spec:** `docs/superpowers/specs/2026-10-23-ate-root-ordered-selection.md`.

## Global constraints

- No World activation, alternative canonical registry/publisher, main merge or endurance.
- Expected root/certificate authority mandatory; production construction/publication remains gated.
- Keys <=32768bytes, values32bytes, nodes<=131072bytes; source fields<=4096bytes fast path.
- Caller owns all schema/write transactions and rollback; no clean-node cache/GC.
- Full suite in successor CI; no polling long tests.

## Review Focus

- Terminated empty/prefix keys must preserve exact lexical order, including absent middle cursors.
- Deletion compression and split prefix must still authenticate child path/count.
- Deep prefix chains must not cause recursion or quadratic Python path retention.
- Coherent unselected SQL surplus must never enter committed-root results; don't claim it was scrubbed.
- Old nonempty and empty scopes must remain exact despite large newer populations.

### Task1: Immutable ordered seek index

**Files:** `simulation/ate_sim/persistence_proof_seek.py`, `simulation/tests/test_stage_0_5_proof_seek.py`.
**Interfaces:** Exact OrderedSeekMap/storage/bytes operations in spec; existing Root type.

- [x] Write vectors, model/rebuild/retained-root/no-op/corruption/stream/rollback/deep-prefix tests; run missing-module RED.
- [x] Implement iterative seek and SQL-spilled path-copy updates. Run all proof regressions GREEN, commit.

### Task2: Root-selected physical occurrence pages

**Files:** `simulation/ate_sim/persistence_proof_occurrence_seek.py`; `simulation/tests/proof_occurrence_seek_fixtures.py`, `simulation/tests/test_stage_0_5_proof_occurrence_seek.py`; narrow optional index-check helper in old occurrence adapter.
**Interfaces:** SeekOccurrenceCertificate and read_occurrence_seek_page in spec; reuse RawOccurrence/scopes/OccurrencePage, guarded snapshots/allocator and exact interval selection.

- [x] Write exact old/current arbitrary-cursor, root/source corruption, alias reassignment/delete and transaction tests; run RED.
- [x] Implement root selection and exact physical admission only. Run affected tests GREEN, commit.

### Task3: Bounded evidence, review and publication

**Files:** `.github/tests/run_proof_seek_scaling.py`, proof CI, `docs/performance/ordered-seek-results.md`, evidence/next integration.

- [x] Commit driver; on clean source run1k/10k/100k node-update and old/new source diagnostics, no payload work and exact results. Distinguish root-authority logical results from full physical scrub.
- [x] Fresh whole-package review; fix Important/Critical RED/GREEN once; retain every ruling/minor. AST/YAML/bash and affected suite GREEN.
- [ ] Publish exact-tree expected-parent branch lease, launch full successor CI and retain link/pending state. No parent-result substitution.

## Ledger

Pre-flight: source adapter consumes root's exact byte positions/32byte row commitments; generic seek index never decodes World state. Both mutations and physical publication must later join existing commit protocol.
Ruling: add a persistent exact-key ordered radix index rather than using SQL filtering or duplicating full per-generation scopes. Cost: another bounded proof-node format and construction/integration work; no weakening of World integrity.
Ruling: root defines committed logical membership; unselected physical surplus is audit work, never admitted. Cost if wrong: full inventory conformance must be established at construction/transitions before activation; current World path remains untouched.
Baseline: restored published05c755de, root433cc2accbab9b5df05cb1eadf94db243fd87a01. Accepted predecessor39909955729 artifacts authenticated. Workspace maintenance recovery repeated no finished implementation.

Implementation: 36 focused cases pass. Reusable TEMP workspace is prepared before a streamed cursor opens; per-operation rows are removed with DML. RED: dropping a per-update TEMP table locked an active SQL cursor. Sorted construction now writes final nodes only; RED: 200 keys previously wrote571 nodes against399 maximum. A mistaken literal vector order was corrected without changing product behavior. Logs retained under docs/performance/ordered-seek.

Fresh review: no runtime defects/Critical; Important evidence gap accepted (large frontier only reached old empty group), RED population assertions reproduced2 failures, fixed test+driver so each measured group gets size newer placements. Minor parser coverage accepted and added in same pass. No runtime edits. Corrected clean-source matrix supersedes initial receipts; all exclusions ruled explicitly in ordered-seek/final-review.md.

Corrected clean-source matrix2746c5b:1k/10k/100k entries; point node reads/writes4/4,5/5,6/6. Both old groups have exactly size newer placements. Group/owner/empty VM upper bounds1799/1699/999 at every size, exact pages, zero payloads and budget rejection.53 focused and406 affected tests pass; syntax/diff pass. Source runtime dcea4f0686b6ceb7bc4eaacc3441236c4ad08327. Receipts retain construction/full-audit/transition/database/RSS separately.
