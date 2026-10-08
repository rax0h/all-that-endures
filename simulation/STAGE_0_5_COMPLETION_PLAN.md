# Stage 0.5 completion plan and consolidated Sol handoff

> **Current execution authority (2026-10-05):** follow
> [STAGE_0_5_SOL_EXECUTION_HANDOFF.md](STAGE_0_5_SOL_EXECUTION_HANDOFF.md).
> P4.1 at 006e2bb is not accepted: four review regressions require repair.
> The owner authorizes Sol to continue through the remaining in-scope gates
> without routine Astra sign-offs. Earlier stop-for-Astra instructions below
> are historical where the new handoff supersedes them. Long-run and merge
> restrictions remain in force.

**Architect:** Astra. **Date:** 2026-10-05.
**Repository:** `rax0h/all-that-endures`; PR #14;
`sim/stage-0-5-stabilization`.
**Accepted implementation baseline:**
`3365f3753e6a271b9c3051da969aa8d26b3e2609`.
Verify the actual live PR/head before working; later documentation commits are
expected. Do not overwrite newer Sol work or silently work from an older head.

## Current handoff — 2026-10-05 P4 preparation review

P4 preparation at `4a6e23feb52894b1298a5cc09914e77156446f12` is accepted.
The next authorized assignment is **P4.1 only**:
[PERSISTENCE_P4_1.md](PERSISTENCE_P4_1.md), with the binding decisions in
[PERSISTENCE_P4_REVIEW.md](PERSISTENCE_P4_REVIEW.md).
Do not repeat section 3 preparation or use section 8's historical prompt as the
next assignment. The broader completion gates below remain in force. P4.2
World/identity integration still needs the specified decision/proof addendum.

## 1. Decision and authorization

P1, P2A/B/C, P3A and **complete current P3B are accepted**.
Do not restart them. The lifecycle acceptance and exact evidence are in
[PERSISTENCE_P3B_LIFECYCLE_VALIDATION.md](PERSISTENCE_P3B_LIFECYCLE_VALIDATION.md).

Decision B still governs: finish durable continued-world architecture before
returning to long-horizon calibration. Stage 0.5 is not ready to freeze or merge.
This plan distinguishes work that can proceed now from later conditional gates.
A checklist is not authorization to run a prohibited workload.

**Execute now:** the consolidated P4 preparation assignment in section 3,
including its bounded diagnostics, design and executable small proof fixtures.
It deliberately batches the difficult preparation into one review package.

**Following architect review:** implement the approved P4 design and its tests
as one coordinated tranche, with internal commits rather than approval requests
for each ordinary implementation step. Prepare P5 tooling/evidence as described
below. A materially different persistence/identity design needs review before
implementation; do not guess to exhaust a usage budget.

**Not authorized:** millennium/endurance runs; balance or magic-progression
changes; Stage 1; normal checkpoint-default replacement; unrelated simulation
work; PR #14 merge or writes to main. A later request to prepare review or finish
this task does not silently lift those restrictions.

Astra's remaining usage should be reserved for the P4 architecture decision and
final correctness review. Sol should own inspection, measurements, implementation,
tests and evidence assembly. Do not launch additional agents merely to duplicate
reviews.

## 2. Completion map

| Gate | Current state | What closes it |
| --- | --- | --- |
| P1/P2/P3 | Accepted within documented scopes | Preserve; investigate only concrete regressions |
| P4 preparation | Next authorized assignment | Complete inventory, measured growth, selected design, proof fixtures and bounded implementation spec |
| P4 implementation | Not yet implemented/accepted | Identity-safe lazy records/current queries with measured bounds and exact continuation |
| P5 short integrated validation | Pending P4 | Same-code controls, failure/lifecycle/compatibility coverage, short representative smoke/profile and full suite |
| P5 long-horizon evidence | Blocked by existing no-run instruction | Explicit authorization of a concrete run/artifact plan, then required evidence |
| Stage 0.5 acceptance | Pending all applicable evidence | Honest final matrix; unresolved correctness/scaling failures remain blockers |
| Merge/gold tag/Stage 1 | Separately withheld | Explicit owner instruction after acceptance |

