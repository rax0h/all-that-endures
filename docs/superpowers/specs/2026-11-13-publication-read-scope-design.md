# Closed coordinator publication validation scope

Continue the authorized Stage0.6 save investigation, active95c61911. Fresh
instrumented current-engine attribution has prepare57042SQL, commit98479SQL,
acknowledgement102387SQL. Acknowledgement invokes6993checked-head reads and
7021pin checks; coordinator validation is its largest component. Times include
cProfile and are attribution, not raw latency acceptance.

Hypothesis: CoordinatorSaveParticipant currently opens read_snapshot before
coordinator/catalog validation. Nested checked_read_operation then cannot own
its read view, so its established metadata sharing is disabled. Let this one
closed participant validation own checked_read_operation instead. Reuse existing
scope invalidation/custody, row/root checks and PublicationProof finish semantics.
No new cache, proof format, long-lived authority, direct acceptance shortcut or
skip of changed-row validation. Arbitrary borrowed transactions remain ineligible;
writes/rollback, SQL callbacks, codec/lease/root drift retain refusal/fallback.
Scope closes before cold confirmation/acceptance and application interaction.

Alternatives: new publication-wide certificate is larger and not yet justified;
removing acknowledgement checks weakens correctness. This small reuse of an
existing checked context is the selected implementation call, within standing
authorization. Prove actual native metadata work reduction and exact full
save/recovery before considering raw whole-save benefit or one hosted gate.

One independent whole-package review, all findings including Minors closed.
Same qualified runtime/input, reusable bounded outputs, no mature/main/default/
endurance actions. First-playable responsiveness and mature performance remain
separate from these persistence benchmarks.

Scope cache allowance must honor min(256KiB,catalog.byte_limit//6), matching
existing nested catalog sharing and reserved buffer accounting. A custom128byte
catalog must not receive the default256KiB. Independent Minor R1 reproduced and
fixed with a permanent small-budget regression; no other findings remain.
