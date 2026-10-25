# Save-head inventory authority implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce, read and atomically update exact raw save-head namespace/count and identity-allocator authority without archive rescans.
**Architecture:** An inactive certificate binds ManifestHead raw fields plus an ordered namespace/count root. Audited bootstrap checks all physical data once. Successors derive count deltas from actual prepared changed keys/segments, compare actual successor head counts, and publish inside the existing directory/content transaction and exact receipt. Raw retained reads use accepted certificates; no World admission.
**Tech Stack:** Existing Python/SQLite/closed metadata codec and OrderedSeekMap.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md and docs/performance/proof-map-foundation/NEXT_INTEGRATION.md.

## Global constraints
Preserve exact state/history/identity and deterministic continuation. One authoritative existing transaction/receipt. No World format activation, merge, endurance or node collection. User authorized routine choices and inline continuation; escalate only fundamental invariant changes. Raw head metadata uses explicit 1MiB aggregate budget and closed parser node/depth limits; namespace keys at most4096bytes and pages at most128 entries. Metadata traversal cost depends on bounded head metadata, not archive size; no namespace-fanout acceptance claim.

## Review focus
- Empty namespace inventory and first creation must work.
- Coherently altered head counts/allocator must reject against accepted parent authority.
- Exact source schemas precede inherited metadata reads, including TEMP/view callback replacement.
- Lazy vs ordinary records and segment count deltas must compose without rereading unrelated bodies.
- Retained head bytes, failed transactions and lost acknowledgements must preserve exact receipt and old authority.

### Task1: Inventory producer/read/successor
**Files:** new simulation/ate_sim/persistence_proof_inventory.py; new simulation/tests/test_stage_0_5_proof_inventory.py; extend directory/collection publication hooks and lowlevel guard call only; diagnostic/workflow/docs.
**Consumes:** existing ManifestHead, OrderedSeekMap, audited source guard, commit_directory/resolve_directory and actual prepared changes.
**Produces:** bootstrap_inventory(store,pin)->certificate/commitment; read_inventory_namespace/read_inventory_namespaces raw count entries; commit_inventory/resolve_inventory using the existing directory/content authority chain.
- [x] Write tests: complete sorted inventory includes empty declaration; raw values match head; count deltas for lazy insert/delete/reinsert, ordinary insert/delete and segment append; metadata-only/noop/empty; counter tamper and schema shadows; retained reads and fault recovery/reopen.
- [x] Run tests RED for missing module.
- [x] Implement canonical exact-head certificate and schema-gated audited constructor/readers. Incremental publisher authenticates parent head/allocator, derives expected counts from prepared point operations, checks successor counts and updates changed namespace nodes only. Do not infer target existence.
- [x] Run focused plus affected proof suite; expected no failures. Fresh whole-change review, one fix pass with RED regressions.
- [ ] Measure clean source at1k/10k/100k archive rows, actual unified inventory save with zero unrelated version-body reads, full construction outside timer. Final full suite/scaling through candidate CI.
- [ ] Save source/evidence/ledger and publish isolated candidate; no main merge.

Execution: clean pre-review archive matrix complete; final-source scaling/full suite delegated to candidate CI. Local affected789 green. Implementation and single review/fix pass complete.
