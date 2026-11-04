# Hosted proof-map regression repair

Failed source: `5efb299fdbae963e8f5cb9e683a0ed24a287842f`.
[Run 41878768574](https://github.com/rax0h/all-that-endures/actions/runs/41878768574),
proof-map job `126745436185`, failed in
`test_new_sequence_backing_retains_checked_fallback` after 61 other native
insertion/mixed/new-backing cases passed. Earlier proof primitives and scaling
commands completed successfully. The queue delay was separate from this defect.

The final sequence descriptor-key guard combined two different decisions:
malformed IDs must fail integrity checks, while valid newly allocated IDs must
leave the existing-sequence optimization and retain full checked publication.
Comparing every ID to the predecessor allocator made valid new sequences raise
`StoreIntegrityError` before fallback. Session cleanup then reported the unresolved
failed save; that secondary error was not the root cause.

The repair validates exact positive integer IDs below 2**63, then returns
`Unsupported` for IDs at or beyond the accepted predecessor allocator. No new
sequence receives append-proof authority. The whole original frozen batch
continues through the existing checked fallback. All budgets remain unchanged.

The pre-existing hosted regression reproduced locally before the fix. A new
real-session regression also reproduced RED for appending to an existing shared
sequence while creating a distinct new Household sequence in the same save.
It checks successful publication, restored values, retained sharing, and the
new sequence's independent identity. Both RED logs are preserved here.

The proof-map native insertion test command now includes the complete sequence
module, so its append, unsupported-shape, tamper and recovery cases run together
with insertion/mixed/new-backing coverage. Runtime launch authority is refreshed
to `339cf658adbac54352bba4124eca59dbfda81479`.

The combined sequence/insertion/mixed/new-backing group passed **84 cases in
292.62s**, including the exact hosted failure and the new mixed regression.
The clean committed source passed **29 benchmark launcher cases in 20.72s**.
An earlier uncommitted-source run had 27 passes and two launcher rejections
because its execution SHA/runtime differed from reviewed committed source;
its raw log is preserved as `harness.log`, and the clean rerun resolves both.
Workflow YAML, every embedded bash script, all launch fingerprints, staged
runtime identity, and `git diff --check` also passed.

Published source checkpoint `8e58a5f0465dbb67bbd916f7e8a5d49e994757d6`
has complete tree `f9c7ae80b76e53468903b867e8c6f150296944a5`, identical to
locally validated checkpoint `261b6a94b24ad599d7f644c7fbbb4d4532dd3410`.
Only commit metadata differs. Evidence is published as one child commit and
one branch update, starting one corrected full/proof validation cycle.

Hosted validation remains required on the corrected published source.
The superseded full-suite was still running at the last prepublication check;
the connected GitHub API has no cancel operation, so it was not stopped.
The workflow's existing concurrency rule may hold the corrected run until
that older run finishes. No retry of the known failing source was launched.
The existing independent package review is preserved; this
small correction is author verified, not represented as a second review.
The complete-year 512-row composition boundary and mature performance targets
remain open. No default activation, main merge or endurance run is included.
