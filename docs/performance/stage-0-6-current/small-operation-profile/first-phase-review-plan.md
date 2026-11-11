# First bounded runtime phase — verification factorization only

Selected scope: remove duplicate canonical parsing and branch re-encoding. No
cache, new validation certificate, wire-format change or gameplay change in this
first phase. Measure its raw effect before expanding the attack.

## Read boundary

Extract a private ProofNodeStore._read_bound_bytes(map_domain,digest) containing
the existing address/type/SQL length checks, diagnostics and domain hash check.
It returns raw bytes whose storage address/domain digest and maximum size have
been checked; it grants no canonical-node certificate. Public read calls this
method, then decode_node, preserving its existing complete contract.

Only SQL-backed ProofMap callbacks use the private raw method. Leave
ProofMap._read unchanged: it independently validates its own root reference and
map-domain digest, decodes the node, then checks count and required prefix.
Keep BOTH hashes. The physical callback may accidentally bind domainA while the
outer map binds domainB. Bytes valid underB, stored as a malformed row underA,
must fail the innerA check even if the outerB hash would succeed.

ProofNodeStore.write stays unchanged, including full readback on INSERT OR IGNORE
collision. Preserve standalone read behavior, counters, byte limits, missing-node
refusal and stored SQL type checks. Do not introduce a caller-controlled 'trusted'
flag that disables generic ProofMap verification.

The eight production SQL bindings at reviewed94267 are:

| Module | Binding |
|---|---|
| persistence_proof_record.py | _map, line78 |
| persistence_proof_reference.py | _map, line49 |
| persistence_proof_scope.py | _map, line103 |
| persistence_proof_publication.py | _map, line50 |
| persistence_proof_world.py | _map, line42 |
| persistence_proof_occurrence.py | checked reader, line249 |
| persistence_proof_query.py | checked reader, line164 |
| persistence_proof_version.py | checked reader, line125 |

Leave in-memory ProofMap construction and reference-only instances unchanged.
Do not accidentally change the write callbacks alongside read factorization.

## Canonical branch decoder

The direct parser must preserve all constraints currently supplied by the
encode_node(result)==raw roundtrip: exact tag/header/total length and size ceiling,
prefix length/nibble interpretation and zero odd padding, child count2–16,
strictly increasing slots within0–15, positive child counts and total count at
mostMAX_COUNT, and exact32-byte digests. Manufactured tuple/Root types remain
exact. Leaves retain exact70-byte shape. Returning identical immutable node
objects and bytes is required; root/domain hashing does not change.

## Meaningful validation

- Keep known canonical byte/root vectors and all existing malformed branch,
  missing/oversized/TEXT node, root-count/prefix, collision and map tests.
- Add the wrong physical domain binding described above, not just a different
  outer root. Preserve both inner and outer refusal paths.
- Construct a multi-level valid SQL tree, finish writes, then measure read-only
  positive and negative lookups. Canonical parser calls should equal fetched
  nodes rather than twice fetched nodes. Reads should no longer invoke the
  branch encoder. This is a work-count requirement, not a wall-time assertion.
- Standalone public store read still performs one canonical parse and rejects a
  malformed-but-correctly-hashed node. The private callback paired with unchanged
  ProofMap must reject that same node at its one canonical parse.
- Compare candidate against independent byte-identical copies of the authenticated
  small input, sequentially on one qualified tuple. Run raw open/first/save/warm
  separately from cProfile/counters. Source preservation, exact saved commitment/
  generation/year/digest and fresh continuation remain mandatory.

Expect lower parse/encode work; SQL fetch counts need not fall in this phase.
Do not claim a target speedup from nested cumulative profile times. If raw targets
still miss, inspect the separately documented closed proof-fact cache and exact
placement-read candidates before a larger architecture change.

Engine changes require new exact engine greens. Keep old monolithic trigger
request untouched; do not label old94267 successes as tests of a new runtime.
Update the new harness's explicit source/green/compatibility authority only after
the bundled engine validation succeeds, preserving original source-control pins.
