# Independent whole-package review: explicit proof-backed opening

Reviewed source: `276d323117cf059f9b6103110e8e6eef083098c2`, runtime tree `53a57cc04c39933bdf2d5d5650a840e267a8877f`, against base `280e95b5c992f7e278ad373d25a44cce9e402b9b`.

Verdict: **Request changes**. One Important and one Minor cleanup finding remain. No second independent review is requested; the same review seat can verify their closure after the work group fixes them. The supplied serial generated-year receipt supports the intended small-world continuation contract; it does not close these cancellation windows.

The review was read-only. No checkout, index, HEAD, branch, or production/test/workflow file was changed by this reviewer. All probes, fixtures, reports and fresh test results are under `/tmp/ate-proof-opening-review`. The parent updated three documentary ledger files during review; production/test/workflow files remained identical to the reviewed source.

## Findings

### R1 — Important: a committed opening lease can be lost before capture returns

Location: `simulation/ate_sim/persistence_lazy.py:18106`–18107; interaction with `LazyRecordStore.capture_pin` (`persistence_lazy_store.py:1207`).

`opening_pin` is assigned only after `capture_pin()` returns. That helper commits the durable lease before constructing/returning its `GenerationPin`. A `KeyboardInterrupt` between the successful COMMIT and the caller assignment enters the opener's BaseException handler with `opening_pin is None`. `abort_open` consequently closes the owned connection but cannot release the already committed lease. This is a real asynchronous-cancellation window, not a malformed-store or arbitrary-accepted-root concern. Repeated occurrences consume pin capacity and can retain old generations.

Reproduction: `probe_pin_return_cancel.py` creates a real ranked SQLite fixture through audited construction, verifies healthy open/close leaves zero pins, and uses `sys.settrace` to raise `KeyboardInterrupt` at the original `capture_pin` return event. At injection, SQLite reports `in_transaction=False` and the original returned GenerationPin is available in the frame. The failure preserves KeyboardInterrupt and closes the connection, but leaves **one durable generation_pins row**. No production function is replaced.

Evidence: `pin-return-cancel.log`, `pin-return-cancel-result.json`, fixture `pin-return-fixture/`.

Required outcome: record the exact owned opaque lease before it can become durable or cancellation can cross this internal handoff; clean only that exact lease, preserve the original cancellation, and leave no pin or transaction. Add a regression at the post-COMMIT/pre-return boundary, with a foreign existing pin control to prove cleanup remains ownership-specific. Do not implement discovery by deleting every new-looking pin or auditing World history.

### R2 — Minor: constructed session registry is not closed when constructor handoff is cancelled

Location: `simulation/ate_sim/persistence_lazy.py:18328`; `simulation/ate_sim/persistence_proof_open.py:139`–142.

`session = LazyWorldSession(...)` leaves the outer local as None until construction returns. Cancellation at the constructor return event (or a later failure inside construction after the registry exists) makes `abort_open` skip registry/session teardown. The database and lease are cleaned, but the owned registry remains open and the constructed session still says active. Cancellation tracebacks retain this graph; its canonical bindings and callbacks are not released by the promised failure teardown.

Reproduction: `probe_session_return_cancel.py` creates a real ranked fixture and raises KeyboardInterrupt from `sys.settrace` at the original `LazyWorldSession.__init__` return event. Observed: connection closed, pin count zero, **registry_closed=False, session_active=True, session_state='active'**, with two live incarnations/two occurrence bindings. No production function is replaced. This is smaller than R1 because no durable lease survives, but violates the explicit registry/resource cleanup contract.

Evidence: `session-return-cancel.log`, `session-return-cancel-result.json`, fixture `session-return-fixture/`.

Required outcome: make the opening operation own the in-construction session/registry early enough for failure teardown, tolerate partially initialized attributes, and close only its owned registry/readers/store while preserving the primary exception. Cover failure after registry allocation as well as constructor return cancellation.

## Validation and scope examined

