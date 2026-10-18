# GC cost measurement correction: independent final review

One fresh-context Astra review inspected local commit
`08e70912a816e24a0e452f8281e797ee544b45ea`, tree
`ea611ec99d6b11bd6c826f5f9e542de213ee1cc0`, against
`13f3c62642b3ec4bbc06578b9db5e731886849a0`.
It found no blocking source findings and cleared only one corrected proof launch.

The reviewer confirmed that weak alias collection changes the dependency-lease
roster and that the supplied namespace trace isolates the measured variation to
those rows. The correction collects fixture garbage before counter reset and
holds automatic cycle collection stable during the measured saves. Reference
count cleanup and real dependency accounting remain active. Exact metric
equality and all three archive/registry traversal traps remain unchanged.
GC enabled state and thresholds are restored, including save failure paths.

The reviewer independently inspected the15-test module result and both GC
schedules' identical155/31/1185 costs at both history sizes. The later expanded
gate passed168 tests in295.62s, zero failures/errors/skips, three existing
warnings. That result was sent to the same reviewer; no second review was
requested. The reviewer also verified all17 proof jobs remain, full-suite
success remains a proof-summary dependency, retained-audit authentication is
mandatory, runtime subtree76dee769... is unchanged and diff checks pass.

## Executor conditions and scope

The review declined to certify hosted state/provenance, final remote readback,
current lease, or a published source object unavailable in local Git. The
executor separately verified all five outgoing files byte/blob exact, the
exact published tree and commit parent, all11 unchanged production fingerprints,
all five active statuses and three cross-SHA branch histories, and expected
proof/mature branch heads. No relevant active run or prior run on the new
source existed. One non-force leased update registered exactly one push
attempt1 for the proof workflow.

Published source `4fecd93fdcc5012a404afc07ce166cb7ff422f59` has the exact reviewed tree.
[Proof39177774744](https://github.com/rax0h/all-that-endures/actions/runs/39177774744) was created
October18,2026 at23:44:30UTC. Its registration status was queued; no later hosted
result is asserted. All17 jobs and the actual fresh full suite remain required.
The failed full-suite archive from39167485117 is forensic evidence only.

The separate saved mature generation12129336378 and successful actual
audit12148235361 remain unchanged. This review authorizes no mature progression,
monitoring, rerun, main merge or Stage0.5 acceptance. The next mature action,
after authenticating the complete fresh proof, is separately reviewed digest1001.
No successful simulation, save or mature audit was repeated.
