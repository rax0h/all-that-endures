# P4 — generation-safe lazy current records and bounded resident state

**Status:** architecture proposal for Astra review. **Do not implement production P4 until this proposal is accepted.**

**Prepared against live PR head:** `62f3ec5e71242c7373d343fd121baaf0afaea842`.

P1/P2/P3A and complete P3B are accepted and are dependencies, not targets for redesign. The measured preparation evidence is in:

- `PERSISTENCE_P4_INVENTORY.md`
- `persistence_p4_baseline.json`
- `persistence_p4_probe.py`
- `tests/test_persistence_p4_probe.py`

The green preparation run is Actions **37269630276**. Five proof-fixture tests passed in 1.16 s. The 1,000/10,000 baseline completed on Python 3.12.14 / SQLite 3.45.1.

## 1. Decision

P4 should add an **opt-in, generation-versioned lazy-current representation** on top of the accepted SQLite transactional store.

The first production family should be `world.people`, because the preparation probe shows an archive-sized open/memory/index cost while point reads and local writes are already bounded:

- fixed 32 active people, 1,000 -> 10,000 inactive people;
- cold-open reads: **2,103 -> 20,103**;
- cold-open peak allocation: **3,821,388 -> 30,963,854 bytes**;
- session memo entries: **1,033 -> 10,033**;
- identity-index identities: **1,033 -> 10,033**;
- first `alive=True` RecordTable membership build: **1,032 -> 10,032 source rows**;
- checked point access: **one payload read** at both sizes;
- one inactive-person reactivation/save: **3 payload writes / 795 bytes** at both sizes.

The current offer implementation is not the selected first target. With 1,000 vs 10,000 irrelevant consumed MagicResource records it visited the same **4 eligible inventory IDs**, returned the same stable offer order and did zero inventory work on the warm repeat query. Resource **residency** still grows and is a later high-impact P4 family.

No record becomes immutable because it is dead, old, consumed or inactive. Resurrection, ownership transfer, direct tracked mutation and old-provenance lookup remain supported.

## 2. Representation

### 2.1 Explicit P4 mode

P4 is a new opt-in current-record mode. A P4 store declares all of these manifest values:

- `record_storage = "generation-records/v1"`
- `collection_storage = "generation-order/v1"`
- `query_membership_storage = "generation-membership/v1"`
- `identity_group_storage = "lazy-identity-groups/v1"`
- `generation_retention = 2`
- `lazy_namespaces = (...)`

Existing P2/P3 stores do not acquire these meanings by inference. The accepted P3B `open_world_session` must reject a P4 manifest early until an explicitly named P4 open API is installed. The proposed new entry point is:

```python
open_lazy_world_session(path, *, rules_id)
```

The normal schema-8 checkpoint default does not change.

### 2.2 Versioned record rows

Add a P4 table logically equivalent to:

```text
record_versions(
    namespace,
    typed_key,
    valid_from_generation,
    valid_to_generation NULL,
    payload,
    payload_checksum,
    codec_version,
    record_schema,
    PRIMARY KEY(namespace, typed_key, valid_from_generation)
)
```

A row is visible to captured generation `G` iff:

```text
valid_from_generation <= G
and (valid_to_generation is NULL or G < valid_to_generation)
```

Deletion is represented by closing the prior interval and omitting a new value row; collection membership separately records the deletion/reinsert ordering transition. No lazy read consults an overwritten mutable "current row" as its authority.

A write to one owner at generation `G+1` closes its old visible row at `G+1` and inserts the new row at `G+1`. Those changes occur in the same SQLite transaction as current-query memberships, collection order, identity metadata, counters, EventLog publication and the new save head.

Existing P1/P2/P3 tables and APIs remain valid for their formats. P4 storage helpers must be additive and mode-checked rather than changing legacy interpretation.

### 2.3 Canonical dictionary order

Lazy root dictionaries cannot keep every key in Python merely to preserve insertion order.

