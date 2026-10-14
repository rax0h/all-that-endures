# Complete Upgrade Memory Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. SOL owns implementation; use an independent review before the final large validation.

**Goal:** Upgrade the retained mature year1000 native lazy snapshot to format6 within the hosted runner's memory budget, with unchanged integrity and continuation semantics.

**Architecture:** Separate validation of the captured source from construction of its final catalog. Use checked, replayable disk staging for conversion inventories and prepared changes that otherwise coexist as decoded graphs, frozen bytes and decoded publication rows; feed them through the existing commit and private-copy publisher. Keep the ordinary `ParticipantDelta` contract and ordinary save behavior unchanged unless evidence proves a shared change is unavoidable.

**Tech Stack:** Python3.12, SQLite, existing WorldCodec/checked spools, pytest, GitHub Actions.

**Spec:** [STAGE_0_5_UPGRADE_MEMORY_REPAIR_HANDOFF.md](../../../simulation/STAGE_0_5_UPGRADE_MEMORY_REPAIR_HANDOFF.md). Read it and `simulation/STAGE_0_5_FINAL_RELEASE_RUN.md` before implementation.

## Global Constraints

- Runtime baseline: `2bc3c85389760ff12578857f7d2a849bc5cf9201`; latest harness: `ccba8cc6eba70965271d2570043829b3368e695a`. Fetch/read the live closeout head; do not reset other work.
- Preserve exact World values, RNG and continuation digests, aliases, NaN handling, container ordering, high-water marks, event IDs, format6, source immutability, atomic no-overwrite publication, and existing commit/recovery authority.
- Temporary disk staging is disposable working data, not another persisted catalog, backend, identity registry, or publisher.
- Ordinary save/open semantics and their existing budgets remain unchanged.
- No main/PR14 merge, default checkpoint replacement, rank/issue17 change, Stage1 work, or unrelated optimization.
- Long jobs run on GitHub; never keep chat waiting for their completion.
- Do not increase runner RAM/swap or weaken checks to satisfy this assignment. Keep timed stack watchdog dumping disabled.
- Target the retained fixture under the existing **8 GiB Python address-space guard** with headroom. Report peak RSS and virtual memory separately; RSS alone does not prove compliance with RLIMIT_AS. This target is a task gate, not a universal bound for arbitrary imported single records.
- New aggregate staging buffers: at most4096 entries **and**2MiB estimated resident payload before spill; honor the smaller limit. Measure Python/index overhead separately. A single oversized encoded row is an explicit input-sized cost, never silently truncated.

## Review Focus

1. Invalid source placements removed by later normalization must still fail before publication (Task1).
2. Large sharing groups/owners and many retired IDs can defeat a seemingly streaming builder through grouping or sorting (Task2).
3. Frozen values, NaN keys and replayed decoded objects must retain identity semantics; persistent `id(obj)` keys across replay are unsafe (Tasks2/4).
4. Duplicate keys, mutable input, spool corruption or disk failure during preparation must not partially publish or damage the source (Task3).
5. A resumed old checkpoint must retain its provenance while evidence names the repaired executable candidate (Task5).

## Source map and first inspection

| File | Responsibility / known risk |
|---|---|
| `simulation/ate_sim/persistence_catalog_copy.py` | First catalog build around328 is replaced around404 after normalization; captures owner rows, placements, segment BLOBs, all versions, ordinary rows and orders; final commit uses tuple concatenation and `delta.decode()` |
| `simulation/ate_sim/persistence_lazy_identity_catalog.py` | `initial_catalog_delta` builds owners/by_owner/by_group/seen/changes in memory, then freezes the entire result |
| `simulation/ate_sim/persistence_lazy_families.py` | `ParticipantDelta.freeze` duplicates rows as encoded tuples; fingerprint encodes the entire aggregate again; `decode` rematerializes it |
| `simulation/ate_sim/persistence_lazy_store.py` | `commit` accepts Iterable, but `_prepare_version_changes`, `_prepare_identity_changes` and `_prepare_ordinary_changes` call `tuple(changes)` and retain prepared rows and duplicate-detection sets |
| `simulation/ate_sim/persistence_event_copy_normalization.py` | `capture_bodies`, normalization maps, `(*versions,*ordinary)`, rewritten lists and source-object identity assumptions |
| `simulation/ate_sim/persistence_history_copy_promotion.py` | Promotion/reconciliation inventories; must retain exact allocation and order semantics |
| `simulation/ate_sim/persistence_lazy_spill.py` | Existing `CheckedSpool`: bounded staging, checksums, count/order seals, replay and cleanup; reusable building block, not a drop-in VersionChange serializer |
| `simulation/persistence_p5_long_validation.py` | Checkpoint verification, complete upgrade, continuation and restore receipts |

