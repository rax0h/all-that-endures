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

## Release decision still open

Implement exact bounded-memory ordered native pressure sum and measure O(H) cache misses. Owner has not authorized that latency exception or changed arithmetic. This does not block continued implementation; it blocks production acceptance. Endurance/restore retention and promotion remain separately authorized gates.