Add generation-versioned collection membership:

```text
collection_members(
    namespace,
    typed_key,
    ordinal,
    valid_from_generation,
    valid_to_generation NULL,
    row_checksum,
    PRIMARY KEY(namespace, typed_key, valid_from_generation)
)
```

Rules:

- first insertion receives the namespace's next monotonic ordinal;
- assignment to an existing key preserves its ordinal;
- deletion closes that membership interval;
- reinsertion after deletion receives a new ordinal, matching Python dict delete/reinsert behavior;
- `len(mapping)` uses committed count plus local overlay, O(1);
- `key in mapping` is a point membership lookup;
- iteration pages current keys by ordinal, **128 keys per page**;
- `values()` / `items()` remain supported and may explicitly materialize/stream O(H) if a caller requests the whole archive.

No ordinary gameplay/current query may depend on full `values()` over a lazy historical namespace.

### 2.4 Versioned current-query membership

Add:

```text
query_membership_versions(
    namespace,
    index_name,
    index_value,
    record_key,
    ordinal,
    valid_from_generation,
    valid_to_generation NULL,
    row_checksum,
    PRIMARY KEY(
        namespace,index_name,index_value,record_key,
        valid_from_generation,ordinal
    )
)
```

The owning record remains authoritative. Membership is a rebuildable, checksummed lookup projection.

Each family adapter defines exact membership extraction and exact final ordering. Persistent membership narrows the key set; Python applies the existing tie/order rule to the **R eligible keys**, not H historical records. Examples:

- people `alive=True`: record key pid; output sorted by pid exactly as `RecordTable.select`;
- applications: `passed`, `(person,society)`; existing ID/year tie behavior preserved;
- notices/conflicts/inquiries/threats: status memberships;
- resources: `(owner_kind,owner_id)` and availability;
- property: `(owner_kind,owner_id)`;
- materials: active settlement/rank membership.

Each membership checksum frames namespace, index name/value, record key, ordinal and generation interval. Full scrub recomputes memberships from owning records and rejects missing, extra, stale, corrupt or duplicate rows.

### 2.5 Unsaved local overlay

A captured session owns a deterministic overlay:

```text
overlay[(namespace,index_name,index_value)] ->
    {record_key: ADD | REMOVE}
```

and a collection-order overlay for insert/delete/reinsert.

Any local record mutation that changes an indexed field updates the overlay through the same owner dirty-tracking hook. Query:

1. reads persisted membership visible at captured generation G;
2. applies final local removes/adds;
3. de-duplicates by canonical key;
4. loads only the resulting R records;
5. applies the existing exact ordering/tie rule.

The overlay contains final unsaved state, not a replay log. Save derives the same membership changes from the dirty owners and commits them atomically. Failed save leaves the overlay and dirty pins intact.

## 3. One mutable instance and retained aliases

### 3.1 Session identity registry

A P4 session owns a `LazyIdentityRegistry`. It replaces archive-sized strong `_memo` / occurrence retention for lazy namespaces.

For each loaded mutable identity it stores a **weak reference** keyed by stable identity occurrence/group metadata. Tracked dict/list/set subclasses and registered mutable dataclasses are weak-referenceable after binding. The registry itself does not keep a clean object alive.

Strong references exist only in explicit pin sets:

- dirty owners/groups until a successful save;
- current/active scope results such as `World._living_cache`;
- the clean cache budget;
- objects genuinely retained by external callers or derived caches.

External Python aliases do not require refcount heuristics. If a caller retains a Person or a tracked nested container, that object remains alive independently. The registry's weak reference therefore resolves to the same object on reaccess. P4 never reloads a second writable instance while that first one is reachable.

### 3.2 Clean cache budget

For the first people pilot:

- clean strong-cache budget **B_people = 256 sharing groups**;
- current/active pins and dirty pins are outside B and are reported separately;
- eviction is allowed only at a completed simulation step / no current scope / no lifecycle operation;
- dirty groups never evict;
- cache pressure drops only the session's strong cache reference.

