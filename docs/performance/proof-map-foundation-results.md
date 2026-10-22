# Durable proof map foundation — 2026-10-22

This is an independently checked immutable-map primitive for [Astra's proof architecture](../superpowers/specs/2026-10-21-ate-incremental-proof-design.md). It is not selected by any World reader or publisher and does not change ordinary simulation speed. No persistent capability is enabled, no existing check is bypassed and no main merge is performed.

The runtime foundation beneath it passed [run 39810513221](https://github.com/rax0h/all-that-endures/actions/runs/39810513221): 3094 tests plus two subtests, with both populated saved successors matching eager state after fresh reopen. Its measured first/warm/save improvements remained small. The next integration package must remove repeated validation of unchanged committed state.

## Implemented contract

- Canonical, domain-separated nodes: leaf or compressed radix branch, at most 696 bytes, exact encoded source keys used only to derive opaque lookup locators. No World-object coercion or second object registry.
- Checked membership/absence, immutable path-copy insertion/replacement/deletion, and complete traversal. Actual fetched nodes must match their digest, count and inherited prefix; old roots retain their original mapping.
- SQLite node persistence inside the caller transaction, immutable duplicate verification and zero retained clean-node cache. The adapter never commits, chooses a generation root, or collects nodes.
- Same-value replacement and absent deletion write no nodes. Point operations traverse bounded locator paths, not a whole map. Complete traversal is an explicit full-audit operation.

## Verification and review

Tests were written and observed RED before each implementation: 21 canonical node cases, 12 map cases, six SQLite cases. One fresh Astra review found an Important pre-fetch memory gap: SQLite TEXT with an early NUL could pass a byte-length-looking guard. A dedicated regression reproduced a 2,099,402-byte Python transfer. The SQL now checks storage class before evaluating length or selecting the body; the bounded rejection test passes. [Red evidence](proof-map-foundation/review-transfer-red.log) is retained.

The final source passed **95 focused tests in 4.74 s**, including all 40 new primitive tests and existing incremental-store/failure regressions ([log](proof-map-foundation/final-focused.log)). These counts overlap the earlier task runs. The reviewer also checked valid maximum-depth maps: a replacement uses 65 search reads/65 node writes; deletion uses 66 search/boundary reads/63 writes. Duplicate-write verification may add reads beyond search-path counts, so the workload's <=66 **total** read gate is not a universal total-IO promise. No further concrete findings or deferred minors were reported; no second review was requested after the tested fix.

The full simulation suite on the new branch remains a separate CI gate before merge. The full green parent suite is not represented as a run on these new modules.

## Exact final-source scaling

Measured local source `a4fb680cef2bf8fa2a7121dfc41aafb5cc5f3c2c`, runtime tree `c16f31094b248f67dab2f951a4e9abbba27ee276`. The [source receipt](proof-map-foundation/source.json) records the driver checksum, Python/SQLite/platform and fixed fixture configuration. The final measurement was rerun after the review fix, using exactly the committed driver.

Each map holds one fixed edited key and an increasing number of unrelated proof keys. The measured operation changes one commitment, commits it, then verifies both old and new roots. Point timings include tracemalloc instrumentation and are **not** simulation-save latency. SQLite scratch cache is capped at 2 MiB; Python clean-node cache is 0.

| Map entries | Node reads | New node writes | Read bytes | New bytes | Traced Python peak | Point time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 4 | 4 | 1,654 | 1,654 | 15,337 B | 3.876 ms |
| 10,000 | 6 | 4 | 2,308 | 2,168 | 18,611 B | 5.930 ms |
| 100,000 | 7 | 5 | 2,810 | 2,670 | 21,279 B | 9.617 ms |

All measured SELECTs addressed proof nodes. No World payload tables exist in this fixture: this establishes the primitive's work bound, **not** the real World point-edit save gate. End-to-end save/open consumption remains unimplemented. Process peak RSS includes construction; it is not a phase peak. Complete case receipts and the summary are retained beside this report.

## Retention cost and production boundary

The diagnostic intentionally retains obsolete/intermediate immutable nodes. At 100k live keys, it retained 546696 nodes in a 358686720-byte SQLite file. This is a measured staging cost, not an acceptable unexplained long-term retention policy. Root-aware collection and bounded batch path deduplication must be specified and verified before World activation. Never collect nodes reachable from the current root, retained pins, unresolved publication receipts, or protected checkpoints.

The primitive does not yet provide immutable content-leaf bindings for existing versioned rows, complete topology/query/order roots, generation manifests, verified copy upgrade, atomic root/head/recovery publication, action admission or resumable scrubbing. Those are the remaining architecture requirements. Preserve canonical digest and exact identity/RNG/order semantics while integrating them.

See the [integration handoff](proof-map-foundation/NEXT_INTEGRATION.md). Interactive targets remain open <=10 s, incremental save <=2 s and warm year <=1 s; none are claimed met by this primitive.
