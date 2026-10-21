# LUNA — Independent ATE Persistence and Performance Investigation

**Date:** 2026-10-21  
**Repository:** [rax0h/all-that-endures](https://github.com/rax0h/all-that-endures)  
**Purpose:** Independent evidence handoff for Astra’s architecture decision  
**Scope:** Read-only investigation. No source changes, endurance runs, or new performance tests were performed.

## Executive findings

1. **The persistence pattern is defensible for ATE’s invariants.** Versioned mutable records, append-only causal event segments, exact typed encoding, identity and query indexes, generation pins, and atomic generation publication can preserve object identity, sharing, history, and deterministic continuation. The evidence does not justify a wholesale replacement.
2. **The current end-to-end path is still far outside the requested budgets.** The latest matched mature comparison is open-only: the candidate reduced open from 1,066.0 seconds to 439.4 seconds (2.43× faster), while still taking 44× a 10-second load target. It provides no current candidate step/save result.
3. **Older year-1002 measurements remain severe, but belong to an earlier runtime tree.** On a 30.22 GB database at runtime tree 76dee76, one year took 57m11s, saving took 48m44s, full store audit took 77m28s, and logical world digest took 73m11s. Do not quote these as current-candidate timings.
4. **The measured access pattern shows repeated work.** That earlier save read 11.49 GB to write 67.9 MB; one simulation year read 7.51 GB and wrote no payloads. Current-candidate open still checked 628,525 payload rows and 2.30 GB of payload bytes, plus millions of metadata and pin rows.
5. **The next decision should be measurement-led optimization and proof-boundary design.** Keep exact validation where bytes or relationships change or are first trusted. Determine which old immutable facts can be reused under generation-pinned, invalidatable proofs; do not replace checks with a stored root that is not anchored or whose underlying data has never been reread.

## Evidence labels and limits

- **Measured** means recorded in an existing run result or profile, with the source revision and workload stated.
- **Source-supported inference** means the implementation path makes the work or scaling behavior visible, but no direct timing isolates it.
- **Hypothesis** means plausible but unmeasured here.
- Workload counts such as payload reads are application counters, not OS physical-device reads. The available mature comparison did not record SQLite cache hits, page faults, physical disk bytes, or filesystem cache state.
- Performance targets below are evaluated against available evidence, not claimed as validated release budgets.

## 1. Verified current architecture and baseline

### Revisions and runs

| Evidence | Exact revision / run | What it establishes |
|---|---|---|
| Candidate branch head observed at investigation start | 7c9dfcd5ade194bf049fc2500896bb80e36cd03e | Docs-only head containing the matched-open harness; candidate product code is the runtime tree below. |
| October 21 performance-repair candidate | commit 5521c094981c9a5f28f1d076453264291b534ff5; runtime tree 48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a | Current candidate source revision used for the latest mature open comparison. |
| Baseline runtime | tree 76dee76973928dbce72860156feb32f2d7f02f86 | Baseline side of the October 21 mature open comparison and the earlier year-1002 results. |
| Latest matched mature open | [run 39605825742](https://github.com/rax0h/all-that-endures/actions/runs/39605825742), artifact 12351885115 | Successful, matched year-1001 open-only baseline/candidate comparison. |
| Mature comparison attempt | [run 39640324933](https://github.com/rax0h/all-that-endures/actions/runs/39640324933) | Failed in comparison setup before measuring the requested candidate step/save. |
| Older year-1002 save | [run 39212571079](https://github.com/rax0h/all-that-endures/actions/runs/39212571079), artifact 12176425731 | Simulation/save timings on runtime commit 2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a, tree 76dee76973928dbce72860156feb32f2d7f02f86. |
| Older year-1002 audit | [run 39285440335](https://github.com/rax0h/all-that-endures/actions/runs/39285440335) | Full audit of the exact year-1002 database produced by the save run above. |
| Older year-1002 logical digest | [run 39302259054](https://github.com/rax0h/all-that-endures/actions/runs/39302259054) | Full canonical logical digest of the same saved world. |

No in-progress or queued candidate workflow was present at the time checked. The failed comparison was not a product result: its baseline setup imported a profiling helper absent from the baseline checkout, and candidate setup created the output directory before code attempted to create that same directory with exist_ok=False. The comparison therefore has no step/save receipt. It should be rerun only after repairing the harness; this investigation did not rerun it.

The current branch head is a documentation/harness head, not an architecture acceptance or release approval. The October 21 candidate run passed its full suite and open-only matched workload. Its source does not change persistence format, simulation rules, clock, or RNG. That does not establish a mature step/save performance result.

### Storage and operation model

The implementation combines:

- A transactional SQLite store with record, segment, query-membership, receipt, and head tables.
- Versioned mutable records and relationship/query projections, with generation intervals and indexes.
- Immutable, chunked causal event-log segments plus a bounded in-memory tail/cache.
- Exact typed serialization and checksums; stable IDs and identity occurrence/owner structures.
- A pinned generation during load and reads, then a prepared multi-family save plan.
- One SQLite transaction that writes changed records, relationships/index memberships, new segments, head metadata, and a durable receipt before publishing participants in memory. The save path handles stale generations and ambiguous acknowledgements.
- Full verification that includes SQLite structural and foreign-key checks plus application-level row, version, identity, membership, and payload validation.

Source pointers at the candidate product commit:

- [Incremental store schema and transaction setup](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/incremental_store.py#L321-L380), [open/check behavior](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/incremental_store.py#L528-L675), and [commit plus full store verification](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/incremental_store.py#L872-L1108).
- [Versioned lazy-store tables and indexes](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy_store.py#L165-L321), [checked version reads](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy_store.py#L1318-L1387), and [full historical verification](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy_store.py#L3142-L3310).
- [Hybrid save preparation](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy.py#L14488-L14510), [transaction and publication](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy.py#L16508-L16794), and [pinned world open/reconstruction](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy.py#L18027-L18310).
- [Owner identity proof cache bounds and invalidation epoch](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy_identity_catalog.py#L450-L513) and [identity-group reconstruction](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_lazy_identity_catalog.py#L740-L831).
- [Validation scope limits and invalidation](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_validation_scope.py#L1-L112), [publication proofs](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/persistence_publication_proof.py#L1-L59), and [event-log chunking/cache](https://github.com/rax0h/all-that-endures/blob/5521c094981c9a5f28f1d076453264291b534ff5/simulation/ate_sim/event_log.py#L38-L180).

The “lazy” store is lazy for many payload families, not a guarantee that opening a world touches only a constant number of rows. Open checks manifests and head inventory, reconstructs eager authorities and event tails, activates identity catalogs, synchronizes identity routes/peers, and may load household pages. Some of these operations must inspect current relationship membership to rebuild in-memory identity structure.

The current normal/default checkpoint path remains separate from the opt-in/complete lazy-store path; the legacy checkpoint uses whole-object pickle/hash materialization. Existing design notes state that arbitrary past-year snapshots are not currently saved: the persistence contract is exact current state plus retained causal history. Confirm that this is still the intended product contract before designing time-travel checkpoints.

### October 20 Astra review scope

The dated October 20 Astra document is [STAGE_0_5_RESTORE_DIGEST_LAUNCH_REVIEW.md](https://github.com/rax0h/all-that-endures/blob/7c9dfcd5ade194bf049fc2500896bb80e36cd03e/simulation/STAGE_0_5_RESTORE_DIGEST_LAUNCH_REVIEW.md). It is a narrow restore-digest launch review, not a broad persistence architecture verdict.

The broad [STAGE_0_5_FINAL_ARCHITECT_REVIEW.md](https://github.com/rax0h/all-that-endures/blob/7c9dfcd5ade194bf049fc2500896bb80e36cd03e/simulation/STAGE_0_5_FINAL_ARCHITECT_REVIEW.md) is dated October 8 and says the candidate is blocked, with findings including clean-cache sidecars, lifecycle guarding, and eager unbounded household membership. The later [repair closeout](https://github.com/rax0h/all-that-endures/blob/7c9dfcd5ade194bf049fc2500896bb80e36cd03e/simulation/STAGE_0_5_FINAL_REPAIR_CLOSEOUT.md) says R1/R2 were repaired but R3 was not integrated as default. The [final candidate handoff](https://github.com/rax0h/all-that-endures/blob/7c9dfcd5ade194bf049fc2500896bb80e36cd03e/simulation/STAGE_0_5_FINAL_CANDIDATE_HANDOFF.md) keeps final architecture acceptance and performance/release approval open. Astra should resolve these open gates separately from the perf candidate’s measured open improvement.

## 2. Measured baseline and cost evidence

### Latest mature matched comparison: open only

The October 21 comparison used the same accepted year-1001 source database (29,922,463,744 bytes; SHA-256 4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2), same harness SHA-256 2eb34ae9e5d6ece98cfd559536fa110cd3b09ed9172fdb5802e100f23abc5047, Linux x86_64, Python 3.12.15, and SQLite 3.45.1. cProfile was disabled.

| Open metric | Baseline | Candidate | Change |
|---|---:|---:|---:|
| Wall time | 1,066.019 s (17m46s) | 439.424 s (7m19s) | 2.426× faster; 58.8% lower |
| CPU time | 1,065.778 s | 439.234 s | Wall and CPU nearly coincide in this runner |
| Peak RSS | 286,957,568 B | 285,458,432 B | Essentially unchanged |
| Checked payload rows | 826,945 | 628,525 | 24.0% fewer |
| Checked payload bytes | 5,686,366,597 B | 2,304,298,297 B | 59.5% fewer |
| Metadata rows | 4,496,867 | 2,749,351 | 38.9% fewer |
| Pin rows | 2,943,702 | 239,254 | 91.9% fewer |

This is a substantial candidate improvement and direct evidence that avoidable open work was removed. It remains 43.9× slower than the 10-second load goal and 219.7× slower than a 2-second goal. The harness copied and hashed the source before the measured open phase, but cold/warm cache state was not controlled. Near-equal wall and CPU time suggests CPU-heavy work in this workload; it does not rule out storage/cache effects. No cProfile, OS disk counters, page faults, or SQLite cache-hit counts were recorded.

### Older mature year-1002 result: prior runtime, not current candidate

The saved database was 30,224,322,560 bytes (30.22 decimal GB), SHA-256 02ac8fb650d0b34df47c642c8bacec3490404b6786fe39d9b0af3f02c04d1d13, year 1002, generation 127. The precise timings were:

| Operation on that artifact | Wall time | CPU time | Application I/O counters |
|---|---:|---:|---|
| Open | 833.923 s (13m54s) | 830.058 s |  — |
| Simulate one year | 3,430.776 s (57m11s) | 3,358.600 s | 7,532,042 payload reads; 7,510,547,757 B read; 0 payload writes |
| Save year 1002 | 2,923.698 s (48m44s) | 2,897.544 s | 2,235,142 payload reads; 11,489,950,851 B read; 219,865 payload writes; 67,919,926 B written |
| Full Store audit | 4,647.825 s (77m28s) | 4,514.688 s | 10,740,876 payload reads; 5,618,350,053 B read; 0 payload writes |
| World logical digest | 4,390.860 s (73m11s) | 4,126.336 s | 12,356,683 payload reads; 3,245,576,960 B read |

The audit and digest operated on the exact database produced by the save run. The audit’s original and all-25 counters matched; the digest’s original and counters matched. These are earlier runtime results, not measurements of the October 21 runtime tree.

The save read about 169× as many payload bytes as it wrote. This is strong evidence of read amplification, but not a diagnosis of which subsystem caused each read. The source shows preparation, identity reconciliation, snapshot verification, and publication checks as plausible contributors; no mature current-candidate profile apportions them. One simulation year’s 7.51 GB reads and zero payload writes similarly show that a “no writes” step can still be dominated by read/validation work.

### Earlier diagnostic profiles

- October 13 year-7/generation-4 profile: open 71.137s; a one-year phase was interrupted at 90s. cProfile and SQLite VM counters showed 1,360 calls to read_identity_group at 61.525 cumulative seconds; action synchronization and eager peer stitching were major overlapping costs. It is diagnostic only, not a mature comparison.
- A later bounded year-7-to-8 profile on an earlier repair candidate measured open 21.970s, simulation 47.063s, save 26.618s, audit 14.878s. The year-8 profile showed 320 packed actions improve from 10.730s / 329 group reads to 0.007175s / 0 group reads after the repair. This is direct work-count evidence for a specific optimization, not a mature whole-world ratio.
- Old INCREMENTAL_PERSISTENCE.md reports year-2000 save/load 127.323s/156.841s and year-3010 full hash 188.563s in a different path/environment. Do not compare these as if they were measured by the current lazy-store harness.

### Fixed-work scale evidence

The final handoff’s synthetic H=1,000 and H=10,000 fixtures show flat counters for selected fixed-size edits:

| Fixed operation | H=1,000 | H=10,000 |
|---|---:|---:|
| Shared-child point edit/save: payload reads / writes | 114 / 14 | 114 / 14 |
| Settlement scalar edit with imported memory: payload reads / writes | 31 / 6 | 31 / 6 |
| Event-ID NaN point add/save: payload reads / writes | 203 / 27 | 203 / 27 |

These fixtures support age-independent work for these exact point operations. They do not establish constant-time open, simulation, whole-world save, digest, audit, or real-world elapsed time. Caller-held parent tuples/text also grow with the input supplied. The tests reject payload reads and writes for true no-op saves, while still disclosing fixed metadata work. See the [candidate handoff scale table](https://github.com/rax0h/all-that-endures/blob/7c9dfcd5ade194bf049fc2500896bb80e36cd03e/simulation/STAGE_0_5_FINAL_CANDIDATE_HANDOFF.md).

## 3. Ranked bottlenecks

| Rank | Bottleneck | Evidence and confidence |
|---|---|---|
| 1 | Open-time metadata, payload, and identity reconciliation | **Measured:** latest candidate open is 439.4s, with 2.30 GB payload bytes, 628k payload rows, 2.75m metadata rows, and 239k pin rows. **Source-supported:** open reconstructs the identity catalog and validates current relationships under a stable pin. The remaining exact split among identity traversal, metadata queries, checksum/codec, and reconstruction is unknown. |
| 2 | Save preparation/publication read amplification | **Measured, older runtime:** year-1002 save read 11.49 GB for 67.9 MB of payload writes, over 2.2m reads. **Source-supported:** save prepares per-family snapshots/identity/index plans, commits atomically, then validates and publishes participants. **Unproven:** which exact layer dominates the 11.49 GB and whether candidate 5521 materially changes it. |
| 3 | Simulation-time payload reads and verification | **Measured, older runtime:** year step read 7.51 GB across 7.53m payload reads and wrote no payloads. **Source-supported:** every checked lazy version read verifies row and payload checksums before decode/use. **Unproven:** share attributable to actual simulation dependencies versus owner/link synchronization and repeated database validation. |
| 4 | Full audit and full logical digest | **Measured, older runtime:** audit 77m28s and logical digest 73m11s. **Source-supported and expected:** both traverse broad historical/current structures to establish complete proofs; verify_all includes retained historical versions, indexes, identities, and payload rows. Full logical digests necessarily process the logical content they commit to unless a trusted incremental proof is accepted. |
| 5 | Physical copy/hash/restore overhead | **Measured:** older restore preparation included roughly 138s hashing and 198s copying; year-1002 DB was 30.22 GB. This work is outside the measured open phase but matters to backup/restore operations. Artifact ZIP was about 4.48 GB. **Unknown:** current candidate end-to-end restore/copy elapsed and hardware bandwidth. |

## 4. Unavoidable work versus repeated work

### Intrinsic to the contract

- Execute deterministic rules over the causal inputs and active objects actually needed for the requested simulation step.
- Encode and durably publish genuinely changed state, new events, identity relationships, index membership deltas, generation metadata, and a recovery receipt.
- Establish correctness on first import or when a payload/relationship is changed or newly introduced.
- Read and hash every relevant byte for an explicitly requested full physical scrub; read all logical inputs for an explicitly requested fresh full-state digest unless a previously trusted proof structure is part of the definition.
- Preserve exact object identity, shared references, ownership, ordering, event IDs, RNG/counter state, and generation consistency during load, save, and recovery.

### Likely avoidable or batchable

- Re-encoding/re-hashing a payload multiple times within one pinned transaction or validation scope.
- Re-traversing an unchanged owner graph, shared identity group, query result, or head inventory once its exact generation-bound proof has been checked and invalidation is reliable.
- Re-reading all affected owners when a precise mutation journal already identifies the changed owner/link closure.
- Whole-history work for a fixed-size point edit, no-op save, or ordinary load when no old history-dependent query is requested.
- Rebuilding indexes that are already transactionally maintained, if their consistency can be proved without a full scan.
- Per-row SQL/codec overhead from poor batching or repeated metadata queries, if profiles establish those costs.
- Cold data rereads on each operation where the exact same immutable bytes and generation have already been validated and proof reuse is anchored to that same database/codec/pin epoch.

The current code already implements bounded caches and scoped proof reuse, with strict invalidation for writes, data/schema version changes, database closure, and borrowed transaction boundaries. This is the right safety shape. The key architecture question is whether more exact committed proofs can be persisted or reused without weakening the proof contract.

## 5. Existing optimizations to retain

Retain these unless a measured alternative proves better without weakening correctness:

- Small bounded owner proof caches and exact epoch checks.
- Mutation journals and dirty-owner deltas for identity/index publication.
- ValidationScope reuse only within the same database, codec, pin, and unchanged SQLite epoch.
- Immutable event segments and bounded chunk cache; avoid rebuilding or decoding the whole causal log for ordinary point operations.
- Versioned current mutable records and maintained query-membership indexes.
- Generation pinning and one atomic SQLite publication of data, indexes, head, and receipt.
- Exact-once/ambiguous-ack recovery and participant publication checks.
- No-op save short-circuit and explicit no-payload-read/no-payload-write assertions.
- Typed exact identity and ordering representation; reject unsupported mutation paths to the slower full reconciliation path.
- SQLite rollback journal with synchronous FULL until matched I/O/fsync measurements justify a different durability mode. Durability semantics should not be traded for a guessed speedup.
- Current semantic checks for structural/reentrant/custom-hook/nonfinite mutation paths; fast routes should remain limited to cases that prove they preserve hook and identity behavior.

The October 21 repair’s indexed scalar assignment fast path is constrained by full pending-placement reconciliation, exact database/topology checks, unchanged hooks, and exact assigned value. Material selection uses an identity-free scalar projection and removes unused heaps. These are reasonable local optimizations; the open result demonstrates benefit, but not save/step effect.

## 6. Architectural alternatives, including keeping the design

| Option | Potential value | Costs and risks | Current assessment |
|---|---|---|---|
| Keep current architecture; profile and remove redundant work | Preserves semantics and existing transaction/recovery model; lowest migration risk. | Requires careful proof-boundary work; current implementation still too slow. | Best-supported next path. The candidate already demonstrates a large open improvement without a format change. |
| Persist per-segment/per-owner cryptographic commitments or Merkle proofs | Point verification can read target content plus a logarithmic proof path; unchanged subtrees can be carried forward by reference. | Proof/index storage, hash CPU, update amplification, more complex atomic publication/recovery; must anchor root outside the mutable archive or protect it independently. Does not detect a corrupted leaf whose bytes are not reread. | Investigate after stating the trust model and measuring current checksum/validation costs. |
| Add periodic materialized state checkpoints plus append-only delta/event segments | Bounds replay distance and can make recovery/resume predictable while preserving the full causal log. | Each checkpoint costs O(size of materialized state); must preserve stable IDs, shared references, owner ordering, RNG/counters, ruleset version, and exact event boundary. Does not make full history scrub sublinear. | Could complement current model. Event log already uses immutable segments; test whether additional mutable-state checkpoints solve a measured open/recovery cost. |
| SQLite WAL mode | Can reduce writer synchronization cost and let readers continue beside an active writer. | Still a single writer; checkpointing, long readers, WAL retention/backup packaging, and restore complexity. It does not eliminate CPU spent traversing records, checksumming, or rebuilding identity state. | Do not switch based on these data: old timings are nearly CPU-bound and current timings lack SQLite/fsync counters. Benchmark only if writes/fsync are shown dominant. |
| Different transactional engine, such as an LSM store | May improve point access, batching, checksums, and write throughput for suitable workloads. | Cross-family atomicity, multi-index consistency, snapshots, backup, crash recovery, compaction/write amplification, and identity publication must all be re-proven. Migration is large and current evidence does not isolate SQLite as the dominant bottleneck. | No evidence now supports wholesale storage-engine replacement. |
| Event sourcing as the sole source of truth | A compact append log can preserve causal ordering and deterministic replay. | Replay cost grows with history; not all exact current state may be recoverable from events; event schema evolution and deterministic replay across code versions are hard. | Unsuitable alone without bounded snapshots and proof that every state transition is represented exactly. |
| Resumable/background scrubbing | Moves full scan out of save/load latency; allows bounded per-operation budgets and progress tracking. | Detects corruption later; requires persisted cursor, generation pin/manifest, repair source, retention/restart semantics, and alerting. It does not reduce total bytes to be checked. | Strong candidate for routine bounded verification, while keeping explicit full audit available. |

Official design references for comparison: [SQLite WAL](https://www.sqlite.org/wal.html), [SQLite online backup](https://sqlite.org/backup.html), [SQLite integrity_check / foreign_key_check](https://www.sqlite.org/pragma.html#pragma_integrity_check), [RocksDB checksums and full VerifyChecksum](https://github.com/facebook/rocksdb/wiki/Basic-Operations), [RocksDB checkpoints](https://github.com/facebook/rocksdb/wiki/Checkpoints), [PostgreSQL checksums](https://www.postgresql.org/docs/current/checksums.html), [PostgreSQL backup verification](https://www.postgresql.org/docs/current/app-pgverifybackup.html), and [RFC 9162 Merkle inclusion/consistency proofs](https://www.rfc-editor.org/rfc/rfc9162.html).

## 7. Correctness, integrity, and recovery risks

- **A stored root alone is not a byte scrub.** Checking that a manifest contains a root takes bounded time, but if the root is stored beside mutable data it is not an independent trust anchor. Even with an independently trusted root, a physical archive scan must read and hash bytes to discover latent corruption in untouched records. A Merkle proof can authenticate a leaf only after the actual leaf bytes are hashed and compared with that leaf’s committed hash.
- **Integrity layers answer different questions.** SQLite integrity_check checks database structure; foreign_key_check is separate. ATE’s verify_all additionally checks application payloads, historical versions, identity occurrences, query/order structures, and semantic constraints. World.digest is a canonical logical-world/event digest. An external file hash checks an exact file image. None is a substitute for all the others.
- **Proof reuse can be safe, but only with strict boundaries.** The repository already binds bounded proof reuse to database identity, codec, pinned generation, SQLite total_changes/data_version/schema_version, and transaction ownership. A future persistent proof scheme must atomically commit data and proof root, detect partial/corrupt proof structures, define the root trust anchor, and test crash recovery at each publication boundary.
- **Deferring checks trades detection latency.** Background scrubbing can satisfy bounded service budgets but a latent fault may remain undetected until that segment is visited. Keep synchronous checks on changed/used data and provide a complete resumable archive scrub with clear status.
- **Index and identity corruption can be semantically worse than a checksum error.** A missing or stale link may create duplicate objects, break shared references/ownership, or make deterministic continuation diverge. Any fast path must prove both payload correctness and graph/index agreement, or force the existing complete reconciliation path.
- **Format migration risks history and exact continuation.** Checkpoint/Merkle/LSM changes must preserve event IDs, stable object IDs, shared-reference topology, order, generation boundaries, RNG and allocation counters, codec/rules version, and the ability to recover an ambiguous commit without applying it twice.

## 8. Long-term scaling and target assessment

| Age / operation | Evidence or projection | Assessment against goals |
|---|---|---|
| Around year 1,000 | Direct older year-1002 archive: 30.22 GB. Candidate open at year 1001: 439.4s. Older save 48m44s, step 57m11s, audit 77m28s, digest 73m11s. | Current ordinary load fails <10s by 44×. Mature candidate save/step is unmeasured; old runtime is far above 1–2s and <10s goals. |
| Year 10,000 | Synthetic fixed-work point operations at H=1k and H=10k show flat payload counters for three selected edits. No whole-world year-10k elapsed benchmark exists. If archive size grew roughly in proportion to year count from the 30.22 GB year-1002 example, a year-10k archive would be about 302 GB; this is a sensitivity estimate, not a forecast. | Age-independent fixed-work edits have evidence. Whole-world open, simulation, save, logical proof and physical scrub do not. |
| 100,000 years or substantially longer | No measured fixture. Under the same explicitly hypothetical linear-size assumption, archive is around 3 TB. | Ordinary fixed-size operations need to touch only active/changed state and a bounded or logarithmic proof path. Complete physical verification remains linear in archive bytes and requires external time/bandwidth. |

A full physical read of the measured 30.22 GB archive in 60 seconds requires at least 0.504 GB/s (about 480 MiB/s) of sustained read throughput before checksum CPU, storage contention, database decoding, or error handling. At the illustrative 302 GB size, the lower bound is 5.0 GB/s; at 3 TB it is about 50 GB/s. These are ideal lower bounds, not promises. No credible claim of sub-minute full physical verification follows from current evidence.

Keep three promises distinct:

1. **Bounded routine check:** fixed byte/row budget, resumable cursor, bounded latency target such as <60s. This can be independent of total archive age per invocation.
2. **Complete logical integrity proof:** every logical record/index/identity/event is covered, either by a fresh traversal or by a previously trusted proof graph. It may be resumable; total work remains proportional to changed proof nodes or, for a fresh proof, the covered state.
3. **Full physical archive re-verification:** every stored byte is reread and checked. Its cost is linear in bytes and should be stated in throughput/time terms.

| User goal | Current evidence |
|---|---|
| Ordinary save 1–2 seconds | Not demonstrated. Earlier year-1002 save was 2,924s; current candidate matched step/save result is missing. Flat counters for selected small edits do not provide elapsed-time proof. |
| Major save under 10 seconds | Not demonstrated; current whole-world save is unmeasured. |
| Routine background verification under 60 seconds per bounded operation | Plausible with a fixed work budget and durable resume cursor; not measured here. This is not a full audit promise. |
| Ordinary load under 10 seconds | Fails current mature open result: 439.4s. |
| Historical work not linear in total age when logically unnecessary | Proven for selected synthetic point edits only. Not proven for open, simulation, general save, or full audit/digest. |

## 9. Measurements required before major decisions

1. Repair the matched mature harness and obtain candidate baseline/candidate **open, one-step, and save** receipts on identical year-1001 inputs and hardware. Do not infer save performance from open.
2. Add subphase timers and work counters for each persistence family: encode, checksum, decode, identity traversal, query/index reconciliation, SQL execution, commit/fsync, post-commit publication, event reads, and recovery checks.
3. Record per-family rows examined versus returned, SQL statement counts and SQLite VM steps, bytes decoded/hashed, identity groups/occurrences, changed records/events, and indexes updated.
4. Capture OS physical bytes read/written, page faults, SQLite page/cache hits/misses, IO wait, storage type, write/fsync latency, CPU profile, allocation/GC, and process RSS. Separate application payload counters from device reads.
5. Run controlled warm-cache and cold-cache trials. The current harness copies and hashes the input before open, so cache warmth is not established by the open phase timer.
6. Measure actual changed-object and event counts for ordinary turn, major event, and no-op save. Compare observed rows/bytes with true dirty set and dependency closure.
7. Time verify_all, World.digest, and external file hashing independently; document what each proof means and whether its scan includes all versions, current state, event history, indexes, or SQLite pages.
8. Measure full database growth by year and by object/event family; report bytes per simulated year, retained versions, index bytes, and compaction/cleanup cost.
9. Specify target hardware and storage throughput before assigning wall-time gates. Confirm any save checkpoint/backup path includes a consistent SQLite snapshot and the full event/state generation.
10. Validate crash recovery, ambiguous acknowledgements, and corruption detection/repair on fault-injected copies before widening proof reuse or changing journal mode.

## 10. Questions Astra must resolve

1. Is the contract exact current state plus a complete causal log, or must the system restore the exact world at any arbitrary past year? Current design notes say arbitrary old snapshots are not stored.
2. Which targets are hard release gates, and on what reference hardware/workload: 1–2s ordinary save, <10s major save, <10s ordinary open, and <60s bounded verification?
3. Which validations must block open/save, and which may be deferred to resumable background scrubs? In particular, must unchanged identity groups be traversed on every open once an exact generation-bound proof is committed?
4. What corruption threat is in scope: accidental device bit rot, partial writes, software bugs, malicious edits, or coherent archive replacement? Where is the trusted root anchored?
5. What is the repair source and recovery promise after a checksum/root failure: replica, backup, event replay, previous checkpoint, or fail-closed detection only?
6. May a previously validated proof for immutable bytes survive later commits, and what exact database/pin/codec/root conditions invalidate it?
7. Is 1–2 seconds expected for a single point edit, a normal full turn with many state changes, or every save? What active-state and changed-set bounds define “ordinary”?
8. Is a full physical scrub allowed to complete over hours/days with resumable progress while every invocation stays under 60 seconds? If yes, what detection-latency SLA is acceptable?
9. Should DELETE + FULL durability remain, or do measured fsync/write costs justify testing WAL? What consistent backup and reader-retention behavior is required?
10. Are Stage 0.5 R3 household-members integration and remaining architecture/release blockers still open? The October 20 restore-digest review does not resolve the October 8 broad architecture findings.
11. For any checkpoint, proof tree, or new engine, how are stable object IDs, shared-reference topology, owner links, insertion order, event IDs, RNG state, counters, schema/rules version, and exactly-once recovery preserved?

## Independent conclusion

ATE’s high-level architecture is appropriate in shape for a world that must retain exact state, identity, relationships, deterministic continuation, and causal history: mutable state is versioned incrementally, causes are retained in immutable segments, and publication is transactional. Those are valuable foundations and should be retained unless the next matched profiles show a specific structural mismatch.

The **current implementation and operational path are not yet suitable for the stated scale or latency goals**. The latest candidate demonstrates a large, real open-path improvement, yet measured mature open still takes 7m19s. The year-1002 historical results expose severe read amplification and multi-minute full verification, but cannot attribute the cause to the October 21 candidate. The current candidate’s mature step/save outcome is unknown because the comparison harness failed before measurement.

The defensible next move is to repair that harness, profile the candidate end to end, and reduce repeated reconciliation/checksum/metadata work by extending the existing generation-pinned proof and mutation-journal model where its invalidation rules are exact. Keep full audit and physical scrub as explicit, resumable linear work. Consider persistent Merkle roots, more checkpoints, WAL, or another engine only when the missing measurements show which cost they address and the trust, recovery, identity, and history semantics are specified.

This report does not approve merge or release. It resolves the evidence handoff; Astra still owns the architecture and release decision.
