# Owner reference projection implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind checked physical-owner payload references to complete committed occurrence roots.
**Architecture:** Compose existing content/occurrence source readers in one snapshot; use the five existing adapters and a closed storage-value codec. No new registry or publisher.
**Tech Stack:** Python3.12/SQLite/pytest.
**Spec:** docs/superpowers/specs/2026-10-23-ate-owner-reference-projection.md

## Global Constraints

- No World activation/main merge/endurance; external accepted authority mandatory.
- max_bytes=1048576, max_references=4096, max_metadata_bytes=1048576; supported arguments as spec.
- Field4096bytes, parsed inventory32768nodes/depth64; zero child/archive payload reads.
- Preserve caller transactions; no hidden schema construction or legacy interval fallback.

## Review Focus

- Different but independently valid content/occurrence authorities must fail on mismatch.
- Immutable Ref/frozenset/key-side references retain exact raw paths and numeric/NaN semantics.
- No mutable World record/custom codec hook executes during storage projection.
- Missing body cannot relabel nonempty topology as absence; empty body/root remains exact.
- Errors/oversized stored fields fail closed in one owned snapshot without archive allocation.

### Task 1: Checked projection composition

**Files:** Create simulation/ate_sim/persistence_proof_projection.py; simulation/tests/proof_projection_fixtures.py; simulation/tests/test_stage_0_5_proof_projection.py. Narrow optional interval list in persistence_proof_occurrence._require_indexes.
**Interfaces:** Spec API consumes VersionCertificate/SeekOccurrenceCertificate; returns RawOwnerProjection. Existing helpers keep defaults.

- [x] Write literal five-family, reference-tag, coherent mismatch, allocator/absence, restricted decode, budgets, corruption, current/old-pin and transaction/index tests. Run missing-module RED.
  Run: PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_stage_0_5_proof_projection.py
  Expected: missing-module failures, then all pass after implementation.
- [x] Implement the spec API and closed codec with adapter reuse; run focused proof and affected store regressions GREEN. Commit.

### Task 2: Measured bounds, review and publication

**Files:** .github/tests/run_proof_projection_scaling.py; proof CI; docs/performance/owner-projection-results.md and owner-projection evidence; NEXT_INTEGRATION.
**Interfaces:** Consumes Task1 reader and test-only full verified fixture construction. Source/driver hashes and phase receipts use continuation_receipts.

- [x] Commit driver; clean-source1k/10k/100k runs assert exactly one selected source payload check/SELECT and no archive/child body reads, exact current/old-pin values and bounded metadata/heap. Record construction separately.
  Expected: three complete exact receipts with source/runtime hashes and zero unrelated payloads.
- [x] Fresh whole-package review (one required reviewer), one Important/Critical RED/GREEN repair pass; retain every ruling and deferred minor. Run syntax/diff and affected suite.
  Expected: green tests and no unresolved Important/Critical findings.
- [ ] Publish exact tree with expected-parent branch lease, launch successor full suite plus diagnostics, retain actual pending launch receipt. Do not poll long CI.
  Expected: exact tree equality and actual CI link, no parent-success substitution.

## Ledger

Pre-flight: Task1 reader/certificate interfaces match Task2 fixture/driver; full verified construction stays outside read timers. Existing dedicated task checkout/branch is preserved from prior authorized work. Accepted CI is baseline; no duplicate full-suite rerun before implementation.
Ruling: limit this component to five existing physical-owner adapters; a generic World object walker would invent ownership semantics. Complete topology/target existence/World admission stay gated. Cost if wrong: later integration needs more adapters, never a silent bypass.
Ruling: use a closed WorldCodec storage-value subset, not caller hooks or mutable restoration. Cost if wrong: unsupported/custom payloads require a separately checked path.

Task1:30 missing-module RED cases;36 focused cases after API guard additions and113 projection/occurrence cases pass. Closed codec returns original source bytes; metadata helper defaults unchanged. No runtime defect observed. Final task command recorded separately by task-done.

Final review: three Important findings accepted and reproduced by6 RED regressions: inherited head mutable restoration/instance hooks, surrogate encoding outside StoreError, delegated budget exception types. Repaired once; pre-repair matrix superseded. Minor deferred: raw pytest evidence whitespace; source/doc diff check excludes *.log. All declined-to-judge rulings and costs in owner-projection/final-review.md. Initial affected XML442 tests/0 failures/0 errors, exit0; console log partial. Successor suite must validate repaired runtime.

Repaired source1dec047 runtime c7c87217e0fb7ec67a93a49003767ef0d785480a:43 projection/449 affected cases pass,209.69s. Six original review regressions RED→GREEN plus delegated field-budget test. Clean-source repaired1k/10k/100k matrix exact; one selected source payload check/SELECT each and zero unrelated payloads. Source/schema/snapshot bounds remain explicit; no World performance claim. Syntax checks and scoped whitespace check pass. Task2 final check validates these receipts and actual CI launch without repeating passed tests.
