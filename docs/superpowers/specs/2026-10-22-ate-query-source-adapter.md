# Pinned query source adapter

Implement the first physical source consumer for the approved proof architecture:
authenticated pages over actual `lazy_query_versions` rows. The user wants to
stop rereading unchanged owner/history payloads merely to validate query results.
Preserve exact ordering, duplicate record positions, retained pins and fetched
row checks. No existing World reader/publisher or format capability selects this
adapter until accepted manifests, source/content/topology consistency and atomic
publication exist. This package is not a complete save integration.

## Trust and exact bindings

Frozen `QueryScope(namespace: str, index_name: str, index_value: bytes)` stores
the EXACT already-encoded query value. Nonempty namespace/index names are exact
UTF8 text without NUL. No payload/key decoding occurs in the read adapter.

`query_domain(store_identity, codec_version, scope)` returns SHA256 over existing
u64-length-framed parts: `ate-query-proof-domain/1`, UTF8 store identity, codec
version as positive canonical ASCII decimal, namespace UTF8, index-name UTF8 and
the exact encoded index value. Generation is excluded so unchanged logical
relations can reuse the same subtree in later verified transitions.

`member_commitment(domain, typed_record_key, ordinal)` hashes framed parts
`ate-query-proof-member/1`, domain, exact record-key bytes and ordinal as unsigned
8-byte big-endian (0..2**63-1). It binds membership, not unrelated owner content.
Positions use existing `query_order_key(ordinal, typed_record_key)`.

Frozen `QueryCertificate(store_identity: str, generation: int, codec_version:
int, scope: QueryScope, order: OrderRoot)` is DATA, not admission authority.
`certificate_commitment(certificate)` hashes framed `ate-query-certificate/1`,
domain, generation as unsigned8 bytes, and the ordered root commitment. Reader
requires this expected commitment from accepted outer authority; computing a
digest from arbitrary local rows does not authenticate a new checkpoint. Full
copy/import validation must establish owner/query completeness before anchoring
the certificate. No `already_validated` flag or product builder that silently
certifies unchecked SQL results is added.

## Reader

`read_query_page(store, pin, certificate, expected_commitment, *, after=None,
limit=128) -> QueryPage` uses the store's existing bounded read snapshot.
`QueryPage(positions: tuple[tuple[bytes,int],...], next_after:
tuple[int,bytes]|None)` returns raw typed keys plus ordinals; after cursors are
`(ordinal,typed_key)`, exclusive. limit is exact1..128. Return a next cursor only
when the authenticated final row has a successor. Empty page has no cursor.

Validate certificate fields/context, expected commitment, same store/codec and
exact pin generation before consuming source rows. Use `_require_pin`, checked
head and retention through the existing snapshot, never a separate reader
transaction lasting a gameplay step. Support current and previous retained
generation; released/stale/foreign pins fail. Do not mint reuse certificates in
an arbitrary borrowed transaction; existing `read_transaction` nesting remains
supported through its explicit ownership flag.

Read scope rows ordered by ordinal,record_key, at most limit+1 for page and
successor. Current generation uses the current-row index. Previous generation
merges bounded current-open and immediately closed streams, preserving the
existing two-visible-snapshot contract. Old query rows must also satisfy
valid_from<=generation. Use parameterized tuple seeks, never caller SQL.

Validate exact row key/integer/interval types and the existing `_query_checksum`
for EVERY fetched row, including neighbor lookahead. Detect duplicate visible
positions across intervals/streams. Every fetched position, including lookahead
and boundary rows, requires exactly one visible interval from the existing
expiry-aware exact-position interval witness (constant SELECT, limit2); limited
ordered streams alone cannot establish physical interval uniqueness. Read one immediate predecessor for the page
beginning; if empty, authenticate a last-entry boundary and its predecessor.
Construct OrderEntry values from these physical rows and call `verify_page`.
Missing/malformed/surplus/reordered results, false absence, changed neighbors,
wrong roots/domains and invalid intervals fail closed. Never catch integrity
errors to return a result from the old path.

Guard SQLite storage classes and byte lengths BEFORE transferring key/checksum
bodies. This initial proof-page path supports individual encoded keys up to
4096 bytes, keeping both129-row old-pin streams below the page metadata budget.
Larger keys raise distinct QueryProofBudgetError (StoreError), not an integrity
verdict. They require a separately budgeted, certificate-checked source path
before World adoption; an unchecked legacy fallback must not swallow corruption.
The default legacy reader is unchanged. Stored checksums must be exact64-byte
TEXT; length is measured as BLOB bytes so early NUL cannot bypass the guard.

The reader selects NO `lazy_record_versions`, `records` or `segments` payloads.
Accepted query proofs establish logical membership; actual owner/content bytes
must be authenticated before any eventual object admission. A deleted/corrupt
unread owner payload is not discovered by this metadata operation; full audit
and fetched-payload admission remain necessary. Returning raw metadata here is
not permission for World to expose unverified objects.

## Validation and integration boundary

Use actual LazyRecordStore fixtures created through its commit API. Test roots
are built in test utilities only, after `store.verify_all()` in the same frozen
fixture transaction; that full scan is explicit construction, not timed query
work. Test source projection completeness, exact typed values (numeric keys,
duplicates, NaN encoding bytes), old/new generation separation, direct SQL row
corruption/deletion/insertion, overlap and endpoint failures. No ordinary open
or save calls this fixture construction path.

Measure 1k/10k/100k unrelated ordinary archive payloads with active query owners,
membership positions, limit and alias fanout fixed. Report both the existing
checked query and the proof reader against the same source/results, including
payload-check counters and SQL table reads. New reader must perform zero owner
or archive payload SELECTs/checks, with bounded proof metadata/heap. These are
real store-schema query measurements, not mature World/save/year latency.

Physical owner/group/link and namespace order adapters, content admission,
manifests/root-payload retention, verified-copy writer fencing and atomic
row/root/head/receipt publication remain mandatory before World activation.
