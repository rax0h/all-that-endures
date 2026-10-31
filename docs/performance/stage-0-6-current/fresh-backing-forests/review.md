# Independent Stage0.6 fresh backing forest package review

Initial reviewed candidate: `98c44a5ab78f98ed8174dfc69629ccecf8c36418`.
Base: `81f40bd`.
Runtime tree: `03ee3545feccf0228a3650cd5ac1881e72d49e08`.
Review date: 2026-10-31.

## Result

No unresolved actionable findings, including Minor findings, in this candidate.
This is the one independent read-only review of the work group, begun at design
time and completed against the committed implementation. No code was edited by
the reviewer, no additional reviewers were spawned, and no hosted or full-suite
runs were launched by the reviewer.

The finite admission design reuses the accepted content/scope/World authorities
and the existing catalog and publisher. Complete new list/map/set/record extents
are checked from frozen rows. Fresh projections determine exact owner/group and
child roots, allocator advancement and semantic facts. Old targets require both
accepted content and backing-inventory facts; they do not trigger traversal of
their history pages/entries. Existing edits retain the value/tail proof path.

The review covered the runtime modules and their integration with manifest
publication, World/type checks, child/scope staging, catalog regeneration,
retirement metadata reads, dependencies and member policies; all changed tests,
the native scaling driver, workflow changes, source pin and scope document were
also inspected. The working tree was clean at that initial candidate. A small
author-origin fallback correction was subsequently inspected within this same
review; its exact scope and evidence are recorded below as F7.

## Consolidated closure register

| ID | Origin / severity | Concrete action | Closure evidence | Status |
|---|---|---|---|---|
| F1 | Design review / Important | Preserve aggregate incarnation semantics: reject differing inline fingerprints/kinds, mixed inline/backed identities, and cycles including record-header edges. | `insert._prepare` aggregates `identities`, checks backed/inline intersection and contiguous fresh allocation; `Forest.check` records all auxiliary edges; `Forest.facts` checks fresh graph acyclicity. Nested shared-record and recataloged cycle tests pass. | Closed |
| F2 | Design and first implementation pass / Important | Bound accepted old alias expansion and reject surplus physical occurrence/link rosters before legacy iterators can scan them. Authenticate and charge legacy catalog dependencies, including retirement reads and link bodies. | `Forest.guard_alias_work` caps aggregate accepted group counts. `CatalogStore._roster` uses indexed expected-count-plus-one probes with field and byte caps; occurrence/link compatibility and streaming APIs pass through this guard. `CatalogStore.read_version` authenticates retirement helper accesses; `CheckedCatalog._read` authenticates catalog dependencies. Both surplus-roster injection tests forbid the legacy scan and verify rollback/retry; over-budget alias fallback passes. | Closed |
| F3 | Design review / Important | Evaluate newly introduced incoming policies against frozen successor type witnesses when an old target changes in the same batch; bind projected descriptors to the prepared successor semantic facts. | `Forest.value` prefers frozen rows; `_policy_counts` uses that successor value. `_target` authenticates the old descriptor and checks its projected semantic commitment against `tail_facts`. Independent direct probe supplied an empty predecessor witness and integer successor witness and confirmed rejection of a newly introduced lineage-pair policy. | Closed |
| F4 | Design review / Important | Registered record headers must replay family field-container and incoming member policies rather than relying only on `_check_field_values(..., None, ...)`. | `Forest.project` replays all matching consuming-family field checks; `Forest.check` derives class-family incoming policies. The new backed MaterialLot policy case rejects boolean transfer IDs. | Closed |
| F5 | First implementation pass / Important | Apply the same policy checks when a fresh owner references an old backed policy-bearing record; accepted old backing facts alone did not establish these class-specific field policies. | `Forest._target` checks old record fields and the direct policy-bearing child descriptors/witnesses, using successor witnesses. The old-backed MaterialLot policy case rejects boolean transfer IDs. No history page/entry traversal is introduced. | Closed |
| F6 | Completion pass / Minor | Update scalar-only/no-new-backing comments and remove unused imports/state. Update formerly-fallback alias tests to assert the newly supported bounded behavior. | Final insert docstring and dependency comment describe fresh forests; unused `Counter`/`old_groups` were removed from the new module; insert/mixed tests assert no full audit for supported alias insertion. `git diff --check 81f40bd..HEAD` is clean. | Closed |
| F7 | Author-origin final fallback correction / Important | Select checked fallback for declared unsupported fresh sequence/frozen/atom/event references, and for valid generic backed records whose concrete container kind differs from the optimized World-family representation. Preserve rejection of invalid generic field types and class member policies. | `_target` raises `Unsupported` for the explicitly unsupported fresh kinds. Generic `_check_field_values(..., None, ...)` still runs before family-specific checks; only the additional family mismatch is converted to `Unsupported`. Two new Household fallback save/reopen regressions and the two existing new/old MaterialLot policy rejection cases independently pass together (`4 passed, 19 deselected in 6.21s`). | Closed |

