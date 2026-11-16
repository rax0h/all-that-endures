# Protected current-engine mature launch

Request: `preserved-current-engine-mature-2026-11-15-1`, mode `mature`, smoke `43778758497`, resume `0`. This is the first compatible mature prefix for engine `84626841`, rather than a retry of the old monolith. Actual mature times and year-1002 deep acceptance remain unmeasured.

## Gates and immutable inputs

- Engine qualification `43735593694` / public `4eadb668` is unchanged. Full/proof artifacts remain available until November 29, 2026; their exact ZIPs and source receipts are also retained in this repository. Do not repeat these suites for this request/docs-only change.
- Successful smoke `43778758497` / public `935df38b` completed November 15, 2026 at 6:19 p.m. America/Chicago (November 16 at 00:19 UTC). All 359 harness tests passed. Every checkpoint/database producer was authenticated using real job/step timestamps. All downloaded archive hashes matched; uploaded catalog, rebase and saved measurement database bytes/hashes matched their sealed receipts.
- Interrupted rebase exited 77, published no false completed checkpoint and retained the exact catalog receipt/database. The ordinary next rebase step restored that same immutable parent. Fresh restore recovered year 2 / generation 1 / digest `cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451` and final smoke acceptance passed.
- All 48 critical source/workflow/helper blobs and engine tree match the smoke. Its hosted Python 3.12.16 / SQLite 3.46.1 runtime signature is bound to the archived real runtime details. The exact candidate tree was checked with real public smoke ancestry. Local branch and API-published commit IDs differ; no fabricated ancestry or local hosted-runtime substitution is used.
- Private draft 446184821 is still private/draft with the exact tag. Both manifests and all ten original-fixture parts match committed IDs, uploaded status, names, byte lengths and SHA256 values. The original mature ZIP was already fully reconstructed and checksum verified in preservation run 43734650623; actual consumer access passed in 43776600177. Live metadata was rechecked before activation. No second 4.4 GB copy is needed to prove the same completed preservation.
- Original year 1001, seed 843000, generation 126, database 29,922,463,744 bytes / SHA `4a39288b...`, ZIP SHA `4f040569...`, and expected year-1002 digest `2a9b53ed...` remain unchanged. The preserved transport has no Actions expiry; original source/accepted-year authority still applies at admission.

## Budgets and retained restart units

Each stage is a separate restart unit. Completed closed database plus sealed metadata survive later failure. Read-only stages retain their predecessor data reference. A partial upload or worker directory grants no checkpoint authority. Retry discovery selects the latest completed compatible producer; never reconstruct a compatible completed prefix automatically.

| Stage | Compute cap | Job cap | Writes a new database |
|---|---:|---:|---|
| Source digest/control import | 60 min | 120 min | No |
| Capture | 150 min | 240 min | Yes |
| Catalog | 150 min | 240 min | Yes |
| Rebase | 150 min | 240 min | Yes |
| After digest | 120 min | 180 min | No |
| Proof construction | 210 min | 350 min | Yes |
| Operational measurement | 15 min aggregate | 150 min | Yes, saved generation 1 |
| Fresh restore | 120 min | 180 min | No |

Transport restore is separately capped at 30 minutes. Each database upload has 45 minutes; sealed metadata and diagnostics each have 5 minutes. Read-only stages skip database upload. Gate/acceptance jobs each have 15 minutes. The smallest writing-stage job retains 90 minutes beyond compute for restore, upload, metadata, diagnostics and setup/cleanup. Measured open/save/first/warm subcaps are 60/60/300/300 seconds within the aggregate deadline. Copy, hash, transport and deep verification are outside those operational measurements.

Before a mature restore, remove disposable runner tools/images and measure actual free space. Original reconstruction requires ZIP + exact database + 512 MiB streaming chunk + 2 GiB reserve. Each next stage requires free space for two input-database sizes plus 64 MiB after source presence; transport requires compressed archive + uncompressed member + 64 MiB. Mature database admission is capped at 96 GiB. These are checked on the actual stage runner before expensive work, not inferred from local disk.

New stage artifacts retain for 30 days (the smoke's expire December 16). Compatibility requires unchanged engine, critical helper/workflow blobs, hosted runtime signature, rules/source/control identity and valid producer/expiry. Request budgets and documentation can change without altering the smoke algorithm. Each retry must recheck expiry and capacity.

## Acceptance and next decision

Measure open <=10 seconds, save <=2 seconds and warm year <=1 second separately; record first-year time too. Existing policy retains saved generation 1 and stops before an expensive fresh digest when targets miss. A target miss leaves Stage 0.6 and deep exact continuation acceptance open; it is not evidence of corruption. If targets pass, fresh restore must independently match the unchanged year-1002 control before acceptance. Optimize only the measured next bottleneck.

Raw completed-run metadata, hosted runtime/harness receipts, recovery evidence, all checkpoint archives and per-member hashes are in `smoke-43778758497-evidence.zip` and its index. `authenticate-smoke.py` verifies recorded evidence without running a World. Downloaded raw database archives were verified locally and are referenced by their authenticated artifact IDs; they are not duplicated into git.
