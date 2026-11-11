# Independent small-operation architecture review

Keep mature execution paused. Try a bounded runtime optimization before another
hours-long constructor. The evidence supports reducing repeated proof work; it
does not yet justify a new storage format, a gameplay algorithm change or a broad
persistence rewrite.

This is the same bounded-genesis closure group. Review used saved evidence and
source only: no engine edit, new profile, expensive run or additional delegation.
Reviewed runtime remains94267bb00a219702a4bd1700a2fc0600a5c5aa56.
independent-review-evidence.json records the inspected hashes and callgraph details.

## What the measurements establish

The actual42961490569 smoke receipt contains these raw wall times. Its operational
proof checkpoint is26,206,208bytes; this is a small4×3World, not the mature fixture.

| Operation | Raw hosted seconds | Instrumented local seconds |
|---|---:|---:|
| Open |1.603|3.364|
| First year |9.756|22.059|
| Save |7.002|15.985|
| Warm year |7.913|17.504|

Raw smoke explicitly records save=false and warm_step=false for the2s/1s targets.
Warm raw CPU7.912s is almost its wall time, with zero physical read bytes. The
profile similarly spends warm17.49CPU seconds in17.50wall seconds. This points
first to CPU/query/validation repetition, rather than a cold disk bottleneck.
Different software and cProfile overhead forbid treating the two columns as a
regression comparison. The profile's fresh generation1/year2 digest equals the
expectedcebc2fcd...; its harness checks immutable source bytes before and after.

The small miss is an early readiness warning, **not a mature failure prediction**.
Inspect raw target flags before permitting another costly mature prefix. A
functional smoke green alone does not establish performance readiness. Use a
cheap raw pilot on the exact candidate/fixture/software before expensive work;
keep this policy distinct from mature acceptance.

## First attack: factor identical proof verification

ProofMap._read calls ProofNodeStore.read, which hashes and decodes a node, then
ProofMap hashes and decodes those same bytes again. Warm has42,840map reads and
exactly85,680decode_node calls. Save has54,080map reads and112,578decodes, including
writes. Save's get path accounts for50,046of54,080map reads. Repeated lookup,
rather than only proof-tree editing, is material.

Start with the smallest factorization that keeps every condition checked:

- A private bounded raw-node fetch can feed the unchanged fully checking
  ProofMap reader. Keep SQL storage-class/size limits before transfer. Keep
  standalone ProofNodeStore.read fully checking and keep collision writes reading
  actual stored bytes. Do not simply remove validation for all store callers.
- Remove the branch decoder's encode-then-compare roundtrip only if its parser
  directly enforces exactly the same canonical padding/tag/length, strictly ordered
  child slots, positive child counts, count overflow and fixed digest constraints.
  Root count and required-prefix checks still run on every edge. No node bytes,
  domains, locators or commitments may change.
- If a shared decoded-node cache is needed, make it both byte- and entry-bounded
  and hold only immutable raw/decoded proof facts. It must be owned by the exact
  store/authority operation, not each short-lived _map factory or a global cache.
  Key by exact DB/codec/domain/digest and accepted manifest/pin/checked epoch.
  A hit still checks the caller's root count and required prefix.

Cache eligibility is part of correctness. Preserve closed-codec checks, callback
and phase-hook boundaries, pin/head/retention checks, schema/data/total-change
epochs and the externally accepted commitment. Invalidate or bypass on publisher
entry, commit/rollback/savepoint, generation change, recovery/uncertainty, untracked
SQL or codec drift. Keep cold fully checking fallback when custody cannot be
proved. Do not mint certificates in arbitrary borrowed transactions. Do not keep
an active read certificate around a gameplay callback, full simulation step or
public iterator yield. A bounded immutable cache may retain facts between calls
only if the next closed read re-establishes their authority before use.

The existing ValidationScope does epoch PRAGMAs on reuse and deliberately rejects
borrowed certification. Enabling it everywhere or making its checks disappear is
not the proposed optimization. Start on the proof-only path, with explicit closed
operation ownership and default readers unchanged. No decoded World/body cache
should bypass the canonical identity registry or retain unrelated historical data.

