# November10 proof-genesis timeout repair

Hosted42720921191 at85f87e1 passed its full suite(4981tests,2subtests,
8958.66s) and proof-map job, including all13 unchanged real-year phases. Its
mature constructor timed out after12600s, still in the first checked catalog
validation. No interactive phase ran; source bytes were unchanged. See the
consolidated findings in ../closure.md and authenticated raw hosted evidence.

The repair keeps three full generic audits of distinct source states, all final
World/source/proof correspondence, both canonical World digests and a fresh
physical/FK audit after proof writes. It removes repeated operational checks
only under exact transaction/source custody. The default copy and ordinary
reader paths keep their audits. There is no construction-budget increase.

## Complete small-constructor comparison

The input is a real generated year2 complete-format6 snapshot:18,501,632bytes,
SHA256935252de0242f44a3700a0aad7c131fa30a5754eb538b21d7ba6afe27e1d8930.
Each run owns a separate byte-identical source copy. The original and restored
World canonical digest is4ce193c52a5ba3de03293f90d24075e44e28f20e8db3b66a7494bad84b2c4e8a.
All accepted samples keep source bytes unchanged and independently open the
resulting proof World to check its digest. Baseline code is85f87e1; candidate
code is fenced per-file in its receipt. Both use qualified313.5/SQLite3.46.1.

| Instrumented operation | Baseline | Final repair |
|---|---:|---:|
| Full generic source audits |11|3|
| SQL execute calls |1,386,734|515,195|
| Save-head queries |119,024|1,616|
| Physical integrity checks |11|5|

Counts are baseline-counted2.json versus candidate-counted3.json. Instrumented
wall times are separate observations; use the raw paired receipts for raw
construction timing. One sequential raw pair measured28.279s baseline and15.045s
repair (46.8%lower). This is a single warm/uncontrolled-cache small-world
observation; it predicts neither mature construction nor interactive latency. Candidate-counted2 predates the closed digest optimization;
its code fence and original result are retained. Earlier constructor-baseline-raw
and constructor-repaired-raw receipts retain their own intermediate source
fences and are not the final paired comparison. bounded_constructor_probe.py
is a preparatory whole-constructor probe, with no completed result claimed here. The first shared-input probes
failed their source-byte comparison and are invalid samples; their error logs
remain. They are not used in comparisons.

## Bounded catalog component

catalog-scope-bounds.json measures checked catalog validation on1000/10000
history elements with disk inventories and an owned frozen source. Operational
checks remain1at both sizes; cache sizes are22/93entries and23,431/96,630bytes,
within the fixed256entry/256KiB budget. Traced peaks are1,523,795/246,947bytes;
the first includes import initialization. This is a component retention probe,
not total live World/conversion memory or mature timing acceptance. Temporary
disk inventories grow with rows; canonical sorting/live identity remain separate.

## Validation boundaries

Local runtime qualification is an unchanged13phase baseline run before repairs,
plus the full runtime fingerprint and preserved earlier312 observations. The
repair passed the unchanged13phase driver on cleanbec836a/runtime94267bb0,
77final transfer/World tests and62independent existing regressions. See
local-validation-summary.json for exact overlapping and interrupted checks.
The overbroad local cold archive400segment benchmark was intentionally stopped
after320completed cases;27remaining targeted cases passed separately. That
unchanged backend is outside this repair and remains in the full hosted suite.
Do not represent that interrupted command as a complete348test pass. Historical negative results are retained; no engine-only
cause or universal version compatibility claim is made.

Stage0.6 remains open until the mature constructor and actual open/save/warm
simulation targets(10s/2s/1s) are measured, with an exact fresh-process year1002
digest and final architecture acceptance. Small-world reductions do not prove
that the mature constructor fits its existing budget or meets those targets.
