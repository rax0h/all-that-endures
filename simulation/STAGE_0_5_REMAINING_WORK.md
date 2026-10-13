# Stage 0.5 remaining acceptance work

The bounded packed-action repair is green on exact new runtime26dbdad84a35497480583cfd5afbcbea24d5ccde:78 affected tests,2,413 full-suite tests plus2subtests, and an exact independent year7-to8 restored continuation with all profile phases completed. See STAGE_0_5_SPEED_REPAIR_HANDOFF.md and stage_0_5_speed_repair_validation.json. The historical3+4+3 P5 certifies its original production source; no new endurance/P5 was run for this repair.

1. Complete final independent architecture acceptance. Existing review findings were repaired and the complete suite is green; review receipt and exact boundaries are disclosed.
2. Decide performance acceptance on the repaired runtime. The formerly interrupted short profile now completes one simulation year in47.063 profiled seconds, save26.618s and audit14.878s; this is not an endurance guarantee or calibrated baseline speed ratio. Remaining compact-owner reconciliation/checksum/codec costs are separately attributed in the handoff. A further bounded repair should be based on a reproducing regression, not a presumption that an older scan bug returned.
3. Resolve the owner decisions on exact pressure arithmetic versus the measured cold-miss exception, separately authorized endurance evidence or explicit release policy, and production promotion. These are not silently authorized by a green test suite.
4. Restore retention is now verified: P5 artifact11786410897 was downloaded, checksum verified and reopened against an independent year7 control. An identical ZIP is preserved beyond CI artifact retention; see stage_0_5_downloaded_restore_validation.json. CI-only logs/artifacts expireOctober27.

No rank issue17 work, PR14/main promotion, force push, source overwrite, checkpoint-default replacement, endurance or millennium run has occurred.