There is no "dead-person eviction" rule. A dead Person can be clean and unpinned, but resurrection/point access simply loads the same canonical record again if no prior alias survives.

### 3.3 Sharing groups

Persisted current identity links are converted during explicit P4 conversion into indexed **sharing-group membership**. A group has a stable ID derived from the canonical lowest encoded owner occurrence. Group metadata identifies all record owners and mutable occurrence paths needed to restore the alias graph.

Accessing any record owner in a group:

1. queries the group members without scanning unrelated identity rows;
2. checks the weak registry for already-live identities;
3. point-reads the group's missing owner payloads at captured generation G;
4. restores aliases using the existing validated identity-path rules;
5. binds each mutable object exactly once.

If a top-level owner has died from the clean cache but a caller still holds a nested tracked list/dict/set from that group, the nested weak entry remains live. Reloading the owner stitches that existing child back into the decoded group rather than creating a second child.

A sharing group may evict only as a unit from the session's **strong cache**. Live external aliases can keep part or all of the group resident; that is counted as pinned residual state, not hidden behind B. This is the rigorous equivalent of whole-group eviction required by the persistence contract.

The first Person pilot normally has group size 1 because Person has no nested mutable fields. Cross-owner alias fixtures are nevertheless required before acceptance. Families with nested mutable structures do not migrate until their group restoration tests pass.

### 3.4 Derived caches

Derived caches may not silently defeat eviction:

- `World._living_cache` is an allowed current-scope Person pin and is cleared as today;
- `SocialGraph._relationships` must store keys/weak handles after edge migration rather than permanent Relationship references;
- magic-resource inventory/selection caches must retain IDs/tokens rather than Resource objects when resources migrate;
- offer books, material heaps, selection pools and rank caches remain derived and are measured separately.

Any remaining strong record reference in a cache counts as a pin in diagnostics.

## 4. Generation-consistent lazy reads and stale sessions

### 4.1 Captured generation

A lazy session captures generation **G** at open and registers a generation pin. Every lazy point or membership read uses G explicitly.

A read operation opens a **bounded SQLite read transaction** and, inside that same transaction:

1. validates the current head row/checksum;
2. reads the record/membership version visible at G;
3. validates row checksum/schema/type;
4. decodes/binds the result;
5. closes the read transaction.

If a writer commits between steps 1 and 2, SQLite's transaction snapshot prevents the operation from seeing a mixed before/after database. If the writer committed before the bounded transaction began, the historical version visible at G is still selected. No head check outside the payload transaction is relied upon for consistency.

Rollback-journal / `synchronous=FULL` remains unchanged. Read transactions are operation-bounded; P4 does **not** introduce a session-long SQLite read transaction that could indefinitely block writers.

### 4.2 Bounded generation retention

To preserve accepted stale-session materializing detach without retaining unlimited generations, P4 selects a **two-generation retention contract**:

- the current committed generation;
- at most one immediately preceding generation required by an open session.

A P4 session registers:

```text
generation_pins(session_token, captured_generation)
```

A writer at generation G may commit G+1 while another session remains pinned at G. Old record/membership versions needed by G remain available.

If current generation is already G+1 while a live pin still requires G, a further commit to G+2 fails immediately with a specific generation-pressure error. It does not wait for a reader and it does not discard the old generation. This is a deliberate availability bound that prevents unbounded retained revisions while preserving the existing stale-detach use case.

After the stale session closes or successfully materializes detach, its pin is removed and obsolete versions can be reclaimed transactionally. A failed detach retains its pin.

A process crash can leave an orphan pin. P4 does not guess liveness from time, PID reuse or refcounts. An orphan may safely cause the same fail-fast generation-pressure error. Recovery is an explicit **source-preserving offline compaction/conversion to a new file** containing only the verified current head; the original file is not mutated. This is conservative but correct.

