# Stage 0.5: private physical-owner save repair

## Failed mature continuation and retained work

[Run 38967941113](https://github.com/rax0h/all-that-endures/actions/runs/38967941113)
failed while preparing the year-1001 save. Simulation took 3635.55 seconds and
save preparation then ran for approximately 1069 seconds before
`hybrid save omits a touched identity owner payload` at the early physical-owner
coverage guard. This was an integrity rejection, not a timeout. No year-1001 or
year-1002 checkpoint was retained. The top-level identity-only header repair was
loaded; this rejection occurs before that repair's World-family fallback.

The saved year-1000 publication remains the input: run 38907665230, artifact
12049884660, `construction-mature-published`. Its archive has 3910109453 bytes and
SHA256 `5ea709166d2bba7f7a22d614fed604f471973ae9ff757979a4148ff197c43382`.
The database has 29601284096 bytes and SHA256
`0d884e52a012ab55325c7111bfc1d054fa7c27aaf0947cf9ab8de4423c213e1c`.
Reuse it; successful preparation, commit, ordering, storage verification, catalog
verification and publication do not need repeating.

## Reproduction and repair

A small complete-format world reproduces the same guard when a published nested
list/map replaces a child and then loses its owning World record before saving.
Payload preparation correctly excludes the held unowned history's private bytes,
but its queued physical identity-placement edits previously survived. The mature
log does not name the omitted owners, so the exact mature trigger is still
unconfirmed. Future coverage errors report a bounded sample of captured owner
namespaces/keys and the total missing count without loading histories.

The repair cancels only journaled placement edits of an unowned physical backing,
restoring each placement's already-checked original incarnation. It retains the
caller's private descendants, including clean shared children whose cached bodies
have been collected. The private backing leaves the save journal before further
shared-child routing, which must resolve the saved physical source. Caller reads
and further private edits can use their retained admitted children. Reattachment
publishes the private graph with the same incarnations.

Independent review also exposed an existing omitted-payload gap: a physical
unchanged-header provider could supply a changed page if that page's child IDs
had not changed. Such a witness now requires byte equality with its checked
saved source; omitted changed pages still fail before commit. No fallback
reconstructs a missing changed physical payload.

There is no format, simulation-rule or checkpoint-lineage change. Work follows
actual dirty backings, their bounded changed physical sources and their placement
journals; it does not inventory unrelated history. Retained children are private
object references, not an additional persisted identity authority.

## Validation and remaining gates

The new regressions cover published list/map replacement and deletion; native
record before-transaction and lost-ack recovery; counted histories; nested private
descendants and garbage collection; repeated edits after saving removal; clean
shared-child collection; dirty original children with and without other owners;
private child swaps; identity-preserving reattachment/reopen; and malicious
omission of a changed physical page. Review findings were reproduced as failing
regressions before their corrections. Existing changed-payload, missing-child,
live-owner-corruption, retirement and compaction checks remain part of the gate.

Final independent review cleared the runtime and validation workflow with no
Critical or Important findings. Its fresh 45-case gate passed in 28.48 seconds.
Additional independent list/map/counted/native-record probes proved unchanged
physical witnesses still work, omitted changed owners reject before publication,
and the complete dirty overlay survives retry and exact reopen.

The final local gate ran the exact 17 test files selected by the CI focused job:
236 passed in 180.75 seconds, with zero failures/errors. Its 12 warnings concern
existing JUnit `record_property` measurements. Workflow YAML, shell syntax,
Python parsing and `git diff --check` also passed.

The validation workflow runs focused tests, then full-suite and recovery jobs on
the exact same commit. It defines no mature construction or continuation job.
Do not reuse the previous runtime's green result for these changed runtime bytes.
After fresh CI passes, repin the continuation execution runtime while preserving
the original checkpoint producer, receipt, input hashes and eager controls.

An exploratory 120-year conversion probe in workspace temporary directories
encountered staging-checksum and malformed-SQLite errors before continuation.
A repeat using a system temporary directory reached complete conversion without
either early error but exceeded its 150-second diagnostic budget there. These
probes do not establish an orphan-repair regression or a mature runtime estimate;
no conversion changes are included. The checked-in 60-year exact continuation
regression remains in the required full suite.

The actual mature year-1001 and year-1002 saves, an independent downloaded mature
restore, and the final Astra review remain required. This repair is not Stage 0.5
acceptance and does not guarantee that the mature continuation will pass or fit
its hosted-runner budget.
