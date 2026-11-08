# Execution ledger — plan: docs/superpowers/plans/2026-11-07-ate-rank-proof-index.md

Baseline f1ecae0, both jobs green in 42417207328. Isolated clean clone in the
current workspace; prior workspaces and uncommitted evidence left intact.

Preflight: Task 1 produces seventh scope root and reverse seek consumed by
Task 2; Task 3 tests exactly that representation. Existing sequence roots
must use [5:6], not [5:], when rank authority is present.

Ruling: follow the authorized handoff inline and explicitly opt in to version-4
scope certificates — avoid silently modifying old format-7 authority; if wrong,
the new representation would lose compatibility. Keep six-root controls.

Ruling: cloud skill helper scripts are not mounted here; keep the task ledger
and raw results directly in this group directory — same recovery record, no
unavailable helper invocation.

Task 1: complete — six new reverse/projection cases RED (missing interface) to GREEN 6/6 in 0.56s; final index/native/seek/scope 103 passed in 29.26s. Separate seventh root preserves old root meanings and records an explicit v4 certificate.

Task 2: complete — rank-copy integration RED then seven real coherent-read damage cases RED; current native/projection/driver cases 33 passed in 25.48s, including empty/surplus lookahead, real stale pin, publisher callback, source-immutable copy, save/fresh restore, and 1k/10k expired bucket controls.

Author test correction A1: SQLite wraps an uncaught UDF exception in OperationalError; assert the caught StoreConflictError inside the registered callback instead. Callback-depth marking belongs to NativeWriteGuard operations, so exercise that actual capability boundary. No production guard change. Historical failed logs retained.

Task 3: broad affected tests running. Independent final review and canonical seven-root generated year pending. Hosted full/proof acceptance pending; no new mature timings.

Final independent review: 4 Important +1 Minor accepted and all fixed together; R1 four live-bucket RED; R2 three huge-input RED indicators plus original-pin RED; R3 shadow RED; R4 decoder/snapshot RED; R5 missing-context RED. Final45new tests39.23s GREEN. No second review dispatched. Independent664boundary comparisons and seven-root sequence/reference closure pass on fixes.

Ruling: all review scope exclusions retain the explicit audited/opt-in contract (review.md). No paused iterator added to a synchronous API, no unvisited-suffix proof claim. Cost if wrong: incomplete admission could be claimed prematurely; full admission gate remains mandatory.

Integration diagnostic: one generated-world conversion failed with checked staging mismatch; a traced retry failed with malformed temporary SQLite data, and a system SQLite3.45.1 retry also failed. Exact baseline copy of the same input passed twice. Investigating without changing unrelated conversion code; not recorded as canonical-year success.

Final R3 codec-continuation check RED->GREEN; all47 new cases45.35s pass.
Broader exact-reviewed-source259cases231.87s pass before final one-line guard;
new guard is covered by final47. Current serial proof-copy control passes;
previous setup failures are retained, not attributed to a source bug without
proof. Finish canonical year serially on a clean commit before publication.

Task3 local validation complete:712broader and259affected pass; final47rank tests pass. Exact clean5505bb4/runtimee07f770 canonical raw/diagnostic year3 eager/fresh equivalence, source immutability and0save audits pass. Full hosted gate remains pending publication. See closure.md for qualified source scopes and unresolved earlier environment/setup errors.
