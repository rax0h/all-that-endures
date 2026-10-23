# Pinned immutable version source adapter

Continue the approved incremental-proof architecture after the green physical
query adapter. Query membership does not admit bytes. Add a closed operation
authenticating one actual `lazy_record_versions` row against an externally
accepted content map. Existing World readers and writers remain unchanged.

## Scope and choices

Reuse the current store, codec, pin, read snapshot and exact content preimages.
Read raw encoded bytes only; do not decode objects or memberships, establish
identity/topology completeness, build production certificates, or advertise a
new format. Ordinary records overwrite their payloads: this operation covers
only retained versioned rows, not ordinary records or segments. Their retention
contracts remain unresolved. No main merge or endurance job.

An independent content adapter is the smallest sound next step: using the
existing checked decoder would not authenticate against durable roots, while
activating World before topology/manifests/publication would trust incomplete
authority. This choice follows the previously approved architecture; it is an
implementation choice, not a newly approved gameplay or format change.

## Exact interfaces and framing

Frozen `VersionCertificate(store_identity:str,generation:int,codec_version:int,
content:Root)` is data, not authority. `version_domain(store_identity,
codec_version)` is SHA256 of u64-length-framed parts
`ate-version-proof-domain/1`, exact UTF8 store identity, positive canonical
ASCII codec version. `certificate_commitment(certificate)` hashes framed
`ate-version-certificate/1`, domain, generation as u64 big-endian and content
digest/count (count as u64). Generation must be an exact int in 0..2**63-1;
root shape/count must satisfy ProofMap's contract, including exact empty root.

Content map keys and values are the existing `version_key(namespace,typed_key)`
and `version_commitment(namespace,typed_key,valid_from,codec_version,
record_schema,memberships,payload)`. No interval-close fields are included.
Callers must supply the expected certificate commitment from accepted external
authority; a matching self-hash alone is not authority. Until a fully verified
copy/manifests/transitions exist, construction is test-only after full verify.

`read_version_bytes(store,pin,certificate,expected_commitment,namespace,
typed_key,*,expected_record_schema,max_bytes=1048576,
max_metadata_bytes=1048576)->RawVersion|None` returns
frozen `RawVersion(payload:bytes,memberships:bytes,record_schema:int,
valid_from:int,valid_to:int|None)` or authenticated absence. No returned raw
value is permission to expose a World object without canonical identity
admission and reference/topology checks. Validate exact bytes/text/integer
types, store/codec/pin context, positive expected schema, and positive exact
max_bytes <=64MiB before SQL. Keys are already encoded. No arbitrary SQL.

## Snapshot, physical selection and budgets

Own or join the existing explicitly owned bounded read snapshot; reject an
arbitrary borrowed transaction. Check live pin and retained head through that
snapshot; support only the store's current/previous generations. One expiry-aware
exact-key interval query with LIMIT2 checks uniqueness across all visible
intervals, not merely optimized current rows. Read at most two guarded rows;
never scan unrelated payloads or order/query/history relations.

SQL must check storage classes, exact64-byte TEXT checksum lengths measured as
BLOB bytes, and combined payload+memberships byte length before transferring
bodies. Non-BLOB bytes, malformed integers/checksums, invalid validity intervals
and overlapping versions fail closed. Oversized valid BLOB bodies raise distinct
`VersionProofBudgetError(StoreError)` before transfer, not an integrity verdict.
The caller may explicitly increase the bounded budget for large real records;
no unchecked fallback or silent unlimited materialization. Two guarded rows plus
proof frontier bound the operation. Report metadata and payload checks separately.

For a present row, enforce valid_from<=pin<valid_to (if closed), codec/schema,
existing exact payload/row checksums and exact content leaf commitment. Preserve
the existing `_payload_check_reads/bytes` attribution for the one fetched row.
For a missing row, the accepted content map must also prove absence; for a
surplus row the leaf must be absent and the operation must reject. It does not
read query/order to establish dangling links: eventual accepted topology is a
separate mandatory contract. No stale authority survives rollback/external writes;
each operation rereads and verifies its fetched rows/nodes in one snapshot.

## Gates and remaining work

Test independent frames; exact raw bytes; old/current pins after mutation/delete;
released/foreign/stale pins; wrong store/codec/schema/authority/root; absent,
missing/surplus/coherently rechecksummed rows; overlaps; corrupt proof nodes;
malformed and multi-MiB bodies rejected before transfer; owned/nested snapshots;
read failure leaves caller transaction intact; unread unrelated corruption is
left for a later fetch/full scrub. Real store test construction uses full verify
outside read timing and SQLite spill to avoid full Python content maps.

At1k/10k/100k unrelated versioned rows, fetch one fixed record and prove one fixed
absent key. Assert exact results, one payload check for presence/zero for absence,
zero unrelated table/payload access, <=256 node reads and <2MiB traced heap for
the fixed small record. Report full proof construction separately. This is not
a point-edit save, World open, warm-year or mature performance acceptance.

Physical owner/group/link and namespace adapters, large query-key path, complete
manifest root/payload retention, verified-copy writer fencing, atomic existing
row/root/head/receipt publication, canonical object admission and actual save/open
consumption remain necessary before the user-visible speed measurements.

## Review correction: complete snapshot metadata envelope

The raw operation also budgets inherited operational metadata before transfer.
A narrow optional private snapshot preflight runs after BEGIN and before pin/head
fetches (also for nested snapshots). It transfers constant-size type/length facts
for head fields and at most MAX_PINS+1 rows of each operational inventory. Exceeding
the existing MAX_PINS64 capacity or malformed64-byte checksum storage fails closed.
Head blobs, pin text, commit-token blobs and state/outcome text share an explicit
max_metadata_bytes budget (default1MiB, configurable exact1..64MiB). Large valid
metadata can request a larger budget; no new format limit is silently imposed.
Encoded transfer limits are distinct from codec object inflation/native SQLite
memory. Fixed small-fixture heap gates do not promise2MiB heap for all legitimate
64MiB payload/metadata budgets. Existing validators still establish checksums,
lineage, retention and semantic state; the preflight creates no new authority.
