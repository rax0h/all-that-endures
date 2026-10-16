# Resumable Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Preserve completed preparation and commit work across construction interruption.

**Architecture:** A no-op private converter seam exposes existing sealed replay streams and commit/order inputs. Validation-only helpers retain closed database/spool files, authenticate exact typed manifests, and execute commit and order restoration on disposable copies before entering the existing verification pipeline.

**Tech Stack:** Python, SQLite, pytest, GitHub Actions artifact transport.

**Spec:** ../specs/2026-10-15-resumable-construction-design.md (approved October 15).

## Global Constraints

- Keep mature execution paused; preserve the 8 GiB address-space guard.
- No source, retained artifact, receipt or accepted destination overwrites.
- Reuse canonical replay rows without graph-wide reencoding during export.
- Existing original commit, order restoration and verifiers remain authoritative.
- Runtime seam changes require fresh focused, recovery and whole-suite validation.
- Producer provenance is checked through authenticated CI transport, independently of manifest hashes.

## Review Focus

- Foreign or inconsistent stream adapters/counts/seals must reject before mutation.
- Source generation, target identity/pin, typed commit arguments and stage lineage must match.
- Close/cleanup/interruption must not delete a previously completed stage.
- A recomputed transport hash cannot excuse logical row corruption.
- Retrying commit/order restoration must never rerun preparation or mutate earlier artifacts.

### Task 1: Durable preparation and replay

**Files:** Modify simulation/ate_sim/persistence_catalog_copy.py; create simulation/construction_checkpoint.py and simulation/tests/test_construction_checkpoint.py.

**Interfaces:** Private _construction_ready(target,pin,*,workspace,streams,commit); prepare(source,source_receipt,bundle,*,rules_id,context); validate_prepared(bundle,*,context). Seven streams: ordinary, versions, catalog, dependencies, identity, orders, states. Replay descriptors bind stream ID, adapter, count and seal; files are target.sqlite, spool.sqlite and manifest.json.

- [x] Write tests proving preparation stops before commit, exports existing stream bytes, closes writers, survives converter cleanup, preserves source and rejects malformed/foreign/corrupt bundles.
- [x] Run PYTHONPATH=.:simulation pytest -q simulation/tests/test_construction_checkpoint.py; observe missing implementation failure.
- [x] Add the no-op seam; implement preparation and strict manifest/file/pin/stream validation with read-only replay.
- [x] Run new tests and existing conversion/checkpoint focused tests; commit passing task.

### Task 2: Commit and order-restoration recovery

**Files:** Extend the same helper/tests; reuse simulation/complete_upgrade_checkpoint.py unchanged.

**Interfaces:** commit_prepared(prepared,bundle,*,context); restore_orders(prepared,committed,candidate,*,context). Committed manifest binds original preparation manifest hash; restored output exactly matches the existing unverified candidate schema.

- [x] Write tests for commit interruption/retry, order interruption/retry, exact ordinary-upgrade equivalence, corrupt logical rows with refreshed transport hashes, no overwrite, receipt failures and fresh-process CLI.
- [x] Run new tests and confirm the new APIs fail before implementation.
- [x] Implement the original commit on a disposable target copy; save before order restoration. Restore orders separately, preserving both earlier artifacts and producing the existing candidate manifest.
- [x] Run focused conversion, checkpoint and P5 recovery checks; commit passing task.

### Task 3: Fresh-runner proof and validation gates

**Files:** Create simulation/construction_checkpoint_ci.py, .github/workflows/stage-0-5-construction-proof.yml and workflow tests.

**Interfaces:** Dedicated proof branch; authenticated source/prepare/interrupt/commit/orders/storage/catalog/publish/continue/restore jobs. Source contains shared nested identities and counted history. An interruption proof consumes retained preparation, deliberately aborts a real commit and proves earlier bytes unchanged; subsequent jobs reuse preparation.

- [x] Write failing workflow/runner tests for stage dependencies, exact artifact membership and producer checks, bounded job limits, nonfatal diagnostics before mandatory stage upload, and absent mature starts.
- [x] Implement fresh-process stage runner and proof workflow; test locally.
- [x] Obtain one independent whole-change review; repair material findings with failing regressions.
- [x] Publish exact source and pinned workflow on a dedicated branch; launch bounded proof plus applicable fresh recovery/full suite. Record links/results without waiting in the chat for long gates. Run 38819525026 passed all 13 jobs, including 2,594 tests and two subtests.

### Task 4: Mature commit from saved preparation

