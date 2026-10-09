# Sol 6.1 — complete Stage 0.5 implementation directive

You are Sol 6.1 in ChatGPT Work. Use High reasoning effort by default. Own implementation, debugging, focused tests, integration, compatibility, measurements and documentation through the entire assignment. Do not stop after the first package or request routine Astra approval. Temporarily increase effort only for a concrete difficult identity/recovery contradiction.

## Baseline and branch

Repository: rax0h/all-that-endures.
Verified implementation baseline: sim/stage-0-5-astra-ownership-repair,
`a6f1b55a30b259c03e9e895a1df18ca0caf8b9b9`.
Baseline tree: `5db9482a5685d6342691e1bcde123057a2212c04`.
Production PR14: sim/stage-0-5-stabilization,
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`, draft and unmerged at review.

First verify live refs and read both documents on sim/stage-0-5-final-architecture:
simulation/STAGE_0_5_FINAL_ARCHITECTURE.md and this execution document.
Create an isolated implementation branch/worktree from the planning commit, whose parent is the verified implementation baseline. Record exact SHA/tree. If newer implementation work exists, inspect its delta and preserve coherent accepted changes; do not silently overwrite it or mix unreviewed changes. Do not modify production PR14 or force-push shared branches.

Read the continuous repair spec/plan/progress, reverse identity plan/validation, continuous-repair-briefs, and relevant P1/P2C/P3B/P4 contracts. The final architecture document controls remaining implementation decisions; older stop-after-one-tranche instructions are superseded by this complete assignment.

## Architectural decision

Implement targeted structural refactoring, retaining the checked SQLite/MVCC store, one hybrid transaction, receipt/recovery protocol, immutable event prefix and accepted lazy family behavior. Do not rewrite the persistence backend or simulation rules.

Replace global identity discovery with a generation-pinned checked catalog and affected-group coordinator. Use a counted ordered tree for household/settlement histories. Finish nested histories and enforce shared cache/maintenance budgets. Concrete family adapters and immutable save participants unify integration without mechanically rewriting every working family.

Existing household gates 59/63/70/44 and P5 passed at runs37870946768,37871823902,37873110356,37873256590. All are ancestors of the baseline; source/tests match the last gate. Counts overlap. Preserve these tests and behavior; they are not final integrated acceptance.

## Execute all packages in dependency order

1. **Contracts, metrics and regressions.**
   Create a concrete family manifest and thin SaveParticipant interface. Each participant prepares immutable writes/index/identity deltas, validates publication and accepts the exact acknowledged plan. Central commit remains authoritative.
   Add permanent regression for deleting one of two persisted occurrences in a shared incarnation: current reverse lookup silently returns an incomplete group. Add exhaustive RECORD_FIELDS classification with growth writers and actual bounds. Instrument bytes/rows, caches, dirty/retained state and maintenance.

2. **Checked identity catalog and coordinator.**
   Add versioned group/owner witnesses and generation-aware P2C link projections, with count/digest completeness, owner/header commitments, canonical encoded paths, mandatory headers and checked retirement metadata.
   Implement checked read_identity_group/read_owner_identity/read_identity_links APIs and exact membership reads. Validate pin/store UUID/interval/schema, missing/extra/reassigned rows and owner agreement. Current ordinary rows cannot provide historical payload authority.
   Preserve LazyIdentityRegistry as the sole live canonical-object registry. Coordinator maintains dirty owners/groups and placement overlays indexed both ways. Before mutation, discover the complete pinned group, overlay replacements/deletions, bind relevant peers and route current owners. Retained aliases must never resurrect removed placements.
   Replace _read_current_identity_links on new-format ordinary open, _refresh_cross_boundary_identity global scans and runtime-only _shared_object_routes. Replace duplicated namespace sets with adapters.
   Reclaim retired metadata safely using checked coalesced retired-ID ranges after pin safety permits; no permanent per-edit tombstone accumulation. Never reuse an incarnation for a different object.

3. **Counted ordered sequences.**
   Implement persistence_lazy_sequence.py: stable-incarnation descriptor, MVCC stable node IDs, leaves of128 occurrences, internal fanout32, subtree live counts, checked parent/occurrence locators. Separate logical rank, occurrence ID and physical slot.
   Arbitrary single-position insert/delete must split/merge local paths, not rewrite suffixes. Preserve duplicates and exact native list semantics.
   Use checked per-value occurrence order trees for first-equal removal and living-candidate selection; relative order survives main-tree rebalancing. Update moved locators and every projection in the same transaction. Tombstone/vacancy pages alone are insufficient for arbitrary insertion.
   Prove behavior with differential traces, boundary splits/merges, repeated same-gap insertion, old pins and index corruption.

4. **Household and settlement integration.**
   Add lazy Household headers with compact members references, alive/settlement indexes and existing current-person selection. Replace _activate_household_pages eager traversal and broad household save/identity preparation with touched journals.
   Represent Settlement.households using the ordered sequence. Preserve extinct household occurrences, duplicates, insertion order, migration first-removal, splits, mortality/inheritance/deactivation and shared lists across families.
   One scalar edit must not read or rewrite member history. Owner deletion must not eagerly materialize a retired sequence.

5. **Nested-history closure and exceptional event IDs.**
   Reuse typed HistoryReference primitives for Relationship.shared_history, resource/lot transfers, skill teachers/provenance, soul transformations and unbounded soul sets/maps. Inspect genealogy/lineage children, social adjacency, resource-owner and community buckets at the nested level; use compact children wherever history grows without an enforced bound.
   Preserve already paged Property/Infrastructure/Institution/Branch/Practice/Divinity histories.
   Keep bounded advancement topology where actual guards justify it; do not claim imported unrestricted values are bounded or truncate them.
   Extend EventIdSet exceptional states using a captured range plus paged removed IDs and paged exact additional values. A single removal from a huge range must not materialize H members. Preserve bool/int/float equality representatives, duplicates-as-set semantics and aliases.
   Finish classification of every schema field. No unexplained eager history may remain.

6. **Exact pressure, lifetime and budgets.**
   Preserve one native ordered sum in Simulation._pressure over all settlement household occurrences. Stream checked preparedness scalars and cache only by complete membership/value revisions. Invalidate on all writers, replacement, migration, duplicates and recovery. Do not use fsum, page subtotals, subtract/add or active-only filtering; these change results.
   Exact cache misses remain O(H) worst case. The owner has NOT yet authorized that performance exception or changed arithmetic. Implement the exact bounded-memory path, measure it and keep this release decision explicit while continuing other work.
   Enforce shared cache byte/entry budgets; release clean sidecars and weak metadata after eviction. Retained page-backed aliases use a valid lease and private detached overlay when unowned; closed backing fails explicitly. Full materializing detach uses one sharing memo.
   Replace _cleanup_expired drain loops with <=256 total eligible-row removals per ordinary commit/pin release, indexed selection and explicit bounded maintenance. Incrementally reclaim retired backing trees and demonstrate progress under churn without violating old pins/receipts.

7. **Integration and release package.**
   Integrate all participants into the existing frozen hybrid save/recovery plan. Run focused/affected and cross-family gates, H1k/H10k measurements, independent P5, then one final full applicable simulation suite on stable exact source.
   Produce complete evidence and request final independent architectural review. Continue repairing ordinary failures yourself; do not return merely because one package is green.

## Non-negotiable integration contracts

One transaction publishes World/eager state, lazy headers/pages, checked identity/current links, query projections, mutable event state, newly sealed segments, prefix descriptor, counters and head. Never duplicate or lose events across prefix/tail authority. Publish in-memory changes only after checked acknowledgement; preserve frozen plan/dirty state on ambiguity and resolve exactly once.

Preserve IDs, years, causes, values, frozen EventLog semantics, RNG behavior, collection order, equality and shared versus distinct identity. Keep stale-writer rejection, old-pin reads, backup/relocation and lifecycle callback guards. No hidden migration on open.

Use capability6 if still unallocated, with complete feature markers and monotonic reader floor. Provide explicit source-preserving copy upgrade and keep genuine legacy readers in documented compatibility mode. Capture a coherent source, verify destination fully, publish without overwriting source. Missing new-format authority is corruption, not legacy fallback. Do not reconstruct old overwritten ordinary payloads from current rows.

Suggested modules: persistence_lazy_families.py, persistence_lazy_identity_catalog.py, persistence_lazy_identity_coordinator.py, persistence_lazy_sequence.py, persistence_lazy_households.py and persistence_lazy_budget.py. Existing persistence_lazy.py, persistence_lazy_store.py, adapters, tracker, household members and typed histories integrate through these interfaces. File boundaries may vary; authorities may not.

## Evidence and bounds

At H=1,000 and10,000 hold current work fixed: eight live candidates, one edit, two sharing placements. Test many historical owners and one long history separately.

Measure payload reads/bytes and writes/bytes, indexed/metadata rows, query plans, decoded objects, identity work, dirty state, cache bytes, external aliases, repeated-save growth and maintenance. Do not use returned-row counts to disguise SQL scans.

Required bounds:

- Ordinary new-format open: no historical household/nested/event payload or global P2C scan.
- No-op save: no archive payload reads or payload/identity writes; no registry/global-owner traversal.
- Scalar household update: header plus relevant projections/identity closure, zero member-history pages.
- Positional sequence edit: local tree paths and bounded leaf movement; no suffix rebuild.
- Identity routing: affected group/owner work, not unrelated archive.
- Maintenance: <=256 eligible rows per ordinary operation.
- Pressure: exact results, bounded memory, explicit measured cold-miss exception.

Initial clean limits: history64 pages AND8MiB; identity4,096 occurrences AND2MiB; records existing <=256 per family plus shared32MiB payload budget; event reader retains four segments. Measure actual Python residency separately. Dirty/external-reference costs must be reported, not hidden inside clean bounds.

Cover replacement/deletion/reinsertion, duplicates, equal-but-distinct objects, shared mutable children, cross-family aliases, retained references, stale writers, old pins, missing/extra/corrupt authority, precommit failure, subprocess death, lost acknowledgement, resolve_save, recovery copy, legacy snapshots and portable detach.

P5: seed843000, independent eager control, 3-year prehistory +4 continuation +3 after reopen. Exact digests/events and identity checks; baseline final digest is 3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e. Include forced-pressure float.hex counterexamples and unchanged RNG outcomes.

## Working method, escalation and completion

Keep coherent commits on the isolated branch and a durable progress/evidence ledger recording package, SHA/tree, commands, results, metrics, run IDs and next action. Resume from it across sessions. Do not continually poll long Actions runs; record IDs and collect completed results later or when prompted. Do not weaken tests to hide a mismatch.

Escalate only when an invariant cannot be preserved, a required bound needs changed gameplay/compatibility, a new competing authority is necessary, or the approved architecture requires substantial departure. Explain the concrete counterexample and options. Routine implementation choices, debugging, compatible refactoring and test repairs are yours.

Final deliverables: implementation commits; schema/growth inventory; migration documentation; H1k/H10k measurement tables; failure/corruption results; exact P5 and final-suite evidence; durable artifact manifest; remaining limitations; independent-review handoff.

Distinguish implementation complete, candidate validated and production accepted. Final release additionally requires owner resolution of pressure arithmetic/latency, independent architecture acceptance, separately authorized final-source endurance evidence or explicit release-policy decision, retrievable restore artifacts and authorized production promotion.

No Stage1, balance/magic changes, unrelated features, checkpoint-default replacement, PR14 promotion/merge, destructive reset/force push or new millennium/endurance run. Routine repository work and focused validation are authorized. Execute the whole closeout; do not ask Astra what to implement after each package.
