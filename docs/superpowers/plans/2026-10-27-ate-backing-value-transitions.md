# Backing value transitions implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Continue inline on the existing authorized branch; one fresh whole-package review at completion.

**Goal:** Extend native incremental saves to existing fixed-shape mutable backing values while preserving checked fallback for actual topology changes.
**Architecture:** Authenticate predecessor bytes under the accepted content root. Reuse World semantic facts only if auxiliary owner reference projections, shape, type counters, descriptors and physical locator roots remain unchanged; changed owner source witnesses must match the frozen bytes. The same central publisher, SQL capability and exact recovery remain authoritative.
**Tech Stack:** Python, SQLite, existing raw adapters and native participants.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md sections5.2–5.5.

## Global constraints
- No second publisher/registry; no silent default activation, main merge or endurance.
- Real canonical identity, exact query memberships, frozen source bytes, member policy and immutable backings stay checked.
- Keep512-row/4MiB fast-classification budgets and checked full fallback outside this domain. Do not label this unrestricted structural optimization or mature performance acceptance.
- Existing approved inline execution and dedicated-branch publication continue; long hosted CI is not polled.

## Review Focus
1. A same-length page may change integer/member class or references; shape alone is insufficient.
2. Map key/ordinal, sequence occurrence IDs, record class/seal and immutable backing state must remain exact.
3. Coherent forged owner headers or lease/type witnesses must not certify incorrect backing content.
4. Shared native aliases and unloaded owners must observe the one changed backing before/after reopen.
5. Lost acknowledgement and native callback restrictions must retain the original frozen receipt.

## Task1: Authenticated auxiliary value reuse
**Files:** Create simulation/ate_sim/persistence_proof_world_backing_value.py and simulation/tests/test_stage_0_5_proof_world_backing_value.py; modify persistence_proof_world_value.py at owner classification/projection only.
**Interfaces:** helper validates old/new frozen VersionChange and returns an eligible unchanged auxiliary projection or False. Existing value classifier still authenticates raw content, owner witness and stage structural roots.
- [x] RED: actual native list/map replacements forbid full audit and survive reopen with aliases; direct frozen backing record/page cases reject type/member/key/reference/immutable changes or use checked fallback.
- [x] Implement shape/member invariants using existing adapters and accepted owner-projection facts. No new publication path.
- [x] GREEN: new cases + existing value/session/manifest suites; checkpoint source.

## Task2: Evidence and single candidate
- [x] Extend existing native scaling driver with a fixed-shape shared-history replacement including first access/save, independent SQL VM work and final audited reopen at1k/10k/100k. Keep changed vs unrelated body reads distinct.
- [x] Run all proof tests and native participant/recovery checks on clean source. One fresh review, one Important/Critical RED→GREEN fix pass; defer minors.
- [x] Publish one bundled candidate and obtain CI link once. Continue the larger finishing objective after its correctness gate; fast admission and mature acceptance remain explicitly pending.