**Architect decision requested:** accept the two-generation/fail-fast concurrency bound. It is the selected design because it preserves stale materialization, keeps rollback journaling, avoids session-long writer blocking and gives a hard revision bound. Increasing the retained-generation constant later is a capacity decision, not a semantic redesign.

### 4.3 Stale behavior

A session pinned at G after another writer publishes G+1 is stale but internally consistent.

Allowed:

- read already-loaded records;
- lazy-read records/memberships at G;
- local mutation of its private World;
- explicit materializing detach from its G + local overlay;
- close.

Rejected:

- save over G+1;
- resolve as though it owned the newer generation;
- any operation that would silently switch lazy reads to G+1.

The accepted P3B stale-detach behavior is therefore preserved rather than weakened.

## 5. Atomic writer contract

P4 extends the accepted cold-save transaction; it does not create a second publication authority.

For dirty owner set K, one commit transaction must include:

1. new/closed record-version intervals for K;
2. collection-order changes for inserts/deletes/reinserts;
3. query-membership interval changes for K;
4. sharing-group/current-identity changes affected by K;
5. accepted EventLog tail/sealed publication;
6. counters, next IDs and collection counts;
7. save receipt;
8. the new checked head.

Failure before commit leaves every old row/head visible. Failure after commit is handled by the accepted lost-acknowledgement recovery pattern: the candidate generation/head and changed records/memberships are compared before deciding whether to retry.

Membership rows can never publish separately from their owning record generation.

## 6. Pilot mapping/API contract

The people pilot supplies a `LazyRecordTable` compatible with the supported operations used by `world.people`:

- `__getitem__`, `get`, `__contains__`;
- `__len__`;
- `__iter__`, `keys`, `values`, `items`;
- `__setitem__`, `__delitem__`, `update`, `setdefault`, `pop`, `popitem`, `clear`, `|=`;
- `ids` / `select` for declared persistent indexes.

Exact compatibility rules:

- point access returns the session's one live mutable Person;
- full iteration preserves canonical dictionary ordinal;
- `select("alive", True)` returns stable pid order exactly as current RecordTable;
- direct Person field assignment remains valid and dirty-tracked;
- delete/reinsert changes dictionary order exactly as Python dict;
- replacing an existing key preserves ordinal;
- unsupported identity cycles fail loudly;
- no hidden full warmup occurs in constructor/open.

The implementation must inventory all direct `world.people` callers before changing the concrete type. Existing point access patterns remain valid. Any code using archive-wide `.values()` becomes an explicit O(H) operation and must not be introduced into annual/current gameplay.

## 7. Growing nested histories

The pilot deliberately avoids inventing a universal segmentation framework.

When later measured families migrate:

- **set/dict membership history** (institution members, church followers, genealogy/lineage child memberships) uses keyed/versioned membership rows when the owning record is still authoritative;
- **ordered lists with proven append-only semantics** may use fixed-size immutable segments plus a bounded mutable tail;
- **lists that permit arbitrary replacement/delete/reorder/direct edits** remain mutable owner payloads until an adapter preserves those operations exactly.

A per-owner record whose nested transfer/provenance list grows without bound is explicitly **not** considered solved merely because the top-level record is lazy. Its payload bytes and rewrite cost remain a reported bound until segmented.

Candidate nested fields include Relationship.shared_history, Property provenance/ownership, SkillHistory teachers/provenance, Infrastructure provenance, MagicResource transfers and MaterialLot transfers.

## 8. Compatibility, conversion and lifecycle

### 8.1 Conversion

Add an explicit source-preserving conversion only after P4 design acceptance:

```python
convert_lazy_record_storage(source, destination, *, rules_id)
```

It:

