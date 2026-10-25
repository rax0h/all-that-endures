# Typed target incoming payload checks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline.

**Goal:** Authenticate every owner body in one selected target's complete incoming group and prove its exact typed-reference paths, kinds and IDs, including unrecorded extra references to that target within those owner bodies.

**Architecture:** Reuse the accepted target/group join in one owned snapshot. Extend its private checked-snapshot seam and group source budget sharing so owner payload reads consume the same aggregate budget. Decode World record schemas into private inert structures; never restore native mutable records or consult caller registries. Auxiliary owners use the existing physical adapters. Ordinary bodies require a separate externally accepted RecordCertificate and use the retained-record reader. Return raw body bytes and checked target paths only.

**Tech Stack:** Existing Python/SQLite proof modules and pytest.
**Spec:** `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`, `docs/performance/proof-map-foundation/NEXT_INTEGRATION.md`.

## Global Constraints

Preserve exact history/identity; reuse the existing writer and canonical registry. No new publisher, World activation, merge, endurance or default open/save behavior. User authorizes inline continuation without routine design approvals. Use existing dedicated branch. Longer CI is handed back with a link and never polled.

This is selected-target incoming storage-reference semantics, not complete World semantics. Inline native mutable counterparts without a closed typed pointer fail closed. Dictionary-key/set member reference routes outside existing World field/key/index policy fail closed. Auxiliary adapter immutable-member paths remain supported. World namespace field-domain policies, child extents, recursion, complete target inventory, unselected owners and native graph admission remain separate gates.

## Review Focus

- A valid catalog over a payload with the wrong path, ID or kind must reject.
- Extra unrecorded references to the selected target inside a fetched owner must reject.
- Within incoming validation one owner body is fetched once even with repeated paths; every path is preserved. Target validation may have fetched that body earlier; reuse across phases is deferred.
- Current/retained ordinary bodies need their own accepted authority; never derive it from SQL presence.
- Shared bytes include target, group, repeated metadata, owner payloads and projected paths; closure must remain one snapshot with no native restoration or caller hooks.

### Task1: Incoming payload composition

**Create:** `persistence_proof_owner_payload.py` (private inert closed schema and reference projection), `persistence_proof_target_incoming.py` (snapshot composition), corresponding fixtures/tests and scaling driver.
**Modify:** private budget plumbing in `persistence_proof_identity_group.py` and private snapshot seam in `persistence_proof_target_group.py`; public behavior stays unchanged.

**Interface:** `read_target_incoming(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,max_members=4096,max_bytes=8388608,max_source_bytes=1048576,max_metadata_bytes=1048576)` returns frozen `RawTargetIncoming(target,group,owners)`. Each owner result has namespace, typed_key, storage_kind, raw source, all selected target paths. Supplied record authority must match pin/store/codec even if no ordinary body is selected; an ordinary body without it rejects.

- [x] Write RED tests: all target kinds; actual payload/body matching; wrong kind/path/ID; extra aliases; ordinary current/retained; raw schemas/events/immutable fields; no-native hook guards; source/member/aggregate budgets.
- [x] Implement shared parent source charging and private checked snapshot seam. Existing public reader remains owned-snapshot only.
- [x] Implement inert closed World schema decoder and complete selected-reference projection; reuse auxiliary adapters, preserve implicit Event-ID owner-zero route.
- [x] Run focused/affected proof tests; add clean1k/10k/100k archive diagnostic with source hashes, exact paths, zero archive bodies, bounded Python allocation and untimed interval-one VM enforcement.
- [x] One fresh review; fix blockers with RED→GREEN evidence; retain results; publish candidate and stop after starting longer CI.

Acceptance: CI40202262497 verified on2ce0745:4006 full-suite/910 proof tests,21 complete matrices. Hosted incoming126.10/141.87/155.29ms, zero archive bodies. Receipts: docs/performance/run-40202262497/acceptance.json.
