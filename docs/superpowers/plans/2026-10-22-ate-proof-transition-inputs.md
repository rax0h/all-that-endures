# Proof Transition Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Supply bounded final-path batch updates and exact content bindings needed by durable save transitions.

**Architecture:** Reuse canonical immutable ProofMap nodes and caller-owned SQLite transactions. A sorted-stream radix merge writes final changed paths once; pure content helpers bind exact stored bytes without World activation.

**Tech Stack:** Python 3.12, hashlib, existing SQLite node adapter, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-ate-proof-transition-inputs.md`, subordinate to `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`.

## Global Constraints

- No new World format is activated.
- No persistent clean-node cache or second canonical-object registry.
- The caller owns atomic rollback if a later input or callback fails.
- Namespace is exact UTF-8, nonempty and without NUL.
- Current targets remain open <=10s, incremental save <=2s and warm year <=1s.
- Preserve exact state, identity, order, RNG and recovery. No main merge.

## Review Focus

- A late malformed or failing generator must not publish a partial root; SQLite rollback restores rows (Task 1).
- Deletion promotes an unchanged corrupt sibling: reject it before returning a root (Task 1).
- Maximal 64-nibble path must remain bounded and canonical (Task 1).
- Typed source bytes may contain NUL and noncanonical-looking values: commit exact bytes (Task 2).
- Closing valid_to must not rewrite old content authority; content alone must not authorize interval selection (Task 2).

## Files and responsibility

- `persistence_proof_batch.py`: sorted-stream merge only.
- `persistence_proof_content.py`: pure physical-row content binding only.
- Two corresponding `simulation/tests/test_stage_0_5_proof_*.py` modules.
- `.github/tests/run_proof_batch_scaling.py`: source-bound, real SQLite diagnostic.
- Existing proof workflow: include new tests and diagnostic. Keep full-suite gate.
- `docs/performance/proof-transition-inputs-results.md`: exact evidence and limits.

### Task 1: Bounded batch merge

**Files:** Create `simulation/ate_sim/persistence_proof_batch.py`; test `simulation/tests/test_stage_0_5_proof_batch.py`.

**Interfaces:** Consumes `ProofMap`, `Root`, `Leaf`, `Branch`, exact `key_locator`; produces `update_sorted(proof_map: ProofMap, root: Root, changes: Iterable[tuple[bytes, bytes | None]]) -> Root`.

- [x] Write tests named `test_batch_matches_independent_mapping_and_canonical_sequential_root`, `test_only_final_nodes_are_written_once`, `test_empty_and_noop_batches_keep_root_identity`, `test_stream_rejects_duplicate_unsorted_and_malformed_changes`, `test_affected_corruption_and_promoted_sibling_are_rejected`, `test_maximum_depth_batch_is_bounded`, `test_sqlite_batch_rollback_and_generator_fault_keep_old_roots`. Assert exact mappings and old roots, final-reachable write inventories, no extra clean cache, <=66 reads for one fixed point edit. Use real SQLite for transaction faults, not a mock transaction manager.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_batch.py`. Expected: missing-module failures before implementation.
- [x] Implement `update_sorted` using one validated lookahead, a maximum 64-level radix walk and final-subtree construction. Reuse opaque unchanged roots, validate promoted boundaries and existing nodes through ProofMap checks. Reject malformed shape/types, non-increasing locators and invalid commitments with StoreIntegrityError. No root publication, sorting, commit or rollback inside the function.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_nodes.py simulation/tests/test_stage_0_5_proof_map.py simulation/tests/test_stage_0_5_proof_store.py simulation/tests/test_stage_0_5_proof_batch.py`. Expected: all pass.
- [x] Commit `feat: merge proof map deltas by final affected paths`.

### Task 2: Exact immutable source commitments

**Files:** Create `simulation/ate_sim/persistence_proof_content.py`; test `simulation/tests/test_stage_0_5_proof_content.py`.

**Interfaces:** Produces `version_key(namespace: str, typed_key: bytes) -> bytes`, `record_key(namespace: str, typed_key: bytes) -> bytes`, `segment_key(namespace: str, ordinal: int) -> bytes`. Produces `version_commitment(namespace, typed_key, *, valid_from, codec_version, record_schema, memberships, payload) -> bytes`, `record_commitment(namespace, typed_key, *, last_changed_generation, codec_version, record_schema, payload) -> bytes`, `segment_commitment(namespace, ordinal, *, created_generation, codec_version, element_count, first_id, last_id, payload) -> bytes`. Ordered fields/tags/types exactly as Spec table; invalid inputs raise StoreIntegrityError. No dependency on Task 1 internals.

- [x] Write independently framed vector tests for all keys/commitments, altered-field parametrization, invalid namespace/types/counters, exact opaque-byte preservation and a 2MiB payload incremental-hash heap bound (<128KiB beyond caller-owned input). Pin no `valid_to` parameter and equal content across interval close by binding real unchanged source fields, not by replacing the existing interval reader.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_content.py`. Expected: missing-module failures.
- [x] Implement the exact signatures and framing above. Return raw 32-byte SHA256 digest for content and framed bytes for keys; never decode payloads or accept cached checksum strings as payload authority.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_content.py simulation/tests/test_stage_0_5_proof_batch.py simulation/tests/test_stage_0_5_proof_store.py`. Expected: all pass.
- [x] Commit `feat: bind proof leaves to exact immutable source bytes`.

### Task 3: Bounded SQLite construction evidence and CI

**Files:** Create `.github/tests/run_proof_batch_scaling.py`, `docs/performance/proof-transition-inputs-results.md`; modify `.github/workflows/stage-0-5-proof-map-validation.yml`.

**Interfaces:** Consumes Task 1 `update_sorted`, existing ProofNodeStore and continuation_receipts. Driver CLI `--output PATH` refuses existing output, requires clean tracked source, records HEAD/runtime/driver hash. Stream deterministic keys through a SQLite TEMP sorting table keyed by locator, cache 2MiB, temp_store=FILE. Measure spill staging, batch construction and fixed point edit separately. Build independent 1k/10k/100k maps; final physical nodes must exactly equal the reachable final set, checked with a SQL-backed visited inventory instead of a Python full-map set. Point edit must use <=66 node reads/<=65 new writes and <512KiB traced heap; batch heap <2MiB (includes cursor/merge, excludes already completed staging), no Python clean cache. Record process RSS separately. Do not collect nodes or benchmark World latency.

- [x] Run real diagnostic after committing tracked driver; retain immutable source/per-case/summary receipts, trace counts, database size and timings. Expected: no transient construction nodes; each fixed point edit stays bounded. No unit tests that merely inspect script text.
- [x] Extend existing CI primitive command to new test files and run the batch driver with 15-minute process budget. Retain logs/XML/JSON, not SQLite. Validate YAML and shell syntax; keep the separate complete simulation suite.
- [x] Run all affected proof/incremental-store failure tests; fresh final whole-package review once, fix Important findings RED->GREEN. Record remaining architecture boundaries and exact source authority, publish and launch CI. Expected: focused suite green; full suite reported pending until actual completion. Do not wait in chat for it.
- [x] Commit `test: retain bounded batch proof construction evidence`.

## Self-review

This plan covers the transition-input spec only. It does not claim the complete
World integration plan exists. Complete topology/query roots, manifests,
payload/root retention, upgrade and actual save/open consumption remain explicit
subsequent packages; ordinary-record payload retention is a blocking design
requirement before activation. Task 3 consumes Task 1's exact signature and Task
2 is independent. Each review focus has a named owning test.