The original P4/P5 requirements remain in
[INCREMENTAL_PERSISTENCE.md](INCREMENTAL_PERSISTENCE.md).
Do not redefine P4 as another EventLog cache improvement or equate a passing P3B
suite with total World-memory readiness. Do not claim a percentage complete from
test counts or estimate remaining model quota as engineering effort.

## 3. Next bounded Sol assignment: P4 preparation

### 3.1 Deliverables and scope

Produce all of the following in one branch update:

1. `simulation/PERSISTENCE_P4_INVENTORY.md`: exhaustive record/index/alias/cache
   inventory and measured selection of the first useful storage family.
2. `simulation/persistence_p4_baseline.json`: reproducible machine-readable
   baseline measurements, commands, runtime versions, source SHA and fixture
   definitions. Separate measured observations from proposed targets.
3. `simulation/PERSISTENCE_P4.md`: proposed implementation architecture with
   exact representation, operations, invariants, compatibility, migration and
   failure/state transitions; task/file/test list and objective acceptance gates.
4. A bounded diagnostic harness, preferably
   `simulation/persistence_p4_probe.py`, plus only meaningful small fixture/
   diagnostic tests. It must not change runtime behavior, checkpoint formats,
   accepted store/session machinery or simulation outcomes.

Do not implement production lazy mappings, eviction, new authority, schema
migration or additional gameplay optimization in this preparation task.
Private, throwaway experiments may establish feasibility; label them and do
not install them into normal imports. Commit the diagnosis even if no safe
eviction candidate exists. Explain the exact missing primitive rather than
inventing a sealed status.

Read the accepted persistence contracts and actual implementation first,
particularly `persistence_schema.py`, `persistence_adapters.py`,
`persistence_tracking.py`, `persistence_session.py`, `record_index.py`,
`core.py`, `query.py`, materials/resources, relationship caches and offer
queries. Use `rg`; trace actual reads, writes and aliases. Do not reread the
entire design history or rerun prior tranches.

### 3.2 Inventory every source of retained growth

For each World root/record family, nested growing collection, canonical index,
derived cache and persistence bookkeeping structure, record:

- authority/key and iteration order; record count and encoded bytes;
- mutable fields and actual mutation paths, including later reactivation;
- which gameplay queries require it and their ordering/tie behavior;
- whether callers retain a record, nested container or cross-record alias;
- strong retention from World, session memo/ownership maps, index caches,
  closures and external aliases;
- current read/write/memory cost and proposed bound;
- classification: KEEP / EXTEND / MIGRATE / DERIVED / DEFER, with evidence.

Specifically include people/paths/wallets, resources and material lots/items,
relationships/genealogy, institutional membership, transfer/provenance lists,
collection-layout/order metadata, current identity rows/reverse lookups and
`event_ids`. Include genuine active stock, not just dead people.

P3B cold open still restores the non-event graph. RecordTable first-use buckets
start with every key, and several subsystem caches hold live objects. P2C
current links eliminate lifetime delta replay, but this alone does not establish
bounded discovery or resident alias metadata. Identify all these costs.
A database holding the facts does not help if Python retains every ID, row,
owner path and decoded object anyway.

Do not call dead/consumed/old records immutable without a proven contract.
Death is not a freeze boundary; resurrection and valid direct edits remain
possible. Already sealed Events are accepted P3 scope, not a new P4 pilot.

### 3.3 Bounded measurements, independent controls

Use deterministic synthetic structural fixtures with a fixed active working
set and fixed edits while increasing inactive archive records at least 10x.
Start with 1,000 and 10,000 records of a selected family; a third size is useful
only if those results leave a concrete ambiguity. Keep unrelated fixture
families fixed so the cause of growth is identifiable. Small generated Worlds
may supplement these fixtures; they do not replace late-world evidence.

Measure separately: create/import, open, first/current query, repeat query,
point history access, no-op save, one local edit/save, close and explicit audit/
export. Count checked payload reads/bytes, decodes, writes/bytes, rows visited,
resident objects, identity/memo entries, cache occupancy and peak/retained
allocations. Report fixture setup separately and define measurement windows.
Wall time is diagnostic; structural counters are the principal regression gates.

