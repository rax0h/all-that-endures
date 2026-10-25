# Frozen and fixed-body extents implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline.

**Goal:** Extend inactive selected-target extent validation to frozen-list, frozen-map, record and nan-key, preserving exact storage semantics and shared source budgets.
**Architecture:** Reuse the accepted version2 five-family child inventory unchanged. Share list/scalar physical verification with mutable histories. Match existing frozen certification semantics: authenticate each distinct referenced frozen/NaN target using accepted roots, then compare the existing one-hop certification bits against complete values; preserve false certifications and never infer transitive closure. Fixed records expose ordered declared field/value pairs; NaN bodies expose no members and retain their exact bytes in the raw target. Reuse the existing owned snapshot and publisher.
**Tech Stack:** Python, existing SQLite proof maps and pytest.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md; docs/performance/proof-map-foundation/NEXT_INTEGRATION.md.

## Global constraints
Existing dedicated branch and inline execution remain authorized. No World activation, merge, endurance run, new family tags, publisher, native construction or broad cache. No long CI polling. The five-family child directory has a closed version2 contract; sequence internal families and Event-ID exceptions need a separate versioned path. This package does not establish recursive graph closure, full field-domain policy, unindexed-owner discovery or a semantic transition producer. The frozen check matches the runtime's existing one-hop certification contract; child certification truth still requires recursive closure before World admission. Fixed record field schema checks do not establish every field's domain semantics.

## Review focus
- Frozen map certification applies to payload values, while member-type witnesses count keys; these must not be swapped.
- Empty snapshots with a false bit must reject, and certification must be checked even after a mutable value makes the running result false.
- Distinct referenced frozen/NaN dependencies share source bytes and a bounded target limit; repeated references reuse one operation-local result.
- Fixed bodies must reject unrelated physical child families, preserve NaN payload bits, declared field order and event seal state without native restoration.
- Accepted retained roots must keep old body/certification data coherent through atomic successor and exact recovery.

## Task 1
**Files:** persistence_proof_child_extents.py; new persistence_proof_frozen_extents.py; new proof_frozen_extent_fixtures.py and test_stage_0_5_proof_frozen_extents.py; new run_proof_frozen_extents_scaling.py; workflow and evidence docs.
**Interfaces:** read_target_members retains existing parameters, adding max_certification_targets=128 (exact integer 1..4096); RawTargetMembers adds certification_targets=(), containing authenticated raw dependency targets. List/frozen-list members are ordered values, map/frozen-map members ordered pairs, records ordered declared (field,value) pairs, NaN empty. Counts are history keys for maps, field values for records, zero for NaN. Shared max_bytes and per-source limits remain authoritative.

- [x] Write real-root frozen/fixed extent tests with literal expected values, exact count/page/ordinal/type witness faults, false certification, referenced target kind/existence, budgets, retained and atomic recovery tests.
- [x] Run RED tests: unsupported extent kind must fail positive frozen/fixed readers before implementation.
- [x] Implement shared physical verification and bounded fixed-body/frozen certification readers. Check all certification dependencies, including after false values; verify accepted targets, cache by exact reference encoding within operation only.
- [x] Run focused tests and all proof tests. Run affected existing frozen/record/NaN runtime tests; full simulation runs in hosted CI under the user's no-polling workflow.
- [x] Run clean-source frozen extent 1k/10k/100k unrelated-parent matrix, interval-one guarded replay, zero unrelated child payloads. Source hashes accompany receipts.
- [x] Commit runtime checkpoint and obtain one fresh independent review over this package; fix Important/Critical findings by RED→GREEN, without a second reviewer.
- [ ] Retain evidence, publish candidate, start long CI and return its link without polling.
