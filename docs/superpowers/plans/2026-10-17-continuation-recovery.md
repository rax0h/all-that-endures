# Durable Continuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Sol owns implementation in the current
> session, followed by one independent final review. Do not spend an independent
> agent on every small task.

**Goal:** Retain each actual mature save before expensive verification, resume
failed verification without simulation, and complete independent downloaded restore.

**Architecture:** An immutable saved-year artifact is explicitly unverified.
Independent audit and digest receipts jointly authorize progression; the final
restore independently downloads and checks the exact retained year-1002 artifact.
The existing original controls and persistence runtime remain authoritative.

**Tech Stack:** Python 3.12, pytest, existing SQLite persistence sessions,
existing authenticated GitHub artifact transport and Actions.

**Spec:** [2026-10-17-continuation-recovery-design.md](../specs/2026-10-17-continuation-recovery-design.md).

## Global constraints

- Read the spec and `simulation/STAGE_0_5_CONTINUATION_RECOVERY_HANDOFF.md` first.
- Original publication is run 38907665230 / artifact 12049884660. Preserve the
  exact original checkpoint JSON, controls, context, config and producer split.
- Execute unchanged runtime `2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a`, subtree
  `76dee76973928dbce72860156feb32f2d7f02f86`; pin new harness sources separately.
- Schema `ate-validation-continuation/1`; saved artifact members exactly
  `candidate.sqlite`, `checkpoint.json`, `save.json`.
- Original years/generations: 1000/125 -> 1001/126 -> 1002/127. The production
  configuration always retains milestones [1001,1002] and bootstrap year 1000.
- Output DB cap 38191218688 bytes; metadata ceiling 16 MiB per file; 8 GiB
  address-space guard; 300-minute command and 360-minute mature job.
- Never open a retained input DB directly or hard-link it to a mutable working
  DB. Never regenerate controls, skip audit fields or advance an unverified year.
- Do not alter the old mature launch branch/workflow, enable monitoring or start
  a mature stage before fresh protocol CI and one independent final launch review.

## Review focus

1. Audit and digest from different saved artifacts with the same year must not
   combine into acceptance (Task 4).
2. A saved generation survives an audit crash; retry never calls simulation or
   save again (Tasks 2, 3 and 5).
3. Closing a normal session changes lease records. Hash only after close and
   prove every retained input stays byte-identical (Tasks 2, 3 and 6).
4. A later failed consumer must not invalidate an earlier successful producing
   job; a failed upload job must never authenticate (Tasks 1 and 5).
5. Saved-state audit placement must be explicit; full original report, digest
   and counters remain mandatory, with no fabricated live-audit result (Tasks 3,
   4 and 6).

## Files and interfaces

- `simulation/continuation_receipts.py`: strict metadata loading, schema/authority
  checks, atomic new-file publication and acceptance composition.
- `simulation/continuation_checkpoint.py`: local save/audit/digest/restore stages,
  always operating on disposable copies and returning explicit receipts.
- `simulation/construction_mature_continuation_stages.py`: production source pins,
  input transport, phase disk/identity guards, CLI stage dispatch and diagnostics.
- `simulation/continuation_checkpoint_ci.py`: bounded, populated fixture stages
  through the same protocol and real artifact transport.
- `.github/workflows/stage-0-5-continuation-proof.yml`: bounded separate-runner
  proof, including deliberate verification interruption/retry.
- `.github/workflows/stage-0-5-mature-continuation-stage.yml`: one explicitly pinned
  mature stage per launch; no automatic loop.
- Tests mirror those module names under `simulation/tests/`; do not modify the
  persistence runtime or restructure the existing P5 harness to build this.