- accepts a fully validated accepted P3B cold source;
- rejects an already-P4 source with instruction to use backup/relocation;
- performs the unavoidable O(total) source traversal once;
- writes P4 record versions, collection ordinals, memberships and identity groups to a private destination;
- fully validates the private destination;
- compares canonical digest and required identity/current-query projections;
- atomically publishes the new path without overwriting source.

No ordinary P4 open performs automatic full import.

### 8.2 Old APIs

- schema-8 checkpoint default remains unchanged;
- checkpoint dumps/save continue to reject bound cold/P4 Worlds until explicit detach;
- direct EventLog pickle rules remain unchanged;
- P2/P3 readers reject P4 manifest before scanning payloads;
- P4 reader rejects P2/P3 mode rather than silently converting;
- legacy checkpoint/P2/P3 continuation remains tested.

### 8.3 Backup / relocation

Exact SQLite backup remains an explicit full-cost operation. A backup containing generation pins/revisions is an exact operational copy, not silently treated as a new current-only store. A source-preserving **current-head compaction/conversion** is the safe way to discard orphan pins or old retained versions.

Relocation may not store absolute payload paths.

### 8.4 Close

Close:

- rejects active lifecycle operation as today;
- clears strong cache/pins and mutation bindings;
- deletes the session generation pin when possible;
- drops weak registry metadata;
- closes EventLog prefix/store;
- performs no implicit archive materialization.

If pin deletion fails because the store is already unavailable, safety is preserved by the durable orphan pin; later writers may fail fast until explicit source-preserving compaction.

### 8.5 Digest / archive / scrub

- canonical digest remains O(total logical World) and streams lazy families at captured G;
- history archive remains O(total) and preserves logical equality;
- full scrub verifies every retained current/version row, membership, group link, collection ordinal and accepted EventLog storage;
- none of these full operations changes ordinary open/save cost;
- materializing detach streams every lazy family at G, applies local overlay, restores exact aliases/order and returns a portable in-memory World.

## 9. Ordinary-operation bounds

Symbols:

- **H** — cold/inactive records in the selected family;
- **A** — genuinely active/current records requested by ordinary simulation;
- **R** — records returned by a requested point/query operation;
- **K** — locally edited/inserted/deleted owners since the last save;
- **L** — identity-link/group metadata for the loaded/changed groups;
- **S** — records/identities in one sharing group;
- **B** — clean strong-cache budget (people pilot B=256 groups);
- **P** — groups kept alive by active scopes, dirty state or external/derived strong references;
- **Q** — membership rows returned by a current query before local overlay; normally Q≈R;
- **E** — accepted P3 mutable/resident EventLog tail state.

Proposed bounds:

| Operation | Payload / row work | Resident-state bound |
| --- | --- | --- |
| open lazy people | O(1) head/manifest + bounded namespace descriptors; **0 Person payloads** | O(B + P + E + fixed roots), not O(H) |
| point person read | O(S) checked record rows; ordinary unshared Person **1 payload** | cache/group O(S) |
| `current_people` first query | O(Q + K) membership rows + O(R) Person decodes; no H scan | O(B + P + A) |
| warm current query | O(Q + K) key rows; decoded live records reused when resident | same |
| full people iteration | O(H + A) by explicit caller request | bounded streaming unless caller retains results |
| no-op save | **0 record payload writes**, no H discovery | unchanged |
| one local Person edit | O(1) dirty owner; overlay O(number of changed indexes) | one dirty group pin |
| save K owners | O(K + membership deltas + affected L + new P3 event work), no H scan | dirty pins until acknowledgement |
| close | O(B + P + K + loaded L), no H traversal | releases session state |
| digest/archive/scrub/detach | O(total logical data) | separately measured explicit operations |

Structural acceptance constants for the people pilot:

