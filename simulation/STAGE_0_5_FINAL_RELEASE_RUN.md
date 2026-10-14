# Final-source validation and authorized long-horizon run

The owner explicitly requested starting final validation and the big test on
2026-10-13. This supersedes earlier no-endurance launch instructions for this
scoped workflow. Main/PR14 promotion, checkpoint defaults, rank gameplay and
Stage1 remain outside this action.

## Final source preparation

Base: f683176563cc2e7e4bc633769419f5a79fdd35ea (evidence head for the green
owner-witness runtime). The final source has one additional runtime repair:
explicit registry diagnostics snapshot metadata while enumerating weak bindings
and owner groups. A real complete-format harness test exposed cyclic collection
mutating the old iteration; a deterministic regression reproduced RuntimeError
before the fix. No live objects gain strong registry roots; ordinary simulation,
arithmetic, RNG and persistence authorities are unchanged. Whole-registry
diagnostics retain their existing explicit inventory cost.

The existing long P5 harness now explicitly selects native graph conversion and
the complete-format copy publisher, checks format6, streams file hashes and
records phase progress. It frees the bootstrap World before conversion. Explicit
initialization selects founders or mature for both eager control and bootstrap;
the legacy default remains founders. Review caught that canonical defaults mature
while the old harness used founders. A regression reproduced missing explicit
selection and now compares mature control against independently generated mature
and founders digests.

Local evidence: 31 identity/cache tests passed0.61s; real complete-format0->1->2
simulation/save/reopen/backup/independent equality test passed57.50s. The new
source receives a fresh GitHub full suite; the old 2,431+2 result is not
misattributed to it.

## Five workflow jobs

1. Recovery gate: focused regressions plus complete-format founders seed843000
   3+4+3 continuation, checkpoint/detach/reopen/relocated restore, known year10 digest.
2. Full simulation test suite on exact pinned candidate (120-minute bound).
3. Canonical mature seed843000, 1,000 years, chronology/progression archive audit.
   120 seconds remains a reported optimization goal; correctness failures are fatal.
4. After all three pass: independent mature control through1002; fresh mature
   bootstrap1000; cold conversion and complete upgrade; continue1001, save/audit,
   reopen; continue1002, save/audit/reopen; backup and independent restore digest
   and counters. Bootstrap digest must equal the canonical year1000 result.
   Process bound350min, job360min. This is a late-fixture continuation, not1000
   sequential years running under lazy persistence.
5. Download the late SQLite artifact on a fresh runner, verify its hash, open a
   disposable copy, check exact year/generation/format/digest/counters and verify
   the retained original remains byte-identical. Bound90min.

All jobs check out an immutable candidate SHA. The workflow commit is separately
recorded. stdout/stderr logs and partial progress upload even on failure;
successful short restore, canonical archive and late restore upload separately.
Artifacts retain14days; checksums, source, rules, mode and restore command are in
receipts. A timeout/OOM/disk exhaustion is incomplete evidence, never a pass.
Hosted late/restore runners remove only unused preinstalled toolchains to reserve
space for disposable database copies; no existing user checkpoint is touched.

## Architecture decision and remaining gates

The fresh-context reviewer inspected capability selection/private copy, single
registry/publication/recovery authority, owner-cache epoch/rollback bounds,
schema/import inventory and scale/maintenance evidence. It accepted architecture
for the stated capability6 scope with disclosed C/D/U/input costs and the exact
pressure arithmetic O(H) cold-miss exception. This does not establish universal
constant work, satisfactory long-horizon performance or production acceptance.

The initialization mismatch was its material launch finding and was repaired.
Minor deferred: reusing a complete harness workdir encounters an existing
complete destination after setup; every workflow run uses a fresh workdir and
existing destinations remain protected. No automatic reruns are configured.

## Launch receipt

