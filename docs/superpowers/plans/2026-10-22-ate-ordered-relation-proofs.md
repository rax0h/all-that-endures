# Ordered Relation Proofs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Authenticate complete ordered pages and local relation transitions without scanning unrelated rows.

**Architecture:** Bind adjacency and extrema through the existing immutable ProofMap. Verified parent witnesses and bounded SQLite staging supply a single final-path transition. These certificates remain inactive in World until manifest/source/publication integration.

**Tech Stack:** Python3.12, SQLite, existing proof nodes/map/batch/store, pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-ate-ordered-relation-proofs.md`, subordinate to the approved incremental-proof architecture.

## Global Constraints

- Existing readers/checks remain active.
- All witnesses refer to the SAME parent root, even for adjacent edits.
- Both functions REQUIRE an existing caller SQLite transaction.
- No whole Python relation or delta dictionary, retained clean-node cache or second object registry.
- Root/payload retention, manifests, upgrade, writer fencing, atomic publication and actual World consumption remain gates.
- No main merge or endurance run; full successor suite runs in CI.

## Review Focus

- Empty byte keys versus absent extrema must remain distinct (Task1).
- A plausible empty/truncated SQL result must fail without authenticated range boundaries (Task1).
- Adjacent insert/delete batches use parent witnesses, avoiding mixed-root neighbor assumptions (Task2).
- Disjoint changed islands must preserve untouched gaps through authenticated boundary keys (Task2).
- A late stream failure or callback failure after writing must leave accepted roots recoverable through caller rollback (Task2).

## File responsibilities

- `simulation/ate_sim/persistence_proof_order.py`: exact ordered descriptors/entry commitments and page verification.
- `simulation/ate_sim/persistence_proof_order_edit.py`: checked construction and staged verified transitions.
- Two corresponding `simulation/tests/test_stage_0_5_proof_order*.py` files.
- `.github/tests/run_proof_order_scaling.py`: real SQLite 1k/10k/100k fixed-work diagnostic.
- Existing proof CI workflow: include these tests and diagnostic.
- Results under `docs/performance/proof-order-*`; no World format selection.

### Task 1: Ordered commitments and complete pages

**Files:** Create `persistence_proof_order.py`, `test_stage_0_5_proof_order.py` in the directories above.

**Interfaces:** Produce frozen `OrderEntry(key:bytes,value:bytes,previous:bytes|None,following:bytes|None)` and `OrderRoot(index:Root,first:bytes|None,last:bytes|None)`; `entry_commitment(domain,entry)->bytes`, `root_commitment(domain,root)->bytes`, `query_order_key(ordinal,typed_record_key)->bytes`, `verify_page(map,root,expected_commitment,*,rows,after=None,before=None,limit=128,boundary=None)->tuple[OrderEntry,...]`. Types, tags, framing and page rules exactly as Spec.

- [x] Write independent framing vectors and SQL-order comparison. Write named page tests for full/partial/ranged pages, legitimate and false emptiness, omission/reorder/surplus/duplicates, forged descriptors and neighbors, stale/wrong-domain roots, empty-byte endpoints and input iterator limit+1. Assert exact returned entries and rejection, not source text.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_order.py`; Expected missing-module failures before implementation.
- [x] Implement exact interfaces with streaming bounded page materialization, mandatory expected descriptor commitment, authenticated entry membership and adjacency/range checks. Reject unused boundary witnesses.
- [x] Run the new module plus existing proof node/map/batch tests; Expected all pass. Commit `feat: authenticate complete ordered proof pages`.

### Task 2: Verified staged relation transitions

**Files:** Create `persistence_proof_order_edit.py`, `test_stage_0_5_proof_order_edit.py`.

**Interfaces:** Consume Task1 types/commitments and existing `update_sorted`. Produce frozen `OrderEdit(key:bytes,value:bytes|None,old:OrderEntry|None,previous:OrderEntry|None,following:OrderEntry|None)`, `build_ordered(map,db,rows)->OrderRoot`, `update_ordered(map,db,root,expected_commitment,edits)->OrderRoot`.

- [x] Write tests with actual SQLite ProofNodeStore for strict-stream construction, seeded mixed transitions against independent ordered mapping and full rebuilt roots, parent old/neighbor/absence tampering, adjacent/disjoint gaps, extrema/all deletion/reinsertion, exact no-op root identity and zero writes, retained old roots, transaction requirement, late malformed input, late generator error and post-insert callback failure rollback. Include repeated record keys at distinct query positions without collapsing them.
- [x] Run `python -m pytest -q simulation/tests/test_stage_0_5_proof_order_edit.py`; Expected missing-module failures.
- [x] Implement caller-transaction-only temporary SQL staging, authenticated consistent parent witnesses, ghost boundaries/extrema and final predecessor/successor derivation. Build one locator-sorted final delta and use update_sorted. Bound Python residency by individual rows/frontier; no list/dict of all edits. Check expected count and return original OrderRoot object on a real no-op.
- [x] Run both ordered modules and all existing proof tests; Expected all pass. Commit `feat: verify ordered relation changes through affected boundaries`.

### Task 3: Fixed-work evidence, review and publication

**Files:** Create `.github/tests/run_proof_order_scaling.py`, `docs/performance/proof-order-results.md`; modify the proof validation workflow.

**Interfaces:** Driver `--output PATH`, immutable receipts; clean tracked source HEAD/runtime/driver SHA256. Independent 1k/10k/100k maps built from SQL-compatible order keys. Fixed middle replacement uses old/immediate-parent witnesses (SQL probes then map authentication), no payload table. Measure staging/build separately from transition. Point node reads <=512, new writes <=256 and traced peak <2MiB for this workload; report actual counts, Python heap, process RSS and SQL sources. Verify a fixed 16-row middle page, old/new exact values and independently rebuilt canonical root. Preserve partial evidence before later phases.

- [x] Commit driver, then execute it on clean source with a 15-minute process budget. Retain source/per-size/summary JSON and logs; Expected all fixed-work gates and canonical rebuild/page assertions pass. No expensive local mature run.
- [x] Add tests/driver to existing proof CI; keep full simulation-suite job. Validate Python AST, YAML and bash syntax. Run all affected proof tests plus incremental-store/failure regressions; Expected all pass.
- [x] One fresh whole-package review via executing-plans, fix Critical/Important RED->GREEN once; record minor deferrals/rulings and remaining integration gates. Publish exact-tree, lease-protected branch update, launch CI and provide its link without waiting for long tests.
- [x] Commit evidence/results/handoff. Expected successor CI explicitly pending until observed green, no main merge or World authority claim.

## Self-review

Task2 consumes exactly Task1 descriptor and commitment types; Task3 consumes both.
Review Focus maps to owning tests. The scope is ordered relation completeness
and transition certificates, not full physical/World topology integration.
Generic order keys do not silently choose an identity-path ordering. Repeated
query record keys at different ordinals remain distinct; exclusions must be
applied after verified raw pages. Interval/source checks are not bypassed.
