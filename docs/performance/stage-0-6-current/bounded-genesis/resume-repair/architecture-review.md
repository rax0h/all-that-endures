# Offline resumable genesis: independent architecture review

Historical design recommendation. Final checkpoint custody is specified in
docs/superpowers/specs/2026-11-10-resumable-proof-genesis-design.md and the A2/A4
closure entries: uniquely ordered successful publication steps in a completed
producer job bind an exact attempt and upload creation time. This permits reuse
after later cleanup failure on an explicit resume; it does not let a failed DAG
continue or relax the original successful full-suite/proof-map prerequisites.
The original recommendation below is preserved as review history.

Recommend a harness-only staged pipeline using unchanged runtime
`94267bb00a219702a4bd1700a2fc0600a5c5aa56`. Keep the six proof builders in one owned
transaction. Authenticate and retain each completed stage independently, so a
later timeout restarts only that stage. No production code or expensive runs were
performed for this review.

Saved run42823293423 evidence shows capture/source/physical transfer completed at
5955.83seconds and the baseline digest started at11921.96seconds. Thus the digest
had approximately678seconds before the12600second budget, not a full-budget
digest trial. `prior-timeout-summary.json` preserves the observations. The retained
timeout evidence contains logs/JSON, not a reusable closed intermediate SQLite
checkpoint; it cannot recover that lost runner's capture/catalog file.

## Baseline digest first

Moving the canonical baseline to a distinct writable copy of the authenticated
original complete-format6 source is sound for this narrowly pinned path. Its
receipt is **source-digest-observed**, not source/catalog/proof validation.

The native transfer preserves current payloads, immutable segments, ordering,
allocator state and identity incidences. It changes store identity and operational
lease/storage bookkeeping, which are not canonical World fields. The checked
catalog path with `_for_proof_genesis=True` adds validation, not logical World
mutation. Comparing the post-rebase canonical digest against the original-source
digest therefore checks transfer plus rebase; the previous copied-before versus
rebased-after control checked only rebase. Do not generalize this reasoning to
legacy graph normalization.

Required conditions are exact original input bytes/hash and opened
seed/year/head/rules, no save or logical mutation during the digest, all existing
capture/catalog/roster/reference/type/sequence/graph checks, mandatory pre-rebase
and owned post-rebase source audits, and final World/proof/physical checks. A small
ordinary fixture should establish original→captured→checked→rebased digest equality
and graph/allocator preservation before mature execution. A900second computation
canary can now fail before the two long preparation stages.

For field progress, pass an adapter to the unchanged `canonical_stream.digest`
that yields the original `_canonical_fields(cls)` pairs once, in their exact
order. Emit diagnostics only for the root World class; do not read/materialize
field values, alter pairs, or change hashing. Check wrapped versus unwrapped
digest equality on ordinary fixtures. A timeout emits no successful digest receipt.

## Stage and failure boundaries

| Stage | Existing operation | Durable success boundary |
| --- | --- | --- |
| Source digest canary | Open a byte-identical original-source working copy; owned read-only canonical digest; close outside scope | Observed digest receipt bound to original input hash/context. Original retained SQLite remains the durable input; a second DB upload is unnecessary |
| Capture | Full-source-audited native current-head copy with existing private target physical check | Closed captured SQLite, new captured store UUID, original source head, output hash and performed/pending-check declarations |
| Checked catalog | Existing `_copy_current_checked_catalog(...,_for_proof_genesis=True)` with the narrow capture handoff below | Closed checked working SQLite and receipt; all current catalog, roster, reference, graph, type and sequence checks completed |
| Rebase | Existing private rebase, including its mandatory full pre-audit, dependency-token reset and row/checksum rewrites | Closed generation0 SQLite and receipt, retaining captured UUID and logical year1001. If post-audit is deferred as in94267, explicitly mark it pending |
| Digest after | Open a distinct working copy of rebased output; owned read-only unchanged canonical digest; close | Digest equals the observed original baseline; receipt binds exact rebased ancestry and closed output hash |
| Complete proof build | Format7/pin setup, real source audit, all six existing builders inside one `ProofGenesisTransaction`, final World audit, sealing, physical/FK checks and commit | Closed format7 generation0 database plus external manifest commitment and exact file hash |
| Operational measurement | Explicit proof opener; real first year/save; warm year; close | Measurement receipt plus closed saved generation1/year1002 database, saved external commitment/hash. Warm unsaved year1003 is not the saved checkpoint |
| Fresh restore | Fresh process/runner against authenticated saved bytes and expected commitment | Accepted year1002 canonical digest, original source binding, source immutability and target verdict |

A receipt for capture or rebasing must not imply checks that were deferred.
Completed intermediate transforms are preparation artifacts, not admitted World
authority. The proof-build stage always reruns its real source audit in its new
owned transaction; no SQL certificate, Python object, hash state or partially built
forest is carried across processes. If proof construction fails, restart from the
closed digest-after checkpoint, not from a partial proof transaction.

## Capture handoff options

