# Earlier checkpoints inside complete-upgrade construction

Status: approved, implemented and green in bounded CI. Stage 0.5 remains unaccepted.
The large retry remains paused. This extends the previously approved
post-construction verification split; its earlier construction boundary is new.

## Failure and preserved evidence

[Run 38762444566](https://github.com/rax0h/all-that-endures/actions/runs/38762444566)
failed with exit code 124 at 20:42:28 UTC on October 15, 2026. Its capture
command reached its 300-minute timeout. This was not the six-hour hosted-job
ceiling. No integrity assertion, MemoryError, or disk-full exception appears
in its log.

Only the 6,593-byte diagnostic artifact was uploaded:
[12005761786](https://github.com/rax0h/all-that-endures/actions/runs/38762444566/artifacts/12005761786).
There is no candidate checkpoint from this attempt. The original retained
year-1000 lazy source artifact 11870590333 remains available and unexpired;
its metadata and digest were rechecked. The original world need not be
simulated again. Its archive was not redownloaded in this investigation.

| Construction interval | Measured duration |
|---|---:|
| Private source copy | 21m 16s |
| Source validation | 20m 35s |
| Remaining source capture | 13m 18s |
| Normalization | 32m 18s |
| Staging and catalog construction | 71m 56s |
| Complete manifest preparation | 5s |
| Commit preparation, writes, acknowledgement and scratch cleanup | 136m 40s |
| Order restoration before timeout | About 1m 40s; did not finish |

The first capture heartbeat began after download and provenance checks.
Catalog commit returned at 20:40:48 UTC, 296m 8s after that heartbeat.
Order restoration then began. The command timeout arrived before the
existing capture hook, which runs only after successful order restoration.

The duration labeled commit is the whole target.commit() call, including
disk preparation and its cleanup. It is not a measurement of SQLite's final
COMMIT statement alone.

Machine-readable measurements:
[stage_0_5_mature_capture_timeout.json](../../../simulation/stage_0_5_mature_capture_timeout.json).

## Root cause and limits of the diagnosis

The checkpoint is too late to protect construction. complete_upgrade_checkpoint.capture()
links the private database only after _restore_copy_ordinals succeeds.
Until that boundary, both the destination and conversion inputs are disposable.
The earlier successful verification-resume proof does not cover interruption
during construction. This mature failure demonstrates that gap.

The previous run reached the same post-commit point after 192m 50s of
construction. This attempt required 296m 8s. Major intervals before verification
were consistently around 1.5 times slower. Comparing b15f4e1 with the repaired
runtime confirms the production changes are in sequence/catalog verification;
the commit and conversion-workspace code are unchanged. This supports overall
throughput variation as a concern. It does not establish whether CPU, storage,
host contention or another environmental factor caused that variation.

The earlier mature log reports 44,187,048 staged row entries, 11,347,739,819
staged payload bytes and a 21,524,033,536-byte workspace after catalog staging.
These are cumulative staging entries, including intermediate streams; they
are not a count of unique final World records.

A new local bounded profile used the existing 500-person/500-Event conversion
probe. It restored the exact expected digest. With cProfile enabled only
around prepared commit, that commit took 14.75s, with 15,571 version changes,
2,501 identity changes and 533 ordinary changes. ReplayRows.__iter__ accumulated
8.10s; SQLite execute calls accounted for 0.76s of self time. These overlapping
profile categories must not be added together. This is evidence of substantial
codec/replay work on that fixture, not proof of the mature workload's dominant
cost or of a particular optimization's benefit. No runtime optimization was made.

The failed mature run did not reach either target verifier. It therefore does
not disprove the sequence-scan repair, and it does not measure the repaired
catalog verifier's mature duration.

## Intended outcome and decision

Preserve Daniel's existing objective: finish exact mature-world acceptance
without another timeout discarding hours of completed construction. Preserve
identity, ordering, counters, RNG, corruption checks and source provenance.
Do not start a large job on the strength of another small-fixture ETA.

Options:

| Approach | Benefit | Limitation |
|---|---|---|
| Increase the command timeout | Small workflow change | Still loses construction; six-hour job ceiling remains |
| Optimize replay/codec work first | May reduce elapsed time | Speedup and mature headroom are unproven; still no earlier recovery |
| Persist construction inputs and committed output separately | Protects distinct completed stages | Requires a checked intermediate-work protocol and interruption proofs |

Recommend the third option. Treat replay/codec optimization as a separate
measured change if stage-level evidence later warrants it.

## Proposed construction stages

1. **Prepare replayable inputs.** Finish source checks, normalization and
   catalog staging. Before target.commit(), retain the closed private target
   database and the exact replayable commit inputs, order-restoration inputs,
   namespace states and checked metadata. Existing canonical staged rows and
   their count/order commitments should be reused where possible. Avoid
   decoding and reencoding the complete normalized graph just to export it.
   Publish a construction-prepared artifact only after all required files and
   descriptors are durable and authenticated. No complete-format acceptance
   receipt is emitted.

2. **Commit the prepared construction.** Authenticate the prepared artifact,
   work on a disposable copy and call the original atomic store commit with
   exactly its captured arguments. Save its closed, committed private database
   before order restoration begins. Retain a reference to the authenticated
   original order/state inputs. An interruption here repeats only commit,
   leaving preparation available. This does not attempt to resume midway
   through a SQLite transaction or trust partial writes.

3. **Restore ordering.** Authenticate the committed artifact and original
   order/state inputs. On a disposable copy run the original
   _restore_copy_ordinals. Save the existing unverified candidate bundle after
   successful restoration. An interruption repeats only this stage.

4. **Use the existing verification and acceptance pipeline.** Storage
   verification, catalog verification, publication, exact year-1001/year-1002
   continuation and independent downloaded restore still gate acceptance.
   Existing successful stage receipts are reusable only for their exact
   immutable artifact lineage.

The first two mature intervals were roughly 159m and 137m in this failed
attempt, before new export/transfer overhead. These measurements motivate
the boundaries; they are not promises for the next attempt.

## Integration and trust requirements

Use a narrow explicit private converter seam or a small converter refactor
to expose the prepared inputs and order/state streams. Do not extract local
variables through stack-frame inspection, pickle Python objects, resume an
open SQLite transaction or make ordinary World readers accept intermediate
construction files.

Every manifest must bind stage, protocol version, runtime and harness SHAs,
source receipt/hash, producing CI run/job/artifact, store identity, generation,
checked pin, rules/configuration, file names/hashes/sizes and required stream
descriptors. Each stream descriptor must bind adapter kind, row count and
complete order/content commitment. Require an exact stage/member inventory.
Generation/token/next-incarnation/format/metadata values must be typed and
consistent with the checked target and source lineage.

Close writers before hashing and publishing files. Retain all required replay
rows despite ConversionWorkspace.close() and temporary-directory cleanup.
Transport hashes authenticate bytes; they do not replace existing logical
validation or CI producer-provenance checks. Keep intermediate candidates
explicitly unverified, immutable and outside normal application publication.

Never overwrite a source, prior artifact, receipt or accepted destination.
Receipt creation remains atomic and durable. Preserve the 8 GiB address-space
guard. Record file and stream sizes, rows processed, per-phase wall and CPU
times, database writes, disk headroom, and transfer duration. Give every stage
upload headroom and measure the additional export/download cost.

If converter/runtime code changes, the previously green runtime tree cannot
be claimed unchanged. Rerun applicable focused, recovery and whole-suite
checks for the new exact candidate. Scope the repair to conversion/validation;
simulation behavior and ordinary persistence semantics remain out of scope.

## Proof and launch gates

Before another mature construction attempt:

- In separate fresh processes, prepare, commit and restore ordering, then
  complete the existing verification/publication/continuation/restore proof.
  Compare exact World values, aliases, ordering, RNG and counters with the
  ordinary upgrade.
- Interrupt before and after each durable boundary and during each active
  phase. Prove restart reuses earlier artifacts without calling earlier
  construction code. Repeat on a fixture with real counted histories and
  shared nested identities, not only flat synthetic people/events.
- Reject missing, duplicate, reordered, corrupted and foreign stream/file/
  generation/runtime/producer inputs, including recomputed transport hashes
  around corrupt logical rows. Do not advance a failed stage.
- Inject receipt-write, upload, publication-race and disk-write failures.
  Earlier immutable artifacts and the original source must survive unchanged.
- Review the complete resume protocol independently. Run applicable fresh
  runtime validation if its blobs changed.
- Prove the small pipeline on fresh CI runners, including a deliberately
  interrupted construction stage and a later retry. Check artifact sizes and
  transfer times before enabling a single mature stage.

Do not re-run run 38762444566 unchanged. Do not silently start the next mature
stage when a bounded test turns green. Inspect its completed predecessor,
artifact provenance, measured time and headroom first.

## Current status

The approved split is implemented with a no-op private converter seam and
validation-only helpers. Local interruption, corruption, equivalence and
fresh-process tests pass; the independent review findings were repaired.
Fresh-runner run38819525026 passed all13jobs, including2594tests and2subtests,
complete recovery, real artifact transport, interrupted construction, exact
continuation and downloaded restore. Its runtime tree is3c7c833dbec178dc513c21ddf1ccdaa6f79d430a.
Preparation run38833265909 succeeded in2h50m47s and fully uploaded immutable
artifact12024550042 (3,631,292,089byte archive). Its authenticated diagnostics
report9,822s preparation/export, a21,538,623,488byte spool and808,775,680byte
target. Daniel's requested completion brief was delivered; he authorized
continuation from the saved inputs.

After75focused checks and independent review, commit-only run
[38851921152](https://github.com/rax0h/all-that-endures/actions/runs/38851921152)
started. Workflow0acb45ef35748f7eda3f8d212c5c33c5d408be8f pins reviewed wrapper
e32ffc7cdc87bf4bde408eb5957458fd6142736b. Runtime and checkpoint helpers remain
byte-identical to the green full proof. The wrapper authenticates saved
preparation, calls the original atomic commit on a disposable copy, and saves
closed committed output before ordering. Measured prior commit scratch usage
motivates100GiB free before download and75GiB after extraction. Commit run38851921152 completed successfully on October16 at07:11UTC; the
4,332,758,248-byte construction-mature-committed artifact12030703178 fully
uploaded. The whole run took2h29m27s; the commit wrapper recorded8461.09s after
164.90s of authenticated preparation download. Its29,405,450,240-byte target
and original preparation lineage are bound in digest-checked diagnostics;
see simulation/stage_0_5_mature_commit_verified.json for exact digests.

The separate ordering stage consumed the original preparation and committed
artifact. Its wrapper passed29 new checks and124 affected checks; independent
review found no issues and ran66 checks. Its fresh runner authenticated both
full ZIPs and their member/file/producer/configuration/pin/stream checks before
the existing restore_orders retained an unverified candidate. It reserved a
full working database copy, full DELETE rollback journal and8GiB margin.

Ordering-only run[38867766111](https://github.com/rax0h/all-that-endures/actions/runs/38867766111)
passed October16 at07:54UTC. Launch8b8c108f032f1e6d58339cc436310402b40a10ce
pins reviewed source0e1986f626b66feea37be65ea1fc8291a939c004. All outgoing
source files and the pinned workflow matched exact readback. Total22m42s;
the wrapper took615.72s and original ordinal restoration153.15s. Immutable
construction-mature-ordered artifact12032507300 fully uploaded, ZIP4,342,414,844
bytes SHA256b9c5ebb5f8e72dcb41d114283557a368cc08a841979defbea0ce228f825430d4.
Digest-checked diagnostics bind the original context/pin and candidate/manifest
digests; see simulation/stage_0_5_mature_orders_result.json.

Daniel's authorized continuation is a separate storage-verification job using
the unchanged complete_upgrade_checkpoint.verify_storage. The new wrapper
authenticates this saved candidate before read-only verification and retains
only the original storage receipt. Twenty-five new real-fixture/wiring checks
and82 affected checks passed; independent review found no issues and passed39
focused checks plus a real closed-pipe diagnostic test. No construction,
catalog verification, publication or continuation runs in this stage. No
mature-world acceptance is claimed. Storage/catalog verification, publication,
exact continuation and independent restore remain gates, followed by the final
Astra handoff. Fine-grained commit phase/write profiling remains deferred.

Storage-only run[38872643738](https://github.com/rax0h/all-that-endures/actions/runs/38872643738)
started October16. Launch4f1a7d7f0bd6c90704b5370f5e508669afe3b00f pins reviewed
source31e1328a93b42c9fcc5c42926047c6ffcdf181c0. All six outgoing source files
and the pinned workflow matched exact readback. Its CI wiring checks passed;
the existing monitor follows storage before catalog verification. No completed
storage receipt or Stage0.5 acceptance is claimed yet.
