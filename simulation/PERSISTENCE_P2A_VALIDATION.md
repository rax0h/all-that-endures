# P2A — complete World snapshots, ready for review

Implementation on PR #14, based on `7235612c0be57c74b87b7dc823677ea5c0deab47`.
Reviewed Sol's isolated `sol/p2a-world-adapters` branch first. Reused its bounded
read transaction and schema-checked record/namespace reads, removed the extra
namespace `fetchall`, and prohibited commits inside an active read transaction.
The isolated introspection workflow was not imported.

## Implemented boundary

`persistence_adapters.write_snapshot(world, path, rules_id=...)` creates a new,
opt-in SQLite snapshot. `read_snapshot(path, rules_id=...)` restores an independent
World. The legacy schema-8 checkpoint and annual simulation remain unchanged.
Caller-supplied rules identifiers must match; they are not inferred from a moving
branch name. Adapter schema is `ate-world-p2a/1`; P1 remains format 2.

The writer audits canonical state, encodes all retained records, commits in a
private sibling directory, then publishes with a no-overwrite filesystem link.
Encoding/commit failures never publish a partial World snapshot. The reader
performs a full P1 scrub and all reads inside one SQLite read transaction. In
DELETE journal mode this pins a generation and can delay a concurrent writer;
it is a short-lived offline restoration session, not a gameplay reader API.

## Coverage and ownership

The checked-in `persistence_schema.py` explicitly enumerates every World/root
field and every allowlisted record's fields: **36 World fields, 23 root state
types, 85 collection/scalar namespaces, and 66 registered record types**.
A new field, type, unknown non-field
attribute, missing root or unexpected schema fails closed. Supported package
imports are `ate_sim` and `simulation.ate_sim`; records use relative stable type
tags, never imports requested by save contents.

| State | Representation and restoration |
|---|---|
| World and subsystem roots | Explicit field registry; no constructor defaults and no subsystem blob |
| Identity dictionaries | Namespace is canonical field path; each original typed key is a record; checksummed ordinal preserves insertion order |
| Empty collections and counters | Required manifest entries; explicit collection kind/count; scalars have one required record |
| People, households and other RecordTables | Preserve wrapper type; restore rows through notification-aware insertion; weakrefs and query buckets rebuild |
| Canonical indexes | Save exact owner/lot/active-lot/genealogy/adjacency/event-ID fields; no inference from surviving records |
| Ability paths | Complete bounded ability, response-model and understanding trees with owning path |
| Retained actions and events | Individual ordered records, not one history payload; agency's existing retained tail is unchanged |
| EventLog | Preserve cold-prefix boundary, logical IDs/order, year index and mutable tail; reconstruct existing in-memory compressed chunks |
| Event immutability | Explicit FrozenDict/FrozenList tags and presence/value of Event._sealed, including individually sealed tail events |
| Mutable identity | Checksummed manifest links between typed canonical paths; verify duplicate stored values agree, then reconnect before returning the World |

### A real identity edge discovered during validation

The first 30-year mature fixture exposed shared mutable input lists between
`response_model.samples` and still-mutable objective event data. Serializing
records independently without an identity manifest would lose this sharing.

P2A records those links explicitly. Within a snapshot, value copies are encoded
alongside the links; on load their types/values must agree before reattachment.
The restored canonical graph is audited again against the identity manifest.
A new World never shares mutable objects with the source World. P1's codec and
the default WorldCodec still reject shared mutable payloads; only the full
adapter writer with a recorded identity manifest enables repeated value encoding.
Cycles are still rejected. This is lossless full-snapshot representation, not
a dirty-tracking implementation or a claim that copied payloads should become
the later incremental ownership model.

Identity targets currently supported are mutable dataclass fields, dictionary
entries and list positions. Unsupported identity boundaries fail explicitly;
they are not silently copied. No such unsupported boundary occurred in the
validated real histories. P2B must account for shared mutation ownership before
claiming record-local incremental writes.

### Rebuildable state deliberately omitted

An exact per-type allowlist excludes SocialGraph relationship/partnership caches,
community membership cache, magic inventory/selection/offer books, material
selection/rank heaps/whole-unit estimates, and living/rank query caches. Indexed
record weakrefs rebind to restored RecordTables. Unknown extras are rejected;
prefix naming alone never authorizes omission. Mid-step snapshots are rejected.
Tests warm these caches before snapshot and compare continuation with both the
original and legacy checkpoint worlds. Restored relationship cache entries must
be the authoritative restored relationship objects.

Growing nested histories (resource transfers, property ownership/provenance,
relationship shared history, teachers/provenance, institution member/record/notice
lists, genealogy and index memberships) remain with their owners in P2A. They
are explicit future segmentation candidates. Full encoding here must not become
an assumption that rewriting one such history is cheap indefinitely.

## Validation

Commands:

```sh
PYTHONPATH=.:simulation python -m pytest -q -s simulation/tests/test_persistence_adapters.py simulation/tests/test_incremental_store.py
PYTHONPATH=.:simulation python -m pytest -q --durations=10 simulation/tests
```

Focused battery: **51 passed** (17.32 seconds), plus the final repeated-immutable-
reference regression passed independently. **Full unit/integration suite: 235
passed in 248.56 seconds, run once.** No millennium was run. Publication uses
`[skip ci]` to avoid the existing PR workflow's automatic millennium; the workflow
and its validation gates are unchanged. This is local tested evidence, not a new
GitHub Actions result.

The tests cover all registered record fields, founder/default/mature roots,
concrete types and dictionary/list ordering, exact float bits, cross-package load,
no creation hooks, detached identity, post-restore index notifications, a real
training/event alias, missing roots/rows, schema/rules mismatch, duplicate ordinals,
invalid identity links, atomic failure/no overwrite, and pinned read generations.
A separate 4,300-event fixture preserves two cold chunks, a mutable tail and an
individually sealed tail event. The restored archive has the same logical digest
and the same linked person, resource provenance and causal-chain query results.

Short histories compare **original = legacy checkpoint restore = P2A restore**
both immediately and after five additional simulated years. No golden digest
was updated. Exact digests and measured full-snapshot costs are in
`persistence_p2a_validation.json`.

| Fixture (seed 843000) | Full write | Full read/scrub | SQLite bytes | Records |
|---|---:|---:|---:|---:|
| Founder, year 0 | 0.130 s | 0.148 s | 1,101,824 | 1,927 |
| Founder, year 12 | 0.264 s | 0.345 s | 3,309,568 | 6,241 |
| Mature, year 30 | 1.506 s | 1.291 s | 9,555,968 | 16,674 |

These are local full-bootstrap measurements, not annual simulation benchmarks,
incremental save timings or bounded-memory claims. Physical SQLite files include
P1's unique store identity and receipt timestamps; canonical payloads and restored
simulation truth, not byte-identical save files, define snapshot equivalence.

## Stop point

P2A is ready for review after the recorded full-suite pass. No P2B, default
checkpoint replacement, lazy eviction, EventLog disk backing, balance change,
Stage 1 work, millennium or merge. Stage 0.5 is still not freeze-ready: incremental
mutation ownership, integrated storage and continued-world scaling remain later
tranches. This pass proves the complete restoration boundary they will use.
