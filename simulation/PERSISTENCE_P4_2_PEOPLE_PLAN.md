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


## Hybrid non-people/EventLog integration subgate

After the green people-write gate, the next slice reuses the accepted P3B
tracking/cold-save machinery for every still-eager root while explicitly
excluding `world.people` from its root/memo/identity bootstrap.

Narrow supporting changes:
- `persistence_tracking.IncrementalWorldSession` gains an internal
  `_excluded_namespaces` set honored by root binding, identity-owner bootstrap
  and persisted-key capture. Default is empty, so ordinary P2/P3 behavior is
  unchanged.
- `persistence_session._capture_cold_baseline_ordinals` accepts an optional
  excluded set; default behavior is unchanged.
- `persistence_events.prepare_sealed_append` accepts the same checked-store
  interface already accepted by `SealedEventPrefix`.
- `persistence_cold_save.prepare_cold_save` accepts optional `force` and
  explicit `token`; defaults preserve P3B behavior. Forced planning is used
  when the only effective mutation is in lazy people.

One hybrid generation:
1. freeze the lazy people overlay into `VersionChange` and
   `IdentityOccurrenceChange`;
2. freeze the P3B eager/EventLog journal with the same target generation/token;
3. merge structural `world.people` layout into the cold plan when necessary;
4. adjust the cold plan's expected namespace counts for lazy people;
5. publish lazy versions, occurrence labels, ordinary P3B records, event
   descriptors/segments and the head in one `LazyRecordStore.commit`;
6. validate lazy touched-owner evidence plus the existing cold successor
   evidence;
7. run the accepted cold runtime prefix/journal publisher, then accept the lazy
   people overlay and moved GenerationPin.

Cross-boundary identity:
- people-only shared incarnations are restored lazily by persisted incarnation
  labels;
- a P2C link crossing `world.people` and an eager owner seeds the lazy
  incarnation registry from the already-resident eager object without decoding
  the Person row;
- until owner-transfer mutation across that boundary has its own proof, a
  mutation that would rewrite a cross-boundary identity group fails closed
  rather than silently splitting or rebinding it.

Focused proofs:
- one short `Simulation.step()` can mutate people, eager roots and EventLog and
  save/reopen to the same canonical digest as an independent eager control;
- D/F/N transfer remains at most four sealed chunks and disk history is not
  materialized;
- people-only and eager-only saves share the same commit/recovery machinery;
- lost acknowledgement, precommit failure and stale competitor preserve
  old-or-new atomicity across both authorities;
- ordinary open remains zero-Person-payload and clean people cache remains <=256;
- existing P3B/P4.1/P4.2 focused regressions stay green.


## Post-hybrid continuation subgate

After the hybrid affected gate passes, prove that the accepted composition is not
only reopenable but can continue independently across a save/close/reopen
boundary before moving on to owner-transfer and detach work.

Focused proof:
- create independent eager control and source worlds from the same seed;
- normalize only the already-documented generated-world event_ids fixture;
- advance eager control two real Simulation steps;
- advance lazy session one real step, save, close and reopen;
- require the reopened first-step digest, IDs, people order and event sequence to
  match the eager control at the same point;
- advance the reopened lazy session a second real step, require exact digest and
  event identity/order/year/cause/value equality with the two-step eager control,
  save, close and reopen again;
- ordinary reopen remains bounded and does not silently replace the lazy people
  authority with an eager materialization.

This is a lifecycle proof only. Do not add gameplay/balance changes or broaden
the persistence authority model. Once green, proceed to the remaining
owner-transfer/provenance/invalidation and explicit materializing-detach work.


## Materializing lazy detach subgate

Implement explicit `LazyWorldSession.detach(materialize_history=True)` only.
The default/no-argument call must fail without side effects. Detach is an
explicit O(total) portability operation and therefore may materialize all
current people and all cold EventLog history; ordinary open/save/gameplay must
remain bounded.

Detach staging requirements:
- materialize the complete logical `world.people` mapping from the captured
  generation plus local overlays, not merely the resident cache;
