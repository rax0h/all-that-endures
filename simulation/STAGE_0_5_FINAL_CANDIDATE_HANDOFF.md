# Stage 0.5 final correctness candidate: Astra handoff

> Current disposition (20 October 2026): candidate architecture and correctness accepted in [the final Astra review](STAGE_0_5_FINAL_ASTRA_REVIEW_2026_10_20.md). Restore-acceptance run 39357369211 and its downloaded output are verified. Production promotion remains pending the explicit release conditions in that review. Earlier statuses below retain their historical source boundaries.

The complete-format implementation has passed its final applicable correctness suite and required independent continuation. Final architecture acceptance and performance/release approval remain open. This handoff contains the tested source boundary and concrete remaining decisions; it does not authorize promotion or further endurance.

## Newer runtime boundary: bounded speed repair green

The packed-action repair is now tested separately at candidate
`26dbdad84a35497480583cfd5afbcbea24d5ccde`: **78 affected tests and 2,413 full-suite
tests plus 2 subtests passed**. The same verified year-7 restore completed one
year, save and full audit with exact independent year-8 authority. Profiled
simulation took 47.063 seconds within its 90-second phase budget. See
`STAGE_0_5_SPEED_REPAIR_HANDOFF.md` and `stage_0_5_speed_repair_validation.json`
for exact source hashes, phase metrics, limitations and residual attribution.
The older suite/P5 evidence below retains its original source boundary; it is
not silently reattributed to the new runtime. Final architecture and release
acceptance remain open.

## Original tested source and evidence

