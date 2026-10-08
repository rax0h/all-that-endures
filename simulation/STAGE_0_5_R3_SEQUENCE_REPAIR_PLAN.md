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


## 2026-10-08 execution update: checked page foundation landed

A standalone, **not yet World-integrated**, R3 storage primitive now exists at
`ate_sim/persistence_lazy_household_members.py` with focused tests at
`tests/test_stage_0_5_household_sequence.py`. This addition does not alter the
current lazy World storage mode or claim R3 closure.

The original focused foundation test run
[37732587525](https://github.com/rax0h/all-that-endures/actions/runs/37732587525)
passed **6/6 in 0.63s**. It covered 1k and 10k historical member IDs,
generation-pinned checked pages, bounded four-page read caching, duplicate
and positional edit behavior, corruption and mutation-guard rejection,
and a single append that wrote exactly **two lazy payload records**
(length + bounded tail) at each historical size. Observed write payload
bytes were **1,497 at 1k** and **283 at 10k**; the differing bytes reflect
the current partial tail and are not an O(history) cost.

After adding failure, old-generation and shrink tests, a later focused
job [37733205786](https://github.com/rax0h/all-that-endures/actions/runs/37733205786)
reported **9 standalone cases passing**; its **overall job failed**
because one of the opt-in World pilot tests expected births to be forbidden
inside `current_people_scope`. That expectation was wrong and has been
corrected on the isolated pilot branch. The standalone failed-attempt test
was also corrected to use accepted explicit `resolve_commit` semantics
before retrying. Never present the pilot job as all-green.

An isolated opt-in World conversion/save pilot (development branch
`sim/stage-0-5-r3-implementation`) has been built but **not promoted**:
its cold-to-P4 conversion physically projects compact household records,
installs checked member pages under auxiliary namespaces, binds the
public sequence, includes canonical-digest streaming, and publishes page
changes in the same hybrid generation. It has passed the original 1k/10k
World digest/append/reopen checks but is still undergoing additional
alias, lifetime, new-household, detach, and recovery validation.

**Unresolved acceptance work:** support newly created/deleted/replaced
households and shared/cross-owner member-list aliases with unchanged
identity and detached-alias semantics; validate true short independent
simulation and failures; re-inventory other nested eager histories.
The pilot refuses shared source member-list links and late new-owner saves
rather than silently corrupting them. Those refusals are fail-safe
development limits, **not accepted final behavior**.

No endurance or replacement late-fixture capture is authorized or
performed. Stage 0.5 remains blocked.