Baseline costs may grow: this task reports them honestly. Do not make diagnostic
tests fail merely because the known eager implementation is eager.
Use checked store counters where available; do not disable integrity checking
or instrument only the wrapper while hiding a full scan underneath.

Include a small independent control experiment using separately generated
Worlds with identical seed/actions, not two copies made from the same possibly
wrong restore. Compare canonical digest and subsequent events after a short
save/reopen continuation. Reuse accepted helpers where appropriate.

Search available retained artifacts for a trustworthy late-world checkpoint/
store and record its provenance/hash/availability. A log containing a digest is
not the World. Do not run centuries to replace a missing fixture. Report it as
a P5 prerequisite and continue the synthetic preparation.

Do not run the existing offer benchmark with its default 200-year setup merely
to time queries. Build an exact bounded fixture or use an available trusted
fixture. Show offer results/order and work versus irrelevant history separately
from the number of genuinely eligible offers.

### 3.4 Required architecture decisions

The proposal must resolve these before P4 implementation:

**One mutable instance.** Define the identity map, ownership of loaded records,
nested sharing and pins. An LRU is not permission to evict a dirty or externally
reachable mutable object. A retained nested alias must keep its owner/group
valid or participate in a proven handle contract. Reaccess may not produce a
second writable copy. No refcount threshold, arbitrary `gc` heuristic or
silently invalidated alias may serve as the correctness rule.

Specify eviction of a whole affected sharing group, or a rigorously equivalent
mechanism. Explain how session tracking/memos stop retaining every object.
Separate bounded cache memory from genuinely pinned active/external state.
If existing supported object APIs require an interface change, identify every
caller and compatibility impact instead of hiding it inside a dict subclass.

**Read generation and stale sessions.** P3B eagerly captures mutable current
records under one read transaction; lazily rereading overwritten current rows
later cannot preserve that captured World. A head check outside the payload
read transaction has a race. Specify the actual generation-consistent read
mechanism and writer interaction, including a winner committing between two
lazy reads, during decode, before save and before explicit detach.
Compare snapshot lifetime/locking versus retained immutable record revisions
and other viable approaches; select one with costs and cleanup rules. Do not
quietly switch P1 journal mode, introduce indefinite writer blocking, retain
unbounded generations, or allow a World mixing generations.
If the smallest sound design changes the accepted stale-detach/lifetime
contract, make that an explicit architect decision, not an implementation detail.

**Current queries.** Persist rebuildable memberships/lookup rows and deterministic
order information so open/first gameplay query does not decode the archive.
The owning records remain authoritative. Specify membership schema, indexed
lookups, checksums/validation, exact reconstruction, deletion/tombstone handling
and versioning. Membership changes, owning records, identity links, counters,
event publication and new head must commit together. Queries during unsaved
local edits need a bounded overlay with exact ordering and no duplicate/missing
results. Canonical index fields cannot disappear merely because a derived
lookup is more convenient.

**Mutable nested history.** Specify record/segment ownership for any measured
large transfer list or membership collection. Preserve order, duplicates,
mutation operations and aliases. If append-only behavior is not guaranteed,
do not force it into immutable storage. A per-record rewrite whose record grows
with world age is still a scaling problem; state the remaining bound explicitly.

**Compatibility and lifecycle.** Define opt-in mode/version recognition, early
refusal by incompatible APIs, explicit source-preserving conversion, legacy
continuation, backup/relocation, full scrub, digest/archive streaming and
materializing detach. New open must never silently reinterpret an older store.
Retain current checkpoint defaults. No automatic full import on ordinary open.
No-store/closed/stale/recovery states must have explicit behavior.

**Ordinary operation bounds.** Define symbols such as active/pinned records A,
requested records R, edited owners K, cold records H, current aliases L and
cache budget B. State time/read/write/resident-state bounds by operation,
including metadata and indexes. An honest bound may depend on actual active
stock or aliases; it may not conceal O(H) behind “metadata.” Provide proposed
counter assertions with actual constants derived from the selected design.
Explicit full scrub/export/materialization remain O(total data), separately
measured.

### 3.5 Proposed implementation sequence and proof obligations

Write the smallest complete P4 plan from the evidence, usually:

