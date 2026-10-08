# Event-ID facade: independently verified component

The concrete `EventIdSet(MutableSet)` is implemented and tested **as a standalone component**. World conversion/open/save, compact descriptor authority, codec/canonical allowlists, stable ordinal fallback journals and successor/recovery/detach integration are not yet connected. Existing Worlds still use their accepted event-ID representation. Do not interpret these component tests as closure of the event-ID storage blocker.

The facade proves a normal range from actual set representatives (exact positive ints, cardinality equals maximum), or preserves an exact native-set fallback. It keeps its public identity while shape changes. Native set/frozenset conversions work because it is not a set subclass with empty native storage. Bool/float representatives are not coerced into integers. Ordinary normal add/discard/pop and membership do not enumerate history; explicit whole-set operations may do so.

Named operations and forward/reflected/in-place operators retain native result types and operand rules. Guards precede even no-op mutation, changed callbacks follow actual changes, and materialization uses a shared memo. Tests preserve native partial mutation on a failing iterable, deduplicate symmetric-difference inputs, detect iterator size changes even before first next, and compare500 deterministic mixed operations with native representatives.

Red:34 tests failed before the component existed (0.12s). Expanded protocol checks exposed two partial-update mismatches plus iterator mutation (3 failed in0.11s), then creation-before-first-next iterator behavior (1 failed in0.10s). These were corrected before the final component gate.

At H=1,000 and10,000, checked normal range retains0 logical member entries; ordinary append visits0 old members; object plus attribute dictionary is<8KiB at both sizes. These are runtime component bounds, **not** on-disk open/read/write bounds. Exact imported fallback is deliberately proportional to its exact members.

Final focused component/storage/owner/institution gate: **143 passed in10.30s**, including47 facade cases. The same source passes P5 seed843000,3+4+3 with paged households (`passed=true`, finalyear10,439events, finaldigest `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`). Final combined architectural review and full simulation suite remain pending; no long run was launched.
