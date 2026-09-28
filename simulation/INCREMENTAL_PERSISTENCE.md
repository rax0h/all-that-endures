# Continuing-world persistence contract

Status: **P1/P2A and opt-in P2B implemented and validated; production integration
and cold storage are not release-validated**. See
[PERSISTENCE_P2B_VALIDATION.md](PERSISTENCE_P2B_VALIDATION.md) for the current
acceptance boundary and the identity-metadata replay limitation.
Prepared against `97e4781c2004509087766f958cbcfab808ce1cb8` on PR #14.
This document does not declare Stage 0.5 complete or change simulation rules.

## Purpose and boundaries

A save has no designed end date. Retained history necessarily consumes storage;
the age of the save must not require every autosave or annual step to scan it.
Real growth in active populations or activity can increase work. Old ownership,
genealogy, events and identities remain recoverable, including when an old
person, object or institution becomes relevant again.

Implement persistence below the authoritative simulation operations. Player and
NPC actions eventually use the same mutation boundaries. Neither storage, a
renderer nor a future narrative layer can invent or replay approximate causes.
No new scheduler, subannual semantics, personhood, balance or rank changes here.

## Findings from the actual code

| Existing component | Consequence for persistence |
|---|---|
| `checkpoint.py`, schema 8 | `save` materializes a full pickle after a full canonical hash; `load` reads/deserializes it and hashes the entire world again. Keep this trusted legacy format as the reference and explicit import/export path. |
| `World` in `core.py` | Dataclass fields define canonical state, including several redundant indexes. Runtime attributes are not uniformly excluded from legacy pickle. An explicit field inventory is required; copying `__dict__` is insufficient. |
| `EventLog` | Sealed 2,048-event chunks are immutable, but all compressed bytes still live inside the world. This is the first safe disk-backed payload family. The current tail must be saved too. |
| `RecordTable` / `IndexedRecord` | Field notifications serve selected secondary indexes only. They do not track nested container edits and are not a persistence mutation journal. |
| `currency.wallets` / `treasuries` | Transfers mutate two nested dictionaries and sometimes supply counters. Every touched record must commit in one save transaction. |
| `advancement.paths` | A person's path contains mutable abilities, response models, understanding dictionaries and lists. Top-level assignment tracking would miss most progress. |
| `MaterialLot.transfers`, relationships, genealogy | Nested histories and member collections grow or mutate in place. Relationships and selection caches retain references to live objects. Eviction cannot introduce duplicate mutable instances. |
| `history_archive.py` | An inspection export, explicitly not a replay checkpoint. It omits state and intentionally transforms some types. Do not load it as a World. |
| `event_ids` | A growing set duplicates consecutive event IDs. A compact range view is possible only after proving canonical membership and import invariants; do not silently drop this canonical field. |

Observed year-2000 save/verified-load times were 127.323/156.841 seconds. At
3010, the full hash alone took 188.563 seconds. These are full-world costs,
not a reason to disable integrity checks or omit authoritative fields.

Sol's offer implementation is validated for exact canonical outcomes. It
still returns complete offer snapshots and refreshes changed inventories as
units; its ordered lists use insertion/removal shifts. The 1.24x short query
benchmark does not prove flat cost at year 3000. Measure this separately after
persistence is usable; do not reopen its implementation speculatively here.

## Decision: transactional local save store with explicit record ownership

Use Python's existing `sqlite3` dependency for a separate versioned save store.
Keep the historical-inspection SQLite schema independent. Start with a single
writer, rollback journaling and `synchronous=FULL`; do not add concurrent writers
or background mutation. Verify effective settings and reject a requested mode
the runtime cannot provide. WAL can be evaluated later with measured readers,
maintenance and backup behavior; it is not necessary to prove this design.

An initial import necessarily visits the entire source world. Subsequent saves
write changed records and new sealed segments only. A no-change save is a no-op.
Do not advertise incremental I/O if discovering changes still scans all history.

Logical schema (exact DDL belongs to the first implementation tranche):

| Table | Key and contents |
|---|---|
| `store_metadata` | Store UUID, persistence-format version, codec version, compatible simulation-schema/rules identifier. No absolute external payload paths. |
| `save_head` | Single published generation, parent generation, simulation position, seed and next-ID counters; reference to complete required namespace inventory. |
| `records` | `(namespace, typed_key)` current payload, payload checksum, record schema, last changed generation. Ordered collections retain their own ordering information. |
| `segments` | `(namespace, ordinal)` immutable payload, codec/checksum, element count and logical first/last IDs or sequence positions. |
| `query_membership` | Versioned, rebuildable persistent lookup rows used to find active/owned records without decoding the archive. Updated atomically with affected records. |
| `save_receipts` | Generation metadata and write counts for diagnosis. Explicit bounded retention; these are storage metadata, not simulated events. |

There is one committed head, not an ever-growing chain of snapshots that must
be replayed on load. Old objective events remain append-only. Replacing a saved
mutable record does not erase its causal event history, and does not claim to
preserve arbitrary past snapshots the current simulator never recorded.
Named manual save branches are independent consistent copies initially; shared
content-addressed branching/version garbage collection is outside this tranche.

