# Complete-upgrade memory repair progress

Implementation starts at90a055030b917d3462d52869fd5abc286c73655e on the existing closeout branch.

## Task1: validation-only source checks

The converter now validates the captured source without constructing the first discarded catalog when normalization/promotion will rebuild it. Initial and final source checks share validation, including physical body/placement agreement and owner path hash collisions. Unchanged catalog-only copies keep their existing publication behavior.

Baseline90a0550 small shared-Event/skill fixture: checked catalog digest5f74ee4b2cbe12a33326ac6212bdf0f758d652304e3fbd12cad3be97cdec65d4; World digeste72e6d203237ac5cac9f15d616e995b2af820e8e637349599624053694913e2b. These exact values remain covered after repair; aliases and unchanged source bytes are checked.

RED: validation-only API absent. GREEN:11 new tests including eight corruption inputs, pre-normalization rejection, digest preservation and bounded subprocess memory comparison. Old aggregate construction of12000 small owners/occurrences fails under110MiB RLIMIT_AS; validation-only succeeds. Before repair, unrestricted180MiB probe passed with130100KiB peak RSS;110MiB probe failed at82224KiB. RSS and address-space caps are distinct measurements. This fixture proves removal of one allocation site, not completion of the large upgrade.

Affected gate: `PYTHONPATH=.:simulation python -m pytest -q simulation/tests/test_stage_0_5_upgrade_memory.py simulation/tests/test_stage_0_5_final_catalog_copy.py simulation/tests/test_stage_0_5_final_identity_catalog.py simulation/tests/test_stage_0_5_final_legacy_event_copy.py` —70 passed22.08s. Baseline copy/Event gate35 passed7.06s.

Tasks2–5 remain open: replayable final catalog, bounded commit preparation, downstream capture/normalization/scrub memory, provenance and GitHub acceptance. No large job launched and no final acceptance claimed.

## Task2: checked replayable final catalog

The conversion uses one private SQLite workspace for indexed owner/placement inventories, radix construction, group/link ordering and replayable VersionChange output. It constructs neither an aggregate ParticipantDelta nor its aggregate fingerprint/decode. Ordinary participants and their fingerprint formula remain unchanged. Source validation now uses disk inventories as well. The workspace writes rows directly: aggregate Python staging buffer high water is zero; each encoded row/adapter and the128KiB SQLite cache are separate costs. File cleanup is context-owned and idempotent.

RED: staging API absent. GREEN: forced-budget reference equivalence for empty, many owners,257-member sharing group,257-placement owner and257 reserved/retired IDs; exact repeated ordering; mutable value capture; payload/count/order corruption and exception cleanup. Combined Task1+spill gate:88 passed24.94s.

Fresh-process final-catalog scale measurements (128/512/2048 owners and occurrences; entry_limit4, byte_limit1024):
{"n": 2048, "rows": 6148, "peak_rss_kib": 18304, "seconds": 0.7878251030001593, "buffer_entries_high_water": 0, "buffer_bytes_high_water": 0, "largest_row_bytes": 481, "largest_row_resident_bytes": 1667, "staged_rows": 6148, "staged_bytes": 2532893, "disk_bytes": 5365760, "python_index_bytes": 856}

## Task3: bounded opt-in commit preparation

Only the explicit private converter opts into `preparation_budget=(4096,2097152)`. Ordinary commits keep their existing preparation path. The bounded path applies the same existing per-row validators, stores immutable encoded prepared records, detects duplicates through private SQLite indexes, and streams namespace groups in their original first-occurrence order. This removes both preparer tuple retention and the writer's namespace lists; publication still uses the existing single transaction/attempt/acknowledgement state machine. Every exit closes the workspace.

RED: opt-in budget keyword absent. GREEN: normal/spilled authority equality through membership publication, deletion, reinsertion and unchanged saves; duplicate version/ordinary/identity keys and malformed memberships reject before an attempt; mutable input changed after preparation cannot alter publication; staged payload corruption and injected SQLite disk-full rejection preserve the store; stale pins and five transaction/recovery fault phases close scratch and retain their existing outcomes.

Affected gate127 passed20.41s: `test_stage_0_5_conversion_preparation.py`, `test_persistence_lazy_store.py`, `test_persistence_lazy_store_failures.py`, `test_stage_0_5_r3_recovery_extra.py`, `test_stage_0_5_upgrade_memory.py`, `test_stage_0_5_final_catalog_copy.py`, `test_stage_0_5_final_complete_format.py`, all under `simulation/tests` with `PYTHONPATH=.:simulation python -m pytest -q`.

## Task4: completed-output retention and scrub

