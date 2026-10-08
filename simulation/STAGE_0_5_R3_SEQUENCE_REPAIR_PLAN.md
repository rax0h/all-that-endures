# Stage 0.5 — R3 household-member sequence repair boundary

**Status:** reproduced, **not repaired**. This is a blocking structural
issue, not a passing P4 completion result. This document is a proof-first
implementation plan, not acceptance or authority to begin unrelated work.

**Source boundary:** final architect review at
`85f8ac6cb5fafac7c16f8a3bc2d203f3548aaad8`.
**Initial repro:** Actions run `37727798155`, fixture with a 1,000-entry
household member list. `sys.getsizeof(world.households[1].members)` was
8,872 bytes; the list was fully resident at ordinary lazy session open.
The final architect review also contains the independent 100/1,000-row
eager open measurements and the original source pattern.

## Why this is a true separate blocker

`world.households` is currently restored as an eager root collection through
`_restore_collection` in `open_lazy_world_session`. The nested
`Household.members` field is a native list of historical member IDs.
`Simulation._demography` appends each birth's ID, and the list is never
truncated simply because a person dies. The existing P4 residual inventory
counted *root eager payload bytes*, but did not measure nested retained Python
lists. A bounded count of rows therefore did not establish bounded memory.
Changing a list to a tuple, range, compressed blob or a full-list wrapper does
not solve both ordinary memory and single-append write amplification.

## Required architecture, before integration

1. Keep `Household.members` a logical exact ordered sequence of integer IDs,
   including duplicates and arbitrary supported positional/slice edits.
   `len`, iteration, indexing, membership, list equality and deterministic
   canonical serialization must preserve precisely the old visible sequence.
2. Use a versioned checked sequence authority. Store owner/incarnation-scoped
   length plus individually addressable ordered entries or bounded fixed-size
   pages. A read pin chooses one generation. Ordinary open loads no unrequested
   member payloads; a single append changes only its bounded tail/length, not
   every historical entry. Positional edits may touch the affected suffix but
   must not rewrite unrelated households. Preserve current identity links as
   sharing authority rather than inventing a second conflicting alias graph.
3. The explicit cold-to-P4 conversion must move existing historical member
   payloads into that authority under an atomic no-overwrite destination
   publication while preserving the source bytes. The eager household record
   must have a **physical** compact storage representation, while its public
   canonical `members` field presents the complete logical list. Never let
   an empty physical storage placeholder enter the gameplay digest, a legacy
   export, or a materialized detach.
4. Integrate sequence operations with the existing eager tracking and hybrid
   save plan so member-entry versions, sequence metadata, owner record fields,
   identity occurrence changes and event-tail authority publish at **one**
   generation. No-op save must not rewrite sequence history. After ambiguous
   save, `resolve_save` must reconcile the same intended sequence exactly
   once; a stale writer cannot publish any part of the loser.
5. Preserve actual alias identity under retention, eviction, transfer and
   replacement. Direct mutation through retained `members` aliases must dirty
   the current canonical owner, not an obsolete replacement. On explicit
   `detach(materialize_history=True)`, produce an ordinary portable Python
   list with exact sharing relationships. Existing P1/P2/P3B APIs and ordinary
   checkpoint defaults remain unchanged.

## Required proof fixtures

- Independently generated control versus converted World at both 1k and
  10k retained member IDs: exact order, counts, digests, identity and no
  archive-proportional ordinary-open residency. Record actual decoded bytes,
  checked row/SQL work and Python retained memory.
- Append one birth to a 10k-member household: near-flat payload writes,
  unrelated owner rows untouched, current-head old/new atomic publication.
- In-place index assignment, insertion, deletion, slicing, reverse, sort,
  duplicate IDs, list concatenation, empty and singleton cases, negative
  indexing, membership, and snapshot iteration with proper mutation guarding.
- Retained top-level/nested alias, cross-owner shared list, move, replace,
  delete/reinsert, clean eviction and reopen; confirm accepted P2C sharing.
- Disk/write failure, pre/post-commit fault, lost acknowledgement, stale
  competing writer, pin evolution, copy/backup, source-preserving conversion,
  failed detach and portable materialization, and a short independent
  continuation with exact events/RNG outcome.
- Recheck remaining nested eager history after migration; do not assume the
  scalar `world.households` row count proves every field bounded.

## Implementation gate

First implement/test standalone checked sequence authority and incarnation
semantics. Only then integrate cold conversion, World adapters and combined
save/lifecycle. Run focused then affected tests and short independent
continuation. If a complete gate fails, retain **R3 BLOCKED** and do not
declare Stage 0.5 accepted, schedule endurance, merge or enter Stage 1.
