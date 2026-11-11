# Independent resumable-genesis review

Final local closure is recorded in [closure-addendum.md](closure-addendum.md).
The initial findings and intermediate observations below are preserved as history.

Review starts at `1447135b71f4bee554c6aa5eb5aae71ea87361bd`, with unchanged
runtime tree `94267bb00a219702a4bd1700a2fc0600a5c5aa56`. This is the same
bounded-genesis closure group. No production edits, hosted runs, expensive mature
operations, or new fault-injection programs were performed by this reviewer.

## Scope and evidence

Read all four new checkpoint/transport/stages/resume modules, the complete new
workflow, request, recovery helper and existing new test modules; checked their
flow against the resumable design, plan and consolidated register. Inspected the
existing artifact authentication, signed download, recorder, catalog transfer,
rebase and source-fence helpers at the boundaries used by the new harness.

The saved local qualification fingerprint matched Python3.13.5/GCC14.2.0/
SQLite3.46.1, including executable, extension, loaded library and compile-option
hashes. `fingerprint.json` is the observation. The qualification's recorded
runtime-tree field describes its historical scenario; current runtime source is
separately fenced at94267.

Existing ordinary tests passed: **139 passed, one expected duplicate-ZIP warning,
127.80s**. `ordinary-tests.log` and `ordinary-tests.xml` preserve the full result.
The command selected the four new genesis modules, retained archive/transport/
launch/producer modules, and existing proof-mature-genesis harness tests. This was
an intermediate pass: the workflow A1 correction landed while review was active.
The exact final-source closure and relevant correction regressions are recorded
separately when the source is stable.

## Concrete findings

| ID | Severity | Evidence at initial checkpoint | Required correction |
|---|---|---|---|
| A1 | Medium | Source-digest `PARENT_RUN` selected the current run whenever the gate supplied an artifact ID. That ID is also always supplied for a selected earlier-run source checkpoint, so the old artifact was paired with the new run and failed origin authentication. | Use the gate's selected run ID directly for this first worker; verify the source-only restart mapping. |
| A2 | Medium | Final diagnostic `evidence` uploads were fatal. A failure after successful database and sealed-metadata uploads changed the job to failure; checkpoint authentication then rejected the completed work. | Make nonauthoritative evidence nonfatal. Preserve fatal data upload, seal and metadata publication. |
| A3 | Minor | The `measure` stage deliberately supplied an empty outer recorder budget, while its request still advertised an aggregate measure budget. Only fixed inner60/300/60/300s budgets ran; the request value had no effect and compute evidence contained a null budget. | Enforce an honest aggregate deadline without conflicting nested alarms, or expose a precise fixed-phase contract instead of an unused aggregate value. |

All three were sent promptly to the implementer for this same register. A1's
workflow correction and ordinary RED/GREEN regression were reported by the
implementer; A2/A3 closure verification remains separate from this initial record.

## Flow assessment

For the admitted complete-format6 native path, an original-source canonical
control followed by the post-rebase comparison covers the logical transfer and
rebase. The digest grants no source/catalog authority. The original full source
audit, captured physical check, unchanged catalog/reference/roster/graph/type/
sequence checks, full pre-rebase audit and fresh full post-rebase audit remain.
The existing ordinary chain test observes exactly three real generic audits.
Six proof builders remain one indivisible guarded transaction with mandatory
final World/source/proof correspondence and physical/FK checks; no SQL memo
crosses a checkpoint or process boundary.

The one-shot native-capture adapter is limited to the exact captured bytes and
the catalog helper's private transfer call. It copies into distinct private
storage, checks its expected options and schema, and restores the patched method
on exit. Read-only phases retain their immutable database references. The saved
successor is published before the separate fresh-process verification. Target
preflight checks actual completed phase measurements before another large
restore; final acceptance requires the exact saved continuation digest and state.

Artifact authentication is independent of later workflow failure. Exact original
green job IDs remain success-gated; the failed mature job provides no green
authority. Checkpoint consumers bind fenced ancestor code, exact semantic context
and worker binary/compile signature, then authenticate archive bytes and exact
bounded regular-file inventory before using the database. The new workflow
avoids old engine and monolithic-trigger paths.

A completed checkpoint can also survive a nonauthoritative post-job cleanup
failure. The reviewed design recommendation is to authenticate uniquely named
successful data/seal/metadata steps, in order, and bind artifact creation to its
upload step. Require a completed producer job, exact existing origin/hash/expiry
bindings and no ambiguous step names. A failed current DAG must stop; a later
resume may reuse its already committed stage. This narrow rule must not weaken
the original full-suite/proof-map success gates. Its implementation is pending
separate source review.

## Remaining acceptance limits

Local tests use authenticated-metadata fixtures and small real databases. Actual
hosted artifact upload/download, the smoke-only subprocess crash and subsequent
ordinary-process retry remain mandatory before mature dispatch. Mature phase
durations, artifact/disk headroom and interactive targets remain unmeasured.
Per-stage budgets bound loss; they do not guarantee completion. Changed software
or fenced code, expired artifacts, an unfinished proof transaction or transport
failure can prevent reuse. No Stage0.6 performance acceptance follows from this
local review.
