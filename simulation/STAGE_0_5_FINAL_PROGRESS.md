# Stage 0.5 complete closeout ledger

Spec: STAGE_0_5_FINAL_ARCHITECTURE.md. Execution: STAGE_0_5_SOL_61_EXECUTION.md.

## Verified starting boundary

Live repair ref a6f1b55a30b259c03e9e895a1df18ca0caf8b9b9, tree 5db9482a5685d6342691e1bcde123057a2212c04.
Planning ref 2d8072e462697a4486c1cf260af10bc26c7cd82a, tree 3ba6debbfc795b0cdb9a20a6f82faa66e4082c13, direct parent a6f1b55.
Implementation branch sol/stage-0-5-complete-closeout; isolated worktree /workspace/scratch/c3a830e86cea/stage-0-5-closeout.
PR14 verified open/draft/unmerged, head c29e3d06a0c9d219235e2b3f0390271bd1245aea. No modifications authorized or made.

Local earlier checkout bf5261b is behind the live baseline. Inspected delta: 19 files / 1044 additions / 23 deletions; preserves four household gates and checked owner-scoped index, living consumers and tail deletion. Source begins from the complete planning commit. Earlier uncommitted identity proposal/regression remain untouched in ownership-repair, outside this implementation tree; they are superseded by the approved counted-tree/catalog design, not silently integrated.

Capability 6 is unallocated at baseline (supported floors 3/4/5). Do not advertise 6 until all mandatory new authorities are complete.

## Preflight shared interfaces

| Producer → consumer | Contract and ruling |
|---|---|
| 1 → 2,4,5,6 | Static concrete adapters classify all root collections, including eager owners. Immutable participant deltas encode inputs before commit. Existing central commit remains the only publisher. |
| 2 → 3,4,5 | One registry; catalog proves complete pinned groups and exact owner membership. Coordinator overlays replacement/deletion before routing. History references preserve incarnations. |
| 3 → 4 | Stable occurrence IDs separate from rank and physical slot. Counted tree supersedes older sparse-vacancy proposal; duplicates/order remain exact. |
| 4,5 → 6 | Compact children expose shared cache accounting and retirement leases. Header/projection revisions govern pressure invalidation; native sum preserved. |
| 1–6 → 7 | Final full suite is deferred until stable integrated source. One final fresh architectural review; ordinary failures repaired inline. |

## Package 1: contracts and baseline inventory

RED: four new contract tests failed because the family/participant module did not exist. Fixture corrections during GREEN: use module-qualified names for the two Institution classes; supply required expected_record_schema to read_version. These were test-fixture mistakes, not production defects.
GREEN: PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py — 68 passed in 5.51s.

Added static family declarations and exhaustive field classification (future fields fail coverage), immutable byte-backed ParticipantDelta / SaveParticipant interface, and actual store-I/O measurement deltas. SQL rows examined are explicitly unknown; query plans/scale measurements remain separate evidence. No storage format change or claim of participant integration yet. Inventory lists pending compact representations and unrestricted import costs honestly; exact writer/bound evidence is refined with each integration package.

Next: permanent missing reverse-occurrence regression and checked catalog, then affected-group coordinator. Packages 2–7 remain incomplete. No final suite, final review or endurance launched.

## Identity foundation checkpoint (October 9, 2026)

Contracts published as bc14d8011a58cd4e02c8c0313441ac149bc1c237, exact tree c0293da984147a2f80cee09ddbe145b68d5d3631; matches local f7bae3265dd94e2b4ddc74568c24357e7bd537ab. Isolated closeout branch, no repair/planning/production ref overwrite.

Added checked MVCC catalog APIs, mandatory descriptor/group/owner/retirement witnesses, canonical versioned P2C projections, and a compressed authenticated owner radix directory. The directory proves exact requested paths without enumerating the other identities in a large owner. Preparation updates affected directory paths/groups and freezes bytes using ParticipantDelta. Added composable checked read snapshots so catalog reads share one head/pin-consistent transaction.

Added coordinator callbacks using the existing sole LazyIdentityRegistry. Complete persisted group discovery precedes mutation; explicit replacement/deletion overlays override persisted placements. No live_bindings inventory. Clean discovery is bounded by 4096 occurrences, 2 MiB estimated Python metadata, and 256 entries; dirty group costs are reported separately. These are independent primitives, NOT yet ordinary World open/save integration.

Observed RED: nine catalog tests before catalog APIs; three affected-path/no-op/large-owner tests before preparation; five coordinator tests before coordinator implementation. Meaningful subsequent REDs: stale intermediate routes after repeated replacement/cancellation; a deleted forward placement incorrectly treated as a new path; a later incompatible peer allowed an earlier copy to be installed before rejection. All repaired and retained as regressions. Fixture corrections: use a explicitly registered dataclass instead of an unsupported arbitrary dict subclass; use matching payload values for genuinely shared roots; use the registry's actual object_for_incarnation API. No broad serializer allowance was added.

Final foundation gate: PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py — **92 passed in 23.75s**.

Existing-runtime compatibility gate: same interpreter/environment, test_persistence_lazy_identity.py, test_persistence_lazy_currency.py, test_stage_0_5_unloaded_alias_routing.py, test_persistence_lifecycle.py, test_stage_0_5_paged_household_world.py, test_stage_0_5_household_scoped_index.py — **73 passed in 48.54s**. These gates have different scopes; neither certifies complete Stage 0.5.

Measured standalone group routing at H1k/H10k: constructor 2 compact payloads / 309–311 bytes; route 9 compact/peer payload reads / 1562–1564 bytes, 48 metadata rows, one indexed query row; two owners loaded and dirtied; preparation 4 compact payload reads / 931–933 bytes; two owner-witness changes, zero unchanged P2C writes, 704 projected payload bytes including both owner copies. Estimated retained requested-group metadata 1019 bytes / 2 occurrences. SQL examined rows remain unknown; reverse EXPLAIN coverage is a separate permanent assertion. Machine-readable measurements distinguish preparation from actual commit counters. This synthetic primitive gate includes no EventLog session markers and is not an integrated World measurement.

