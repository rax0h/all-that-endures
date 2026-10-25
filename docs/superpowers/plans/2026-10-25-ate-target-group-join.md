# Accepted target and complete incoming group join

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline.

**Goal:** Resolve a typed backing and its entire authenticated incoming group from the same accepted content/scope/inventory authorities, without caller-supplied per-owner authority bundles.

**Architecture:** Add an inactive raw composition, `persistence_proof_target_group.py`. Own one checked snapshot; reuse the existing target verifier and complete identity-group verifier. Resolve the group/link/owner certificates through the accepted scope directory. Enumerate only the selected group to discover exact owner scopes. Bound members before enumeration. Charge discovery and target bytes first, then give the group verifier only the remaining source budget. Return `RawTargetGroup(target, group)`. No new publisher, registry or native admission.

**Tech Stack:** Python, SQLite, pytest, existing immutable proof maps.

**Spec:** `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`, `docs/performance/proof-map-foundation/NEXT_INTEGRATION.md`.

## Global Constraints

Preserve history, exact values, identity and the existing single transaction. Work on the existing dedicated branch under prior inline authorization. No main merge, endurance run, World activation, GC, alternate registry or format advertisement. CI longer than one minute is handed back with a link; never poll it. Existing full-suite CI establishes the baseline; new full-suite acceptance remains the next CI gate.

This proves the complete incoming physical group metadata and backing descriptor for one live typed target. It does not prove every incoming owner's payload semantics, parent/child extents, recursive graph closure, complete World topology or semantic kind transitions. Keep those boundaries explicit.

## Review Focus

- Later peer corruption must reject even when the point target's first placement still verifies.
- Ordinary and auxiliary owners must retain distinct exact paths and canonical links.
- Member/byte bounds must apply to the whole composition, including discovery.
- Current/retained certificates must not mix even when roots are unchanged.
- Source hooks, arbitrary transactions, SQL shadows/views and wrong external authority must fail closed.

### Task 1: Bounded raw target/group composition

**Files:** Create `simulation/ate_sim/persistence_proof_target_group.py`, `simulation/tests/test_stage_0_5_proof_target_group.py`; reuse existing owner-target fixture and group reader unchanged.

**Interface:** `read_target_group(store,pin,reference,content_authority,scope_authority,inventory_authority,*,max_members=4096,max_bytes=4194304,max_source_bytes=1048576,max_metadata_bytes=1048576)` returns frozen `RawTargetGroup(target,group)`.

- [x] Write tests for all paths/canonical links, all nine target kinds, later peer/owner/link corruption, limits, retained roots, wrong kind and source/authority guards. Expected RED: new module absent.
- [x] Implement exact certificate derivation and bounded group discovery; pass only remaining source bytes to existing complete group verifier. Expected GREEN: focused target/group tests pass.
- [x] Add a clean 1k/10k/100k diagnostic and workflow steps, with source hashes, exact group results, VM/memory/SQL bounds and zero archive-body reads. Construction is outside reader timing.
- [x] Run affected proof suite; retain results; request one fresh whole-package review and fix blocking findings with RED/GREEN tests.
- [ ] Publish candidate and launch full-suite/scaling CI. Report remaining gates and stop without polling.

Review fix: add test_stage_0_5_proof_target_group_scaling.py to the dedicated workflow test step. Guard test RED→GREEN; replace sampled instruction estimate with an interval-one guarded replay outside latency timing. Final full proof suite and clean archive-size diagnostic are rerun after this fix.
