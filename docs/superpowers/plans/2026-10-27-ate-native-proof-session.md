# Audited native proof session integration implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Continue inline on the authorized dedicated branch; one fresh whole-package review.

**Goal:** Run actual canonical native World sessions with accepted format7 manifests and publish/recover their frozen participant plans through the existing manifest writer.
**Architecture:** Explicit `open_audited_proof_world_session(path, rules_id=..., expected_commitment=...)` authenticates and fully audits one matching snapshot before native restoration. Reuse every existing registry, alias stitching, participant, save journal and acknowledgement. Bind native frozen changes to the existing manifest producer; preserve parent authority across lost acknowledgement. Conservative epoch guards invalidate direct SQL/external changes before reads or preparation.
**Tech Stack:** Python, existing SQLite writer/native runtime/proof components.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md, sections5.2–5.5; docs/performance/world-manifest-results.md.

## Global constraints
- Preserve canonical identity, raw bytes, iteration/RNG order and exact continuation.
- No second publisher or registry, in-place conversion, default native format7 activation, main merge or endurance run.
- This explicit audited integration retains full audits at admission and changed publication/epoch resynchronization. It establishes correctness, not fast open/save. Affected-owner incremental transitions remain required for target latency.
- Keep the producer's unsupported partial retirement/mixed inline/backed/cyclic/key-reference source states fail closed.
- Existing inline/publication authorization persists; no new approval gate or repeated design questions.

## Review focus
1. Caller-supplied wrong/stale/cross-store commitment must fail before native objects escape.
2. Frozen session commit descriptor must match the manifest's exact token/generation; it may not be silently overwritten.
3. Before-head/before-commit/after-commit and partial in-memory acknowledgement failures must resolve exactly once against the original parent, preserving dirty journals.
4. Accepted epoch must not refresh across raw same-connection SQL or external writes without authentication; uncertainty must block ordinary mutation.
5. Native shared aliases, structural history edits, events and fresh recovery must retain canonical identity and manifest authority.

## Task1: Explicit native admission and frozen save/recovery bridge
**Files:** Create simulation/ate_sim/persistence_proof_world_session.py and simulation/tests/test_stage_0_5_proof_world_session.py. Modify persistence_lazy.py, persistence_complete_format.py and persistence_lazy_store.py only at admission/save/recovery/snapshot seams.
**Interfaces:** consume existing `commit_world_manifest`, `resolve_world_manifest`, `_load`, `_audit_world` and `FrozenHybridPublication.commit_arguments`. Produce `open_audited_proof_world_session` returning the existing LazyWorldSession, whose `proof_manifest` returns the accepted pair. An operation-scoped authority borrows the same store/publisher; no independent native objects.
- [ ] RED: real checked-copy fixture, canonical shared alias, scalar/structural save + reopen, noop, wrong authority, all three fault seams, partial acknowledgement, frozen descriptor mismatch and same/external SQL invalidation.
- [ ] Implement matching-snapshot full audit before native activation and exact frozen-plan translation; retain original parent across uncertain/partial publication; validate successor before acknowledgement.
- [ ] GREEN: focused session tests plus existing35 manifest cases; relevant native/copy/recovery cases; commit local checkpoint.

## Task2: Review, evidence and publication
- [ ] Run all proof tests and related native participant/catalog/recovery tests. Full simulation suite remains hosted only.
- [ ] One fresh Astra/high review; one Important/Critical RED→GREEN fix pass, no second review; ledger declined-area rulings and costs.
- [ ] Retain source hashes and test evidence, document full-audit costs and next affected-owner integration boundary. Publish one bundled candidate; obtain CI link once, stop without polling.