Still required before Package 2 completion: full World converter/open/binders/save/ack/detach routing integration; eager owner/version commitments; safe checked retired-ID directory and reclaiming zero-placement headers after retention permits; large-group spill/stream handling; complete cross-family fault/recovery matrix and catalog full scrub. Current primitive keeps explicit zero-placement headers and a checked empty retirement-directory marker; no bounded churn reclamation claim. Capability 6 is NOT emitted, and no ordinary open builds missing authority. Counted sequence work may proceed behind its interface, then integration closes these gaps.

Next action: counted order-tree primitive and checked occurrence projections, with local edit/split/merge differential regressions; then household/settlement and catalog/coordinator runtime integration. Existing source/checkpoints and old compatibility mode remain intact. Final suite/review/endurance have not started.

## Counted sequence checkpoint (October 9, 2026)

Added `persistence_lazy_sequence.py`: counted B+ main tree (leaf128/fanout32),
stable MVCC node/occurrence IDs, checked reciprocal parents and occurrence
locators, per-value relative-order AVL trees and an authenticated compressed
membership-root directory. Ordinary rank edits rebalance local paths. Explicit
conversion and bulk edits may visit affected history. Streaming holds a bounded
leaf and depth stack and follows native list iterator ranks after a mutation.
The central store commit remains the sole publisher; immutable prepared bytes
and dirty state survive failed/lost acknowledgements and clear only on exact
checked acknowledgement. Clean payloads and sidecars share a 64-entry/8MiB
budget; dirty journal costs and tracemalloc observations are separate.

RED: 18 initial tests failed with the missing module. Two later permanent REDs
exposed silent repair of corrupted moved locators and child-parent projections.
Both now validate affected projections before overwriting them. Fixture
corrections: a no-op still performs its required pin check (archive counters
remain unchanged); the store requires a new attempt token after a resolved
non-commit, even when retrying identical frozen participant bytes.

Checked primitive gate: same interpreter/environment as earlier gates,
`pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence.py` —
**31 passed in 86.44s**. Combined affected gate: that file plus final identity
coordinator/catalog/contracts, lazy identity reverse, store and store failures
— **123 passed in 115.40s**. Subsequently added separate SIGKILL tests during
version writes, before commit and after commit — **3 passed in 1.08s**; old or
fully new authority was recovered and fully scrubbed. These scopes overlap;
this is not the final integrated simulation suite.

Implementation blob: `775c61b58bb75bac1d508509adb46a3aef71c487`.
Expanded test blob: `9e79cbef3ec84204ef90799734de7aee891b1ad8`.
Harness blob: `5ce6fa8ba3a354e0af8fd8e1a18a76c61938c016`.
Measurement blob: `e0e375f1c1030ca1340f5686b97749f3d5e80a03`.
The code blob is identical across the combined gate, death tests and final
measurement run. Later changes to these primitives require new evidence.

Reproducible command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_sequence.py --output simulation/stage_0_5_final_sequence_metrics.json`.
Explicit conversion is excluded; eight candidate values and one edit are fixed.
The long duplicate history is a separate fixture. These are sequence-only
measurements, not an integrated World/identity/event bound.

| Ordinary operation | H1k payload reads / bytes | H10k payload reads / bytes | H1k / H10k main-node writes | H1k / H10k total version changes |
| --- | ---: | ---: | ---: | ---: |
| Midpoint insert | 152 / 92,001 | 180 / 110,606 | 2 / 3 | 134 / 90 |
| Midpoint delete | 148 / 86,882 | 177 / 104,074 | 2 / 3 | 132 / 89 |
| First-equal remove, duplicate history | 169 / 36,591 | 213 / 64,181 | 2 / 3 | 139 / 146 |
| Eight candidate lookups | 36 / 47,670 | 41 / 92,655 | 0 / 0 | 0 / 0 |

Insert commit payload writes/bytes: 134/46,105 at H1k and 90/51,602 at H10k.
Delete commit payload writes/bytes: 129/45,365 and 85/51,706 (retirements account
for the difference from total version changes). First removal: 137/13,250 and
144/17,306. Midpoint physical slots differ; bounded locator movement is 126/81
for insertion, 125/80 for deletion, not a suffix rewrite. Formula gate checks
main writes <=3L+3, locators <=256 and total changes <400.

Cold full streaming is explicitly O(H): 18 payloads/42,525 bytes at H1k and
166/436,383 at H10k. Its measured tracemalloc peak is 147,228/505,616 bytes.
Insert dirty estimated bytes are 217,695/210,173; tracemalloc peak
417,066/437,284. Recursive residency estimates are conservative and are not
process RSS. The JSON contains all preparation/commit/query/metadata/cache
counters. EXPLAIN reports indexed namespace/key/version lookup; actual SQL
rows examined remain unknown. Churn with future bounded cleanup still needs a
separate query-plan/scan gate; returned rows do not prove that bound.

Still pending: typed references and numeric/import compatibility for settlement
lists, household headers/selectors, catalog/coordinator integration, retirement
leases/reclamation, shared cross-family budgets and the full integration matrix.
The primitive currently preserves the existing positive-integer household
element guard; it is not yet a replacement for unrestricted settlement lists.
Capability6 is still not emitted. No production ref changed, final review or
endurance started. Continue through the integration packages, not a green-test
stop or routine Astra implementation request.

## Eager-owner commitment checkpoint (October 9, 2026)

Sequence checkpoint published as `479bd4f467312f03353083bf8f278feca51df116`,
tree `e8640726601e9e043ea52e9dbe9d949c638ad337`; matches local implementation
commit `41b0490c4ac61d4a309808d479e5919424e725cb`. Production PR14 still has
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`.

Catalog preparation now accepts concrete ordinary family writes alongside MVCC
owner writes. Current ordinary source checksum/schema/revision must match its
versioned witness; old-pin ordinary identity metadata comes only from that
witness. This does not recover overwritten ordinary payloads. World adapters
must use their captured eager objects, not today's rows, for historical data.
No shadow ordinary payload authority or second registry was added.

Permanent RED: scalar-only acknowledgement accepted a different source body
because it checked the frozen witness but did not validate the owner/source
agreement. Acknowledgement now validates every changed owner witness, including
scalar-only plans. Another RED showed a missing body plus missing owner witness
could hide surviving placements for a new path. An indexed owner-existence
probe now rejects this; it does not enumerate all paths in that owner.

