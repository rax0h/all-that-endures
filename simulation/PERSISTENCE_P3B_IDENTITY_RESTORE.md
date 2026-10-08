# P3B next bounded assignment: cold-safe identity restoration

Status: implemented; see `PERSISTENCE_P3B_IDENTITY_RESTORE_REVIEW.md` for the
review correction and acceptance. Next assignment: `PERSISTENCE_P3B_COLD_CAPTURE.md`.
This specification follows accepted identity primitives at
`b756023395a3acb2aa0bfae9326e76dc6f10cd4e`. Read
`PERSISTENCE_P3B_IDENTITY_REVIEW.md` and section 5 of `PERSISTENCE_P3B.md`.
Verify the live PR/head before editing; the acceptance/specification commit is
the intended continuation of this baseline.

## Goal and allowed scope

Make existing identity path resolution, restoration and graph verification
usable on an already-constructed World with a composite EventLog, without
reading sealed history. This prepares cold restore; it does not implement the
World/session loader or expose a new public persistence API.

Allowed product files: `ate_sim/persistence_adapters.py`,
`ate_sim/event_log.py`, and only a necessary shared helper in
`ate_sim/persistence_identity.py`. Add
`tests/test_persistence_cold_identity_restore.py` and a concise
`PERSISTENCE_P3B_IDENTITY_RESTORE_VALIDATION.md`.

Extend the existing internal helpers with an explicit keyword mode (suggested
`mutable_event_tail_only=False`): `_at_path`, `_restore_identity`,
`_complete_identity_groups`, and `_verify_identity_graph`. Factor shared logic
where useful; do not copy an independent restore subsystem. Keep default
behavior compatible with accepted P2/legacy callers. Default-mode helpers must
reject a disk-backed EventLog before descending into its history.

Do not change manifest/storage formats, codecs, `read_snapshot`,
`write_snapshot`, `bind_snapshot`, baseline audits or current session APIs in
this slice. Do not implement cold creation/open, binding retirement, save plans,
acknowledgement recovery, detach, checkpoint/export integration or engine guards.
The existing legacy `_audit` continues to reject cold input; do not relax it.

## 1. Resolve paths without accessing excluded history

Cold-mode path resolution must recognize an EventLog wherever it is reached,
including through an alias under a current object. For an `index` component:

* Require a canonical integer absolute index; reject bool, negative, malformed
  and out-of-range indices using the existing format/integrity error families.
* Compute F = disk count + pending chunk count * 2,048 from existing metadata.
  Reject indices below F BEFORE calling logical `__getitem__`, decoding a chunk,
  or reading a segment. Pending history is excluded even before disk transfer.
* Access the resident tail directly at index - F. Reject an individually sealed
  tail Event before resolving the Event or any of its descendant fields.
* Check borrowed-backend lifetime. Resolving an EventLog root also checks its
  availability; a cached/tail-only operation does not make a closed log usable.
* Preserve existing canonical field/key/index validation for all other values.
  An Event reached independently through a non-log current field keeps the
  existing identity semantics even if it is sealed. Do not reject such a path
  merely because a sealed log value represents the same historical Event.

Resolving one tail index is O(1) in history size. Do not build a per-event or
per-year map, enumerate the log, or scan the mutable tail to find the index.

## 2. Verify the same projected identity graph

Cold `_complete_identity_groups` and `_verify_identity_graph` must use the
accepted mutable-tail enumeration boundary for every encountered EventLog.
Preserve log-root occurrences, eligible tail aliases, nested shared parents and
descendants, and current non-log occurrences. Use the same immutable-container
boundary as the accepted cold occurrence index; do not independently redefine
which occurrences are current.

Preserve cycle rejection and the existing rule that every alias must be
explained by an explicit link or an ancestor link. Validate explicit endpoints
with the cold path resolver before graph traversal. Missing/excluded endpoints,
unexplained sharing and contradictory links remain errors, not rows to discard.

This is explicit bootstrap/restore verification: O(current projected graph) is
allowed. Cold prefix and pending sealed history contribute zero payload reads,
zero decodes and zero retained occurrences. This is not a per-save full-graph
verification policy.

## 3. Restore aliases through mutable EventLog tail entries

