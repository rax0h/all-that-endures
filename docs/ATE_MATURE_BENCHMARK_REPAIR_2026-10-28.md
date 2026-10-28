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
| Terminal handoff | Shared budget mixes preparation with operations | Separate preparation budget; auth/copy/hash subtimers; optional independent phase caps; real-fixture timing regression | Closed locally |
| Terminal handoff | Smoke exercises Stage 0.5 instead of current workflow | Explicit workflow selector; actual Stage 0.6 measure, fresh restore and final gate executed on tiny fixture | Closed locally |
| Terminal handoff | Missing restore receipt hides primary timeout | Gate checks timing status first; timeout-before-missing-file regression | Closed locally |
| Terminal handoff | Fresh open and digest lack separate timing | Separate authenticated-input, fresh-open, digest, close and final-hash phases; internal restore timeout receipt regression | Closed locally |
| Terminal handoff | Workflow edit can launch expensive benchmark | Only a deliberate launch-record change triggers it; no launch record created | Closed |
| Independent review, Important | Preparation error can lose result.json during cleanup | Missing-source RED/GREEN regression; postcheck failure captured separately | Closed locally |
| Independent review, Important | Second retention failure discards verified first archive | Producer evidence fetched first, per-archive provenance, partial manifest, always upload only final ZIP/JSON names; partial-failure RED/GREEN regression | Closed locally |
| Independent review, Minor | Preparation lacks component times | Source-authentication/copy/copy-hash subtimers; RED/GREEN component regression | Closed locally |
| Independent review, Minor | Residual overhead mislabeled preparation | Corrected analysis above; original raw measurements unchanged | Closed |
| Retention deadline | Accepted source/acceptance expire Nov 1–2 | Dedicated bounded archive-only job requests 90-day retention; preserves exact original ZIPs and producer evidence | Hosted execution pending |

Validation: 36 focused tests passed locally, plus the exact current-workflow
measurement/restore/gate smoke. Independent whole-package review completed;
all four findings were addressed. No simulation runtime files were changed.
The existing 4,391-test green baseline remains prior evidence, not validation
of this patch. The hosted preservation job repeats focused validation and smoke.

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
