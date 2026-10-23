# Pinned owner/group occurrence source proofs

Continue the approved incremental-proof architecture after authenticated green
version-source CI39899113040. Authenticate complete bounded pages from actual
`lazy_identity_occurrence_versions`, scoped either to an exact owner or exact
incarnation. No owner-payload reads, object/key/path decoding, World activation,
new registry, main merge or endurance job.

## Choice and authority

Use the reviewed ordered proof primitive and existing physical occurrence table.
Both views represent the same raw logical placement relation. Test-only full
verified construction derives them from one frozen source. Future publication
must update both and prove payload reference projections, existing owner radix
trees, group headers, links, retirement and allocator cross-consistency. This
adapter alone does NOT prove that full topology or supply a production trust
constructor. Keep all current World checks active. Returning raw occurrence
metadata never authorizes object admission or resurrects a retired incarnation.

## Interfaces and exact bytes

Frozen `OwnerScope(namespace:str,typed_key:bytes)` and
`GroupScope(incarnation_id:int)` are the only scopes. Namespace is exact nonempty
UTF8 without NUL, typed keys/paths remain exact encoded bytes. Incarnation and
allocator fit the existing SQLite positive signed integer domain1..2**63-1.
Frozen `RawOccurrence(namespace:str,typed_key:bytes,path:bytes,incarnation_id:int)`.

`occurrence_domain(store_identity,codec_version,scope)` hashes u64-length-framed
`ate-occurrence-proof-domain/1`, store UTF8, canonical positive ASCII codec,
then scope tag `owner` plus namespace UTF8/key, OR `group` plus id as u64.
`member_commitment(domain,row)` hashes framed `ate-occurrence-proof-member/1`,
domain,namespace UTF8,key,path,incarnation u64; valid_from/to are excluded.
`group_order_key(namespace,typed_key,path)` concatenates three terminated byte
strings: each zero byte becomes00ff and each field ends0000. This is injective
and preserves SQLite BINARY order(namespace UTF8,owner_key BLOB,path BLOB), even
with embedded zeros/prefix keys. Owner positions are exact path bytes.

Frozen `OccurrenceCertificate(store_identity,generation,codec_version,scope,
next_incarnation_id,order:OrderRoot)`. Expected certificate commitment is REQUIRED
from accepted outer authority; certificate data/self-hash is not authority.
`certificate_commitment` hashes framed `ate-occurrence-certificate/1`,domain,
generation u64,allocator u64,ordered root commitment. Generation exact0..2**63-1;
group id must be below allocator. Root types/count/extrema follow reviewed rules.

`read_occurrence_page(store,pin,certificate,expected_commitment,*,after=None,
limit=128,max_metadata_bytes=1048576)->OccurrencePage`. Frozen
`OccurrencePage(rows:tuple[RawOccurrence,...],next_after:tuple[str,bytes,bytes]|None)`.
Cursor is exclusive raw(namespace,key,path), owner cursors must match owner.
Exact limit1..128; metadata budget exact1..64MiB. Field bodies(namespace UTF8,
key,path) each capped4096 encoded bytes. Larger valid fields raise distinct
`OccurrenceProofBudgetError(StoreError)` before transfer. This is an explicit
fast-path budget, requiring a separately budgeted proof path before World use.
Peak memory scales with bounded page/field limits, not entire relation/archive;
fixed small-row diagnostics use a stricter2MiB heap gate.

## Physical selection and snapshots

Reuse the existing read_snapshot and its private same-snapshot preflight for
operational metadata (including64-row inventory bounds). No arbitrary borrowed
transaction. Check context, exact live pin, current/previous generation and a
guarded unique physical identity-state interval. It must match certificate
allocator; use existing row checksum and interval checks before exposure.

Explicit `create_occurrence_indexes(db)` requires caller transaction; it never
commits, constructs roots or opens a World path. Add ordered covering indexes
for current and just-closed owner/group rows OUTSIDE ordinary open/read/save.
Creation belongs to verified-copy construction. Reads require the exact declared
index columns/partial status and fail if unavailable; never create an index on
first access or silently sort an entire group. Owner current may reuse the
existing current owner index. Current streams use valid_to NULL; previous
streams merge at most limit+1 current-open and valid_to=pin+1 rows with seeks.
Explicit row ordering is path for owners, namespace/key/path for groups.

Validate every fetched row including neighbors before trimming: SQL storage
classes/lengths before transfer, exact64-byte TEXT checksum length as BLOB bytes,
valid interval and0<incarnation<allocator, scope and existing occurrence checksum.
An expiry-aware exact placement probe LIMIT2 must prove physical interval
uniqueness even for group rows, where a duplicate may name a different group.
Construct page adjacency from real immediate predecessor/lookahead. Empty/end
pages require authenticated last-entry boundary. Verify returned entry values,
adjacency/count/extrema against accepted OrderRoot before returning metadata.
No exclusions before verification; no integrity-error fallback.

## Tests, measurements and next gates

Independent framing/order vectors including zero/prefix keys and Unicode;
real owner/group pages/cursors/empty scopes; same raw relation agrees both ways;
old/current pins after reassignment/deletion; foreign/released/stale pins;
bad expected context/allocator, missing/surplus/coherently changed rows, overlaps
hidden behind LIMIT or in another group, false empty, endpoints/lookahead faults;
large malformed BLOB/TEXT early-NUL guards and operational metadata;
owned/nested/arbitrary transactions; missing/wrong indexes and construction
transaction ownership. Tests use full verified source construction outside read
timers, not a production certificate builder.

At1k/10k/100k unrelated actual occurrence rows, hold requested alias fanout8,
owners4, page4 and affected owner paths2 fixed. Compare raw page to checked
existing source/literals. Zero owner/history payload SELECT/checks/decodes,
<=512 proof-node reads and<2MiB traced Python heap for each fixed page. Report
construction and RSS separately; inspect plans for ordered index seeks without
temp B-tree. No World point-edit save or mature speed claim. Future complete
topology, large-key path, manifests/retention, atomic publication and World
consumption remain mandatory before interactive measurements.

## Review correction: interval capabilities and newer candidate work

Both exact-placement and allocator interval indexes must match their canonical
complete definitions, and the live store must advertise both usable capabilities.
The legacy _interval_rows compatibility fallback is forbidden for this reader.

An old-pin current stream must NOT apply valid_from<=pin as a SQL filter after
its ordered seek: newer rows could cause an unbounded scan before LIMIT. This
fast path instead fetches at most limit+1 ordered candidates without a visibility
filter, validates their metadata, and raises OccurrenceProofBudgetError if a
legitimate head-generation placement intervenes. Closed-stream candidates are
also fetched without a hidden start filter, so malformed intervals are rejected
after bounded candidate transfer. No partial page or unchecked fallback is
returned. Previous-pin pages remain supported where newer candidates do not
intervene. A general bounded certificate-checked previous-pin selection path is
STILL REQUIRED before World adoption, alongside the large-field path. This is an
explicit fast-path limitation, not complete production old-pin support.

Diagnostic extension: record instrumented SQLite VM upper bounds, measure exact
previous-pin group/owner pages, and populate a formerly empty old group with
1k/10k/100k new head placements. The old empty query must explicitly reject with
<20000VM steps at each size. Genuine large transition setup is outside that
read timer. SELECT counts/no-temp-sort plans alone do not prove bounded work.