Tests cover pinned eager scalar changes/deletion, wrong acknowledged ordinary
body, missing mandatory witness, cross-lazy/eager mutable-child routing with the
sole registry and one hybrid acknowledgement. The proposed in-place authority
move was a fixture outside the approved source-copy upgrade design: it is now a
permanent rejection/atomic-source-preservation test. Duplicate/competing owner
source plans are rejected. Destination bootstrap remains explicit future work.

Affected gate: final catalog/coordinator/contracts, lazy identity reverse,
store and store failures — **100 passed in 26.44s** with the same interpreter
and `PYTHONPATH=.:simulation`. Log: `final-eager-identity-affected.log`. Existing
identity foundation metrics remain historical evidence on their recorded
earlier source; this acknowledgement closure requires fresh integrated metrics.

Next: typed sequence/reference and settlement equality/import compatibility;
catalog retirement ranges/large-group handling; runtime family callbacks and
frozen participant integration; lazy household headers and settlement fields.
Do not emit capability6 until complete authority/feature markers and explicit
checked copy upgrade are ready. Final P5/full suite/review remain pending.

## Sequence compatibility checkpoint (October 9, 2026)

Eager-owner checkpoint published as `5681038d8a7cb63ed84a9681d762ea4cde5e73cf`,
tree `ebca0eee46a82ed8d40bae725f8947f1dcc24933`; matches local
`f8ae0d0f295947ecf81ecc30bcf56eb3453406d7`.

Added an explicit native immutable-value mode to the counted sequence. Its
versioned descriptor preserves the mode; the original positive integer-ID
descriptor and element guard remain compatible. Integer membership indexes
include equal bool/float representatives while leaves retain their actual
types. Unsupported indexed probes use the native equality compatibility path.
Assignments between equal values of different types preserve the newly assigned
representative. Compact HistoryReference('sequence', incarnation), codec/frozen
snapshot handling, memoized portable materialization and frozen-plan save
acceptance are now available as integration interfaces.

RED: five focused compatibility tests initially failed on the missing value-mode
argument. Verified focused GREEN: **5 passed in 5.08s**. A previous redirected
invocation produced an empty log and was not treated as evidence; the foreground
rerun above is the verified result.

Affected exact-source gate:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_persistence_lazy_nested_history.py simulation/tests/test_persistence_lazy_cold_scalar_families.py simulation/tests/test_persistence_event_log.py simulation/tests/test_persistence_lifecycle.py`
— **99 passed in 147.91s**. This includes the three sequence subprocess-death
tests. Counts overlap earlier gates and are not final integrated acceptance.
Implementation source was unchanged throughout this gate.

Pending: World runtime sequence binders and owner callbacks, capability6 feature
markers and source-copy upgrade, household/settlement integration, and shared
cache/lifetime budgets. This checkpoint does not replace live household or
settlement fields. Native mode supports immutable schema values; it does not
claim closure over arbitrary mutable imported list elements or external NaN
identity after eviction. Those cases require explicit compatibility proof in
the integrated inventory. Earlier sequence measurements describe their recorded
source; the updated implementation needs new integrated measurements.

Next action: checked retirement ranges/large-group handling and runtime
catalog/coordinator/sequence participant integration. Final independent P5,
stable full simulation suite and architectural review remain pending. PR14 has
not changed, and no new endurance run or production promotion was started.

## Checked retirement checkpoint (October 9, 2026)

Sequence compatibility published as `bdd99adf973615d60e37896873555cea3a345a78`,
tree `2d13baf4858d9a478ecae0e42babfc98eb67f683`; matches local
`fb27a9d932be82046e2dcc4da72fc5c035035ab3`.

Added authenticated MVCC coalesced retired-ID ranges with local AVL edits,
subtree interval/ID counts, ordering/boundary commitments and a bounded clean
cache (64 entries AND 2MiB). The catalog v2 descriptor commits this mandatory
directory and the live-header/retired-ID inventory. Missing group headers are
accepted only with a checked range proof and zero current placements/links.
Retirement selection uses the existing checked current-query index, a pin-safe
retirement generation and explicit protected backing leases supplied by callers.
Plans contain <=256 version changes; source-copy upgrade/runtime lease wiring
and the shared physical maintenance budget remain pending.

Revival removes that same ID from its range and restores its group header in
the existing hybrid transaction. No ID is reused for another object by this
directory. Legacy catalog v1 remains readable/writable in compatibility mode;
it cannot enter retirement mode implicitly. Capability6 is still not emitted.

RED: missing range module and retirement preparation (7 failures initially).
Further permanent REDs: warmed payload corruption escaped full scrub; initial
directory construction could overwrite existing authority; allocator-only
reservations received no mandatory headers. Full scrub now bypasses clean
caches, initial construction rejects existing authority, and reservations
publish empty checked headers eligible for later retirement. Cancelling a
replacement does not cancel the consumed incarnation IDs. Cancellation tests
now require those exact reserved IDs, no placements/ordinary writes and no
rewrites of existing owners/groups. The standalone catalog no-op checks two
compact pin/allocator metadata rows; no archive payload/query/write work. The
coordinator true-no-op fast path retains its stricter zero-archive behavior.

Fixture corrections: retirement preparation, rather than a third-generation
commit, is checked while a generation1 pin is retained; the existing two-pin
generation-pressure contract is preserved. The scale-edit target initially
named an already-present ID; it now names an absent ID and asserts actual node
writes and membership after reopen. The measurement harness initially omitted
world_identity_links from its head inventory; checked full verification rejected
it, and the harness now supplies the required inventory.

Final affected gate on unchanged implementation:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_retired_identity.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_identity_reverse.py simulation/tests/test_persistence_lazy_store.py simulation/tests/test_persistence_lazy_store_failures.py`
— **118 passed in 37.54s**. Includes 18 new retirement tests, legacy/no-hidden
upgrade, protected IDs, old pins/revival, missing/corrupt authority, 600-ID churn
and three subprocess SIGKILL points. Counts overlap earlier gates.

Reproduce metrics with the same environment/interpreter and
`simulation/measure_stage_0_5_retired_identity.py --output simulation/stage_0_5_final_retired_identity_metrics.json`.
Source SHA256 values are embedded in that JSON. Explicit conversion is excluded.

| One interval edit | H1k | H10k |
| --- | ---: | ---: |
| Payload reads / bytes | 20 / 7,488 | 26 / 10,206 |
| Node changes | 10 | 13 |
| Total version changes | 11 | 14 |

