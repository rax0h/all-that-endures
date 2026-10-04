# P3B — live cold session open/bind

Status: accepted at `2819391359fa3e2e16f9c8e3151e99ce06d8a373`, 2026-10-04.
See `PERSISTENCE_P3B_LIVE_OPEN_REVIEW.md` for acceptance and historical findings.
This document remains the completed live-open contract. Its cold-save refusal
is intentionally superseded only by the next assignment in
`PERSISTENCE_P3B_COLD_SAVE.md`; all other accepted behavior remains required.
Baseline: PR #14, branch `sim/stage-0-5-stabilization`, accepted cold-bootstrap
head `876d7fcd1300c5a7ab0de006bfd06c450f77d0e8`.

Read before editing:

- `simulation/PERSISTENCE_P3B.md`
- `simulation/PERSISTENCE_P3B_COLD_CAPTURE_REVIEW.md`
- `simulation/PERSISTENCE_P3B_COLD_BOOTSTRAP_VALIDATION.md`
- `simulation/PERSISTENCE_P3B_IDENTITY_REVIEW.md`
- `simulation/PERSISTENCE_P3B_IDENTITY_RESTORE_REVIEW.md`

## 1. Goal

Implement ONLY the live **open/bind/close foundation** for a cold P3B World.

The accepted cold database can already be created, fully validated and captured
as an unbound World. This slice turns that captured World into an owned live
`IncrementalWorldSession` without materializing or traversing the committed
event-history prefix.

The public addition for this slice is:

```python
open_world_session(path, *, rules_id) -> IncrementalWorldSession
```

The returned session exposes its restored World as `.world`, participates in
the existing mutation/identity tracking machinery, supports context-manager
ownership and explicit `close()`, and can continue ordinary simulation in
memory while open.

**Cold save is NOT authorized in this slice.** A cold session's `save()` must
fail explicitly before any persistent or runtime boundary mutation. Atomic cold
save/recovery is the next reviewed slice.

Do not implement `resolve_save()`, `detach()`, `verify_history()`, engine
checkpoint replacement, automatic save cadence, P4, Stage 1, balance changes,
millennium/endurance work or PR merge.

## 2. Required authority boundary

The accepted cold EventLog partition remains authoritative:

- `[0,D)`: committed P3A prefix; immutable disk history.
- `[D,F)`: resident pending sealed chunks; immutable value history.
- `[F,N)`: resident live tail; only unsealed tail occurrences participate in
  mutable LOG identity ownership.

Opening/binding must not alter D, F, N, event IDs, years, causes, sealed flags,
RNG state, current aliases, query-visible values or the persisted store.

The session must never register committed prefix Events or pending sealed Events
as mutable LOG owners. Individually sealed Events still physically present in
the tail are also value history, not mutable LOG owners.

Current non-log World occurrences remain ordinary current identity authority even
when their value also appears in sealed history.

## 3. One store, one captured generation

`open_world_session` must:

1. Open exactly one `TransactionalStore` connection using the existing
   `WorldCodec(identity_links_recorded=True)`.
2. In one caller-owned read transaction, use the accepted cold-capture path to
   capture head, manifest, current links, descriptors, current World state and
   only the resident event suffix.
3. Capture any insertion-ordinal/baseline metadata required by the existing
   incremental tracker from that SAME pinned generation. A narrow helper or
   capture extension is allowed. Do not reopen or compare against a second
   generation.
4. End the read transaction before returning the session.
5. Initialize the existing `IncrementalWorldSession` machinery from the
   already-captured World/store rather than calling its legacy constructor,
   `read_snapshot`, `bind_snapshot`, `verify_all()` or any full-history
   baseline comparison.
6. On success, the EventLog prefix reader and the session must share the same
   owned store authority.
7. On any failure after opening, undo partial wrappers/bindings, close the prefix
   reader if created, close the store, and leave no global session ownership.

Do not leave a read transaction pinned during gameplay.

Another writer may advance the file after the open snapshot completes. This
session still represents the exact generation it captured. Future save conflict
handling belongs to the save/recovery slice; do not silently refresh/rebase.

## 4. Refactor, do not fork P2 tracking

Reuse `IncrementalWorldSession`; do not create a second independent tracking
implementation.

A narrow internal factory/classmethod/helper such as a cold-capture constructor
is appropriate. The exact private name is not architectural, but it must share
the same mutation hooks, root wrappers, dirty/deleted sets, binding registry,
identity occurrence index and current-link reducer used by legacy sessions.

Legacy `IncrementalWorldSession(world, path, ...)` and `bind_snapshot` must
keep their current behavior and validation.

Cold mode must carry an explicit internal mode flag/state. Do not infer cold mode
from incidental object shape after construction.

