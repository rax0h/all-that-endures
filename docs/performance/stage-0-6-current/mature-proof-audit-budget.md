# Mature proof audit budget

November 20, 2026 · Stage 0.6 · `sol/durable-proof-map` at `ad052e61`

**Hold the 210-minute mature retry.** The previous proof run spent **135m13s**
before calling the World manifest. A separate mature run on its direct
catalog ancestor spent **57m02s** in the catalog audit before it even entered
sequence verification. Charging these two observed intervals against
12,600 seconds leaves **17m45s** for every other remaining pass. This is a
historical budget comparison. The current engine's mature runtime remains
unmeasured.

## Prior proof run on the exact retained input

[Run 43918798385](https://github.com/rax0h/all-that-endures/actions/runs/43918798385)
used engine `0d9dab5d`. The retained [proof failure archive](proof-source-audit-repair/failure.zip)
contains `14285020598.zip`. Its `phase-start-proofs.json` and
`progress-00000.json` through `progress-00007.json` give the following
intervals. The outer and nested archives match the [retained index](proof-source-audit-repair/evidence-index.json).

| Compute interval | Seconds |
|---|---:|
| Compute start to record bootstrap | 257.83 |
| Record bootstrap to scope bootstrap, including the initial full source audit | 2,127.04 |
| Scope bootstrap to content bootstrap | 1,820.46 |
| Content bootstrap to directory bootstrap | 2,311.51 |
| Directory bootstrap to inventory bootstrap | 1,385.99 |
| Inventory bootstrap to World manifest | 210.59 |
| **Compute start to World manifest** | **8,113.41** |
| **Nominal budget left at the World manifest** | **4,486.59** |

The compute result is censored at 12,602.01 seconds. The retained traceback
reached the old version proof path lookup after scope reconstruction. It
did not reach the rest of the source comparisons, collection-directory
reconstruction, fixed World/head/event checks, catalog audit, retirement or
adoption checks, backing/owner topology, fact roots or final physical check.
The current source comparison reads each reachable proof node once during
comparison. It still checks every physical source commitment and compares
both complete inventories.

## Catalog evidence from the direct ancestor

[Catalog job 133050300010](https://github.com/rax0h/all-that-endures/actions/runs/43780946218/job/133050300010)
published the generation-126 catalog that was subsequently rebased into
the retained generation-zero input. Its [raw diagnostic archive](mature-catalog-timing-14196725864.zip)
matches artifact 14196725864 (24,437 bytes, SHA-256
`191d978c8759378febdd08b0bd9421283282a235487f36add0d29cbb0a9cf024`).
Elapsed times come from the archived process timestamps.

| Start marker and next boundary | Archive progress records | Seconds |
|---|---|---:|
| Groups → owners | 00001 → 00024 | 1,505.26 |
| Owners → inventories | 00024 → 00048 | 1,009.64 |
| Inventories → member types | 00048 → 00049 | 459.84 |
| Member types → sequences | 00049 → 00050 | 446.98 |
| **Groups → sequences start** | **00001 → 00050** | **3,421.72** |
| Sequences start → before publish | 00050 → 00051 | 1,334.79 |

The groups and owners loops passed **2.2 million** and **2.3 million**
entries, respectively, per progress records 00023 and 00047. The
groups-to-sequences interval includes those complete loops, inventory
comparisons and member type checks. The last interval also includes the
catalog copy's later dependency roster, reference and backing graph work.
The archive gives no standalone sequence completion time.

The catalog producer, old proof run and current small recovery used
Python 3.12.16 and SQLite 3.46.1 with the same hosted software signature
`a6cc6e5e404ca8bd7cfdf50e08b3f0c163405fb3941b77d83921f492213b3982`.
From the catalog producer to the current engine, the only engine changes
are in the rebase helper and the World source comparison. Both catalog
call sites use the same `_verify_catalog` under owned, frozen source
custody. Generation normalization, proof tables, spill and cache state,
and runner I/O can still change absolute timings. The **3,421.72 seconds
is an observed subtotal for the ancestor job**.

## Remaining work on the current proof path

| Current work | What the available evidence establishes |
|---|---|
| Reconstruct all scoped roots | The same constructor runs at bootstrap and again before source comparisons. Repeat construction validates existing node bytes when keys collide. The first mature bootstrap interval was 1,820.46 s, including its surrounding work. The duration of the second invocation is inseparable in the old trace. |
| Recompare all three source maps | The repaired traversal removes repeated proof path reads. Full source validation, checked commitment spooling and traversal remain. The synthetic and small results give no mature wall-time bound. |
| Reconstruct the collection directory | The audit reruns the same per-collection construction and ordered tree build used in bootstrap. The first mature directory interval was 1,385.99 s including its setup and guards. The old proof run never timed reconstruction. |
| Validate fixed World sources, head and events | Separate checks after source comparison validate the fixed World contract and head. `SealedEventPrefix.verify_full()` rereads the captured event segments and checks event order. Mature costs are unmeasured. |
| Recheck the catalog | The directly related mature ancestor provides the 3,421.72 s subtotal through sequence start. Whole catalog cost in the current proof transaction is unknown. |
| Validate topology and build World facts | Retirement and adoption validators run after the catalog. The audit then checks backing descriptors, projects every owner and placement, compares both occurrence inventories, rejects orphan and cyclic child relations, and builds the fact roots. The old proof run did not reach this work. |
| Check physical integrity before commit | Later `store.verify_all()` calls reuse the original source audit within the same owned transaction. The final physical integrity and foreign-key checks still run over the enlarged proof database at seal/commit. Their mature duration is unknown. |

[Small recovery 44028694698](https://github.com/rax0h/all-that-endures/actions/runs/44028694698)
confirms the call order and completed checks on the current engine. In the
[retained smoke archive](after-digest-admission/hosted-smoke-44028694698-evidence.zip),
`original-artifacts/14303709393.zip` records scope reconstruction, source
map counts 8,519/176/0, catalog completion, World completion and the final
physical check. The two nested catalog starts represent the wrapper's
workspace setup and the one full invocation. The small proofs compute took
6.81 seconds in total.

The remaining **1,064.87 seconds** under this historical comparison would
require the entire balance to fit in less time than either the old first
scope or first directory interval. Repeat costs can differ. This evidence
justifies holding the retry and prioritizing the independent cost of scope
and collection reconstruction before a new full proofs run. Preserve the
owned-source and byte-check contracts when investigating repeat work. Keep
separate measurements for source comparison, full catalog, topology/fact
construction and final physical integrity when validating a successor.

## Restart authority

Resume only from `after_digest` **14267625292** and closed rebase data
**14261110486** on run 43918798385 when ready. Both and the inherited
catalog pair **14197005279**/**14195829058** were live at inspection. Of
these four mature refs, **14195829058** expires first, **Dec 16 at 03:59:09 UTC**. The
earliest overall gate dependency is the current proof-map qualification
**14292956213**, which expires **Dec 1 at 02:18:52 UTC**. The gate also
reauthenticates the small recovery's original catalog and after-digest
pairs. Of those four refs, catalog data **14187731783** expires first,
**Dec 16 at 00:15:38 UTC**, ahead of the Dec 17 expiry of the small
recovery's own evidence.

Continue using the [exact retained admission](after-digest-admission/README.md)
and its actual small recovery. All five completed prerequisite stages remain
reusable. This investigation used retained metadata and logs. Mature open,
save, first/warm year and exact year-1002 continuation remain unmeasured.
