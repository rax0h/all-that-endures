# SDD ledger — plan: docs/superpowers/plans/2026-10-27-ate-value-transition.md

Baseline96ccb7c, run40429026742 accepted4273 full/1177 proof/27 complete matrices.
Pre-flight: manifest producer currently audits all changed Worlds and native authority audits again before/after acknowledgement. Both must change in the same bundle to demonstrate actual native save work, not an isolated primitive timing.
Ruling: start with authenticated value-only updates of existing lazy registered records and singleton inline identity — structural edits retain the checked full-audit path — this gives a real common native point-save guarantee without pretending unrestricted graph mutation is covered.
Ruling: use the existing connection's authorizer to prevent durable writes outside central publication/full audits, then bind the exact successor under a locked epoch check — total_changes alone cannot distinguish authorized participant writes from raw SQL — preserve caller authorizers and invalidate prepared statements at window boundaries.

Task1/2 development: isolated existing World scalar reuse RED (full audit called),
actual native scalar save RED (native acknowledgement still full-audited), then both
GREEN after semantic validator and scoped SQL capability. Prepared-statement capability
regression GREEN; attempted unlisted acknowledgement writes blocked.13 focused value
cases passed37.11s. Positive typed query update and rejected integer-for-boolean query
plus adjusted legacy scalar-mode contract passed3/3 in9.04s.
Ruling: require a changed source witness for every changed World owner and authenticate
both old projection and singleton inline groups — unchanged paths alone cannot justify
alias coherence — shared inline mutations retain full audit.
Ruling: tighten legacy checkpoint reuse to session commit metadata only; validate every
value-only counter envelope/head — two RED probes demonstrated accepted wrong year/head
and raw counter envelope — fix remains inside this bundle, with constant-size head checks.
Ruling: retain full audit for512-row/4MiB classification overflow, structural work and
uncertain recovery — actual affected work can legitimately be large — no unrestricted
mature save or fast-open claim is made.

Additional validation:2 counter/head RED probes now reject without publication. Positive
query projection and exact bool-vs-int membership checks pass; legacy scalar-mode test
was updated after observing the intentional old full-reaudit assertion fail (all other
71 initial focused cases green). Native no-full-audit and SQL-write capability cases
passed. Implementation checkpoint follows; actual native scaling and full suites remain
pending. Sealed-prefix archive case is still in its explicitly audited fixture setup.

Fresh whole-package review80a9726:0 Critical/2 Important/1 Minor. Single fix pass
replicated event-counter999 with matching head and foreign lease add/remove. Executor
also replicated mutable public value vs prepared-byte divergence and foreign lease
removal hiding in structural fallback. All5 negative variants RED. Mandatory lease
policy now precedes classification, counters keep event authority, and semantics decode
exact frozen prepared bytes; own-release/expired-pruning positives pass.
Ruling: apply publisher lease ownership before fast/fallback selection — structural work
must not disguise a foreign active lease release — cost is bounded affected lease metadata.
Ruling: derive semantics from encoded prepared bytes rather than mutable public values —
SQL read-only callbacks do not freeze Python objects — cost follows changed payload bytes.
Final: minor (deferred): stale native authority module header; results/plan describe actual
bounded-save scope accurately. Prior closed-session error-type Minor remains deferred.
Every declined review area/cost is documented in value-transition/review.md.

Corrected sealed-prefix fixture uses EventLog.seal_before(1), not2048 mutable live tail
owners. The original live-tail fixture correctly exceeded the fast domain and fell back;
proper sealed-prefix scalar save passed5.25s with0 archive body reads. Corrected new-domain
suite23/23 passed56.66s. Initial broader corrected suite83/83 passed216.06s before the
final global lease/fallback extension; final suites and clean-source matrix follow.

Author-found callback boundary fixes, same review fix pass: trace callbacks could inject
unlisted writes inside a publisher window or during the entry epoch read. Both probes
were RED. Native SQL capability now starts before the entry check, wraps trace/progress/
authorizer callbacks, rejects callback SQL including preexisting cursors, and preserves
a denied-attempt flag. Pure observation/fault callbacks remain supported. Focused native
and value suites passed53/53 in104.17s after these corrections. No second review.
Ruling: reject nested SQL from SQLite callbacks during a native operation — such writes
are outside the prepared publication — cost is callbacks must remain SQL-free in this
window. This remains a SQL capability, not arbitrary Python isolation.

Final verification on clean source 17ed08c9b978a5e96938511662aea1110a06d2aa: 1205 proof, 120 native-regression, 53 focused-value-and-native passed; corrected native1k/10k/100k matrix complete with0 unrelated history reads and0 measured full audits. Source hashes and exact metrics are in value-transition/verification.json and native-scaling/summary.json. Candidate full hosted suite remains required.

Hosted acceptance:4301 full-suite tests +1205 proof tests +28 complete matrices,
zero failures/errors/skips. See run-40462604262/acceptance.json for paired exact-source
evidence. Task3 complete. Explicit native World integration and value-only save
consumption are accepted. Fast-open/default admission, general structural optimization,
matched mature performance and scrub progress remain outside this completed package.
Ruling: close this integration package rather than invent another stage — the approved
plans are implemented and green — the larger architecture's performance gates remain
explicitly unfinished. No main merge, endurance or default format activation.
