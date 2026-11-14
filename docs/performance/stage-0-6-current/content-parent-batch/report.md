# Content-parent path union verification

Preceding annual-lifetime engine457a619f/runtime95c61911 is verified GREEN in
43501337447:5115passed plus2subtests (XML5117), proof34XMLs1960overlapping tests
plus scaling. Downloaded artifact/source/XML/hash receipts are retained in
../rank-ecology-lifetime/hosted-43501337447/. This closes W12's hosted gate.

## Resulting behavior

Content-parent validation checks the same bounded physical predecessor rows and
same accepted version/event roots before any source mutation. It now stages
expected commitments in a TEMP SQLite spool sorted by existing domain locator,
then streams each root's selected path union once. Every selected node uses the
unchanged ProofMap._read (address/domain/hash/canonical/count/prefix checks).
Missing branches authenticate absence. Strict input locator order rejects
malformed, duplicate/colliding and out-of-order entries. Late callback/input
failures propagate; TEMP cursors/table are removed before source writes or on
failure. Expected version mismatch remains integrity failure; an existing event
append remains conflict. Corrupt proof nodes remain integrity failures.

New verifier is read-only and stateless: one current member plus bounded radix
path/fanout; no cache/certificate survives. No root/format, gameplay, identity,
source-byte bound, publisher/recovery/lease or physical successor check changes.
Public point gets remain unchanged. Unselected descendant bodies and nonempty
root bodies on zero-row requests are not promised, matching selected-point
proof semantics. Hash collision resistance remains the existing assumption.

## RED, work and state evidence

- red.log/xml: missing verifier before implementation; integration-red proves
  old content guard repeats point proofs. Both are preserved RED evidence.
- focused.log/xml: new and original content-publication94tests pass4.72s.
- faults.log/xml: max64-depth65reads plus persisted failures at both parent
  verifiers roll back, clean TEMP state, resolve and fresh-token retry;3pass1.43s.
- Final related battery379tests/12files passes, including new30cases and native
  proof-open/mixed/composed World saves. Engine/test/XML/log hashes verified.
- Instrumented actual saved-world guard:1129physical predecessor checks in both
  engines; point gets1129→0 and checked proof-node reads5310→2043 (61.5%lower).
  Source checks are retained. Saved year2/gen1 and fresh-process year3 state match
  exactly on the original authenticated small input. See work-comparison.json.

measure_parent.py wraps only the actual guard with cProfile and calls the
unchanged exact-state driver. It intentionally modifies the child function
binding for instrumentation, always delegating to the production function;
filesystem/import/state fences remain checked. These runs overlapped related
checks and are work evidence, not latency acceptance. Printed phase times include
instrumentation and contention. work-setup-error.log records a helper path setup
failure before any input/profile opened; corrected absolute-path execution passes.
The complete qualified313 runtime fingerprint was rechecked this turn.

## Review and restart boundaries

One independent whole-package review, no actionable Critical/Important/Minor:
independent-review/review.md and source SHA fence.256sparse models5120memberships,
64depth, late malformed/duplicate/callback checks, persisted failures on both
parents and recovery pass. Initial reviewer assumptions that pending-attempt rows
roll back or same-token immediate retry is allowed were corrected against the
unchanged recovery contract. Raw diagnostics remain preserved, not open findings.

Selected-related-membership scope, no mature/universal-runtime claim and no raw
speed claim in advance are accepted review limits. Final timed data below is the
owner's bounded observation, not an independent-review performance endorsement.

Before local execution, prior hosted file durations were inspected. The original
180s/file policy was rejected before starting because a known module took179.67s;
use300s/file900s/invocation and reserve full310s before starting another file.
Each completed file has independent XML/log/source digests for compatible reuse.
The known composed-world module passed223.46s within that chosen budget. No
unchanged expensive generated-world constructor prerequisite is repeated locally.

Raw trials use the unchanged reviewed runner and thin engine/root pin adapter:
A-B/B-A,120s/trial, complete Python inventory/blob/input/module/state fences,
disposable copies, bounded process-group cleanup. No CPU tests/reviewer probes
run during raw timing. Each completed trial is retained; failures do not authorize
rerunning a completed compatible prefix. Mature/main/default/endurance remain
outside scope. One bundled proof/full engine gate follows local closure.

## raw-pairs observations

| seconds | Pair1 baseline | Pair1 candidate | Pair2 baseline | Pair2 candidate |
|---|---:|---:|---:|---:|
| open | 2.070 | 2.361 | 2.088 | 1.818 |
| first_step | 10.695 | 9.984 | 10.932 | 10.503 |
| save | 10.164 | 10.645 | 8.851 | 10.116 |
| warm_step | 10.274 | 9.473 | 9.847 | 7.197 |
| fresh_verify | 18.952 | 20.284 | 25.505 | 31.542 |

## buffered-raw-pairs observations

| seconds | Pair1 baseline | Pair1 candidate | Pair2 baseline | Pair2 candidate |
|---|---:|---:|---:|---:|
| open | 1.772 | 2.222 | 2.362 | 1.889 |
| first_step | 9.288 | 10.727 | 8.617 | 9.353 |
| save | 7.379 | 7.991 | 11.604 | 7.378 |
| warm_step | 8.546 | 8.589 | 9.854 | 7.577 |
| fresh_verify | 26.362 | 25.274 | 28.064 | 19.117 |

## Final disposition: not promoted

The TEMP-only variant reduced actual parent proof-node work5310→2043 while
keeping1129physical predecessor checks; full saves were slower in both raw pairs.
The bounded-memory amendment uses <=1MiB charged retained inputs (resident_bytes
per row plus128bytes for list/sort overhead), with the checked TEMP overflow path.
Current source/input rows retain their separate existing bounds; no total-RSS
claim. Its34focused normal/forced-spill cases and amended independent review pass,
including memory accounting, collision/partial-spill cleanup and persisted retry.
Documentation Minor W13e was fixed and independently verified closed.

The revised full-save pair is mixed:7.379→7.991s and11.604→7.378s. Baseline itself
varies substantially; causality of whole-save differences is not established.
Lower-level node work alone is insufficient acceptance for this speed assignment.
Neither prototype is promoted. All source variants and regressions remain in
prototype/; qualified fingerprints, complete trial data and original failures
are preserved. No claimed overall/mature improvement or stage completion.

Restore the exact preceding green active engine/runtime95c61911 and its original
test/workflow state. This is an evidence/documentation publication, so no new
full/proof CI cycle is triggered. Prior hosted43501337447 remains the accepted
engine gate. The379-related pass applies to the TEMP-only prototype;34focused
passes plus amended review apply to the memory prototype. Do not relabel those
as the final buffered full-related gate: that gate was intentionally not spent
after the timing decision.

Next investigation should attribute the whole save's phases, including preparation
and acknowledgement, with same-engine controls before another implementation.
The existing profile shows substantial work outside this guard. Do not assume
TEMP was the cause, pursue a third patch blindly, or repeat mature construction.