Daniel authorized a preparation-completion brief followed by continuation. Run
38833265909 passed in 2h50m47s and uploaded construction-mature-prepared
artifact 12024550042 (3,631,292,089 bytes, archive SHA256
01db7a227f4a50a0bab347a211c09e2409880875de685cff1e32a01724322e06).
Authenticated diagnostics report 9,822 seconds for preparation/export and
files target.sqlite (808,775,680 bytes) and spool.sqlite (21,538,623,488 bytes).
The original atomic commit previously took 136m40s; that is a measurement,
not a guaranteed duration on another runner.

**Files:** simulation/construction_mature_commit.py,
simulation/tests/test_construction_mature_commit.py,
.github/workflows/stage-0-5-mature-commit.yml.

- [x] Test commit-only reuse, foreign input rejection, exact transport, duplicate/rerun protection, and nonfatal post-boundary diagnostics.
- [x] Implement a validation-only wrapper around the unchanged commit_prepared API; preserve the preparation context and record the new executing producer separately.
- [x] Run focused mature/construction/transport tests; verify core helpers and runtime tree remain byte-identical to the green full proof.
- [x] Obtain independent review and resolve material findings. Review identified inadequate minimum scratch space; two boundary tests reproduced the issue, then passed with 100 GiB before download and 75 GiB after extraction. Final 75 focused checks passed; no open Critical/Important findings.
- [x] Publish the exact reviewed wrapper, pin its SHA in the dedicated workflow, read back outgoing files, and start only one commit job. Launch 0acb45ef35748f7eda3f8d212c5c33c5d408be8f pins e32ffc7cdc87bf4bde408eb5957458fd6142736b; run 38851921152.
- [x] Record its run and update the existing hourly monitor. Inspect its committed artifact and timings before ordering. The job and mandatory upload passed on October 16; total 2h29m27s, wrapper 8461.09s after authenticated preparation download (164.90s). Artifact 12030703178 is 4,332,758,248 bytes with ZIP SHA256 ec5dbeb0224a7bae109771b59da2bdca6eca451ebf67f1f5102fc77b91506077. Digest-checked diagnostics bind the original context, preparation manifest 15954ddf26504c15f195b1915fabb337911609fbbf7ca7359181c8b59b121557 and committed target 29,405,450,240 bytes, SHA256 06b18a6eb568863e8236ac270e507343cfefc9e7c7aaed4c58175619f53d28ad. Last free disk was 58,277,339,136 bytes.

Ruling: reuse the existing whole-suite/recovery proof for byte-identical runtime
and core helpers; validate the new stage wrapper with focused real-fixture
checks and independent review. A new runtime change requires fresh runtime gates.

### Task 5: Mature ordering from saved preparation and commit

Daniel authorized each completed-stage brief followed by continuation. Run
38851921152 and its committed artifact are successful; neither construction
preparation nor commit may be repeated to advance ordering. This stage consumes
the original context, generation 124 preparation, generation 125 commit, and
the same store identity and pin token. Its full ZIP/member/file authentication
on a fresh runner precedes the original restore_orders helper.

**Files:** simulation/construction_mature_orders.py,
simulation/tests/test_construction_mature_orders.py,
.github/workflows/stage-0-5-mature-orders.yml.

- [x] Write and observe failing tests for real-fixture exact values/aliases, immutable earlier inputs, foreign manifests/configuration, transport, duplicate starts, no overwrite, disk boundaries, and nonfatal post-boundary diagnostics. All 29 failed for absent wiring/workflow.
- [x] Implement only a wrapper around unchanged restore_orders; retain the existing unverified candidate before any storage/catalog verification or publication. New ordering checks pass 29/29.
- [x] Run affected construction, transport, verification and workflow tests; confirm runtime tree and core helper hashes still match the green proof. 124 tests passed in 76.90s; the one warning is the intentional duplicate ZIP-entry fixture.
- [x] Obtain one independent review and resolve material findings with failing regressions. Independent review found no Critical, Important or Minor issues and independently passed 66 ordering/construction/transport tests. No material findings needed repair.
- [x] Publish the exact reviewed source, pin it in a separate launch commit, read back all outgoing files, inspect for earlier launches, and launch only ordering. Source 0e1986f626b66feea37be65ea1fc8291a939c004 (tree 670070f9332f13cb12e7169d0e4d12c96354fbda) and all six files read back exactly; launch 8b8c108f032f1e6d58339cc436310402b40a10ce changes only the source pin and its workflow was read back exactly. Zero earlier ordering runs were found. Final pinned-workflow checks passed 29/29.
- [x] Record launch evidence and update the same existing monitor to inspect ordering completion before verification. Run 38867766111, job 116864437819 mature-orders: https://github.com/rax0h/all-that-endures/actions/runs/38867766111. It passed October 16 at 07:54 UTC; total 22m42s, wrapper 615.72s, original ordinal restoration 153.15s. Artifact 12032507300 construction-mature-ordered fully uploaded: ZIP 4,342,414,844 bytes, SHA256 b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4. Digest-checked diagnostics bind candidate 29,601,284,096 bytes SHA256 d96a0932ab0cb101de69e10ce4f0519de896d5cae44ee947c100b8af1429c7ee, manifest fd457aee712a4cfcfe69d10445e38294b21b34b5fe8496cbadb4484f6fbadf73, original context and generation-125 pin. The candidate remains explicitly unverified until the acceptance gates pass.