`ArtifactRef` is a frozen dataclass in `continuation_receipts.py`, with exact
fields `artifact_id: int`, `run_id: int`, `workflow_sha: str`, `workflow_path:
str`, `producer_job: str`, `name: str`, `archive_sha256: str`, `archive_bytes:
int`, `harness_sha: str`, `runtime_sha: str`, `runtime_tree: str`. Reject missing
and extra fields, Boolean integers and malformed SHAs/digests. Production
wrappers authenticate these expectations with the existing transport and
published source; local stages do not pretend local files prove CI provenance.

`Authority` is a frozen dataclass in the same module containing the immutable
original `checkpoint_sha256`, `checkpoint_bytes`, `context`, `source_config`,
`publication: ArtifactRef`, `published_database_sha256`,
`published_database_bytes`, `checkpoint_runtime_sha`, `execution_runtime_sha`,
`execution_runtime_tree`, `bootstrap_generation`, `store_identity`, and
`output_max_bytes`. Nested mappings must be defensively copied or frozen. The
production wrapper constructs it from the existing pinned publication authority;
fixtures construct their own equally checked authority. No production test-mode
flag or environment bypass is allowed.

Every stage gets a separate `Producer` mapping with exact harness/workflow SHA,
run ID, job and stage. A manifest's own future artifact digest is never invented.

### Task 1: Strict receipt and original-authority boundary

**Files:** create `continuation_receipts.py` and `tests/test_continuation_receipts.py`.

**Interfaces:** `load_receipt(path: Path) -> dict`; `validate_original(checkpoint:
Path, authority: Authority) -> dict`; `validate_saved(bundle: Path, *, authority:
Authority, expected_year: int, expected_predecessor: dict, producer: dict) -> dict`;
`publish_receipt(path: Path, value: dict) -> None`. Returned metadata never implies
external provenance unless the wrapper authenticated its `ArtifactRef`.

- [ ] Write real-file RED tests for wrong original bytes/config/controls/product,
  duplicate JSON keys, extra/missing fields, symlinks, Boolean/negative years or
  generations, oversized metadata, wrong DB size/hash, foreign runtime and wrong
  predecessor. Assert rejection before any World open or mutable output exists.
- [ ] Observe failures with `python -m pytest -q simulation/tests/test_continuation_receipts.py`.
- [ ] Define exact key sets for saved/audit/digest/acceptance/restore schemas;
  validate original receipt from its pinned bytes rather than trusting a copied
  control object. Reuse durable no-overwrite publication patterns from
  `complete_upgrade_checkpoint`, with strict parsing added for the new protocol.
- [ ] Test publication interruption: no completed receipt appears after failed
  write/fsync/link, and an existing destination remains byte-identical.
- [ ] Run the module tests plus `test_checkpoint_artifacts.py`; commit this boundary.

### Task 2: Save one year and retain a closed unverified candidate

**Files:** create `continuation_checkpoint.py` and `tests/test_continuation_checkpoint.py`.

**Interface:** `save_year(input_bundle: Path, destination: Path, *, authority:
Authority, year: int, predecessor: dict, producer: dict) -> dict`. Bootstrap input
is the existing checked publication; subsequent input is a saved bundle plus
authenticated prior `year-verified` authority. Keep its original checkpoint file
byte-identical. Reuse `_counters`, `_compact_working_set`, `Simulation` and normal
World sessions without changing their runtime semantics.

- [ ] Add a real bounded fixture with populated treasuries and correct currency
  conservation, counted histories and shared aliases; compute its independent
  controls before persistence. Assert one simulation interval, generation +1,
  exact live counters before/after save and the three exact output members.
- [ ] Observe RED. Add faults after simulation, after save, during close, hash,
  receipt write and final publication. Assert no accepted candidate appears and
  all retained inputs preserve exact bytes.
- [ ] Implement copy/open/one-year simulation/save/counter comparison/close/hash/
  fsync/manifest publication in that order. After close, retain the working DB
  without an extra backup copy. Never publish a DB while its writer is open.
- [ ] Guard against generation or control mismatch, output cap violation and
  wrong input year. Assert save stage cannot call audit, digest, snapshot,
  conversion, world generation or earlier successful stages.
