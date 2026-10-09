# Stage 0.5 final architecture

Status: **approved implementation blueprint; Stage 0.5 is not release accepted.**
Review date: 2026-10-09. This supersedes conflicting remaining-work instructions in the continuous-repair briefs, not accepted simulation semantics or P1–P3 guarantees.

## 1. Verified boundary and evidence

Repository: rax0h/all-that-endures.
Implementation baseline: sim/stage-0-5-astra-ownership-repair at
`a6f1b55a30b259c03e9e895a1df18ca0caf8b9b9`, tree
`5db9482a5685d6342691e1bcde123057a2212c04`.
Production PR #14: sim/stage-0-5-stabilization at
`c29e3d06a0c9d219235e2b3f0390271bd1245aea`; verified draft and unmerged.
These were checked through live GitHub refs/commit/PR endpoints, not inferred from local checkout names.

Four completed workflow runs and their logs were checked once:

| Run | Tested source | Focused result | P5 |
|---|---|---|---|
| 37870946768 | 00a0c693ed3e7a0d6b34241b230c564c2d6d7f73 | 59 passed, 103.09 s | passed |
| 37871823902 | 63400fb02841434c1d7b0e96fcc0d0e5cc4fb595 | 63 passed, 122.02 s | passed |
| 37873110356 | 53575cfeb38fc20604e6e575628f682caa3fb70c | 70 passed, 144.54 s | passed |
| 37873256590 | 7917a27498d927b5ad314c33f81e58bb2a622684 | 44 passed, 135.28 s | passed |

These overlap, and must not be added as unique tests. GitHub comparison confirms all four source commits are ancestors of the baseline. Between the last tested source and the baseline, only progress/results documents changed: simulation source and tests are identical. That establishes integration of those repairs, not a final full-suite certification.

P5 seed 843000, 3+4+3 years, reached year 10 with control final digest
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
No new long test was launched for this architectural review. Historical 907-test and endurance results in the ledger are evidence at their own source boundaries, not certification of the forthcoming implementation.

Read the continuous repair spec, plan, progress, reverse identity plan/validation, six briefs, and P1/P2C/P3B/P4 contracts with this document. Source inspection concentrated on persistence_lazy.py, persistence_lazy_store.py, household members, nested histories, schema/adapters, event IDs, and actual simulation consumers. Two independent focused investigations checked identity completeness and arithmetic/order design. This is a source-based architecture assessment, not a claim that every possible bug has been exhausted.

## 2. Accepted foundations to preserve

- P1 checked SQLite records/segments, coherent head, counts, receipts, durability and failure resolution.
- P2 explicit field/type schema, exact codec restoration, mutable ActionRecord strength, shared identity and current-link semantics. Identity describes current placements, not an accumulating replay journal.
- P3A immutable 2,048-event segments, bounded reader/four-segment LRU, checked full verification bypassing warm caches.
- P3B hybrid event prefix/tail, frozen semantics, session lifecycle, capture/save/recovery and explicit materialization.
- P4 lazy record families, checked MVCC generation pins, current query indexes, weak live identity registry, accepted replacement/owner routing fixes.
- Compact exact consecutive EventIdSet authority, scalar conflict/inquiry/threat and belief storage, typed nested list/map/set histories, adoption threshold indexes, community/token minimum selection.
- Household current living selection, owner-scoped membership index, mortality/inheritance/deactivation consumers, indexed first-match selection and bounded tail deletion.

Acceptance of these foundations is not proof that every field inside a lazy record is bounded. Do not revert the above behavior while replacing its remaining global coordination.

## 3. Confirmed defects and proof gaps

Source locations below refer to the baseline; function names are the durable references.

