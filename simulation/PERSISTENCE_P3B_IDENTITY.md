# P3B next bounded assignment: event identity scope and retirement primitives

Status: implemented and accepted at `b756023395a3acb2aa0bfae9326e76dc6f10cd4e`;
see `PERSISTENCE_P3B_IDENTITY_REVIEW.md`. The next assignment is
`PERSISTENCE_P3B_IDENTITY_RESTORE.md`. This specification narrows execution of
section 5 of `PERSISTENCE_P3B.md`; the
parent document remains the full architecture, not authorization to implement
all remaining tasks in one turn. P1/P2/P3A and the reviewed composite EventLog
remain accepted underneath this work. Stage 0.5 remains decision B, unmerged.

## Objective and boundary

Prepare the reusable identity-index primitives needed by a future cold World
session. Discover current mutable sharing without reading or retaining sealed
log history, and remove retired event owners while preserving/reanchoring the
remaining occurrences. Do not implement a cold session or transaction yet.

Allowed product files: `ate_sim/persistence_identity.py` and, only if needed for
a narrow internal accessor, `ate_sim/event_log.py`. Add
`tests/test_persistence_event_identity.py`. Reuse existing test fixtures where
practical and record measured results in
`PERSISTENCE_P3B_IDENTITY_VALIDATION.md`. Other product-file changes require a
concrete blocker reported for architectural review, not speculative expansion.

Do not wire these primitives into `IncrementalWorldSession`, change adapter
formats, implement restore/relink, add snapshot creation/conversion, save-plan
composition, acknowledgement recovery, detach, engine guards or exports in this
slice. Those callers must be adapted later; this is not acceptance of an
integrated cold World or of complete binding-memory reclamation.

## 1. One reusable event-identity enumeration boundary

Add an internal helper in `persistence_identity.py` (suggested name
`iter_mutable_event_items(log)`) yielding `(absolute_index, original_Event)`.
It supports an ordinary or disk-backed EventLog and has these exact semantics:

* Let D be the disk event count, F = D + pending sealed chunk count * 2,048,
  and N the logical count. Inspect only the existing `_tail`, at absolute
  indices `[F,N)`. Never enumerate the logical log, slice it, decode a pending
  chunk, read a disk segment, or create an intermediate list of history.
* Exclude individually sealed Events in the tail as well as all `[0,F)`
  occurrences. Semantic sealing, not successful segment transfer, ends LOG
  mutable-identity ownership. Missing `_sealed` and explicit False both mean
  mutable; preserve objects and flags without modifying or freezing anything.
* Preserve absolute indices, object identity and order. Holes for individually
  sealed tail Events do not renumber later occurrences.
* Enforce the existing borrowed-backend lifetime before beginning and before
  each yield, including resuming a suspended iterator after close. Do not open
  a reader or take ownership of the store. No simulation mutation during an
  enumeration is supported; these are quiescent, internal operations.
* Iteration uses O(1) auxiliary memory and O(N-F) visits. It creates no new
  retained cache/index and does not traverse any Event's children itself.

Keep this helper read-only. Do not change public EventLog iteration, sealing,
append, equality, lookup, caching or storage ownership.

## 2. Explicit opt-in occurrence-index scope

Extend `IdentityOccurrenceIndex` with an explicit constructor option for cold
identity projection (suggested `mutable_event_tail_only=False`). The default
retains accepted legacy behavior for ordinary in-memory EventLogs. A default
index encountering a disk-backed EventLog must fail clearly before reading its
history; the opt-in scope is required, not an implicit full traversal.

In opt-in mode, when `_scan` encounters an EventLog:

1. Include the log object itself as an ordinary mutable occurrence, preserving
   aliases to the log root under different paths.
2. Descend exclusively through the helper above, using absolute `index` path
   components. Apply this rule everywhere the log is reached, including through
   an alias under another current record, not only at `World.events`.
3. Preserve existing recursive behavior, cycle rejection, shared-parent and
   descendant discovery for all remaining current objects.

A sealed Event independently reachable through non-log World fields is NOT
globally excluded. Those occurrences and their existing sharing remain current;
only occurrences obtained by descending into sealed LOG history are excluded.
Do not redefine global record mutability based solely on an Event's sealed flag.

For owner-wise bootstrap, provide/reuse a small adapter over the same helper
yielding `(owner, value, path)` with owner `("world.events", absolute_index)`
and path `(("field", "events"), ("index", absolute_index))`. It must yield
only eligible event owners. Future callers must use it instead of
`enumerate(world.events)`. Direct `bootstrap/refresh` callers still supply valid
owner roots; do not guess missing log context from an arbitrary nested path.

Do not weaken `seed_explicit_links`: an explicit link with an endpoint absent
from the projected graph must fail, not be silently discarded. Full saved-path
validation before resolution, and creation-time conversion/reanchoring, remain
requirements for the future adapter/session integration.

## 3. Batched owner retirement

