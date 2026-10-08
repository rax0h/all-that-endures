# Shared-owner correctness repair

This is the first correctness slice of continuous Task 1, not completion of its bounded-discovery work.

Confirmed defects: a shared wallet edit publishes only its loaded owner; an IndexedRecord descendant publishes only its top record, leaving containing wallet payloads stale; equality suppresses distinct mutable replacement and retains obsolete sharing.

Design: reuse the checked current incarnation registry to resolve all current lazy owner placements before mutation. Rehydrate only those peers, validate that each placement still contains the same object, and attach their notifications before the edit. For IndexedRecord assignments, notify containing owners after the assignment through optional table hooks; ordinary non-lazy RecordTable behavior is unchanged. No new sharing authority or independent commit is introduced. Equal distinct mutable replacements are changes even when their serialized values compare equal.

Implementation: generic namespace-to-table routing in LazyWorldSession; dictionary preflight resamples bindings after cold peers attach; lazy-table record hooks bridge IndexedRecord notifications. Placement replacement/deletion must remain authoritative and retained aliases must never route into a different current object.

Verification: observe all mutation-side/reopen-order cases red, inspect saved owner payloads, run affected currency/people/identity/ownership/lifecycle and recovery gates, then save/reopen and portable detach checks. Preserve no-op values and stale mutation guards. Subsequent bounded identity work replaces the current global baseline inventory; this slice must not claim that open/save inventory has already been bounded.