| Priority | Finding and evidence | Required disposition |
|---|---|---|
| Release blocker: integrity | reverse identity lookup checks returned rows but has no complete-group witness. An isolated temporary-store probe created people[1] and people[2] with incarnation 1, deleted the second occurrence SQL row, and lookup silently returned only people[1]. | Checked versioned group completeness, owner commitments and current-link witnesses. Permanent regression. |
| Release blocker: scaling | open_lazy_world_session calls _read_current_identity_links; _refresh_cross_boundary_identity walks global links/live bindings/targets; _shared_object_routes uses runtime placements rather than persisted reverse discovery. | Replace with affected-group coordinator. |
| Release blocker: scaling | _activate_household_pages (~10216) visits all household records; _household_page_changes (~10344) and _household_member_identity_changes (~10417) revisit broad inventories. | Lazy household headers and touched journals. |
| Release blocker: scaling | middle delete/insert uses _replace_all in LazyHouseholdMembers; Settlement.households is an eager historical list. | Shared counted ordered-sequence backing. |
| Release blocker: nested history | LazyTrackedList is a resident list; resource/lot transfers and Relationship.shared_history are serialized with their owner. _bind_skill_list uses resident LazySoulTrackedList for teachers/provenance. Soul transformations also use resident nested containers. | Finish nested histories within the existing typed-history architecture. |
| Release blocker: latency | _cleanup_expired uses a while loop until exhaustion for each table; release_pin and commit call it. batch_size=4096 limits allocation per batch, not total work. | Globally budget maintenance and index its eligible-row selection. |
| Architectural drift | Identity namespace lists disagree: SKILL is in lazy_incarnations but not lazy_occurrences; OWNER_INDEX/LINEAGE_CHILD are omitted in relevant routing sets. | One adapter manifest and coverage checks; application-level consequences remain unproven, not claimed reproduced. |
| Owner decision | Native ordered preparedness sum over all settlement household occurrences has no demonstrated history-independent exact replacement. | Preserve exact behavior; explicit performance exception or separately approved arithmetic revision. |
| Proof gaps | Final integrated bounds, cross-family faults, final full suite, independent review and new-source endurance evidence are outstanding. | Release gates below. |

The reverse-index reproduction does not establish malicious tamper resistance requirements. Checked witnesses detect accidental deletion/reassignment/inconsistency; an attacker rewriting every authority and checksum is outside this storage integrity contract.

## 4. Architecture decision

**Choose B: targeted structural refactoring on the existing checked store.**
Keep storage and publication, replace global coordination, and consolidate concrete history primitives. This is more than completing a few local repairs, but is not a domain-model rewrite.

| Criterion | A: more local repairs | B: targeted refactoring (chosen) | C: redesign persistence/domain model |
|---|---|---|---|
| Correctness/determinism | Least immediate change; duplicated routing remains fragile | Explicit authority boundaries, existing behavior oracle | Every object/collection/event contract must be re-proven |
| History growth | Local fixes leave global seams | Indexed lazy headers, pages, affected identity groups | Can be excellent, but still needs the same history/index design |
| Gameplay latency | Accumulating exceptional scans | Logarithmic edits; exact pressure exception exposed | New storage alone cannot fix native sum semantics |
| Memory/cache bounds | Per-family and per-owner loopholes | Shared byte budgets and compact child references | Potentially clean, substantial migration burden |
| Storage/write amplification | Whole nested owner rewrites remain | Local pages and touched witnesses; bounded GC | Normalized entities could help; not automatically better |
| Atomicity/recovery | Proven core | Preserve one proven transaction | New proof and failure matrix required |
| Identity/sharing | Ad hoc namespace coordination | One catalog, registry and coordinator | Stable entity IDs simplify some cases but do not represent arbitrary shared mutable children for free |
| Compatibility | Smaller changes individually, repeated upgrades | One explicit new capability and source-copy upgrade | Broad object-model conversion and legacy reader burden |
| Complexity | Lowest per patch, rising aggregate | Moderate implementation; removes repeated authorities | Highest initial and transition complexity |
| Maintainability | Large orchestration continues growing | Concrete adapter manifest and save participants | Potential long-term benefit only after replacing simulation access patterns |
| Integration risk | Hidden coupling persists | Bounded interfaces and incremental gates | Highest; dual-system migration risks |
| Effort to verified state | Apparently short, unpredictable repair cycles | Several substantial packages plus final validation | Materially larger rewrite and revalidation project |

Do not justify retention by engineering time already spent. The positive evidence is actual atomic/fault behavior, compatibility contracts, exact continuation, and reusable checked primitives. Conversely, a relational/entity-ID or event-sourced rewrite would still require order, duplicates, mutable child identities, current indexes and transactional tail ownership. No observed defect requires abandoning SQLite MVCC or immutable event segments. Event sourcing as a new primary authority would add replay and snapshot problems without solving these boundaries.

