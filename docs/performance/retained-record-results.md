# Retained ordinary content: actual save results

The ordinary-content proof producer now performs explicit full physical audited bootstrap, retains exact immutable ordinary bodies, and publishes successor content roots inside the existing LazyRecordStore.commit transaction. Selected actual written rows are checked against prepared bytes immediately before commit. Existing default callers keep their paths; proof-aware calls opt in explicitly. No World reader, new format capability, full manifest publisher or collector is enabled.

Parent CI40028259840 accepted for6d8f2193/runtime79a9ad08:3582tests plus2subtests,488dedicated proof cases,all9prior diagnostics. Both artifact SHA256 digests,11source receipts and XML were authenticated. Raw evidence in run-40028259840/.

## Actual ordinary point-save measurement

One instrumented sample per size, with tracemalloc, SQL trace and VM counters. These are real existing store transactions changing one ordinary record, updating head/receipt and retaining body/root atomically. Full fixture and bootstrap construction are excluded and separately recorded.

| Unrelated ordinary records | Actual point save ms | Python peak bytes | VM-step upper bound | Unrelated body reads |
| ---: | ---: | ---: | ---: | ---: |
| 1000 | 24.18 | 153141 | 2799 | 0 |
| 10000 | 21.49 | 108439 | 2999 | 0 |
| 100000 | 22.49 | 117934 | 2999 | 0 |

Every measured save checked exactly1actual changed mutable body, read0unrelated payload bodies, and produced exact current/retained/successor results. Raw old/new reads checked exactly1selected immutable body each. Root update follows the changed sorted delta and proof paths. SQLite main/temp caches2MiB each, temp_store FILE, no retained clean proof cache. Source/driver/fixture hashes, construction time, SQL/heap/VM/RSS and database sizes are in retained-record/scaling/.

The final matrix uses system Python3.12/SQLite3.45.1, matching CI. Initial pre-review samples were superseded by this exact-runtime matrix. Final measured local head48e7623, runtimefe161613; candidate source equivalence and CI recorded separately.

## Verification and review

Initial18missing-module RED cases, constructor-budget RED, then9missing-commit-API RED failures. A2MiB conflicting body allocation and external-write parent-epoch gap were independently reproduced and fixed. Initial29focused/610affected, then31focused/612affected passed before independent review.

Independent review found4Important issues, no Critical/Minor: SQL callbacks could escape transaction control; noncommitted recovery paired a stale certificate; bootstrap accepted future revisions; malformed metadata transferred unbounded bytes. Pre-fix new regression completion17failed/4passed is retained as an honest completion summary (full background redirected log unavailable). One fix pass added a tracked/chained connection authorizer enforcing read-only SQL callbacks in all phases, exact recovery parent/source matching, and pre-audit type/byte/revision guards. COMMIT, rollback/rebegin, executescript, outside-transaction write+commit, existing authorizer preservation/removal, pending/already-resolved recovery, future revision and embedded-NUL metadata are covered. Focused60passed; final affected641passed in59.09s. Syntax, workflow and source checks recorded in ledger. Full candidate suite remains pending until authenticated CI acceptance.

## Scope and remaining gates

This closes actual retained ordinary body availability for the component's live current/previous pins and its atomic content-root update. Root preservation alone does not create topology, query membership or complete World authority. Normal/old writes can advance without proofs; missing current roots fail closed. Complete verified topology/target/query/order/event/inventory roots, full atomic generation manifest publication, writer fencing/format activation and canonical World admission remain required before switching World paths. No node/body collection is implemented.

The bootstrap's inherited full lazy/segment audit is explicit archive work; only the ordinary source body/metadata transfer limits are newly enforced here. The SQL callback guard preserves an existing authorizer but is not an arbitrary-Python sandbox. All review scope rulings/costs: retained-record-ledger.md and retained-record-review.md.

No new full World startup, mature-year save or warm-year measurement is supplied. The22ms-scale point save is not a full World save or acceptance of the2second target for the mature workload.

Candidate CI [40051989785](https://github.com/rax0h/all-that-endures/actions/runs/40051989785), head`b80fd5a7c658e55963beba40123779287c8bae9b`, runtime`fe161613a47b3a4eebebd58b1dd5c0b5da7dda8d`; in progress at launch, full-suite acceptance pending.

## Accepted CI

Run40051989785 completed successfully on exact candidate b80fd5a7c658e55963beba40123779287c8bae9b/runtime fe161613a47b3a4eebebd58b1dd5c0b5da7dda8d. Both artifact ZIP SHA256 digests verified; all12source receipts, driver/fixture hashes and XML checked. Full suite3642passed plus2subtests;548dedicated proof cases; all10diagnostic matrices complete. Hosted ordinary point saves27.50/26.04/31.63ms at1k/10k/100k, zero unrelated body reads. Full World performance remains unmeasured. Raw acceptance: run-40051989785/acceptance.json.
