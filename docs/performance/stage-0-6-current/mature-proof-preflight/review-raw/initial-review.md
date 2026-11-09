# Independent whole-package review — mature proof-fixture preflight

Reviewed base `b9196f9885fed0323c473bcc148f6b9dad9da9eb` through candidate
`b43ca5ea7fcda923441bf2e9be0297f7de947cee`; actual HEAD matched candidate and
`simulation/ate_sim` tree remained `6ca23be5208e8c198081c73b40806b42a4eb8626`.
Read-only review: checkout, index, HEAD and branch were not changed. No subagents.
All review-created files are under `/tmp/ate-mature-preflight-review`.

## Finding R1 — Moderate (P2), open

**Reject wrong or incomplete world/pin requests before the large retained transport.**
`simulation/stage_0_6_proof_mature_preflight.py:146-158` validates schema,
operation, attempt, budget, source identity/fingerprints, database identity and
disk before `prepare_retained`, but never checks request `world` and `pin` there.
Those fields are first checked in retained `authenticate_staged`, after the
4,419,106,896-byte ZIP has been downloaded and the 29,922,463,744-byte database
has been extracted/authenticated. Wrong seed/year/store/head and missing seed or
captured_head therefore reach large transport despite being locally decidable
invalid requests. This violates the explicit bad-request-before-big-transport
contract and can waste the bounded run and tens of gigabytes of runner work.
It does not bypass later accepted-source authentication or change source bytes.

Reproduction: `probes.py` runs the actual `check_source` against the clean
candidate, changes only one request world/pin field at a time, and replaces the
transport seam with a sentinel exception. All six cases reached that seam;
`request-probes.json` records exact outcomes. Disk was given ample headroom only
for this transport-boundary probe. No network request was made.

Required closure: derive the accepted seed/store identity from the existing
original authority and expected year/head from the original launch (or another
equally immutable original binding), validate exact world/pin shape/types/values
before `prepare_retained`, and add wrong/missing field controls asserting zero
transport calls. Preserve the unchanged downstream authentication. Same-seat
verification of the fix closes this review; a second independent review is not
requested.

No actionable Critical, Major or Minor finding was established in the reviewed
scope. R1 must be resolved in this work group before publication.

## Verified behavior and evidence

- Qualified Python executable/extension/libsqlite hashes, Python/compiler/SQLite
  versions, SQLite source ID and complete compile options match the existing
  qualification reference. Historical application `runtime_tree` is not treated
  as an interpreter fingerprint; current application tree independently matches
  the pinned green/runtime contract. See `runtime.json`.
- Re-ran exactly the new plus retained targeted gate: **85 passed, one deliberate
  duplicate-ZIP warning, 29.08s**. See `targeted.log` / `targeted.xml`.
- Independent real small-database probes: **8 passed, 3.85s**. Covered oversized
  metadata key/value and namespace, non-integer head generation/seed, actual
  read-only URI and required PRAGMAs/transaction/connection closure, immutable
  table-journal collision with final error, and a mutation after closed SQL
  rejected by the final hash. See `test_independent_probes.py`, `probes.log` and
  `probes.xml`. An initial independent namespace corruption setup collided with
  the schema's unique key before invoking the inspector; its raw log/XML are
  preserved as `probes-construction-failure.*`, then only that setup was corrected.
- Inspected actual monotonic progress-handler cancellation control, before/after
  closed-connection hashing, fixed SQLite aggregate expressions, bounded returned
  metadata, namespace cap, immutable started/table/final receipts and no decoder
  or World restore/step/save/migration call in inventory. Existing real SQL
  interruption test passes in the 85-test gate.
- Inspected reuse of retained producer/archive/original candidate/acceptance
  authentication. One-source + pinned ZIP + 6 GiB reserve is checked before the
  transport. No additional whole-source database copy is introduced.
- AST, YAML, all four Bash blocks and all 14 committed request fingerprints pass.
  Workflow is dedicated to the request marker or explicit dispatch, has the
  45-minute job/35-minute command/900-second inventory bounds, always uploads
  only small evidence and does not schedule a full simulation suite. See
  `static-checks.json` and extracted `workflow-step-*.sh`.
- Reviewed all changed product and documentary paths, retaining raw historical
  red evidence. No runtime-tree change. Review source and evidence hashes are in
  `source-hashes.json` and `evidence-sha256.json`.

## Declined to judge / limits

- Did not download or scan the 29.922 GB retained fixture, verify live artifact
  expiry/availability independently, or predict the scan's completion time,
  temporary-disk peak or aggregate inventory. The bounded hosted job measures
  those facts; no mature-resource or performance acceptance is claimed here.
- Did not independently re-run the prior 9,233.81-second hosted full suite or
  full proof-year gate, or re-fetch their job records. Reviewed their documentary
  closure only; parent-provided verified hosted bindings remain prior evidence.
- No World opening/restore/decode/step/save, proof-genesis conversion, migration,
  default activation, main merge or endurance acceptance was attempted.
- Did not claim protection against a hostile concurrent process replacing the
  owned extracted source and restoring identical bytes; the existing source
  ownership plus sidecar/hash checks are the intended local contract.

## Publication readiness

**Not yet ready at b43ca5e: R1 remains open.** After R1 is fixed and its early
rejection controls plus the bounded targeted/static gates pass on the final
source, this package is suitable for publishing the single authorized inventory
job. Its result must be read before selecting proof-genesis resource budgets.
