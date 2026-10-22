# Proof transition inputs

This implements the next bounded portion of package C in the approved
[incremental-proof architecture](2026-10-21-ate-incremental-proof-design.md).
The user wants fixed small changes to avoid irrelevant history, while preserving
exact state, identity, order, RNG and recovery. No new World format is activated.

## Batch map transition

Repeated `ProofMap.set` currently persists transient ancestors for each key.
The 100k diagnostic retains 546696 nodes / 358686720 bytes. Final-path batching
is preferable to an unbounded Python overlay or accepting that write amplification.

Provide `update_sorted(proof_map, root, changes) -> Root` in a focused module.
Each change is `(exact_typed_key: bytes, commitment: bytes | None)`; `None`
deletes. Input must be strictly increasing by the existing domain-specific
`key_locator`, with duplicate locators rejected. The caller supplies a bounded
sorted stream, using SQLite spill when necessary; this function never sorts or
materializes the entire delta. The caller owns atomic rollback if a later input
or callback fails. No logical head is published by this helper.

Merge the sorted delta with compressed radix subtrees. Untouched child roots
are reused without visiting their leaves. Read each affected old node once
through existing hash/count/inherited-prefix checks; validate a surviving
unchanged child before deletion promotes it. Keep at most one lookahead change
and at most 64 radix levels of 16 child references. Write only nodes reachable
from the final returned root, once each. No persistent clean-node cache or
second canonical-object registry. Empty/no-op batches return the original Root
object and write nothing. Preserve the canonical root produced by sequential
set for the same final mapping, including all-deletion and absent-deletion cases.
Errors propagate; old roots remain usable. A callback or invalid stream may have
written orphan immutable nodes, which must be rolled back by the caller.

## Exact content commitments

Provide pure key/commitment helpers for the existing physical source families.
All commitments are SHA-256 over unsigned 64-bit length-framed parts, using
distinct `ate-proof-content-<family>/1` and `ate-proof-key-<family>/1` tags.
Namespace is exact UTF-8, nonempty and without NUL; typed keys, payloads,
membership encoding and event boundary IDs are exact bytes. Integer fields are
exact non-bool integers encoded as canonical ASCII decimal, nonnegative except
codec/schema/count fields which must be positive. Do not decode or normalize
typed values, floats/NaNs, membership order, duplicate entries or event IDs.

| Family | Logical key parts after key tag | Commitment parts after content tag |
| --- | --- | --- |
| version | namespace, typed_key | namespace, typed_key, valid_from, codec_version, record_schema, memberships, payload |
| record | namespace, typed_key | namespace, typed_key, last_changed_generation, codec_version, record_schema, payload |
| segment | namespace, ordinal | namespace, ordinal, created_generation, codec_version, element_count, first_id, last_id, payload |

Logical keys return the framed bytes, not a second hash; ProofMap derives the
locator. Commitments return 32 bytes. Hash payload parts incrementally without
constructing a second full-size frame. Version `valid_to` is deliberately not an
input: interval closure must not invalidate retained old-pin content. Existing
mutable interval checks stay authoritative until manifest-based selection and
interval transitions are implemented. A leaf commitment alone is insufficient
to authorize an SQL interval result or a complete query.

These helpers do not check a persisted checksum field instead of the payload,
select a codec, decode data, fetch rows, retain bytes or confer admission.
Ordinary `records` are overwritten in today's store; a root is not a backup of
those bytes. Before proof authority, migration/retention must provide the exact
ordinary-record versions needed by retained roots, not just retain proof nodes.

## Acceptance and remaining integration

Seeded mixed batches must match an independent dictionary and canonical
sequential roots, while retaining old snapshots. Tests cover malformed stream,
path/count/bytes corruption, missing nodes, deepest valid paths, callback faults,
SQLite rollback/savepoints, final-only writes and bounded point reads.
Content helpers get independently framed vectors and one-field-at-a-time
tamper/domain/type checks, including opaque typed bytes and payload-size memory.

An actual SQLite 1k/10k/100k batch construction diagnostic must retain only final
reachable nodes from each accepted checkpoint (no transient intermediate roots).
Report sorting/spill work and peak memory separately from point update work.
No deletion/GC is authorized before manifest/pin/receipt reachability exists.

Next packages must define complete topology/group/owner and ordered query
commitments; generation manifests; root AND payload retention; explicit verified
copy; old-writer fencing; atomic changed-row/root/receipt publication; World
save/open consumption; canonical lazy action admission; scrub and actual mature
equivalence. Current targets remain open <=10s, incremental save <=2s and warm
year <=1s. Primitive timings do not establish any of those targets.
