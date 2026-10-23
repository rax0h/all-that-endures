# Root-selected ordered access for retained generations

Continue the approved durable-proof architecture after accepted occurrence
CI39909955729. Resolve the arbitrary-newer-candidate scan/rejection problem by
selecting exact committed positions directly from an immutable ordered root,
then checking physical rows by exact placement. No current World reader/writer,
format capability or canonical registry changes. No merge or endurance.

## Chosen access path

The existing hashed ProofMap proves membership but cannot seek an arbitrary
lexical cursor. Persisting all rows once per generation would make local saves
rewrite whole scopes. Instead use a compressed radix tree over exact byte keys,
with immutable domain-separated nodes and path-copy updates in the caller's
existing SQLite transaction. This is proof/index metadata, not a second World,
identity registry or publisher. Roots must eventually publish with existing
row/head/receipt transactions. Retain every old node; collection remains gated.

## OrderedSeekMap contract

New `persistence_proof_seek.py`: `OrderedSeekMap(db,domain)`; caller-transaction
`create_schema()`, `set(root,key,commitment_or_none)->Root`, `build(sorted_rows)`;
`page(root,*,after=None,limit=128)->tuple[(bytes,bytes),...]` (exact1..256 limit),
`get(root,key)->bytes|None`, `verify(root)`, diagnostics/reset. `Root` reuses the
existing digest/count type but distinct empty/node domains and a private table
prevent interpreting it as a hashed-map root. Keys exact bytes <=32768; values
exact32-byte commitments. Empty bytes are a valid key; None is absence/cursor.

Keys become an order-preserving symbol string: each high/low hex nibble becomes
its value+1 (symbols1..16), followed by0 terminator. Thus a key precedes all its
extensions. Leaves store exact key/value; branches store maximal shared symbol
prefix and2..17 strictly sorted child(slot,count,digest) references. Prefixes
contain symbols1..16 only; slot0 is the terminator. Nodes are canonical for a
logical mapping, independent of insertion order. All counts fit u64.

Exact bytes: leaf `ATES\x01L + key_length_u32be + key + commitment32`;
branch `ATES\x01B + prefix_length_u32be + prefix_symbols + child_count_u8 +`
each `slot_u8 + count_u64be + digest32`. Empty digest is framed SHA256 of
`ate-ordered-seek-empty/1`,domain; node digest uses framed
`ate-ordered-seek-node/1`,domain,raw. Maximum raw node131072 bytes. Reject malformed
tags/padding/lengths/counts/slots/prefixes/trailing bytes and missing/corrupt/wrong
domain nodes. Check every fetched node's count and required parent prefix.

Storage table `ate_ordered_seek_nodes(domain,digest,raw)` keyed by domain/digest.
Before transfer, SQL guards raw BLOB storage/length. Inserts are immutable,
conflicting bytes fail, no independent commit. Same-value/absent delete returns
the original root with zero immutable writes. Initial sorted construction is an
explicit full operation; no full Python mapping or retained clean-node cache.
Point updates spill ancestor node bytes to a temporary SQLite path table, then
unwind one node at a time; no Python archive/path dictionary. Late failures
require caller rollback, preserving accepted old roots.

Seek is iterative with at most one candidate successor subtree, not a complete
Python traversal stack. Compare compressed prefixes to the cursor; descend a
matching slot or the smallest greater child, remembering the nearest greater
sibling. A page repeats strict successor search, bounded by page size and actual
key-prefix depth rather than unrelated physical generations. No recursion limit
or retained Python path stack. Full verify enumerates bounded pages, checks
all reachable leaves and count, outside ordinary reads. Work is not universally
O(1): real prefix depth/key bytes/page size matter.

## Occurrence integration

New `persistence_proof_occurrence_seek.py`: frozen
`SeekOccurrenceCertificate(store_identity,generation,codec_version,scope,
next_incarnation_id,root:Root)`. Domain is framed SHA256 of
`ate-occurrence-seek-domain/1`,the existing occurrence_domain; certificate digest
is framed `ate-occurrence-seek-certificate/1`,domain,generation_u64,
allocator_u64,root.digest,root.count_u64. Expected outer commitment is mandatory;
no production certificate constructor. Scope/allocator/generation types retain
the existing strict contracts.

Root keys are existing owner path bytes or existing group_order_key bytes.
Values are existing member_commitment(occurrence_domain,RawOccurrence). Group
key parsing must invert the three escaped fields exactly, including zeros,
prefixes and UTF8, with no TypedCodec object/key/path decoding. Guard the same
4096-byte individual field fast-path budget; budget error is distinct.

`read_occurrence_seek_page(store,pin,cert,expected,*,after=None,limit=128,
max_metadata_bytes=1048576)->OccurrencePage` accepts existing raw cursors,
including arbitrary absent interior positions. Reuse the guarded owned snapshot,
exact store/codec/live retained pin, physical allocator, actual/cached exact
occurrence/state interval indexes. Do not require ordered physical indexes:
the proof root supplies order. Select at most limit+1 root entries to establish
continuation. For each returned position, seek its exact physical visible
placement with LIMIT2, guard checksum/integer types before transfer, reject
missing/overlapping/wrong interval or allocator and compare row commitment to
the selected root leaf. No raw SQL range/visibility-filter scan; no old-pin
newer-candidate rejection for supported field sizes.

The root defines the COMPLETE committed logical relation. Physical rows not
selected by it never enter a result, including coherently inserted surplus
rows. This bounded operation does not discover unselected physical surplus or
corruption; full physical/logical audit must compare complete inventories.
Missing or altered SELECTED rows/nodes fail immediately. This matches the
approved proof-versus-scrub boundary; do not claim universal corruption detection.
World activation remains gated on full verified construction, complete topology,
root/ordinary-payload retention, atomic publication and canonical admission.

## Gates

Independent exact framing vectors, sorted/prefix/zero/empty keys, seeded mixed
updates versus literal model and rebuilt canonical roots; retained roots after
rollback/deletion, no-op writes, missing/forged nodes, malformed oversized stored
bodies, strict stream/transaction failures. Arbitrary middle/end cursors and
all deletion. Real source current/previous pages after massive newer insertion,
reassignment/deletion; fetched physical corruption/overlap, wrong authority,
pin release, missing interval capability, owned/nested transactions.

At1k/10k/100k newer placements in an old group, old-root empty and nonempty
pages must return EXACT results, not budget rejection, with zero owner/history
payload reads/checks/decodes and bounded VM/node/heap observations. Also measure
a local ordered-root update at1k/10k/100k index entries; retain old-root results
and equality with full rebuild, no full Python map. Report full construction,
real changed-set costs and metadata residency separately. No mature save/open
or1s/2s target claim until World consumes this authority.