An additional permanent RED caught shallow dirty-memory accounting that omitted
the journal's retained node objects. Recursive reporting now includes those
objects and baseline bytes: 13,942 / 18,921 estimated dirty bytes at H1k/H10k;
separate tracemalloc peaks are 26,531 / 28,098 bytes. Metrics were rerun on the
corrected implementation, matching the final gate above.

600 reserved unplaced IDs are reclaimed in three plans: 251/251/98 headers,
256/256/103 total version changes, leaving one interval/node and zero group
headers. Indexed selection is evidenced separately; actual SQL rows examined
remain unknown. These are standalone metadata fixtures, not World bounds.
The same metrics explicitly expose the old store's drain-loop work: commit
maintenance_rows 1518/1524/610 counts selection plus deletion. This does NOT
satisfy <=256 physical eligible-row removals per ordinary operation. Closing
that shared budget and proving point lookups against a cleanup backlog is the
next dependency of safe bounded retirement; do not conceal the old counters.

Next: bounded store maintenance and backlog-safe indexed reads, then large-group
stream/spill and World catalog/coordinator/frozen participant integration.
Household/settlement and nested-history integration, final P5/full suite/review,
release pressure decision and production acceptance remain outstanding.

## Bounded maintenance checkpoint (October 9, 2026)

Retirement published as `e48a41616b1059b6d4ff1f3ef30b3f4c7fd6bb4c`, tree
`62ad988962b2faa876cc69ad95d9ac84debc91ea`; matches local
`fbdbc1918bfaf75d4afa9ebf279b4434549362b2` (two coherent local commits).

Replaced the six drain loops with one shared <=256 physical eligible-row
removal budget. Selection uses each table's expiry index; ordinary commit and
pin release invoke it once. Explicit maintenance(row_budget=0..256) performs
one checked transaction with bounded reclamation, preserving head, live pins
and operational receipts. There is no hidden drain. Diagnostics now report
maintenance_removed_rows separately from inspected/deleted-row work.

Full verification reports expired_rows_pending_maintenance instead of rejecting
a legitimate backlog. Its existing all-row checksum/structural verification
remains active, including expired payloads, as a permanent corruption test
confirms. Precommit maintenance failure rolls back the rows and leaves receipts
resolvable. Fixed one-record churn drains a prior bulk backlog incrementally;
old pins retain payload/identity authority and prevent premature removal.

Added interval-leading indexes for key/owner/group/allocator/query point reads
on newly created stores and explicit copy upgrades. Reads seek current or
not-yet-expired intervals instead of walking all old versions to find a second
visible row. Overlap detection remains checked. Open only inspects index layout;
genuine legacy layouts stay unchanged and use their documented compatibility
query path. Final capability6 must require these indexes; it is not emitted yet.

Permanent REDs: pin release removed 2,002 eligible rows in one operation;
record lookup executed 7,025/70,025 SQLite instructions with H1k/H10k expired
versions; limited-query membership proof still scanned old rows; owner-witness
source probe took 7,180 instructions at H1k. Further measurement found ordinary
publication's SELECT DISTINCT namespace walked namespace history even with no
ordinary changes. Its H10k regression failed at 31,567 instructions with cleanup
suspended. Ordinary publication now checks only affected namespace declarations
by indexed existence probes and still rejects historical authority switches.
Fixture reinsertion flags now apply only after initial insertion, preserving the
store's existing reinsertion contract.

Affected gate (same interpreter and PYTHONPATH as above): maintenance,
retirement, final catalog/coordinator/contracts, lazy identity reverse, store and
store failures — **128 passed in 54.50s**. The subsequently added fixed-work churn
test passed separately (**1 passed in 0.43s**) on identical implementation.
Final focused maintenance gate, including that churn test:
`simulation/tests/test_stage_0_5_final_maintenance.py` — **11 passed in 13.06s**.
Existing World compatibility gate: lazy identity/currency, unloaded alias
routing, lifecycle, paged household World and household scoped index —
**73 passed in 55.20s** after the final namespace fix. Earlier sequence plus
World gate was **112 passed in 162.44s** before that fix; it is scoped historical
evidence, not the final integrated suite. Counts overlap and are not summed.