- Read AGENTS.md, the design/plan, complete BASE..HEAD change, both supplied untracked serial-year files, closure/register/progress and candidate source metadata.
- Independently verified the workspace-qualified Python/compiler/SQLite tuple, SQLite source ID and compile options, interpreter/extension/loaded-library hashes against `fixture-construction/qualified-local-runtime.json`. Result: match. Saved `runtime-verification.json`.
- Traced raw metadata/schema bootstrap and provisional-head protection through constructor, capture and matching snapshot; component/fact composition and seven-root/v4 eligibility; early native record/version/selector/identity/roster/head guards; canonical construction/current-tail aliases; context checking before and after rollback; ownership/abort; unchanged checked publisher/recovery; audited/default paths.
- Fresh independent focused run: **57 passed in 65.78s**, including the 44 opening cases and 13 launcher cases, on the reviewed source. Evidence: `focused.log`, `focused.xml`. Command:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:simulation /workspace/scratch/d88f8db353e8/ate-qualified-python/bin/python -m pytest -q simulation/tests/test_stage_0_6_proof_open.py .github/tests/test_real_year_probe.py -p no:cacheprovider -o junit_family=legacy --junitxml=/tmp/ate-proof-opening-review/focused.xml`
- Parsed all eight changed Python files; parsed workflow YAML; `bash -n` checked its three explicit Bash blocks (the two remaining run blocks are one-line install commands); BASE..HEAD `git diff --check` clean. Saved `static-evidence.json`.
- Independently checked serial receipt source HEAD/runtime tree/driver SHA256 against the reviewed source, all 13 completed phases, exact raw/diagnostic eager/fresh digests, actual child opener names, zero parent/child recorded World audits and diagnostic zero full-audit list. Its recorded raw open/year/save/fresh+digest times are 1.841/9.504/7.140/11.557 seconds. No second timing run was added during concurrent correctness work.
- No additional selected-source authentication, authority-composition, default-compatibility or checked-publication defect was established. This is bounded review evidence, not proof that every possible corruption/interruption has been exhausted.

## Declined-to-judge items and reasons

1. Mature-world 10s opening / 2s save / 1s year, physical page I/O, filesystem cold-cache behavior, or general history-independent total runtime: only a small-world serial receipt and returned-BLOB controls are available. Opening is allowed to materialize live roots and current tail, and indexed physical completeness checks remain in scope.
2. Health of dormant/unvisited cold bodies: explicitly outside proof opening's guarantee. Existing controls show zero returned archived BLOBs during open and rejection before decode when the damaged segment is selected or fully scrubbed. I did not reinterpret deferred corruption as an admission bug.
3. Semantic validity of arbitrary externally supplied root sets: the contract requires a previously accepted audited-construction/checked-publication World commitment. The review tested/authenticated byte selection under that trust model and did not demand an implicit full-World audit.
4. Bundled Python3.12.14/SQLite3.53.1 suitability: expressly unqualified by AGENTS; no acceptance probe used it. Workspace runtime qualification is not a universal supported-version matrix or an engine-only causal conclusion.
5. Hosted CI/full 4,955-test acceptance and endurance: the one bundled hosted gate is still pending; broad author evidence was inspected rather than rerunning an unbounded suite. No main/default/endurance action was taken.
6. Workflow path filters omit the real-year driver/launcher files: recorded in `workflow-path-selection.json`, but not promoted as a defect. AGENTS explicitly calls for targeted validation of benchmark-only harness changes without automatically running the full simulation suite; this package's production/test/workflow edits already select the combined gate.
7. Preserved raw historical red logs/XML/whitespace: accepted historical evidence, not unfinished product changes. Documentary pending-status text was being reconciled by the parent as part of the closure register and is not a new product finding.

## Acceptance conditions

Resolve R1 and R2 (including the Minor) in this work group, preserve their red repro evidence, add/run focused closure controls on the final source, reconcile the consolidated register and run the authorized single bundled hosted full/proof gate. The implementation otherwise follows the explicit Stage0.6 proof-backed opening direction observed in this review. No mature-performance or final-architecture acceptance is granted here.
