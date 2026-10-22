# Proof transition inputs — 2026-10-22

The previous immutable map branch passed [run 39830820929](https://github.com/rax0h/all-that-endures/actions/runs/39830820929): **3134 tests plus two subtests**, one warning, in 4106.90 seconds. Both CI artifacts were downloaded, authenticated against GitHub's SHA256 digests and retained under [run-39830820929](run-39830820929/acceptance.json).

This next bounded package implements two prerequisites from [Astra's architecture](../superpowers/specs/2026-10-21-ate-incremental-proof-design.md). It does not activate proof authority in World or remove any current check. Interactive speed targets remain unmet/unmeasured on this package.

## Implemented

`persistence_proof_batch.update_sorted` merges a strictly locator-sorted stream into an accepted immutable map. It reuses unaffected roots, checks affected paths and deletion boundaries, and writes each final changed node once. It keeps one lookahead change and a bounded radix frontier; no full delta dictionary, internal sort, clean-node cache, commit or head publisher. Caller transaction rollback remains necessary after callback or late stream errors.

`persistence_proof_content` binds exact source namespace/key, version identity, codec/schema, membership bytes or event boundaries, and actual payload bytes. Tags separate versioned records, ordinary records and segments. It never decodes typed values or substitutes a stored checksum for payload bytes. `valid_to` is excluded from immutable content; an actual LazyRecordStore interval-close test confirms the old version's content commitment survives while its existing mutable interval checksum changes and its old pin remains readable. Existing interval selection remains checked separately.

The helpers have no reader/admission authority. In particular, retaining a proof node does not retain an overwritten ordinary record's payload. Payload retention, as well as root retention, must be solved before World activation.

## Bounded construction evidence

Source `19eb0a1acb466de882743edd5c3370e12a7f77c0`, runtime tree `ffac58e621ffe05e060f97ff7be8f030c5dfe303`, driver SHA256 `177bc4e0e2b40943e2b64a828213f7da60fcb4e38ccf2b5ff3fd00b794b567dc`. The [source receipt](proof-transition-inputs/source.json) records Python 3.12.14 / SQLite 3.53.1 and platform. The final measured runtime is unchanged by subsequent test/documentation edits.

Each case starts an independent map, spills exact keys to a SQLite TEMP table ordered by domain locator, then constructs the final map in one caller transaction. SQLite main and temp caches are capped at 2MiB each, temp_store=FILE. The batch timing/heap includes merge, node encoding, actual SQLite writes and commit with tracemalloc; completed spill staging is reported separately. A complete checked traversal uses a SQL-backed visited inventory and proves every physical construction node is reachable from the final root, with zero surplus/transient nodes. This audit is outside the construction/point timers.

| Keys | Final construction nodes | Batch traced heap | Batch time | Point reads / new nodes | Point traced heap | SQLite file after point |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 1,350 | 77,312 B | 0.100 s | 4 / 4 | 80,383 B | 266,240 B |
| 10,000 | 13,850 | 341,242 B | 1.067 s | 5 / 5 | 78,053 B | 2,523,136 B |
| 100,000 | 137,297 | 783,050 B | 11.019 s | 6 / 6 | 81,201 B | 24,809,472 B |

Staging took 0.002 / 0.021 / 0.290 seconds; peak TEMP page inventories were 18 / 154 / 1488 pages of 4096 bytes. Process RSS includes all previous phases and is not a phase peak. Final logical roots exactly match the prior sequential diagnostic at each size. The earlier 100k sequential fixture retained 546696 nodes / 358686720 bytes, including all transient ancestors; batching removes that unnecessary construction retention. These file sizes compare construction/retention strategies, not a controlled hardware latency comparison or a mature save forecast. Root-aware collection is still required for future accepted transitions.

Measured fixed batch edits took 7.1 / 8.0 / 11.3 milliseconds including tracing, under workload bounds of <=66 node reads, <=65 new nodes and <512KiB traced heap. Those are this workload's gates, not a universal total-IO bound for arbitrary deep deduplicated updates. All measured point SELECTs addressed proof nodes. No World payload table or real save exists in the diagnostic. [Raw JSON and logs](proof-transition-inputs/summary.json) retain the exact observations.

## Validation and remaining work

Batch and content tests were observed failing on missing modules before implementation. The combined proof/incremental-store/failure suite passed **125 tests**, most recently in 5.39 seconds (the retained first final run took 5.11 seconds). [Final focused log](proof-transition-inputs/final-focused.log) records that first final run. A fresh [independent review](proof-transition-inputs/final-review.md) found no Critical/Important issues; two optional failure-path regression cases are deferred after passing its real SQLite probes. The separate full simulation suite must run again on the published successor; the green parent run is not a successor result.

The next architecture boundary is complete topology/group/owner and ordered query commitments, then manifest authority, exact ordinary-payload retention, root reachability/GC, verified copy and writer fencing. Changed rows and successor roots must join the existing commit/receipt transaction before World save/open consumes them. Canonical lazy action admission, bounded physical scrub and actual mature year-1002/year-1003 equivalence remain required. No main merge, endurance run or performance acceptance is performed here.
