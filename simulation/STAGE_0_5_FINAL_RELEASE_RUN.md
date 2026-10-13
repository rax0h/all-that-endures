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

Launch receipt and results will be appended after GitHub assigns the run ID.
Final Stage0.5 release acceptance remains pending the exact-source jobs and
explicit performance-policy assessment. No merge or promotion is performed.