| Evidence | Exact boundary / result |
|---|---|
| Corrected source | a65d6afa08921477cbaf419695b08f0f98dea4b1; tree f33fa16a1b7b5fa0dd8004bd9673e34b45176d28 |
| Final complete suite | [38378944249](https://github.com/rax0h/all-that-endures/actions/runs/38378944249): **2,406 passed, 2 subtests passed**, no failures; 4,988.93 seconds; CPython 3.12.15 |
| CI source pin | Workflow-only cb21c4f502c4190f29b4a40728721d32b64a90ec checks out the exact corrected source and proves all 106 production/script SHA256 entries equal the passing P5 source |
| Complete-format P5 | [38335872125](https://github.com/rax0h/all-that-endures/actions/runs/38335872125): seed843000, 3 prehistory + 4 continuation + 3 reopened years; **passed**, final year10, 439events |
| P5 production boundary | 5bf5c0192b307d15b9ab525cee20938584506ae6; later corrections change only stale test assertions and documentation, not production/scripts |
| Canonical final digest | 3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e |
| Canonical year7 digest | b31c2272d220a1624ff5ee204e229ccaf95adf9a7eaff86643b350567b5e9387 |
| Focused/recovery | Latest component gates78 and17 passed; test-only floor repair41 passed plus2subtests; four actual complete-format cross-family fault/copy/reopen/resolve scenarios passed. Counts overlap. |
| Permanent receipts | stage_0_5_final_correctness_validation.json; stage_0_5_complete_p5_final.json; stage_0_5_complete_candidate_validation.json; stage_0_5_complete_floor_repair_validation.json |

## Delivered architecture

Retains the checked SQLite/MVCC backend, one lazy identity registry, checked catalog/coordinator, immutable event prefix and sole frozen hybrid publication/recovery plan. Concrete family adapters and save participants integrate existing paths. Counted ordered sequences back household and settlement histories. Recursive histories, native record headers and exact NaN atom keys share the same physical ownership and dependency authority. No second persistence system or gameplay rewrite was introduced.

Capability6 requires exact complete-feature markers and reader floor. Ordinary complete open validates checked metadata and rejects missing/competing authority without repair or legacy fallback. `persistence_complete_format.upgrade_lazy_snapshot(source, destination, rules_id=...)` delegates to the existing private, fully verified, source-preserving copy publisher. It currently accepts the bounded legacy lazy format5 lane; genuine formats3/4 first use the established explicit conversion path. Destination races/faults never overwrite a source or competing destination. Genuine earlier readers retain documented compatibility costs.

The root/import audit closes Settlement.memory, culture.Institution.practices, currency maps, advancement records and exact Event-ID exceptions through existing checked binders. All483 stored fields are classified in STAGE_0_5_FINAL_SCHEMA_INVENTORY.md. Immutable imported tuple/text bytes remain actual caller-held/current-input costs; they are not claimed universally constant. Complete copy fully scrubs exception semantics, including positive sorted in-prefix removals and additions overlapping a surviving prefix; ordinary removal probes validate only local queried closure.

## Fixed-work scale evidence on final production bytes

Fixture construction/conversion is full-copy work and excluded from ordinary operation counts. Hold eight live candidates, one edit and two sharing placements fixed for the complete point case. Each entry below reports H1,000/H10,000.

| Operation | Payload reads | Writes | Metadata rows | Read bytes | Written bytes |
|---|---|---|---|---|---|
| Complete shared child point edit/save | 114/114 | 14/14 | 718/718 | 23,859/23,859 | 3,932/3,933 |
| Settlement scalar edit with imported memory | 31/31 | 6/6 | 337/337 | 4,992/4,992 | 1,097/1,097 |
| Event-ID NaN point addition/save | 203/203 | 27/27 | 1,478/1,478 | 56,278/56,284 | 12,746/12,749 |
| Caller-held imported parents tuple edit/save | 42/42 | 4/4 | 472/472 | 50,440/455,440 | 14,966/149,966 |
| Caller-held imported species text edit/save | 42/42 | 4/4 | 472/472 | 11,758/38,758 | 2,072/11,072 |

Settlement scalar edits read zero memory entries. Event-ID point additions visit zero facade prefix members. Complete no-op tests forbid versioned archive reads and require zero payload writes; fixed cold metadata remains disclosed. The checked registry is forbidden from global live-binding inventory in ordinary point/edit/save proof. Full property objects also retain checked-byte, pin, query and maintenance counters in the candidate receipt. Earlier package receipts cover counted edits, clean budgets, retained aliases, source lifetimes, bounded maintenance and corruption; their historical source boundaries remain explicit. Whole iteration, scrub, conversion, detach and current packed action-body synchronization retain their declared H/C/input work.

## Independent review and repairs

STAGE_0_5_COMPLETE_REVIEW.md records one fresh-context read-only architectural review and the repair pass. Material findings were a semantic exception full-copy scrub gap and cumulative dirty owner/backing rescanning; both were reproduced and repaired, then validated by the final suite. Dirty journals now notify actual newly touched owners/backings without another persisted authority. The schema inventory was regenerated with actual generated guards/import treatment. Review scope preceded the final repair pass and was not a line-by-line proof; final architectural acceptance is requested on this tested package.

The first complete CI suite had2405passes and three stale format assertions in older ownership tests. The established conversion already required5 in the recovered pre-session source. The correction verifies floor5 across edits, both faults, retry, copy and reopen, while retaining identity/value/generation assertions and existing transactional floor rollback/non-downgrade tests. The final corrected suite above is the acceptance result.

## Restore artifacts

[Green suite logs/JUnit](https://github.com/rax0h/all-that-endures/actions/runs/38378944249/artifacts/11806349572), archive SHA2564c5e535d8e4857c697050b8abed99b3f4eab2a5cad17910236aa4e549f7f8875.

[P5 JSON/log and relocated SQLite restore](https://github.com/rax0h/all-that-endures/actions/runs/38335872125/artifacts/11786410897), archive SHA2562a77fbf1e6d05d89d9a76e2e2f72dc431377d78e8187ae8038e15e3e7503ab85. Downloaded archive and original SQLite hashca75aa18d6b81642d8d102765dd790cd078fd6c64fe0ceac32d9fdfe24a25199 were verified. The CI artifacts expireOctober27. A verified identical ZIP is also preserved as stage_0_5_verified_restore.zip; its durable identity and hash are recorded in stage_0_5_downloaded_restore_validation.json. The downloaded copy reopened at year7 with337events and exact independent control digest, generation4 unchanged. Normal session pin capture/release and bounded cleanup may alter an extracted operational copy; the retained ZIP remains unchanged. A runner pathname is not the retained artifact.

## Remaining decisions and next bounded investigation

The P5 result proves exact continuation and restore behavior; its runtime is a material remaining concern. First4-year continuation603.007s and reopened3-year continuation1398.147s contrast with eager year10 control0.152s. These lanes have different work scopes, so this is not a calibrated speed ratio. It demonstrates substantial backend overhead whose dominant cause has not yet been established. The earlier notified-dirty reconciliation fix was verified, but does not account for all remaining latency.

Next performance work should profile one fixed short continuation from a verified restore copy, separate ordinary simulation from open/save/full audit, retain phase and SQL/callback attribution, and stop at an explicit diagnostic budget. Diagnose before modifying source; preserve native arithmetic/RNG/identity and one authority. A localized repair requires a reproducing regression, affected gates, measured before/after and a new final runtime source boundary. Do not launch another full3+4+3 or endurance merely to find a hotspot.

Astra should review capability selection/compatibility, identity and recovery closure, schema/import and byte boundaries, scale/maintenance proofs and the review repair pass. The owner decisions remain exact pressure arithmetic versus the scoped bounded-memory O(H) cold-miss exception, performance requirements, separately authorized final-source endurance or explicit release policy, and production promotion. The pressure cold-miss exception must not be presumed to explain all measured P5 latency.

PR14 remains draft/unmerged atc29e3d06a0c9d219235e2b3f0390271bd1245aea. No rank issue17 changes, main/PR14 promotion, force push, source overwrite, checkpoint-default replacement, Stage1 or new millennium/endurance run occurred.
