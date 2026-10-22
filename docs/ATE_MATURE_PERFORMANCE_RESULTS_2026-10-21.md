# Mature performance repair: verified results and next architecture handoff

The October 21 performance candidate preserves the accepted year-1002 logical
state and improves load time substantially. It remains far from interactive
performance: a warm simulation year takes 35m58s and saving takes 36m31s.

## Verified execution and evidence

- Successful [run 39647739463](https://github.com/rax0h/all-that-endures/actions/runs/39647739463),
  commit `2749092cdd8e3a910746223079ef4d9ed582364e`.
- Baseline runtime tree: `76dee76973928dbce72860156feb32f2d7f02f86`.
- Candidate runtime tree: `48e3e21b3b8d4ccb57eab74e11412a1ec4e74b6a`.
- Both lanes downloaded and authenticated the same accepted year-1001 source:
  29,922,463,744 bytes, SHA-256
  `4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`,
  seed 843000, generation 126, store `06d24556-2bb1-4086-93f7-448f23b7eb5a`.
- Both used the same unprofiled measurement harness and common helper. The
  reported Linux platform, four-CPU count, Python 3.12.15 and SQLite 3.45.1
  matched. The lanes ran on separate hosted runner instances; physical hardware
  equivalence and filesystem cache state were not established.
- Comparison ZIP artifact `12383706612` is 14,876 bytes, SHA-256
  `60c4a23e70d8cb7c94335826cb25f45d7efc99a2c07968eec52f1185db69e03e`.
  Its checksum was verified, both original lane ZIPs were independently
  downloaded and checked against GitHub's archive digests, and their receipt
  bytes exactly match the comparison artifact. Recomputing the comparison from
  those receipts reproduced its published result.

Unmodified receipts and the authentication manifest are retained in
[performance/run-39647739463](performance/run-39647739463/provenance.json).
This result supplements the
[Luna investigation](LUNA_ATE_PERSISTENCE_PERFORMANCE_INVESTIGATION_2026-10-21.md),
whose current-candidate step/save measurements were still pending when written.

## Phase times

| Operation | Baseline | Candidate | Speedup | Time reduction |
|---|---:|---:|---:|---:|
| Open year 1001 | 13m22s | 5m13s | 2.56x | 60.9% |
| First step, 1001 to 1002 | 49m25s | 40m47s | 1.21x | 17.5% |
| Save year 1002 | 43m44s | 36m31s | 1.20x | 16.5% |
| Warm step, 1002 to 1003 | 38m08s | 35m58s | 1.06x | 5.7% |

The sum of these measured phases fell from about 2h24m39s to 1h58m29s,
roughly 18.1%. Copying, source/file hashing, teardown, artifact transport and
fresh verification are outside that sum. These are one sample per lane, not a
statistical benchmark or an endurance/scaling acceptance.

## Correctness boundary

Both lanes saved exactly year 1002 at generation 127, then measured year 1003
without saving it. After the timing process closed, a separate Python process
opened each saved database and checked its initial file hash/size, seed, year,
store identity, generation and canonical world digest. Both reproduced:

`2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7`

The accepted input file remained unchanged in both lanes. The saved databases
were the same size, 30,224,322,560 bytes, but had different physical SQLite
hashes. Opening and closing the restore sessions also changed physical file
bytes; both receipts disclose this. The matching canonical digests establish
the year-1002 logical-state result, not byte-identical SQLite images.

These were fresh-process reopens of closed per-lane output files on the same
runner. The new year-1002 databases were not uploaded and downloaded as separate
checkpoint artifacts. The warm year-1003 state received no canonical digest or
save/restore check. This run did not repeat a full store scrub, authorize a
merge/promotion, or establish arbitrary future-year correctness.

## Remaining cost, measured on the candidate

| Metric | First step | Save | Warm step |
|---|---:|---:|---:|
| Payload read requests | 5,424,484 | 1,651,746 | 4,208,498 |
| Payload bytes read | 6,996,367,496 | 8,601,872,232 | 6,814,005,703 |
| Payload check requests | 5,914,400 | 1,918,258 | 4,302,650 |
| Payload bytes checked | 7,031,127,828 | 8,675,496,103 | 6,828,681,227 |
| Metadata rows | 24,960,411 | 9,393,932 | 19,343,646 |
| Pin rows | 11,175,267 | 8,120,143 | 14,548,916 |
| CPU time / wall time | 96.2% | 99.4% | 99.9% |

These are application counters, not physical disk reads. Read and check
counters may overlap; their byte counts must not be added as disjoint IO.
The harness did not capture application IO for its open phase; the earlier
dedicated open benchmark remains the source for that operation's IO evidence.

The save wrote exactly 219,865 payloads / 67,919,926 bytes in both lanes. The
candidate therefore read about **127 payload bytes for every payload byte
written**. This establishes substantial read amplification, while leaving its
precise division among save preparation, identity reconciliation, encoding,
publication and validation unresolved.

Warm-step payload requests fell only **0.54%**, from 4,231,275 to 4,208,498;
the read-byte volume barely moved. Pin-row work fell about 65%, but elapsed time
fell only 5.7%. This makes repeated payload processing a higher-priority
attribution target than further pin-query tuning alone. It does not prove that
every read is redundant or identify the responsible functions.

CPU time nearly equaling elapsed time, especially during save and the warm
step, strongly suggests CPU-heavy processing in these runs. It does not isolate
Python versus SQLite/codec/checksum costs or eliminate cache and storage effects.

Recorded process peak RSS fell from 3,904,737,280 to 2,473,697,280 bytes,
about **36.6%**. Memory improved materially while remaining above 2 GB.

## Next architecture assignment

Treat this candidate as a measured improvement with preserved year-1002
continuation, not completion of interactive performance work. Use the retained
receipts with Luna's source investigation to design the next package.

1. Attribute the remaining warm-step and save CPU cost to actual simulation
   rules, checked payload reads/decodes, identity/owner traversal, preparation,
   commit and publication. Prefer bounded representative profiles and explicit
   work-count regressions; do not repeat the complete mature comparison merely
   to obtain another green result.
2. Determine which unchanged payload and relationship facts can safely reuse
   generation/pin-bound proofs, and which owner/link closure genuinely changed.
   Specify invalidation, corruption detection and recovery behavior before
   implementing broader proof reuse. The counters support investigating this
   boundary, not deleting validation wholesale.
3. Preserve exact identity, causal history, RNG/counters, transactional
   publication and the accepted digest. Neither a clock reset nor a storage
   engine replacement is justified by this benchmark alone.
4. Give Sol a concrete bounded implementation package and regression gates
   based on the attributed dominant work. A future performance acceptance must
   cover active stepping and saving as well as load.

No new long-running test was launched while recording these results.
