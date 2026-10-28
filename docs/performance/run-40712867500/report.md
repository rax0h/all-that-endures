# Current mature-world measurement — October 28

Run: https://github.com/rax0h/all-that-endures/actions/runs/40712867500

Candidate: `36a362d6bd51c27ba239f776792a692d4deeffa6`; runtime tree `63d5ac487d0157a5ef521b4def8ee9ce94532e0c`. Python 3.12.15, SQLite 3.45.1, four reported CPUs. Artifact 12840817860 was downloaded and its ZIP SHA256 checked against GitHub metadata; file hashes are in evidence.json. Original receipts are retained unchanged.

The run failed its acceptance gate after the shared 10,500-second measurement budget expired during the warm year. This is a censored performance observation, not a failed full correctness suite. Authentication succeeded and the accepted input database remained unchanged. Save reached year 1002/generation 127, but fresh-process verification was skipped; this run does not establish accepted restoration of that save.

| Operation | October 21 seconds | Current seconds | Repository working target | Result |
|---|---:|---:|---:|---|
| Open including restoration | 313.270 | 454.541 | 10 seconds | Fail |
| First simulation year | 2446.796 | 4092.171 | No distinct target | Completed; no target verdict |
| Incremental save | 2190.653 | 3219.980 | 2 seconds | Fail |
| Warm simulation year | 2158.448 | >=2452.955, incomplete | 1 second | Fail; censored |
| Fresh restore | Not timed | Not reached | No distinct target | Unmeasured |

Targets come from `docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md`, section 2. The separate millennium-generation target is not measured here. Historical numbers come from run 39647739463's candidate receipt. Runner/cache conditions differ; the observed differences alone do not identify a code regression.

Opening and restoration cannot be separated retrospectively. The original timer also included authentication/copy work in its overall budget. The final warm-year duration is only its elapsed work before that shared budget expired; it is not an independently budgeted complete-year result. No separate verification-overhead timing or final database-size measurement was recorded.

## Attribution available now

- Open: 454.380 CPU seconds / 454.541 wall seconds; 628,525 payload reads, 2.304 GB read, 2.749 million metadata rows.
- First year: 4040.108 CPU / 4092.171 wall seconds; 5.422 million payload reads, 6.996 GB read, 24.926 million metadata rows, 11.123 million pin rows.
- Save: 3210.909 CPU / 3219.980 wall seconds; 1.652 million payload reads, 8.602 GB read, 67.920 MB written, 9.394 million metadata rows and 8.120 million pin rows. Payload verification counters separately report 8.675 GB checked; these counters must not be summed as physical disk traffic.
- Process peak RSS reached 2,458,542,080 bytes, approximately 2.29 GiB. This is cumulative process peak, not an isolated save allocation measurement. The source database is 29,922,463,744 bytes; output size and physical disk IO were not measured.

The phases are predominantly CPU time and incur substantial checked reads. Repeated historical authentication/reconciliation and cache churn are hypotheses requiring bounded attribution. Counters alone do not prove that unrelated ancient history was scanned, or identify the expensive function. Save is the largest completed persistence operation; the first simulation year is the largest completed operation overall.

## Reconciliation and next work

The remote run used an unchanged green runtime, but a different launcher from the locally prepared package. Preserve this receipt and reconcile into the existing workflow rather than launch a parallel benchmark. Exact-launcher smoke coverage, phase budgets, durable timeout evidence and separate restore timings are supplied by the prepared harness. Launches must now be explicit, not caused by housekeeping pushes.

Fixture retention remains an operational blocker: this run uploaded receipts, not the source database. Original source expiry is November 1, acceptance expiry November 2. The reconciled workflow retains authenticated input before future measurements, but no successful replacement-fixture upload is claimed yet. Complete that retention and bounded attribution before another full mature measurement. No full suite, benchmark retry, proof-default activation or endurance run is justified by the housekeeping commit alone.