The cold manifest's `("EventLog-disk/v1", N, F/C)` description must be treated
as the EventLog collection kind where tracker classification requires a base
kind, without rewriting the manifest into the legacy `EventLog` kind.

Preserve stable collection ordinals exactly. Do not reconstruct dict/set
ordinals from current Python enumeration if the persisted rows already contain
authoritative insertion ordinals.

## 5. One event-owner boundary everywhere

Use the already accepted identity helpers:

- `iter_mutable_event_items(log)`
- `iter_mutable_event_owners(log)`
- `IdentityOccurrenceIndex(..., mutable_event_tail_only=True)`

Cold tracking must route every EventLog graph/owner traversal through this
boundary. In particular audit/adapt the cold path through:

- `_bind_root_collection`
- `_iter_identity_owners`
- `_bootstrap_identity_index`
- `_current_identity_links`
- `_owner_value`
- `_remove_owner_recursive`
- `_plain`
- `_unwrap_value`
- any `_contains_identity` / incoming-alias traversal reached by normal
  tracked mutations
- traversal through a current alias to the EventLog root itself

Do not use ordinary `for event in log` for cold tracking, because it walks the
disk prefix.

The EventLog object itself may remain a mutable identity object when it is
legitimately aliased by current World state. Its historical children still obey
the mutable-tail-only boundary.

Malformed persisted cold identity paths that descend into committed/pending
sealed history must continue to be rejected by accepted cold capture/identity
validation without reading cold payloads.

## 6. Binding and mutation behavior

After open:

- current non-event roots are wrapped/tracked exactly as in accepted P2C;
- mutable EventLog tail Events are bound using absolute logical indices;
- pending sealed and committed Events have no LOG owner/binding/index rows;
- individually sealed tail Events have no LOG owner/binding/index rows;
- current shared parent/child identity is preserved;
- cross-session mutable alias rejection remains intact;
- appending a new Event registers its absolute `("world.events", index)` owner;
- ordinary current mutations mark only their actual owners;
- no operation performed merely by open/bind may dirty the World.

A successful open must begin with empty dirty/deleted sets and no pending
current-link patch.

The capture already proved current-link authority. Do not run the legacy
full-World identity audit or rebuild identity by decoding old history.

## 7. Semantic sealing retirement

This slice DOES include the in-memory identity transition caused by
`EventLog.seal_before()`, because the next atomic-save slice depends on it.

When one or more leading live-tail chunks become pending sealed chunks:

1. Preserve the existing EventLog sealing rule and timing exactly. Do not call
   sealing merely for persistence convenience.
2. Determine the exact LOG owners that moved from mutable tail to sealed history
   using absolute indices; do not decode committed history.
3. Retire those owners from `IdentityOccurrenceIndex` using the accepted
   affected-owner retirement primitive.
4. Merge the resulting current-link removals/reanchors through the existing
   final-state reducer.
5. Remove only the retired LOG owner from object binding ownership. If the same
   object remains owned by another current World record, keep that binding and
   its tracking.
6. Ensure old mutable children replaced by `Event.freeze()` no longer dirty
   the log. If such a child is still referenced by current World state, mutation
   through that surviving reference must dirty the surviving current owner.
7. Do not retain newly sealed source Event objects merely because tracking once
   owned them. Use weakref/reference-map tests where supported.
8. Do not persist anything in this slice.

Absolute paths for the remaining mutable tail do not shift when F grows; only
the mutable-owner floor advances.

An individually sealed Event in the tail must be excluded from LOG ownership
without pretending it creates a transferable full chunk.

## 8. Cold save is deliberately blocked

Until the next slice, calling `save()` on a cold session must raise a clear
`StoreError` (or a more specific existing store error) before:

- refreshing/publishing cold identity;
- preparing a P3A append;
- committing records/segments;
- changing D/F partition ownership;
- clearing dirty state;
- advancing session generation.

User simulation edits and dirty state must remain intact after this refusal.

Legacy P2/P2C sessions must continue to save normally.

Do not partially implement cold save behind a private flag in this assignment.
The next slice will review the entire one-generation save and lost-ack recovery
boundary together.

## 9. Close and ownership

Cold `close()` must be idempotent and must not save.

For this bounded slice:

- unbind current tracked state without enumerating the committed prefix;
- clear global binding ownership;
- close the EventLog's owned/borrowed prefix reader;
- close the session store;
- mark the session inactive;
- do not materialize history;
- do not mutate the database.

After close, disk-backed EventLog operations that require backend readability
must fail explicitly through the existing closed-reader/store checks. Already
returned frozen Event values remain ordinary Python values.