**Do not stop at replacing a list with a generator.** The commit preparers currently rematerialize generators. Do not merely move the same large freeze to the second catalog build. Do not change the fingerprint formula for ordinary participants as an opportunistic optimization.

### Task 1: Preserve source checks without building a disposable catalog

**Files:** modify `persistence_lazy_identity_catalog.py`, `persistence_catalog_copy.py`; create `simulation/tests/test_stage_0_5_upgrade_memory.py`.

**Interfaces:** introduce `validate_initial_catalog_inputs(codec, owner_versions, identity_changes, *, next_incarnation_id, generation, ordinary_changes=()) -> None`. Preserve `initial_catalog_delta(...) -> ParticipantDelta` for existing callers. Shared validation may use the staging context introduced in Task2; it must not construct/freeze a full unused output catalog.

- [ ] Add a real small complete-conversion test comparing owner/group/link authority and final World digest with the baseline, preserving aliases and source bytes. Capture baseline evidence before altering the builder; compare logical checked rows at the same generation, not whole SQLite file bytes or generated store UUIDs.
- [ ] Add corruption cases for duplicate owner/path, missing owner, unallocated incarnation, wrong physical reference placement, invalid auxiliary body and colliding path hash. Include a malformed placement that normalization would otherwise remove. Each must reject without a destination and with unchanged source hash.
- [ ] Observe the memory regression in a separate bounded subprocess, using many valid owners/placements and small payloads; record the old peak and failure. Keep this fixture small enough for normal development. Semantic tests that already pass are preservation tests, not claimed RED regressions.
- [ ] Extract validation from construction. On paths which necessarily rebuild after normalization/promotion, run validation only before normalization; on unchanged catalog-copy paths, retain the original effective behavior. Validate the final normalized catalog independently.
- [ ] Run the new tests and existing `test_stage_0_5_final_catalog_copy.py`, `test_stage_0_5_final_identity_catalog.py`, and `test_stage_0_5_final_legacy_event_copy.py`. Commit the tested unit with `[skip ci]`.

### Task 2: Stage and replay the final catalog without aggregate freeze/decode copies

**Files:** create `simulation/ate_sim/persistence_conversion_workspace.py`; modify `persistence_lazy_identity_catalog.py` and `persistence_catalog_copy.py`; extend `test_stage_0_5_upgrade_memory.py`.

**Interfaces:** the new private context manager `ConversionWorkspace(codec, *, directory, entry_limit=4096, byte_limit=2*1024*1024)` owns all temporary staging files. `stage_versions(changes) -> replayable Sequence[VersionChange]` validates/encodes once; replay checks immutable row/count/order commitments. `close()` is idempotent. Use the existing `CheckedSpool` internally where suitable; add explicit tuple adapters for VersionChange/RecordChange/IdentityOccurrenceChange instead of teaching WorldCodec about temporary implementation objects.