Add `IdentityOccurrenceIndex.retire_owners(owners) -> (removed_links, added_links)`.
This is the reusable occurrence-index operation that later sealing hooks will
call for newly ineligible log owners. It performs no store writes, binding-hook
changes, Event mutation or prefix adoption.

* Remove all supplied owners' occurrence rows first, then recalculate links
  once per affected identity using the existing codec-ordered anchor rule.
  Report a final patch relative to the previously indexed explicit links;
  do not emit transient anchors for partially retired batches.
* Update `owner_occurrences`, `occurrences`, `path_to_ident`, and
  `links_by_ident` consistently. Release objects/paths held solely by retired
  owners. Preserve current occurrences of objects that also have other owners.
* If the old anchor retires and at least two occurrences survive, report old
  link removals and new links anchored to a surviving path. One surviving
  occurrence needs no link; zero surviving occurrences need no retained entry.
* Handle parent and descendant aliases, a batch containing all anchors, and
  individually sealed tail-owner retirement. Do not rescan unrelated owners
  or bootstrap the full graph. Use the existing reverse occurrence structures.
* Empty input, duplicate owners and already absent owners are harmless. A
  repeated retirement returns an empty patch. Validate the owner iterable into
  an owner set before changing the index, so malformed/unhashable input cannot
  leave an accidental half-applied retirement.
* Output contains no duplicate link or simultaneous addition/removal of the
  same encoded link. Preserve exact P2C path encoding and deterministic anchors.
  Default-mode behavior of the existing `refresh` API remains compatible.

Complexity: O(occurrences removed + paths in affected alias groups), apart from
the existing per-affected-group anchor sorting. There must be no term depending
on unrelated cold events or unrelated current alias groups. It is acceptable
that one genuinely large affected alias group costs proportionally to its size.

This removes retention within the occurrence index only. `_BINDINGS`, `_memo`,
dirty ownership, baseline ordinals and old tracked children must be retired by
the later session integration before any end-to-end bounded-memory claim.

## 4. Required evidence

Use small synthetic event fixtures and accepted checked P1/P3A APIs, not a
long simulation run. Tests must establish all of the following:

1. Helper equivalence to an independently constructed expected tail, including
   empty/in-memory/disk logs, pending chunks, absolute indices and an individually
   sealed tail Event. Ordinary public history iteration remains unchanged.
2. With real 4- and 40-segment stores and the same resident suffix, helper and
   cold-mode index discovery perform zero segment reads and zero pending-chunk
   decodes. Instrument forbidden traversal paths to fail on use. Report actual
   occurrence/path counts; they must be independent of disk-prefix size.
3. Root aliases to an EventLog obey the same projection. Shared tail data and
   nested parent/descendant aliases are retained exactly. A sealed Event held
   under two non-log owners still has those two current occurrences.
4. A saved explicit link into an excluded log occurrence fails index seeding;
   do not resolve it by touching disk. Retained valid current links still seed.
5. Reader/store close, including while helper iteration is suspended, fails
   before yielding another Event. Values already returned remain unchanged.
6. Bootstrap eligible owners, seed links, seal a chunk with the accepted
   EventLog rule, and retire the resulting log owners. Compare the resulting
   live occurrence groups and current links against independent expected
   surviving paths. Check old-anchor retirement, one/zero survivor cases,
   shared-parent descendants, multiple owners in one batch and idempotence.
   Repeat with individually sealed tail Events.
7. References retained exclusively by the index disappear after retirement;
   surviving current owners remain. Use weak references/GC or equivalent
   direct retention assertions while accounting for caller references and
   the permitted bounded EventLog cache. Repeated seal/retire cycles must not
   accumulate owner/path/link entries for history.
8. At 100/300/1,000 unrelated current alias groups, retire one fixed local
   event group. Measure scanned owners/affected groups and patch sizes. No
   unrelated owner rescan or unrelated link rewrite is allowed; document the
   same bounded local result at each size.
9. Keep the existing P2B/P2C identity, EventLog and P3A regressions green.

Tests here do not prove restored continuation, atomic cold save, binding
retirement or format compatibility for a cold World. Those remain explicit
future acceptance gates in the parent architecture.

## 5. Execution and delivery

Verify live PR #14/head and read repository instructions first. Do not revert
the review's typed-value comparison or generation guard in prefix adoption.
Implement this slice with focused tests, then run the affected persistence and
EventLog suites. Run one full `simulation/tests` suite on stable final code;
there is no need to run it repeatedly during development.

Commit only this scope to `sim/stage-0-5-stabilization`, using `[skip ci]` because
the ordinary workflow includes a prohibited millennium run. Do not weaken or
modify workflows. If using an isolated unit-test CI candidate, verify exact
product/test blob equality with the landed commit.

Return the exact head, files changed, commands/results, measured bounds and any
remaining limitation. Stop for architect review. Do not proceed into session
implementation, alter balance/magic progression, run millennium/endurance,
start Stage 1, replace normal checkpoints or merge PR #14.
