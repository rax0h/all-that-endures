# Durable mature continuation and verification

Status: Astra design decision and implementation assignment. The treasury report
repair is implemented separately; the staged continuation protocol below is not
implemented or validated yet. Stage 0.5 remains unaccepted. Do not relaunch the
old two-year continuation command.

## Objective and preserved authority

Finish Daniel's exact mature-world acceptance without a late diagnostic failure
discarding an earlier successful save. Preserve the actual world, original
independent controls, rules, configuration, provenance and all required logical
checks. Scheduled monitoring stays disabled. No merge or acceptance precedes the
actual saved years, independent downloaded restore and final Astra review.

Start from published year 1000, run 38907665230, artifact 12049884660,
`construction-mature-published`. Do not regenerate the world, controls,
preparation, commit, ordering, storage/catalog verification or publication.
`simulation/construction_mature_continue.py` contains the exact immutable input
pins and remains the reference for validating them. Preserve its original
`CONTEXT`, `SOURCE_CONFIG`, `SOURCE_CHECKPOINT`, `PUBLISHED_FILES` and receipt
checks. The original configuration still describes both milestones [1001,1002]
and bootstrap year 1000; a per-stage year is a separate field, not a rewritten
source configuration.

Original checkpoint execution producer:
`bbc3cbf11becb58aa4b9483114559fd1296878f1`. Original simulation product in the
source configuration: `2bc3c85389760ff12578857f7d2a849bc5cf9201`.
Current validated execution runtime: `2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a`,
runtime tree `76dee76973928dbce72860156feb32f2d7f02f86`.
Keep these authorities separate from new harness/workflow producers.

The published database is 29601284096 bytes, SHA256
`0d884e52a012ab55325c7111bfc1d054fa7c27aaf0947cf9ab8de4423c213e1c`.
Its original checkpoint JSON is 134251 bytes, SHA256
`082081583f68c8e032669df7114e5a75950ed6e1a94d7000b653fe37d6f39f53`.
The archive is 3910109453 bytes, SHA256
`5ea709166d2bba7f7a22d614fed604f471973ae9ff757979a4148ff197c43382`.
It remains unexpired through October 30. The older lazy source expires October
28; neither expiry date is permission to regenerate the world.

## Observed failure and limits of the evidence

