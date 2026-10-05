# P4.1 validation and P4.2 identity-design addendum

**Implementation baseline:** `953240816b6d332aa95e65a26b463b10a4b58ef4`  
**Stable P4.1 code candidate:** `c3f3525d7ddf3b2afdf39946a6fa9add9dd98225`  
**Focused gate:** Actions run `37307695625` — **56 passed in 5.10 s**.  
**Full simulation/tests gate:** Actions run `37307789377` — **674 passed in 1737.93 s (28:57)** against the exact stable code candidate above.

## Scope landed

P4.1 is an explicit opt-in persistence format 3 implemented in
`simulation/ate_sim/persistence_lazy_store.py`. Existing format-2
`incremental_store.py`, P2/P3 adapters, World/session behavior, EventLog,
normal checkpoint defaults and gameplay systems were not changed.

The P4 facade provides:

- `LazyRecordStore.create/open`;
- immutable checked `GenerationPin` capture/release;
- `read_version`, keyset-paged `iter_keys`, and indexed `query_keys`;
- typed `VersionChange` including explicit reinsertion;
- atomic combined commit of lazy versions, ordinary P1 changes, immutable
  segments, metadata/head, the writer pin and its latest receipt;
- `resolve_commit` for explicit interrupted-acknowledgement recovery;
- full scrub, diagnostics/query-plan evidence, exact backup and
  source-preserving `copy_current_head`.

Unknown/crossed format modes reject before cold-payload traversal. Format 2
keeps its accepted behavior.

## Versioned authority and checked visibility

Lazy records, collection order, generic query memberships and per-namespace
state use half-open validity intervals `from <= G < to`; a NULL upper bound
is current. Payload and metadata checksums frame row kind, namespace, typed
identity/index value, schema/codec, ordinal where applicable, validity interval,
declared complete memberships and payload.

Ordinary reads validate every row they consume but do not claim to scrub the
archive. `verify_all()` separately verifies SQLite/FK integrity, head/pins/
receipts, P1 rows/segments, every retained lazy generation, exact owner/order/
query completeness, namespace counts, interval/checksum invariants and retained
expiry bounds. Deleting a required order/query row is therefore detectable even
when every remaining row still has a valid checksum.

Collection assignment preserves ordinal. Deletion closes membership. Explicit
reinsertion receives a new ordinal. Empty namespaces remain distinguishable
from missing required owners. Key iteration uses bounded keyset pages capped at
128, never repeated OFFSET traversal.

Before update/delete, the current owner projection is checked against its
stored complete membership declaration. A write cannot silently heal a damaged
order/query projection.

## Atomic pins, publication and acknowledgement

`capture_pin()` checks the current head and inserts the durable pin in one
`BEGIN IMMEDIATE` transaction. Pins are bound to store identity, token and
captured generation. The store has a hard cap of 64 registered pins.

A non-no-op commit validates the expected pin/head while holding the publication
write lock and advances exactly one generation. The same transaction publishes:

1. lazy record/order/query/state intervals;
2. ordinary P1 record changes;
3. immutable segments;
4. checked head metadata/counts;
5. the committing writer's pin moved from G to G+1;
6. one checked latest receipt for that pin;
7. bounded expiry-index cleanup.

There is no second transaction required to make the writer safe. A true no-op
does not advance the generation and writes no receipt/payload.

If an exception is injected after SQLite commit, the facade enters explicit
recovery-required state. Subsequent write/release is blocked until
`resolve_commit` establishes the outcome. The retained per-pin latest receipt
can resolve a committed G+1 after another writer has advanced to G+2; the
resolved result is marked stale and the old durable pin prevents G+3 until it is
explicitly released. Older commit tokens fall outside the one-receipt contract
after a later acknowledged commit.

Process-death tests cover before-transaction, during-publication and after-commit
states and recover only a complete old or complete new generation.

## Two-visible-snapshot retention

At head G, G->G+1 is rejected with `GenerationPressureError` when another pin
requires a generation below G. A pin at G may become the previous visible
snapshot. Releasing it permits the next advance.

The retention floor is the oldest required pin, or the head when there is no
older pin. Only rows whose `valid_to <= floor` are obsolete; unchanged rows are
never reclaimed merely because their creation generation is old. Cleanup is
driven by expiry indexes inside successful publication, not by scanning world
history on no-op saves.

Focused proof: **100 successive single-writer saves** completed without
self-blocking and ended with one live record version, one order version, one
namespace-state version, one pin and one receipt.

## Bounded query/storage evidence

Focused tests populated 1,000 and 10,000 irrelevant owners plus one requested
owner, then queried both current and retained-previous generations.

For the requested `bucket=hot` lookup at both scales:

- exactly one query-membership row was consumed;
- zero payloads were decoded by `query_keys`;
- the returned key set contained only the requested owner;
- a zero-result lookup consumed zero query rows;
- query-plan evidence used the indexed `lazy_query_visible` lookup;
- point `read_version` decoded only the requested payload.

The number of retained owner versions after the one local edit was N+2, as
expected for current plus previous visibility of the changed owner; unrelated
owners were not revised.

Diagnostics separately count payload reads/writes/bytes and metadata, query,
pin and maintenance rows. SQLite physical file shrinkage is not claimed by the
logical-retention bound.

## Backup and explicit orphan recovery

`backup(destination)` is an exact SQLite backup: it preserves store identity,
historical retained versions, pins and receipts and makes no compaction claim.

`copy_current_head(source, destination, ...)` has a different contract. It
opens a consistent source read snapshot, fully verifies that snapshot, copies
only current logical lazy authority plus current ordinary records, immutable
segments and head metadata into a private format-3 staging store, assigns a new
store identity, removes operational pins/receipts/history, fully verifies the
result, and publishes by atomic no-overwrite link/rename semantics.