- clean cache groups: **<=256**;
- key iteration page: **<=128** keys;
- nonshared point read: **exactly 1 checked Person payload**;
- no-op save: **0 Person payload writes**;
- fixed one-person field edit: **1 Person version write**, plus only its exact membership/identity/head/event-related rows;
- first `alive=True` query with fixed A while H grows 10x: Person payload decodes **<= A + local additions**, and membership rows visited **<= A + local overlay cardinality**;
- `_memo`, identity-object registry and loaded Person count must not grow with H on open;
- revision visibility spans at most **2 committed generations**; a third required generation fails before transaction publication.

These are structural counters, not wall-clock gates.

P4 is not closed merely by meeting people-pilot bounds. After each expansion the residual ordinary open/resident inventory is remeasured. Any remaining archive-sized family that materially dominates ordinary memory/read work remains a P4 blocker.

## 10. Implementation sequence after architecture approval

### Task P4.1 — versioned store primitives, no World integration

Files:

- `ate_sim/incremental_store.py`
- `ate_sim/persistence_schema.py` or a narrowly named P4 schema module
- new `ate_sim/persistence_lazy_store.py`
- focused storage tests

Implement:

- P4 mode/version recognition;
- record/version interval point reads at captured G;
- collection-member/version rows;
- membership/version rows and checksums;
- generation pins and two-generation pressure;
- source-preserving conversion primitives;
- full scrub coverage for new tables.

Proofs:

- writer commits between head read/payload read;
- writer commits during decode;
- old G read remains old G;
- stale session point read;
- G -> G+1 allowed with G pin; attempted G+2 fails fast;
- close pin then G+2 succeeds and old revisions reclaim;
- before-commit failure, writer death, lost acknowledgement;
- missing/corrupt version/membership/order rows;
- old-format and unknown-mode early refusal;
- backup/source relocation.

**Stop only for a material authority change; ordinary failures are fixed within the tranche.**

### Task P4.2 — people lazy pilot and identity groups

Files:

- new `ate_sim/persistence_lazy.py`
- `persistence_session.py`
- `persistence_tracking.py`
- `record_index.py` only if needed for the supported facade
- `core.py` only for query adapter plumbing, not simulation semantics
- focused people/identity tests

Implement:

- LazyRecordTable for `world.people`;
- weak identity/group registry;
- B=256 clean cache;
- dirty/current/external pin accounting;
- alive membership adapter and local overlay;
- lazy dictionary order;
- conversion of Person current identity groups.

Proofs:

- external top-level alias across cache pressure;
- direct Person mutation through retained alias;
- delete/reinsert/order;
- inactive -> alive reactivation;
- death -> resurrection;
- dirty pin survives pressure;
- failed save retains dirty pin/overlay;
- successful save releases eligible clean pin;
- cross-owner shared-object fixture;
- nested-alias group fixture using a prepared non-Person sharing group to prove registry mechanics before expanding nested families;
- no duplicate mutable instance on reaccess.

### Task P4.3 — current-query adapters

Files depend on measured families, initially:

- `core.py` current people;
- `persistence_lazy.py`;
- query adapter tests.

Then add status/owner adapters only for migrated families. Preserve exact current ordering and ties. Do not install a universal query DSL.

Required differential tests compare the existing eager World and P4 World for exact result IDs/order under:

- local indexed-field mutation before save;
- delete/reinsert;
- direct edit through alias;
- cache invalidation;
- save/reopen;
- stale local branch.

### Task P4.4 — expand to measured residual families

Rerun the inventory probe after the people pilot. Expand only where ordinary open/residency is still dominated.

Expected next candidates from retained late-world evidence:

1. `magic_resources.resources` + aspirations, preserving owner index and offer order;
2. `materials.lots/items` + active/lot indexes;
3. wallets/treasuries and person-coupled advancement/metaphysics as required to avoid person-history pinning;
4. relationships/genealogy/institutional memberships where alias/index metadata remains archive-sized.

Each migration requires a family adapter, exact current memberships, identity-group tests and its own nested-history decision.

### Task P4.5 — canonical residual metadata

Before P4 acceptance, address remaining ordinary O(history) metadata, specifically:

