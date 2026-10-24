# Verified scoped relation directories

Accepted parent: [CI40051989785](https://github.com/rax0h/all-that-endures/actions/runs/40051989785), exact retained-record candidate b80fd5a7c658e55963beba40123779287c8bae9b/runtime fe161613a47b3a4eebebd58b1dd5c0b5da7dda8d. Both artifact digests,12source receipts, driver/fixture hashes and XML authenticated:3642tests plus2subtests,548dedicated proof cases,10diagnostics. Hosted ordinary point saves27.50/26.04/31.63ms at1k/10k/100k, zero unrelated body reads. Raw acceptance: run-40051989785/acceptance.json.

## Implemented

`persistence_proof_scope.py` constructs all nonempty owner/group placement scopes, lazy query scopes and complete reverse query sets per owner from one fully audited current physical snapshot. Its4directory roots contain generation-independent scope descriptors. Generation/allocator bindings belong to the enclosing externally accepted certificate, allowing unchanged roots to remain shared across saves.

Directory resolution authenticates exact scoped descriptors or absence and reconstructs existing SeekOccurrenceCertificate/SeekQueryCertificate values. Existing raw page readers still check selected physical rows and checksums. No owner payloads are decoded by directory/page reads. Supported field path is4096bytes; larger fields require a separate checked path. This is an inactive physical-relation component, not complete World authority.

Opt-in saves use the actual existing LazyRecordStore.commit transaction. Actual old/new query rows and placements are checked against prepared input and accepted parent roots. The reverse per-owner witness proves the complete old query set, including coherent removal of old metadata. SQLite spools contain changed scopes/members and sorted directory deltas; unrelated scope roots are shared. Bounded historical cleanup is deferred until final scope staging within this transaction so a parent without another live pin remains available for verification.

Affected predecessor source guards run before inherited reads in a stable owned read snapshot and repeat inside BEGIN IMMEDIATE. Fixed metadata types/byte lengths are checked before transfer; old version payload+memberships have an explicit combined64MiB bound. Main/temp triggers are rejected so node/descriptor/root/cleanup writes cannot mutate already-checked sources. Existing read-only SQL fault callbacks and external data_version epochs are preserved.

Optional ordinary-record authority composes retained ordinary bodies/content roots and scope roots into that same transaction. Existing exact-token recovery resolves both components without replay. No-op returns parent authority; conflicts return none; default writes leaving a missing scope generation fail closed. Local receipt recovery does not independently defend against coherent replacement of the whole store; externally accepted complete generation authority remains a future gate.

## Verification

55focused cases passed in8.92s. The final affected command exited0 with696XML cases and zero failures/errors/skips (91.805s). Its redirected log exposed stale earlier invalid-fixture failure output; final XML and an explicit completion JSON are retained instead of presenting that stale log as a successful run. Initial687affected cases passed before review.

One fresh independent review found2Important issues and no Critical/Minor: predecessor transfer guards were too late, and DB triggers could mutate source after staging. Seven RED regressions reproduced these problems. One fix pass plus temp-trigger and actual writer-transaction recheck tests passed. No second review. Earlier coherent parent-placement/query-removal RED cases also prove the reverse witness and old-point checks. Full details, initial invalid fixtures, review rulings and costs: scope-directory-ledger.md, scope-directory-review.md and scope-directory/.

Python syntax, YAML and every workflow shell block validated. New CI includes the scope suite and1k/10k/100k diagnostic alongside all existing tests and ten diagnostics. Candidate/launch receipts are recorded separately; full candidate CI acceptance remains pending.

## Measured work

Final measured head4627076, runtime770b634ceddae1aa6542b98f3861da6f1f7b0de9. One instrumented sample per size, native Python3.12/SQLite3.45.1, tracemalloc/SQL trace/VM counters; SQLite main/temp caches2MiB each, temp_store FILE, no retained clean proof cache.

| Unrelated scopes per directory | Actual point save ms | Python peak bytes | VM upper bound | Allocator-only save ms | Unrelated body reads |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 99.26 | 289805 | 16799 | 18.20 | 0 |
| 10000 | 97.08 | 168490 | 17399 | 16.70 | 0 |
| 100000 | 100.64 | 169194 | 17899 | 15.02 | 0 |

Every point save performed4descriptor write attempts, fetched2selected predecessor body rows (one checked by the inherited writer), ran2boolean-only body-size probes, and read0unrelated payloads. Current/retained/successor pages checked literal group1→2 and query ordinal0→7 results without owner body reads. Every allocator-only save shared all4directory roots and wrote0descriptors. Complete directory sizes were1001/10001/100001 each. Raw receipts retain construction time, database sizes, lifetime RSS and all current/retained/successor observations. The100k full fixture+audited bootstrap is explicit archive work, not ordinary save/open work.
 Full fixture and audited4directory bootstrap are outside timers and separately reported. The scenario changes one actual lazy owner membership and one placement through the existing save transaction. It is not a full World/year save.

## Remaining gates

Complete World topology/target existence and kind, version-content production/publication, ordinary order/event/namespace/allocator inventory roots and the full atomic seven-root generation manifest remain ahead. Format activation, old-writer fencing, canonical World admission and collection remain gated. No first-interaction/open, mature full-save or warm-year result is supplied; the full World performance targets remain unmeasured.
