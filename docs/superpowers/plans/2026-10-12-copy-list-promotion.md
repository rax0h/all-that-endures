# Persisted List Copy Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Native execution is authorized by the complete Stage0.5 directive.

**Goal:** Promote explicitly selected persisted append backings into counted sequences during the checked private copy, preserving incarnation, values, order and sharing.

**Architecture:** Read selected checked lists only during explicit full-copy preparation. Build counted output with the existing LazyOrderedSequence in the mutable-empty destination, rewrite compact reference roles in copied current headers, and project new physical leaf ownership through the existing catalog. Remove selected old append descriptors/pages only from the destination. Ordinary assignments retain their no-hidden-migration guard; source objects, methods, pins and bytes remain unchanged.

**Tech Stack:** Existing Python/SQLite copy, typed histories, counted sequences and checked catalog.

**Spec:** simulation/STAGE_0_5_FINAL_ARCHITECTURE.md §§8,10; simulation/STAGE_0_5_SOL_61_EXECUTION.md.

## Global Constraints

- Explicit O(H) conversion is allowed here; ordinary mutation/open must not perform it.
- No second registry, publisher, ownership graph or capability6 completeness claim.
- Keep selected incarnation IDs and source allocator; do not merge equal separate lists.
- Preserve nonselected collections, source aliases and unsaved source overlays.
- Rank issue17 remains deferred; no gameplay, endurance or PR14 changes.

## Review Focus

- Selecting a nonexistent, wrong-kind, duplicate, boolean or retiring ID fails before publication.
- Multiple aliases keep one counted backing; equal independent lists keep different IDs.
- Empty and multi-page lists retain exact native order/duplicate behavior.
- Old physical child routes must become new permanent-occurrence leaf routes.
- Existing collection ordinals/high-water counters and unrelated namespaces remain coherent.

### Task: private promotion integration

**Files:** Create simulation/ate_sim/persistence_history_copy_promotion.py; modify simulation/ate_sim/persistence_catalog_copy.py; create simulation/tests/test_stage_0_5_final_copy_promotion.py.

**Interfaces:** `_copy_with_checked_catalog(..., promote_lists=())` accepts an explicit finite selection. The promotion helper validates/captures selected source list values and transforms copied version/ordinary changes, placements, rosters, ordering metadata and catalog inputs using existing primitives.

- [x] Write RED for copied persisted list promotion with shared aliases and same incarnation.
- [x] Implement checked selection and existing counted builder, then role/physical-placement transformation.
- [x] Verify save/reopen, counted household assignment, empty values, multiple IDs, faults and source preservation.
- [x] Run focused and affected copy/promotion/sequence gates; checkpoint exact source/evidence.

Final focused20 passed in3.58s. Affected96 passed in99.27s, preceding only
the extra held-source-alias test (covered by focused20). Production matches
both gates. Extra locator RED reproduced a semantic validation gap; the copy
now invokes the existing full counted-sequence scrub before publication.
Both real commit fault phases, wrong-kind/retiring/missing selections, two
equal independent lists, nested leaf placement and source pending overlays pass.
This is opt-in private copy promotion, not ordinary format6 activation.
