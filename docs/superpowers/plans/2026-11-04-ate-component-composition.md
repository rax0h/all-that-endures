# Bounded Source/Catalog Composition Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline, then one fresh whole-package review. User working agreement requires closure of Minor findings too.

**Goal:** Certify a composed source/catalog native save without increasing any component's 512-row limit or omitting original publication rows.

**Architecture:** A finite routing helper separates shape accounting from proof authority. Existing frontier, value and canonical catalog validators certify their own inputs; the original publisher retains all writes and final root checks.

**Tech Stack:** Existing Python/SQLite proof runtime, pytest and native saved-world fixtures.

**Spec:** `docs/superpowers/specs/2026-11-04-ate-component-composition-design.md`.

## Global Constraints

- At most 512 noncatalog source rows including ordinary rows; at most 512 catalog rows.
- Keep insertion aggregate 4 MiB encoded request-plus-predecessor limit.
- Existing lease budgets remain 4,096 rows / 4 MiB old-plus-new bytes.
- Frontier input, including owner-header witnesses, stays at most 512 rows.
- All original rows, atomic frozen attempt, exact catalog and successor roots remain mandatory.
- No main merge, default activation, endurance or mature performance acceptance claim.

## Review Focus

- Source/catalog/frontier exhaustion: no partial authority or oversized streamed materialization.
- Missing, extra or corrupt catalog witnesses: rejection, rollback and retry.
- Lease plus fresh-source composition: complete publication rows retained.
- Lost acknowledgement and before-head faults: original frozen attempt resolves exactly once.
- Unsupported fresh sequences/map/ownership shapes: checked fallback remains effective.

## Task 1: Bounded native component routing

**Files:** Create `simulation/ate_sim/persistence_proof_world_components.py` and `simulation/tests/test_stage_0_6_proof_world_components.py`; modify manifest guard, insertion classifier, value/backing eligibility and tail metadata routing; create `persistence_proof_world_scalar_growth.py` for bounded accepted nonempty scalar map/set append extents.

**Interfaces:** Helper consumes prepared versions/ordinary lengths and accepted lease markers. Produces bounded semantic/frontier inputs and an insertion shape-budget decision. Scalar preparation certifies exact rows in `request.scalar_rows` and composes existing tail facts, child root, source rows/counts only after complete validation. It creates no certificate or commit participant.

- [x] Write a real native composed save with more than 512 semantic rows, each source/catalog component below 512, and assert no World audit plus exact restored values/sharing. Run it RED against green parent.
- [x] Add exhaustion, streamed input, catalog tamper and fault/recovery cases; run RED where new behavior is expected, keep existing rejection/fallback assertions meaningful.
- [x] Implement bounded classifier and wire existing validators. Do not decode bodies in classifier; do not change original publisher input.
- [x] Run component tests and affected sequence/insertion/mixed/new-backing/lease tests. Require every case green.

## Task 2: Exact complete-year integration and package closure

**Files:** Existing canonical `.github/tests/run_proof_real_year_probe.py`, component tests, launch runtime pin, current performance closure/register/ledger.

**Interfaces:** Real-year driver consumes clean exact source; produces raw timings and separate diagnostic fallback attribution, eager/fresh-process equality and unchanged accepted input.

- [x] Reproduce complete-year baseline and identify remaining unsupported branches with explicitly instrumented scratch-only probes; never present relaxed diagnostic caps as product timings.
- [x] Run canonical complete-year driver on clean candidate. Add exact uncovered shape regressions if this implementation needs correction; preserve unsupported fallback rather than widen authority.
- [x] Refresh runtime pin; run clean-source launcher checks and YAML/bash/fingerprints.
- [x] One independent whole-package review; close every finding with RED/GREEN evidence in one register.
- [ ] Commit evidence and publish once. Record exact source/tree mapping and start one bundled hosted validation. Hosted completion and mature targets remain explicit open gates until verified.

Ruling: exact-year diagnostics exposed scalar set growth, implemented in the same group. They then reached unsupported ordinary event/data/action and motive replacement allocations; preserve fallback and record the exact next gate rather than widen the allocator authority. One review Minor is closed by retained lineage-policy/mixed-frontier/fresh-process cases. Original broad run included two overstrict test sentinel failures; corrected final module passes and those failures are retained as author A1 evidence.