[Run 38992881882](https://github.com/rax0h/all-that-endures/actions/runs/38992881882),
launch `3512bf8f379934ff7b67c4832b164ea3d01e5bc8`, harness
`93f6d4259ce970b70af49431da287ee842dcaaaa`, failed October 17 at 05:56:50 UTC
with exit code 1. Its only artifact is diagnostic ZIP 12091846715, 6066 bytes,
SHA256 `e279474e393e0e6eeeca74dfa302900a925163146fb75876abc9aa757aa2146f`.

| Observed interval | Duration |
| --- | ---: |
| Open published checkpoint, after checksum verification | 1006.65 s |
| Simulate year 1001 | 4087.60 s |
| Save call and following compact diagnostics | 3645.25 s |
| Audit start to serialization exception | 4897.53 s |

`session.save()` returned before `audit_started`. This establishes passage beyond
the earlier missing-owner guard, not correctness of the saved world. No
`reopen_started` or `milestone_verified` record exists. Year 1002 never started.
The temporary database was not uploaded; year 1001 must be simulated again from
the original publication. Do not describe this attempt as having retained a
usable year-1001 checkpoint.

`snapshot()` exposed `world.currency.treasuries` directly. Complete-format
treasury entries are `LazyHistoryMap` instances, which the standard JSON encoder
does not accept. A real converted one-treasury fixture reproduced the same
exception in 0.437 seconds. Legacy dictionaries happened to work; empty
treasuries hid the defect. The existing 60-year continuation test checks digest
equality but does not call `_audit()`.

This evidence identifies a report-boundary bug and a validation-orchestration
failure. It does not justify another persistence-runtime rewrite. The observed
first-year simulation/save/audit cost also gives no defensible basis for putting
both years plus reopening and backup inside one 300-minute command. No new
mature-duration estimate is implied by small fixtures.

## Options and decision

| Approach | Result |
| --- | --- |
| Fix JSON and rerun the existing command | Leaves the known late retention boundary and unsupported combined time budget. Rejected. |
| Run one year per job, including all audits and reopening | Reduces scope but still discards its save if audit fails and combines two unmeasured scans with simulation. Rejected as the default. |
| Retain each save, then verify that exact artifact in separate stages | Protects completed simulation and gives each expensive operation its own budget. Selected. Adds transfer/open overhead. |

No speculative scan/codec optimization or raised timeout is part of this repair.
Use the existing 300-minute command, 360-minute job and 8 GiB address-space guard
per expensive stage. The design makes failures resumable; it does not guarantee
every stage will fit. Measure real stages and diagnose an individual overrun
before adjusting its design.

## Reporting repair

In `run_long_history.snapshot`, build the treasury report as an outer dictionary
whose values are ordinary `dict(coins)` copies. Treasury values are denomination
counts, already validated by `current_audit`; no recursive whole-world
materialization, permissive JSON default, stringification, omission or replacement
of invalid values is allowed. Preserve the exact eager report and original
control values. Test populated legacy and complete-format stores before save,
after actual mutation/save and after reopen, plus detached snapshot semantics.

## Stages and trust transitions

For each year, run **save**, **audit**, **digest**, then **accept-year**. Audit and
digest may run in parallel on separate fresh runners using independent working
copies of the same artifact. Only accept-year permits the next year's save.
Save 1001 consumes the published generation 125; save 1002 consumes accepted year
1001, generation 126. The only expected new generations are 126 and 127.

### Save

Authenticate the full input ZIP, producing job, exact members, file hashes/sizes,
original checkpoint and lineage before opening anything. Copy the retained DB
to disposable space; never hard-link a database that a session will open.
Normally open it and verify year, format 6, seed, store identity and generation.
Simulate exactly one year. Capture live year/counters immediately before and
after save, require that saving did not change them, and compare them with the
original bound control. Require the returned generation and captured head to be
exactly the predecessor's generation plus one.

Close the session normally before hashing, manifest creation or publication.
Record phase start/end, wall/CPU time, store I/O and bounded working-set metrics.
Capture useful working-set information before close without running full audits
or digest scans. Retain the closed database and receipt as a new immutable
`year-saved-unverified` bundle. Publish only after all files and the containing
directory are durable. A mandatory successful artifact upload completes this
stage; a local save or local manifest alone does not.

This stage must not call `_audit`, `_digest`, `snapshot`, backup, conversion,
world generation or independent control generation. No further simulation runs
in its process. It ends with no claim of full logical correctness.

### Audit

On a fresh runner, authenticate and fully download the exact saved bundle. Work
on a copy, open normally and verify its year/generation/store identity. Call the
unchanged substantive `_audit` checks with the repaired report adapter: current
state, currency conservation, event chronology/causality, material provenance,
event counts and complete snapshot. Require equality of **every** audit field
with the original control except `audit_seconds`; compare counters as well.
Produce a small `year-audited` receipt bound to this exact saved artifact and
manifest. Check retained input hashes after closing the disposable copy. Do not
save or simulate, and do not upload another database.

### Digest

Independently authenticate/download the same saved artifact on a fresh runner,
copy and normally open it. Verify year, generation, store identity, full World
digest and all counters against the original control and save receipt. Emit a
small `year-digest-verified` receipt, with retained input hashes unchanged. This
stage must not simulate, save, call the full audit or create a database backup.

### Accept-year and final continuation evidence

Authenticate the successful producer and exact bytes of both receipts. Require
them to bind the **same** saved artifact, database hash/size, manifest hash,
year/generation/store identity, original authority and execution runtime. An
audit for one candidate and digest for another never combine into acceptance,
even if values or recomputed transport hashes look plausible. Require the save
producer's success and its published artifact proof too.

Emit `year-verified` only when both checks pass. For year 1002, also authenticate
the year-1001 acceptance chain and emit `continuation-verified` binding both
milestones and their original controls. This is a new schema; do not fabricate
an old P5 result claiming it ran the old sequence. The exact year-1002 saved
artifact is the final continuation database. Reference its immutable artifact ID
and hashes instead of recopying/reuploading 30 GB merely to rename it.

### Explicit change to audit placement

The old harness audited a live World after save, then reopened it for a digest.
The staged harness audits the **saved, normally reopened World**. Capture and
compare live counters in save, but do not claim that a full live-object audit
ran there. This changes evidence placement, not the required saved-world values:
full persisted audit and full digest must both equal the original independent
control, with exact counters, years, generation and lineage. Keep the existing
monolithic P5 harness and its live-audit regressions as compatibility tests.
Do not weaken audit fields or regenerate controls to accommodate the new order.

## File protocol and authentication

Use schema `ate-validation-continuation/1`. Saved bundles contain exactly
`candidate.sqlite`, the byte-identical original `checkpoint.json`, and
`save.json`. Small stage artifacts contain exactly their named receipt:
`audit.json`, `digest.json`, `year-verified.json` or `continuation-verified.json`.
No stage may accept extra members, symlinks, duplicate JSON keys, unexpected
fields, Boolean-as-integer years/generations, negative counts or malformed
hashes. Use explicit schema validation rather than trusting a dictionary's
truthiness or a caller-provided `passed` flag.

`save.json` binds schema/stage, previous/current year and generation,
store_identity, database name/bytes/SHA256, original checkpoint bytes/SHA256,
original configuration/context/publication proof, predecessor artifact and
acceptance references, execution runtime SHA/tree, producing harness/workflow
SHA/run/job, live counters before/after save and measured phase statistics.
Preserve original source receipts rather than replacing their product SHA with
the new executor. Session pin tokens are temporary leases; do not treat a
released session token as a durable checkpoint authority.

Audit/digest/acceptance receipts bind the saved manifest hash and database
identity, complete original authority, candidate artifact proof, their own
producer/runtime/harness, results and input preservation. Acceptance additionally
binds exact receipt artifact proofs. A producing artifact's own archive digest
cannot be embedded before upload; its consumer authenticates that external
proof and records it. Never create a self-referential manifest hash.

Use the existing `checkpoint_artifacts` full transport. Authenticate the
successful **producing job**, even if a later consumer made its run fail. Do not
relax that rule to accept failed upload jobs. The first save reuses existing
`download_inputs` and `validate_inputs` for all original publication proofs.
Subsequent stages carry the exact original checkpoint and authenticated chain;
they do not redownload the original 30 GB database merely to re-prove lineage.
Their configuration still pins its original file/receipt/archive hashes.

Every consumer gets an explicit expected artifact ID/run/workflow/job/archive
hash/size and producing harness/runtime, pinned after inspection. No latest-run,
latest-branch or artifact-name-only selection. JSON and declared file sizes must
be bounded before loading; use a 16 MiB ceiling for each metadata file and the
existing database cap `38191218688` bytes.

## Failure, retry and launch behavior

Failures before successful save-bundle upload repeat only save from its retained
predecessor. A failed audit repeats audit; a failed digest repeats digest. A
successful sibling receipt remains reusable for the identical candidate. A
failed acceptance or restore repeats only that stage. Never repeat a successful
save, preparation, conversion or predecessor merely to advance another stage.
An audit or digest mismatch blocks advancement; preserving the candidate is not
permission to ignore the mismatch or trust its data.

Commands produce mandatory stage output first and optional diagnostics second.
Diagnostic stdout/summary failure cannot suppress a durable result. Upload
failure still prevents successful producer authentication. Consumers reject
partially published local directories and interrupted manifests.

Use stage/year-specific output names and one shared mature-continuation
concurrency group. Keep same-SHA/rerun guards and inspect active/pending runs
across SHAs before every launch. Operator source publication is inert; one
separate, expected-ref launch commit pins the reviewed source and inputs.
Do not discover push runs with the PR-filtered commit-workflow endpoint. Do not
change the disabled monitor or introduce an automatic mature-stage loop.

## Disk and time accounting

Let B be the verified input database size, C=38191218688 the maximum output
database size, Z the authenticated input ZIP size, M=8 GiB and S=64 MiB for
metadata/receipts. Check each phase against actual free bytes before entering it.

* Save before download: `max(B+Z, B+2*C)+M+S`. After extraction: `2*C+M+S`
  additional free bytes, reserving working output plus a full rollback journal
  or output-archive allowance. Closing and retaining the working DB must not
  create a third database copy. Recheck before publication/upload.
* Audit/digest/restore reader before download: `max(B+Z, 3*B)+M+S`. After
  extraction: `2*B+M+S` additional free bytes, reserving a disposable copy and a
  conservative full journal even though normal open only changes leases.
* Receipt-only acceptance: bounded metadata downloads plus M+S; no DB download.

These are conservative peak reservations, not claims of measured journal or
upload allocation. Artifact extraction/upload size bounds must be checked from
authenticated metadata before large transfers. Account for simultaneously
retained original small receipts. Do not delete retained inputs to make room.
Only the already-approved disposable-runner cache cleanup is allowed.

Emit separate timings for authentication/download, copy, open, simulation, save,
close, hash, audit, digest and receipt publication. The current log's save
interval includes compact diagnostics, so do not relabel it exact SQLite commit
time. Include addresses/RSS and disk headroom; do not infer work progress from
heartbeats. Keep upload time outside the 300-minute command with the 360-minute
job ceiling. Stage-level bounds are deliberate, not an ETA guarantee.

## Independent downloaded restore and final acceptance

After both actual years are verified, implement/launch the separate restore
stage against the exact retained year-1002 artifact. It must authenticate the
entire continuation/control/source chain and full ZIP/member/file bytes, copy
the DB to disposable space and open it normally on a fresh runner. Obtain
actual year 1002, complete snapshot values, full digest and counters equal to
the original bound control; verify retained file hashes remain unchanged.

Use independent `restore-values` and `restore-digest` jobs if needed to keep the
full report scan and full digest scan in separate 300-minute budgets. Each must
perform its own authenticated full download and fresh normal open; neither may
reuse continuation verification receipts as its observation. A small
`restore-verified` receipt requires both actual observations for exactly the
same candidate. No further simulation, save or backup is needed. A fixture or
metadata check never substitutes for this actual mature restore.

Final independent Astra review assesses the complete evidence, including the
explicit saved-state audit placement. Stage 0.5 and main remain unaccepted
until that review clears the actual mature gates.

## Required proof before a mature save launch

Use a real bounded world with populated treasuries, correct currency totals,
counted histories and shared nested identities. Exercise two saved years and
the exact original independent controls through normal conversion/publication,
then execute save/audit/digest/acceptance/restore in separate processes and fresh
CI runners with actual authenticated artifact transport. Include a known
populated late-world fixture where practical; increasing age alone does not
cover reporting shape.

Observe failing regressions first. Inject audit failure after save publication,
digest failure after successful audit, restart in a new process, interruptions
around close/hash/manifest/publication, diagnostic failure and failed upload.
Prove restart never calls Simulation or successful predecessor stages. Reject
wrong year/generation/runtime/control/source/producer, mixed candidate receipts,
altered DB or manifest with recomputed transport hashes, duplicate keys/members,
symlinks, incorrect byte counts and changed retained inputs. Compare every audit
field, actual digest, counters, values and shared identities with eager controls.

Run focused harness/transport/legacy compatibility gates and appropriate fresh
full validation for changed helper bytes. If the `ate_sim` subtree remains
exactly `76dee76973928dbce72860156feb32f2d7f02f86`, its approved runtime proof
38985095878 remains relevant; it never certifies new wrappers or reports.
Runtime edits require new applicable runtime/recovery gates. Obtain one
independent final implementation/launch review, exact published readback and a
fresh cross-SHA active-run inspection. Launch only the next required mature
stage once. The reporting fix's green tests alone do not authorize the old run.