- [ ] Run focused tests; commit only after GREEN. Record the saved stage as
  unverified even when counters match.

### Task 3: Independent audit and digest stages

**Interfaces:** `audit_year(saved_bundle: Path, destination: Path, *, authority:
Authority, candidate: ArtifactRef, producer: dict) -> dict`; `digest_year` with
the same signature. Destination is one new small receipt file.

- [ ] RED tests call the real `_audit` and `World.digest` on separately reopened
  copies. Assert all original audit fields except timing, complete snapshot,
  counters, year, generation and identity match; assert the returned receipt
  binds the exact candidate and save-manifest hash.
- [ ] Inject a report mismatch without changing digest expectations, and a digest
  mismatch without changing audit expectations. Each must block its own receipt.
  A permissive JSON encoder or omitted report field must fail these tests.
- [ ] Inject audit failure after a successful retained save; retry audit in a new
  process while forbidding Simulation/save/conversion calls. Assert the original
  saved bytes and controls survive unchanged. Repeat for digest.
- [ ] Implement normal open on a disposable copy and retained-file hashes checked
  after close. Produce receipts only after all comparisons and input-preservation
  checks pass. Reuse substantive P5 audit/counter/digest helpers.
- [ ] Record `audited_state: saved-reopened`; never label it a live-object audit.
  Run affected report, P5 and checkpoint tests; commit GREEN.

### Task 4: Acceptance and exact lineage without another large upload

**Interfaces:** `accept_year(saved: dict, audit: dict, digest: dict, *, authority:
Authority, candidate: ArtifactRef, audit_proof: ArtifactRef, digest_proof:
ArtifactRef, previous_acceptance: dict | None, producer: dict) -> dict`;
`accept_continuation(first: dict, second: dict, *, authority: Authority,
producer: dict) -> dict`. Wrapper authenticates exact incoming receipt bytes
before calling these pure validation/composition functions.

- [ ] RED tests combine matching real receipts, then mutate every bound
  candidate/manifest/DB/year/generation/runtime/control/source/producer field
  independently and assert rejection. Same-year receipts from different
  candidates must reject even when their observed digest is equal.
- [ ] Require 1001/126 then 1002/127 for production, and explicit predecessor
  acceptance before the second save. Reject missing or foreign first-year proof.
- [ ] Emit `year-verified` and then `continuation-verified` without opening,
  recopying or uploading a database. Bind the original second saved artifact as
  the final continuation artifact. Keep Stage 0.5 acceptance false.
- [ ] Test successful audit reuse after a failed digest and successful save reuse
  after either verifier fails. Verify exact receipt hashes, not only decoded
  semantic values. Run focused tests and commit GREEN.

### Task 5: Runner orchestration and real transport proof

Execution order: build this task's orchestration and test definitions, implement
Task 6's restore stages, then return here for the final whole-protocol review and
fresh-runner CI gates. Task 7 starts only after both tasks are complete.

**Files:** create the two wrapper modules and two workflow files listed above;
create `tests/test_construction_mature_continuation_stages.py` and
`tests/test_continuation_checkpoint_ci.py`.

**Interface:** `main()` accepts explicit `--stage` from `save`, `audit`, `digest`,
`accept-year`, `accept-continuation`, `restore-values`, `restore-digest`,
`accept-restore`, and `--year` where applicable. Production inputs come from an
explicit checked-in launch JSON with stage/year/ArtifactRefs, pinned by the
separate workflow source commit. Unknown/incomplete stages fail before download.

- [ ] RED workflow/transport tests assert exact checkout source, runtime tree,
  report and P5/helper hashes, input artifact proofs, 300/360-minute limits,
  address limit, stage-specific required output and nonfatal diagnostics.
- [ ] Preserve `download_inputs`/`validate_inputs` for bootstrap save. Every later
  large input uses existing authenticated `checkpoint_artifacts.download` with
  exact IDs/digests and member inventory. Fetch producing-job metadata rather
  than requiring unrelated consumers to pass.