SQL transactions provide publication: data, lookup rows, counters and head move
together. No page/blob written outside that transaction is required for recovery.
This deliberately avoids a two-file manifest/blob-store commit protocol.

## Record boundaries and codec

Never put all people, wallets, resources or paths in one serialized state blob.
Split each top-level identity-bearing collection into individual records:

* `people[pid]`, `households[hid]`, `materials.lots[lid]`,
  `materials.items[iid]`, `magic_resources.resources[rid]`;
* `advancement.paths[pid]` owns its bounded ability/understanding object tree;
  wallets and treasuries are separate per-owner records;
* relationships keyed by their actual pair, claims, memberships, transmissions,
  institutions, branches, notices, applications, souls and threats by their
  existing typed keys; no synthetic replacement identities;
* small per-world metadata includes configuration, counters and bounded maps;
  every allegedly bounded field must be justified in the adapter registry.

Large nested collections need their own adapter. An ancient institution's
membership set or a long-lived object's transfer list must not become a hidden
ever-growing single record rewritten after every append. Use keyed membership
rows or fixed-size sequence segments plus a bounded mutable tail. Preserve list
order, duplicate list entries and exact set semantics. A new growing field
requires an explicit storage choice, not automatic inclusion in world metadata.

Implement a versioned, allowlisted typed codec, separate from the current
canonical JSON. Distinguish lists, tuples, sets, frozensets, typed dictionary
keys, enums and registered record types. Preserve dictionary insertion order
for runtime behavior; canonical ordering for a digest does not authorize a
different simulation iteration order. Preserve exact numeric values, including
negative zero; reject unsupported values explicitly. Do not silently stringify
keys or round floats. Never import arbitrary Python classes from stored names.

Authoritative cross-record links should already be stable IDs; enumerate any
exceptions. A mutable child has one declared owner. If shared mutable ownership
is encountered, preserve it through an explicit identity reference or reject
that adapter until resolved; serializing two copies is not equivalent.
Derived strong-reference caches are rebuilt and never encoded as facts.

Require coverage tests that recursively inventory every canonical dataclass
field and collection. Each field is persisted directly, represented losslessly
by an adapter, or reconstructed by a tested exact rule. Unknown fields fail
coverage. Canonical index fields such as `owner_index`, `active_lot_index`,
`genealogy.children` and `social.adjacency` cannot simply disappear because
they look redundant. Preserve them first, or prove their exact reconstruction.

## Mutation coverage and identity

Persistence binding adds a distinct dirty-record tracker. Do not overload the
query index's notification link. Recursively bind mutable nested dataclasses
and containers to their record owner. Assignment, insertion, deletion and
in-place container operations mark that owner dirty. New nested values become
bound immediately. Replacing a nested value detaches the previous binding.
Tests must cover `setdefault`, slices, augmented updates, deletion, list sorting,
set updates and mutations through retained aliases, not merely method calls.

Explicit mutation authorities remain preferred public APIs. Existing valid
direct edits must either remain tracked or fail loudly; silent persistence loss
is forbidden. A restricted mutation API cannot be introduced without migrating
and testing every affected caller. A full-scan debug verifier is useful during
development but is not the production change detector.

An identity map guarantees one live object for `(namespace, key)` within a world
session. Start by retaining materialized mutable objects: incremental saving
does not by itself promise bounded memory. Subsequent eviction requires an
explicit quiescent boundary and removal/rebinding of persistent caches such as
`SocialGraph._relationships`, resource inventory tuples and offer-book tokens.
Retained writable aliases must pin the object or use handles. Never reload a
second mutable copy while the first is still reachable. Dirty objects cannot
be discarded before commit. Death alone never authorizes freezing a person:
resurrection and later legitimate edits remain supported.

## Save, load, failure and verification contracts

1. Save only after a completed `Simulation.step`, outside current-person/rank
   scopes. Later player-action transactions may expose the same quiescent
   boundary; this phase must not invent a mid-step replay model.
2. Freeze mutations during capture and commit. Enumerate dirty keys and new
   segments, encode them, and write one transaction with affected lookup rows
   and all position/counter metadata. Publish head in that same transaction.
3. Clear dirty markers only after successful commit. On any error retain them.
   A process exit before commit must recover the old head; after commit the
   complete new head. A lost acknowledgement is resolved from the committed
   generation; retry must not duplicate events or increment IDs again.
4. Load checks format, namespace inventory and rules compatibility, then binds
   a World view to one committed head. Load the working set, not all history.
   Indexed disk lookups must support active/current queries without warming
   indexes by materializing every historical record. Writes use an expected-head
   check; another process cannot silently overwrite a newer save.
5. Verify each payload's checksum and type before using it. Missing/corrupt
   payloads fail explicitly; no default values, regenerated history or silent
   rollback. Provide a separate full scrub checking every payload, reference,
   logical index and canonical digest. Retain current full CI audits unchanged.

