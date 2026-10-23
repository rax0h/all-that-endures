# Query Source Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read authenticated ordered pages from real pinned SQLite query rows without rereading owner/history payloads.

**Architecture:** Bind source scope/store/codec/generation to the reviewed ordered certificates, check fetched physical row metadata and verify page adjacency. Use existing store snapshots; only explicit test/diagnostic fixtures construct accepted test roots. Default World paths remain unchanged.

**Tech Stack:** Python3.12, SQLite, existing LazyRecordStore and proof primitives, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-ate-query-source-adapter.md`, subordinate to the incremental-proof architecture.

## Global Constraints

- No existing World reader/publisher or format capability selects this adapter.
- No payload/key decoding occurs in the read adapter.
- The reader selects NO `lazy_record_versions`, `records` or `segments` payloads.
- Never catch integrity errors to return a result from the old path.
- Full copy/import validation must establish owner/query completeness before anchoring the certificate.
- No main merge, endurance job or claim of mature interactive performance.

## Review Focus

- A plausible but unchecked SQL projection must not become accepted authority (Task1 contract/fixtures).
- Current/previous rows at the same position must reject overlap rather than merge away duplicates (Task1).
- Empty results and limit-boundary lookahead must reject missing/forged endpoints (Task1).
- Repeated typed keys at distinct ordinals must remain distinct and ordered (Task1).
- Corruption of fetched metadata must fail even when its logical position still matches the root (Task1).

### Task 1: Bound actual source query pages

**Files:** Create `simulation/ate_sim/persistence_proof_query.py`; test `simulation/tests/test_stage_0_5_proof_query.py`; test utilities `simulation/tests/proof_query_fixtures.py`.

**Interfaces:** Frozen QueryScope/QueryCertificate/QueryPage and exact `query_domain`, `member_commitment`, `certificate_commitment`, `read_query_page` signatures/encodings from Spec. Consumes ProofNodeStore/ProofMap/OrderRoot/OrderEntry/verify_page. A single closed reader operation owns or joins the existing explicitly owned read snapshot; arbitrary borrowed transactions fail.

- [ ] Write independent binding vectors and real-store tests for exact pages/cursors/duplicates, zero payload SELECT/check counters, previous/current pin separation, released/foreign/stale pins, wrong certificate/context/root, metadata checksum/type/interval corruption, missing/surplus rows, visible overlaps, false empty boundaries and invalid limits/cursors. Fixtures build only after full verification; no test-only production methods.
- [ ] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_query.py`; Expected missing-module failures before implementation.
- [ ] Implement exact physical scope and page binding, bounded ordered SQL seeks/merge with existing current/open/closed indexes, all-fetched-row checks and ordered verifier. Return raw key/ordinal metadata and authenticated continuation only; no source payload reads or object exposure.
- [ ] Run new tests plus all existing proof tests; Expected all pass. Commit `feat: verify pinned query pages against real source rows`.

### Task 2: Actual-store scaling evidence and successor CI

**Files:** Create `.github/tests/run_proof_query_scaling.py`, `docs/performance/proof-query-results.md`; modify existing proof validation workflow.

**Interfaces:** Driver `--output PATH`, immutable source/partial/per-case receipts on clean committed source. Use actual LazyRecordStore commit API for fixed8 query owners with two distinct membership ordinals each and1k/10k/100k unrelated ordinary archive records. Build fixture proofs after one full verify per case, outside timing. Compare old checked limited query and new proof page exactly; record payload-check counts and SQL reads separately. New reader gate: zero source payload SELECT/checks, <=512 proof node reads, <2MiB traced heap, exact results and continuation. Record construction/RSS separately; source/driver hashes mandatory.

- [ ] Commit driver/workflow, validate Python AST/YAML/bash syntax, then run bounded15-minute diagnostic on clean source. Expected all sizes pass with exact results and zero new-reader payload work; preserve partial receipts before later phases.
- [ ] Run all proof tests plus incremental-store, store-failure and actual pinned-store regressions; Expected all pass. One fresh whole-package review, fix Critical/Important RED->GREEN once and retain findings/rulings.
- [ ] Publish exact-tree leased update, launch separate full suite plus scaling CI and retain link. Expected new full suite pending until observed green; no parent-result substitution or waiting for long CI.
- [ ] Commit evidence/handoff. Source adapters do not activate World; next mandatory integration gates remain explicit.

## Self-review

Task2 consumes Task1's exact raw metadata interfaces and test-only verified fixture utility. Each Review Focus has owning tests. This package closes query row/page consumption only; it does not represent a completed global manifest, source constructor, topology checker or World adoption path.
