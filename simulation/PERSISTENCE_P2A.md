# P2A — complete World adapters and exact snapshot restoration

Implementation and evidence are now in
[PERSISTENCE_P2A_VALIDATION.md](PERSISTENCE_P2A_VALIDATION.md). This specification
remains the review contract; completion of P2A does not authorize P2B.

Assignment for Sol after P1 review. Base implementation:
`0671a9f39d4216a2cd130f177a70e35a5e0af22e`; verify the true PR #14 head first.
The parent contract is [INCREMENTAL_PERSISTENCE.md](INCREMENTAL_PERSISTENCE.md).

## One objective

Prove that a real World can be decomposed into explicit persistence records,
restored exactly, and continue producing the same history. This is the first
part of P2, not permission to implement all remaining persistence stages.

Build opt-in snapshot adapters outside `Simulation.step` and existing checkpoint
entry points. Full bootstrap/restoration can visit all state in P2A; report that
cost honestly. Do not claim incremental saves or bounded resident memory yet.
The point is to establish lossless boundaries before mutation tracking uses them.

## Required implementation

1. An explicit adapter registry covering every canonical World field and every
   reachable canonical record field/type. Field coverage must fail when a new
   unclassified field appears. Do not infer authority from naming prefixes alone
   and do not silently omit default-valued or empty fields.
2. An allowlisted codec/type registry for actual ATE record types and enums,
   using stable versioned type tags. No dynamic imports from save contents.
   Module paths used to invoke tests must not accidentally select the wrong
   class registry; use consistent package imports and test supported entry points.
3. A full snapshot writer into a new/empty P1 store, and a reader that constructs
   a detached World. Use P1 transactions and schema checks. Do not overwrite an
   existing nonempty save as a shortcut. A failed bootstrap must not be reported
   as a usable World save. Never modify the input World or legacy checkpoint.
4. A small documented coverage report listing record boundaries, authoritative
   ordering, special wrappers, reconstructed indexes and excluded caches. Identify
   growing nested collections needing later segmentation; do not invent their
   incremental mutation model in this tranche.

Suggested location: `ate_sim/persistence_adapters.py` and focused adapter tests.
Names are flexible; boundaries and guarantees below are not.

## Concrete representation rules

* Split identity-bearing dictionaries into per-key records: people, households,
  paths, wallets, treasuries, resources, lots, relationships, memberships,
  institutions, notices and the other existing collections. A World pickle,
  `__dict__` dump, or single huge JSON/blob of a subsystem is not an adapter.
* Store nested bounded ability/understanding state with its owning person path.
  Preserve every ability field and array position. Unbounded nested membership
  and transfer histories need an explicit representation and later segmentation
  classification; full P2A snapshots may encode these collections in full.
* Preserve typed dictionary keys and insertion order. SQL primary-key order and
  canonical digest order are not necessarily simulation iteration order. Use an
  authoritative ordinal in the checksummed entry envelope where needed, plus
  explicit collection metadata for empty collections and collection kinds.
  Do not let unprotected, rebuildable query-membership rows be the sole authority
  for canonical ordering. Detect duplicate/missing ordinals when reading.
* Preserve all canonical index fields initially, including `owner_index`,
  `active_lot_index`, `lot_index`, genealogy maps, adjacency and `event_ids`.
  Exact reconstruction is allowed only with direct equality tests covering order
  where meaningful. Do not optimize these fields away during the adapter pass.
* `RecordTable` is a wrapper over authoritative rows plus disposable query state.
  Restore its notifications/rebuild behavior deliberately. Do not encode weak
  references or obsolete index buckets. Prove later direct edits query correctly.
* Handle EventLog explicitly. Preserve all logical events, IDs, year order,
  current tail and sealed-event immutability. An in-memory reconstructed EventLog
  is sufficient for P2A; disk-backed event reads are P3. Stream event-sized records
  or bounded batches through the codec, never expand all events into one payload.