- preserve exact people order, current live Person objects/incarnations and
  any already-restored cross-boundary aliases;
- reuse the accepted cold EventLog materialization and eager-wrapper staging;
- stage every replacement before publication;
- a staging failure leaves the lazy session usable and its pin intact;
- active or stale sessions may detach local current state, but
  recovery-required sessions may not guess;
- stale detach never publishes local state to the winner's store;
- publish removes persistence lifetime/binding machinery, releases the
  GenerationPin, closes the backing store and returns the same World object as
  a portable in-memory graph;
- detached people use a normal `RecordTable` and detached history has no disk
  prefix; checkpoint roundtrip and further standalone mutation must work.

Focused proofs cover >256 people, retained aliases, unsaved people/eager edits,
cross-boundary sharing, staging failure, stale-local detach and portability.


## Cross-boundary shared-Person field-edit subgate

Before owner-transfer topology is enabled, permit the narrower sound case where
one Person incarnation is shared between `world.people` and an eager owner and
only a declared immutable-valued Person field is edited.

Requirements:
- the eager owner binding and LazyRecordTable both observe the same live Person;
- one field edit journals both authorities and publishes them in one hybrid
  generation;
- reopen restores the exact cross-boundary alias and edited value;
- declared Person fields may pass only when the assigned value is recursively
  immutable, so this subgate cannot introduce new mutable identity topology;
- eager container replacement/removal/reparenting remains fail-closed until the
  separate owner-transfer proof lands;
- ordinary non-cross-boundary behavior is unchanged.

Focused proof edits the shared Person through the lazy/eager alias, verifies
both journals, rejects an attempted eager-container alias move before mutation,
saves, closes/reopens and checks identity plus value equality.


## Cross-boundary owner-transfer subgate

This supersedes the earlier temporary fail-closed topology restriction after the
shared-Person field-edit proof is green.

Implementation contract:
- seed persisted cross-boundary current links into the hybrid eager tracker's
  current-link baseline without adding people owners to its eager occurrence
  index;
- after only dirtied eager owners are refreshed, reconcile each live/previously
  shared Person group from the lazy people occurrence(s) plus the eager
  occurrence index's current paths;
- generate the same canonical anchor/link form as P2C over the combined group;
- reconcile only affected/live groups and prior cross links, never scan cold
  people history;
- current link additions/removals ride the existing cold current-link journal
  and therefore publish atomically with lazy Person versions, eager owners,
  EventLog state, counters and head;
- alias deletion, creation, replacement and remove-then-add owner transfer must
  preserve one live Person instance and exact reopen topology;
- existing eager sharing restrictions still reject unsupported simultaneous
  ownership patterns/cycles rather than weakening P2C rules;
- Person field values shared across the boundary remain restricted to declared
  recursively immutable assignments until nested-Person identity versioning has
  its own proof.

Focused proofs: create a new cross-boundary alias from a loaded lazy Person;
replace one eager owner's shared Person with another Person; move the same Person
between eager owners; edit the old Person in the same generation; save/reopen
and verify exact object identity/value topology.


## Measured family expansion — magic aspirations pilot

Residual measurement on product head `008d5ebf2af1e1ff1fd0929b506df2c260ef3218`
(run 37386442258) proved ordinary lazy-world open still scales directly with
magic-resource history:
- 1,000 resources + aspirations + owner-index rows: 6,033 payload reads,
  2,155,371 payload bytes;
- 10,000 rows in each family: 60,033 payload reads, 21,523,384 bytes;
- Person payload loads remained zero.

The first bounded migration within this measured family is
`world.magic_resources.aspirations` because each `MagicAspiration` is a
scalar-only mutable record. This establishes a second lazy namespace without
introducing resource transfer-list or owner-index semantics in the same step.

Contract:
- conversion moves aspiration rows from ordinary P1 records into versioned lazy
  rows with exact stable dict order and existing incarnation labels;