Reproduce store metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_maintenance.py --output simulation/stage_0_5_final_maintenance_metrics.json`.
Fixture construction suspends cleanup only to create valid checksummed expired
versions. Real bounded cleanup is restored for measured ordinary publication.
Source hashes are embedded; final implementation stayed unchanged throughout
these gates and measurements.

| Measured operation | SQLite instructions H1k | H10k |
| --- | ---: | ---: |
| Checked record read | 120 | 120 |
| Order / namespace / allocator point | 39 / 36 / 32 | 39 / 36 / 32 |
| Exact identity occurrence | 43 | 43 |
| Reverse group / owner | 260 / 159 | 260 / 159 |
| Limited query with checked witness | 288 | 288 |
| Scalar commit including 256 removals | 19,005 | 19,005 |

Both ordinary commits removed exactly 256 rows; each explicit maintenance call
removed 64. Commit payload writes are one scalar, 14/15 bytes. Separate observed
tracemalloc peaks are 12,987/15,668 bytes; instrumented commit durations
0.0166/0.0112s are observations, not a latency guarantee. Remaining expired rows
5,742/59,742 are reported rather than hidden. VM instructions are distinct from
returned rows and actual SQL rows examined (still unknown). This is a store
backlog fixture, not integrated World or pressure acceptance. Prior retirement
JSON retains its source-pinned pre-budget counters as historical evidence.

Next: shared cache/lifetime budget integration, large-group stream/spill and
World catalog/coordinator/frozen participant integration. Retired backing-tree
leases/GC remain separate unfinished work. Household/settlement integration,
nested closure, exact pressure path, migration, independent P5/full suite/review
and production acceptance are still outstanding. No production ref changed.

## Shared history cache checkpoint (October 9, 2026)

Workspace execution recovered. Verified local implementation `66c550b`, tree
`2e462db3c35ea39ffb6bf2eafa3897dddf6ae651`, with only the six uncommitted
budget tests retained from the interruption; the attempted budget module had
not been written. Public implementation remains `d2081e8`; documentation-only
recovery commit `0744fac13adbd3cd378e629ae64a19919e0163ce`, tree
`182ce85e40bf66097143d7e0b13b764a5da95cfa`, is preserved in this local tree.
No implementation was silently overwritten or reset. See the recovery document
for the precise earlier interruption; it is historical, not the current state.

Implemented a shared clean LRU with simultaneous entry and byte limits,
weak owners (including unhashable proxies), owner-local eviction/forget/release,
and bounded teardown. Eviction never changes logical ownership, dirty state,
registry placements or persisted authority. Collected owners lose payload and
weak metadata; replacing an entry changes its charge without evicting the new
value. Oversized pages are returned without clean retention. Payload/sidecar
weights and recursively estimated manager metadata are separately reported;
these are not claimed as process RSS.

Counted sequences accept the manager and release it on clean-to-dirty transfer,
rollback, exact acknowledgement and clean pin advance. Typed lists/maps/sets
and compatibility household member pages share one session manager, capped at
64 entries AND 8 MiB. Existing smaller per-list four-page bounds remain.
Session close and portable materialization release the bounded clean inventory
without a registry walk. Dirty pages/baselines and detached aliases have separate
Python residency diagnostics. New tests cover cross-family World histories,
clean sidecar teardown, oversized page rejection, external proxy collection,
dirty survival and acknowledgement. Counted-sequence World ownership integration
is still pending; this change does not emit capability6 or upgrade any store.

RED evidence: six missing-module failures on resume (0.15s); typed list/map/set
and household constructors rejected cache_budget; World lacked the shared
manager and household sharing. A permanent additional RED found cancelled
typed-list edits retaining every touched dirty page/baseline after returning to
original bytes. Preparation now drops cancelled journals and unpublished empty
pages, preserving exact numeric representatives and real changed/deleted pages.

Commands use `PYTHONPATH=.:simulation` and
`/workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q`.
Final source affected gate:
`simulation/tests/test_stage_0_5_final_budget.py simulation/tests/test_stage_0_5_final_world_budget.py simulation/tests/test_stage_0_5_household_sequence.py simulation/tests/test_stage_0_5_household_tail_delete.py simulation/tests/test_stage_0_5_paged_household_world.py simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_nested_history.py simulation/tests/test_persistence_lazy_nested_maps_sets.py`
— **99 passed in 84.69s**.
Sequence/lifecycle/alias/scoped-index gate:
`simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_stage_0_5_unloaded_alias_routing.py simulation/tests/test_stage_0_5_household_scoped_index.py`
— **77 passed in 103.99s**. Both ran on unchanged implementation source;
counts overlap other gates. Earlier 87-test gate preceded the final household
and cancelled-journal changes and is not substituted for these final gates.
One initial command named a nonexistent advancement test file and collected no
tests; it was corrected before the actual gates. No failures are concealed.
Staged whitespace checking subsequently found trailing blank lines in two new
files; these were removed, the source-hashed measurements regenerated, and the
final focused budget/World gate passed **13 tests in 9.19s**. No behavior changed.

Reproduce metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_history_budget.py --output simulation/stage_0_5_final_history_budget_metrics.json`.
Explicit construction/traversal is O(H), not ordinary-open acceptance. Long
fixtures use two histories; many-owner fixtures retain at most eight external
proxies. Source SHA-256, real checked read/commit counters, old-pin assertion,
dirty residency and cleanup results are embedded. SQL rows examined remain
unknown; returned counters are not presented as proof of absence of SQL scans.

| Fixture H1k / H10k | Peak clean entries | Clean weighted bytes | Traced Python peak bytes | Actual edit payload writes / bytes |
| --- | ---: | ---: | ---: | ---: |
| Two long histories | 8 / 8 | 37,504 / 34,336 | 83,802 / 91,311 | 1 / 1; 1,802 / 1,929 |
| Many owners, eight external aliases | 8 / 8 | 3,584 / 3,584 | 36,625 / 36,626 | 1 / 1; 108 / 108 |

World regression additionally traverses 39 independent Property/Infrastructure/
Household histories and verifies their combined 64-entry limit and release on
close. Component fixture clean weights stay bounded as H grows; this is not a
claim about all World caches, overall process RSS, or pressure latency.

Next: large identity-group streaming/spill, World catalog/coordinator/frozen
participant integration and household/settlement counted-sequence headers.
Shared 32-MiB record budget, lifetime leases, retired backing-tree reclamation,
nested closure/exceptional EventIdSet, exact pressure and migration remain.
Independent P5, stable final full suite and architectural review are not run.
Stage 0.5 is neither implementation complete, candidate validated nor accepted.

## 2026-10-09 checked identity membership streaming/spill

Resumed at public `14b278ca667c6ab468e338e5c833909bda16488f`, local
`f8789fec8c90639f083473ad1a80885f4a5b7fa8`, exact matching tree
`e8359f9c0b4e14b35ad05c61f3958b79b4c687c5`. PR14 remains untouched.

Checked reverse and link-projection iterators now close captured snapshots on
normal completion, explicit close and validation failure. Catalog readers
stream complete count/digest, owner/radix and exact occurrence proofs before
returning a group. Oversized captured membership, digest sorting and links use
private immutable checked SQLite spill buffers, whose checksums and captured
order/count seals reject later damage. These files are replay storage only;
the pinned catalog remains authority and the existing registry remains the
sole live-object identity registry. Small groups preserve native tuple results.

Coordinator membership overlays now replay captured placements and indexed
final additions without building an additional resident G-sized membership
dictionary. Output owners and actual unsaved peer installations remain G work;
dirty witnesses and external group references are separately retained. Each
spill database has a declared 128-KiB native SQLite page-cache limit, reported
separately from estimated Python residency. This is not an overall RSS bound.
Catalog publication preparation still builds affected dirty deltas; this change
does not claim that all large-group save preparation is bounded in memory.