1. Store/query representation and checked generation-consistent access, with
   migration/old-store refusal tests before World integration.
2. One measured high-impact family through lazy lookup, local mutation,
   tracking/identity, save/recovery and lifecycle. Do not begin with a universal
   proxy framework spanning every collection.
3. Necessary current-query adapters and deterministic local overlays.
4. Expand only to the additional families/indexes required by measured residual
   growth. Document genuinely active/pinned memory separately.
5. Integrated compatibility, independent continuation, failure and scaling proof.

For each task name concrete files/APIs, invariants, regression cases and cost
counters. The pilot alone does not close P4 if unrelated archives still dominate
ordinary open/residency.

Required scenarios include: external top-level and nested aliases across cache
pressure; shared parent/child aliases crossing owners; dirty pin then successful/
failed save; local delete/reinsert/order; old provenance query then mutation;
reactivation, ownership transfer and resurrection; cache invalidation; stale
writer; before-commit failure; writer death and lost acknowledgement; corrupt/
missing rows and memberships; backup relocation; close; failed/successful detach;
digest/archive equality. Use real domain methods where available, with explicit
fixture transitions for otherwise unexposed states. Preserve RNG consumption.

**Stop once the complete preparation package is committed.** Report the proposed
design decision, measured bottleneck, exact next implementation task and any
unresolved architectural choice. Request one focused architecture review.
Do not break this assignment into serial “may I inspect/measure/write?” requests.

## 4. After P4 design acceptance: Sol implementation handoff

Use the accepted `PERSISTENCE_P4.md` as the bounded implementation contract.
Implement its tasks sequentially with focused regression tests and internal
`[skip ci]` commits. Preserve accepted P1/P2/P3 behavior. Fix concrete failures
within scope without seeking permission for each reversible edit. Escalate only
a change to authority, generation isolation, supported alias semantics or scope.

Run small affected tests first. After product bytes stabilize, run the required
affected/integrated checks and **one full suite**. If the full suite already
covers the affected set on identical bytes, do not rerun redundant broad jobs.
Measurements belong in a separate reproducible gate if they dominate runtime.
Reuse completed evidence only when source/test blob equality is established.

Record exact tested SHA, commands, completed job URLs, results, source equality,
failure injections, cost tables and limitations in
`simulation/PERSISTENCE_P4_VALIDATION.md` plus machine-readable measurements.
Implementation reports are review inputs, not self-issued architect acceptance.
One end-of-tranche review should cover code and evidence together.

If a test takes a long time, start it once using an authorized unit-only workflow
or local runner, return its run identifier, and let the owner re-prompt after
completion. Do not spend model usage repeatedly waiting/polling. Do not change
the regular workflow merely to obtain a green check.

## 5. P5 preparation and short integrated validation

Once P4 architecture is stable, prepare a reproducible integration harness and
`simulation/STAGE_0_5_RELEASE_VALIDATION.md` so the final evidence can be gathered
without improvisation. Existing scripts do not currently imply a production
cold-session CLI; explicitly exercise the accepted opt-in API. Do not replace
the normal checkpoint defaults to make the harness convenient.

The harness must compare:
- independent unbound simulation;
- trusted schema-8 checkpoint roundtrip and continuation;
- new cold store/session continuation, saves, close/reopen and history access;
- backup/relocation and explicit detach back to portable World.

Use identical seed, initialization/configuration and action sequence. Compare
full canonical digests, event IDs/order/years/causes/values/frozen flags, counters,
current identity and future events. Validate domain invariants and archive
logical equality. Isolate fixture creation/full audit costs from gameplay,
open/resume and ordinary incremental save costs. Include warmed query caches.

Prepare short smoke and failure coverage on final code and one full suite after
the last material product change. The existing targeted smoke is
`PYTHONPATH=.:simulation python simulation/specific_test.py --seed 843000 --years 10 --section all`.
Inspect its current behavior before use. Do not inadvertently run the regular
PR workflow: it includes a millennium.

Check available late-world fixture provenance and retain a portable consistent
backup, rules/schema, producing SHA, seed/config/year, canonical digest, file
checksum and reproducible restore command. Never substitute the inspection
archive for a replay World. Document actual artifact retention/expiry and keep
the required fixture outside an ephemeral workspace. No unattended rerun is
authorized to compensate for a missing artifact.

