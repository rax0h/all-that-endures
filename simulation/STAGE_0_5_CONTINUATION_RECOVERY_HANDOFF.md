# Astra: finish continuation without discarding completed saves

Sol has implemented the local durable continuation protocol and runner wiring.
See [implementation status](STAGE_0_5_CONTINUATION_CHECKPOINTS.md). Fresh protocol
CI, final implementation/launch review and the actual mature stages still gate
advancement. The treasury-report repair passed focused and full CI39070285697
(2831 tests plus two subtests). Monitoring remains disabled and main is unchanged.

## Verified failure

[Run 38992881882](https://github.com/rax0h/all-that-endures/actions/runs/38992881882)
failed October 17, 2026 at 05:56:50 UTC. It used execution runtime
`2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a`, subtree
`76dee76973928dbce72860156feb32f2d7f02f86`. Year 1001 simulation finished and
`session.save()` returned; audit then raised `TypeError: Object of type
LazyHistoryMap is not JSON serializable`. Reopen/control verification and year
1002 were never reached. Only diagnostic artifact 12091846715 uploaded. There
is no recoverable uploaded year-1001 checkpoint from that run.

The old missing-owner save guard did not reject this attempt. That is progress
through the save path, not proof that the saved world was correct. The report
bug is independently reproduced with a real complete-format one-treasury
database in under a second. The green 60-year regression did not call this audit.

Observed first-year simulation: 4087.60 seconds; save plus compact diagnostics:
3645.25 seconds; audit until failure: 4897.53 seconds. Another combined two-year
300-minute run has no supported time budget. No mature performance guarantee
follows from the report correction.

## Completed correction

`run_long_history.snapshot` now copies the treasury mapping and each denomination
map into plain dictionaries. It preserves exact values and prevents reports
from retaining mutable lazy-world references. It does not add a permissive JSON
encoder, omit fields or change simulation/persistence behavior.

New tests in `tests/test_long_history_report_treasuries.py` cover populated legacy
and complete stores through actual mutation/save/reopen, and detached snapshots.
Before the fix: 1 passed, 2 failed, including the exact mature TypeError. After
the fix: **65 affected tests passed in 273.95 seconds**, with the existing
intentional duplicate-ZIP-member warning. The affected selection includes this
new file, `test_stage_0_5_final_long_harness.py`,
`test_construction_mature_continue.py` and `test_checkpoint_artifacts.py`.

Independent review approved the report fix, validation-only workflow and design
handoff with no Critical or Important findings. Its three report tests passed
in 2.47 seconds. One minor plan-ordering ambiguity was corrected: implement the
restore stages before the whole-protocol review and fresh-runner CI gates.
This review does not approve the unimplemented protocol or a mature launch.

The `ate_sim` subtree remains exactly
`76dee76973928dbce72860156feb32f2d7f02f86`. Repair CI 38985095878 remains the
existing proof for those runtime bytes, not for new harness behavior. The new
report validation workflow runs focused and full suites on the exact published
source and contains no mature job. Its result must be inspected before claiming
full fresh validation. It does not implement or certify the staged protocol.

## Architecture decision and implementation

Read both documents before changing wrappers:

- [Design](../docs/superpowers/specs/2026-10-17-continuation-recovery-design.md)
- [Implementation plan](../docs/superpowers/plans/2026-10-17-continuation-recovery.md)

Sol owns the implementation using the existing approved runtime. Retain a
closed, explicitly unverified database after **each** saved year. Run the full
audit and full reopened digest in separate stages on authenticated copies.
Accept a year only when both receipts bind the same exact artifact and match
the original independent control. Year 1002 cannot start before year 1001 is
verified. Failed verification resumes from the retained saved artifact; it does
not simulate that year again.

The audit intentionally moves from the producer's live World to the normally
reopened saved World. Preserve and compare live counters around saving, keep
every substantive audit/control comparison, and label the new evidence
accurately. Never fabricate an old P5 result claiming the old live-audit order.
This decision changes validation orchestration; no runtime-format, simulation
rule, ownership or corruption invariant is relaxed.

The source is still published year 1000, run 38907665230, artifact 12049884660.
Preserve all original checkpoint/config/context/producer hashes and original
controls from `construction_mature_continue.py`. Preserve original producer
`bbc3cbf11becb58aa4b9483114559fd1296878f1` separately from execution runtime
`2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a`. Do not repeat successful preparation,
commit, ordering, storage/catalog verification or publication. Only year 1001
simulation must restart because the failed run uploaded no saved candidate.

## Sol execution gates

1. Build strict receipts, single-year save, separate audit/digest, acceptance and
   independent downloaded restore as specified. Observe real-fixture RED then
   GREEN, including populated treasuries and actual interruption/retry.
2. Prove separate-process and fresh-runner authenticated transport. Demonstrate
   that an audit failure preserves a completed save, a digest failure preserves
   successful audit evidence, and a retry calls no earlier simulation/save.
3. Preserve no-overwrite, full authentication, disk/address/upload guards and
   300/360-minute limits per stage. Read the explicit audit-placement decision
   and do not silently weaken it. Inspect measured time before changing budgets.
4. Obtain one independent final implementation/launch review, resolve material
   findings, publish exact source and verify readback. Check all active/pending
   continuation runs across SHAs before a single stage launch.
5. Launch only the next missing mature stage, starting with save1001 from the
   retained original publication. Give Daniel the direct link. Do not poll long
   jobs or create/re-enable an automation. Preserve successful artifacts/receipts
   and inspect each before advancing.
6. After real 1001/1002 verification, perform the actual independent downloaded
   mature restore on fresh runners. Authenticate the exact complete artifact
   and original chain, use disposable copies, compare actual values/digest/
   counters and prove retained bytes unchanged. Then request final Astra review.

Do not merge main or call Stage 0.5 complete before all actual gates pass.