- [ ] Add tests for equivalent catalog rows with forced spilling (`entry_limit=4`, `byte_limit=1024`), repeated replay, exact ordering, zero rows, a giant sharing group, a large single owner and many retired incarnations. Compare owner roots/group digests/links/allocator state with the existing small reference implementation.
- [ ] Add tampered row, missing/extra/reordered row and cleanup-on-exception tests. Preserve original exception classes for invalid input; corruption of private staging fails closed.
- [ ] Implement indexed disk grouping/sorting for high-cardinality owner/placement/group inventories. Preserve WorldCodec byte ordering and the existing radix/group commitment algorithms. Avoid whole-owner Python dict/list construction where the new scale tests show it exceeds the staging budget; imported single-row costs remain explicitly reported.
- [ ] Produce the final catalog into checked replayable rows. The conversion path must not construct a full `ParticipantDelta`, encode the aggregate for its fingerprint, or decode the whole result merely to pass it to commit. Keep old ordinary-participant APIs and their fingerprints intact.
- [ ] Measure increasing valid inventory sizes (N,4N,16N) in fresh subprocesses, recording row counts, staging bytes, resident-buffer high water, peak RSS, wall time and disk bytes. Test bounded staging directly; do not assert unrealistic constant total process RSS.
- [ ] Run the Task1 gate plus `test_stage_0_5_final_identity_spill.py`; commit with `[skip ci]`.

### Task 3: Prevent the existing commit preparer from rematerializing the staged input

**Files:** modify `persistence_lazy_store.py` and the new workspace module; add `simulation/tests/test_stage_0_5_conversion_preparation.py`.

**Interfaces:** add an opt-in `preparation_budget: tuple[int, int] | None = None` keyword to `LazyRecordStore.commit`, expressed as `(entry_limit, byte_limit)`. Default `None` preserves existing caller behavior. Only the explicit private-copy path opts in. Its prepared sequences must support length/truth testing and repeatable checked iteration used by the existing transaction/recovery code. The store owns their lifetime through all exits.

- [ ] Write equivalence tests running the same valid version/ordinary/identity changes through normal and forced-spill preparation, checking resulting authority, memberships, generation and commit outcome. Exercise empty streams, deletes, reinsertion, stale pins and unchanged saves.
- [ ] Write failures for duplicate version keys, duplicate identity placements, duplicate ordinary keys, malformed memberships, mutation of input after preparation, staging corruption and disk write failure. Preserve pre-transaction rejection and all existing recovery outcomes.
- [ ] Factor row validation/encoding so both modes use the same checks. Use bounded replayable encoded records for spill mode, including disk-backed duplicate detection. Do not keep the original mutable change object rooted for every prepared row. Reconstruct only the row currently needed by unchanged commit logic.
- [ ] Remove full tuple/list concatenation at the converter call site. Ensure no aggregate prepared-row indexing, seen-set or fingerprint encoding defeats the opt-in budget. Keep one existing commit attempt/state machine; no auxiliary publisher or direct-write bypass.
- [ ] Close staging on success, conflict, abort, preflight failure, commit-acknowledgement recovery and exceptions. Preserve the final source and destination guarantees.
- [ ] Run the new gate plus affected lazy-store commit/recovery and catalog publication tests; name the selected files in the receipt. Commit with `[skip ci]`.

### Task 4: Verify the complete conversion path, not just the first failed allocation

**Files:** inspect/modify only measured offenders in `persistence_catalog_copy.py`, `persistence_event_copy_normalization.py`, `persistence_history_copy_promotion.py`, and the workspace; extend memory tests.

**Interfaces:** preserve `upgrade_lazy_snapshot(source, destination, *, rules_id)` and its result semantics. Preserve normalization's logical outputs and allocation order. The workspace is private scratch owned by the unpublished conversion.

- [ ] Run the synthetic full upgrade with per-phase resource measurements. Inventory simultaneous retained objects before/after source capture, normalization, final catalog, commit preparation, commit and scrub. `ru_maxrss` is lifetime peak; also record current RSS to locate retention.
- [ ] Stage only the remaining measured high-cardinality inventories that prevent the budget from holding: captured signatures, source/output versions, placement/order maps, immutable segment payloads, or scrub bookkeeping. Release superseded generations of temporary data promptly. Reuse the fixed captured source snapshot for checked replay; never reread an advancing live source.
- [ ] If replay is introduced into normalization, prove alias identity before proceeding. Existing `id(source)` keys for frozen bodies assume resident decoded objects; replace/restrict them using stable source/owner/path identity where necessary. Do not merge distinct equal frozen containers or split one shared container by accident. Add cross-row aliases, frozen nested values, NaN-key identity, Event-ID facade, advancement, packed actions and promotion cases.
- [ ] Exercise source-advances-during-copy, competing destination, source==destination, failures before/after commit and validation, partial scratch cleanup, and retry from the retained source. Keep all source bytes and the final destination protected.
- [ ] Run existing copy/normalization/format regressions including `test_stage_0_5_final_complete_format.py`, `test_stage_0_5_final_legacy_event_copy.py`, `test_stage_0_5_final_copy_promotion.py`, `test_stage_0_5_final_frozen_snapshot_authority.py`, `test_stage_0_5_final_legacy_nonreflexive_copy.py`, and `test_stage_0_5_final_nonreflexive_copy.py`.
- [ ] Review the complete diff independently before the large candidate run. Report any remaining input-sized costs honestly. Commit the verified candidate with `[skip ci]`.

