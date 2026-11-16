# Mature rebase locator repair

Run **43780946218**, public `6f3d0a88`, failed in rebase after its 9,000-second compute cap. It did not reach operational measurement. Source verification, capture and catalog completed successfully. Rebase's diagnostic archive was published after the controlled failure; no completed rebase database/receipt was published.

## Cause and narrow fix

The traceback terminates in `_bounded_rows()` fetching `lazy_order_versions`. SQLite 3.46.1 chooses `lazy_order_visible(namespace=?)` for the original logical-key point lookup because that index covers all requested fields. It then searches the namespace for each requested key. The bad plan is reproduced with the production DDL and 1,024 keys, without a large World. Running ANALYZE changes the old plan, which explains why a small functional smoke does not establish a scaling bound.

The repair preserves logical keyset pagination and the 64-locator/one-payload-row memory bound. Each batch also captures the private rowid; the payload is fetched by that unique locator. No schema, stored payload, checksum, simulation semantics, identity or acceptance digest changes. The tables are rowid tables and locators are consumed inside the existing owned construction transaction. Existing tests cover revision mutation, the allocator INTEGER PRIMARY KEY alias, multiple locator batches, multiple query positions, source preservation, corruption and cancellation rollback.

The regression fails against the original helper without ANALYZE; the repair passes both with and without ANALYZE. Synthetic counts from 512/1,024/2,048 rows are approximately 1.06m/4.22m/16.83m instructions before and 11k/23k/48k after. These are locator-only measurements and establish no mature save, year or end-to-end speed claim. Reproduce from the repository root using the qualified interpreter, `PYTHONPATH=.:simulation` and `probe.py`; the baseline public commit is explicit.

## Retained restart point

Catalog metadata **14197005279** and database **14195829058** were authenticated against the completed catalog job and its publication timestamps. Metadata ZIP SHA256 is `6239ebd5d486cbb00ecdb0e6206a288190cf4fb9d857fcbc90a3a674eda3b335`. The closed database is 29,389,029,376 bytes, SHA256 `8cc3dd2cd49ec143dd318a2ae6928f90b168ea06862c3939bec4aa32d6022562`, year 1001, seed 843000, generation 126. Its ZIP SHA256 is `9ffe8035682e24511f2219a3e5a379ed070d8374fd3efbfba7d44ac2ce89f8f2`. Database retention expires December 16, 2026 at 03:59:09 UTC. The actual original receipt/control chain is unchanged. Only small metadata/evidence archives were downloaded again; the 4.4 GB database ZIP has not been redundantly fetched for this investigation.

**Compatibility is not yet admitted.** The repaired engine differs from the old catalog's context. Existing `compatible()`, `check_context()` and recursively identical parent-context checks correctly refuse it. Do not change engine/green constants or relabel the old receipt to force a retry through. Do not blindly rerun source/capture/catalog either.

The next recovery package must explicitly authenticate and retain the original catalog chain and exact closed bytes; bind the exact old/new engine and helper delta in a reviewed transition record; qualify the new hosted engine; and exercise small transition, rollback and corruption controls before a mature retry. Fresh audited opening and post-rebase canonical digest equivalence remain required. Rebase remains the first incomplete expensive stage. No mature retry is activated by this repair.

## Qualification gate

The hosted green qualification pins remain attached to engine `84626841`; they do not qualify this successor. Source/runtime fences are unchanged. The canonical source-digest compatibility declaration now names candidate `0d9dab5d`, with its exact manifest fingerprint updated in the source request; every historical source/digest/model/schema/codec binding is unchanged. This declaration is not execution or retained-catalog admission. The harness contract now checks its declared green engine against the real qualified ancestor, then proves that a clean different engine is refused. Previously it required the new engine already be qualified before the qualification CI itself could run. That circular assumption was reproduced as a failing test before repair. Production admission stays closed.

Local and independent-review results are recorded in `validation.json` and the forensic closure register. One bundled hosted harness/proof/full qualification is required because engine code changed. An expensive mature prefix is not authorized merely to test this query fix. Stage 0.6 performance and exact year-1002 acceptance remain open.

Local validation:79affected cases passed; initial complete quick harness had356pass/3fail (two dirty-checkout refusals and stale canonical declaration). Both causes were corrected, all58source/resume cases passed, and final committed-clean-tree closure repeated the three failures plus untested-engine refusal with4passes. This is not reported as a complete local359green run. The next hosted complete clean gate remains required before proof/full jobs. Raw failures, focused closures and exact XML counts are retained.

Final independent whole-package review approved publication for new-engine qualification only. All findings, including Minors, are closed; all25evidence members and8XML summaries match their indexes. Mature admission remains pending.