- ordinary open materializes zero aspiration payloads;
- point read materializes exactly one aspiration and binds its persisted
  incarnation;
- clean cache is bounded at 256; retained aliases survive eviction;
- scalar field mutation, insert/delete/replacement and delete/reinsert use the
  same generation/pin/atomic-save machinery as people;
- no-op save writes no aspiration payload;
- eager P3B tracker excludes this namespace entirely;
- collection layout and head counts publish atomically with people/eager state;
- explicit detach materializes the complete aspiration mapping into a normal
  dictionary before teardown;
- current cross-boundary identity machinery is generalized from a people-only
  boundary to the declared lazy namespaces so aspiration sharing, if present,
  is restored/reconciled rather than silently dropped.

After this pilot is green, migrate `magic_resources.resources` and replace the
redundant eager `owner_index` with checked lazy owner memberships/query
adapters while preserving exact inventory ordering and transfer/consume
behavior.


## Measured family expansion — magic resources subgate

After the aspiration pilot gate passes, migrate
`world.magic_resources.resources` into the same versioned lazy store.

Resource-specific contract:
- `MagicResource` remains live/mutable and index-notifiable only while bound;
- the nested `transfers` list remains arbitrarily mutable through a bounded
  notifying list adapter; retained child aliases after parent cache eviction
  must still dirty/reload the canonical resource;
- conversion preserves top-level and nested transfer-list incarnation labels;
- lazy memberships index only currently available ownership:
  `owner=(owner_kind, owner_id)` and `owner_kind=owner_kind`;
- point reads decode one requested resource/group; clean cache B=256;
- transfer/consume/create preserve exact values, ordering and owner-query results;
- unsaved owner/consumption changes are reflected in query overlays;
- save publishes resource payload, memberships, nested incarnation labels,
  aspirations, people, eager roots, EventLog and head atomically;
- no-op resource saves write no resource payload;
- explicit detach materializes all resources and plain transfer lists while
  preserving supported current sharing.

The existing canonical `owner_index` remains exact during this subgate. Once
resource membership/query behavior is green, replace its eager open cost with a
checked lazy adapter and prove differential equality before removing eager
materialization.


## Measured family expansion — lazy magic-resource owner index

Post-resource measurement on product head
`fa3b6481e98f4fd91058d5318bdaa3ed727a4876`
(run 37388835042) proves the remaining eager owner index dominates ordinary
open for this family:
- 1,000 resources/owners: 2,033 payload reads, 114,239 payload bytes;
- 10,000 resources/owners: 20,033 payload reads, 1,032,248 payload bytes;
- resource payload loads = 0 and aspiration payload loads = 0 in both cases.

Migrate `world.magic_resources.owner_index` into a bounded lazy mapping rather
than leaving a stale compatibility copy or teaching gameplay about persistence.

Contract:
- conversion migrates every owner-index bucket into versioned lazy rows with
  exact current key order and persisted top-level set incarnation;
- ordinary open decodes zero owner-index payloads;
- key iteration uses lazy collection order metadata and does not decode bucket
  payloads;
- point get/setdefault loads only the addressed bucket;
- loaded buckets are weakly bound notifying set wrappers; retained bucket aliases
  after cache eviction rehydrate the canonical owner row and remain authoritative;
- add/discard/remove/pop/clear/update mutate exactly as normal sets and dirty only
  the corresponding owner row;
- resource transfer/create/consume behavior and existing MagicResourceState API
  remain unchanged;
- owner-index changes, resource memberships/payloads, aspirations, people,
  eager roots, EventLog and head publish in one generation/token;
- exact differential proofs require each current owner bucket to equal
  `set(resources.owner_ids(*owner))` before save and after reopen;
- no-op save writes no owner-index payload;
- explicit detach materializes a normal dict of normal sets;
- eager tracker and ordinary open exclude the owner-index namespace only after
  the lazy adapter is installed.

After this gate, rerun the 1k/10k residual measurement. The owner-index migration
passes only if ordinary open no longer scales with owner-index payload count.