- [ ] Prove disk checks at equality and one byte below the spec's per-phase
  formulas; reject oversized declared artifacts before transfer. Protect retained
  input and reserve full working/journal or archive space before copy/open.
- [ ] Test same-SHA duplicates, non-first attempts and active runs across SHAs.
  Use one mature concurrency group and operator expected-ref publication.
  Preserve accurate pipeline exit status through `tee`; no error suppression.
- [ ] Bounded CI runs source, save1, deliberate audit interruption, audit retry,
  digest1, acceptance1, save2, audit2, digest2, continuation acceptance and actual
  downloaded restore on separate fresh runners. Each consumer authenticates the
  producing artifact; the interrupted probe catches its deliberate exception
  and proves no receipt before exiting successfully. It never repeats save1.
- [ ] Mandatory uploads define successful stage production. Add a failed-upload
  provenance rejection test; diagnostics cannot turn required upload failure green.
- [ ] After Task 6's restore implementation is GREEN, obtain one independent final implementation review after the whole local
  protocol is GREEN. Publish exact source, read back every outgoing file and
  launch bounded proof only. Record actual CI counts/results and artifacts.
- [ ] Run full applicable helper/runtime validation as required by changed bytes.
  Do not infer new protocol correctness from the report-only workflow.

### Task 6: Independent downloaded mature restore

**Interfaces:** `restore_values` and `restore_digest` have the same local stage
signature as Task 3 plus authenticated `continuation-verified` authority.
`accept_restore(values: dict, digest: dict, *, continuation: dict, proofs: dict,
producer: dict) -> dict` requires both fresh observations of the same final DB.

- [ ] RED tests require complete snapshot values and counters from a real
  reopened saved DB, plus full digest in the independent digest job. Fail when
  supplied only prior continuation receipts or a metadata-only stand-in.
- [ ] Both restore jobs freshly download/authenticate the exact final saved
  artifact, copy it to disposable space and normally open it; all retained input
  hashes remain unchanged. Do not simulate/save or create a new backup.
- [ ] Inject foreign original controls, runtime/source chain, candidate members,
  wrong year/gen, altered retained file and a wrong actual value. Reject every
  variant even when outer transport hashes are recomputed.
- [ ] Exercise both restore jobs in bounded fresh-runner CI and include them in
  final implementation review before any mature stage launch.
- [ ] After real 1001 and 1002 verification and artifact authentication, launch
  ONLY the separate mature downloaded restore stages. Preserve every successful
  predecessor and sibling receipt if either restore job needs repair.

### Task 7: Controlled mature execution and final Astra handoff

- [ ] Verify all required CI jobs and exact artifacts. Compare published
  runtime/helper/source blobs, inspect active/pending launches across SHAs and
  review the concrete launch configuration once independently.
- [ ] Launch only save1001 from original artifact 12049884660. Give Daniel its
  direct Actions link; do not wait/poll a long run or re-enable monitoring.
- [ ] At each user-requested continuation, authenticate the completed stage and
  exact retained artifact/receipt before launching only the next missing stage.
  Reuse successful audit/digest receipts for their exact candidate.
- [ ] Assemble all measured timings, original authority, both saved-generation
  proofs, complete comparisons and independent downloaded-restore observations
  for final Astra review. Report failures and unmeasured limits honestly. Do not
  merge main or declare Stage 0.5 accepted without the final review.

## Reporting repair already completed in this assignment

`simulation/run_long_history.py` now materializes only the treasury report maps.
`test_long_history_report_treasuries.py` contains three cases: legacy and
complete-format audit equivalence through mutation/save/reopen, and snapshot
detachment. RED was observed: one legacy pass, two failures (the exact mature
TypeError and live-reference drift). Record final affected/full CI results in
the handoff; this fix alone does not implement Tasks 1-7 above.
