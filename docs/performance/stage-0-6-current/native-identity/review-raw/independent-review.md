# Independent native identity package review

Reviewed baseline `f08d2e1fe1f026ea2dca3f9b976ba1c9169262c4` plus the native identity adapter, four LazyRecordStore integration seams, product tests, specification/plan, closure records, and the subsequently visible workflow inclusion/runtime-pin edits. Read AGENTS.md. This is the single whole-package review; no runtime, product-test, index, HEAD or branch changes were made by the reviewer. Review-only probes and evidence are in this directory.

## Result

No actionable Critical, Important or Minor findings. No finding is deferred. The implementation is suitable to proceed to the author's remaining exact-source, canonical continuation, launcher and publication gates; this report does not assert that those gates have completed.

## Checked relationships

- `persistence_proof_native_identity.py:16-58`: accepted manifest allocator and scoped certificate agree; the physical open allocator is unique, typed, checksum-checked and not future-started/future-closed.
- `:74-103`: an exact physical placement is checked against both owner and incarnation commitments. Duplicate open locators, missing accepted points, changed incarnations, future closure and scalar/checksum corruption fail closed. Exact absence uses the accepted owner scope.
- `:106-140,154-189`: owner physical tuple cursors cannot skip a duplicate locator because exact point checks reject duplicates. Physical-next comparisons cover leading/interior surplus, lookahead and final surplus before that page's decoding. Adaptive pages retain the unreturned lookahead as the next accepted position, so the cursor does not skip it.
- `:166-181`: equal selected-current-group count plus every accepted exact point proves group completeness. A missing point compensated by another physical row still fails the missing-point check. The count is held only within one iterator bound to its original accepted epoch.
- The public state/point wrappers first validate the actual caller pin; owner/group iterators pass that actual pin to the shared snapshot mechanism. Original-epoch and active-authority checks run before a suspended iterator can yield another value. Scoped summaries use the existing ValidationScope and do not cache physical rows. Owned read snapshots end before public yields; private catalog operations can retain their own enclosing checked snapshot as before.
- Physical identity queries return only bounded scalars/checksums or booleans/counts. Owner/archive bodies are not selected. Existing compatibility tuple shapes and sorting remain. Existing publisher capability and callback exclusion logic remain in charge; no new admission/publisher/registry path was added.

## Verification

Python: `/tmp/ate-identity-venv/bin/python`, `PYTHONPATH=.:simulation`.

| Evidence | Result |
|---|---|
| `probes.py`, `probes.log`, `probes.xml` | 13 passed in 19.60s |
| `product.log`, `product.xml`; all cases in `simulation/tests/test_stage_0_6_proof_native_identity.py` | 46 passed in 109.01s |

The 13 independent probes cover contradictory empty-owner/unallocated-group scopes, allocated-group surplus, future closures, compensated deletion plus addition with unchanged group count, leading/final owner surplus before decoding, duplicate exact locators through point/owner/group APIs, and SQLite query plans using indexed SEARCH without a temporary sort. The product run covers the supplied forgery/pin/epoch/cache/callback/body-read/132-alias/default-budget long-field controls. Its three warnings are from this review invocation using pytest's default xunit2 output with `record_property`; the product workflow explicitly uses legacy JUnit. They are not runtime or assertion failures.

Reviewed source SHA-256:

| File | SHA-256 |
|---|---|
| `simulation/ate_sim/persistence_proof_native_identity.py` | `d3f76dddf305417923b2c4eb3548f3a08694600e81189b459015cd879791c5ff` |
| `simulation/ate_sim/persistence_lazy_store.py` | `0461cbe52528a73cb37fa62ad5f4db22e5a0562814fdcbc3aa61fad7847d6faf` |
| `simulation/tests/test_stage_0_6_proof_native_identity.py` | `a3221ab72060c7df307682d6bd290eb9bd81f8e4dcf1bc79ed8daaff52f1be7e` |

## Explicitly declined judgments and non-findings

- No constant-time first-page group claim. Before its first output, each original-epoch group iterator counts all current rows of the selected incarnation using the existing `(incarnation_id, valid_to)` interval-index prefix. That work is linear in the selected current group, excludes expired history, transfers one scalar, and uses no temporary sort. Subsequent exact selections/pages are bounded as specified. I accept this documented ruling; I do not recommend an implicit archive index build or a format migration for this package.
- No approval to remove full audited admission. Catalog, ordinary-roster and remaining raw-consumer coverage remain separate gates. The scoped identity reads do not establish complete World admission by themselves.
- No independent completion claim for the parent's broad regression, exact canonical eager/fresh continuation, source immutability, clean launcher, source-tree mapping, hosted CI, or publication. Those are author gates that follow this report.
- No performance improvement, maturity, default activation, main merge or endurance judgment.
- A trial fixture using 132 mutable descendants inside a skill history was rejected by the existing converter with `StoreFormatError: skill/soul history contains unsupported mutable descendants`. This is an unsupported fixture, not a regression or a request to relax runtime limits. Owner multipage cursor behavior was reviewed statically; supported 132-entry and adaptive long-field multipage behavior was executed through the group fixture.
- The original author failures about absent optional indexes, unsupported partial retirement and over-limit derived query keys are reconciled with the current implementation/tests and documented rulings. They are not outstanding product findings.
