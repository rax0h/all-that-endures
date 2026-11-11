# SDD ledger — plan: docs/superpowers/plans/2026-11-10-resumable-proof-genesis.md

Base9e6f022, existing dedicated sol/durable-proof-map checkout; no runtime edits.
User authorized hands-off completion and explicitly requires protected/reusable
expensive work. No new mature request or CI rerun has been started.

Pre-flight: Task1 receipt/data-ref contracts feed Task2 workers; Task3 must seal
real data-artifact refs after upload before publishing metadata. Read-only stages
reuse the preceding DB ref. Parent receipts embed exact ordered contexts/hashes.
Task2→3: stages only accept authenticated inputs at the production launcher;
local test records are not remote authority. All critical runtime/harness/workflow
code is fenced, configuration-only budgets may change without relabeling results.

Task1: checkpoint9RED→GREEN, transport12RED→GREEN;21combined tests passed.
Added separate fresh_restore receipt boundary10checkpoint tests passed. No source
audit certificate persists between processes. File/job/run/ZIP hash bounds fail closed.
Task2: source_digest/capture/catalog/rebase/after_digest/proofs and forced resume
passed; exactly3real generic source audits remain, with finalWorld/physical checks.
Fresh verification separated from measure/save. Five stage tests pass78.28s,
including a real generated4x3World continuation and fresh-process digest. Fixture
without cells initiallyfailedweatherKeyError; corrected to generatedWorld before
observing intended NotImplementedErrorRED. Raw failures preserved.

Task3: pure green-reuse tests written and observed8RED(modulemissing). Implement
launcher/fences/provenance, workflow and request next. Keep new .github/tests,
new workflow/request separate from old triggers; do not touch simulation/tests,
old monolithicrequest/workflow or simulation/ate_sim. Independent reviewer agrees
original-source baseline is stronger/equivalent for format6-only exactcopy+rebase.

Open: full Task3 implementation, whole-group independent review/closure, real small
hosted transport/recovery smoke, then protected mature attempt. No Stage0.6 closure.


Task3: new launcher/workflow/request implemented. Pure green/target acceptance,
software mismatch, dependency fence, workflow DAG and crash-drill wiring controls
pass. Fenced42actual helper/data/workflow dependencies, unchangedengine94267;
new request budgets/mode scheduling excluded from code identity but semantic
context is exact. Gate selects last compatible successful stage, no automatic
restart if inputs missing/expired. Source-first60mindigest,150mincapture/catalog/
rebase,60minpostdigest/fresh,210minindivisibleproofs; operational phases separately
bounded. Transport restore30min and upload45min reserves; stage-level wall limits
in YAML. These are limits, not measured mature durations or a completion guarantee.

Additional explicit boundaries: measure publishes saved DB before fresh validation;
known mature target failure prevents final expensive restore. Real hosted smoke
includes a test-only child crash mid-rebase and fresh ordinary process retry from
the same authenticated parent. Smoke cannot promote into mature context.

First broad affected pass136tests109.55s/1deliberate duplicate-ZIP warning, before
latest boundary/evidence checks. Final full affected rerun and independent closure
are pending. All new production API source remains unpushed; first publication
will trigger ONLY small smoke. Existing monolith request/YAML and engine unchanged.


Task3: complete locally (commits29bf714..1447135 plus review correction commit).
Final: fixed A1–A4 with RED/GREEN regression evidence in this group. A1 binds
source restart run; A2 preserves committed publication across diagnostic/cleanup
failure while stopping failed current DAGs; A3 enforces the aggregate measure
deadline; A4 binds exact artifact/receipt/job attempts. No deferred findings.
Final independent review:72tests passed98.76s;42critical dependencies match the
tested source. closure-addendum.md and closure-fence.json retain the same reviewer's
closure. Spec/register reconciled; historical architecture recommendation retained
with a supersession note. All Minor findings closed in this group.

Final affected command: PYTHONPATH=.:simulation ate-qualified-313/bin/python -m
pytest -q .github/tests/test_stage_0_6_genesis_*.py
.github/tests/test_stage_0_6_retained_*.py
.github/tests/test_stage_0_6_proof_mature_genesis.py ->156passed,1deliberate
ZIP-duplicate warning in77.87s. Full executable/SQLite/lib/compile fingerprint
matches saved qualified313 (final-runtime-fingerprint.json). Raw final-affected.log
and XML retained. Unchanged simulation/ate_sim tree94267 and old monolith
request/workflow confirmed. No engine full-suite rerun is needed for this harness
change; exact successful9e6full/proof jobs remain gating and authenticated.

Task4: independent local closure complete; protected publication/small hosted
transport and crash/recovery proof next. Request is mode=smoke with both external
run IDs0. No mature launch before hosted smoke success. Stage0.6 acceptance remains
OPEN until actual mature targets and exact saved1002digest pass.
