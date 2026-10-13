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
