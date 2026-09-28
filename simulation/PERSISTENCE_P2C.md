# P2C — current identity state without an accumulating replay journal

Status: architectural decision and next bounded implementation assignment.
Prepared against accepted P2B head `e6511d2b3250c7517129c06c3a5fb713d91a8307`.
Verify the actual PR #14 head before starting. Work only on its clean continuation.
P2B acceptance stands; this closes its documented production limitation.

## Why this precedes P3

Identity links describe current shared mutable objects, not simulated history.
P2B correctly saves affected changes but retains every identity-delta record.
Alternately adding/removing one alias produced this independent measurement:

| Saves | Current alias links | Delta records read | Delta payload bytes read |
|---:|---:|---:|---:|
| 20 | 0 | 20 | 8,760 |
| 200 | 0 | 200 | 87,600 |

Keep the bounded save behavior while making identity storage/reconstruction
depend on current links rather than the lifetime number of edits. This is a
metadata-only probe, not another simulation benchmark.

## Selected representation

Use P1's existing current-record table. Do not add a second replay mechanism or
periodic full-World compaction to normal saves.

* Namespace: `world_identity_links`.
* Typed key: the target occurrence path, using existing tuples and typed path
  components. Do not stringify paths or use Python object addresses as saved IDs.
* Value: the owner occurrence path. Record schema: explicitly versioned `1`.
* One current record per explicit target. Insert/update the current owner, or
  delete the record when that explicit link ceases to exist.

New World snapshots use an explicit manifest mode `identity_storage =
"current-links/v1"`. The manifest has `schema`, `collections`, and
`identity_storage`; it does not also contain a base alias list. Declare the
current-link namespace in the committed head even when it has no rows. Keep
`collections/v1` live layout metadata separate as established in P2B.

Preserve the existing legacy manifest shape (`schema`, `collections`,
`identity_links`) and optional `world_identity_deltas` as a distinct compatibility
mode. Reject unknown modes and mixed current/legacy identity sources. A reader
must never silently choose one of two competing authorities.

New-format snapshots must not write or replay identity deltas. Loading their
identity metadata enumerates only current link records; full World restore still
has its existing full-state cost. Do not claim lazy loading or bounded World
memory from this change.

## Mutation and atomic publication

Reuse the reviewed occurrence/reverse-ownership index. Rescan only affected
owners and their actual shared-identity dependencies; no World or global alias
rediscovery on save. Keep parent/descendant sharing and canonical path-anchor
changes correct.

Reduce pending edits to the final state per target before constructing P1
changes. If a target is removed and re-added with a different anchor in the same
save, emit its final upsert, not duplicate writes or a replay-order dependency.
Likewise, cancel a transient create/remove when the target was absent at the
committed baseline. Preserve pending changes across failed commits and resolve
lost acknowledgements without inventing another generation.

Alias records, owning World records, live collection descriptions, counters and
save head publish in the same P1 transaction. P1's protected counts/checksums
remain in force. Do not change transaction mode, durability, receipts or P1's
generic record format for this work.

Restore must validate path types and boundaries, check payload copies before
relinking, restore ancestors/descendants correctly, and verify the resulting
identity graph. Reuse the existing reviewed checks rather than weakening them.

## Compatibility and explicit conversion

Keep existing legacy P2A/P2B reads and continuation supported. Legacy binding may
retain its compatibility writer; clearly identify that mode and its replay cost.
Do not silently mutate or migrate a user's source database merely by reading or
binding it. The new default for the opt-in `write_snapshot` API is current links;
the ordinary game checkpoint API remains unchanged.

Provide an explicit conversion entry point from a trusted legacy snapshot to a
new destination. A full read/scrub and full per-record snapshot export are allowed
for this one-time conversion. Never overwrite the sole source save or publish a
partial destination. Keep IDs, field values, insertion order, frozen EventLog
semantics, shared identity, world digest and future continuation exact. Do not
introduce a World-sized payload as a conversion shortcut.

The implementation may use existing `read_snapshot` plus new `write_snapshot`
internally. Make its full-state cost explicit and retain P2A's atomic no-overwrite
destination publication. Do not confuse converting storage with changing rules.

## Required evidence

1. Preserve all existing persistence and independent bound/unbound/restored
   controls. Test new sharing, nested parent+child sharing, cross-owner sharing,
   anchor replacement/deletion, list shifts, sealed/tail events and rebind.
2. Exercise multi-owner edits and repeated changes to the same target before one
   commit. Check the final graph, including mutation through retained aliases.
3. Alternate one alias on/off for 20 and 200 saves, including restore/rebind.
   Current-link rows must alternate between one and zero, with no delta namespace
   or history-sized identity read. A no-op save writes nothing. Report actual
   identity rows/bytes read and written, not only a helper-call counter.
4. Repeat local edits with 100 / 300 / 1,000 unrelated current alias groups.
   Incremental work/writes must follow affected owners/links, not unrelated groups.
   Preserve the structural-save bound from the final P2B review as well.
5. Fail before commit and after commit/lost acknowledgement with simultaneous
   identity and World edits. Recover old or new complete state, never a mixture.
   Include a subprocess writer-death case using existing P1 test facilities.
6. Test genuine old-format fixtures: P2A base links, P2B deltas beyond single-digit
   ordinals, and `collections/v1` overlays. Do not generate only new snapshots and
   label them legacy tests. Read, explicitly convert, compare identity/digest,
   then continue both original/restored worlds. Source stays unchanged.
7. Reject unknown/mixed identity modes, wrong namespace/schema, missing/corrupt
   link payloads, invalid paths, incompatible copied values and stale generations.
   Verify portable backup/relocation through existing P1 facilities.

SQLite file size can retain reusable free pages; do not assert that physical file
size exactly follows live row count or VACUUM after every save. Distinguish live
identity metadata, reusable database space and canonical objective history.

Run focused tests first, then one full suite on stable final code. Short real
simulation continuation is enough. Report implementation SHA, exact tested
source, counts/bytes, compatibility behavior and remaining limitations.

## Stop boundary

**P2C only, then stop for review.** No normal checkpoint replacement, disk-backed
EventLog, eviction, lazy World loading, balance changes, Stage 1, millennium,
multi-millennium experiment or merge. Preserve main and PR #5.

After acceptance, Astra should specify P3's save-session/EventLog lifetime and
failure boundaries before delegating that implementation. P4 resident-state work
and P5 integrated long-horizon validation remain necessary for Stage 0.5 freeze;
P2C alone does not establish an indefinitely playable save.