Long term, entity-oriented APIs may be appropriate for future gameplay. This closeout supplies stable references, paged histories, explicit operation costs and family registration without designing combat or a new ECS now.

## 5. Authority and module boundaries

Retain a single hybrid commit. Introduce small modules rather than further expanding persistence_lazy.py:

- persistence_lazy_families.py: concrete FamilyAdapter registration.
- persistence_lazy_identity_catalog.py: versioned checked identity metadata APIs.
- persistence_lazy_identity_coordinator.py: session affected-owner/group overlays.
- persistence_lazy_sequence.py: counted ordered sequences and membership projections.
- persistence_lazy_households.py: lazy Household headers and current selectors.
- persistence_lazy_budget.py: shared cache accounting and bounded maintenance policy.

Names are chosen interfaces; Sol may adjust file boundaries without changing authority.

FamilyAdapter registers namespace, root path, concrete codec/schema, nested field kinds, checked query projections, owner loading/path binding, identity projection, dirty routing and materialization. Include eager owners explicitly. Do not infer adapters from arbitrary classes or introduce an unrestricted plugin serializer.

Use a SaveParticipant protocol: prepare_delta(context) -> immutable ParticipantDelta; validate_publication(delta, successor_pin); accept_delta(delta, successor_pin). Delta includes version/ordinary writes, identity placement changes, index changes and a prepared-state fingerprint. Preparation is pure with respect to committed authority; it may populate bounded caches. The central plan combines all deltas before the existing commit and publishes them only after checked acknowledgement. Existing family implementations can be wrapped; no mechanical rewrite of every working adapter.

No parallel transaction, alias replay log, shadow event authority or second live object registry. LazyIdentityRegistry remains canonical live object-to-incarnation identity, with weak lifetime handling. Persistent placement completeness belongs to the catalog.

## 6. Generation-pinned identity

### Persisted representation

Keep versioned occurrence rows, canonical typed owner keys and paths. Add:

- identity_group_versions: incarnation, interval, kind, occurrence count/digest, P2C count/digest, checksum.
- identity_owner_versions: typed owner, interval, existence, owner revision, identity projection count/digest, payload/header commitment.
- identity_link_versions: typed target path, interval, incarnation, canonical source path, checksum; indexes for target and incarnation.
- Checked catalog descriptor: schema/capabilities, allocator bounds, namespace/index versions.

Digests hash framed canonical logical tuples, not interval-closure checksums that change when an old row is closed. Keep a versioned group header for every live or retained incarnation; allocator reservations create headers atomically. A missing header is not implicitly empty. After retention safety permits reclaiming a retired header, record its ID in a checked, paged directory of coalesced retired-ID intervals. The catalog commits to that directory root; checked traversal distinguishes retired IDs from missing required headers. Never reuse an ID for a different object. Revival of an externally retained same object removes its ID from the retired directory and restores its header atomically. Interval count follows surviving gaps/live identities rather than the lifetime number of alias edits. Retained pins keep their earlier headers/directory versions. A bounded compactor may lag, but must demonstrate progress under steady churn. This avoids both silent missing-header acceptance and an immortal tombstone per past alias.

This is the P2C current-link relation made generation-aware, not a competing relation. New-format writers derive its canonical star from final current placements; no independently editable ordinary links. Compatibility readers retain old current-links mode separately. Reject mixed modes. Canonical path selection uses deterministic encoded absolute paths. Versioned metadata must preserve captured old-pin identity: current ordinary records cannot substitute for old ordinary payloads.

### Checked interfaces and coordinator

Catalog APIs: read_identity_group(pin, incarnation), read_owner_identity(pin, owner), read_identity_links(pin, incarnation), with batched equivalents and compact exact-occurrence membership checks. Validate store UUID, pin, interval uniqueness, canonical encoding, mandatory header, counts/digests, forward owner agreement and P2C projection inside a checked read snapshot.

Work may be proportional to the requested sharing group G. Do not validate one occurrence by enumerating every other identity in a large owner. Commit owner/header revisions to compact identity metadata; point membership uses exact checked rows and revision binding. Full scrub additionally reconciles the entire catalog.

