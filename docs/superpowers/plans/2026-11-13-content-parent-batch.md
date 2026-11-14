# Content parent batch implementation plan

> Execute inline via superpowers:executing-plans; one independent whole-package review.

**Goal:** reduce redundant proof-tree reads in unchanged content predecessor validation.
**Architecture:** stream locator-sorted expected entries over one checked path union; stage existing bounded physical predecessors in a TEMP spool before source writes.
**Tech Stack:** Python/SQLite, qualified313.
**Spec:** docs/superpowers/specs/2026-11-13-content-parent-batch-design.md

## Constraints and review focus

Unchanged roots, codec, budgets, source-read guards, lease/recovery and pre-write
validation. No cache/certificate. Check compressed-prefix gaps, empty maps,
selected corrupt child/count/domain/path, late malformed/duplicate input,
callback failure and temp-table cleanup. Preserve event-conflict classification.

- [ ] RED read-work test plus independent membership/absence model.
- [ ] Implement focused verify_sorted API using existing _read checks; GREEN.
- [ ] Integrate content parent spool and prove no repeated point get there,
  rollback/recovery and native exact save/reopen; preflight previous file durations.
- [ ] Qualified bounded profile/work and raw A-B/B-A with pinned source fences;
  no CPU tests/probes during timing, retain completed compatible outputs.
- [ ] One independent whole-package review; close all findings in closure.md.
- [ ] Final bounded related checks and one hosted proof/full bundle.

Restart unit: one tiny fixture/test file or120s disposable small-input trial.
No expensive world constructor prerequisite. Preserve each completed XML/log/hash
receipt before continuing; never repeat unchanged green stages after a later
failure. Reserve15minutes publication. Reuse43501337447 for unchanged work; new
engine needs its own gate. No mature request changes.

Amendment after first whole-save comparison: TEMP-only timing negative, not
promoted. Add persistence_proof_parent_inputs.py with <=1MiB charged retained
rows (resident_bytes(row)+128 plus initial list); overflow uses identical TEMP
path. Current source/input row remains separately bounded, not a total-RSS claim.
Normal/forced-spill publication/fault tests before remeasurement; final full
related gate only if measured candidate retained. This is second hypothesis.

Final disposition: both prototypes archived after whole-save timings failed to
establish a credible win. Restore exact hosted-green95c61911; final buffered broad
and hosted gates intentionally not run. No unverified completion claim. All raw
source/state/runtime data and prototype reproduction files retained in report.md.