Ordering disk ruling: reserve one entire working database copy, one full SQLite
DELETE rollback journal and 8 GiB margin after extraction (62.78 GiB); at start,
also reserve both retained input bundles, the larger transfer ZIP and 64 MiB for
manifests (115.07 GiB total). Clear unused tool/image caches only on the fresh
disposable CI runner while retaining the selected Python runtime. Fail before
ordering if these bounds are unmet. A full target journal is conservative;
actual touched pages have not been measured for this mature ordering stage.

The ordinary runtime, core helpers and simulation behavior are unchanged.
Fine-grained mature commit phase/write accounting remains a deferred diagnostic
minor. Ordering records wall/CPU, output blocks, peak RSS, transfer times and
disk free bytes. Stage 0.5 acceptance is still gated by storage verification,
catalog verification, publication, exact years 1001/1002 and downloaded restore,
followed by the final Astra handoff.

### Task 6: Separate mature storage verification

The successful ordering candidate is retained and is the sole large input for
this stage. Authenticate its exact producing run/workflow/job/artifact, ZIP and
member inventory, manifest and database hashes/sizes, source configuration,
original context, generation 124 source and generation 125 pin. The unchanged
complete_upgrade_checkpoint.verify_storage performs its original read-only
verification and emits its original storage.json receipt. No construction,
catalog verification, publication or continuation runs here.

**Files:** simulation/construction_mature_storage.py,
simulation/tests/test_construction_mature_storage.py,
.github/workflows/stage-0-5-mature-storage.yml.

- [x] Write and observe 25 expected missing-wiring/workflow failures; implement the wrapper and pass all 25 checks. Real fixtures prove original receipt contents, unchanged candidate, corruption rejection despite refreshed hashes, interruption, receipt-write failure, broken diagnostic output, transfer provenance, duplicate starts, disk boundaries and nonfatal post-boundary summary failure.
- [x] Run affected checkpoint, transport and workflow tests; confirm unchanged runtime/core helper hashes. All 82 passed in 180.78s; one expected warning came from the duplicate ZIP-entry rejection fixture. Runtime tree and helper hashes match the green proof.
- [x] Obtain one independent review and resolve material findings with failing regressions. Independent review found no Critical, Important or Minor issues, passed 39 focused checks and verified a real closed-pipe subprocess exits 0 without stderr under unbuffered Python. No material findings required repair.
- [x] Publish and pin exact reviewed source, read back all outgoing files, inspect prior launches and start only storage verification. Source 31e1328a93b42c9fcc5c42926047c6ffcdf181c0, tree bd54fdd5cbdc4c7229a604c2ff9863c460e64f79; all six files matched exact readback. Launch 4f1a7d7f0bd6c90704b5370f5e508669afe3b00f changes only the source pin and its workflow was read back exactly. Zero prior storage runs were found; final pin tests passed 25/25 in 12.34s.
- [x] Record launch and update the existing monitor to inspect the storage receipt before catalog verification. Run 38872643738, job 116880131564 mature-storage: https://github.com/rax0h/all-that-endures/actions/runs/38872643738. It passed October 16 at 09:43:52 UTC, total 1h26m57s; original storage verifier 4428.83s, wrapper 4540.59s, candidate transfer 468.50s. Artifact 12037828504 construction-mature-storage fully uploaded: ZIP 554 bytes SHA256 7bf248f63a1b37be151f6da7c7745c056dd83e1a0ed0de320d21283f92cd6df4. Its exact sole storage.json member is 691 bytes SHA256 8e4324023fd60da647d2147eaa46d2cb171026037ecca07873080f7b086f3d65. Producer provenance and full ZIP digest were authenticated; downloaded receipt matches the exact original schema, context, candidate database and manifest. Diagnostic ZIP 12037943237 was separately downloaded and hash-checked. No catalog verification or acceptance is claimed yet.