### Task 5: Resume the retained fixture with accurate provenance and finish validation

**Files:** modify `persistence_p5_long_validation.py`, its harness tests, the validation-branch workflow and `STAGE_0_5_FINAL_RELEASE_RUN.md`.

**Interfaces:** add `checkpoint_product_sha: str | None = None` to `run` and CLI `--checkpoint-product-sha`. Only explicit resume accepts it. It permits matching the old receipt's product SHA while `product_sha` remains the executing candidate SHA; every other configuration check remains exact. New checkpoint/summary receipts record both identities and source workflow/database hash. New checkpoints bind their config to the new candidate for subsequent stages.

- [ ] Add tests for old-checkpoint/new-candidate resume, accurate output provenance, rejection without explicit source provenance, wrong seed/rules/maturity/milestones, wrong stage, corrupted database and unchanged old receipt. Extend the real small cold->lazy->complete->continuation harness lane.
- [ ] Verify the retained lazy artifact and compare source/candidate changes. Compatibility is explicit: no changed World schema, codec meaning, simulation rules or checkpoint contents. If the repair cannot read the old checkpoint unchanged, document the concrete incompatibility before scheduling an upstream rebuild.
- [ ] Pin the exact repaired candidate and separate workflow SHA. Run focused tests, one full `simulation/tests` suite and complete3+4+3 recovery on GitHub. Prior green results remain baseline evidence, not a claim the changed runtime already passed.
- [ ] Resume only the year1000 complete upgrade from run38508408370/artifact11870590333 under the 8GiB guard. Retain phase/RSS/disk evidence and the complete checkpoint. Do not launch the original bootstrap or repeat an unchanged failed stage. If the guard identifies another allocation, repair that measured path and rerun only the affected stage after focused verification.
- [ ] After the repaired candidate's gates pass, resume year1001/1002, save/audit/reopen, and compare with the retained independent controls. Reuse the original canonical year1000 digest as source-world evidence only; do not relabel its benchmark as a new-candidate measurement. If simulation behavior changed, stop: that is outside this assignment.
- [ ] Download the resulting restore onto a fresh runner, verify original hash, open a disposable copy, check year/generation/format/digest/counters and unchanged original. Record both source-checkpoint and repair identities.
- [ ] Publish a final receipt with commands, candidate/tree/workflow SHAs, artifact IDs/hashes/expiry, actual full-suite counts, memory high water, conversion timing, continuation equality and restore proof. No merge or promotion.

## Verification commands and acceptance

Use `PYTHONPATH=.:simulation` for local pytest and scripts. Targeted example:

```bash
PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_stage_0_5_upgrade_memory.py simulation/tests/test_stage_0_5_conversion_preparation.py simulation/tests/test_stage_0_5_final_catalog_copy.py simulation/tests/test_stage_0_5_final_long_harness.py
```

The final GitHub full-suite command is `python -m pytest -q simulation/tests` with stdout/stderr and JUnit retained. Reuse the explicit staged workflow, not a new uncheckpointed monolith. Do not run hours-long tests locally or block a chat turn waiting for them.

Done means the repaired **entire upgrade** passes under the guard, all integrity/corruption/recovery gates hold, year1001/1002 match independently, and fresh-runner downloaded restore passes. A diagnostic failure that yields useful evidence is progress, not acceptance. A single giant imported row remains an explicitly measured limitation; never claim this finite fixture proves universal fixed memory.
