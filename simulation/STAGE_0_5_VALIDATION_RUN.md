# Complete candidate acceptance: current run status

## Current full-suite rerun

[Run 38378944249](https://github.com/rax0h/all-that-endures/actions/runs/38378944249) completed successfully: **2406 tests and2subtests passed in4988.93s, no failures**. It tests corrected candidate `a65d6afa08921477cbaf419695b08f0f98dea4b1`, tree `f33fa16a1b7b5fa0dd8004bd9673e34b45176d28`. Validation branch commit `cb21c4f502c4190f29b4a40728721d32b64a90ec` adds only the isolated CI workflow; checkout is pinned to the corrected candidate. The job also verifies all106 production/script hashes match the passing P5 source before testing.

## Previous completed acceptance run

[Run 38335872125](https://github.com/rax0h/all-that-endures/actions/runs/38335872125) tested production candidate `5bf5c0192b307d15b9ab525cee20938584506ae6`.

- Required complete-format seed8430003+4+3 P5 passed independent controls and all portable lanes: year10,439events, exact expected finaldigest. [P5 result and relocated restore artifact](https://github.com/rax0h/all-that-endures/actions/runs/38335872125/artifacts/11786410897), available untilOctober27. Exact report is also committed as `stage_0_5_complete_p5_final.json`.
- Full suite completed in81m16s:2405passed,3failed assertions (two fault-phase subtests and one copy test), all expecting obsolete floors3/4 while the established fixture conversion requires5. [Logs and JUnit](https://github.com/rax0h/all-that-endures/actions/runs/38335872125/artifacts/11787785511).
- Local RED reproduced these exact mismatches. Test-only repair now verifies floor5 across mutation, faults, retry, copy and reopen, retaining alias/value/generation checks. Focused gate:41passed plus2subtests in10.29s. Existing transactional floor rollback/non-downgrade tests remain green. Runtime/script bytes are unchanged, so P5 is retained rather than repeated.

The earlier local processes stopped without final reports and were never passing certification. GitHub runs proceed independently of the chat. The final full suite is green. Final independent architecture acceptance and performance/release review remain pending. Recorded P5 correctness does not imply latency acceptance: four continuation years603.007s and reopened three years1398.147s; release performance/pressure/endurance decisions remain explicit. Main, PR14, rank issue17, checkpoint defaults and endurance are unchanged.

[Green full-suite logs and JUnit artifact](https://github.com/rax0h/all-that-endures/actions/runs/38378944249/artifacts/11806349572), available untilOctober27. Archive SHA256:4c5e535d8e4857c697050b8abed99b3f4eab2a5cad17910236aa4e549f7f8875.

The verified P5 restore ZIP is preserved beyond CI retention as stage_0_5_verified_restore.zip. Downloaded restore verification passed at year7/337events with exact independent eager authority, generation4 unchanged. See stage_0_5_downloaded_restore_validation.json for durable identity/checksums and operational-copy pin/maintenance notes.
