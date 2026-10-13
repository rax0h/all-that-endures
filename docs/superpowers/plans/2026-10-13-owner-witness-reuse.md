# Checked owner-witness reuse implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one fresh-context final review.

**Goal:** Remove repeated checked owner-tree decoding from unchanged SQLite authority, without changing identity semantics.

**Architecture:** Reuse only immutable `CheckedOwnerIdentity` results after a complete validation. A bounded catalog-local LRU is qualified by connection identity, both catalog/store codec identities, captured generation, total_changes, data_version and schema_version. Pin/head/retention validation still runs before every hit. Only standalone catalog-owned read transactions may reuse/admit entries; borrowed/nested transactions clear and bypass the cache, preventing rollback/savepoint epoch ambiguity. No new durable authority.

**Tech stack:** Python3.12, SQLite, pytest, existing GitHub validation.

**Spec:** simulation/STAGE_0_5_SPEED_REPAIR_HANDOFF.md; simulation/STAGE_0_5_FINAL_CANDIDATE_HANDOFF.md.

## Global constraints

- Preserve native arithmetic, RNG, exact values, identity and current publication/recovery authority.
- No main/PR14 promotion, rank issue17 changes, checkpoint defaults, millennium or endurance.
- Keep long tests on GitHub. Preserve the previously green source and original restore.
- Additional clean owner certificates: at most256 entries,4096 occurrences and256KiB estimated payload/sidecar weight by default, each capped by the catalog's supplied limits. Container overhead is separately disclosed. Spilled, oversized and non-immutable results are never retained.
- Bypass reuse for borrowed transactions, including savepoint/write/rollback cases. Never trust a cache to validate a foreign/released pin or closed store.

## Review focus

1. Same-connection and external corruption after warming must fail, including absent metadata or forward occurrences.
2. Borrowed transactions and rollback must never publish a certificate for transient authority into ordinary reads.
3. Generation movement, connection/codec replacement, pin release and store close must not authorize stale results.
4. Cache retention must stay bounded for large owners and many small owners; spilled resources remain caller-owned.
5. Shared children and dirty placement overlays must remain distinct from cached persisted metadata, through faults/save/reopen.

### Task 1: Bounded owner-certificate reuse

**Files:** modify simulation/ate_sim/persistence_lazy_identity_catalog.py; create simulation/tests/test_stage_0_5_owner_witness_cache.py.

**Interfaces:** consumes LazyRecordStore.read_snapshot/read_version and CheckedOwnerIdentity; retains read_owner_identity(pin, owner) signature; exposes cache diagnostics for measured residency.

- [ ] Add real-store repeated-read regression: identical occurrences, zero repeated payload decoding, nonzero pin validation. Baseline must fail its cost assertion.
- [ ] Add warmed corruption, external commit, released/foreign pin, successor generation, rollback/borrowed transaction and bounded-retention cases.
- [ ] Implement bounded immutable-result reuse with the validity and resource rules above.
- [ ] Run new regressions and affected catalog/coordinator/World tests. Expected: no failures, unchanged semantic results.
- [ ] Commit source, tests and measured evidence with skip-ci.

### Task 2: Review and integrated validation

**Interfaces:** consumes Task1 source and immutable candidate commit; produces exact-source CI evidence and release-decision record.

- [ ] Run a fresh-context read-only review of all changes and remaining architecture claims. Repair concrete important findings with regressions.
- [ ] Start affected gates, complete applicable suite, and the same checksum-verified year7-to8 profile on GitHub. Also record an unprofiled short timing; do not compare profiled seconds as native speed.
- [ ] Preserve logs, metrics and exact independent authority; return the durable run link without waiting in chat on the full suite.
- [ ] Record final architecture/performance status honestly. Owner-only pressure/endurance/promotion decisions remain explicit, not automatic.

## Execution ledger

Ruling: continue inline under the existing complete-execution directive and this explicit request; no routine design approval pause. This is a derived-cache optimization of the accepted architecture, not a new feature or authority. If validity cannot be proven, omit the optimization.

Ruling: dedicated freshly cloned checkout at b91b0c8 is isolated from other work; no additional linked worktree is created. Previous baseline suite2413+2 and affected78 are verified GitHub evidence; do not rerun the hour-long baseline locally.

Pre-flight: Task2 consumes Task1's immutable source boundary. No source publication is claimed green until exact-candidate CI completes.
