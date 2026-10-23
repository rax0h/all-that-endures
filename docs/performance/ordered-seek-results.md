# Root-selected retained-generation pages

Accepted predecessor [CI39909955729](run-39909955729/acceptance.json):3354 tests plus2 subtests,260 proof cases,all six diagnostics. This successor adds an inactive immutable ordered index and exact root-selected occurrence source. No World reader/writer or format capability is activated.

## Implemented boundary

`OrderedSeekMap` stores domain-separated immutable radix nodes over exact byte keys and32byte commitments. Terminated nibble paths preserve empty/prefix/NUL and arbitrary absent cursor order. Streamed sorted construction writes final nodes only; point updates spill ancestors to SQLite TEMP workspace and copy only the changed path. No recursion, full Python mapping or retained clean-node cache. Caller owns schema/write transaction and rollback; no node collection.

`SeekOccurrenceCertificate` binds store/codec/generation/scope/allocator and ordered root/count to mandatory external expected authority. The root supplies complete committed logical membership; each returned placement is fetched through exact interval indexes and checked for overlap, interval, allocator, checksum and committed content. Newer physical rows are never scanned for ordering. Empty committed roots return exact emptiness. Unselected physical surplus/corruption is not discovered by this bounded read and requires full inventory audit; it never enters results. Full inventory conformance at construction/transitions remains mandatory before activation.

Individual fields above4096bytes still require a separately budgeted path. The original occurrence adapter retains its explicit newer-frontier budget rejection. This new source is a component, not production World previous-generation support.

## Corrected measurements

| Index entries / newer placements per group | Point node reads / writes | Point heap / time | Old group / owner / empty VM upper bounds | Old group / owner / empty time |
|---:|---:|---:|---:|---:|
| 1,000 | 4 / 4 | 12,982 B / 4.397 ms | 1799 / 1699 / 999 | 3.094 / 1.396 / 1.121 ms |
| 10,000 | 5 / 5 | 12,738 B / 4.977 ms | 1799 / 1699 / 999 | 4.265 / 2.307 / 0.840 ms |
| 100,000 | 6 / 6 | 15,274 B / 9.595 ms | 1799 / 1699 / 999 | 3.320 / 1.330 / 0.552 ms |

All results are exact with zero owner/history payload SELECTs/checks/decodes and zero old-pin budget rejections. Each measured old group has1k/10k/100k newer archive placements, including the old nonempty group1 and old empty group2. Old group fanout8, owner paths2, page4 remain fixed. Selected owner paths include still-open and just-closed placements after reassignment/deletion. Current root counts and a literal current page are checked. Point results retain the old root and match a full canonical rebuild.

[Clean source receipt](ordered-seek/scaling/source.json): local2746c5b0261a4299377fef5ab01437a4aa3c34a4, runtimedcea4f0686b6ceb7bc4eaacc3441236c4ad08327; driver and fixture hashes are recorded. [Full corrected measurements](ordered-seek/scaling/summary.json).

These are instrumented single observations, not a latency distribution or matched World speedup. Filesystem caches are sequential/warm/uncontrolled. SQLite main/temp caches2MiB each, temp_store FILE; Python clean-node cache0. VM bounds use100-instruction progress ticks. Full source fixture construction, verified root construction, genuine2*size placement transition, full index verification/rebuild, database size and process lifetime RSS are reported separately in raw receipts. Point timing includes SQLite commit; it does not represent World save.

## Review and validation

The first scaling driver populated only the empty old group with the large newer frontier. Fresh review identified this Important evidence gap. Two population assertions reproduced RED; the corrected test/driver give EACH measured group size newer placements and assert real database counts. Initial scaling is superseded and is not accepted evidence. Minor parser boundary coverage was added in the same pass. No runtime defect was found or runtime repair needed. All declined-to-judge behaviors are explicitly ruled in [review and rulings](ordered-seek/final-review.md); no additional review round.

53 focused cases and406 affected proof/store/failure/validation-scope/identity cases pass. AST/YAML/bash and diff checks pass. RED logs also retain missing-module tests, active-stream TEMP schema locking and excessive initial construction writes; fixes use reusable workspace with DML cleanup and final-only sorted construction.

## Remaining integration gates

Complete owner/group/link/reference-projection cross-consistency, existing owner radix/header agreement, retirement/absence, namespace proofs, manifests, retained root AND ordinary payload availability, verified-copy/writer fencing, atomic existing row/root/head/receipt publication and canonical World admission/consumption. No main merge, endurance or mature speed claim. Open<=10s, incremental save<=2s and warm year<=1s remain unmeasured.

Successor full-suite and seven diagnostics CI awaits publication/launch. Parent green is separate evidence. Authenticate the successor artifacts and source before acceptance; do not poll long tests.

## Published successor

Exact-tree candidate641a0c23c83b0cc097a799e284890f61493d5bc1 matches local964113f95d8a0789b94bdc3d2724bdc99721a4b3 treeafc3b4c678078b6ee7af4d69146c1d7f1e2d231b and measured runtimedcea4f0686b6ceb7bc4eaacc3441236c4ad08327. Only sol/durable-proof-map advanced using the exact expected-parent lease. [Run39961497870](https://github.com/rax0h/all-that-endures/actions/runs/39961497870) is in_progress with the full simulation suite and seven bounded-work diagnostics. Acceptance is pending; [launch/resume receipt](ordered-seek/ci-launch.json). Authenticate successor artifacts/source on green before continuing integration; inspect this run on failure. No long-test polling or predecessor-success substitution.

## Successor accepted

Run39961497870 completed green:3407 tests plus2 subtests,1 warning,6587.44s;313 proof cases and all seven diagnostics. Downloaded SHA256 digests, source head/runtime receipts and corrected newer-frontier populations match. [Acceptance and raw evidence](run-39961497870/acceptance.json). This supersedes pending status above.
