# Independent continuation protocol review

Reviewed implementation: local `11ef1722fda5fd7f8ae1085d2dca34d7fb849ede`, full tree
`dc6a2cf5459b0c84ecae7dd978af44659523fa8a`, based on
`78607c2aec564b8fde94d4b6c79d7ea55a2dbddd`. This record and status edits are
subsequent documentation only; implementation and workflow bytes remain those
reviewed and tested.

A fresh independent `gpt-6.1-sol` high-reasoning reviewer examined all 19 changed
paths, the plan/specification, ledger rulings and frozen helpers. The requested
Astra reviewer was unavailable due to a model usage limit and performed no
review. Sol performed the actual independent gate with no implementation
history. The review was read-only; no code was changed by the reviewer.

## Verdict

Ready to publish and launch the bounded fresh-runner proof plus full suite.
No Critical or Important issues. This verdict does not accept Stage 0.5,
authorize a main merge, or clear a concrete mature launch.

## Findings

Minor, deferred: `continuation_receipts.normalized_audit` excludes
`audit_seconds` from equality without requiring its presence or a finite,
nonnegative numeric value. Removing that diagnostic timing field from a real
audit receipt still passes validation. Substantive audit fields, snapshots,
counters, digests and candidate identity remain mandatory and unchanged.
The implementer agrees this affects timing-metadata completeness only; it is
not a blocker to the bounded proof. No implementation fix was included.

## Evidence

The reviewer independently passed 68 receipt/launch/transport boundary tests in
0.52 seconds, with the intentional duplicate-ZIP warning, and the real
15-process transport pipeline regression in 39.60 seconds. Diff whitespace was
clean. The implementer's final affected selection passed 124 tests in 197.56
seconds, with zero failures/errors/skips and the same expected warning.

The review confirmed that acceptance binds exact saved candidate identity,
manifest/database hashes, original authority and runtime; different artifacts
from the same year cannot combine. Save closes before hashing; independent
readers copy retained inputs, open normally and recheck input hashes. Reader
retries contain no simulation/save calls. Authentication requires successful
producing jobs, including upload, independently of later consumers. Original
year-1000 authority remains pinned, and saved-state audit placement is explicit.
The unchanged runtime subtree remains
`76dee76973928dbce72860156feb32f2d7f02f86`.

## Scope boundaries and implementer rulings

* Actual fresh-runner proof/full-suite results are pending. Their real jobs and
  authenticated output must pass; local proof is not a replacement. Cost of
  ignoring this boundary: claiming unexecuted GitHub evidence.
* Published source readback and remote artifact metadata require subsequent
  exact inspection. Read back every outgoing file/blob before the single proof
  launch, and authenticate outputs after success. Cost if skipped: wrong source
  or producer could be accepted.
* Mature launch configuration is deliberately inert. Only inspected proof and
  input ArtifactRefs plus an independent concrete launch review can enable the
  next missing stage. Cost if bypassed: an unproved or duplicate mature launch.
* Actual mature years 1001/1002 and downloaded mature restore remain unexecuted
  gates. Preserve the existing year-1000 world and execute each missing stage
  once. Cost if bypassed: accepting a fixture as mature evidence.
* Mature duration/memory/disk sufficiency is not established by the bounded
  fixture. Retain approved time/address/disk/upload guards without a completion
  guarantee. Cost if the reservations prove insufficient: a bounded failed run,
  whose earlier successfully retained evidence stays reusable.
* General persistence-runtime correctness is outside this wrapper review. The
  exact unchanged runtime pin retains its prior proof; actual mature gates are
  still required. Cost of overstating it: claiming a new general runtime proof.
* A new live-object audit is not claimed. The approved design requires complete
  saved-reopened audits and actual live counters around save. Cost if this
  distinction is lost: presenting saved observations as an unperformed live audit.
* Main merge, Stage 0.5 and final mature acceptance remain blocked on all actual
  mature results, independent downloaded restore and final Astra handoff. Cost
  of bypassing the boundary: accepting incomplete Stage 0.5 evidence.