## Second candidate: avoid whole-owner work for one reference read

Warm's1295_owner_changes calls spend7.25s cumulative. Of these,1002 originate in
RecursiveHistoryRuntime.decode and spend4.03s capturing whole-owner metadata to
check one owner/path's incarnation. Descriptor checks also repeat913times/5.99s.
These timings overlap each other and proof-map timings; they must not be summed.

After the first candidate is measured, consider a proof-only current-placement
lookup for decode, using the existing exact identity membership proof plus the
coordinator's current placement overlay. Preserve synchronization, new/private
owner cases, tombstones, expected reference kind/incarnation, group discovery,
canonical object lookup and occurrence attachment. Leave complete owner/group
closure checks on mutation, replacement, retirement and publication intact.
The accepted manifest supplies the global current authority; prove that exact
point checking meets this read's contract before selecting it. Ordinary audited
readers must retain their existing completeness guarantees. A closed batch sharing
one checked owner inventory is the conservative alternative.

Do not optimize agency/magic gameplay merely because agency_step is the largest
cumulative parent:11.49s includes history/identity/proof work below practice paths.
That is not evidence its game rules or random choices should change.

Save separately spends8.27s cumulative in commit and5.07s in acknowledgement.
Both include proof work. Retain every distinct participant/source/successor check
and ambiguous-publication recovery rule. Share immutable verified nodes within a
valid closed validation region; do not skip acknowledgement because a SQLite
epoch matches, or hold one certificate over all mutable publication callbacks.

## Bounded decision and verification

Use independent byte-identical copies of the authenticated small proof checkpoint.
Compare raw sequential operations on the same qualified software, with source
hashes, external commitment, exact saved generation/year/digest and fresh restore.
Collect callcounts separately from raw latency. Record cache bytes/entries, misses,
node reads/decodes, owner/descriptor visits, pin/epoch and SQL work. Keep the
existing corruption, alias replacement/deletion, rollback, callback, codec,
stale-writer, recovery and publication controls; no skipped audits or enlarged
whole-history resident inventory.

Measure after this bounded patch before expanding scope. If raw small timings and
logical work do not improve materially, or fixed live/dirty work still scales with
unrelated archive history, inspect a bounded batched proof/placement API next.
That would warrant an explicit architecture change. A global cache, larger
retention limit or removing a distinct integrity check is not a substitute.
Any engine edit invalidates the old94267 engine greens; earn one bundled new
validation after local evidence justifies it, rather than CI per micro-finding.
Future profiles must fence actual working source/import paths as well as HEAD:
the current profiling script's HEAD-tree assertion alone would mislabel dirty
engine edits. The inspected baseline has no such engine edits.

## Upload readback correction

The initial404 helper was wired to old green-artifact lookup while seal still
used the single GET. That concrete wiring finding was sent immediately and is
now corrected: seal calls read_uploaded_artifact; inspect_green is unchanged.
Existing seal regressions retain actual byte/context/producer/reference validators
while exercising404→success and404→invalid-origin refusal.

The narrow predicate is sound: exact positive artifact ID; at most four identical
GETs; only HTTP404 retried; waits1/2/4s; all other failures and integrity mismatches
remain fatal. These are request-count/backoff bounds; API calls retain their60s
network timeout, and the enclosing job limit owns the total wall bound. Do not
describe the7s backoff as the complete operation duration. Do not rerun a stage inside this helper. The
successful published workflow rerun demonstrates retained-parent restart wiring;
it does not itself exercise this subsequently unpublished helper change.

The Minor exact-response check is also corrected: returned metadata ID must equal
the upload action's requested ID before sealing. A successful response with wrong
ID fails without retry, even if other origin/name fields match. Independent
targeted verification passed8tests/53deselected in0.08s, covering successful and
invalid-origin seal readback, exact ID, retry exhaustion and non404 refusal.
retry-closure.log/xml, retry-closure-source.json and the full matching qualified313
fingerprint preserve this local closure. All findings remain in the existing
consolidated group. The selected smallest implementation phase is detailed in
first-phase-review-plan.md; it deliberately includes no cache yet.
