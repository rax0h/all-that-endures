# P4.5 — metaphysics soul lazy migration plan

**Date:** 2026-10-05  
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, STAGE_0_5_COMPLETION_PLAN.md,
PERSISTENCE_P4_INVENTORY.md, and owner handoff at live head
e857873f672b7d23574e5c0a874ac7a4086c6e53.

## Scope

Migrate only `world.metaphysics.souls`.

Keep `resurrection_tokens` and `next_token` eager in this slice. Do not begin
advancement, relationships, genealogy or another family until the soul gate is
green and measured.

## Authority / representation

1. `SoulState` remains the canonical owner record and becomes tracking-aware
   only through the existing `IndexedRecord` notification seam.
2. `authorities`, `marks`, `cosmic_links`, and `transformations` remain
   ordinary supported mutable set/set/dict/list semantics. They are not flattened,
   frozen, segmented, or copied on load.
3. Each soul has persisted incarnation occurrences for:
   - `()`
   - `(("field","authorities"),)`
   - `(("field","marks"),)`
   - `(("field","cosmic_links"),)`
   - `(("field","transformations"),)`
4. Nested wrappers are soul-specific retained-owner adapters using the accepted P4
   identity registry. A retained nested object can outlive parent cache eviction;
   mutation rehydrates/marks every current owning soul for that incarnation.
   Shared nested identity across multiple owners stays one live object.
5. Replacing a nested field detaches only the old occurrence and binds the new
   object/incarnation. Obsolete retained aliases never write into replacement slots.
6. Death is not an immutability boundary. Old souls remain fully mutable.

## Required behavior

- ordinary lazy open decodes zero soul payloads;
- point access decodes only requested souls and their required identity metadata;
- exact dictionary insertion/delete/reinsert order;
- direct scalar SoulState edits are save-visible;
- arbitrary supported mutation through all four nested fields is save-visible;
- retained nested aliases after parent eviction remain live and owner-correct;
- exact top/nested identity survives save/reopen;
- real `record_death`, `mark`, resurrection and transform paths stay differential;
- no-op save writes zero soul payloads;
- precommit and lost-ack recovery remain old-or-new atomic;
- stale session behavior remains accepted;
- source conversion is explicit, checked, no-overwrite and source-preserving;
- materializing detach returns a plain soul dictionary and plain nested containers
  while preserving sharing; checkpoint roundtrip remains portable;
- 1,000 -> 10,000 historical souls with fixed requested access keeps ordinary-open
  soul payload loads at zero and point work bounded.

## Evidence

Measure for 1k and 10k fixtures:
payload reads/bytes, payload writes/bytes, resident soul owners, clean cache count,
identity live bindings/group pins, and fixed point access loads.

After focused + affected soul tests are green, remeasure residual P4 families.
Proceed autonomously to `world.advancement.paths` only if that residual remains
material. Do not start relationships/genealogy before the soul/path tranche is
green.
