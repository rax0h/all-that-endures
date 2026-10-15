# Checkpointed complete-upgrade validation

This is a validation harness, not a save format. `candidate.sqlite` is explicitly
unverified and must never be used as a P5 complete checkpoint. Runtime code under
`simulation/ate_sim` remains byte-for-byte identical to runtime commit
24cc39974b0762e428e2a5a0d7581f7f92216310 (subtree
c3229ed9ed46bd338bf31d76e7f037d0d77b87b6).

`python -m simulation.complete_upgrade_checkpoint` exposes capture, storage,
catalog, publish and p5-publish stages. Each takes an independently trusted
`--context` JSON containing runtime SHA, harness SHA and the source artifact's
ID/run/archive SHA-256. The command enforces an 8 GiB address-space limit.

Capture stops only after the existing target commit and successful ordinal
restoration. A hardlink retains the private database across converter cleanup;
the writer closes before hashing and manifest publication. It does not create an
accepted destination. Source verification and conversion checks are preserved.

Storage runs the original full store verifier. Catalog requires the exact
storage receipt and runs the original catalog verifier, including type and
sequence checks. Both use the captured checked pin, prohibit writes, verify
retained bytes, and publish a receipt only after successful verification.
Publication requires both receipts for the exact manifest/runtime/harness and
prior lineage, checks a private copy with the original complete-open check,
releases its pin through the checked store API, and uses the original atomic
no-overwrite publisher. The P5 bridge lets the existing runner validate its lazy
source and produce its normal complete checkpoint receipt.

## Trust and retries

A JSON receipt is not a certificate. CI separately authenticates the artifact
run, workflow commit/path, unique successful producing job and upload time,
archive SHA-256/size, and exact regular-file ZIP members. Fixed local filenames,
unexpected members, duplicates and traversal are rejected. The CI harness also
checks its checkout and exact green runtime subtree.

The small CI proof uses separate source, capture, storage, interruption, catalog,
publication, continuation and downloaded-restore jobs. The interruption job
executes the original catalog reader before faulting, retains no success receipt,
and checks unchanged candidate bytes. The next fresh runner resumes from the
same earlier candidate and storage evidence, then proves exact independent
control at years 1 and 2 and a further downloaded restore.

Use GitHub **Re-run failed jobs**, preserving successful upstream artifacts.
Do not rerun all jobs or overwrite immutable artifact names. An interrupted or
failed producer artifact is deliberately not trusted. Diagnostics are non-fatal
and run before the main final artifact upload. Job cancellation during the final
upload/transition can still leave unusable partial evidence; authentication
fails closed. Artifacts expire after 14 days. This is restartability between
stages, not within a failed construction or verifier.

## Evidence and remaining gate

Local focused gate: 66 passed in 247.40 seconds, plus two workflow policy tests.
This includes ordinal/capture faults, verification/receipt faults, corrupted
transport and payloads, malformed/foreign/reordered receipt rejection, destination
race preservation, fresh subprocess execution, alias equivalence, normal P5
receipt generation, exact continuation, original long-harness and sequence tests.
Independent review found no Critical/Important correctness issue. Its diagnostics
upload availability issue was treated as material to retry behavior and fixed
with a failing-then-passing workflow regression test.

Runtime evidence remains run38690643226: 2522 tests plus 2 subtests and the exact
3+4+3 recovery passed. The bounded fresh-runner proof run38756130032 passed all nine jobs in10m21s,
including68 harness tests, interrupted catalog verification, fresh-runner resume,
exact continuation and downloaded restore. Its final restore artifact is
11983179741 (archive SHA256
240b92c2df78105f905c9ed018e23bbe30721d7eb68e4240a56e84dcb66b4667).

The next stage uses `checkpoint_mature_capture.py` and the separate
`stage-0-5-mature-capture.yml` workflow on
`sol/stage-0-5-mature-checkpoint-validation`. It authenticates that green proof,
checks the exact green helper-file hashes and runtime subtree, authenticates
original artifact11870590333/run38508408370, and verifies every original source
configuration field and database hash. It requires55GiB free before download and
45GiB after extraction, keeps the8GiB process guard, and reports copy phases,
ordinal-restoration timing and60-second resource heartbeats. Its300-minute
command budget within a360-minute job reserves about60minutes for uploads.

This construction job creates ONLY an unverified candidate and summary. It does
not run storage/catalog verification or continuation. Inspect construction
elapsed time, candidate size and upload time before enabling subsequent large
stages. Existing measurements suggest construction could still take3–4hours;
that is an estimate, not a bound. A failure within construction still requires
construction to retry. Once capture succeeds, later stages can reuse that artifact.
Neither mature phase timing nor Stage0.5 acceptance is established by the small
proof. Do not retry the old monolithic six-hour job.