The release matrix must cover ordinary working-set bounds across larger
non-event history and late-stock offer behavior, not only P3B event segments.
A synthetic fixture proves cost structure; a representative late-world profile
is still required to validate actual workload. Report unavailable evidence
explicitly rather than describing a proposed test as passed.

## 6. Conditional long-horizon/release gate — do not execute now

Before requesting this gate, provide the owner a concrete plan with candidate
SHA, initialization/config, seeds, intended years, commands, expected artifact
sizes/storage destination, failure handling and all short-test evidence.
Only an explicit lifting of the no-run restriction authorizes execution.

The original release requirements include representative 100/500/1,000-year
behavior, fixed-seed determinism, chronological progression/currency/resource
audit and one canonical seed-843000 millennium on stable code. Consolidate
milestones into one instrumented run where equivalent; do not repeat a millennium
for each persistence patch. Additional seeds/horizons need a concrete unresolved
question. A trusted late-world fixture should support a short resumed profile;
do not default to another 3,000-year rebuild.

Validate both the integrated opt-in backend and its independent control where
needed. An unchanged legacy-only millennium cannot by itself validate P4.
Gather simulation time separately from digest, scrub, archive, save and restore.

Preserve actual current owner decisions: 120 seconds is an optimization goal,
not grounds to conceal correctness failures; old 20–25 Diamond targets must not
be silently reinstated. Existing workflow files/roadmap contain historical
threshold differences: report and reconcile documentation against explicit owner
decisions, without opportunistically weakening executable correctness gates.

Report participation, rank/path funnels, recurring new Irons, lineages,
institutions, economy/threat coupling and growth/provenance using existing
definitions. Preserve 4 essences/20 abilities and all advancement gates.
Unexpected populations require diagnosis; this plan does not authorize balance,
magic pacing or hard-coded quotas. Any needed behavioral repair gets its own
bounded proposal and owner authorization.

## 7. Exact definition of release readiness

Stage 0.5 can be proposed for acceptance only when the report identifies:

- final implementation SHA and exact verified candidate/source equivalence;
- all canonical fields/legacy compatibility accounted for;
- independent deterministic continuation and exact identity/event authority;
- atomic old-or-new recovery, corruption refusal and resource lifetime proof;
- measured ordinary read/write/resident costs, including residual active pins;
- representative required short and authorized long-horizon audit evidence;
- unchanged simulation rules, honest performance/participation limitations;
- available durable restore artifacts and reproducible commands;
- no unresolved correctness or decision-B architectural blocker.

Check live PR mergeability and base drift as a separate integration concern.
If resolution is needed, explain and verify it; no merge or main write follows
from a green test result. Prepare freeze metadata on the PR only. Gold tagging,
merge and Stage 1 remain separate owner decisions.

A budget ending does not convert missing evidence into acceptance. If architecture
is done but long-run authorization/evidence is absent, report **“architecture
accepted; final release validation pending”**, not “Stage 0.5 complete.”

## 8. Compact next-session prompt

> Work on rax0h/all-that-endures, PR #14, sim/stage-0-5-stabilization.
> Verify the live head. Read simulation/STAGE_0_5_COMPLETION_PLAN.md and execute
> its entire section 3 P4 preparation assignment. P1/P2/P3A and complete P3B
> at 3365f3753e6a271b9c3051da969aa8d26b3e2609 are accepted; preserve them.
> Produce the inventory, bounded reproducible measurements, small proof fixtures
> and complete PERSISTENCE_P4.md proposal together. Resolve identity pinning,
> mutable-row generation isolation, atomic current query memberships, growing
> nested histories and explicit operation bounds in the proposal.
> Do not implement production P4 before architecture review. Do not run
> millennium/endurance, change balance/magic, replace checkpoint defaults, start
> Stage 1 or merge. Use [skip ci] commits. Do not poll long jobs; return their
> identifiers and let me re-prompt. Commit the complete review package and give
> the proposed architecture, measured evidence, exact remaining decisions and
> next bounded implementation task in one response.
