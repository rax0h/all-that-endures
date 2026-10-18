# Durable continuation implementation

Implementation status: the local saved-year protocol, separate verification,
receipt composition, independent restore and runner wiring are implemented.
Independent implementation review and all 17 fresh-runner proof jobs passed.
Actual mature gates remain pending. The old two-year command remains paused.
The new configuration pins the authenticated proof for the separate year-1001
save. Its independent concrete launch review cleared, and exactly one mature
save stage has now launched.
Monitoring remains disabled. Stage 0.5 is unaccepted.

The actual year-1001 save is [run 39098313631](https://github.com/rax0h/all-that-endures/actions/runs/39098313631),
created October 18, 2026 at 04:47:29 UTC. Workflow source
`94f7c72666d6bc2041ad3324ef1d2d65529f7810` checks out harness
`dd795af561ca81a342fd3aa8e835db5233ef8d6b` with configuration SHA256
`89ff9fc8221999dce7a1173a5e3a97f8d5d57a9e884f5f8fcd41c486cce9ac68`.
Readback and immediate duplicate/active checks passed before the single launch.
The run was in progress at launch inspection; no mature result is claimed.
`stage_0_5_save1001_launch_result.json` and `STAGE_0_5_SAVE1001_LAUNCH_REVIEW.md`
retain the exact record. Only this save runs; later verification must authenticate
its successful uploaded candidate and reuse it. No automatic downstream launch.

The single bounded proof/full-suite launch is [run 39090807612](https://github.com/rax0h/all-that-endures/actions/runs/39090807612),
created October 18, 2026 at 02:38:25 UTC. Its source is
`084f6a9e90614b9df6189d0501bcc38cd6a9175f`, full tree
`7fc2ceaac8322e5320c5f11fd14a4ea18a1790f1`, byte/blob exact against local
`fda8075624990906c910179c5cfb01db1b983337` for all 20 outgoing files.
The run completed successfully October 18, 2026 at 04:31:25 UTC. All 17 jobs
passed. Full suite: 2938 tests plus two subtests, 41 warnings, 6589.51 seconds;
focused selection: 124 tests, one expected warning, 149.71 seconds. The actual
fresh-runner interruption/retry and independent downloaded restore passed. The
restored bounded World also retained its shared nested identity and eight
counted-history descriptors. Proof and restore ZIPs/members were downloaded,
hash-checked and authenticated against successful producing jobs; recursive
restore acceptance and every implementation/helper/source identity check passed.

Original launch/readback snapshots remain in `stage_0_5_continuation_proof_launch.json`
and `stage_0_5_continuation_source_readback.json`. Actual result, artifact pins
and exact member hashes are in `stage_0_5_continuation_proof_result.json`.
`stage_0_5_save1001_launch_preflight.json` records the original publication,
separate provenance and unchanged mature guards. No small fixture constitutes
a mature result.

## Authority and previous evidence

The treasury-report repair passed run 39070285697 on exact source
`1fde17241c17bcb1b490e9f3e445e4b4de29a5da`: both jobs passed, including 2831
full-suite tests and two subtests in 5069.11 seconds. The execution runtime stays
`2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a`, subtree
`76dee76973928dbce72860156feb32f2d7f02f86`. The persistence runtime is unchanged.

The sole mature input remains published year 1000, run 38907665230, artifact
12049884660. Its complete database SHA256 is
`0d884e52a012ab55325c7111bfc1d054fa7c27aaf0947cf9ab8de4423c213e1c`;
the exact original checkpoint SHA256 is
`082081583f68c8e032669df7114e5a75950ed6e1a94d7000b653fe37d6f39f53`.
Original producer `bbc3cbf11becb58aa4b9483114559fd1296878f1`, configuration,
controls, context and source receipts are preserved separately from new
executing harness/workflow producers. Do not repeat successful preparation,
commit, ordering, verification or publication. Failed run 38992881882 uploaded
no year-1001 database; that simulation still has to run once.

## Implemented boundaries

* `continuation_receipts.py` validates typed, bounded, duplicate-free metadata,
  original checkpoint bytes, immutable authority and exact producer/candidate
  bindings. It publishes durable new receipts without overwriting evidence.
* `continuation_checkpoint.py` copies retained input, normally opens it,
  simulates one year, checks live counters around save, closes and publishes a
  saved-unverified bundle. Its audit/digest/restore stages normally reopen
  disposable copies and compare actual observations with the original controls.
* `construction_mature_continuation_stages.py` authenticates producer metadata,
  source/runtime pins and full ZIP/member/file transport; enforces stage/year,
  disk/address/output bounds and launch uniqueness; dispatches one pinned stage.
* `continuation_checkpoint_ci.py` executes a bounded 6x6, two-year fixture with
  populated treasuries, counted histories and shared nested identities. It
  proves interruption/retry and independent restore through fresh runner jobs.

The stage sequence is save1001, audit1001 plus digest1001, accept1001, save1002,
audit1002 plus digest1002, accept1002, continuation acceptance, independent
restore-values plus restore-digest, then restore acceptance. Successful sibling
receipts stay reusable for their exact candidate. Receipt-only acceptance never
downloads or reuploads a database. The exact saved year-1002 artifact remains
the final restore input.

Audit placement follows Astra's explicit design: the full audit observes the
saved, normally reopened World. Live counters are compared before and after
save. Every original substantive audit field, full digest and counters still
must match; no old P5 live-audit result is fabricated. Year-verified and
restore-verified receipts keep `stage_0_5_accepted` false pending final review.

## Verification and execution

The final affected selection passed **124 tests in 197.56 seconds**, with one
expected warning from the duplicate-ZIP-member rejection fixture. It includes a
15-process full transport pipeline and a reopened year-2 point check proving
shared craft provenance and eight actual counted-history descriptors. Python,
workflow graph, shell and diff checks passed. The fresh independent Sol review
found no Critical or Important issues; its 68 boundary tests and separate
15-process pipeline also passed. One minor timing-metadata validation issue is
recorded in `STAGE_0_5_CONTINUATION_CHECKPOINT_REVIEW.md`. Actual fresh-runner CI
has now passed on the byte-identical implementation. The Astra reviewer could not start because
of its model usage limit; the completed review used a fresh Sol context.

The implementation was built from observed failing regressions. Local gates
cover changed original authority, generation/year/runtime mismatch, interrupted
save/close/hash/receipt writes, audit/digest failure and fresh-process retry,
mixed candidates, complete saved-state comparisons, independent restore and
no-overwrite behavior. Runner checks cover active cross-SHA continuations,
duplicates/reruns, failed producing uploads, source pin verification, extraction
limits and disk boundaries. A complete 15-process local pipeline uses the real
authenticated ZIP transport against a test-only HTTP fixture; it is not a
substitute for actual GitHub fresh-runner CI.

Run the affected selection from the repository root with `PYTHONPATH=simulation:.`
and `python -m pytest -q`, selecting `test_continuation_receipts.py`,
`test_continuation_checkpoint.py`, `test_continuation_verifiers.py`,
`test_continuation_acceptance.py`, `test_continuation_restore.py`,
`test_construction_mature_continuation_stages.py`,
`test_continuation_checkpoint_ci.py`, `test_long_history_report_treasuries.py`
and `test_checkpoint_artifacts.py` under `simulation/tests/`.

The proof workflow `.github/workflows/stage-0-5-continuation-proof.yml` runs the
affected selection, full suite and separate actual GitHub artifact-producing
and downloading jobs. A final proof-summary job runs only after the actual
restore producer and full suite succeed. Its authenticated small summary binds
the actual restore receipt and exact implementation/helper fingerprints.

Before any mature launch, inspect all proof jobs and downloaded receipts, obtain
the final independent implementation/launch review, publish exact source and
verify byte readback. Pin the inspected proof summary ArtifactRef and exact
input ArtifactRefs in `stage_0_5_continuation_stage_launch.json`; publish a
separate workflow launch commit with the reviewed harness SHA and configuration
SHA256. Fresh byte identity with the proof is mandatory. Inspect active runs
across old/new continuation branches and launch only the next missing stage.
Give Daniel the direct link; do not poll a long run or re-enable monitoring.

## Implementation decisions and limits

1. Historical schema1 receipts are governed by their pinned exact bytes. New
   strict schema rules do not rewrite or reject historical fields merely for
   being outside the new schema. The risk of a mistaken restriction is rejecting
   an otherwise valid original checkpoint.
2. Local producer mappings are declarations; only the wrapper authenticates
   external producing jobs and artifact proofs. Local files never certify CI
   provenance. A mistaken boundary here could trust an unauthenticated producer.
3. Verifier receipts carry the exact original checkpoint text and saved
   manifest, bound by their hashes, so acceptance can recheck controls and
   generation without downloading the large database. This costs metadata
   space, bounded at 16 MiB per file. Restore observations reference the
   continuation metadata by its hash/binding to limit duplication.
4. The existing full transport stays byte-identical. A serial guard wraps its
   public extraction seam to reject ZIP-declared oversized members before
   extraction and restores the callable in `finally`. Concurrent unguarded
   downloads in the same process could share this guard; these runners perform
   serial downloads only.
5. A separate proof-summary job follows the completed restore producer because
   successful-job authentication cannot authenticate an artifact while its own
   producing job is running. This costs one additional bounded metadata job.
6. The bounded same-run proof obtains newly assigned IDs from exact
   run/workflow/job/name metadata and authenticates them immediately. Mature
   launches still pin explicit inspected ArtifactRefs. Ambiguity, wrong producers
   and non-first attempts reject. Incorrect selection would otherwise validate
   the wrong artifact.

Per-stage 300-minute commands, 360-minute jobs, 8 GiB address-space guard, full
rollback-journal/upload allowances and output cap remain. A declared database
size also constrains extraction before copy; an unknown size uses the full
allowed cap for conservative reservations. No mature time guarantee follows
from the small proof, and no performance optimization is included.

The complete actual year-1001/year-1002 evidence, authenticated saved artifact,
separate fresh downloaded mature restore and final Astra handoff still gate
Stage 0.5 and any main merge.