IdentityCoordinator owns dirty_owners, dirty_incarnations, placement_overlay and indexes of that overlay by owner/incarnation. discovered_groups is generation-keyed and bounded by bytes and occurrence count. Operations:

- discover_group(incarnation)
- routes_for_mutation(object)
- replace_owner / replace_subtree / retire_owner
- prepare_delta / accept_delta

On load, resolve checked incarnation references through the live registry. Before mutation, discover the complete pinned group, overlay current replacements/tombstones, load only relevant owner headers, validate their current paths and bind peers before changing shared content. Route all remaining owners dirty. Removal wins over old persisted placement; externally retained aliases must never resurrect removed owners.

Save processes only dirty owners/groups and actual changed payloads. Re-anchor a group after canonical-owner removal; O(G) changes are real output work. Clear overlays only after acknowledgement. On ambiguous commit retain the exact plan and block further mutation until resolve_save. Rebase discovery caches at successor generation without replacing surviving canonical objects.

Large groups must stream or spill their checked membership rather than bypass the cache byte limit. Loading owner headers can be O(G); unnecessary historical child payload loading cannot. Distinct-but-equal objects keep distinct incarnations.

## 7. Ordered sequence authority

Use one stable-incarnation **counted B+ order tree**, initially for Household.members and Settlement.households. Retain generic typed append-page histories where positional edits are explicitly whole-history operations; do not gratuitously migrate every list.

- Leaves: at most 128 entries, each (stable occurrence ID, exact value).
- Internal nodes: at most 32 children, each child ID and checked live count.
- Descriptor: kind/schema, root node ID, length, next occurrence/node IDs, revision, optional membership-index root.
- Node IDs are stable keys with MVCC versions; split/merge creates/retires nodes. Parent-directory entries are versioned and checked against reciprocal child references.
- Logical rank, occurrence identity and physical slot are different concepts.
- get/set/insert/delete by rank traverse counts. Rebalance only affected paths and bounded neighboring pages. Never renumber the entire suffix.
- Duplicate values have separate occurrence IDs. Deletion removes exactly one occurrence; remove(value) chooses the first equal occurrence.

Tombstone pages with vacancy rank/select alone are rejected: repeated insertion between two neighbors exhausts vacancies and forces relabeling. This tree gives a precise local repair bound.

The sequence descriptor also references a checked paged key directory for membership roots. A point lookup must traverse that directory to prove a value is absent; a missing SQL root row alone is not proof of no matches. Returned roots must agree with directory commitments.

For integer-ID membership, keep a checked per-value ordered occurrence tree (AVL is sufficient), rooted by (sequence incarnation, canonical member ID), with nodes keyed by occurrence ID. Its order is the relative order in the main sequence; insertion comparisons use checked logical ranks. Main-tree balancing changes ranks but not relative order, so it does not reorder these trees. Minimum yields first-match removal without scanning all duplicates. Enumerating living candidate occurrences costs O(K + returned occurrences), with logarithmic traversal factors. Locators moved during one leaf split are bounded by leaf capacity. Main nodes, locators, membership roots/counts and occurrence nodes publish in one transaction.

Validate missing/duplicate locators, reciprocal links, counts, wrong sequence/value and overlapping versions. Root/count commitments prove query completeness; per-returned-row checks alone are insufficient. Full tree scrub verifies global order and index correspondence. A point query verifies its traversed closure, not all unrelated corruption.

Preserve existing element validation and Python observable behavior: negative indices, slicing, insertion order, duplicates, first-equal removal, equality, iterator invalidation and callbacks. Optimized integer lookup must respect existing equality semantics; unsupported lookup types use the compatibility path rather than a false negative. Explicit sort/reverse/arbitrary bulk replacement may traverse affected history; report that cost. A single arbitrary insertion/removal is an ordinary bounded operation.

## 8. Household integration and remaining nested fields

Household headers become a LazyHouseholdTable of IndexedRecord values with compact members HistoryReference. Current queries retain alive/settlement indexes; membership selection joins current person candidates to the checked sequence index, not all archived households. Scalar preparedness/wealth/food changes write the header and necessary projections, never member pages.