Storage disk ruling: verification is read-only; retain a candidate-sized scratch
allowance plus 8 GiB after extraction (38,191,218,688 bytes). Before download also
reserve the retained database, ZIP and 64 MiB metadata allowance
(72,202,026,492 bytes). Keep the 8 GiB address-space guard and 300-minute command
within the 360-minute job. Upload the completed receipt with independent,
nonfatal diagnostics. Diagnostic stdout failures cannot suppress an already
saved receipt; verifier exceptions and receipt-write failures still propagate.

Reuse the approved full-suite/recovery proof only while runtime/core helpers
are byte-identical; the wrapper gets fresh focused tests and independent review.
The successful mature storage-verification duration is recorded above.

### Task 7: Separate mature catalog verification

The successful storage receipt is immutable and must be reused. Consume only
ordered candidate artifact 12032507300 plus storage artifact 12037828504;
authenticate their exact producers, ZIPs/members and files. Require the original
candidate manifest/database/context/source configuration/generation/pin and the
inspected 691-byte storage receipt. The unchanged verify_catalog must check the
original storage receipt authority and run only the original catalog verifier.
Never repeat successful storage verification to advance this stage.

**Files:** simulation/construction_mature_catalog.py,
simulation/tests/test_construction_mature_catalog.py,
.github/workflows/stage-0-5-mature-catalog.yml.

- [x] Write and observe 30 expected absent-wiring/workflow failures, including normal/rejected launch guards, refreshed-hash wrong receipt authority, interruption/write failure, changed prerequisites and broken diagnostics.
- [x] Pass new real-fixture tests and affected checkpoint/transport checks; verify unchanged runtime/core helper hashes. All 30 new checks passed in 28.53s; all 87 affected checks passed in 385.82s. The one warning is the intentional duplicate ZIP-member rejection fixture. Runtime/core helpers match the approved green proof.
- [x] Obtain one independent review and resolve material findings with failing regressions. Independent review found no Critical, Important or Minor issues and passed 44 catalog-wrapper/transport checks in 31.19s. Runtime tree and helper checks passed independently; no repair was required.
- [x] Publish/pin exact reviewed source, read back outgoing files, inspect earlier launches and start only catalog verification. Source e83c2f725cbe133a0401823cbeb3d351e927f292, tree b73e94d8c1cf26a7c2305be56fdddba3bc503417; all six files matched exact readback. Launch ee5000a156ebcf1fcec4a893da1a06958feb0ed5, tree 4cc65ab09e4aa9743590aed61d653269e1f454d7, changes only the source pin and its workflow matched exact readback. Zero prior catalog runs were found; final pin checks passed 30/30 in 26.09s.
- [x] Record launch and update the existing monitor to inspect the catalog receipt before publication. Run 38884880079, job 116920088588 mature-catalog, started October 16 at 10:05:19 UTC: https://github.com/rax0h/all-that-endures/actions/runs/38884880079. Exactly one run was observed; the existing monitor was retargeted and remains enabled. No mature catalog result, publication or acceptance is claimed.

Reuse the storage stage's read-only scratch and transfer reserves, whose 64 MiB
metadata allowance also covers the small storage-receipt ZIP. Keep 8 GiB memory,
300-minute command/360-minute job and mandatory receipt upload after nonfatal
diagnostics. Check the storage receipt and candidate manifest remain unchanged
after verification. Publication, exact continuation and downloaded restore
remain later stages, followed by final Astra handoff. The runtime and original
helpers remain unchanged; focused real-fixture checks plus independent review
apply to this wrapper. Catalog run 38884880079 passed October 16 at 11:40:32 UTC;
total 5713s (1h35m13s), wrapper 5211.71s, original catalog verifier 5136.86s,
candidate transfer 402.47s and storage transfer 1.62s. Artifact 12043567528
construction-mature-catalog fully uploaded: ZIP 585 bytes SHA256
854c941a708c3aa7abd8a85836369c4a209e089496d6b82906afe30f9a9b1bbd.
Its sole catalog.json member is 753 bytes SHA256
f453b3f861ad868d64a5b18adcfdf6869542ede4bc3cb9b564f03e594ccef3e3.
Producer provenance, downloaded ZIP/member and original receipt authority were
authenticated against the exact storage receipt and candidate. Diagnostics
12043383557 (3267 bytes) were downloaded/digest-checked independently.