Incremental integrity and the existing canonical world digest are **different
contracts**. Keep `World.digest()` unchanged as the cross-backend comparison.
It is still an O(history) explicit audit; do not recompute it on each autosave,
substitute a checksum of changed bytes, or relabel a storage checksum as the
canonical digest. Opening a lazy store verifies the opened working set and
verifies cold payloads on access; it cannot truthfully claim it just read and
validated all cold bytes. Full scrub retains that stronger explicit guarantee.
This verification distinction must be visible in APIs and validation reports.

Schema 8 pickle remains trusted-input-only. Import to a new store, perform full
digest/continuation validation, then publish that new store; never rewrite the
sole old save in place. Reject unknown schemas/rules versions. Later migrations
must state whether simulation semantics change, preserve IDs, and provide a
recoverable original. Binary store bytes need not be identical; canonical world
and history results must be identical for unchanged rules.

Use SQLite's consistent backup mechanism for a portable manual copy; do not
copy an open database file casually. Explicit export/backup/full scrub can cost
O(total retained data). Report those costs separately from routine incremental
save and load. Storage exhaustion must leave the last committed generation
readable. Compaction may reclaim obsolete storage representations, never delete
canonical events or resources to improve a metric.

## Implementation tranches and stop points

**P1 — store and codec only (accepted after repair).** See
[PERSISTENCE_P1_REVIEW.md](PERSISTENCE_P1_REVIEW.md) for the disposition and evidence.
The original implementation contract follows: add the standalone
transactional store/codec and adversarial tests. Do not connect World, change
`checkpoint.save/load`, touch progression or run a millennium. Use the operations
`create`, `open`, `read_record`, `read_segment`, `commit(expected_generation,
changes, new_segments, metadata)`, `verify_all`, `backup`, `close`. Include
diagnostic counters for payload reads/writes/bytes. No world-root pickle fallback.
Stop for review with implementation SHA, tests and explicit limitations.

**P2 — complete adapter registry and mutation coverage.** Inventory every World
field; implement tracked ownership and exact codec round trips. First full
bootstrap followed by a no-op save and selected nested mutations must prove
only affected records are encoded. Test direct aliases and cross-record money/
resource operations. Keep the legacy checkpoint as the reference.

P2 is split into reviewable steps. P2A's complete World adapters and P2B's opt-in
mutation ownership/saving are accepted; see
[P2B final validation](PERSISTENCE_P2B_VALIDATION.md).
**The next bounded Sol assignment is P2C only**:
[current identity state without an accumulating replay journal](PERSISTENCE_P2C.md).
Preserve legacy compatibility and exact continuation. This does not replace
checkpoints or authorize P3 implementation.

**P3 — integrate incremental saves and disk-backed immutable events.** Preserve
EventLog order, year queries, sealed immutability, tail and event IDs; cold chunks
load on demand with a bounded cache. Compare memory/legacy/store worlds using
identical actions, full digests and archive output. Full import and full scrub
remain deliberate, separately measured operations.

**P4 — lazy record loading and bounded resident state.** Add persistent current
query memberships and identity-safe eviction, starting with truly sealed records.
Prove reactivation/transfer/resurrection and old provenance queries. Measure how
much memory remains pinned by genuine activity versus avoidable archive caches.
No blanket cold/dead status rule; no automatic conversion of people to averages.

**P5 — integrated release validation.** Full suite and smokes, chronological
audit, checkpoint and archive equality, one canonical millennium after stable
short tests. Use a durably retained trusted late-world fixture for a short
continuation/profile; obtain longer horizon evidence only to resolve an actual
scaling question. Do not repeat a 3,000-year run after each tranche.

## Mandatory evidence

* Kill a writer in subprocess tests before transaction, during writes and after
  commit; recover exactly old or new generation, never mixed state. Inject disk
  errors and failed encoding; retry without duplicate IDs/events or lost dirtiness.
* Reject wrong store/version, stale expected generation, invalid codec types,
  missing rows and corrupted payloads; test backup/restore and source relocation.
* Verify all dictionary/list/set/enum/numeric types and ordering, shared identity
  rules, cold cause lookups and nested mutation coverage.
* Match full canonical digests and future histories for memory, legacy-checkpoint
  and new-store runs, including a warmed offer index and reference caches.
* Count rows/bytes decoded and rewritten with fixed working set/changes while
  increasing cold history 10x. A no-op save must not encode any record; one-wallet
  change must not decode all wallets. These tests verify cost structure, not
  flaky wall-clock thresholds. Time initial import, normal save, resume, full
  scrub, backup and archive export separately.
* Assert every canonical field is covered and simulation RNG consumption is
  unchanged. Never update a golden digest just to make a backend pass.

Freeze remains blocked until the integrated backend is measured and validated.
A green P1 storage test suite alone does not establish indefinite-world readiness.

## Backend references

Official SQLite documentation: [atomic commit](https://www.sqlite.org/atomiccommit.html),
[synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous),
[backup API](https://www.sqlite.org/backup.html),
[WAL trade-offs](https://www.sqlite.org/wal.html). Recheck the deployed SQLite
version and filesystem behavior before selecting a different journal mode.
