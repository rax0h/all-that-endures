# Physical owner to target join

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Authenticate a registered physical owner's entire direct reference projection and resolve every distinct referenced backing under the same pinned content/scope/inventory roots.
**Architecture:** Reuse the existing owner projection and target verifier. Derive owner/version certificates from actual accepted roots; resolve exact owner paths to typed references, verify path/ID agreement and deduplicate repeated target reads within the operation. One snapshot, aggregate source bytes and at most128 direct references. No recursive traversal or new publisher.
**Spec:** docs/performance/proof-map-foundation/NEXT_INTEGRATION.md and docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md.

## Constraints/review focus
Preserve exact values/history/identity. Existing isolated branch/inline authorization applies; no routine approvals, World activation, merge, endurance or GC. Source guards precede metadata. Wrong target kind must reject even if incarnation projection matches. Deleted owners need proved empty projection. All direct paths are verified before returning any result. Aggregate budget covers owner and all distinct target sources; repeated references share validation without erasing placements. No complete aliases, parent member extent, semantic transition or World graph admission claim.

### Task1
- [x] Write RED tests for valid repeated targets, wrong kind with same ID, missing target/placement, absent/no-reference owner, bounds and retained snapshots.
- [x] Extract the existing target snapshot resolver without weakening its public owned-snapshot gate; share its source budget for the join.
- [x] Implement read_owner_targets(store,pin,namespace,typed_key,content_authority,scope_authority,inventory_authority,*,max_bytes=4194304,max_source_bytes=1048576,max_metadata_bytes=1048576,max_references=128). Return raw owner source, all encoded path/incarnation pairs, and distinct raw targets.
- [ ] Focused/affected verification, one fresh review/fix pass, archive-size diagnostic and final candidate CI; retain evidence.

Execution:839 proof tests and full clean archive matrix passed; fresh review no blocking issues, deferred test-coverage minor in ledger. Candidate CI owns full simulation/hosted scaling acceptance.
