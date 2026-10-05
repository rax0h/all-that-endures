# P4.2 — people lazy pilot / session integration plan

**Authority:** `simulation/STAGE_0_5_SOL_EXECUTION_HANDOFF.md`.
**Identity prerequisite:** runtime + storage focused gate
`37347927599` — **86 passed in 11.58 s** on product head
`654cd7883f917e970f4dc9f63ab19929c36bcec9`.

This slice is opt-in and additive. P3B remains the accepted legacy/cold session
path and ordinary checkpoint defaults remain unchanged.

## Exact files and APIs

New:
- `simulation/ate_sim/persistence_lazy.py`
- `simulation/tests/test_persistence_lazy_people.py`
- `simulation/tests/test_persistence_lazy_conversion.py`

Narrow supporting edits:
- `simulation/ate_sim/record_index.py`: one inert optional preflight callback
  before an `IndexedRecord` assignment; ordinary `RecordTable` behavior is
  unchanged when the callback is absent. This is required so stale lazy-session
  mutation rejects before changing a Person.
- `simulation/ate_sim/persistence_lazy_store.py`:
  checked ordinary-record compatibility reads, checked head object access and
  namespace-size/key-existence primitives only.
- `simulation/ate_sim/persistence_tracking.py` only when the lazy session
  needs already-reviewed mutation hook classes; no P3B semantic change.
- `simulation/ate_sim/core.py` only if a query-adapter plumbing change is
  proven necessary. The preferred path is no core change because
  `current_people()` already uses `RecordTable.select()`.

Public opt-in entry points:
- `convert_cold_to_lazy(source, destination, *, rules_id)`
- `open_lazy_world_session(path, *, rules_id)`
- `LazyWorldSession.world`, `.save()`, `.resolve_save()`, `.detach()`,
  `.close()` as lifecycle work lands.
- `LazyRecordTable` for `world.people`.

## Conversion contract

Input is a checked P3B cold/current-links store. Destination is a new P4 format
3 store. Source is never modified.

Conversion is explicit O(total) and publishes by private-file no-overwrite
publication. It may reconstruct the full current non-event graph once for
identity/incarnation labeling, but it must not materialize all disk EventLog
segments at once. P1 records and immutable segments are copied/validated as
streaming/batched rows.

Destination authority:
- `world.people` rows become lazy record versions, with exact stable dictionary
  order and an `alive` membership row per person.
- all other P3B current records remain ordinary P1 rows initially;
- current P2C identity-link records remain authoritative ordinary records;
- occurrence/incarnation labels and allocator state are P4 identity metadata;
- P3B sealed EventLog segment/descriptors/tail authority is preserved exactly;
- head metadata/counters/generation are preserved; format/store identity changes.

The lazy people payload is the Person value itself, not the P2 envelope. Order
moves into `lazy_order_versions`. Conversion validates source envelope ordinals
and preserves them exactly; it must not infer order from SQL row order.

## LazyRecordTable contract

`LazyRecordTable` subclasses `RecordTable` so existing `indexed()`,
`current_people()`, `ids()` and `select()` call sites remain valid.

Required behavior:
- `len`: checked lazy namespace state; no Person decode.
- iteration/keys: P4 page iterator; <=128 temporary keys.
- point get: exactly one checked Person payload for a nonshared top-level record
  plus only identity metadata actually required.
- `alive` query: store membership lookup + unsaved overlay; decode only returned
  Person/group payloads.
- dictionary insertion order and delete/reinsert behavior exactly match eager
  RecordTable.
- clean cache capacity B=256 groups. Dirty/current/external pins are separate
  and observable.
- cache eviction may drop clean unpinned objects only.
- loaded Person mutation updates the local overlay and dirty owner.
- retained old alias after replacement/deletion is detached and never rebound.
- same object moved/reinserted preserves incarnation.

Underlying `dict` storage is cache only, never archive authority. Any inherited
method that would inspect only the cache must be overridden.

## Identity binding

P2C current links remain sharing authority. Conversion labels mutable
occurrences with stable incarnation IDs. On load:
- persisted occurrence labels seed `LazyIdentityRegistry`;
- one live object per incarnation in the session;
- loaded descendants are rebound according to checked P2C links and occurrence
  labels at the same GenerationPin;
