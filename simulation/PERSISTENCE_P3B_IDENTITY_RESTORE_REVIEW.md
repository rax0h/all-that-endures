# P3B cold identity restoration — architect review

Reviewed Sol implementation: `8545846d08f223fc58d5a14bf22ab0455ef0d10c`.
Accepted preceding baseline: `4629a309868720064e71d13e82954e8752de9152`.
Review: 2026-10-03 America/Chicago. PR #14 remains open and unmerged.

## Finding and correction

The implemented cold resolver, projected identity verifier, typed-copy checks
and private EventLog tail relinking match the bounded architecture. No format,
session, save/recovery or gameplay machinery was added.

One failure-order blocker remained. If a loaded tail Event had an ID inconsistent
with its absolute log position and the replacement had the same malformed ID,
typed-copy comparison passed. `_relink_mutable_tail` rejected the ID only during
application, after an earlier valid link in the same batch had already changed
object identity. The call raised while leaving a partially relinked graph.

Review reproduced this on both ordinary and disk-backed EventLogs. Both added
regression cases failed against the landed code and passed after the correction.

The correction factors the existing private tail checks into
`_validate_mutable_tail_relink`, which returns the resident offset without
mutating anything. The adapter invokes it for each EventLog target during
whole-batch preflight. The applying relink calls the same validator again;
there is no second implementation of the ID/year/type/lifetime checks.
This preserves the complete-batch-before-mutation requirement and existing
exception behavior. No accepted persistence semantics or storage format changed.

## Verification

The reviewed product/test blobs exactly match isolated candidate
`025d728fa65157a601ee0f6863be8253de317d8a`. Its final validation document was
added afterward; its temporary workflow was not landed. Actual logs from run
`37161776401`, job `111316527583` show:

* 61 focused tests passed in 35.40 seconds.
* 249 affected tests passed in 155.62 seconds.
* 416 full-suite tests passed in 356.46 seconds.

Final local corrected-code verification:

* New malformed-tail batch regressions: 2 passed, after both failed before fix.
* Focused cold identity restore suite: **24 passed in 6.81 seconds**.
* One complete simulation/tests suite: **418 passed in 311.66 seconds**.

Commands used Python 3.12 with pytest supplied through a temporary dependency
directory: `PYTHONPATH=/tmp/ate-review-deps:simulation python -m pytest -q -s
simulation/tests/test_persistence_cold_identity_restore.py` and
`PYTHONPATH=/tmp/ate-review-deps:simulation python -m pytest -q simulation/tests`.

The focused fixtures instrument forbidden EventLog iteration and pending decode.
At 4 and 40 disk segments, the projected graph has the same 14 groups/27 paths,
with zero segment payload reads and no cold/pending cache growth.

## Acceptance and next boundary

The cold identity restoration component is accepted with this review correction. It
preserves mutable-tail aliases, current non-log sharing, exact typed values,
fixed storage boundaries and explicit backend lifetime while excluding sealed
LOG identity paths.

This is still helper-level acceptance. There is no cold World/session loader,
atomic World save/recovery, tracked ownership retirement, detach, conversion or
end-to-end restored-continuation acceptance yet. Stage 0.5 remains decision B.

Next Sol assignment: `PERSISTENCE_P3B_COLD_CAPTURE.md` only. It restores a complete
unbound World from the specified cold records inside a borrowed caller-owned
read transaction, with a lazy disk prefix. Session binding and save publication
remain subsequent bounded work. No millennium/endurance, calibration, Stage 1,
normal checkpoint replacement or PR merge was performed or authorized here.
