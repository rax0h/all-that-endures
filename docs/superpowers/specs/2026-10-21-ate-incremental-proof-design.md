# Astra review: interactive performance through reusable state proofs

Date: 2026-10-21. Status: architecture recommendation grounded in the two latest
successful tests; no runtime implementation or performance acceptance in this review.

## Decision and user intent

Move from repeatedly reconstructing integrity evidence to **incrementally
maintained proofs of committed state**. Keep SQLite, continuous absolute time,
exact world semantics, the existing identity registry, and atomic publication.
Separate value dirt from reference/ownership dirt. Make a save's work follow
changed data and its affected dependencies, with authenticated access paths into
unchanged state. Irrelevant historical payloads must stay unread.

The user explicitly wants small changes to reuse proofs rather than comb through
old history. History must remain available and exact; age alone never makes a
record irrelevant. An old record sharing the changed object is an affected
dependency and must participate. This is a persistence boundary redesign, not a
clock reset, data deletion, gameplay simplification, or larger unbounded cache.

The current repairs are useful foundations. They are insufficient for the target
latencies. Durable proofs address validation amplification; active-state access
and ordinary rule execution also need measurement and optimization. There is no
evidence yet that proofs alone will deliver a one-second mature year.

## 1. What the two tests actually establish

The reviewed baseline runtime tree is `76dee76973928dbce72860156feb32f2d7f02f86`;
the candidate tree is `48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a`. Local imported
source SHA-256 matches the mature candidate receipt:
`95687fd763b7ebffff1fe651d10634a8308f96d16511a2bf8b7123e4e6a95fc9`.

Both tests use the accepted year-1001, generation-126 source: 29,922,463,744 bytes,
SHA-256 `4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`.