Focused final source gate (unchanged implementation during run):
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_identity_spill.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_retired_identity.py simulation/tests/test_stage_0_5_final_maintenance.py simulation/tests/test_persistence_lazy_store_failures.py simulation/tests/test_persistence_lazy_identity_reverse.py`
— **110 passed in 64.27s**. Counts overlap earlier gates. Permanent regressions
cover missing occurrences, missing projection rows, recomputed spill row
checksums, partial-read snapshot closure, old pins and current reanchoring,
replacement filtering, exact representatives and final-reference file cleanup.
Initial missing-module/iterator/budget tests were RED. Two test-fixture errors
(list weak-reference eligibility and an unsupported list subclass) were repaired
using the existing registered Box record; registry/codec checks were preserved.

Next: integrate immutable family participants into the World hybrid save and
recovery path, then catalog/coordinator and household/settlement headers.
Capability6 is not emitted. Integrated H1k/H10k evidence, P5, final full suite,
independent architecture acceptance and production decisions remain pending.

## 2026-10-09 immutable World hybrid participants and receipt recovery

Continued from public `148b25a455da3198eecffb636bda35ae972f9cb0`, local
`0e689502107f77d68107aae2ac381771b8474104`, matching tree
`0858f6f23cf7b07b0f15155ed44168f4eb558663`. This checkpoint integrates
`persistence_lazy_participants.py` into actual World preparation, the existing
single store commit, checked acknowledgement and `resolve_save`.

Each changed namespace has a concrete participant holding immutable source
bytes. Prepared values and commit arguments are fresh detached decodes;
publication and retries replay those bytes, including eager writes, ordinary
query memberships, identity deltas, nested/auxiliary writes, event segments,
head metadata, layouts, allocator and reader floor. An explicit source-field
inventory rejects future omitted save fields. Namespace and source deltas
share immutable payload bytes. Pending-plan diagnostics report frozen bytes;
these are unsaved costs, not charged to clean caches or claimed as total RSS.

Common version/identity row proofs are consolidated in participants. Existing
specialized minimum/adoption/scalar-child checks and frozen cold event protocol
remain. Event controls join that existing descriptor/token proof before any
participant accepts; they are not redundantly reread or given another commit
path. Central publication still clears the existing runtime family journals
only after checked acknowledgement. No capability6, hidden open migration,
production branch modification or event-authority change is introduced.

RED evidence: ordinary ParticipantDelta discarded query memberships; World
plans had no participants and Person values still aliased live records.
New tests verify detached replay, immutable metadata, lost acknowledgement,
wrong delta/pin rejection and exhaustive source coverage. The initial combined
gate found duplicate proofs exceeding the unchanged H1k/H10k read-check limit
(12 then 11 checks versus <=10); consolidating common proofs and joining the
cold descriptor proof restored 9 checks. Nested corruption still raises the
existing diagnostic. A nonexistent lazy-cold-save test filename collected no
tests and was corrected; no passing result is attributed to that command.

Broader affected integration gate before the final receipt-exception correction:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_stage_0_5_paged_household_world.py simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_cold_save.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lazy_cold_scalar_families.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_social.py simulation/tests/test_persistence_lazy_resources.py simulation/tests/test_persistence_lazy_materials.py`
— **153 passed in 193.74s**. This is affected evidence, not the final full suite.

Further adversarial REDs exposed postcommit exception-class handling that could
discard a durably committed plan on StoreConflictError or GenerationPressureError,
and a superseded-successor acknowledgement remaining recovery-required.
Exception handling now consults the durable matching attempt before classifying
any error (pending/committed/acknowledged preserves the plan). A genuinely newer
head marks the acknowledged session stale before participant acceptance.
The earlier supersede fixture accidentally reused a stale peer and was corrected
to open the peer after the first commit; the callback exception case became its
own permanent regression. Final changed-path gate:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_stage_0_5_final_contracts.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lifecycle.py`
— **62 passed in 39.09s**. Counts overlap the 153-test gate.

Final contract consumers gate on unchanged executable source:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_identity_coordinator.py simulation/tests/test_stage_0_5_final_sequence.py simulation/tests/test_stage_0_5_final_sequence_compat.py`
— **71 passed in 154.94s**. Counts overlap prior component gates.

Reproduce focused metrics:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_participants.py --output simulation/stage_0_5_final_participants_metrics.json`.
Source SHA-256 values match the final source. Eight live candidates and one
Person scalar edit are fixed. This fixture has no cross-family sharing; alias
compatibility is covered by affected gates, not claimed by these numbers.

| Metric | H1k | H10k |
| --- | ---: | ---: |
| Frozen source payload bytes | 4,595 | 4,596 |
| Changed namespace participants | 2 | 2 |
| Payload reads / bytes | 7 / 505 | 7 / 505 |
| Checked payload reads / bytes | 9 / 1,747 | 9 / 1,747 |
| Payload writes / bytes | 3 / 767 | 3 / 767 |
| Metadata / returned query rows | 190 / 4 | 190 / 4 |
| Traced Python peak bytes during save | 449,555 | 154,268 |
| Save seconds, single observation | 0.1124 | 0.0645 |

First-use imports are included in the first traced peak; these observations are
not an RSS or latency guarantee. Fixture construction/native SQLite memory are
excluded. SQL rows examined remain unknown. Captured old-pin Person values
remain exact. Subsequent no-op writes zero payload rows; the legacy cold checker
reads three event-control descriptors (217 bytes), reported in full and traced
to `read_records(world_event_storage)`, with no fixture archive payload reads.
The original metrics assertion incorrectly equated all payload counters with
archive reads; it was corrected to trace both ordinary bulk/point and version
read APIs and retain the total counters, not hide the control reads.

Artifact manifest: new participant module, permanent World participant tests,
ordinary-membership contract regression, World integration changes,
`measure_stage_0_5_participants.py`, source-hashed JSON metrics and this ledger.
Resume by verifying `git log -1 --format='%H %T'` and the public branch ref; local
and API commit SHAs differ while their trees must match. No long Actions run
or endurance run is outstanding.

Next critical work: concrete runtime family adapters and World catalog/coordinator
integration; lazy Household headers and Settlement counted sequences; remaining
nested histories and exceptional EventIdSet; shared record budget and lifetime/
retirement closure; exact pressure and explicit copy upgrade. Then integrated
H1k/H10k/fault evidence, independent P5, one stable final full suite and final
independent architecture review. No routine package review is required.
Stage 0.5 remains implementation in progress, not candidate validated or accepted.

## Published immutable participant source checkpoint

Public implementation commit: `b4174345acaa0a315e4b01e8a27b002d8c3457ba`.
Local implementation commit: `edaf40032aaa67397bc5d1bd3ffe3027fe163c57`.
Matching implementation tree: `c3cd5822b75740ee3fa447db124001ed900ae91d`.
Public branch: `sol/stage-0-5-complete-closeout`. These source commits contain
both the implementation and the source-hashed measurement artifact above.
The following ledger-only commit changes no executable source or tests.
PR14 ref remains `c29e3d06a0c9d219235e2b3f0390271bd1245aea`.
All locally launched focused gates above have completed; no test/Actions job
is running. Resume with the next critical work listed above, preserving this
checkpoint and the accepted legacy behavior. No routine Astra approval is needed.

## Release decision still open

Implement exact bounded-memory ordered native pressure sum and measure O(H) cache misses. Owner has not authorized that latency exception or changed arithmetic. This does not block continued implementation; it blocks production acceptance. Endurance/restore retention and promotion remain separately authorized gates.

## Concrete runtime bindings and shared record bytes checkpoint (October 9, 2026)

Implementation local commit `23ee53eea937f14476fd38b726bd2849a051f5db`,
public commit `0d06148e8f03a993b194ae7e24dc2644000f43d3`, matching tree
`f620d0f6c84d97dd453bed1b39a7e598a54b32e9`. Native API publication explains
SHA differences; trees are verified identical. The live closeout branch had
not moved since the previous checkpoint. PR14 remains exactly
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`; no production update, Actions,
endurance run or architectural-review request was made.

