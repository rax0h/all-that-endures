# Sequence and Event-ID extents implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline.

**Goal:** Finish bounded raw extent validation for all nine closed target kinds, adding counted sequences and compact/exceptional Event IDs.
**Architecture:** Explicit include_children=True,include_sequence=True construction adds a sixth version3 scope root for the four existing sequence internal families (parents,occurrences,members,member_directory), grouped by parent incarnation. The version2 five-family child root and four-root version1 encodings remain unchanged. Existing atomic scope publication maintains the sixth root from actual prepared changes; old roots never gain implicit authority. A read-only sequence checker borrows existing pure node/member/directory commitment methods, verifies complete tree/rank/locator/reciprocal-parent/member order and exact physical inventories under accepted content. Event-ID authority validates the existing owner-zero root plus its two fixed exception slots, composes accepted sequence/set extents and preserves exact bool/float representatives. One owned snapshot and shared byte/child/value-work budgets cover the operation.
**Tech Stack:** Existing Python/SQLite immutable maps and pytest.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md; docs/performance/proof-map-foundation/NEXT_INTEGRATION.md.

## Global constraints
Existing dedicated branch/inline execution authorized. No World activation, main merge, endurance or long CI polling. No new publisher, native restoration or object registry. Additional directory has a distinct version3 commitment; default remains version1 and include_children alone remains version2. Internal rows are physical authority, not global parent liveness. Recursive outgoing closure, whole-World field domains/topology, reusable semantic transitions and full manifest/verified-copy/participant/World integration remain gated. Full selected audit is separately budgeted and must not become ordinary admission.

## Review focus
- Sequence native bool/float values intentionally share integer membership keys; reciprocal projections and commitments still require exact encoded types.
- Physical surplus in any internal sequence family must reject without scanning unrelated parent rows; legacy authority must fail closed.
- Event-ID owner-zero has exactly the root path for ranges and root/removed/added paths for exceptions, with exact typed IDs and no competing backing kind.
- Prefix numeric aliases may be added only after their equal integer is removed, preserving stored representatives; all component work shares one budget, including prefix expansion.
- Six-root successors share unchanged descriptors and retain exact old/new/recovery authority through failure seams; existing four/five-root commitments remain compatible.

## Task 1
**Files:** modify persistence_proof_scope.py,target.py,target_incoming.py,child_extents.py; create sequence/event extent modules and fixture/tests/driver; update workflow/evidence.
**Interfaces:** bootstrap_scope_proofs gains include_sequence=False, valid only with include_children=True. Private SequenceScope tag5 covers four fixed existing internal families. RawTargetMembers gains components=(), exposing raw backing extents for Event-ID removed/added children. Existing certification_targets stays frozen-only. Shared max_children counts physical child locators across all components; max_values counts materialized value work (Event prefix span plus removed/added histories), max_bytes remains shared source budget. Public defaults remain unchanged.

- [x] Write real-root RED tests for sequence values/duplicates/native semantics, branch boundaries, internal orphan/missing/typed projection errors, Event range/exception equality/order/count/owner-slot errors, legacy rejection and shared budgets.
- [x] Implement explicit six-root construction/publication/recovery preserving earlier formats.
- [x] Implement bounded read-only full sequence structure validation and Event-ID component composition with exact root/slot joins.
- [x] Verify focused/all proof and affected existing runtime suites; test sixth-root add/delete/sharing/retained/exact failure recovery.
- [x] Run clean1k/10k/100k unrelated-internal-parent scaling with zero unrelated payloads, bounded metadata/memory and interval-one VM guard.
- [x] One fresh independent review; fix Important/Critical findings in one RED→GREEN pass. Retain minor findings and decisions.
- [x] Published7a3f30a; CI40242013460 accepted4135full/1039proof/24matrices on the next green.