- [Run38447779260](https://github.com/rax0h/all-that-endures/actions/runs/38447779260): failed in reopened save; downstream jobs skipped.
- Exact candidate: `bdde5bc20c40583045fcb3562698847db460b080`.
- Candidate tree: `9a3857db96d01de8c7aa8ed091702c2e964b5dc0`.
- Workflow-only commit: `53ec46fd9f95098ec202cddcc043656197bef8c4`.
- Latest local focused check including initialization regression:32 passed,
  one previously verified long integration case deselected,1.01seconds.
- Initialization regression observed RED before its repair; whole exact-source
  suite and all recovery/horizon evidence are pending in this run.

Final Stage0.5 release acceptance remains pending the exact-source jobs and
explicit performance-policy assessment. No merge or promotion is performed.

## Dependency capture repair

The initial recovery gate passed33 focused tests (81.99s), then failed at the
year10 reopened save: mandatory dependency authority absent for backing8031.
No full suite, millennium or late-fixture job ran. Failed job115470568633 and
artifact11839890191 retain the traceback and focused evidence.

A deterministic small regression reproduced the same error: prepare_delta first
captured a target containing an unpublished backing; weak collection then removed
its live alias and _new marker; the subsequent checked read reclassified the
captured backing as persisted and incorrectly required an existing row.

The repair copies unpublished IDs before capturing the target roster and uses
that captured status throughout preparation. This is temporary save metadata,
not a retained live-object root or a second authority. Existing persisted rows
remain mandatory; validation is not relaxed. Tests cover commit followed by
lease release, abort without leaked unpublished metadata, and corruption after
collection of an already persisted alias. Local gate:45 passed0.96s; original
unpublished race observed RED before the repair. The complete3+4+3 rerun must
confirm that this resolves the observed integrated failure on the new source.

The revised workflow adds these dependency tests to the first gate and retains
disposable recovery databases on failure for further diagnosis. All original
exact-source, correctness and long-run gates remain in force. A new run will
follow because rerunning the old pinned workflow would test the old source.

Repair launch: [run38459262962](https://github.com/rax0h/all-that-endures/actions/runs/38459262962)
is in progress. Exact candidate `2bc3c85389760ff12578857f7d2a849bc5cf9201`, tree
`fd232ce57b7e2332c91446d0485fab9a1b2d22e4`; workflow-only commit
`fb9505a0349e083882672e2de9e8e7735b68fd77`. Recovery, complete suite and
long-horizon conclusions remain pending. No successful job from the failed
initial run is being misattributed to this repaired source.

## Hosted runner interruptions and recoverable validation

Run38459262962 attempts1 and2 both ended with runner shutdown and exit143,
without a Python traceback or correctness assertion. Attempt1 job115549208763
ran21:28:20–23:34:44 UTC; attempt2 job115598439858 ran23:40:05–01:10:00 UTC.
Both last reported complete_upgrade_started. Neither reached the350-minute
process timeout. The root cause of runner termination is unknown; resource
exhaustion is not proved or excluded. Neither attempt uploaded late evidence or
an intermediate database because runner shutdown skipped even always() uploads.
Recovery, full-suite and canonical millennium gates remain successful on runtime
candidate2bc3c85389760ff12578857f7d2a849bc5cf9201.

The revised validation harness stops after cold publication, native lazy
conversion and complete upgrade, each in a separate fresh-runner job. Each
successful job uploads a checksum-bound database and JSON receipt carrying the
independent control, bootstrap digest, exact configuration and prior checks.
Resume rejects wrong source/configuration, stage or database checksum before
opening a database. Fresh runs reject occupied workdirs. Partial stages explicitly
return passed:false; only continuation, audit, reopen and restore produce a pass.
No incomplete/private conversion database is accepted as a checkpoint.

The workflow retains runtime source2bc3c85389760ff12578857f7d2a849bc5cf9201 as
the product identity and records the new harness source separately. It requires
an identical simulation/ate_sim Git tree43c2976e97474127ec860bcb6382988660ddadb3
and verifies the prior three successful jobs before reusing those gates. Only
the validation harness, its tests and documentation change; simulation behavior,
persistence implementation and acceptance checks do not change.

Runner diagnostics stream memory, disk and largest-process usage every minute.
The harness CLI emits stack samples every five minutes and logs existing copy
phase seams; those samples are diagnostic, not a timeout failure. Each stage
starts a new process, releasing all allocator state from earlier conversions.
This bounds work lost to the active stage and may reduce carried-over memory;
it does not prove or claim to fix the unexplained infrastructure shutdown.
A further upgrade failure can be investigated/retried from the retained native
lazy database without repeating the independent control, bootstrap and cold
conversion. Final acceptance remains pending.

Local staged-harness verification:3 tests passed in110.13seconds, including the
original complete0->1->2 lane, canonical mature initialization, and an artifact
handoff lane copying only the checkpoint receipt plus current-stage database.
The staged test initially failed on the missing stop_after API, then passed after
implementation. Workflow shell scripts and embedded Python parse successfully;
git diff --check passes. Independent reviewer found no launch blocker. Resume
compatibility is scoped to this workflow's immutable harness commit; do not reuse
these receipts across changed harnesses without a compatibility check.

Staged launch: [run38500678444](https://github.com/rax0h/all-that-endures/actions/runs/38500678444).
Harness commit:b546cf56dabe1cf2887cab0b770c2674861c83bc; harness tree:
10abba3022abc5c70ff800e1eb83b8d7d5c98836. Workflow commit:
8a6744c34c1c42ea32411fbcb723a42dcf014387. Runtime product remains
2bc3c85389760ff12578857f7d2a849bc5cf9201. New staged execution is pending;
no additional full suite or canonical millennium rerun was launched.

## Retained cold checkpoint and native crash during lazy conversion

Run38500678444: harness-gate and late-cold passed. Cold checkpoint artifact
11866834418 (246,500,655-byte ZIP; SHA256
1f9479ecf0b1f79fb1f38a99ce5999370287b5997e4b27767c4ccdd4c0693a37)
retains the verified control/bootstrap and cold database until2026-10-28.
Lazy job115661045355 verified that checkpoint and began conversion, then exited139
at03:40:53 UTC while the fifth scheduled faulthandler dump was printing a filename.
Unlike the earlier exit143 shutdowns, the runner survived and uploaded diagnostics
artifact11867929214 (ZIP SHA256
ccc127a798543d314301a5a9c4f8ae07c191902a3ba97154af204ae9dd5c788e).
The last sample showed Python RSS2,647,736KiB, available memory12,442MiB, zero swap
use and91GiB available disk. These samples do not indicate memory/disk exhaustion.

The newly added watchdog stack traversal is the leading hypothesis, not a proved
native root cause: the log ends within its dump and no native core backtrace was
retained. CPython reports https://github.com/python/cpython/issues/116008 and
https://github.com/python/cpython/issues/131580 document crashes during concurrent
faulthandler stack walking; they support the hypothesis but do not establish the
exact Python3.12.15 crash here. This does not explain the older exit143 failures.

The controlled retry removes only dump_traceback_later from CLI diagnostics;
fatal-crash reporting, external memory/disk monitoring and copy-phase logs remain.
The simulation, conversion, checkpoint schema and resume acceptance code are
byte-identical to the staged candidate. Cross-workflow reuse of its cold receipt
is therefore explicitly compatible. The new workflow verifies the previous cold
job/source and receipt origin, downloads that retained artifact, and begins at
lazy conversion. It does not repeat the completed cold stage or prior runtime
gates. Further native failures request kernel/core metadata in the diagnostics.

Local real CLI smoke: seed843000/bootstrap0/milestone1 cold checkpoint followed
by a separate process resuming to the lazy checkpoint both exited0 after removal;
receipts report stages cold/lazy and passed:false as required. Revised shell and
embedded Python syntax checks pass. Full long-fixture outcome remains pending.
