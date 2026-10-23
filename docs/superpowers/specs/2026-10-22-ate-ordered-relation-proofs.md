# Ordered relation proofs

This is the next package C prerequisite in the approved incremental-proof
architecture. The user wants small saves to reuse committed integrity evidence
without reading irrelevant history, preserving exact identity/state/order/RNG.
It implements complete ordered relation certificates and verified local
transitions, usable by query and alias-group projections. World authority,
manifest publication, physical source adapters and cross-projection validation
remain subsequent integration work. Existing readers/checks remain active.

## Decision

Extend the existing immutable hashed ProofMap with authenticated predecessor and
successor commitments. This reuses the reviewed bounded map rather than adding
a second ordered tree or sorting the whole relation for every page. A page of
positive membership proofs alone is insufficient: it can omit rows. Adjacency
and authenticated range boundaries establish a complete contiguous result.

Trust starts at a fully checked construction and then verified transitions.
An arbitrary caller-created root/digest is not proof of global linked-list
consistency. The eventual generation manifest/directory must authenticate the
descriptor commitment. No boolean `already_validated` admission flag.

## Exact representation

`OrderEntry(key: bytes, value: bytes, previous: bytes | None, following: bytes | None)`
binds an exact ordered position, a 32-byte source commitment, and immediate
neighbors. Keys compare as raw byte strings, strictly increasing. Empty byte
keys are legal and distinct from absent endpoints. No decoding/normalization.

`OrderRoot(index: Root, first: bytes | None, last: bytes | None)` binds the map
root/count and extrema. Empty roots must equal the domain's exact empty root
with both endpoints None. One entry requires equal endpoints; larger relations
require first < last. The descriptor is not independent checkpoint authority.

Use SHA256 over u64-length-framed parts, matching existing map framing:

- entry: `ate-proof-order-entry/1`, map_domain, key, value, previous-presence,
  previous-key, following-presence, following-key.
- root: `ate-proof-order-root/1`, map_domain, index.digest, count as unsigned
  8-byte big-endian, first-presence, first-key, last-presence, last-key.
- presence is exact `b'0'` for None (key part b'') or `b'1'` for bytes.

All types are exact, counts <=2**64-1. Entry pointers must satisfy
previous < key < following when present. Root commitment binds domain and all
descriptor fields. Invalid proof inputs raise StoreIntegrityError.

`query_order_key(ordinal, typed_record_key)` is unsigned 8-byte big-endian
ordinal followed by exact typed key bytes, for 0 <= ordinal <=2**63-1. This
matches current SQLite `ORDER BY ordinal,record_key`, allowing repeated record
keys at different ordinals and ordinal ties broken by typed bytes. Duplicate
exact positions remain invalid. Other relations supply an explicitly specified
order encoding; do not apply query order encoding to identity paths by guess.

## Page verification

`verify_page(map, root, expected_commitment, *, rows, after=None, before=None,
limit=128, boundary=None)` returns an immutable tuple of the authenticated
OrderEntry objects. expected_commitment must come from the accepted outer
manifest/directory. This function verifies it against the supplied descriptor.
after/before are exclusive byte bounds; None is unbounded. limit is an exact
integer in 1..128; at most limit rows may be consumed (reject limit+1 without
materializing an unbounded input). Reversed/equal finite bounds return an empty
result only if no rows/boundary were supplied.

Authenticate each entry against its map leaf commitment. Verify strict order,
range, reciprocal adjacency inside the page and endpoint claims. The first
row's previous must be None (and row==first) or <=after, proving no earlier
qualifying row was omitted. If after is None, previous must be None. Every
following=None requires key==last and every previous=None requires key==first;
conversely extrema cannot claim a neighbor beyond the relation.

A short page must end the range: following=None or following>=before. A full
page may have a following entry inside the range; its authenticated pointer is
the continuation boundary. Surplus, repeated, reordered and omitted rows fail.

An empty page on a nonempty relation needs one authenticated boundary entry:
either key<=after and following is absent or >=before, or key>=before and
previous is absent or <=after. This proves the requested interval is empty.
Empty whole-range results on a nonempty root always fail. Empty root needs no
boundary. Do not silently accept an unused/surplus boundary witness.

