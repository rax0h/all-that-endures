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

## Release decision still open

Implement exact bounded-memory ordered native pressure sum and measure O(H) cache misses. Owner has not authorized that latency exception or changed arithmetic. This does not block continued implementation; it blocks production acceptance. Endurance/restore retention and promotion remain separately authorized gates.
