# Catalog sequence verification repair

> **For agentic workers:** Use superpowers:executing-plans inline, with one final independent review. Steps use checkbox syntax.

**Goal:** Remove descriptor-count multiplied by shared-namespace-row-count work from complete-copy catalog verification.

**Architecture:** Preserve each sequence's checked structural/locator traversal. During explicit catalog verification, accumulate expected physical keys in the existing disposable checksummed disk inventories, then stream each of the six visible sequence namespaces once and check exact equality for active incarnations. Standalone scrub retains its existing behavior. No persisted format, ordinary operation, publication, or resource-cap change.

**Tech stack:** Python, existing SQLite MVCC store, ConversionWorkspace/DiskSet, pytest.

**Spec:** Daniel's performance lead for run38645679329/candidateb15f4e1 and the boundaries in `simulation/STAGE_0_5_UPGRADE_MEMORY_REPAIR_HANDOFF.md`.

## Global constraints

- Diagnose with descriptor counts, rows per namespace and per-sequence durations before behavior changes.
- Preserve source immutability, aliases, exact continuation, incarnation/pin isolation and all corruption detection.
- Preserve checked retirement's exemption for partially reclaimed trees.
- Use existing 8GiB address-space guard; no unchecked inventory or aggregate in-memory shared namespace cache.
- Run long acceptance jobs on GitHub; do not wait for them in chat.
- No main/PR14 merge, checkpoint replacement, rank/issue17 change, or Stage1 work.

## Review focus

- Extra, missing and overlapping sequence projections must still reject.
- Scratch row deletion/key/checksum changes must fail before publication.
- Old generation pins must see their own physical inventory after another commit.
- Partly retired sequences must retain existing treatment.
- Standalone dirty/new sequence scrub and cache/pin contracts must remain unchanged.

### Task1: Diagnose, repair and validate the shared sequence inventory

**Files:** `simulation/ate_sim/persistence_catalog_copy.py`, `simulation/ate_sim/persistence_lazy_sequence.py`, `simulation/tests/test_stage_0_5_catalog_sequence_scrub.py`, `simulation/tests/catalog_sequence_scrub_probe.py`.

**Interfaces:** `_verify_sequences(store,pin,workspace)` performs catalog-only verification; `LazyOrderedSequence.scrub(*,_inventory=None)` accepts an internal expected-key collector for clean persisted sequences only. `_inventory(namespace,keys)` receives one sequence's already validated expected key set.

- [x] Measure the unchanged baseline with the probe at8/32/128 descriptors; preserve full per-sequence data.
- [x] Add integration regression asserting at most one full key scan per namespace per catalog verification; run and confirm failure due to repeated scans.
- [x] Add coverage for shared-versus-standalone semantics, generation isolation, extra/missing/overlap projections, deferred-inventory corruption, retirement and publication cleanup.
- [x] Implement expected-key collection and one streamed visible inventory using existing authenticated DiskSet objects. Check duplicates explicitly before deduplication; validate all scratch seals after use.
- [x] Run the focused sequence/catalog/complete-format/retirement/conversion gates. Repeat the identical scale probe with shared verification and report rows as well as time.
- [x] Obtain independent scoped code review; address material findings with regression tests.
- [ ] Commit source/tests/evidence, push the existing implementation branch, and launch fresh full-suite/recovery gates and retained-checkpoint acceptance with detailed verification progress. Preserve all candidate/source/workflow provenance.

## Execution record

Workspace: existing clean implementation checkout on `sol/stage-0-5-complete-closeout`, advanced by fast-forward to liveb15f4e1. No worktree created or main branch changed.

Run38645679329: fresh full-suite/recovery successful; large job116163910403 exited124 under350m command timeout. Upgrade commit finished11575.96s after start, `_verify_catalog` entered at03:43:10Z, job stopped05:33:19Z. The original log did not record per-sequence counts/timings; these are measured on controlled fixtures before repair and will be recorded on the next real conversion.
