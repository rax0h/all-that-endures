# Independent benchmark launch review and closure

Fresh Astra/high readonly b3030921..1a5a7ad. Initial verdict: changes required,0 Critical/3 Important/1 Minor.10 targeted cases independently passed5.54s; additional probes reproduced the Important findings. No mature transport/run or source mutation by reviewer; no second review.

| Finding | Author closure | Evidence |
|---|---|---|
| R1 shallow checkout lacks pinned ancestor | fetch-depth0 retains ancestry, SHA/runtime/imported source/fingerprint fences unchanged | Real file:// Git clone honoring workflow depth reproducedRED with absent green commit; GREEN after checkout fix |
| R2 early verifier failure loses final receipt; timeout total says complete | split finalization tolerates unreached phases; final verifier result/error/timeout propagated to verification_total, preserving censored flag | Wrong hash/size/sidecar and inherited timeout casesRED→GREEN |
| R3 GNU timeout/SIGKILL has no active-phase/censored record | Publish phase-start before timed work; workflow independently records numeric command exit and nonzero outcome, creates explicit terminated diagnostic from journals if final receipt absent | Real shell timeout subprocessRED→GREEN; no assumption Python finally runs; diagnostic elapsed-since-start is not claimed as exact phase-end time |
| R4 cumulative temporary-key peak differenced as counter | Explicit before/after cumulative high-water fields; true counters remain additive; nested opening/restoration split does not reset counters |100→120 and unchanged120 high-water regressionRED→GREEN |

All four findings closed in this group; none deferred. Final39-case targeted/affected gate and exact workflow CLI smoke include all fixes. Runtime tree remains63d5ac487d0157a5ef521b4def8ee9ce94532e0c. These tests are benchmark/diagnostic gates, not mature latency results.

Declined judgments and author rulings:
- No additional full suite requested: runtime unchanged; new harness/tests/workflow paths don't match the expensive existing full-suite filter. Cost: no redundant correctness run; historical green b303 remains exact runtime baseline.
- Phase/job budgets and disk estimate statically reasonable; actual hosted throughput/capacity empirical. Guarded source+copy+archive+upload headroom retained; failures preserve diagnostics. Cost: hosted budgeted timeout remains possible, reported censored.
- Artifact availability not independently rechecked by reviewer: author checked current metadata, archive digests/expiry and downloaded/validated small acceptance chain; large DB verification remains mandatory on runner. Cost: metadata availability alone does not prove large transport will finish.
- Controlled cache, isolated phase RSS peaks, SQLite page-cache counters, SQL tracing and full scrub not demanded: unavailable/not measured explicitly recorded. Cost: comparisons are observational, not controlled hardware/cold-cache statistics or full scrub acceptance.
- Open resource raw snapshots retained; no additional convenience-counter requirement. Counter and high-water semantics now explicit. Cost: some split resource comparisons require using retained snapshots.
- Accepted digest pin, saved-generation sequence, unsaved warm step, retained input integrity and original producer authentication preserved. Cost: warm1003 correctness is not independently digest-accepted; saved1002 is verified separately.
- CI attribution avoids invented setup/teardown totals or hardware-controlled regression claims. Cost: top call times include in-test fixture construction; fixture reuse optimization awaits bounded attribution.

Post-review fixes were author verified; no claim that reviewer approved subsequent source. Actual mature measurement, optimization and Stage0.6 completion remain pending.

October28 reconciliation: remote36a362d6 measurement completed with warm timeout. The reviewed harness was ported into the actual existing workflow; duplicate local workflow removed, automatic push launch replaced with workflow_dispatch. Actual-workflow smoke and single-workflow regressions RED→GREEN;40 targeted/affected tests passed24.16s. These integration edits were author verified; the original independent review is not claimed to cover subsequent edits. No additional reviewer cycle or runtime change. Fixture-retention upload remains a required operational gate, not a claim from configuration.
