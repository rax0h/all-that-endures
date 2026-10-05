# P4.2 — identity schema and runtime proof slice

**Authority:** `simulation/STAGE_0_5_SOL_EXECUTION_HANDOFF.md`.
**Prerequisite gate:** repaired P4.1 product head
`4fc8cf187aeac82970fc80e5666ce824c33dce1d`, focused run
`37314495881` (68/68) and full run `37326902078` (686/686).

This slice is deliberately proof-first. It defines incarnation identity and
weak runtime binding before any `World`, `world.people`, eviction, conversion,
or session integration.

## Files

- new `simulation/ate_sim/persistence_lazy_identity.py`
- new `simulation/tests/test_persistence_lazy_identity.py`
- `simulation/ate_sim/persistence_lazy_store.py` only for versioned
  occurrence/incarnation storage primitives needed by the proof
- `simulation/tests/test_persistence_lazy_store.py` only for atomic storage
  publication/visibility tests

No `core.py`, gameplay, checkpoint default, P3B semantic, balance, Stage 1,
or merge changes are authorized in this slice.

## Encoded identity schema

Incarnation identity is storage/runtime metadata scoped by `store_uuid`.
It is not simulation RNG state and is excluded from canonical gameplay digest.

- `incarnation_id`: monotonically allocated positive integer within one store.
- occurrence key: typed owner `(namespace, key)` plus typed occurrence path.
- occurrence row: `owner_namespace, owner_key, occurrence_path,
  incarnation_id, valid_from, valid_to, checksum`.
- identity state: versioned `next_incarnation_id` with the same captured
  generation semantics as lazy owner/query/order rows.
- current P2C identity links remain the alias authority. Occurrence rows only
  label the mutable objects those links describe; they never create a second
  sharing graph.
- group IDs are derived lookup aids and are never incarnation identity.

All identity rows use checked half-open generation intervals and publish in the
same `LazyRecordStore.commit` transaction as changed owner values/order/query
metadata/head. There is no separate identity publication head.

## Runtime API

The standalone module provides:

- `IncarnationId(store_identity, value)`;
- `Occurrence(owner_namespace, owner_key, path)`;
- `LazyIdentityRegistry`;
- deterministic monotonic `IncarnationAllocator` seeded from checked store
  identity state;
- bind/rebind/move/remove operations whose contract is:
  - same live Python object retains the same incarnation when moved or removed
    and reinserted;
  - equal-but-distinct Python objects receive different incarnations;
  - an obsolete retained object is never rebound to a replacement at its old
    owner occurrence;
  - one live mutable instance per incarnation within one registry/session.

The registry uses weak references in both incarnation->object and object-id
reverse lookup. Object-id reuse is safe because callbacks compare the exact
weakref/token before deleting state. No refcount thresholds are used.

The registry separately records current occurrence ownership. Removing the final
canonical occurrence makes a still-live externally retained object detached;
mutating it cannot implicitly dirty a new replacement owner. Reattaching the
same object can restore its prior incarnation explicitly.

## Strong-reference audit

The proof module itself holds no strong reference to registered mutable objects.
The reverse lookup contains weakrefs plus incarnation metadata only. Occurrence
maps contain incarnation IDs, not objects. Derived group projection contains
occurrence/incarnation IDs only.

The later World/session slice must enumerate strong roots from:
`_BINDINGS`, `_memo`, root wrappers, `IdentityOccurrenceIndex`,
query/index caches, EventLog bindings and current-scope caches before any
archive family migrates. This standalone gate does not claim those existing P2
structures are bounded.

## Standalone proof matrix

Tests must cover:

1. retained top-level alias and reaccess returns same instance;
2. equal-but-distinct replacement gets new incarnation and old alias stays old;
3. move/remove/reinsert same object preserves incarnation;
4. delete/reinsert different object does not reuse incarnation;
5. retained child after parent object is dropped: child identity survives and
   its current owner occurrence remains known;
6. parent/child cross-owner sharing;
7. group merge/split changes only derived group projection;
8. weak cleanup removes dead reverse/live entries without global sweep;
9. deliberate Python-id-reuse simulation cannot erase a newer binding because
   cleanup is weakref/token checked;
10. close clears registry metadata without mutating user objects;
11. store occurrence/state current and retained-previous reads are generation
    consistent;
12. owner values, occurrence labels, next-incarnation counter and head publish
    atomically; injected failure leaves complete old state;
13. stale pin reads old owner + old occurrence together;
14. backup/current-head recovery preserve current labels while old-only identity
    revisions are not copied;
15. no-op writes no occurrence/incarnation rows.

## Gate

Run the standalone identity tests plus P4.1 storage tests first. The slice passes
only if the identity semantics above hold without World integration and the
P4.1 contracts remain green. Then proceed automatically to the people/session
integration plan required by the handoff.

Long full-suite execution is deferred until the next integrated stable product
gate; do not run a full suite merely for this isolated proof slice.