The measured source-owner inventory was retained beside a second decoded capture; it is now released after validation. Immutable segments and source orders stage directly. Normalization retains its existing decoded-object identity contract; replay starts only after normalization/promotion completes and aliases have explicit incarnation placements. Completed versions, ordinary records, placements, dependencies and orders stage on disk before final catalog/preparation. Reference scrub traverses one graph at a time, resetting temporary object IDs between replayed rows. Final catalog scrub uses checked disk sets and streams source owners instead of rebuilding the complete decoded owner inventory.

Two additional edge regressions first failed: indexed replay returned a value before authenticating later rows, and a scratch database initialization failure left its file behind. Indexed replay now finishes authentication and constructor failure cleans scratch. Existing before/after commit, source advancement, destination race, NaN, readonly nested graphs, Event-ID, action, advancement and promotion tests remain covered.

Final affected gate152 passed49.39s: Task3/new memory tests plus `test_stage_0_5_final_complete_format.py`, `test_stage_0_5_final_legacy_event_copy.py`, `test_stage_0_5_final_copy_promotion.py`, `test_stage_0_5_final_frozen_snapshot_authority.py`, `test_stage_0_5_final_legacy_nonreflexive_copy.py`, `test_stage_0_5_final_nonreflexive_copy.py`, `test_stage_0_5_final_catalog_copy.py`.

Fresh-process synthetic end-to-end measurements (2000 people/Events, exact restored World digest verified), using `PYTHONPATH=.:simulation python simulation/tests/complete_upgrade_memory_probe.py 2000`. Baseline uses git archive90a0550 as PYTHONPATH. RSS is KiB; VmSize is separately read from `/proc/self/status`.

| Source | Upgrade peak RSS | Highest sampled upgrade VmSize | Publication elapsed seconds | Final digest verified |
|---|---:|---:|---:|---|
| Baseline90a0550 |184160|218144|39.22|yes|
| Tasks1–3 |82992|99512|52.51|yes|
| Task4 measured tree |69020|90284|61.19|yes|

Task4 phase RSS/VmSize: after source capture44360/71968; after normalization59672/88352; after catalog staging59728/88352; scrub completed59428/87212. Post-publication digest materialization raised lifetime peak to75020KiB and VmSize103596KiB; this is separate from conversion. Disk staging trades time/I/O for memory; this synthetic conversion became slower, not faster.

Remaining input-sized costs: resident source/normalization graphs and their existing per-incarnation/path maps; one oversized encoded record or builder input; backing graph metadata; selected promotion values; SQLite caches. No universal fixed-memory claim. The retained mature year1000 fixture under8GiB RLIMIT_AS remains the required large acceptance gate. Independent whole-diff review precedes its launch.

## Final inventory/provenance checks

Four indexed-inventory corruption tests exposed missing protection for private owner/placement metadata and lost rows. The builder now seals source row counts/order and full owner/placement metadata, checks those seals before output construction and again after it, while preserving the reference catalog values. RED97-test affected inventory/preparation/catalog gate subsequently passed97 tests22.90s.

Harness provenance now accepts an explicit `checkpoint_product_sha` only during resume. Every seed/rules/maturity/milestone/schema/stage/database check remains exact. The checkpoint source product matches the retained receipt; executable `product_sha` remains the repair candidate. New checkpoints bind to that executing candidate and retain the prior source product, workflow, database hash and original receipt hash. Subsequent stages carry that chain into final summaries.

Harness gate:5 passed127.16s, including actual cold->lazy->repaired complete->1/2 continuation, accurate source/candidate provenance, unchanged original source receipt, configuration/stage/checksum rejection and the original complete lane. Actual CLI rejects `--checkpoint-product-sha` without explicit resume before creating output.

GitHub metadata independently confirms retained artifact11870590333, run38508408370, origin124c3215468a60862b7848086f00a8e768a6ed66,1339563957 ZIP bytes, ZIP SHA256409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9, not expired. The gated complete job will stream-verify the archive and receipt/database checksum before conversion; metadata alone is not a restored-database proof.

Prepared five-job acceptance workflow: fresh focused/recovery gate and full suite, repaired complete upgrade under8GiB RLIMIT_AS, exact1001/1002 continuation from its new checkpoint, and downloaded restore on a fresh runner. All checkout the pinned repair candidate, record separate workflow SHA and preserve old checkpoint provenance. No original bootstrap or canonical millennium rerun. Canonical1000 results remain old source-world evidence. Workflow shell blocks and embedded Python parse; no long job has launched yet.

## Hosted full-suite metric failure

Run38603776178 recovered correctly (95 focused tests plus complete3+4+3) and passed2484 tests/2 subtests in the full run. Its single failure was the inherited ru_maxrss comparison in the synthetic memory test; both110MiB guard outcomes were correct. The original run remains red. `STAGE_0_5_MEMORY_METRIC_REPAIR.md` records the deterministic warm-parent reproduction, corrected child-image metrics and46-test green gate. Runtime98a37c6 remains byte-identical; scoped resume checks original evidence and reruns the corrected metric cases without relabeling the failed whole run.