Add one narrow private EventLog tail-relink method for adapter restoration.
It must keep the existing EventLog object and all storage/count/year boundaries.

The method checks lifetime, absolute integer index, membership in the mutable
tail, exact Event type, unsealed source/target, ID == index + 1 and unchanged
year before replacing that one `_tail` reference. No assignment into disk or
pending history, no re-sealing, no append, no year-index rebuilding, no reader
replacement and no public sequence mutation API. Use a local import if needed
to avoid the existing Event/EventLog module dependency cycle.

Before calling it, the adapter must validate every link's source, destination
and supported assignment boundary and compare every payload copy using the
accepted typed codec with recorded identity enabled. Python equality is not a
substitute: bool/int/float distinctions, signed zero and NaN bits must survive.
Do these checks for the entire batch before applying any assignment. A late
invalid sealed-history path or unsupported target must not leave earlier
targets relinked. Preserve duplicate-target and incompatible-copy rejection.

Then reuse the accepted ancestor-before-descendant application order and
re-resolve owners after ancestor assignments. Use the private relink method
only for an EventLog index target in explicit cold mode. Ordinary record/dict/
list target restoration retains its accepted semantics.

EventLog is not newly permitted as a serialized nested payload. If a whole-log
endpoint appears in a synthetic/current alias graph, only the same existing
EventLog object may satisfy it without a value comparison; reject distinct log
objects clearly instead of encoding or enumerating their histories. Do not add
a codec for EventLog or claim on-disk support for new root-alias shapes.

All operations are internal, quiescent and unbound. Concurrent mutation and
in-place relinking of a live tracking-bound World are outside this assignment.

## 4. Required tests and measurable evidence

Use real P1/P3A stores with synthetic history plus small independently assembled
Worlds. Do not run a long simulation. Include:

1. Cold index lookup and projected verification at 4 and 40 disk segments with
   the same pending chunks/tail: zero checked segment payload reads, zero
   pending decodes and identical projected occurrence counts. Make forbidden
   logical EventLog traversal fail loudly. A tail lookup must not enumerate the
   tail. Include root-log alias traversal in a supported synthetic current graph.
2. Reject endpoints inside disk history, pending chunks and individually sealed
   tail Events, including descendant paths and paths through aliases. Verify
   no history I/O and no target mutation. Check malformed, negative, bool and
   out-of-range indices and closed reader/store before any relink.
3. Restore a shared mutable tail payload and nested child shared with current
   World state. Exercise parent plus descendant links and both link directions.
   Check exact Python `is` relationships and projected verification afterward.
4. Restore a whole mutable Event tail entry shared with an independent non-log
   current occurrence, exercising the new private tail-relink path. Check stable
   log identity, IDs, years, ordering, counters, pending bytes and prefix reader.
   Reject different Event types/IDs/years and sealed replacement Events.
5. Preserve sharing between sealed Event occurrences outside the log, while
   continuing to reject an endpoint obtained by descending into sealed history.
6. Exact typed copy checks: matching NaN payloads succeed; unequal NaN payload
   bits, bool/int, int/float and positive/negative zero mismatches fail before
   mutation. Do not change the accepted codec to make these tests pass.
7. Place a bad endpoint or unsupported assignment boundary after a valid link
   and prove the complete batch leaves its original object identities intact.
   Keep cycle, conflicting target and unexplained alias rejection intact.
8. Verify a distinct whole-log endpoint is rejected without history reads; an
   already-shared root does not cause full-history value comparison.
9. Keep the accepted legacy identity, P3B identity and EventLog suites passing.

Report actual read/decode counts and projected graph sizes. No end-to-end cold
World restore/continuation, session atomicity or total resident-memory claim is
earned by this helper-level slice.

## Delivery

Implement only this specification. Run focused tests during development, the
affected persistence/EventLog tests, then one full `simulation/tests` suite on
stable final code. If using an isolated CI candidate, prove landed product/test
blob equality. Commit to PR #14's existing branch with `[skip ci]`; do not modify
workflows or invoke the ordinary millennium workflow.

Return exact head, files changed, commands/results and measured bounds. Stop
for architect review. No millennium/endurance, balance/magic progression,
Stage 1, default checkpoint replacement, unrelated work or merge. GitHub
authorization for this scoped work is already standing.
