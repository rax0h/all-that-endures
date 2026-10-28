# October 28 mature benchmark: recovered results and harness repair

Run [40712867500](https://github.com/rax0h/all-that-endures/actions/runs/40712867500)
failed after the 10,500-second internal operation lane budget expired during the
warm year. This is a performance failure, with incomplete correctness acceptance.
The source authentication succeeded. The fresh-process restore was skipped.

## Authenticated evidence

The 37,010-byte diagnostic ZIP, artifact `12840817860`, has SHA-256
`dc0cf89a8264501ac85a923bf4242a6546ca237dbff9ae8d4fa67f0f2cda8676`.
The downloaded bytes matched that digest before extraction. All ten original
members are retained unchanged under [run-40712867500](performance/run-40712867500/provenance.json).
The measured HEAD was `36a362d6bd51c27ba239f776792a692d4deeffa6`, runtime tree
`63d5ac487d0157a5ef521b4def8ee9ce94532e0c`.

The accepted source was seed 843000, year 1001, generation 126, database
29,922,463,744 bytes, SHA-256
`4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`.
Its post-run checksum matched. Year 1002 reached the save boundary at generation
127. There is no fresh-restore or canonical-digest acceptance for this run.

## Measured operations

| Operation | October 21 candidate | October 28 current | Observation |
|---|---:|---:|---|
| Open | 313.270 s | 454.541 s | Complete; 45.1% longer |
| First year | 2,446.796 s | 4,092.171 s | Complete; 67.2% longer |
| Save | 2,190.653 s | 3,219.980 s | Complete; 47.0% longer |
| Warm year | 2,158.448 s | 2,452.955 s | Interrupted; completed-year duration unknown |

This is a descriptive comparison of single samples, not a controlled regression
attribution. The code/runtime tree changed. Both report four CPUs, Python
3.12.15, SQLite 3.45.1, but different hosted runners/cache states and kernel
versions were used; physical CPU equivalence was not established.

The four recorded phase intervals sum to 10,219.648 seconds. The approximately
280.352-second difference from the shared budget is **unmeasured overhead**:
authentication/copy/hash plus inter-phase validation, diagnostics and receipt
work. Preparation alone cannot be recovered from this run. Post-timeout cleanup
and the final source hash also fall outside the internal alarm.

Against the repository's interactive targets, completed open is about 45.5 times
the 10-second target and save is about 1,610 times the 2-second target. The warm
year had already consumed 2,453 times its 1-second target when interrupted.

## Remaining work and attribution boundary

Save performed 1,651,746 payload reads / 8,601,872,232 bytes while writing
219,865 payloads / 67,919,926 bytes: approximately 127 read bytes per write byte.
Those save counts exactly match October 21. The first year read 5,421,599 payloads
versus 5,424,484 previously. Increased elapsed time therefore is not explained
by increased payload request counts alone. Save CPU time was 3,210.909 seconds
against 3,219.980 seconds wall time; this supports investigating CPU processing.
Read/check counters overlap and are not additive physical disk traffic.

No attributed spans were collected (`instrumentation: none`). These receipts do
not isolate codecs, proof checking, identity reconciliation or simulation rules
as the dominant CPU function. Do not delete validation or change simulation
semantics on the strength of these counters.

Next repair package: use the corrected harness for a separately bounded,
explicitly attributed profile, starting with open and then the dominant checked
read/identity path; retain incomplete spans on timeout. Compare exclusive spans
and repeated checked keys with logical mutation counts, reproduce the dominant
cost on a representative fixture, then implement a work-count regression and
the smallest invalidation-correct optimization. A full mature rerun, full suite,
default activation, merge and endurance remain outside this housekeeping step.

## Consolidated findings register

| Origin | Finding | Concrete disposition and evidence | State |
|---|---|---|---|
| Terminal handoff | Shared budget mixes preparation with operations | Current Stage 0.6 records source verification, copy and copy verification outside independent operation alarms; real-fixture timing regression | Closed locally |
| Terminal handoff | Smoke exercises Stage 0.5 instead of current workflow | Current Stage 0.6 tests execute their own measurement and fresh-restore commands on a tiny fixture | Closed locally |
| Terminal handoff | Missing restore receipt hides primary timeout | Current Stage 0.6 summary retains timing status, missing measurements and shell termination evidence explicitly | Closed locally |
| Terminal handoff | Fresh open and digest lack separate timing | Current Stage 0.6 separates fresh database open, state restoration and logical digest, with timeout regressions | Closed locally |
| Terminal handoff | Workflow edit can launch expensive benchmark | Current benchmark uses workflow_dispatch only; preservation workflow also manual after its first run | Closed |
| Independent review, Important | Preparation error can lose result.json during cleanup | Initial legacy repair passed missing-source RED/GREEN; superseded by current Stage 0.6 final-receipt handling; legacy harness left unchanged | Closed locally |
| Independent review, Important | Second retention failure discards verified first archive | Producer evidence fetched first, per-archive provenance, partial manifest, always upload only final ZIP/JSON names; partial-failure RED/GREEN regression | Closed locally |
| Independent review, Minor | Preparation lacks component times | Current Stage 0.6 source-verification/copy/copy-verification timers replace initial legacy subtimers | Closed locally |
| Independent review, Minor | Residual overhead mislabeled preparation | Corrected analysis above; original raw measurements unchanged | Closed |
| Retention deadline | Accepted source/acceptance expire Nov 1–2 | Dedicated bounded archive-only job requests 90-day retention; preserves exact original ZIPs and producer evidence | Hosted execution pending |

## Reconciliation with concurrent source work

Source branch advanced to `e3358b5c5b92e621497060c31b1e85972a5f0511`
while the repair candidate was being prepared. That commit contains the reviewed
canonical Stage 0.6 harness. Retain it and its single manual measurement workflow;
remove the overlapping changes to the Stage 0.5 helper and old launcher smoke.
This prevents breaking the current verifier's intentional use of its legacy
helper under an outer alarm. Rename the archive-only workflow outside the
`stage-0-6-*` measurement namespace. Do not launch it again during reconciliation.

The first candidate passed 36 focused tests plus its measurement/restore/gate
smoke. That independent review found four issues, all addressed before initial
publication. Reconciliation is verified against the canonical Stage 0.6 tests,
including actual measurement and verification shell commands. The local clone
needed the full green-ancestor history for that source-fence test; the first
reconciliation run failed that fence, not a simulation assertion. After fetching full history and committing the clean candidate, all **45 focused
tests passed in 23.82 seconds**, including the exact current workflow shell smoke.
Launch fingerprints, unchanged runtime tree, YAML and diff checks also passed.
No simulation runtime files were changed. The existing 4,391-test green baseline remains prior
evidence, not validation of this patch.

The archive-only preservation run is
[40758464881](https://github.com/rax0h/all-that-endures/actions/runs/40758464881),
launched at initial candidate `5cfe4c73f76bed9f3adfbab337aa116956ef70a6`.
It uses that candidate's self-contained focused checks and original-archive
retention code; reconciliation does not cancel or restart it. Hosted completion
and resulting artifact expiry remain unverified until the run finishes.

## Retention contract

Original source archive `12129336378` expires November 1 at 1:26 a.m. Central;
acceptance archive `12165934374` expires November 2 at 12:04 a.m. Central.
The preservation job authenticates original workflow, commit, producer and
archive hashes, then uploads original ZIPs plus original producer evidence with
90-day retention. It does not extract or simulate the world. A partial package
is explicitly marked partial; killed partial downloads are excluded from upload.

The new artifact is a transport mirror, not a newly accepted simulation state.
On recovery, authenticate the mirror producer/run and its manifest, verify each
nested ZIP against the original pinned archive size/hash, then extract through
the existing strict member validation and recheck the saved/acceptance binding.
Do not replace original ArtifactRef producer identities with the mirror's ID.
The current benchmark still uses original live inputs; selecting the verified
mirror is an explicit next-launch preparation step once its hosted receipt exists.