- `event_ids`: introduce an exact set-compatible compact/range representation only after tests prove the accepted consecutive-ID invariant, import equality, membership/iteration behavior and direct-operation compatibility;
- baseline ordinals / persisted-key sets / identity occurrence maps: lazy/versioned replacements must show no H-sized Python copies;
- derived caches: replace historical strong record references with IDs/weak handles or report them as genuine pins.

### Task P4.6 — integrated lifecycle / compatibility proof

Required scenarios:

- independent Worlds generated separately with identical seed/actions;
- exact canonical digest and subsequent events through save/reopen;
- warmed current query caches;
- external top-level and nested aliases under cache pressure;
- shared parent/child aliases crossing owners;
- local delete/reinsert/order;
- old provenance query then mutation;
- ownership transfer;
- resurrection;
- stale writer;
- before-commit failure;
- writer death and lost acknowledgement;
- corrupt/missing rows, memberships, group rows and ordinals;
- backup/relocation;
- close;
- failed and successful materializing detach;
- digest/archive equality;
- full scrub;
- unchanged RNG consumption.

Run focused/affected tests first; after product bytes stabilize run one full `simulation/tests` suite. Measure the 1k/10k fixed-active fixture again and require the structural counters above. Do not run millennium/endurance under this authorization.

## 11. Acceptance gates

P4 architecture/implementation is acceptable only if all are true:

1. Ordinary open and current people query no longer decode or retain all historical Person records.
2. One mutable instance is preserved across point reads, current queries, cache pressure and retained top-level/nested aliases.
3. Dirty/current/external pins are distinguished from the bounded clean cache and reported.
4. A World captured at G never mixes G+1 payloads or memberships.
5. One newer winner generation remains readable for stale detach; a third retained generation fails fast rather than discarding correctness or growing without bound.
6. Query memberships, owner records, identity state, counters, accepted EventLog publication and head move atomically.
7. Local unsaved membership changes are exact, deterministic and duplicate-free.
8. Delete/reinsert preserves dictionary order semantics.
9. Resurrection and old-record mutation remain supported; no death/freeze shortcut exists.
10. No-op save performs zero lazy-record payload writes and changed-record save cost is independent of H.
11. Full scrub/digest/archive/detach remain explicit O(total) operations and logically match eager/legacy controls.
12. Legacy P2/P3/checkpoint behavior remains unchanged and incompatible modes refuse early.
13. Residual ordinary resident growth is re-inventoried; P4 is not declared complete while another archive family or metadata structure still dominates.
14. A durable representative late-world fixture is still required for P5; synthetic proof is not relabeled as late-world validation.

## 12. Preparation evidence and limitation

The preparation probe is deterministic and bounded. It uses synthetic structural Worlds with fixed active state and 1,000/10,000 inactive records plus a separately generated short continuation control. The independent control matched exact digests through cold save/open, one year, save/reopen and another year; final digest:

`70ad8a91e29e3df58172e9ecf73be1486042e85f9e17872bb0dc2b41d2ff637e`

with 100 events / next_event 101.

The prior year-2000/year-3010 checkpoints are not available; the repository states they were lost in a workspace reset, and the inspected historical Actions runs expose no retained artifacts. This is not repaired by an unauthorized long run. A durable late-world fixture remains a P5 prerequisite.

## 13. Architecture-review request

**Proposed design decision:** generation-versioned lazy record rows + versioned atomic current memberships + weak sharing-group identity registry + explicit strong pins + two-generation fail-fast retention.

**Measured bottleneck:** eager non-event restore/identity/index retention scales approximately with inactive Person history even when active state and edit scope are fixed.

**Exact next implementation task after approval:** **P4.1 only** — versioned store/membership/order/generation-pin primitives and failure tests, with no World integration.

**Focused architect decision:** approve or reject the selected two-generation/fail-fast stale-session retention contract. All other implementation tasks in this document assume that bound.
