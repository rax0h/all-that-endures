# Independent content-parent batch whole-package review

Verdict: no actionable production findings in the reviewed scope. No Minor findings remain open. This is correctness review plus bounded independent probes, not latency acceptance or a new full-suite gate.

Scope: new `simulation/ate_sim/persistence_proof_verify_batch.py`; `_guard_content_parent` change in `persistence_proof_publication.py`; `test_stage_0_6_content_parent_batch.py` including the subsequently added maximum-depth regression; design and plan dated 2026-11-13. Reviewed caller ordering in `persistence_lazy_store.py`, unchanged node codec and map reader, and publication fixtures/recovery behavior. Repository baseline was reported as local 7c8d493f / remote 0759128, runtime 95c61911, prior hosted GREEN43501337447. Other existing acceptance documentation is not production code under review.

## Reasoning

Strict locator increase makes each subtree's requested members a contiguous interval. `visit` first rejects or consumes the compressed prefix's leading absence interval, then visits the sixteen child intervals in order, and finally consumes the trailing absence interval. Every recursive required prefix grows by at least one nibble; canonical branch prefixes cannot exceed63, so maximum traversal is64 branches plus a leaf. A selected child is checked by unchanged `_read`, preserving digest/domain, canonical format, reference count and required-path checks. Nonselected child bodies remain unread. No cache, write callback or retained cross-call authority is introduced; memory is one current request, previous locator, and bounded64-depth/16-fanout frames.

Input is consumed through exhaustion on successful validation, including empty-tree paths; late malformed, duplicate, reversed and colliding locators reject. Callback exceptions propagate. Empty requests validate root-reference shape and empty-root identity without authenticating unrelated nonempty root bodies, consistent with selected-path contract and the explicit test.

The guard retains namespace/body byte checks and `_source_version` predecessor reading. TEMP spool sorts by the same domain-locator bytes recomputed by verification. Both map checks complete before `_write_lazy_changes`, identity, ordinary or segment writes. Only `ProofValueMismatch` on events maps to append conflict; corrupt selected proof bodies remain integrity errors. Versions retain their predecessor-integrity classification. Iterator cursors close before the outer finally drops TEMP state. The central publisher/recovery implementation remains unchanged.

## Independent evidence

Full qualified runtime fingerprint checked: Python version/compiler, interpreter binary hash, SQLite version/source id/compile options, extension binary hash and loaded SQLite library hash against the repository receipt.

- Exhaustive synthetic locator model:256 sparse maps,5,120 present/absent comparisons against ordinary independent `get`; includes gaps before/after compressed nodes and internal missing slots. Selected node read identities unique; no writes.512 late malformed/duplicate cases rejected.
- Maximum possible depth:64 branches and a leaf, exactly65 checked nodes.
- Node-reader callback failure propagated without writes.
- Actual persisted SQLite publication: injected iterator-consuming failure in each parent verification separately. No source writer called, transaction rolled back, TEMP spool absent. All persistent tables equal the pre-attempt snapshot except intentional `pin_attempts` pending recovery registration. `resolve_commit` returned `not_committed`; fresh-token retry committed; closed database passed `PRAGMA integrity_check`.
- Original implementation tests cover selected missing/body/count/path/domain corruption and prior-valid-call freshness. Existing publication tests cover unified rollback, loss-of-ack, source tampering, spilled preparation and retained authorities. Parent owns affected battery execution and resulting receipts; I did not rerun those files.

Logs/scripts are retained beside this review. `probe-initial.log` and `probe-diagnostic.log` contain successful mathematical/runtime checks followed by an overstrong probe assumption that all operational tables should roll back. `persisted-unrecovered.log` and `persisted-reused-token.log` preserve rejected retry experiments. These are probe corrections, not product regressions: `_register_attempt` intentionally persists pending state and requires resolution plus a new token. `persisted-probe.log` is the successful corrected persisted probe for both kinds. No production modifications were made by this reviewer.

## Closure register

| Origin | Observation | Action/evidence | Status |
|---|---|---|---|
| Independent probe | All-table equality incorrectly included durable pending-attempt registration | Compared unchanged source/proof tables; asserted pending registration; inspected existing `_register_attempt` and `resolve_commit`; retained failure logs | Closed: probe corrected |
| Independent probe | Immediate/same-token retry conflicts under established recovery rules | Resolve pending attempt, retry new token; both parent-failure scenarios pass in persisted-probe.log | Closed: probe corrected |

## Explicitly declined to judge

- No raw A-B/B-A speed claim; parent has not supplied final timed data to this review.
- No new hosted full-suite approval inferred from prior hosted GREEN43501337447.
- No mature-size, endurance, main/default activation or universal runtime compatibility claim.
- No authentication of unselected descendant bodies or nonempty root body with zero requested rows is promised; this is a selected-membership proof, matching unchanged point-read semantics.
- Hash collision resistance remains the existing cryptographic assumption. Same-stream locator collisions reject via strict ordering; the integration spool also rejects duplicate locator insertion.

## Same-group scope amendment: bounded ephemeral input buffer

Reviewed added `persistence_proof_parent_inputs.py`, amended guard integration, small-batch no-TEMP regression and forced-spill parent-failure regression. Initial TEMP-only timing reported by parent was worse in both pairs; it is not an accepted speed improvement. No final revised latency evidence was examined here.

The helper reserves `resident_bytes(row)+128` before retaining each row and spills before exceeding1MiB. Independent inspection found the128bytes sufficient for list pointers/over-allocation, transient two-item sorting keys, key-array and merge workspace on the qualified runtime; repeated resident accounting also conservatively counts shared integers/None separately per row. This bounds charged retained predecessor inventory; it is not a total RSS or allocation-peak cap. The current incoming row, source body/encoded key, helper fixed overhead and SQLite spill memory remain separate bounded or existing runtime costs. No long-lived cache or certificate is added.

Spilled state is set immediately after table creation, before buffered insertion, so partial insertion failures leave cleanup ownership intact. A same-kind duplicate locator rejects either through strict streaming order in memory or translated SQLite integrity failure during spill. Distinct kinds can share a locator. Guard cursor/generator closure and helper close run for either mode. Caller order and existing source/type/byte checks remain unchanged.

Independent amended probes (`helper-probe.py` / `helper-probe.log`) passed exact threshold admission, mixed-kind sorted spilling, duplicate rejection in both paths, collision during initial buffered spill, partial inserted-row callback failure and idempotent table cleanup. Representative maximal nonspill inventory:3033rows,552744estimated actual row/list resident bytes,1048364charged bytes (<1048576). This is accounting evidence, not a process-peak measurement. `amended-persisted-probe.log` records the real SQLite failure/rollback/no-source-write/recovery/retry scenarios passing for each parent with forced spill and normal memory limit.

Amended production verdict: no actionable code findings. One documentation Minor was raised to parent: design/plan must describe the new bounded-memory path and scope of its1MiB claim rather than retaining TEMP-only design text. Its closure is pending the parent's doc amendment. This supersedes the initial no-open-findings statement only for that documentation item.

### Documentation Minor closure

Closed after read-only inspection of both amended design and plan. They now explicitly distinguish1MiB charged retained rows (`resident_bytes(row)+128`, initial list charge), separately bounded current source/input row, and absence of any total-RSS/SQLite-page-cache bound. They also preserve the negative TEMP-only performance result and require revised whole-save evidence before promotion. Parent records this item as W13e in its consolidated closure register. No actionable findings, including Minors, remain open in this independent review. No additional CPU probe was run during revised raw measurement.