The stronger engine-wide fail-before-mutation guards, detach/materialization,
checkpoint behavior and explicit full-history verification remain later lifecycle
work. Do not widen this slice to implement them.

If a caller closes `session.store` directly while the session is otherwise
active, subsequent EventLog backend access must fail; do not silently reopen.

## 10. Required tests

Add a focused cold-session test file (for example
`test_persistence_session_open.py`). Reuse existing fixture helpers where
reasonable; do not weaken accepted cold-capture/bootstrap tests.

At minimum prove:

### Open/capture modes

- empty cold World;
- tail-only cold World;
- prefix-only cold World;
- mixed prefix + mutable tail;
- a cold fixture with resident pending sealed chunk(s);
- individually sealed tail Event;
- wrong rules;
- legacy P2/P2C source rejected with explicit instruction to run
  `convert_event_storage`;
- malformed/mixed cold mode still rejected;
- corruption confined to an old sealed segment is deferred on lazy open and
  fails when that segment is actually accessed.

### Exact live identity

Construct independent expected state and prove after open:

- parent/child aliases across current World fields survive;
- current field <-> mutable-tail child alias survives;
- current field <-> mutable-tail Event alias survives when legal;
- current alias to the EventLog root, if supported by the existing codec,
  does not cause prefix traversal;
- individually sealed/pending/cold log occurrences are absent from current LOG
  identity ownership;
- no dirty/deleted/link patch exists immediately after open.

Mutate through retained aliases and assert the correct current owners become
dirty without scanning cold history.

### Sealing retirement

Create enough mutable tail to seal at least one complete chunk while the cold
session is open. Include:

- a retained Event reference;
- a mutable child shared between an event and a current World record;
- a shared parent+child group whose old identity anchor is in the event log.

After sealing, prove:

- the Event is frozen exactly as normal EventLog semantics require;
- retired LOG owners are gone;
- surviving current owners remain bound and dirty correctly;
- identity links are reanchored rather than discarded;
- the detached old child no longer dirties LOG ownership;
- no disk segment payload was read;
- retired source objects are not retained by session internals once caller
  references are released, except where a surviving current owner legitimately
  retains them.

### Close/failure cleanup

- open failure after partial binding leaves no leaked `_BINDINGS`;
- context-manager exit closes the store/prefix;
- double close is harmless;
- close with unsaved dirty state performs no write/generation advance;
- cold `save()` refusal leaves dirty state and generation unchanged;
- legacy session save regression remains green;
- direct store close makes disk-backed history access fail rather than reopen.

## 11. Scaling evidence

Use 4, 40 and 400 committed cold segments with the SAME resident suffix/current
graph shape.

For each, measure and report:

- cold segment payload reads during open;
- disk EventLog cache occupancy after open;
- count of LOG owners registered in the tracking/identity index;
- total identity occurrence/path counts attributable to event ownership;
- retained pending/tail counts;
- close-time cold segment reads.

Required result:

- **0 cold segment payload reads on open/bind**
- **0 cold segment payload reads on close**
- disk cache remains empty on untouched history
- LOG owner count depends on mutable tail only, not H
- identity bookkeeping for event history does not grow with 4 -> 40 -> 400
  committed segments

Also repeat a local current alias mutation at 100, 300 and 1,000 unrelated alias
groups and retain the accepted affected-owner scaling behavior. This is a
regression check, not a new optimizer.

Do not claim bounded total World memory. Report the event/history-specific
structures only.

## 12. Validation and delivery

During development run focused open/bind + accepted identity/EventLog/cold tests.

Then run the affected persistence suite:

```sh
PYTHONPATH=.:simulation python -m pytest -q \
  simulation/tests/test_incremental_store.py \
  simulation/tests/test_persistence*.py \
  simulation/tests/test_cold_history.py \
  simulation/tests/test_event_year_queries.py \
  simulation/tests/test_canonical_digest.py \
  simulation/tests/test_history_archive.py
```

Then run one full suite:

```sh
PYTHONPATH=.:simulation python -m pytest -q simulation/tests
```

No millennium/endurance/canonical long-history run.

If isolated candidate CI is needed, use a temporary workflow only on the
candidate branch, prove exact product/test blob equality on landing, and do NOT
land the workflow.

Record actual commands/results and the 4/40/400 measurements in a new
`simulation/PERSISTENCE_P3B_LIVE_OPEN_VALIDATION.md`.

Commit only this bounded implementation/tests/validation to
`sim/stage-0-5-stabilization` with `[skip ci]`, report the exact landed head,
and STOP for Astra review.

Do not proceed automatically to cold save, acknowledgement recovery, detach,
checkpoint integration, P4, Stage 1, millennium runs or PR merge.
