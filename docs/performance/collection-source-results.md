# Checked collection order and namespace counters

Accepted parent CI40098756156:3764tests+2subtests,670proof cases,12diagnostics,14authenticated source receipts and both ZIP digests. Hosted unified saves132.12/143.99/160.27ms. Raw acceptance: run-40098756156/acceptance.json.

Production bootstrap now constructs a complete per-lazy-namespace order root and exact declared/member_count/next_ordinal state from the existing physical full audit. Absent lazy namespace state differs from a declared empty collection; this does not prove absence of an ordinary namespace. Root-selected raw pages check exact pinned order rows, interval/checksum and namespace counters without owner payload reads. External expected certificate authority is mandatory. Current/retained reinsertion order remains exact. Per-field path4096bytes; unsupported fields fail closed. TEMP shadows/triggers, arbitrary transactions, legacy index fallback and overridden codec helpers are rejected.

One fresh independent review:2Important input boundary findings (counter comparisons before type validation; inherited _enter/_node_sort_key hooks). Five RED regressions, one fix pass,20focused GREEN2.66s. Review rulings/costs: collection-source-review.md. No re-review. Final affected XML and CI launch recorded separately.

Final measured source41c62f6. One instrumented three-member page per size; full fixture/audited root construction outside timer. At1k/10k/100k members:10.01/7.10/20.26ms, exactly3physical order-row checks,0payload reads, VM upper2299/2399/2499. SQL/heap/source receipts in collection-source/scaling. SQLite main/temp caches2MiB each, temp_store FILE; no retained clean cache. These are raw page timings, not save or World timings.

Next gate: incremental successor order-root publication, global namespace/allocator/target inventory, complete topology and conceptual seven-root manifests, verified-copy construction, writer fencing and canonical World integration. Existing writer is unchanged by this package. No World path activation, GC or endurance. Full World targets remain unverified.

Final affected suite768passed136.15s; complete XML and console retained. Python/workflow syntax checks passed. Full candidate CI acceptance pending.
