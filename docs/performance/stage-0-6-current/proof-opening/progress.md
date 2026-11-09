# Execution ledger — plan: docs/superpowers/plans/2026-11-08-proof-backed-opening.md

Baseline280e95b, runtime d91d48cc36dc4fa822b1bf5a52bca6a218437a28.
Hosted8d0fea0/run42494896887 green4911tests+2subtests9304.06s; proof job green.
Qualified system-derived local venv has123focused passes and original13phase
canonical eager/fresh validation. Its full interpreter/SQLite fingerprints must
match fixture-construction/qualified-local-runtime.json before execution.

Ruling: use existing dedicated sol/durable-proof-map workspace inline, preserving
its branch and local backup checkpoints — existing user continuation authorization
and no other edits/workers on this branch — creating another implementer/worktree
would duplicate the already isolated project state. No main/master implementation.
Ruling: existing hands-off continuation authorization covers the outlined explicit
proof-backed opener; preserve defaults/audited API and reject unsupported scope on
new API — no routine approval pause — wrong eligibility would reject a snapshot
that still has its audited compatibility path, not expose unverified state.
Ruling: cloud skill helper scripts are not executable local files; keep the exact
plan/spec identity, task state, rulings and evidence in this versioned ledger.
AGENTS overrides generic deferred-Minor advice: every review finding closes here.

Pre-flight Task1->2: authority admission must be active before restore metadata;
owned alias restore stays inside OwnedOpenRead so failure cleanup has one owned
lease. Private opening manifest protects constructor/capture/snapshot raw heads.
Pre-flight Task2->3: new API requires7scope roots; driver proof_only requires
rank_proofs and must propagate mode into its fresh child. One final review/CI.

Task1: corrected an initial test import typo before valid RED (collection error
preserved separately). Valid RED19missing-API failures/1audited positive26.07s.
Initial bootstrap/early authority GREEN20passed23.70s. Qualified interpreter,
SQLite extension and loaded library hashes rechecked; source AST/product whitespace
checks pass. Task1 interfaces implemented; continuation/cleanup/cold gates follow.
Ruling: keep preauth bootstrap in a focused private module returning the same
LazyRecordStore, rather than another connection/publisher or duplicating restoration.
Exact pinned opening manifest guards inherited capture/head reads until native
authority is active. Complete-format check reuses existing late contract via
check_restore without replaying admission. Cost if wrong: a preauth read could
select forged bytes; negative controls and final review must cover this boundary.

Task2: restore-red reproduced four real defects among12cases: late capture
cleanup lost its pin, foreign private admission invoked a callback, a changed
codec method escaped the final check, and rebound cleanup rolled back a borrowed
connection. Exact admission type is now checked before dispatch; the original
lease and owned DB/codec are retained lexically. Closed-codec and context checks
run through final transaction cleanup. restore-green32passed36.94s.
Owner-red reproduced three further failures: changed store identity, changed
session pin, and a changed session pin from the final rollback callback. Final
checks now join the accepted manifest identity and original session binding;
abort uses the immutable original lease. owner-green35passed36.41s.

Task3 cold/recovery controls7passed17.18s. At1and4sealed2048-event segments,
proof opening materialized zero segment payload bytes; selected first access
materialized649122bytes; audited positive control materialized1947366and7809444
bytes. Counts describe returned BLOB materialization, not physical SQLite page
I/O. Coherently rechecksummed dormant corruption is rejected before decode on
first selected access and explicit verify_full; no-op save does not visit it.
All three original native save interruption/recovery outcomes still pass.

Resumed after unavailable execution environment; working tree and completed
cold-controls evidence recovered intact. Full qualified-runtime fingerprints
rechecked before the broader affected selection. No failed test result was
inferred from that workspace outage.

Driver RED5cases proves missing proof-only/rank eligibility and CLI propagation;
child-helper RED1case proves missing fresh-process API. Preserve audited default,
construction audit, eager oracle and accepted-source hash. Selected parent and
fresh-child APIs now have actual World-audit counters; proof-only mode raises
on any attempted continuation audit. Final driver/affected checks pending.

