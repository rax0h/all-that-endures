# Independent native-session review

Reviewed032af75..790c62a (fresh read-only Astra/high, review_native_world_session).
Verdict:0 Critical,3 Important,1 Minor. The reviewer inspected the complete implementation
and native save/acknowledgement path and independently reproduced each finding. This
was one review; amended source is validated by executor regressions, not a second review.

## Important — single fix pass

1. **Epoch resampling race.** During a no-op, an external connection corrupted an ordinary
   row after the comparison sampled the original epoch. The later assignment sampled and
   accepted the new epoch without audit. Regression `test_noop_does_not_accept_a_new_epoch_without_audit`
   reproduced false manifest exposure. Fix: retain the exact unchanged sample; changed
   operations accept only the epoch captured inside the authenticated writer transaction.
   Admission and rolled-back-attempt resynchronization use that same rule. A write after
   the transaction remains detectable by the next guard, never adopted by resampling.
2. **Frozen token/generation disagreement.** The descriptor check used the outer plan token
   while publication consumed commit_token_bytes. Replacing only that frozen token committed
   generation1 and made native recovery permanently disagree. Frozen target-generation
   disagreement could also publish. Parameterized `test_frozen_token_disagreement_cannot_commit_an_unrecoverable_attempt`
   reproduced both. Fix: compare exact frozen publisher token and generation with the outer
   plan and original manifest parent's next generation before invoking publication; validate
   the descriptor against that exact token/generation and retain the same token for recovery.
3. **Schema epochs.** CREATE TRIGGER and TEMP VIEW do not change data_version/total_changes.
   `test_native_epoch_rejects_untracked_schema_changes` reproduced both. Fix: also bind DB
   and codec identity and main/TEMP schema versions. The native opener's owned restore
   transaction rolls back audit workspace DDL: normalize only that TEMP schema component
   to its exact captured pre-admission value after the known rollback. Keep the verified
   data/main-schema epoch; do not sample a new external epoch at opener exit.

All five Important regression variants were observed RED before production edits. Initial
TEMP-schema tracking correctly invalidated reads but also exposed the opener's legitimate
workspace rollback; existing canonical alias tests pinned the required normalization.
Final GREEN suite evidence is in verification.json.

## Deferred minor

Closed explicit proof sessions currently raise sqlite3.ProgrammingError from save()/
resolve_save() before native lifecycle validation, rather than the existing StoreError.
Both operations fail closed without publication. The review correctly graded this an
error-type/API consistency issue. It is deferred; no production fix or failing permanent
regression is included. Its two independent RED probes remain in native-world-review-red.log.

## Declined areas — rulings and costs

- Fast admission, affected-owner scaling, interactive latency and total memory: outside
  this explicitly audited correctness integration. Retain full audits and default format7
  fence; no performance acceptance. Cost: native opening/saving remains history-dependent.
- Partial retirement, mixed inline/backed identities, cyclic backing graphs and inline
  key-reference routes: retain producer exclusions and fail closed. Cost: an excluded
  native edit cannot publish through this path; dedicated support requires its own proof.
- Independent reproduction of archived hosted results and full current suite: executor
  evidence stays separately attributed; hosted run40413908172 is authenticated through
  archives/source/hash/XML/matrix checks. Require next candidate hosted CI before acceptance.
  Cost: this read-only review is not an independent whole-suite/performance validation.

Current disposition: see [consolidated cleanup register](../review-cleanup/register.md) for closure of this checkpoint's recorded Minor findings. Historical review evidence above is preserved.