`RuntimeFamilyBindings` now binds concrete session/root authorities once,
without owner traversal or payload reads. Both shared-object routing and
IndexedRecord alias callbacks use its immutable maps. It includes skill and
lineage record authorities that the former callback map omitted. Scalar map
families are routing authorities, not falsely classified as record callbacks.
Wallet-first skill and soul children use their existing unrestricted
multi-owner adapters; this does not introduce a second live identity registry.
Child mutation resamples callbacks after binding cold current peer owners.

Permanent REDs: a lineage alias had no authoritative callback; a wallet-first
skill alias failed on its native nested list; a cold skill child mutation left
its authoritative table clean. These now preserve canonical identity through
mutation, save and reopen. Other legacy unsupported native nested containers
have not been claimed to be closed by this targeted change.

Every concrete lazy record family, including the separate lineage-child table,
and hot query LRUs now joins one shared 32MiB byte budget. Weights include
resident schema values and checked baseline payload/presence/incarnation/order/
identity sidecars. Python estimates avoid lazy readers and history iteration;
page-backed reference objects are charged here and their clean pages remain
in the existing shared history budget. Dirty owners are excluded from clean
admission. Eviction releases sidecars and weak budget metadata, and does not
retire persisted occurrences or detach a retained external canonical alias.
Oversized reads return their requested live object without retaining it as
clean. Budget eviction also removes step-touch metadata.

A second RED matrix exposed an oversized owner being evicted again during its
post-mutation rehydration. Eight scalar/history cases failed across skills,
souls, social edges and property. Actual mutation notifications now pin the
owner as dirty before checked loading, retaining exact dirty state on failures.
Tests also cover tiny-budget precommit rollback/lost acknowledgement,
resolve_save, accept-once/no-op and retained identity. A fixture correction in
the earlier retained-alias test adds ordinary people churn: rejecting oversized
skill entries correctly does not evict a smaller existing entry by itself.

Compatibility is explicit: format3/4/5 behavior and the accepted 400-current-
people hot-step regression remain. The shared byte budget applies inside steps;
the strict <=256 per-family clean count during new-format steps remains to be
activated with the complete capability6 runtime. Query budgets and ordinary
per-family count eviction retain existing interfaces. No capability6 floor or
feature marker is emitted; no hidden open-time migration occurs.

Final changed-source focused gate (counts overlap with previous gates):
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_stage_0_5_final_record_budget.py simulation/tests/test_stage_0_5_final_runtime_families.py simulation/tests/test_stage_0_5_final_world_participants.py simulation/tests/test_persistence_lazy_people.py simulation/tests/test_persistence_lazy_skills.py simulation/tests/test_persistence_lazy_lineage.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_persistence_lifecycle.py`
— **92 passed in 54.31s**, `final-runtime-cache-final-recovery.log`.

Final cross-family/household gate on the same implementation:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_persistence_lazy_typed_property_histories.py simulation/tests/test_persistence_lazy_typed_institution_divinity.py simulation/tests/test_persistence_lazy_materials.py simulation/tests/test_persistence_lazy_resources.py simulation/tests/test_persistence_lazy_social.py simulation/tests/test_persistence_lazy_souls.py simulation/tests/test_persistence_lazy_currency.py simulation/tests/test_stage_0_5_r3_cross_family_extra.py simulation/tests/test_stage_0_5_paged_household_world.py`
— **96 passed in 185.98s**, `final-runtime-cache-final-families.log`.
Earlier 72/98/47 gates cover intermediate source, not additional final acceptance.
One intermediate command named a nonexistent recovery file and collected no
cases; it was corrected before the recorded gates. `git diff --check` passed.

Independent eager-control compatibility P5:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/persistence_p5_validation.py --paged-households --output simulation/stage_0_5_runtime_cache_p5.json`
— **passed**, seed843000, 3-year prehistory +4 continuation +3 after reopen,
439 exact events, final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Checks include reopen, relocated backup and portable detach/checkpoint lanes.
This is an independent-control run for the compatibility runtime, not final
new-format acceptance. JSON records exact source hashes. Forced-pressure
float.hex/identity closure still require the final integrated acceptance matrix.
The harness verified then removed temporary restore files: retrievable final
restore artifacts remain outstanding, rather than being falsely declared saved.

Reproducible measurement:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_record_budget.py --output simulation/stage_0_5_final_record_budget_metrics.json`.
Eight live candidates, one scalar edit and two sharing placements are fixed.
Old pins retain the exact previous payload; retained aliases remain canonical.
Explicit archival cache churn is a separate O(H) read, not counted as the edit.

| Measurement | H1k | H10k |
| --- | ---: | ---: |
| Edit payload reads / bytes | 7 / 505 | 7 / 505 |
| Edit checked payloads / bytes | 11 / 3,047 | 11 / 3,047 |
| Edit writes / bytes | 4 / 1,417 | 4 / 1,417 |
| Edit metadata / returned query rows | 201 / 4 | 201 / 4 |
| Clean after edit: entries / Python bytes | 9 / 21,373 | 9 / 21,373 |
| Clean after explicit churn: entries / Python bytes | 257 / 610,406 | 257 / 610,662 |
| Clean manager metadata after churn | 122,464 | 122,464 |