Launcher GREEN13passed5.85s includes real fresh-child audited/proof opens and
six-root proof-only rejection. Parent mode validation6passed0.07s. YAML/all5Bash
blocks/changed-Python AST/product whitespace checks pass. Small isolated launcher
correctness fixtures may overlap broader regressions; the generated-year timing
and acceptance probe remains serial after all correctness runs finish.

Cancellation investigation: original audited post-restore wrapper already catches
BaseException, but canonical restoration caught only Exception. New fast opening
therefore left one owned lease on KeyboardInterrupt/SystemExit. Both reproduce
RED; extending the owned restoration exception boundary and preserving primary
cleanup errors yields GREEN2passed3.40s. The broader run had already loaded the
pre-cancellation source and42opening cases; qualify it accordingly and run the
final44opening cases on the final source before committing/profiling.

Final local opening/launcher run57passed72.55s, including44opening and13launcher
cases. candidate-source.json hashes match the tested final runtime/driver/workflow;
Python AST/YAML/all5Bash blocks/product whitespace checks pass. All4955simulation
tests collect in1.40s. Broader affected run remains in progress on its pre-cancel
source; no speed claim derives from concurrent correctness-test durations.

Broader affected selection completed469passed920.82s, no failures/errors. It
loaded the pre-cancellation handler; its normal Exception paths are unchanged,
while final57 verifies the final handler including both BaseException cases.
The original admission/default source, metadata/source/order/query/identity/
roster/rank and existing publisher/recovery cases remain green. Exact selection
is affected-selection.json. Final source checkpoint and serial original-driver
proof-only year follow; independent review/hosted validation remain open.

Clean source checkpoint276d323117cf059f9b6103110e8e6eef083098c2,
runtime53a57cc04c39933bdf2d5d5650a840e267a8877f. Serial unchanged-scenario
driver command: qualified venv Python .github/tests/run_proof_real_year_probe.py
--rank-proofs --proof-only, bounded15m, scratch output proof-open-year-01.
All13phases pass; raw/diagnostic eager and fresh-process state equal, accepted
source SHA256 unchanged, zero parent continuation World audits, zero diagnostic
save-time World audits and zero audits in both actual proof-only child processes.
Receipt pins source/runtime/driver and separately records raw/diagnostic timings.
Raw open1.841/year9.504/save7.140/fresh restore+digest11.557s; diagnostic
open1.735/year9.499/save19.271/fresh+digest9.712s. Diagnostic timings are not
substituted for raw. Small world/shared host; no mature or controlled speedup claim.
One independent whole-package review requested against this source and receipt.

Independent review of276d323 found R1Important (committed pin handoff cancellation)
and R2Minor (session constructor handoff/partial registry teardown). Both original
probes are promoted: four canonical cases first fail4.94s, then pass5.17s.
Private lexical resource ownership now spans allocation/constructor handoffs,
without changing ordinary callers' private kwargs. The initial broader opening/
launcher/default-store revision passes112cases83.76s. R1 closure's duplicate-token
negative control exposed false ownership before INSERT; promoted RED1.40s,
registration moved after successful INSERT and before hook/COMMIT, final5closure
cases pass6.23s. R2 is independently closed, including before-registry cancellation;
R1 same-seat final closure and final-source regression/probe are pending.
Earlier276d323 timing/source evidence remains historical supporting evidence;
repeat the exact serial driver after checkpointing the final corrected runtime.

Final review-fixed source:113regressions pass78.38s (49opening,13launcher,
51default-store), final-source.json hashes match. Same independent review seat
closes R1/R2:10fresh controls13.46s plus real SQLite KeyboardInterrupt/SystemExit
after INSERT/before registration prove rollback preserves the foreign pin/DB.
R2 before/after-registry and constructor-return controls pass; partially initialized
fields tolerated. Independent source hashes match final bytes. Review-raw preserves
initial request-changes, intermediate collision red and final closure. Every finding,
including Minor, closed in this work group. Checkpoint/serial final probe next.