Tests prove:

- abandoned pins in the source can block normal advancement without damaging
  data;
- the new current-head copy starts with zero pins/receipts and immediately
  restores write availability;
- current values, order/query state, ordinary P1 rows, immutable segments,
  counters and generation are preserved;
- old-only revisions are not copied;
- the original store identity, pins and retained old snapshot remain usable;
- existing destination, injected pre-publication failure and current-row
  corruption fail without a partial final destination.

No timeout, PID guess, clock heuristic or automatic pin deletion is used.

## Focused regression result

Actions run `37307695625` executed the two new P4.1 test modules together with
the accepted P1 `test_incremental_store.py` suite on the real repository:
**56 passed in 5.10 s**.

Coverage includes format isolation, checked current/previous reads, empty and
delete/reinsert semantics, generic versioned identity-link records, corruption
and completeness failures, 128-key paging, no-op behavior, 100-save retention,
generation pressure, 1k/10k indexed queries, pre/post-commit fault injection,
lost acknowledgements, one-latest-receipt semantics, pin capacity/foreign pins,
capture-vs-cleanup race, subprocess death, exact backup and source-preserving
recovery copy.

## P4.2 proposed identity decision — design only

P4.1 deliberately does **not** implement World lazy binding, eviction, a sharing
group registry or object-incarnation semantics. The following is the proposed
binding decision for P4.2 review.

### 1. Stable incarnation identity is distinct from owner placement

Every persistable mutable object incarnation should have an explicit stable
`incarnation_id` scoped by store/world identity. An owner key/path says where
that object is currently reachable; it is not the object's identity. A sharing
group ID is derived metadata/projection, never the authoritative incarnation
identity.

Replacing an object at owner key K creates a new incarnation even when K is
unchanged. Delete followed by reinsertion at K likewise creates a new
incarnation. A retained alias to the old object therefore continues to name the
old incarnation and must never be rebound to the replacement merely because the
owner key was reused.

### 2. Nested retained aliases survive parent eviction without retaining archives

A child that remains live after its parent/owning aggregate is evicted must keep
its own incarnation identity and a generation-consistent binding to the current
authoritative owner/link information needed to persist its mutations. Mutating
that child must dirty the true current logical owner or link row; reloading must
recover the same child identity when the authoritative current link still says
the alias exists.

The registry used to find live incarnations must not strongly retain the World
or cold archive. Entries should be weak where object lifetime permits. Cleanup
must validate the incarnation token, not only Python `id()`, so object-ID reuse
cannot remove or attach a later object accidentally.

P4.2 proof must explicitly retain a child, collect/evict its parent, mutate the
child, save, release/reload and demonstrate correct dirty-owner capture and
identity reconstruction.

### 3. Current links are authoritative; sharing groups are rebuildable projections

P2C current identity links remain the sharing authority. In lazy storage they
should be versioned typed records (for example `world_identity_links`) at the
same captured generation as their owners. Sharing groups are connected-component
or equivalent projections derived from those links and current owners.

A merge or split changes the derived group projection; it does not rewrite
incarnation identity. No group ID derived from "lowest owner occurrence" may be
used as object identity because deletion of that owner or group merge/split
would make it unstable.

Any cached group/order/query acceleration must be checked against the same
GenerationPin and be safely rebuildable from authoritative current links.

### 4. Weak binding cleanup and measured bounds

P4.2 should key live binding state by stable store/world identity plus
`incarnation_id`, with enough generation/owner metadata to reject stale
rebinding. Dead weak entries must disappear without a global archive walk.

A claimed registry bound must report:

- live group/incarnation count;
- group-size distribution/max group size;
- retained bytes, not merely dictionary-entry count;
- number of strong roots retained by binding structures.

There must be no global memo whose values keep every decoded historical object
alive.

### 5. Compatibility must not hide an archive load

Mapping/codec/query compatibility may use generation-safe facades, but operations
on a requested owner/incarnation must load only that owner and the indexed
current-link/group metadata actually required. Iteration remains explicitly
paged. Compatibility helpers may not materialize all owners just to preserve a
legacy Python mapping interface.

P4.1 already provides the storage proof points P4.2 can build on:

- `world_identity_links` works as an ordinary typed versioned namespace;
- current and retained-previous link/owner records can be read from the same
  GenerationPin;
- current-head recovery copies current authoritative links without copying
  old-only history;
- 1k/10k indexed query tests do not decode unrelated owner payloads.

Those facts do **not** prove the P4.2 runtime identity problem. P4.2 still needs
the explicit incarnation model, weak-registry lifetime tests, retained-child
mutation proof, merge/split projection tests and measured resident-state bounds
before the people pilot or eviction work can be accepted.

## Deliberate exclusions / remaining review gates

Not implemented or run in P4.1:

- World/session lazy integration;
- eviction or resident-World memory claims;
- sharing-group registry/object-incarnation runtime;
- automatic conversion or checkpoint-default replacement;
- resource/material migration;
- compact event IDs;
- millennium/endurance;
- balance/magic/gameplay changes;
- Stage 1;
- merge.

The required implementation validation is complete: focused run `37307695625`
passed **56/56 in 5.10 s**, and full `simulation/tests` run `37307789377`
passed **674/674 in 1737.93 s (28:57)** against stable code candidate
`c3f3525d7ddf3b2afdf39946a6fa9add9dd98225`. P4.1 now stops for architect
review; this validation record does not authorize P4.2 implementation or any
excluded work listed above.
