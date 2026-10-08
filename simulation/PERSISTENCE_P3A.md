# P3A — immutable event segments and a bounded disk reader

Next bounded Sol assignment, after P2C acceptance at
`4a05ddcf6620092496c2fbdb2cb03c6621667c11`. Verify actual PR #14 head first.
Implement this storage component only, then stop for Astra review.

## Purpose and exact boundary

Move toward cold history without changing authoritative simulation behavior.
Use P1's existing transactional `segments` table and the allowlisted WorldCodec.
Build a sealed-event prefix writer/reader that P3B can compose with EventLog's
mutable tail. Do not wire it into World or replace checkpoint APIs in P3A.
This is reusable production storage machinery, not another simulation model.

Suggested module: `ate_sim/persistence_events.py`. Existing EventLog uses
2,048-event chunks, consecutive IDs starting at 1, nondecreasing years, inclusive
year queries and a four-chunk cache. Preserve those semantics.

## Storage contract

Use immutable segments in namespace `world_sealed_events`, with fixed 2,048-event
chunks and zero-based ordinal. Encode a versioned typed envelope containing the
sealed Event tuple. P1 segment metadata must agree with the payload's count and
first/last IDs. No pickle, dynamic imports or unchecked compressed object blobs.

Keep one bounded descriptor record in `world_event_storage`, keyed
`sealed-prefix/v1`: format version, chunk size, committed segment/event counts
and last event year (None when empty). Require event_count = segment_count *
chunk_size. Header counts are not proof that every cold payload has been read.

Provide an append-preparation API that returns the expected generation, bounded
record changes and new segments for P1.commit. It must not commit independently:
P3B must be able to publish World changes, tail, segments, descriptor and head in
one transaction. Reuse P1 stale-generation protection and immutable-segment
enforcement. Process a bounded batch of chunks per preparation; do not collect
an entire historical archive in one payload or an unbounded change list.

Input events must already be sealed. Reject unsealed events, mutable nested data,
wrong IDs, nonmonotonic years, partial chunks and incompatible types/versions.
Do not call seal() on caller-owned mutable events or manufacture events. Validate
continuity against the captured committed prefix; empty append is a no-op.
Check count/ID metadata against actual decoded events on reads as well.

Use only existing P1 APIs where possible. A narrow checked segment-envelope read
API may be added if needed to expose protected count/ID metadata. Do not weaken
checksums, bypass the codec, change transaction mode or redesign P1 storage.

## Reader and lifetime

Construct a read-only sealed-prefix view from a borrowed open store. Capture its
descriptor, store identity and committed generation in a short read transaction.
Do not hold a SQLite read transaction across gameplay/reader lifetime.

The captured prefix remains stable when later generations append segments: its
count never changes, and old segments are immutable. This is a view of an
immutable prefix, not a claim to pin mutable World state at that generation.
Create a new view explicitly to see an enlarged prefix.

Support len, indexed access (including negative indices), slices, iteration and
between(first_year, last_year) matching EventLog's inclusive behavior. Map indices
to segment ordinals arithmetically. A four-segment LRU owns decoded cold payloads;
opening the reader must not load every segment or build a history-sized Python
list of events/segment descriptors. Slice results may allocate the requested
result; iteration should stream.

For year ranges, use lower/upper-bound binary searches over indexed events,
followed by reading the selected range. O(log N + returned data) access is a
valid first implementation; a whole-prefix scan or copied year index is not.
Measure segment reads, including the search overhead. Do not add a broad new
indexing subsystem merely to save those logarithmic reads.

Decoded objects preserve Event, Layer, exact values, causes, frozen container
semantics and sealed status. Eviction must not thaw objects retained by callers.
Immutable value equivalence is required across reload; Python object identity
for separately decoded sealed objects is not a new persistence guarantee.

Reader.close clears its cache and releases its borrow, without closing the shared
store. A closed reader/store must reject reads even on cache hits. Do not leak
connections or silently reopen a path. Backup and relocation use P1's portable
SQLite backup. Missing/corrupt cold data raises explicitly when accessed; no
synthetic defaults or omitted history. Keep an explicit full-prefix verification
operation separate from lazy access and report which guarantee was exercised.

## Required tests and measurements

1. Compare sealed-prefix values, order, IDs, types, causes and year queries with
   existing in-memory EventLog across chunk boundaries, repeated/negative years,
   empty ranges, slices and negative indices. The mutable tail stays outside
   this component; include a source with a tail to prove it is not exported.
2. At 4 and 40 segments, opening performs no segment-payload reads. A cold point
   lookup reads one segment; a repeated cached lookup reads none. Cache occupancy
   remains <=4 after traversal, and an evicted event reloads exactly. Count actual
   reads/bytes and resident segments, not just helper invocations or wall time.
3. Verify logarithmic year-bound search plus selected-range reads. No hidden
   full archive enumeration at reader construction or append preparation.
4. Existing view remains a fixed prefix after append; a new view sees the newly
   committed prefix. Appending one chunk writes only that chunk and bounded
   metadata, independent of 4 vs 40 old segments; empty append writes nothing.
5. Before-commit failure, after-commit/lost acknowledgement, stale generation and
   subprocess writer death preserve an old-or-new complete descriptor/prefix.
   Failed/uncommitted preparation must not cause callers to discard source data.
6. Reject wrong schema, ID/count/header mismatches, chronology violations,
   unsealed/mutable input, missing segments and corrupted payloads. Corrupt an
   uncached segment: opening may succeed, its access/full verification must fail.
   Do not label lazy opening a successful full scrub.
7. Verify backup/relocation, close semantics and retained-event immutability.
   Reuse the existing test facilities rather than constructing a large harness.

Run focused P1/P2/prefix tests, then one full suite on stable code. Synthetic
sealed fixtures suffice; no millennium or endurance run. Report exact tested SHA,
tests, reads/writes/bytes, cache bounds, append atomicity and limitations.

## Stop here

No World adapter integration, normal checkpoint replacement, mutable-record
eviction, EventLog rewrite, balance changes, Stage 1, main/PR #5 edits or merge.
Do not retrofit sealed segments into existing World snapshots in this tranche.

P3B must later connect session ownership, mutable tail and atomic saves, while
ensuring P2 binding/identity discovery does not eagerly materialize or retain the
disk prefix. Detach, digest/archive export, legacy checkpoints and failed-save
recovery need explicit treatment there. P3A alone does not establish bounded
World memory or finish Stage 0.5.