## Independent verification

Command:

```text
PYTHONPATH=simulation:. python -m pytest -q simulation/tests/test_stage_0_6_proof_world_new_backings.py
```

Observed result at `98c44a5`: `21 passed in 34.18s`. This evidence predates F7
and is not presented as a rerun of the corrected tree.

This includes empty/small/multiple-page fresh lists, old shared 10k history with
old-body read guards, nested maps/sets/shared records, a fresh-process reopen,
fully recataloged cycle rejection, fresh/old backed record policy rejection,
three publication fault boundaries, missing/surplus physical and identity rows,
bool-vs-int witness integrity, dependency kinds, physical alias roster guards,
and explicit over-budget fallback. A direct successor-policy probe also passed.

The implementation owner is running the wider existing proof/native regression
gate and the scaling matrix separately; this report does not claim their results.

## Deliberate limits

The fallback remains necessary for unsupported fresh sequence/frozen/atom/event
graphs, arbitrary existing backing-reference replacement, deletion/retirement
transitions and over-budget batches/alias rosters. The new path has finite
512-row / 4 MiB input-and-dependency limits and separate projection/alias caps.
This review establishes correctness of the bounded slice, not mature-history
speed, full-year cost, default-format activation, merge readiness, or endurance
acceptance.

## Same-group supplemental inspection for F7

The author found and corrected the fallback issue after the initial reviewed
commit. This was a focused closure pass within the original work group, not a
second whole-package review. No additional unresolved issue was found.

The inspected supplemental runtime file SHA-256 was
`f68a26d55340572d9243db1d6efc95f151786cf2e55d68f534f50e0b822606a2`
for `simulation/ate_sim/persistence_proof_world_new_backings.py`. The tested
regression file SHA-256 was
`f3e9a2c76f0a6a0342db239736b280eb016668f60d088b9efaf58ca9ac571927`.
These changes were uncommitted during this focused inspection; the author will
record the final commit/runtime source pin and wider target gate separately.

Independent supplemental command:

```text
PYTHONPATH=simulation:. python -m pytest -q simulation/tests/test_stage_0_6_proof_world_new_backings.py -k 'new_sequence_backing_retains_checked_fallback or generic_backed_record_representation_retains_checked_fallback or backed_record_cannot_bypass_class_incoming_policy'
```

Observed result: `4 passed, 19 deselected in 6.21s`. The original 21-test gate was
not repeated. `git diff --check` was clean for the supplemental changes.

The workflow timeout change from 60 to 90 minutes was also inspected. It adds
job-level headroom for the reported prior green duration of 52m32s, the added
forest scaling matrix and hosted variance. The individual scaling-command
timeouts remain unchanged. Workflow SHA-256:
`eee7d3f90df988e3e84ad18e8219784812abc50d03a071980e856bc1ce0e1f74`.
