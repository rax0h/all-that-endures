# Event-ID implementation brief

Read `../STAGE_0_5_CONTINUOUS_REPAIR_SPEC.md`. Work only in event-id-work. No child agents, GitHub writes, full suite or endurance. Write unit design/plan, observe red tests, implement, run focused existing affected gates, commit locally and write `STAGE_0_5_EVENT_ID_VALIDATION.md` with exact evidence.

Implement your concrete MutableSet range/fallback design. Actual set values prove the range: exact positive int representatives, cardinality equals max; emptyend0. Never derive membership from EventLog/next_event. Retain facade identity across exact fallback; exact mode uses populated checked stable ordinal set, not one full payload. Implement native named operations, forward/reflected/in-place operators, builtin result types/operand rules, guard-before-noop, bool/float representative semantics, deduplicated symmetric_difference_update and augmented same-object root assignment.

Compact collection kind `event-ids-range/v1`, description `(tag,end,0)`, checked record key0/value `(0,(tag,end))`; physical count1 including empty. Validate exact type/tag/count/key/layout and reject extras/missing/mismatch. Conversion skips member rows after classifying actual authority. Open/save avoid per-member ordinal/key caches. Encode descriptor during ordinary save; concrete codec/canonical/identity allowlists support facade; explicit detach/checkpoint becomes shared native set. Preserve legacy3/4 exact sets.

Freeze descriptor/fallback transition in ColdSavePlan with EventLog/head. Coalesce key0 transitions and validate compact successor before runtime adoption even when full_evidence=False. Test rollback, uncertain acknowledgement, retry, stale writers and retained facade.

Own shared `BOUNDED_AUTHORITY_FORMAT_VERSION=5` and accept3/4/5, transactional monotonic max(current,required), no later downgrade. Other units need floor5; communicate minimal commit/interface early.

At H=1k/10k range:0 residentmembers/ordinals,1 persistedkey,1 open authorityrow,0 member/order visits or ordinary emit/save ID visits,1 descriptorwrite peremit,≤8KiB resident and≤1KiBgrowth,descriptorbytegrowth≤32,0 journalafterack. EventLog integration sealedhistories2048/20480 plusfixedtail. Nativeoperationmatrix, holes/extras/import/representatives, corruptauthority, legacy/detach/digest and formatchecks required.
