# Private Checked-Catalog Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Native execution is already authorized by the complete Stage0.5 directive.

**Goal:** Move the existing checked-catalog bootstrap out of test-only setup into a source-preserving private copy step for the eventual complete converter.

**Architecture:** Reuse LazyRecordStore.copy_current_head to capture one checked, explicitly bounded format5 source generation into a private directory. Create a separate empty mutable destination with the unchanged immutable segments and captured-generation baseline; import its current records, placements, catalog and empty dependency rosters through the existing commit. Preserve source ordinals/high-water counters during private construction, scrub the destination, then use the accepted no-overwrite publication helper. Do not move live namespace authority, emit format6 or describe this intermediate copy as a complete World upgrade.

**Tech Stack:** Existing Python/SQLite checked stores, catalog and participant primitives, pytest.

**Spec:** simulation/STAGE_0_5_FINAL_ARCHITECTURE.md §Identity catalog/source-copy upgrade and simulation/STAGE_0_5_SOL_61_EXECUTION.md.

## Global Constraints

- Preserve source state, held source aliases, immutable event segments and native equality semantics.
- No second registry, owner DAG, serializer or publisher.
- No incomplete capability6 marker, PR14 changes, gameplay or new endurance run.
- GitHub issue17 is deferred gameplay; do not change advancement/rank or old golden fixtures.
- Focused/affected checks per component; one final applicable full suite only on the complete stable Stage0.5 source.

## Review Focus

- Competing destination created after preflight must not be overwritten.
- Fault after the private commit must not expose a partial destination.
- Corrupt source or inconsistent owner/backing metadata must fail before publication.
- Source advances after capture: the copied generation must remain coherent, not mix heads.
- Physical sequence interior nodes are not child-owning leaf authorities; preserve their checked tree without inventing owner headers.

### Task 1: Private catalog bootstrap copy

**Files:**
- Create: simulation/ate_sim/persistence_catalog_copy.py
- Test: simulation/tests/test_stage_0_5_final_catalog_copy.py

**Interfaces:**
- Consumes: LazyRecordStore.copy_current_head, initial_catalog_delta, dependency_value, verify_type_witnesses, checked catalog reads, accepted no-overwrite publication.
- Produces: private integration helper `_copy_with_checked_catalog(source, destination, *, rules_id) -> dict`, explicitly `complete_format=False`; future complete converter must still normalize remaining graphs and validate all feature markers.

- [x] Write regressions for copied sharing/physical owners/dependencies, unchanged source bytes, new store UUID and explicit incomplete format boundary.
- [x] Run RED for the missing helper (7 expected assertion failures).
- [x] Implement source-current capture and a separate mutable-empty destination; install current authority and catalog through one existing commit, with no legacy ordinary links ever installed there.
- [x] Scrub all groups/owners and backing type witnesses; create empty rosters and verify every compact reference's allocated target/kind, including references inside eager headers.
- [x] Add faults at private-copy, actual commit and publication boundaries; competing path, corrupt/missing-reference source, duplicate catalog, preserved ordering/high water and post-capture source-head advance cases.
- [x] Run focused (20 cases) and final selected affected (49 cases) catalog/copy checks; broader 118-case gate precedes the final ordinary-query-membership preservation change.
- [ ] Preserve exact source evidence and checkpoint publication.

The in-place authority-move guard correctly rejected the initial clone/commit
approach. Keep that guard. The destination is instead mutable-empty at the
captured generation, with no World reader until validation/publication. Source
advancement is tested after capture has released its read transaction: inline
writer attempts during a rollback-journal read transaction block by design.

Copy construction also preserves ordinary query membership values/ordinals;
their generation advances with the imported current record. An explicit damaged
source probe removed a history descriptor and matching type witness while leaving
a root reference, exposing a semantic gap beyond low-level checksums. Full-copy
reference target/kind validation rejects this before publication.

This task does not close recursive imported root collections, complete format activation, persisted promotion, exotic keys or final release gates.
