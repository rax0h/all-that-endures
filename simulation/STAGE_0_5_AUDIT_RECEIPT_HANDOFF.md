# Mature audit passed; receipt handoff blocked

Repair status: implementation and19 targeted regressions pass locally after
observing12 failures on the old code. All153 affected checks passed in166.02s,
with one expected duplicate-ZIP warning; the final19 handoff checks passed0.73s.
Fresh independent Astra review cleared proof-only publication. The single
new17-job proof/full-suite run is [39167485117](https://github.com/rax0h/all-that-endures/actions/runs/39167485117),
created October18,2026 at21:21:37UTC. Source
`e3800ed91ca27725f0b75ff0ef38b4fd940da2bd` has exact reviewed tree
`cf20288baaa0217654471d8176189d8ab1b6cd99`; all10 changed files including the
binary fixture read back byte/blob exact. The run completed with failure
October18 at23:15:14UTC. Fifteen jobs succeeded, including the actual retained
audit's authenticated download/reader/full-control check and the bounded
independent downloaded restore. The full suite had2966 passed, two passed
subtests and one failed cost assertion; proof-summary was skipped. A new green
proof remains mandatory before mature continuation.
The successful mature audit and saved generation are reused unchanged.
`stage_0_5_receipt_handoff_repair_local.json` records the exact local gates.
`stage_0_5_receipt_handoff_repair_launch.json` and
`STAGE_0_5_RECEIPT_HANDOFF_REPAIR_REVIEW.md` bind the review and single launch.

## Observed full-suite failure and test measurement repair

The sole failure was
`test_sealed_suffix_publish_has_fixed_unrelated_history_work`: H1000 cost
(155 reads,31 writes,1185 metadata rows) versus H10000 (158,32,1196).
There was no archive-walk rejection or logical audit/restore failure. Exact
failed-suite and successful harness/restore archives and members were
downloaded/hash-checked. Failed-job diagnostics are forensic evidence only,
not a successful producing-job proof. The original strict authentication rule
is unchanged. See `stage_0_5_receipt_handoff_proof_failure.json`.

Five standalone hash-seeded executions passed. A bounded change to cycle-GC
thresholds reproduced unequal costs. Written-namespace traces isolated all
variation to dependency-lease rows:7 versus9 in one reproduction; all other
written namespace counts were identical. BackingDependencyPool tracks weak
alias lifetimes, so automatic cycle collection changes the live lease roster.
The benchmark compared different temporary-object lifetimes rather than a
constant affected closure at different unrelated archive sizes.

The test now explicitly collects fixture garbage before resetting diagnostics
and disables automatic cycle collection only during the two measured saves
and cost capture. It restores the prior GC enabled state and fixture thresholds
in finally blocks. Ordinary refcount cleanup and all actual save/dependency
accounting still run. Exact cost equality and all three archive/registry-walk
rejections remain unchanged; no ceiling, tolerance or retry was added.
Normal and aggressive fixture schedules both measured155/31/1185 at both
sizes. The complete15-test module passed39.73s. The full module is also added
to the early proof gate so this regression is checked before starting the
hosted full suite. Persistence/runtime and receipt helper bytes are unchanged.

The expanded early gate, final independent review and a fresh actual full-suite
proof remain required. Successful mature save/audit evidence remains retained;
no mature stage is repeated or advanced on this failed run.

Actual audit1001 [run39152488567](https://github.com/rax0h/all-that-endures/actions/runs/39152488567)
completed successfully October18,2026 at19:21:19UTC (14:21:19 America/Chicago).
Job117748798734 uploaded artifact12148235361, continuation-stage-audit-1001:
ZIP35605 bytes, SHA256
`c9b502c71e355644b26ae4b0bdb3ca3edc6dfb567335d73465da009af4cd1943`.
Its sole audit.json is223650 bytes, exact file SHA256
`4be22bcfeea6dd71e588d8f65c4e63ab7538c2faca7c4a07640b26b2f1252b97`.
Diagnostics12147711736 ZIP31851/SHA256
`65ccda96de81b33c9af0ed2561077f8d6d054dbbf30392370efb4eebee8bb2b2`
also downloaded and all three members checked. Producing job, source/workflow,
runtime/helper identities, archive sizes/hashes and exact members authenticate.

The downloaded audit passes validate_verification against the original mature
authority and exact bound original checkpoint. Full audit and counters match
the original year1001 control. Its embedded saved manifest equals the earlier
authenticated save summary, SHA25672649d5bef65e4af16ed6cb269b26acde061b57966b728ddd633755ae667b827.
Year1001/generation126 and candidate12129336378 remain unchanged. The actual
runner fully downloaded/authenticated that saved ZIP before opening its
disposable copy, completed audit3068.61408908s and normal close, and preserved
retained inputs. No local large download, simulation or SAVE repeat occurred.

## Exact downstream rejection

The audit artifact is genuine and its full logical control comparison passes.
Its bytes are not stable under receipt_bytes(load_receipt(file)).
Calling the actual next-stage _small reader on this exact downloaded artifact
reliably raises ValueError: noncanonical receipt member bytes.
Acceptance has not run remotely; this is an observed local reproduction of
the current accept-year consumer.

receipt_bytes sorts Python integer year keys numerically before JSON converts
them to strings. Reopening the resulting JSON yields string keys, which sort
lexically. For example, years2 and10 reverse relative order. The mature
new_irons_by_year field crosses this boundary; the prior two-year fixture does
not. The decoded audit's receipt_hash is
`d5b3f1c750c7355c342ed3f127a660ccd2d09d36e5a4c48951902361c04c1f0d`,
which differs from the authenticated physical member SHA above solely because
of serialization order. This is a separate writer/reader handoff gap left
outside the previous comparison repair.

The previous repair correctly fixed logical audit comparison. Its regression
tested the real cross-digit audit/control values, but did not cover this full
publish/reload/next-stage reader path. No runtime or format change has been
made during that status update. The bounded repair below is separate.

## Bounded repair

New receipt writing normalizes JSON key conversion before sorting, using the
same duplicate-key rejection as logical comparison. Publication and reload
therefore agree on bytes and hashes even across digit-width boundaries.
Receipt fields, schema1 and persisted World formats remain unchanged.

One explicit compatibility entry identifies all fields of the actual immutable
audit ArtifactRef, its original physical member SHA4be22bcf, size223650 and
decoded canonical content SHAd5b3f1c7. The consumer still authenticates the full
original producing job/workflow/harness/runtime and exact ZIP before reading.
Its reader requires the exact physical member bytes; arbitrary noncanonical
JSON, rewritten copies and foreign artifact references do not gain this path.
Full original-control validation remains mandatory.

Acceptance's receipt_sha256 continues to mean the physical member hash. For
this one retained artifact, composition and recursive validation bind4be22bcf,
not the hash of a reserialization. New canonical receipts use their stable
ordinary hash. The exact artifact/archive proof plus pinned content identity
keep the embedded receipt and physical source bound without rewriting the
source or rerunning the successful mature audit.

The exact35KB original artifact is checked in as a regression fixture. Tests
cover publish/reload/acceptance, physical versus canonical hashes, every
ArtifactRef pin, whitespace/rewrite rejection, tampered values/control and
duplicate keys. Synthetic digest metadata in unit composition is explicitly
not an actual mature digest result.

The existing17-job proof also gains a mandatory harness step that fully
authenticates/downloads the actual retained mature audit and runs the real
reader and full original-control validator without opening a World. All
existing saved-year, retry, independent downloaded restore and full-suite jobs
remain required. No new mature stage or successful predecessor repeats.

## Required continuation

Preserve the successful save12129336378, actual audit12148235361, diagnostics,
original year1000 and all original controls/provenance. Do not repeat the
successful mature audit or simulation merely to reserialize evidence.
A reviewed compatible receipt handoff must retain authentication of these exact
existing bytes and substantive control validation; do not drop a guard just to
advance. Cover actual publish/reload/consumer behavior across digit-width
boundaries with failing then passing regressions, applicable fresh helper gates,
independent final review and exact published source readback before using new
helper bytes.

Then perform the separate digest1001 and year acceptance on the same saved
candidate, followed by actual year1002 gates, separate fresh downloaded mature
restore and final Astra handoff. No downstream stage, monitoring, merge/main
acceptance or Stage0.5 acceptance occurred. Exact success and blocker evidence
is in stage_0_5_audit1001_result.json.