The churn entries comprise <=256 people plus the wallet, not 257 in one family.
Budget byte evictions are separately tested with small limits across families,
inside simulation steps and with oversized query results. Native SQLite/RSS
and total dirty/registry/callback memory are not inferred from these estimates;
the JSON separately reports traced peaks and the two edited payload objects.
The source hashes match exactly. SQL examined rows remain unknown. Subsequent
no-op still honestly reports three checked event-control descriptor reads,
217bytes, zero writes, and no archive payload reads. Open remains the legacy
P2C path; these measurements do not assert a new-format global-scan bound.

**Assignment remains implementation-in-progress, not candidate validated or
production accepted.** Continue through the complete architecture: checked
catalog/coordinator activation and immutable owner publication; lazy household
headers and counted household/settlement histories; nested-history and
exceptional event-ID closure; exact pressure scalars/cache revisions; strict
new-format counts, detached alias leases and retired backing-tree reclamation;
complete capability6 source-copy upgrade; actual writer/guard inventory;
integrated corruption/recovery/H1k/H10k matrix; final-source independent P5 and
one final applicable full suite; final independent architectural review and
retrievable restore artifacts. Pressure latency/arithmetic, endurance policy
and production promotion remain separately owner-controlled release decisions.
No routine Astra approval is needed to implement the next package.

## 2026-10-09 — eager/lazy child publication and exact pressure regressions

Implementation local `750edbed60232c5ef23834da97078ea7e8f71e89`, public
`757e9a8d7a940eb2706e57671b005868b097b807`, matching tree
`3c80b056f9aa3eb99c0abcd6f63d9554c8204455`. Live publication verified with a
leased, non-force ref update. PR14 remains unchanged; no Actions or endurance
run was launched.

The eager-to-lazy seed bridge now shares the concrete runtime manifest. Its
third duplicated callback map previously omitted skill and lineage records;
its skill child type check wrongly expected SkillHistory for a provenance list.
Both legacy cross-boundary refresh filters now use the same manifest. This
repairs namespace drift but does not remove the legacy global refresh.

Concrete skill/soul/advancement list/set aliases bind their lazy owner before a
cold mutation. The eager tracker retains their existing weak object binding;
guards and changed notifications reach both current payload authorities.
Direct eager child aliases, deletion followed by retained-reference mutation,
closed backing, save/reopen and canonical sharing are covered. A retained alias
does not recreate a removed settlement placement.

RED tests then reproduced native partial writes with failing iterables: list
extend and set update/difference changed their value but never dirtied the
owner. Callbacks now run in finally when the actual container changed. Set
notifications also preserve changes in equal values' representatives. The
first broader advancement gate caught a duplicate own-owner notification
turning scalar edits into complete graph reconciliation. IndexedRecord already
delivers its exact field notification; shared notification now reaches peers
without repeating the original owner with field=None. The existing scalar
fast-path regression is preserved, not weakened.

Intermediate evidence (overlapping scopes, not final-source acceptance):
bridge RED3, bridge focused58/1 then59 passed65.13s; affected134 passed62.35s;
direct partial-write RED3/8; runtime11 passed1.05s; affected138 passed77.57s;
cross-family55/1 identified advancement; fixed advancement/runtime23 passed8.23s.
Logs are `/tmp/final-eager-bridge-*.log`; they are reproducible scratch logs.

Final stable-source command:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python -m pytest -q --tb=short simulation/tests/test_persistence_tracking.py simulation/tests/test_persistence_lifecycle.py simulation/tests/test_persistence_lazy_souls.py simulation/tests/test_persistence_cold_save.py simulation/tests/test_persistence_cold_save_failures.py simulation/tests/test_persistence_cold_identity_restore.py simulation/tests/test_stage_0_5_final_runtime_families.py simulation/tests/test_stage_0_5_final_pressure_arithmetic.py simulation/tests/test_stage_0_5_final_record_budget.py simulation/tests/test_persistence_lazy_advancement.py simulation/tests/test_persistence_lazy_skills.py simulation/tests/test_persistence_lazy_lineage.py simulation/tests/test_persistence_lazy_currency.py simulation/tests/test_stage_0_5_r3_cross_family_extra.py simulation/tests/test_stage_0_5_r3_recovery_extra.py simulation/tests/test_stage_0_5_paged_household_world.py`
— **194 passed177.06s**, `/tmp/final-eager-bridge-stable-gate.log`, exit0.
`git diff --check` passed. This affected suite is not the final applicable full suite.

The five new forced-pressure regressions preserve one native ordered sum,
duplicate/extinct occurrences, repeated unsaved preparedness assignments,
shared list mutation/first removal/replacement and reopen. Exact float.hex
events and forced RNG call sequences match independent eager worlds. Concrete
CPython3.12 counterexamples reject fsum, page subtotals and subtract/add. No
pressure arithmetic or engine implementation was changed. Checked scalar
streaming, complete cache revisions, H measurements and the owner's latency
exception decision remain outstanding.

Independent compatibility P5 rerun on this exact production source:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/persistence_p5_validation.py --paged-households --output simulation/stage_0_5_runtime_cache_p5.json`
— **passed**, seed843000 3+4+3, 439 events, exact final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
Log `/tmp/final-eager-bridge-stable-p5.log`. JSON includes changed production
module hashes, engine/harness and pressure regression provenance; all verified.
Temporary restore files were verified then removed, not declared retrievable.

H1k/H10k rerun:
`PYTHONPATH=.:simulation /workspace/scratch/c3a830e86cea/ownership-gate-venv/bin/python simulation/measure_stage_0_5_record_budget.py --output simulation/stage_0_5_final_record_budget_metrics.json`
— exit0, `/tmp/final-eager-bridge-stable-metrics.log`. Both edits still read
7/505 payload rows/bytes, check11/3047, write4/1417, metadata201/query4,
clean9 entries/21373 estimated Python bytes. Source hashes now include the
eager tracker; every embedded hash verified. Existing legacy-open, SQL scan,
unpaged histories, dirty-memory and strict hot-step count caveats still apply.

**Next action:** finish compact family header comparison for the checked
coordinator without materializing page-backed histories, then activate the
complete checked catalog/coordinator through the integrated new-format runtime.
Continue all remaining packages listed above. Implementation remains in
progress; this passing checkpoint is not candidate validation or release acceptance.
