# Bounded raw reference closure implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline.

**Goal:** Validate all directed reachable backing references, their complete physical owner projections, incoming groups/bodies and selected extents in one checked snapshot, preserving shared aliases and mutable cycles.
**Architecture:** Compose existing closed raw readers with one shared source/work budget. Extract private checked incoming composition; allow its group reader to use a context-bound shared Sources. Enable an operation-local accepted raw value memo and extent memo only for the new closure reader; existing readers retain their defaults. Breadth-first discovery derives every edge from actual accepted physical owner bodies (including map keys and Event-ID fixed component slots), compares complete OwnerScope projections, and checks every distinct target's incoming bodies/extent/policies. Return raw canonical-by-incarnation nodes/typed physical edges only. Verify acyclic frozen certification dependencies bottom-up against actual reached extents; mutable graph cycles remain valid. Frozen certification cycles are explicitly unsupported and fail closed rather than treating stored cyclic bits as independent truth.
**Tech Stack:** Existing Python/SQLite accepted roots and pytest.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md; docs/performance/proof-map-foundation/NEXT_INTEGRATION.md.

## Global constraints
Existing dedicated branch and inline execution authorized. No new publisher, node formats, persistent certificate, native registry/restoration, World activation, main merge, endurance or long CI polling. Requires accepted six-root scope authority. Only directed outgoing closure from one supplied typed root is certified; incoming owners' other references are not followed merely because that owner aliases a reached node. Entirely unindexed outside owners, global liveness/inventory, complete World field domains, semantic transition reuse/producer, full manifest/copy/fencing/participants/World remain gated. This is a bounded full selected-closure audit/reference path, not ordinary admission.

## Interfaces
read_reference_closure(store,pin,reference,content_authority,scope_authority,inventory_authority,*,record_authority=None,max_targets=128,max_edges=4096,max_members=4096,max_children=4096,max_values=65536,max_bytes=33554432,max_source_bytes=1048576,max_metadata_bytes=1048576) returns RawReferenceClosure(root,targets,edges,immutable_targets). Targets are sorted RawTargetMembers, one per reached incarnation; edges retain source incarnation, physical owner namespace/typed key/path and target incarnation/kind. max_targets capped1024; other bounds match existing readers. max_members sums all reached incoming rows; max_edges sums all outgoing physical reference occurrences. One source-byte budget and one child/value-work budget cover all nodes; Event-ID component extents are charged once even when also reached as nodes. No memo crosses operation/snapshot boundaries.

## Review focus
- A child body with omitted/surplus catalog placement must reject even if target descriptor and incoming proof are otherwise valid; include map-key and nested immutable references.
- Repeated aliases and mutable cycles must terminate while preserving each physical path; conflicting typed kinds for one incarnation must reject.
- Empty primitive/sequence-branch owners must have zero reference scope; do not treat branch links as native graph references or feed branch bodies to leaf-only adapters.
- Frozen bits need actual descendant validation; false leaves and true/false chains must reject mismatches, and cyclic certification uses a distinct fail-closed unsupported path.
- Cached extents/Event-ID components must still receive complete incoming validation; shared budgets and retained/current authority must not reset or mix across nodes.

## Task 1
- [x] Add real accepted-root RED graph fixtures/tests covering aliases, mutable cycles, outgoing projection errors, missing/wrong child targets, map keys/records/sequences/Event components, frozen truth/cycles, budgets and atomic retained recovery.
- [x] Implement private shared composition, context-bound raw source/extent memo and bounded graph reader without changing existing public behavior.
- [x] Run focused/all proof and related existing runtime suites, raw physical corruption and stale/legacy tests.
- [x] Clean source1k/10k/100k unrelated-parent scaling with zero unrelated bodies, bounded metadata/VM/memory, interval-one guarded replay and source hashes.
- [x] One fresh independent review; fix Important/Critical issues in one RED→GREEN pass, retain minors and decisions.
- [ ] Publish candidate/start long CI and stop with link.