Replace _activate_household_pages with lazy binding on first record access. Replace broad _household_page_changes/_household_member_identity_changes with owner/sequence journals through the coordinator. Sharing the same list between households or other supported fields means one incarnation/backing; replacing one occurrence forks ownership, not historical data silently. Death/inheritance/deactivation and split/migration retain their existing ordering and duplicate behavior.

Settlement headers can remain current-world objects, but households is a compact sequence reference. Track append/removal/replacement through the adapter. Loading a settlement must not instantiate all historical household headers.

Finish nested history closure using existing HistoryReference and typed history manager:

| Field family | Baseline status / selected treatment |
|---|---|
| Household.members; Settlement.households | Paged inner/eager outer and eager list respectively; use counted sequences above |
| Relationship.shared_history | Resident LazyTrackedList inside lazy edge; paged typed integer list |
| MagicResource.transfers; MaterialLot.transfers | Resident list in lazy record; paged typed integer list |
| SkillHistory.teachers, provenance | Resident LazySoulTrackedList; paged list, checked membership for teacher uniqueness where required |
| SoulState.transformations | Resident list; paged typed integer list |
| SoulState.authorities, marks, cosmic_links | Tracked resident set/map; use typed set/map when not bounded by an enforced finite domain |
| Genealogy/lineage children, social adjacency, resource owner buckets, community membership buckets | Lazy outer containers do not bound one bucket; use compact typed sequence/set/map children for historical or unbounded buckets, retain checked current query semantics |
| Property/Infrastructure/Institution/Branch/Practice/Divinity fields listed in NESTED_RECORD_FIELDS | Already use typed histories; preserve and integrate coordinator/budget |
| Advancement path and response model | Complete nested object loaded per path. Generated-world bounds include MAX_SKILLS=20, small response samples/coefficients and capped application/transfer evidence; document actual guards, not just comments. Unrestricted imported oversized values cannot acquire a fake bound. |
| EventIdSet | Consecutive form bounded; nonconsecutive fallback is currently resident. Keep range fast path and use a range-plus-paged-exceptions backing for new-format exceptional states; preserve native set equality representatives and aliases. |

EventIdSet exceptional representation is a captured positive-integer range, paged removed integer IDs, and paged additional exact values. These authorities are disjoint under Python set equality. Removing one ID from a huge range writes an exception, not H initial members. Adding a float equal to a removed integer must retain the float representative when native set would; bool/int/float equality and signed-zero behavior need differential tests. Extend the range only when it preserves exact representatives; full compaction is explicit maintenance. Do not silently materialize the range to enter fallback mode.

For fields containing immutable IDs/scalars, use existing concrete history codecs. Do not flatten shared mutable child objects into values. When a nested mutable record has a proven fixed topology, keep its existing identity handling; an unbounded mutable subtree must use incarnation references and the same coordinator.

Produce a schema coverage table for EVERY RECORD_FIELDS entry: scalar, fixed tuple, enforced finite-domain, current-work collection, compact history reference, or explicit legacy-only materialized representation. Include each growth-producing writer and bound. Unclassified fields fail the gate. This closes the inventory rather than authorizing unrelated migrations.

Residual eager state is not “all bounded”: household headers, settlement histories, global identity links and the nested fields above are confirmed counterexamples. Current cells/local/settlements/trade topology legitimately cost current-world size C. Settlement memory currently writes monster_surge and war keys; currency denominations are finite. Agency.actions is trimmed at 50,000 by agency_step, a generated-world bound, not a license to truncate imported larger lists or immutable history. Explicit compatibility states and user-held aliases must be separately measured. This inventory must be updated with implementation evidence before acceptance.

## 9. Exact preparedness and the owner decision

engine.Simulation._pressure uses one native sum over the canonical Settlement.households order, including duplicates and extinct households. CPython 3.12 uses compensated summation. Executed examples:

- sum([1., 2**-53, 2**-107]) is 0x1.0000000000000p+0; math.fsum is ...001p+0.
- sum([1., 2**-53, 2**-53]) is ...001p+0; summing page subtotals gives ...000p+0.
- Updating cached sum([1., 2**-53]) by subtract/add to represent [1., 2**-52] gives ...000p+0; native recomputation gives ...001p+0.

