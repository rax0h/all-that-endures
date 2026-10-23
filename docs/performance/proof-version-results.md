# Pinned raw version source adapter

The previous physical query package is accepted on authenticated [CI39890667390](run-39890667390/acceptance.json):3258 full-suite cases and162 proof tests. The new adapter supplies the next necessary boundary: exact fetched retained-version bytes bound to an externally accepted content map. No World reader/save/open/format capability selects it.

## Implemented

A VersionCertificate binds exact store/codec/generation/content root and requires an expected commitment from outer authority. One closed read joins the existing explicitly owned snapshot, checks live retained pin/context, proves content membership or absence, and fetches at most two exact-key visible source rows. Overlap, missing/surplus rows, malformed metadata, bad row/payload checksums and coherent rechecksummed payload replacement all fail closed. Returned bytes are raw, with no payload/membership decoding or identity admission.

SQL storage-class and BLOB byte-length guards precede transfer. Combined payload/membership bodies default to1MiB; callers may explicitly budget up to64MiB. Larger bodies raise VersionProofBudgetError, never an unchecked fallback. Multi-MiB malformed bodies and early-NUL TEXT checksum regression cases use less than128KiB traced heap. Previous pins retain exact prior bytes after update/delete; interval closure remains outside immutable content bindings but is checked physically.

## Fixed access diagnostic

Synthetic retained contents use the real LazyRecordStore commit and version schemas. Each case contains one fixed active people record and1k/10k/100k unrelated archive versions. Test-only content construction performs a full verification in a caller transaction and streams locator-sorted deltas via SQLite spill; it is outside the point timers. No production constructor silently certifies arbitrary local SQL. One point fetch and one exact absent key are compared to literal results and the existing checked reader.

| Unrelated versions | Presence / absence node SELECTs | Payload checks | Traced heap | Presence / absence time |
|---:|---:|---:|---:|---:|
| 1,000 | 4 / 3 | 1 / 0 | 14,601 / 12,835 B | 1.911 / 1.429 ms |
| 10,000 | 5 / 4 | 1 / 0 | 15,849 / 12,483 B | 2.233 / 1.873 ms |
| 100,000 | 6 / 5 | 1 / 0 | 15,681 / 13,787 B | 4.170 / 3.320 ms |

Every proof operation issued one exact-key version SELECT, zero unrelated table SELECTs and zero payload decodes. Presence checked only the requested42-byte encoded payload; absence checked no payload. These are application-level observations, not physical disk traffic or a save history-read gate. A record deliberately fetched must be checked. Both operations meet the declared <=256 proof-read/<2MiB workload bounds. Post-repair initial full construction and lifetime RSS are reported separately in each per-size receipt; no full Python content map or clean-node cache is retained. Caches are sequential/warm/uncontrolled, tracemalloc is enabled, and no latency distribution or speedup is claimed.

[Source receipt](proof-version/source.json) pins commit9f26548 and exact runtime/driver/fixture hashes, Python/SQLite/environment, caches and declared scope. [Raw size/summary evidence](proof-version/summary.json) preserves all observations. These source fixtures are not mature Worlds.

## Verification and remaining integration

Thirty-six initial tests were observed failing for the missing module before implementation. All39 source cases subsequently passed. After review repair,54 source cases and the affected proof/incremental-store/lazy-store/failure/validation-scope suite passed306 tests in22.50s. AST, workflow YAML, bash run blocks and git diff checks pass. The fresh review found one Important operational-metadata materialization issue, repaired RED/GREEN with same-snapshot guards; successor CI acceptance is pending; the accepted parent suite is not candidate evidence.

Physical owner/group/link and namespace adapters, large query-key budget path, accepted manifests, root AND ordinary payload retention, verified-copy/writer fencing, atomic changed-row/root/head/receipt publication, canonical object admission and actual save/open consumption remain mandatory. Interactive open10s/save2s/warm-year1s targets remain unproven. No main merge or endurance job.

## Independent review repair

A fresh read-only review found one Important memory issue: inherited pin/head validation could transfer multi-MiB malformed operational metadata before the new source guard. Eight adversarial cases reproduced RED; a ninth capacity case already rejected. A private optional snapshot preflight now checks constant-size storage/length facts after BEGIN and before those existing fetches, including nested reuse. The existing64-row pin/receipt/attempt bounds are enforced before inventory materialization. Variable legitimate head/token fields share a separately configurable1MiB metadata transfer budget (explicit max64MiB); a large valid metadata regression proves the budget can be raised without a format restriction. Oversized malformed checksums/bodies reject below128KiB traced Python heap. Default existing snapshot callers are unchanged. The final306-case suite includes validation-scope regressions; full successor CI must still test the shared seam. No Critical/Minor findings and no second review pass.

Review exclusions remain mandatory integration gates, never implicit acceptance: World/canonical admission/topology/manifests/writer fencing, ordinary/segment retention, mature performance, candidate full-suite results and unread corruption. [Review record](proof-version/final-review.md). Pre-review diagnostic receipts remain in pre-review/ and are superseded by final receipts.