- retained child aliases carry current owner/group pin information sufficient
  to dirty the real canonical owner;
- externally retained groups may remain pinned as a correctness-first policy;
  pin count/bytes are measured.

No global strong `_memo` or archive-wide binding table is permitted for the
lazy people family.

## Open contract

`open_lazy_world_session`:
1. opens P4 store and captures one durable GenerationPin;
2. restores the checked cold manifest, roots and all non-people collections;
3. constructs EventLog with disk prefix/tail authority without full history load;
4. installs `LazyRecordTable` for `world.people`;
5. restores/validates current identity only for loaded/currently required groups;
6. validates head metadata vs World scalars;
7. ordinary open loads **zero Person payloads**.

Initial read-only/open gate lands before save. Save/lifecycle is a separate
implementation step in the same handoff and may proceed automatically once the
open/query gate is green.

## Open/query proof gate

- explicit source-preserving P3B->P4 conversion;
- exact source vs destination head metadata, event descriptors/segments, current
  identity links and non-people rows;
- destination people order/values match source control when explicitly iterated;
- ordinary open decodes zero Person payloads;
- point read decodes one Person payload;
- first/warm `alive=True` query returns exact eager control IDs/order;
- 1k/10k inactive growth with fixed active A: returned Person decodes <=A,
  membership SQL work scales with A/overlay rather than H;
- delete/reinsert order;
- no hidden `dict(...)`, tuple(all keys), full digest or archive traversal.

## Save/lifecycle follow-on

After the open/query gate, implement mutation tracking, dirty/current/external
pins, stale guard, atomic owner/query/identity/EventLog publication, lost-ack
resolution, close/detach and short independent continuation. Do not weaken P3B
D/F/N authority or stale-state semantics.

## Gate discipline

Run focused conversion/open/query tests plus P4.1/P4.2 storage regressions.
Do not run a full suite until the integrated save/lifecycle product bytes
stabilize. No millennium/endurance, balance, default-checkpoint, Stage 1 or merge.


## People write subgate

This subgate enables only the already-migrated `world.people` family. It does
not yet enable `Simulation.step()`, EventLog mutation or non-people root
mutation.

Implementation:
- `LazyRecordTable.changed()` records loaded Person field edits and keeps dirty
  entries resident.
- table insert/delete/replacement are local overlays over the captured pin;
  inherited dict storage remains cache only.
- structural insertion order is allocated from the checked namespace
  `next_ordinal`; existing updates preserve ordinal; delete+reinsert receives a
  new ordinal.
- top-level Person incarnation is the authoritative occurrence for this family:
  same live object remove/reinsert preserves its incarnation; distinct
  replacement gets a new one; retained old aliases are detached.
- save emits only effective `VersionChange` /
  `IdentityOccurrenceChange` rows and the checked World head metadata.
- redundant field assignment or a structural sequence whose final state equals
  the captured baseline is a true no-op where possible; no lifetime attempt log.
- save conflict marks the session stale and retains local overlays; after stale
  detection further people mutation/save is rejected.
- lost/ambiguous acknowledgement keeps the exact token and frozen change plan;
  `resolve_save()` delegates to `LazyRecordStore.resolve_commit()`.
  Committed resolution advances the pin and clears only the plan's dirty state;
  not-committed resolution returns to active with edits retained; conflict marks
  stale.
- close releases the current pin only when no unresolved acknowledgement exists.

Focused proofs:
1. one Person scalar edit writes one payload and reopens exactly;
2. no-op save writes zero payloads and does not advance;
3. insert/delete/replacement and delete+reinsert preserve exact order/query
   membership and incarnation rules;
4. retained replaced alias remains detached and cannot dirty the replacement;
5. fixed-H local edit does not decode or rewrite unrelated people;
6. failed publication leaves old complete state and edits retryable;
7. lost acknowledgement resolves committed exactly once;
8. competing writer causes stale state; local edits remain inspectable but
   further bound mutation/save is rejected;
9. save/reopen `current_people()` matches an eager control.

Only after this subgate passes do EventLog/non-people tracking and
materializing detach become eligible.