### Task 8: Separate mature publication

**Files:** Create simulation/construction_mature_publish.py,
simulation/tests/test_construction_mature_publish.py and
.github/workflows/stage-0-5-mature-publish.yml. Record catalog result in
simulation/stage_0_5_mature_catalog_result.json; update this plan/spec status.

**Interfaces:** run_publish(candidate, storage_receipt, catalog_receipt, source,
bundle, *, workflow_sha) consumes ordered artifact 12032507300, storage
12037828504, catalog 12043567528 and original year-1000 source 11870590333.
All exact producers/ZIPs/members/files/context/configuration/pin/generation and
original chained receipts must authenticate before unchanged publish_p5 runs.
It produces ONLY checkpoint.json and p5-long-complete.sqlite, using the normal
P5 complete checkpoint schema and original control state. The original context
is retained separately from the executing producer. No successful verifier or
construction stage, simulation, continuation or world generation may run here.

- [x] Write real-fixture tests for exact published values/aliases/normal receipt, immutable inputs, refreshed-hash foreign receipt/config/pin rejection, interrupted publication, receipt failure/race/no-overwrite and nonfatal post-boundary diagnostics. Add exact transport, launch, workflow and disk-boundary tests.
- [x] Run the new test file and observe expected absent-wiring/workflow RED failures. All 36 failed in 2.49s for the missing module/workflow. Eight later focused authority regressions also pass.
- [x] Implement only publication wiring around unchanged publish_p5. Use a disposable P5 workspace with a hard link to the read-only source and a copied source receipt; preserve original inputs. Retain a closed, fsynced complete database and original normal complete receipt before continuation. All 44 new checks passed in 20.18s. The test's ordinary World comparisons use disposable copies; all retained inputs and published bytes remain unchanged.
- [x] Run the new publication, construction, transport and checkpoint/P5 affected tests; check runtime/helper/P5 runner hashes against the approved proof. Before the workflow-only cleanup repair, 101 passed in 247.05s. Final affected gate passed 102/102 in 324.32s; only the existing intentional duplicate-ZIP warning. Runtime/core/P5 helper identity remained unchanged.
- [x] Obtain ONE independent review of this stage and resolve material findings with failing regressions before publishing. The initial attempt was interrupted by a transient usage limit; the same reviewer resumed and completed the review. No Critical, Important or Minor findings; 59 independent publication/transport checks passed in 19.62s. Runtime/core/P5 equality and helper hashes were independently verified. The disk-cleanup regression passed as part of all 45 publication checks (22.52s).
- [ ] Publish exact reviewed source, read back all outgoing files, pin it in a separate launch, inspect all prior publication launches across SHAs, run final pin tests and launch only publication once. Record actual run and retarget the same monitor.

Publication disk ruling: allow one complete working copy and one full SQLite
rollback journal OR one full-sized upload ZIP, plus 8 GiB after all extractions.
Retained candidate bytes are 29,601,284,096. Original source extraction is capped
at 16 GiB (enforced before publication); source-job disk logs show roughly 11 GiB
for its retained source plus prior cold input, but do not give an exact member
size. Before downloads also reserve the candidate, that full source cap, the
larger transfer ZIP and 64 MiB metadata. No second full database copy is needed:
the P5 source and retained completed output use hard links, while receipts are
copied into disposable space. Preserve 8 GiB memory, 300-minute command inside
360-minute job, and mandatory upload after nonfatal post-boundary diagnostics.
Use the ordering stage's broader disposable-runner cache cleanup, which measured
117 GiB free rather than the smaller cleanup's 103 GiB. Retain Python and the
Actions bundled runtime. A real disposable-filesystem regression reproduces
missing tool/image cleanup and verifies the repaired script preserves Python.
If any size or headroom bound is unmet, fail before publication, not blindly retry.
The original source artifact expires October 28; later construction/receipt
artifacts expire October 30. Full large ZIP/file authentication runs on the
fresh CI runner, as in earlier stages; local connected-app downloads are capped
at 512 MiB and cannot download the 1.34 GB original source or 4.34 GB candidate.
No required check is skipped: real fixture tests and the same tested CI transport
perform them in the supported environment. Mature publication duration remains
unproven; acceptance still requires continuation, downloaded restore and Astra.

## Execution ruling

Daniel approved the explicit request to implement and test this revised split. Execute inline as offered; this is not another request to approve routine planning. Do not launch mature construction as part of this approval. The only independent agent is the final review required by executing-plans.
