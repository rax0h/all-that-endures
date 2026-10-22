# Durable proof map node contract

Status: implementation contract for the first part of package C in [Astra's approved design](2026-10-21-ate-incremental-proof-design.md). No reader capability is enabled by this document. Complete generation manifests, query/order authority, migration and save/open consumption remain separate required work. The existing format-6 reader remains authoritative until those pieces are integrated and tested.

## What this primitive establishes

A root commits to a finite mapping from exact encoded key bytes to 32-byte value commitments. It supports membership and absence, immutable path-copy insert/replace/delete, a complete traversal, and verification of every node fetched. It does not encode World objects, own canonical identities, authenticate an SQL query's order, or replace a canonical World digest.

Use a compressed hexadecimal radix tree over 256-bit key locators. A locator is SHA-256 of the length-framed map domain and exact existing typed key bytes. Hashing changes only the lookup path; the source codec's bytes and distinctions remain authoritative. Reject duplicate locators for different exact input keys during verified construction rather than silently merging them. This relies on SHA-256 collision resistance, as the existing checked store already does.

## Canonical bytes

`frame(parts)` concatenates each part preceded by its unsigned 64-bit big-endian byte length. Hash domains are literal ASCII bytes. Value commitments and node digests are 32 raw bytes, not hex text. An external JSON receipt may render them as lowercase hex without changing their hashed representation.

- Locator: `SHA256(frame((b'ate-proof-map-key/1', map_domain, typed_key)))`.
- Empty root digest: `SHA256(frame((b'ate-proof-map-empty/1', map_domain)))`; count 0, no stored node.
- Leaf bytes: `b'ATEP' + b'\x01L' + locator + value_commitment`; count 1.
- Branch bytes: `b'ATEP' + b'\x01B' + prefix_length_u8 + packed_prefix + child_count_u8 + children`.
- `prefix_length_u8` counts hexadecimal nibbles (0..63). Pack two nibbles per byte, high nibble first; an odd final low nibble must be zero. `packed_prefix` has exactly `ceil(prefix_length/2)` bytes.
- Each child is `slot_u8 + count_u64_be + digest_32`. There are 2..16 children, strictly increasing slots 0..15. Child counts are positive; their sum is the branch count. A single child is compressed away; empty branches are absent.
- Node digest: `SHA256(frame((b'ate-proof-map-node/1', map_domain, node_bytes)))`.

A node is at most 696 bytes (6-byte tag, length byte, at most 32 prefix bytes, child-count byte and 16 41-byte child entries). Reject trailing bytes, wrong domains/tags, malformed lengths, noncanonical padding, repeated/unsorted slots, zero counts, count overflow and branches beyond locator depth. A node's advertised count must equal its checked contents and the parent/root reference. Counts describe SQLite rows and fit unsigned 64 bits; this does not narrow simulation counters or source values.

A child leaf's locator or branch prefix must extend the parent prefix through its selected slot. Check this whenever that child is fetched. A traversal also checks unique leaf locators and its total count. Construction and scrub validate the complete reachable graph; point admission validates its path against an accepted root. No proof promises to discover fresh corruption in an unread descendant.

## Interfaces and storage

Keep this module independent of `WorldCodec`, native records and identity registries. `Root(digest: bytes, count: int)` identifies a map within a separately supplied `map_domain: bytes`. A zero-count root is accepted only if its digest equals this domain's exact empty-root digest. `get(root, typed_key)` returns the bound commitment or authenticated absence. `set(root, typed_key, commitment_or_none)` returns a new root; `None` deletes. Same-value set and absent-key delete return the exact original root without writes. The caller holds a stable SQLite read/write snapshot for a multi-node operation.

Persist nodes in a private SQLite table keyed by `(map_domain, digest)` with canonical bytes. Store a node only after checking its digest/shape; a repeated key with different bytes is an integrity failure, not replacement. The adapter must join a caller-owned transaction and never commit it. New or existing nodes from a rolled-back transaction confer no reusable runtime authority.

Use no full-map Python dictionary. Point update loads only its checked search path and at most one surviving child when compressing a deletion. Maximum search depth is 64 branches plus a leaf. Shared paths may be reused within a bounded batch; clean-node cache bytes, dirty nodes and scratch/spill buffers must be reported separately. Initial construction may stream into the SQLite workspace and pay a full verified scan once. Do not garbage-collect nodes until the future root-retention contract exists; retaining extra immutable nodes is safer than breaking old pins.

## Integration boundaries that must remain explicit

This map alone does not make any existing check redundant. Before a format-7 store can be published, the following need their own contracts and tests:

1. Immutable content-leaf bindings, excluding mutable interval-close fields so old-pin content roots remain stable. Fetched rows still require exact payload/version/codec binding and interval-selection checks.
2. Separate topology roots binding complete owner/group placements, retirement and absence. A payload update must prove its reference projection agrees with unchanged topology.
3. Complete query/order commitments, including ordered pagination, duplicate/reinsertion behavior and omitted/surplus-result rejection. An unordered hashed map's positive membership proofs do not establish a sorted range.
4. Generation manifests binding store identity, schema/rules/codec, head/allocator/counters, content/topology/query/event roots, and the exact existing commit token/recovery receipt. Data and roots publish in the existing single SQLite commit.
5. Verified copy upgrade, old-format routing, old-pin root retention and bounded recovery/maintenance. No in-place unverified capability flip.

Acceptance for this primitive is deterministic authenticated lookup/update behavior and bounded path work at 1k/10k/100k keys. Mature timing and interactive performance remain acceptance for later consumption packages.