Query exclusions are applied only AFTER verifying contiguous raw pages. To fill
a limited filtered result, verify further raw pages as required. Filtering SQL
results before proof verification would disguise omissions. Limit zero is a
caller-level no-row operation, not a proof page. No payload decoding or object
exposure occurs in this helper.

## Checked construction and transition

`build_ordered(map, db, rows)` accepts strictly order-key-sorted `(key,value)`
pairs, validates shape/types/duplicates, constructs links with bounded lookahead,
spills locator-sorted map changes into SQLite TEMP storage, calls update_sorted
once and returns OrderRoot. Count/extrema derive from the consumed source, not
caller assertions. All source rows must be validated by the explicit import
before calling this construction primitive.

`OrderEdit(key, value_or_None, old, previous, following)` describes a parent-state
edit. For an existing key, old must authenticate and both immediate parent
neighbors must be supplied/authenticated when present, with reciprocal links.
For an insertion, prove the key absent and authenticate the immediate gap
endpoints, including first/last/empty bounds. All witnesses refer to the SAME
parent root, even for adjacent edits. An absent deletion is a no-op with no
old/neighbor witnesses. A value replacement preserves order. Reordering is an
explicit old-key deletion plus new-key insertion; no implicit identity merge.

`update_ordered(map, db, root, expected_commitment, edits)` consumes strictly
order-key-sorted edits once. Stage authenticated parent entries, boundary keys,
edits and final locator-sorted changes in SQLite TEMP tables. Duplicate parent
witnesses must agree; their successful admission may be reused within this
one batch only. Ghost boundary keys carry no authority and never get map leaves.
They prevent disjoint affected intervals being incorrectly joined.

After applying insert/delete/value changes in the staging inventory, derive
final neighbors by ordered predecessor/successor over the staged live keys.
Every directly affected neighbor was authenticated; untouched outer neighbors
remain ghost boundaries. Update only actual entries and edits, never ghosts.
Seed old extrema so new extrema derive correctly for head/tail/all-deletion
cases. Check expected cardinality against the resulting map root. Reuse the
existing final-path batch updater. Empty/no-op transitions preserve root object
identity and write zero proof nodes.

Both functions REQUIRE an existing caller SQLite transaction, never begin,
commit, choose a head, collect nodes or publish a second generation. Temporary
staging is disposable and removed on exit. Late stream/callback/SQL faults
propagate; caller rollback restores all immutable writes. Accepted old roots
remain usable. SQLite spill/caches are caller-budgeted; no whole Python relation
or delta dictionary, retained clean-node cache or second object registry.
Python residency follows radix depth, bounded page size and largest individual
input key/witness; unusually large keys must be charged by source adapters.

## Integration contract and gates

The certificate binds logical membership/order. A future physical adapter must
bind actual fetched row bytes/interval selection and complete source reference
projections; it must not treat SQL row presence as authority. Owner/group/link
cross-consistency, retirement/absence, allocator bounds and canonical alias
admission remain required before topology authority. This package alone does
not implement complete World topology.

Relation values must bind the relevant membership/reference fact. Do not bind
an unrelated scalar payload into a topology/query value and thereby invalidate
an unchanged relation on every content edit. Exact payload bytes belong to the
separate content root. Physical source adapters must define these bindings and
their canonical ordering explicitly before the certificates become authority.

Required tests: independent framing vectors; SQL-compatible query order with
ties/repeated record keys; page omission/surplus/reorder/false absence and forged
boundaries/descriptors/domains; old/new-root distinction; local mixed transitions
including adjacent/disjoint edits, all deletion, reinsertion/reordering; corrupt
or inconsistent old/neighbor witnesses; lazy stream/callback failure rollback;
no-op writes; independent full-rebuild equality after seeded transitions.

Hold changed keys/fanout fixed against 1k/10k/100k unrelated entries, measure
node reads/writes and zero relation-payload reads, then verify pages against
independent ordered results. This is an ordered-proof diagnostic, not a World
save or one-second-year result. Root/payload retention, manifests, upgrade,
writer fencing, atomic publication and actual World consumption remain gates.