Prefer the one-shot harness adapter over duplicating catalog validation or
changing the tested runtime. In its isolated worker, narrowly replace only the
single expected `LazyRecordStore.copy_current_head` invocation made by the existing
catalog helper. Before invocation, authenticate the captured artifact and exact
closed DB hash/context. The adapter must:

- Match exact source/destination roles, expected codec/schema/rules and private
  defer option; reject an unexpected call or second call.
- Create a distinct writable destination using a closed-file copy, never a hard
  link or move of the retained input. Verify byte equality before SQLite opening.
- Preserve the captured UUID/head deliberately, return the corresponding real
  `CopyResult`, and restore the original method in `finally`.
- Assert the expected call happened once, every ordinary helper validation
  completed, retained input bytes stayed unchanged, and output closed normally.

This replaces repeated acquisition of already authenticated captured bytes; it
does not replace any catalog check. A production helper extraction is cleaner
long-term but changes runtime identity and requires new runtime validation.
Copying the validator's implementation into a harness risks silent omitted checks
and should be avoided.

## Producer trust, validation reuse and receipts

Keep validation-gate evidence separate from intermediate-stage evidence.
Successful full-suite and proof-map jobs from9e6 can be reused even though their
parent run's mature job failed. Require the exact run/attempt, job IDs, commit,
workflow/branch/event and successful required steps, plus their source receipts
and runtime tree94267. Do not accept a job by display name alone or require the
overall parent run to be green. New harness/workflow/request code needs its own
reviewed hashes and targeted staged/fresh-process tests; old runtime green does
not validate the new adapter.

`checkpoint_artifacts.authenticate` already selects a successful producer without
requiring overall-run success; its pattern is usable, but the new boundary should
also pin attempt/job/head/step identities and parsed timestamps. Do not weaken
`authenticate_retained_producer` globally: it protects a different, originally
successful source transport.

Each stage receipt should bind an exact schema/stage/options version, original
source authority/hash/size/year/head/rules, captured identity lineage, runtime tree
and actual runtime tuple, reviewed harness/workflow fingerprints, exact parent
artifact and raw receipt hashes, input/output closed-file hashes/sizes, performed
and pending checks, and relevant digest/manifest fields. Match exact expected
input roles and stage order. Preserve the original source UUID separately from
the new captured UUID and generation0/1 contexts. Use strict JSON and typed fields.

Consumers authenticate the exact successful producer job and authoritative stage
and upload steps, immutable artifact ID/archive digest, safe exact members and
limits before opening a writable working copy. Authenticate chain evidence without
needing to redownload every old DB. Retention is finite: preserve the latest usable
checkpoint and ancestry metadata; an expired ancestor must not force recapture
when an independently authenticated descendant contains the complete data/binding.

## Operational conditions that prevent another whole restart

- Use a separate resume request/workflow and `.github/tests` harness tests. The
  existing proof-map workflow triggers long validation on changes to its own YAML,
  `simulation/tests/**` and the old genesis request. Changing the old request also
  enables the monolithic mature job. Do not accidentally retrigger it. New request
  changes select expensive stages; harness/docs-only edits run targeted checks.
- Stage completion must include remote durability. Fsync/close SQLite, reject
  journal/WAL/SHM sidecars, hash closed files, publish the receipt last, then upload.
  Retry upload while the completed closed file still exists; do not recompute the
  expensive stage for an upload retry. End the producer job without fallible
  optional diagnostics after that boundary. Failed/censored jobs upload logs, not
  a success checkpoint. Downstream jobs require the exact completed checkpoint.
- No raw hash/copy while a SQLite connection has the file open. This also avoids
  the previously documented POSIX lock observer hazard. All work uses independent
  copies; original and retained stage inputs are checked unchanged after closure.
- Keep computation and transport/closure budgets separate. Reserve job time for
  hashes, closure and upload; report both stage and cumulative wall time. A
  fifteen-minute canary timeout is censored evidence, not an integrity verdict.
- Preflight per-stage disk for archive+retained input+writable output+journal+
  scratch+upload margin. Proof output can exceed original-source size. Existing
  extractors have100GiB total caps; choose explicit justified stage caps, do not
  silently remove limits. Repeated30GB DB checkpoints cost I/O/storage; metadata-
  only read-stage receipts may reference an already durable DB when the contract
  makes that identity explicit.
- Pin/record consumer Python/SQLite fingerprints and loaded runtime paths; do not
  mix a new harness checkout with an unintended imported engine. Input download
  and hashing warm filesystem caches; resumed timing is not a cold-cache claim.

Before expensive stages, run targeted provenance/receipt/adapter checks and one
small fresh-process end-to-end stage chain, including resume from a completed
predecessor and absence of a success receipt after interruption. Validate original
versus staged canonical equality and final fresh proof restore using existing
runtime functions. These are one bundled review group, not a CI cycle per issue.
Mature resource/timing feasibility remains unproved; resumability prevents loss
of completed work rather than promising a shorter total computation.
