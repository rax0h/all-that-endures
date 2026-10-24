# Unified version/event content publication

Accepted parent [CI40070133798](https://github.com/rax0h/all-that-endures/actions/runs/40070133798):3697tests plus2subtests,603proof cases,11diagnostics. Both artifact digests,13source receipts, driver/fixture hashes and XML authenticated in run-40070133798/acceptance.json. Hosted scope point saves110.57/112.23/119.45ms, zero unrelated body reads.

## Implemented

`persistence_proof_publication.py` explicitly constructs production version-content and event-segment roots from a full physical audit. Exact version bytes/memberships/schema/start generation and segment bytes/ID bounds/count/creation generation are bound by immutable content preimages. Legal zero-element segments now have content commitments; all existing positive-segment hashes remain unchanged.

Externally accepted ContentCertificate authority binds store, codec, generation and both roots. Raw current/retained readers return opaque selected source bytes or authenticated absence. Selected bytes still require complete reference/target/topology and canonical identity admission before World exposure. No World selector or format capability is enabled.

The unified public save requires exact accepted content, ordinary-record and scope authorities. One existing LazyRecordStore.commit transaction authenticates affected actual predecessor version content, writes actual changed data, stages exact successor version/event bodies against prepared inputs, and publishes all implemented component roots with the existing head/receipt. Existing read-only SQL callbacks, data_version epochs, scope predecessor guards and bounded cleanup deferral remain effective. Metadata-only generations reuse every unchanged root. Lost acknowledgement resolves the exact existing token without replay and composes all component results.

This is not the conceptual seven-root generation manifest: complete topology/target, collection-order and namespace/allocator inventory producers remain ahead. Component authorities are not interchangeable with a completed manifest.

## Review and validation

One fresh independent reviewer ran64publication/content tests and found2Important issues, no Critical/Minor. TEMP shadows could redirect validated persistent writes to ephemeral tables; inherited full audit transferred unguarded non-content sources.17RED regressions reproduced both issues. One fix pass adds shared main/TEMP source collision and trigger protection across content/scope/ordinary paths, and pre-audit per-field type/byte/counter/checksum guards for all sources transferred by the inherited audit. Full archive row-count materialization remains explicit construction work.

Final67focused cases passed8.43s. The affected command exited0 with763complete XML cases, zero failures/errors/skips,91.549s. Its redirected console log ended partway through progress; XML, actual completion receipt and explicitly named partial log are retained. Initial746affected cases passed83.56s before review. All review rulings and costs are recorded in content-publication-review.md and content-publication-ledger.md; no second review.

## Actual unified save measurements

Measured local head2e5e576, runtime4233da09ca3b5057ef5a4dda6e4bd0bde3e52714; native Python3.12/SQLite3.45.1. One instrumented sample per size, with tracemalloc, SQL trace and VM counters. SQLite main/temp caches2MiB each, temp_store FILE, no retained clean proof cache.

| Unrelated versions/scopes/event segments | Actual unified save ms | Python peak bytes | VM upper bound | Metadata-only save ms | Unrelated body reads |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 117.97 | 231480 | 24499 | 23.42 | 0 |
| 10000 | 160.38 | 176411 | 25199 | 27.79 | 0 |
| 100000 | 114.57 | 170110 | 25399 | 23.33 | 0 |

Each actual save changes one version and membership, one placement, one ordinary body and appends one event segment, all through the same existing receipt. Every size fetched4selected version bodies,1selected ordinary body and1selected event body, plus2boolean-only body-size probes;5body checks and0World payload decodes. Raw current/retained/successor selection checked exactly3selected bodies per operation and returned exact literal old/new values. Metadata-only commits shared every implemented root.

Full fixture and all audited component bootstraps are excluded from operation timers and separately reported (100k construction100.03s). Raw receipts include source/driver/fixture hashes, all three sizes, heap/VM/SQL counts, database sizes and lifetime RSS. These point samples are not full mature-year saves, startup or warm-year results.

## Remaining gates

Complete topology and target existence/kind, collection order and namespace/allocator inventory, one verified-copy snapshot establishing every component, complete atomic conceptual seven-root manifests, writer fencing/format activation and canonical World consumption remain required. No node collection or endurance is implemented. Existing local recovery does not independently authenticate a coherently replaced whole-store successor history; complete externally accepted generation authority remains required.

Full World performance targets remain unmeasured. Exact candidate CI and all twelve diagnostics are pending launch/acceptance.
