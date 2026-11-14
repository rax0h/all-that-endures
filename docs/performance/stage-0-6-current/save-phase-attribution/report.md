# Closed coordinator acknowledgement read scope

Active baseline95c61911 is hosted GREEN43501337447 (5115passed plus2subtests).
W13 parent-batch experiments remain archived and are not reintroduced here.

## Current-engine attribution

Fresh qualified313 current-profile/ wraps only the original preparation, commit
and acknowledgement methods with separate cProfile runs, delegating to them in
full through the unchanged exact-state driver. This intentionally changes child
method bindings for instrumentation; filesystem/import/runtime fences and saved/
fresh continuation checks pass. Instrumented phase timing is not raw latency.

Prepare57042SQL, commit98479SQL, acknowledgement102387SQL. Acknowledgement has
6993checked-head calls and7021pin checks, with coordinator validation its largest
individual component. The outer participant read_snapshot means its nested
catalog checked scopes cannot own the view and so cannot share their metadata.

## Change and authority boundaries

Only CoordinatorSaveParticipant.validate_publication's outer context changes to
existing checked_read_operation, budgeted at min(256KiB,catalog.byte_limit//6).
The context owns one closed read; existing metadata checks, per-frozen-row loops,
exact pin/root/schema/codec/epoch checks, source ownership and PublicationProof
lifecycle remain. No new persistent cache, certificate, format or direct accept
shortcut. Scope closes before cold confirmation/acceptance and gameplay. Borrowed
transactions do not gain eligible scope or reusable standalone proof. Writes and
rolled-back writes invalidate; corruption between validate/accept still rejects.

Real native32-person acknowledgement: original147checked-head validations;
candidate at most10, with identical32wealth values saved/reopened and no scope
retained on return. Original RED and GREEN receipts are retained.

Independent review found a resource-budget Minor: default outer256KiB could
retain2026bytes for a configured128byte catalog. Permanent regression RED,
then explicit min(256KiB,catalog.byte_limit//6) fixes it. Independent rerun:
allowance21/retained0 for the128budget. R1 is CLOSED in the single review report;
normal/borrowed/exception/corruption/rollback cases pass. No open findings.

## Actual work and raw comparison

phase-comparison.json: preparation and commit SQL counts unchanged. Acknowledgement
102387→88855SQL (-13.2%),17438→15519proof-node reads,6993→3550head checks. Same
saved year2/gen1 and fresh continued year3 digest. These work counts come from
instrumentation and are separate from raw elapsed observations.

Raw run_pair.py only supplies two committed engine pins/roots to the unchanged
reviewed runner. Full Python inventory/Git-blob bytes, original input hash,
loaded-module paths, same saved/continued state, qualified runtime and original
input preservation are checked. A-B/B-A sequential, no test/reviewer CPU probes.
120s/trial, bounded process cleanup; completed compatible trials retained.

| save seconds | Baseline | Candidate | Reduction |
|---|---:|---:|---:|
| Pair1 |4.268104|4.098666|4.0%|
| Pair2 |4.430619|4.210657|5.0%|

This is a modest same-input save observation on two ordered pairs, not a latency
distribution or overall/mature/interactive-readiness claim. First/warm/open/fresh
phases are reported in full below; no effect is attributed to unrelated code.

## Validation and scope

focused-final.xml:44passes, exact-source after R1. Reuse that completed focused
battery for the final related gate; do not rerun it merely to bundle it with
additional files. Additional related files have300s/file900s/invocation limits,
full310s reserve, independent XML/log/source-hash receipts and prior hosted-duration
preflight. No expensive generated-world constructor prefix is rebuilt locally.

One independent whole-package review and routine R1 closure in independent-review/.
Review is separate from performance/hosted acceptance claims. Mature/default/main/
endurance/universal-runtime claims are excluded. No unresolved Minor is deferred.
One proof/full hosted gate follows if the final related checks pass. First-playable
interpretation is a separate note and does not relax formal W3/U10 targets.

## Full raw phase observations

| seconds | Pair1 baseline | Pair1 candidate | Pair2 baseline | Pair2 candidate |
|---|---:|---:|---:|---:|
| open | 1.190 | 1.071 | 1.067 | 1.165 |
| first_step | 5.208 | 5.282 | 5.463 | 5.687 |
| save | 4.268 | 4.099 | 4.431 | 4.211 |
| warm_step | 4.446 | 4.443 | 4.329 | 4.643 |
| fresh_verify | 11.430 | 11.837 | 11.433 | 11.799 |

## Final local acceptance

44focused cases reused from exact post-R1 source plus160additional related tests
(nine files) all passed:204distinct cases. XML/log/engine hashes and independent
review source fences checked; full qualified313 fingerprint rechecked before
publication. No later source change occurred. The new hosted gate remains required.
