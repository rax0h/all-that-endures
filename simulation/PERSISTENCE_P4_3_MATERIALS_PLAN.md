# P4.3 — materials / active-index lazy migration plan

**Date:** 2026-10-05  
**Authority:** `STAGE_0_5_SOL_EXECUTION_HANDOFF.md`, section 4, following the green
people and magic-resource family gates.  
**Starting head:** `5e1e693930bb26b4b11509ff3979574e89a0e924`.

## Scope

Migrate the measured material family without changing simulation rules:

- `world.materials.lots`
- `world.materials.items`
- `world.materials.lot_index`
- `world.materials.active_lot_index`

Keep `next_lot` and `next_item` in the accepted eager/cold state. Preserve the
existing selection/rank/whole-unit caches as derived runtime state only.

No wallets, advancement, metaphysics, relationships, genealogy, institutions,
`event_ids`, checkpoint-default replacement, Stage 1, balance change, endurance
run or merge belongs to this slice.

## Representation and invariants

1. `lots` and `items` use the existing versioned lazy-record/order primitives.
   Dictionary order remains the exact current cold/checkpoint order. Delete and
   reinsertion append at a new ordinal, matching Python dictionary semantics.
2. `MaterialLot` and `CraftedItem` become `IndexedRecord` subclasses only to
   expose direct supported field mutation to the persistence tracker. Their
   serialized/canonical fields and simulation behavior remain unchanged.
3. A lot's `transfers` list remains an arbitrary mutable list: append, extend,
   insert, replacement, deletion, slice edits, reorder and retained external alias
   all remain supported. It is not segmented or declared immutable in this slice.
   A retained list may rehydrate its evicted owning lot and dirty the real owner.
4. `lot_index[sid]` remains the canonical ordered list of every lot ID ever
   created for that settlement. It is lazy per settlement and supports arbitrary
   list edits/order/duplicates; ordinary open must not materialize those lists.
5. `active_lot_index[sid]` remains the canonical current set of active lot IDs.
   It is lazy per settlement and supports existing set mutations. Its size is
   genuine active stock, not silently reclassified history.
6. Persistent current-query membership for lots is derived from the lot record:
   `active_settlement=sid` only while `quantity-consumed > .01`, and
   `active_rank=(sid, material_rank)` on the same condition. Membership and the
   owning lot version publish in one generation.
7. Existing `MaterialEconomy.available`, `has_available`, `best_available`,
   `best_at_rank`, `magical_available_count`, `selection_ids`, and
   `crafting_capacity` must preserve result ordering and tie behavior.
   Current operations may use lazy active buckets/memberships and derived
   ID/primitive caches; they may not force a full `lots` or `lot_index` scan.
8. `rebuild_active_index()` remains an explicit full maintenance operation. It
   may stream/materialize the required logical archive because callers explicitly
   requested a rebuild; ordinary open/save/gameplay may not invoke it implicitly.
9. P2C identity links remain sharing authority. Versioned occurrence/incarnation
   rows cover top-level lots/items/index buckets and nested lot transfer lists.
   Cross-boundary sharing must remain exact. One live mutable instance exists per
   incarnation in a lazy session.
10. Conversion remains explicit, checked, source-preserving and no-overwrite.
    P3B source records are streamed into the destination; EventLog behavior and
    accepted P3 authority are unchanged.
11. Save remains one combined publication with people, aspirations, magic
    resources, owner index, materials, cold tail/segments, counters, current
    links and the single head. Failed/ambiguous saves preserve accepted recovery
    behavior; no-op saves write nothing.
12. Materializing detach produces plain portable dictionaries/lists/sets with the
    same values, order, aliases and retained live objects where already loaded.
    Close never implicitly materializes the material archive.

## Files / APIs

Expected implementation surface:

- `simulation/ate_sim/materials.py`
  - tracking-only `IndexedRecord` inheritance;
  - query helpers may recognize lazy active membership adapters without changing
    gameplay semantics.
- `simulation/ate_sim/persistence_lazy.py`
  - material namespace/schema constants;
  - conversion insert/membership helpers;
  - bounded lazy lot/item/list-index/active-index adapters;
  - material identity binding, save plan, layout/count, validation, detach,
    diagnostics and open exclusions.
- `simulation/tests/test_persistence_lazy_materials.py`
  - differential/lifecycle/alias/order/scaling coverage.
- Existing material-selection tests remain authoritative and must stay green.

Do not alter P1/P2/P3 transaction semantics or introduce a universal proxy layer.

## Focused proof matrix

The focused gate must cover:

- open with zero unrequested lot/item/index-bucket payload loads;
- point lot/item load exactly on demand;
- `available` and active/rank queries match eager controls in stable ID order;
- create lot/item, partial/full consume, purchase-style owner mutation, transfers,
  delete/reinsert and reopen;
- direct supported field mutation dirtying;
- retained lot `transfers` alias after cache eviction, save and reopen;
- retained `lot_index` list and `active_lot_index` set aliases after eviction;
- arbitrary list/set mutations preserve order/duplicates/set semantics;
- derived selection, rank heaps, selection pool and crafting-capacity behavior
  stays differential with the eager material implementation;
- no-op save produces zero additional payload writes;
- save failure / resolve paths remain atomic old-or-new;
- materializing detach returns plain portable containers and checkpoint roundtrip
  preserves digest;
- 1,000 -> 10,000 cold historical lots with fixed active A/R/K does not increase
  ordinary-open lot/item/index payload loads; measure store rows/bytes, resident
  lot/item/bucket counts and active-query loads;
- nested lot payload growth from `transfers` is reported honestly as a remaining
  per-owner cost rather than called solved.

Run these focused tests plus the existing material-selection and affected P4 lazy
tests. Batch fixes on stable product bytes. Run one full `simulation/tests`
suite only at the integrated stable gate required by the Astra handoff, not for
every small material fix.

## Gate / continuation

When the focused material gate is green and measurements satisfy the fixed-active
bound, update the P4 evidence/inventory and continue to the next measured residual
family from the handoff (wallets/paths/souls or whichever residual measurement
actually dominates). Do not request routine Astra permission. Stop only for a
fundamental invariant conflict, unavailable capability, a running long job, or
the explicit long-horizon authorization boundary.