Thus neither fsum, page aggregates nor subtract/add preserves the actual contract. No general impossibility theorem is claimed.

Implement the semantics-preserving path: stream exact scalar values in canonical occurrence order into ONE native sum call, with bounded cache residency. A checked preparedness projection may avoid full household records, but is derived transactionally from headers, never another editable value. Cache the completed numerator/count by membership and contributing-preparedness revisions. Invalidate on assignment, replacement, deletion, duplicates, migration, agency.prepare, magic_economy protection, rollback/recovery and reopen. Unchanged revision may reuse exactly the previous native result. Do not consume RNG while querying or rearrange simulation consumers.

Worst-case cache miss remains O(H). Persistent cache installation must not hide an O(H) scan in small saves; cache may be session-local. Current identity routing and a household-to-settlement occurrence index give affected-settlement invalidation, including aliased lists. Missing referenced household behavior must remain explicit, not substitute zero.

**Owner decision required before final acceptance:** authorize this specific bounded-memory O(H) pressure-cache-miss exception, or authorize a separately specified/versioned change to arithmetic semantics. Recommended for Stage 0.5: preserve behavior and accept the measured exception. That is a recommendation, not authorization. Sol can complete every other package and the exact streaming path while this decision remains open; must not declare all ordinary work history-independent. A future aggregate design needs its own equivalence proof or gameplay-version approval.

## 10. Conversion, generation, recovery and lifecycle

Use new persistence capability **6**, provided live source has not allocated it meanwhile. Checked manifest advertises completed features individually; format floor rises monotonically. Do not emit a partially upgraded format claiming absent authority is an empty collection.

New conversions produce complete capability-6 stores. Existing supported legacy/current stores remain readable through explicit compatibility mode with documented materialization/scaling costs. Provide upgrade_lazy_store_copy(source, destination, rules_id): validate/capture source head, stream when possible, build new authority in a temporary destination, full verify, atomic no-overwrite publish. Full-history conversion is explicit. Preserve source bytes, IDs/incarnations, order, values, sharing and continuation; destination has its own store UUID. Do not reconstruct overwritten historical ordinary records from today's values. Source pins remain with source; destination starts a coherent captured generation. Ordinary open never builds missing indexes or migrates history.

Frozen hybrid plan covers World/eager changes, lazy headers, nested pages, current identity relation/witnesses, query indexes, mutable EventLog tail, newly sealed segments, prefix descriptor, counters, metadata and generation/head in the same existing transaction. Tail partition is [sealed prefix][mutable tail] with exact contiguous event authority: transfer eligible events only after commit acknowledgement; failure leaves the old authoritative partition and prepared plan recoverable. No duplicated/missing events after restore or resolve_save.

Maintain stale-writer rejection, exact generation pins and token-based lost-ack resolution. Validate publication against frozen bytes/witnesses before clearing dirtiness. Old pins resolve old pages/identity; no use of current eager payloads as historical authority. A new session captures eager current state and its matching versioned compact witnesses atomically.

Clean eviction drops all baseline payloads/sidecars no longer needed; weak identity does not mean strong metadata is free. External references legitimately retain objects, but not unrelated history. Retired page-backed children retain a session/pin lease and readable backing without eagerly detaching the full sequence during ordinary owner deletion. Mutations after last owner removal are detached from World authority; represent their private overlay without resurrecting owners. Explicit materializing detach creates portable plain values using one shared memo and may visit full history. Session/store close invalidates still-backed proxies deterministically; already materialized values remain usable. Do not silently make I/O-free-looking access reopen a closed store.

All digest/archive/export/full verification/detach entry points use lifecycle preflight; nested callbacks cannot mutate during protected operations. Failure restores guard state and resources; before-commit errors preserve pending changes, after-commit ambiguity blocks mutation until resolution. Backup uses consistent SQLite backup/capture, not copying an active database file without WAL handling.

Maintenance: replace drain-to-empty cleanup with a global max_rows budget, covering all version/witness/index tables. Index valid_to plus stable cursor/tie key. Normal commit/pin release processes at most 256 eligible rows total; explicit maintain(max_rows) may do more. Preserve retention-floor/receipt safety. Retired backing trees enter an incremental work queue; do not enumerate all their pages on last-owner deletion. Reclamation may lag, and old pins intentionally retain versions. Measure backlog/live/free database bytes separately; no routine VACUUM. Bound metadata to live history, active pins, pending edits and bounded maintenance backlog progress—not total number of past visits.

