# Stage 0.5 bounded speed repair candidate

The candidate is now green on GitHub run38402924015:78 affected tests and2,413
full-suite tests plus2subtests passed; the verified restore completed year8 with
exact independent authority. See `STAGE_0_5_SPEED_REPAIR_HANDOFF.md` and
`stage_0_5_speed_repair_validation.json`. The interrupted local evidence below
is retained as history and is superseded by the complete CI result.

This is a new runtime candidate based on the Astra diagnostic handoff at
`65710f7c48dbcc059de6eaadfd18f0187cd1ae03`. The earlier full-suite and P5 passes
certify the previous runtime; they do not certify this repair.

The repair uses the existing changed-owner journals and checked identity
coordinator. Unchanged packed action placements no longer rediscover every
identity group. A checked scalar projection permits per-position reconciliation;
structural changes and actual mutable/native-backed records retain the complete
graph path. Requested mutations recheck their affected identity group. Generation,
same-connection writes (`total_changes`), and external SQLite commits
(`data_version`) invalidate the projection.

Scalar payload dirt remains published through real owners without being treated
as another structural packed-list edit. Packing also normalizes tracked mutable
fields through the existing alias-preserving plain-value conversion, retaining
closed-record validation. The mutable-field packing failure was reproduced on
the unchanged diagnostic baseline before applying this fix.

## Evidence and current limits

- The baseline 320-action regression reproduced repeated unchanged-group work.
- An intermediate repair measured append reconciliation at 0.04538956 seconds,
  zero group reads and zero owner reads, versus the handoff's 10.730-second
  append and 329 group reads. This is component evidence, not a whole-world
  speed claim, and predates the final scalar-dirty follow-up.
- Targeted warm-corruption, mutable-field and move/duplicate tests passed together
  (3 tests, 21.71 seconds) before the last closed-record guard was added.
- The final affected local batch stopped after 58 progress markers out of 78
  collected tests, without a reported test failure or final JUnit report. The
  runner was no longer available at 2026-10-13 13:05 UTC. This is incomplete
  validation, not a pass or a diagnosed test failure.

The dedicated validation workflow reruns all 78 affected tests with verbose
progress and retained JUnit output. After that gate, separate runners execute the
full applicable suite and fresh component/90-second-per-phase restore profiles.
The restore profile downloads the previously verified P5 artifact and verifies
the original SQLite checksum before using a disposable operational copy. A
profile budget interruption remains diagnostic only; a completed year must also
pass its independent authority comparison before being reported as correct.

No new P5/endurance run, Stage 1 change, promotion, main update, or PR 14 update
is part of this candidate validation.
