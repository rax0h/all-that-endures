# Next save investigation, before another implementation

Current engine is the exact hosted-green95c61911; W13 batching is archived.
Do not spend another full CI run on a proof-read reduction without credible
complete-save evidence. Baseline save itself ranged7.379–11.604s in the latest
memory-variant paired trials; do not assign all variation to source changes.

## What the evidence actually narrows

The earlier full diagnostic (post-rank-profile/, engine6b4e02da) has instrumented
save49.384s, preparation14.570s, atomic commit24.407s and in-memory publication/
acknowledgement9.877s. Nested costs overlap; do not sum cumulative rows as an
independent latency claim. Publisher code is unchanged in later95c61911, but
fresh current-engine attribution is required, not a timing compatibility claim.

Actual95c61911 parent guard accounts for only0.941instrumented seconds in its
separate work probe; the TEMP batching prototype took0.404instrumented seconds
and fewer node reads, yet whole-save trials did not establish a win. The selected
boundary was too small to explain the whole save. Profiler overhead and contention
prevent treating those component numbers as raw speedups.

The save profile records1664checked dependency-value calls,3178read_version
calls and10803snapshot starts. _publish_committed_hybrid validates all immutable
participants, then accepts them; DependencySaveParticipant invokes family row
validation, pool validation and pool acceptance, and pool acceptance validates
again. Existing Coordinator PublicationProof already avoids some unchanged
acknowledgement rechecking. These are concrete call sites to attribute, not
permission to remove checks or proof of redundancy under every failure mode.

## Bounded next sequence

1. On exact current engine/input/runtime, instrument only preparation, atomic
   commit and acknowledgement separately; retain full saved/fresh continuation
   digests and original bytes. Record call/SQL work, not just elapsed times.
2. Use same-engine controls to bound observed machine/process variation before
   comparing another candidate. Keep each disposable trial independently closed
   and bounded; do not rerun compatible completed prefixes.
3. Determine where repeated head/pin/root/row work actually comes from. Inspect
   existing validation_scope and publication-proof custody rules before designing
   a phase-local reuse mechanism. Existing scopes deliberately disallow arbitrary
   borrowed transactions, writes/rolled-back writes, callbacks, stale leases and
   in-place codec mutation; keep those refusal boundaries.
4. Only after identifying a substantial boundary, design a bounded immutable
   publication/acknowledgement proof or other smaller justified change. Prove
   corruption between validation/acceptance, release/replacement, partial ack,
   before/after commit recovery and exact frozen-plan identity. No authority may
   come from dirty flags or a long-lived cache.
5. Measure full save with pinned sources before promoting. One whole-package
   review and one bundled full/proof gate only for a retained engine change.

No mature/default/main/endurance action follows. W3/U10 stay open. Do not turn
this investigation outline into an unreviewed authority redesign.