## 11. Required budgets and instrumentation

Let H be unrelated archived rows or one history length, C actual current working state, D dirty owners/pages, G affected sharing placements, K requested/output occurrences, L counted-tree height. Claims may be O(C+D+G+K+log H), not “constant memory” without qualification.

Required paired fixtures H=1,000 and 10,000, fixed C (eight live candidates), D (one edit), G (two placements), with separate one-long-sequence and many-owners histories:

| Operation | Gate |
|---|---|
| Ordinary new-format open | Zero historical household/nested/event payload reads; no all-owner/P2C scan; fixed descriptor/current-root work |
| No-op save | Zero payload/identity writes and zero archive payload reads; no live-registry/global occurrence walk |
| Scalar household update | One logical header change plus fixed indexes and affected identity closure; zero membership-history payload reads/writes |
| Sequence rank edit | O(L) main-tree nodes, O(log multiplicity) value-index nodes, at most bounded leaf-capacity locator movement; no suffix rewrite |
| Selection | Indexed current candidates and actual returned duplicates; no historic household population scan |
| Identity mutation | Requested group/dirty-owner metadata only; no unrelated group reads or retention |
| Cleanup | <=256 rows removed per ordinary operation, even after releasing a long-held pin |
| Preparedness | Exact results; bounded resident pages; separately report cold miss O(H), warm hit and invalidation costs |
| Repeated saves/visits | No growth in clean sidecars/registries after collection; disk growth corresponds to facts/retained pins/backlog, not alias replay |

Use leaf128/fanout32 and assert operation-specific formulas (e.g. main-node writes <=3L+3 plus bounded locator and membership-index changes). Record actual constants and bytes, not merely big-O. H=10,000 must not produce ~10x work for fixed ordinary edits. Membership index can add O(log H * log H) comparison reads; report and budget explicitly.

Preserve existing four-segment event LRU. Set initial shared clean history-page cache to 64 pages AND 8 MiB, checked identity cache to 4,096 occurrences AND 2 MiB, and existing record cache ceilings <=256 per family plus a shared 32 MiB clean-payload budget. Oversized individual payloads must be classified/split or streamed, not quietly exempted as a “single cache entry.” Limits are initial measurable engineering budgets, not guaranteed Python RSS; report tracemalloc/RSS separately. Dirty state costs actual unsaved changes; externally retained aliases are measured separately. Ordinary step-scoped caches must not pin archived records merely visited during a long traversal.

Instrument payload reads/bytes, writes/bytes, SQL rows returned and examined where measurable, metadata, decoded objects, dirty/retained state, identity group sizes, cache bytes, page/index changes, maintenance and repeated-save growth. EXPLAIN QUERY PLAN plus scale measurements must rule out full scans hidden behind LIMIT. Use wall time as secondary diagnostic, not the sole correctness assertion.

## 12. Dependency-ordered execution packages

Sol owns all packages, not just the first.

1. **Foundation and regression ledger.** Add schema field inventory, metrics harness and permanent missing-occurrence regression. Register concrete adapters and thin SaveParticipant interfaces. Tests under simulation/tests/test_stage_0_5_final_*; no behavior change.
2. **Identity catalog/coordinator.** Implement capability-6 witness storage and source-copy upgrade scaffolding in lazy_store/catalog; integrate coordinator in load, mutation, save, acknowledgement and detach. Replace global reads/scans and namespace sets. Prove old-pin/group deletion/replacement/shared-child behavior before dependent adapters.
3. **Counted sequence primitive.** Implement descriptor/nodes/locators/per-value order index, list differential tests and transaction faults independently of World. Include count/digest and missing-index corruption. Test all split/merge boundaries and repeated insertion between neighbors.
4. **Household/settlement integration.** Lazy header table, compact sequence fields, current indexes, touched-only save, living selectors and migration/split/death. Preserve prior four household test groups and cross-family list sharing.
5. **Nested-history closure and exact-set fallback.** Migrate specifically identified residual nested histories and bucket containers using accepted typed primitives/coordinator. Extend EventIdSet fallback to checked paged storage. Finish the exhaustive schema classification; retain bounded generated-state structures without rule changes.
6. **Pressure projection/cache and budget/lifecycle closure.** Exact ordered stream/cache; owner decision ledger. Shared caches, retained aliases, incremental backing reclamation and bounded SQL maintenance. Exercise all adapters through one frozen publication plan.
7. **Integrated validation/release package.** Paired scales, cross-family matrix, independent P5, one full applicable suite on stable exact source, retained evidence, final independent review request. No new endurance without authorization.

