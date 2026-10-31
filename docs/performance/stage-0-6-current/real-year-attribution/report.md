# Complete small-world year: current runtime measurement

Runtime is exactly the green a21954a tree
`ec913495f7cd83dbef6b9eebe6c2a6dd9efe0bf7`; no simulation code changed.
Both hosted jobs of41181438097 were independently confirmed successful.
Probe source/hash and all observations are recorded in receipt.json. The exact
measured driver snapshot is measured-driver.py; its bytes match the receipt.
The reusable entrypoint is .github/tests/run_proof_real_year_probe.py.

Fixture: seed843000,8x6,one settlement,mature initialization, eager years1–2,
then a full native proof-backed year3. Independent eager year3 digest is the
acceptance reference. This is a small real simulation, not the retained
year1001 checkpoint. Local hardware/cache are uncontrolled.

| Raw operation | Seconds |
|---|---:|
| Open plus full proof admission | 8.697 |
| Complete simulation year | 1.798 |
| Save | 20.824 |
| Fresh interpreter restore plus digest verification | 10.319 |

Construction/eager control took33.715s and copying0.007s; both are separate
from save. Fresh restore includes verification, not an isolated restore-only
measurement. CPU attribution distinguishes parent and child processes; RSS
fields are explicitly process-lifetime high-water observations. Storage bytes
are retained separately. Both copied runs restored the exact eager digest and
the accepted input hash stayed unchanged.

The separate diagnostic pass is instrumented: its59.299s save must not replace
the20.824s raw result. It observed two full World audits (24.366s and24.831s
under profiling). Those spans are inclusive portions of the diagnostic save,
not extra durations to add to raw timing.

## Demonstrated blocker

The frozen producer supplies1202 version rows,17 ordinary rows and67 identity
changes. The manifest adds one control record; there are no event segments.
615 version rows are dependency leases,18 newly created. Both value and
insertion validators return at their initial512-row budget gates (lines66 and46
in this runtime), before detailed transition classification.

Even removing all615 lease rows would leave587 version rows plus ordinary
changes. Raising limits alone would still leave existing sequence/ownership
transitions outside current semantic proof coverage. The diagnostic shape
records2 existing sequence descriptor changes, with new occurrence/member and
directory rows; new sequence construction alone would not address this case.

This explains why fast isolated/mixed creation receipts have not improved the
complete-year path. The supported proofs are useful but the whole-year batch
still never reaches them.

## Next implementation group

Implement authenticated whole-year delta composition against this captured
workload: account for dependency-lease work, certify existing sequence append
and associated owner/child/scope facts, then compose remaining ownership changes
under bounded input/source budgets. Keep the same central transaction/catalog.
Do not discard required leases or raise caps as a substitute for proof coverage.
Measure this same complete-year scenario again before another component-only
performance claim. Retain eager-control and fresh-process continuation checks.

Mature opening10s, save2s and warm year1s acceptance remain unestablished. No
new mature run, default activation, merge, endurance or full simulation CI was
launched for this harness-only group. Four failure-evidence tests pass; both
Minor review findings are closed in review.md. A superseded instrumented pass
is not used as completed evidence. Failed/interrupted CLI runs leave phase
receipts; callers must retain timeout/termination status when using a wrapper.