1. [Run 39605825742](https://github.com/rax0h/all-that-endures/actions/runs/39605825742):
   full suite passed (3,065 tests plus two subtests), and matched open on the same
   runner fell from **1,066.019 to 439.424 seconds**. Open payload reads fell from
   826,945 / 5.686 GB to 628,525 / 2.304 GB. The archive digest was checked again
   for this review; unmodified receipts are in
   [run-39605825742](../../performance/run-39605825742/provenance.json).
2. [Run 39647739463](https://github.com/rax0h/all-that-endures/actions/runs/39647739463):
   matched first step, save, and subsequent warm step completed. Both closed
   year-1002 outputs reopened in fresh Python processes and matched accepted
   canonical digest `2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7`.
   [Verified results and raw receipts](../../ATE_MATURE_PERFORMANCE_RESULTS_2026-10-21.md)
   document the source, artifacts, hardware and limits.

The intervening failed run 39640324933 failed during harness setup and provides
no simulation-performance observation. The second successful run used separate
hosted VMs with matching reported configuration, not proven identical hardware
or controlled filesystem caches. Neither test supplies a latency distribution.
The new outputs were reopened locally on their runners, not uploaded and
downloaded as new checkpoint artifacts. Warm year 1003 was not saved or digested.

## 2. Target gap

The October 20 architecture/implementation handoffs and the tracked
`simulation/STAGE_0_5_SOL_61_PERFORMANCE_RESULTS.md` record the working engineering
targets of 1-second warm step, 2-second incremental save, and 10-second open.
Those handoffs label them proposed engineering targets, not measured guarantees.
The user has now reiterated the need to reach the speeds in the repo.

| Operation | Latest baseline | Latest candidate | Time reduction | Working target | Remaining factor |
|---|---:|---:|---:|---:|---:|
| Open | 802.138 s | 313.270 s | 60.9% | 10 s | 31.3x |
| First year after open | 2,964.851 s | 2,446.796 s | 17.5% | Report separately | — |
| Incremental save after a year | 2,624.302 s | 2,190.653 s | 16.5% | 2 s | 1,095.3x |
| Warm year after save | 2,288.048 s | 2,158.448 s | 5.7% | 1 s | 2,158.4x |

The previous open observation is 439.424 seconds; do not average it with 313.270
or claim an intervening code speedup: both ran the same candidate runtime.
Even a further 10x improvement would leave the warm year at about 216 seconds.
Reaching 1 and 2 seconds requires eliminating about 99.95% and 99.91% of the
current elapsed work respectively, or an equivalent combination of work removal
and execution efficiency. Small constant-factor tuning is not a sufficient plan.

Keep the causally rich **1,000 years in <=120 seconds** benchmark as a separate
optimization goal. `docs/LIVING_DESIGN.md`, including the supplied Living Design,
preserves it. `docs/STAGE_1_FOUNDATION_CONTRACTS.md` explicitly distinguishes it
from a correctness gate. Historical 87–92-second eager millennium runs are not
equivalent to this mature persistent workload and do not prove its attainable
speed. UI frame/input latency is another separate requirement.

The next elapsed-time acceptance needs a declared reference machine and workload:
CPU model, storage, Python/SQLite, active population, mutation volume, alias
fanout, and cache state. Do not redefine this measured full-year save as a tiny
point edit to claim the two-second target. Report point edits and large saves
separately. Luna also records 1–2-second ordinary saves, <10-second major saves,
<10-second load and <60-second bounded verification; its older candidate timing
claims are superseded by the successful step/save test.

## 3. New deductions from the retained receipts

[Derived evidence](../../performance/proof-review-2026-10-21/derived-evidence.json)
retains the arithmetic and adjacent-snapshot differences.

- Candidate warm step reads **4,208,498 payloads / 6.814 GB**, with 19,343,646
  metadata rows. Baseline payload-request reduction is only **0.54%**. Pin-row
  work fell **65.2%**, yet elapsed time fell only 5.7%. More pin tuning alone is
  poorly aligned with the remaining gap.
- Candidate save reads **8.602 GB** to write **67.920 MB**, about **127 read bytes
  per written byte**, across 1,651,746 payload reads and 219,865 payload writes.
  The written row/byte totals are identical to baseline. These physical payload
  row counts are not counts of distinct gameplay objects.
- The first-step material-lot load snapshot fell from **397,288 to 99,346**,
  about 75%. That repair did useful cold-start work. Across the warm step, the
  candidate counter increases by only **three**. Material-lot loading is not the
  explanation for that 36-minute warm year.
- The exact household-pressure cache reports **zero hits, misses and occurrence
  visits** throughout both lanes. The known exact O(H) cold pressure sum remains
  a future scaling risk; it did not cause these measured delays.
- Candidate warm-step family load deltas include **31,762 resources**, **26,706
  people**, **17,924 social edges**, **15,040 owner-index buckets**, and **8,353
  advancement paths**. These deltas are identical to baseline. At the warm
  endpoint there are only 578 logical owner-index buckets, so 15,040 loads cannot
  represent one load of each bucket. Attribute their callers and reuse distance.
- History-cache eviction count increases by **81,322** during the warm step.
  This is pressure/churn evidence, not proof that the same 81,322 pages were
  reread. The shared record-byte cache reports zero evictions; per-family caps
  and identity/history caches have different policies and must be measured
  separately. Raising every cache limit is not a diagnosis.
- Save and warm CPU time are about **99.4% and 99.9% of wall time**. This points
  toward CPU-heavy processing, without resolving Python, codec, SQL, hashing,
  allocation and rule-execution shares. Peak process RSS is still **2.47 GB**,
  despite a 36.6% reduction. Dirty state, identity metadata, derived indexes and
  temporary plans must be included in memory accounting.

The counters are application work, not physical disk traffic. Read/check byte
counts overlap and must not be summed. Family load counters are cumulative;
warm deltas above subtract the save snapshot. There are no mature per-function
timings or distinct-key/reuse-distance measurements. Do not assign invented
percentages to checksum, SQL, reconciliation or gameplay cost.

## 4. Why existing proofs have not solved this

Source references below are under `simulation/ate_sim/` at candidate runtime
48e3e21. These are observed mechanisms, not measured mature CPU percentages.

| Current component | Actual behavior | Required next boundary |
|---|---|---|
| `persistence_lazy_store.py:read_version`, `_check_record_row` | Starts a checked snapshot, finds a visible version, hashes payload and row, then decodes on a payload read. | Reuse validated immutable data/proof within its exact authority; validate fetched bytes once before admission. |
| `persistence_validation_scope.py` | Private scopes reuse bounded immutable witnesses; scope exit invalidates them. | Keep short scopes, add durable content/topology proofs that are independent of Python object lifetime. |
| `persistence_record_runtime.py:RecordBinding`, `persistence_lazy.py:_before_indexed_assignment/_after_indexed_assignment` | Scalar tickets avoid a duplicate route, but the first route and pending-placement synchronization still happen. | Value-only mutation should reuse proven unchanged topology, while marking every actual affected owner dirty. |
| `persistence_lazy_world_identity.py:_synchronize_pending/_synchronize_owner` | Dirty owner journals cause checked old-placement collection and current-placement comparison, even when comparison discovers no topology change. | Maintain distinct, complete journals for content and topology; no repeated structural reconciliation for an ordinary scalar edit. |
| `persistence_lazy_identity_coordinator.py:discover_group/_routes_for_mutation` | Group discovery is bounded; routing constructs placements and resolves owners; acceptance clears discovered groups. | Reuse group completeness by immutable topology identity, and invalidate only affected authority. |
| `persistence_lazy_identity_catalog.py:read_identity_group` | Validates occurrences, owner paths, counts, links and commitments; a real traversal remains on each uncached group read. | Authenticated group/index completeness proofs reused for unchanged nodes, including absence/retirement proofs. |
| `persistence_lazy.py:_prepare_hybrid_save_inner`, family `prepare_save_changes` | Routes dirty backings, prepares families, compares against baseline bytes and builds participant plans. | Changed-data encoding plus the affected proof closure, with attribution of baseline rereads and forced owner copies. |
| `persistence_publication_proof.py` and coordinator acceptance | Reuses one fully validated successor to avoid validating it twice. | Preserve this; it does not eliminate the first large validation or provide durable cross-generation proofs. |
| `persistence_lazy_world_identity.py:stitch_eager_action_peers` | Iterates retained actions and discovers their groups during open; this fixture has 50,000 actions. | Remove per-action graph reconstruction from ordinary open through authenticated bulk/lazy identity admission. |

There is already useful versioning, a persistent owner radix tree, dirty journals,
typed references, immutable event segments and transactional receipts. Extend
them. Do not introduce a second authoritative world, object registry or event log.

## 5. Selected proof architecture

### 5.1 Distinct content, topology and query commitments

A proof-bearing generation manifest binds store identity, generation, format,
codec/rules version, allocator/counter state, current-state content roots,
ownership/reference roots, query/order roots and event-segment roots. Exact RNG
inputs/state and absolute year retain their existing authoritative encoding.

Use immutable, content-addressed proof nodes with path-copy updates. Reuse the
existing owner-tree structure where its completeness semantics fit. A new format
capability is required for durable cross-generation proof authority; this is not
an instruction to interpret today's row checksums as a sufficient global proof.
Specify canonical node encoding, domain-separated hashes and bounded node sizes
before implementation. Hash raw typed representation; do not alter existing
float, NaN, ordering, duplicate, numeric-key or alias semantics.

Separate these facts:

- **Content:** the exact bytes of a particular record/version or history block.
- **Topology:** which stable incarnations occur at which owner paths, including
  alias groups, links, retirement and absence.
- **Query/order:** complete membership and ordering of the indexed result.

A wealth change changes content and any genuinely affected derived index. It
does not change topology merely because the owner's payload checksum changed.
A transfer, alias replacement or container edit changes topology too. Changed
payloads must be checked against the declared reference projection; storing
separate roots is not permission to let references and topology diverge.

### 5.2 Save as a verified transition

For parent root R, frozen delta D and its affected closure C:

1. Establish the accepted parent root/pin and read authenticated old values or
   boundary proofs actually required by D. Prove additions, deletions and query
   boundaries; positive membership alone cannot prove completeness.
2. Validate the changed payloads, identity placements, query/order deltas, new
   events and counter transitions. Follow all affected aliases even if an owner
   is currently unloaded or historically old.
3. Encode each changed payload once into immutable prepared bytes. Reuse
   unchanged subtree hashes; update only changed leaves and ancestor paths.
   Deduplicate repeated proof-path visits within a bounded internal batch.
4. Commit data, derived index changes, successor proof roots, head and durable
   recovery receipt in the same existing SQLite transaction. No separate
   authoritative sidecar or later best-effort proof write.
5. Acknowledge the exact committed transition with the existing frozen
   publication/recovery protocol. Validate actual changed-row bindings; avoid
   rewalking unchanged closure. Lost acknowledgement resolves that same receipt
   and never reapplies the logical change.

Expected work follows changed bytes, affected aliases/dependencies and changed
index/proof paths. Metadata lookup may be logarithmic in stored keys. This is
not universal O(1): a mutation that truly changes 10,000 owners costs more than
one that changes one. Large fanout must stream or spill within declared budgets.

### 5.3 Runtime mutation and active working set

Use the existing canonical registry and native objects. First checked admission
establishes their content and identity facts. A value-only assignment updates
the existing dirty journal and affected indexes without re-deriving unchanged
ownership. Structural changes reconcile immediately so aliases remain correct
during the same step. Custom hooks, reentrancy, uncertain placements and
unsupported values keep the established slow path.

Proof keys include store, committed content/topology identity, relevant overlay
revision, codec/schema and authority epoch. Old-pin reads stay attached to their
old roots. Rollback, external writes, direct SQL/fault hooks, changed codec,
schema or ambiguous publication invalidate affected runtime certificates or
force checked fallback. A generation number or `already_validated=True` flag is
not a proof. Do not create a transaction spanning an entire simulation year.

Measure the hot working set by family and access reason. Prefer shared live
projections and batched checked reads, preserving iteration/RNG order, over
reloading the same small buckets or rebuilding indexes. Preserve existing memory
limits for the first implementation; any proposed rebudgeting must include
measured reuse distance, total RSS, dirty-state growth and explicit bounds. The
32-MiB clean-record cache is not a bound on total process memory.

### 5.4 Open and historical access

Ordinary open checks the manifest/root and minimum current-state authority,
then admits additional objects lazily or through bounded authenticated batches.
The retained 50,000 actions must remain available in their original order with
their original identities. Deferring their group work requires a compatible
action access path that canonicalizes an object before exposing it, including
aliases through another owner. Simply skipping `stitch_eager_action_peers` would
be incorrect. Include the first actual use in cold-interaction measurements;
moving all 300 seconds into the first click is not success.

An old record is fetched and checked when a rule, query or player action needs
it. The proof must authenticate the actual fetched bytes and complete relevant
relationships. Unrelated historical payloads remain untouched. A displayed year
offset or millennium restart does not remove any of this required work.

### 5.5 What a proof promises, and what a scrub promises

A retained proof establishes facts validated at construction and the correctness
of verified transitions thereafter. It cannot discover new physical corruption
in bytes nobody rereads. Check fetched/changed bytes synchronously; reject bad
proofs, missing links, surplus results, stale pins and malformed transitions.

Trust begins at an authenticated accepted checkpoint or a fully validated import.
A local manifest in the same writable DB is not an independent defense against
coherent replacement of both data and proofs. Keep external checkpoint receipts
for artifact authentication. Adversarial whole-store replacement would require
a separately protected root; this design does not invent that guarantee.

Keep explicit full logical digest/audit and full physical scrub. Make background
scrubbing resumable with a generation/root-bound cursor and byte/time budget;
pin retention must keep its input available. Report progress and last completed
coverage. A sub-minute invocation is a bounded slice, not a claim that the whole
30-GB archive was checked. On corruption, fail closed for affected operations;
repair still needs a verified backup/replica or other separately proven source.
Proofs do not manufacture missing history. Canonical digest semantics remain
unchanged; a new proof root is not a replacement golden digest.

## 6. Alternatives considered

| Approach | Benefit | Limitation | Decision |
|---|---|---|---|
| Extend short-lived caches and tune queries only | Low migration cost; already improves measured load. | Warm payload requests barely changed; does not establish durable reuse. | Keep useful pieces, insufficient as the main plan. |
| Durable content/topology/query proofs plus changed-state runtime | Makes unrelated historical work unnecessary while preserving exact continuation. | Needs a versioned proof contract, reliable dirt tracking, compatibility migration and recovery validation. | Recommended. |
| Replace SQLite, restart every millennium, or load everything into RAM | May alter some constants or initial behavior. | Does not remove required state or repeated validation; adds migration/identity risk or unbounded memory. | Unsupported by these measurements. |

## 7. Delivery sequence and acceptance

This is the architecture and work-package boundary, not permission to claim
performance or a completed implementation. Keep each package reviewable.

**A. Attribute and budget.** Extend the existing phase runner with non-overlapping
subsystem timings; save prepare/commit/publication timings; namespace/reason
read counts; distinct-key and repeated-key sampling; decode/checksum/SQL CPU;
proof hits/misses/invalidations; content-versus-topology dirt; forced owner-copy
counts; cache admission/eviction reasons; RSS and physical IO where available.
Bound diagnostic overhead and label instrumented results. Each stage must write
partial evidence on timeout. Repair the missing open-IO snapshot in the newer
runner. Use retained evidence and small bounded cases before another mature job.

**B. Stop reconciling topology for value dirt.** Extend the existing binding,
bridge and coordinator journals. One checked topology version must support
multiple eligible scalar edits without repeated owner reconstruction. Preserve
field-specific index invalidation, unloaded aliases and every structural path.
This package can be evaluated independently of a new persistent format.

**C. Introduce durable transition proofs.** Define exact manifest/node/leaf formats,
authenticated index completeness and absence, proof construction and validation,
root retention and migration. Implement an explicit copy upgrade from a verified
checkpoint; pay initial construction once, outside ordinary open/save. Old stores
continue through their checked old reader. Atomically publish changed data and
proof roots, then validate exact recovery at every existing fault seam.

**D. Consume proofs in save and open.** Replace repeated unchanged-closure reads
with authenticated reuse. Address action admission and hot bucket reloads using
A's attribution. Retain complete full-audit/digest tools and add bounded scrub
progress. This package is not complete merely because proof production exists.

**E. Demonstrate the user-visible outcome.** On fixed hardware, measure open,
first interaction/year, warm year, point-edit save, the full-year save and larger
changed sets separately. Preserve the accepted year-1002 digest and add paired
year-1003 equivalence if using its warm result as acceptance. Run the appropriate
corruption/recovery suites and a fresh-process save/reopen; retain the existing
independently downloaded restore gate for release. No endurance chain is needed
to prove that a fixed small edit avoids irrelevant history.

Required deterministic gates before expensive timing:

- Hold active state, changed set and alias fanout fixed while unrelated archived
  history grows through 1k, 10k and 100k synthetic records. **Unrelated historical
  payload reads must be zero** for the point edit; proof metadata must follow
  declared path depth, not archive size. Then vary active work, dirty size and
  alias fanout separately so their real costs remain visible.
- Repeat scalar edits on one object under unchanged topology: no additional
  topology reconstruction after the first checked admission; structural edits
  must invalidate and reconcile all affected peers before observation.
- Transfer, delete, resurrect, reorder, duplicate and share data with unloaded
  historical owners. Compare exact order, identity, event/counter state and
  canonical result against the existing checked path.
- Test corrupt payloads, omitted/surplus query results, forged child roots,
  membership/absence proofs, stale roots, old pins, raw DB writes, rollback,
  custom hooks and same-key changed overlays. No catch-and-ignore fallback.
- Interrupt before commit, during commit and during acknowledgement; reopening
  must select a complete old or complete new generation, never mixed roots/data.
- A true no-op save remains free of payload reads/writes. A small scalar edit
  does not visit a historical collection merely to establish that it is unchanged.
- Memory accounts for proof metadata, native objects, dirty state, active indexes,
  frozen plans and spill buffers. No full-history cache or second object registry.

## 8. Review limits and excluded local diagnostic

The two successful mature tests remain the timing evidence. A supplemental local
127-person, year-0 diagnostic was attempted with a 180-second budget on the exact
candidate source, Python 3.12.14 / SQLite 3.53.1. It failed while constructing the
complete-format fixture, before any open/step/save profile. The first attempt
reported `database disk image is malformed`; a bounded upgrade retry on the
retained legacy input reported `attempt to write a readonly database` in
`ConversionWorkspace.stage`. Both retained cold and legacy DBs returned `ok`
from SQLite `quick_check`. The cause is unresolved; neither an environment
explanation nor a candidate regression is established. This is not a failure of
the authenticated mature continuation tests and supplies no hotspot timing.

The [diagnostic receipt](../../performance/proof-review-2026-10-21/diagnostic-result.json),
[probe source](../../performance/proof-review-2026-10-21/diagnostic-probe.py), and
[retry traceback](../../performance/proof-review-2026-10-21/diagnostic-setup-error.txt)
preserve that boundary. Resolve fixture construction before relying on it for A;
do not silently substitute empty-world timings for mature behavior.

No product code, accepted checkpoint, runtime format, CI launch marker, main branch or
release status was changed by this review. No new remote long-running test was
started. The next implementation should be judged by removed work and exact
results, then by the actual latency targets—not another green correctness badge.
