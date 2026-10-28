# Value-transition whole-package review and fix pass

One fresh read-only Astra/high review of96ccb7c..80a9726 (review_value_transition).
Verdict:0 Critical,2 Important,1 Minor. Reviewer independently reproduced both Important
findings on isolated fixtures; did not rerun full suites or matrices. No re-review claimed.

## Important — single fix pass

1. **Event counter authority.** A coherent next_event ordinary envelope and matching
   head.next_ids999 was fast-certified with an unchanged empty event log, then rejected
   on audited reopen. A new regression reproduced accepted generation1. Changed next_event
   values are now excluded from value-only reuse and receive the full event-authority check.
   Cost: event/structural saves retain the disclosed full-audit path.
2. **Publisher lease ownership.** A publisher could add another active token or remove
   another active publisher's backing lease. Both new regressions reproduced fast commits.
   New lease additions must belong to request.pin.token; active foreign removals are
   rejected, while own release and expired-token pruning remain supported and tested.
   An additional RED probe proved a foreign removal could hide behind structural fallback;
   the lease rule is therefore mandatory before choosing fast or full audit, including
   deletion/new-row cases. Cost: legitimate lease updates stay bounded by MAX_PINS and
   affected dependency rows; deliberate foreign lease editing is rejected.

## Additional executor finding in the same fix pass

A public VersionChange.value could be mutated by a fault callback after encoding. The
new semantic validator examined that mutable object while publication used frozen bytes.
A RED regression changed a reference in the encoded payload while making the caller's
value look unchanged, and committed with a false witness. Validation now decodes the
exact prepared payload/key/membership bytes into private semantic values. Ordinary
counter checks also consume their exact prepared bytes. This is prepared-byte binding,
not a claim to sandbox arbitrary Python/private-object mutation. Cost: decode work follows
changed bytes within the explicit fast-classification budget.

Five new negative regression variants were observed RED (event counter, foreign add,
foreign removal, mixed structural foreign removal, mutable prepared-value disagreement).
Positive own-release and expired-token pruning tests remain green. Final suite and matrix
evidence are retained in verification.json after corrected-source verification.

## Deferred minors

- Current review: native authority module header still says no fast save claim. The
  current results/plan correctly distinguish fully audited admission from bounded saves;
  this module-level prose is deferred, with no runtime effect.
- Prior review: closed explicit-session save/resolve reports SQLite ProgrammingError
  instead of native StoreError. Both reject without writing; API error-type consistency
  remains deferred, not silently fixed during this pass.

## Declined areas — rulings and costs

- Fast/default format7 admission: retain full audited explicit admission and default
  fence; cost is history-dependent setup, not hidden first-save work.
- Unrestricted structural optimization/mature-world performance: retain full audit and
  no mature/whole-year acceptance claim. Cost is slow structural saves until their
  authenticated transition coverage and matched mature measurements are implemented.
- Previously deferred closed-session error type: keep the prior Minor; cost is callers
  catching SQLite's exception rather than the native StoreError contract.
- Arbitrary Python tampering with private objects or explicit superclass methods: this
  SQL capability is not a Python sandbox. It guards normal connection SQL/authorizers and
  binds prepared bytes; cost is no adversarial arbitrary-code isolation guarantee.
- Independent regeneration of archived baseline matrices: executor archive digest/source/
  hash/XML checks stay separately attributed; require the candidate hosted full suite.
  Cost is one independent source review, not independent whole-suite performance replication.

Author-found callback boundary fixes, same review fix pass: trace callbacks could inject
unlisted writes inside a publisher window or during the entry epoch read. Both probes
were RED. Native SQL capability now starts before the entry check, wraps trace/progress/
authorizer callbacks, rejects callback SQL including preexisting cursors, and preserves
a denied-attempt flag. Pure observation/fault callbacks remain supported. Focused native
and value suites passed53/53 in104.17s after these corrections. No second review.
Ruling: reject nested SQL from SQLite callbacks during a native operation — such writes
are outside the prepared publication — cost is callbacks must remain SQL-free in this
window. This remains a SQL capability, not arbitrary Python isolation.

Current disposition: see [consolidated cleanup register](../review-cleanup/register.md) for closure of this checkpoint's recorded Minor findings. Historical review evidence above is preserved.