Packages 2/3 can be developed independently behind interfaces but integrate before 4. Package 5 uses 1/2 and existing history primitives; do not develop a second nested identity mechanism. Package 6 starts metrics early but closes after 4/5. Commit coherent working boundaries with focused tests, not broken shared-branch stubs.

## 13. Failure and validation matrix

| Failure/scenario | Required proof |
|---|---|
| Deleted occurrence/link/header/index row; extra or reassigned row | Requested checked group/query rejects; full scrub detects global mismatch |
| Overlapping intervals, wrong store UUID/schema/pin | Reject before binding/mutation; no implicit fallback |
| Shared versus equal children, mixed families, canonical-owner deletion | Exact aliases preserved; removed placements never resurrect |
| Duplicate IDs, replace/delete/reinsert, non-tail edits | Native ordered-list differential trace across save/reopen |
| Failure during any prepared participant; before commit | Old complete store, pending mutation retained, lifecycle recovered |
| Writer death during SQL transaction | Old or complete new head; all indexes/witnesses/tail agree |
| Commit succeeded, acknowledgement lost | resolve_save accepts exact prepared state once; no duplicated event/page/link |
| Two writers, old reader pin, cleanup/backing retirement | Stale writer rejected; old pinned reads remain correct until release |
| Backup/recovery copy/relocation | Store/pin identity rules enforced; complete portable state opens and continues |
| Explicit digest/archive/detach with malicious callbacks | Mutation preflight rejects before partial effects; guards/resources restored |
| Clean eviction and retained aliases over 1k/10k visits | No historical payload/metadata accumulation; aliases route only current owners |
| Legacy conversion failure | Source unchanged, destination unpublished; genuine old fixtures still readable |
| Pressure edge floats, duplicate/extinct households | float.hex/event bytes/RNG continuation identical to independent eager control |

P5: seed843000; independently constructed eager control; 3-year prehistory +4 continuation +3 after reopen. Compare exact canonical digest, event IDs/order/years/causes/values/frozen semantics, identity assertions and RNG-dependent outcomes. Existing baseline digest is a regression oracle, not permission to normalize differing values.

Full suite must run on stable implementation and tests, with source SHA/tree and workflow-only differences explicit. Do not repeatedly run it during each package. A later product fix requires affected gates and a renewed final full-suite boundary. Never poll long workflows repeatedly; save run IDs and collect when completed or prompted.

## 14. Release criteria and external gates

Implementation complete requires packages1–6, exact contracts, no known material defects and truthful remaining exceptions.
Candidate validated additionally requires package7 focused/cross-family/P5/scales/full-suite evidence and independent architectural review with all material findings repaired.
Production accepted additionally requires owner resolution of the pressure tradeoff, separately authorized endurance evidence on the final implementation (or an explicit owner-approved release policy), durable artifacts and authorized production promotion. This assignment authorizes none of the last actions automatically.

The old year-1000 run37679777350 remains historical. A logged runner path/checksum of p5-long-restore.sqlite is not a retrievable artifact. Do not claim the reported ~5.125GB fixture is retained without downloading/verifying an actual copy. Before any future authorized endurance run, preflight artifact storage/free space; use SQLite backup, compress/split if necessary, retain a manifest with source/tree/rules/runtime/seed/digests/SHA-256 and a durable retrievable restore fixture. Verify download, restore and digest. No need to preserve redundant uncompressed copies on the runner.

No PR14 merge/promotion, normal checkpoint-default replacement, Stage1, balance/progression or new gameplay. Only genuinely unresolved project decision now is exact preparedness semantics versus the scoped latency exception; endurance and production acceptance remain explicit later authorization gates.