* P1 intentionally rejects FrozenList/FrozenDict. Add explicit allowlisted
  adapter representations preserving their frozen semantics; never loosen P1
  back to generic subclass flattening. Test nested frozen data and current mutable
  event data separately. `Event._sealed` is noncanonical but behaviorally relevant:
  restore it intentionally, not by guessing that all old-looking events are sealed.
* Preserve the existing retained `agency.actions` tail exactly. Do not infer
  omitted older actions or add new history retention policy.
* Derived caches such as `_query_offer_books`, inventory tuples, relationship
  references, rank caches and material selection structures may be omitted only
  with exact reconstruction/continuation evidence. Canonical dataclass fields
  alone are not proof that every non-field attribute is irrelevant to behavior.
* Do not rerun creation hooks, essence absorption, births, resource discoveries or
  RNG to reconstruct stored objects. Use restored data and tested cache rebuilds.

## Ownership and consistency

The restored world must be independent of the source world. Editing its wallet,
path or relationship cannot mutate the source. Within the restored world, each
authoritative identity must have a single mutable object; runtime caches must
refer to it. Cross-record semantic links remain the same stable IDs.

Audit shared mutable children across canonical record roots. Preserve genuine
sharing with an explicit identity representation or stop with a measured example
requiring an architectural decision. Do not blindly deepcopy each root and claim
equivalence, and do not weaken P1's explicit rejection of unsupported sharing.
Duplicating immutable value objects is acceptable when identity has no behavior.

Snapshot reading must observe one committed generation. P1 exposes individual
reads, not a pinned multi-read World snapshot. Use a bounded-lifetime SQLite read
transaction for the full restore/scrub, or provide an equivalent explicit session;
do not read a head and then accidentally mix records from a later commit. No
background writer is needed. Test the chosen consistency behavior. Release read
transactions promptly after full restoration.

If narrowly necessary, add typed enumeration/read-metadata methods to P1 instead
of scattering raw SQL across adapters. Preserve checksums, stored record schema
checks and diagnostics. Unknown World adapter versions, missing collection roots,
unknown fields/types, missing rows and incompatible rules must fail explicitly.
A load with missing mandatory fields must not silently call World defaults.

## Cheap, high-value acceptance tests

* Coverage against actual dataclass fields/types, plus a fixture introducing an
  unclassified field/type that is rejected. Test empty collections and defaults.
* Founder and mature worlds after short real histories. Include a cold-history
  fixture with several thousand events; it need not simulate thousands of years.
* Compare original, legacy checkpoint restore and P2A restore using unchanged
  `World.digest()` and direct type/order/field assertions. Check frozen versus
  mutable event payload behavior in addition to the digest.
* Continue each restored/control world for a short identical history and compare
  exact final digests. Warm Society offers, relationship caches, material selection
  and current-state indexes before the snapshot. Use existing fixture helpers.
* Export one small restored/control history archive and compare its logical digest
  and linked person/resource/event chains. Do not use archive export as save input.
* Test detached mutable identity, stable IDs/counters, namespace/record-schema
  failures, snapshot read consistency, and mutation after restored index rebuilding.
* Measure bootstrap/read seconds, encoded bytes and record/event counts on the
  short fixture. Label them full-snapshot costs; no speedup claim is required.

Run targeted adapter tests first, then the full existing unit suite once. Reuse
the suite's deterministic histories instead of launching a redundant millennium.
Do not refresh any golden digest. If field-exact restore changes a later outcome,
investigate iteration order, aliasing, hidden state and cache rebuild behavior.

## Stop point and report

Commit tested P2A code on PR #14 and stop for Astra review. Report exact commit,
files, field coverage, tests, before/after/continued digests, short snapshot costs
and any unsupported state. The full report must distinguish P2A full bootstrap
from later incremental saves.

No automatic dirty tracking, live mutation binding, lazy record eviction,
EventLog disk backing, default checkpoint replacement, simulation rule changes,
balance tuning, Stage 1 work, millennium or merge. P2B will bind mutation ownership
only after these record and reconstruction boundaries are proven.
