# Independent compressed batch package review

Reviewed source: `352751a1e1730f0389d607a5ee7cd6ea145cb6a5`, engine tree
`7347092a500a666710598fe4dcd31ae08d63848f`.
Baseline: `1e84f17da40ff126a3a5129da828bb4e82d527cd`, engine tree
`4654b0194149f735a15c79507a6e57c88a7acbb2`.
The production/test source diff was unchanged at review verification. Only this
review directory was written by the reviewer; no production edits, commits,
pushes, branch changes, or additional reviewers were used.

## Scope and strengths

Read AGENTS.md, the review template, compressed-batch/plan.md, the entire engine
diff and new test file, existing proof map/batch/node implementations and tests,
representative publication callers, the pinned pair wrapper, its reused bounded
runner, and completed raw-pair manifest. Static review ran during timing; probes
began only after the coordinator explicitly declared timing clear.

The change addresses the measured source of work without introducing a new
cache, mutable authority, data representation, or transaction boundary. The
single-leaf work assertion detects the original 65-call behavior, and the long
prefix controls exercise canonical updates and thousands of absent deletions.

The merge invariants hold:

- A stored node is checked before its prefix is used. The common-prefix scan
  proves that the already checked node belongs under the tighter boundary;
  removing virtual levels removes no actual stored-node validation.
- Every recursive call increases prefix depth. Repeated completed ranges resume
  in the loop, so many absent deletions do not accumulate wrapper frames.
- Each jumped range consumes all changes in that range. A later sorted change
  may wrap the completed subtree but cannot modify it, preserving final-only
  node writes. Byte ordering and nibble ordering agree.
- Real branch children retain hash, canonical decode, count, and path checks.
  An untouched child promoted to the new root still passes `_read` at its old
  parent/slot boundary. Unrelated children stay outside point admission exactly
  as before; full traversal remains responsible for auditing them.
- Empty batches and semantic noops return the original root object. Immutable
  old roots remain readable. Input, generator, and callback errors propagate;
  rollback remains the documented caller obligation.

## Independent verification

Command, from the repository root:

```sh
PYTHONPATH=simulation:. /workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python docs/performance/stage-0-6-current/small-operation-profile/compressed-batch/review-raw/review_probe.py
```

Exit status 0; exact output retained in `probe.log`. The script loads baseline
batch code from its pinned Git commit and compares it with the actual candidate.
The map/node dependencies are unchanged in the reviewed engine diff.

| Independent cases | Count | Assertions |
| --- | ---: | --- |
| Exhaustive four-key state/delta combinations | 4,096 | Omission, deletion, same value, changed value; point-update canonical root; noop identity; retained roots; one read per actual node; unique final-reachable writes; baseline touched-node/read/write sets |
| Seeded mixed transitions | 320 | Shared prefix lengths 0, 1, 20, 57, 58, 60, 62, 63; random insertion/update/deletion; same invariants |
| Corruption and promotion differentials | 1,209 | Missing and modified actual node bytes at every reachable digest; changed root count; swapped deep child paths; inflated boundary-child count; all nonempty subsets of affected updates/deletions; exact baseline status, reads and writes |
| Real SQLite rollback faults | 6 | Both implementations; late malformed input, generator failure, and callback failure after the third actual insertion; partial writes observed; savepoint rollback restores all rows exactly; old root remains readable |

The existing focused artifact records 56 passed in 0.99 seconds, including map,
batch, node and new compressed-prefix controls. That compatible suite was not
needlessly repeated by this reviewer. Independent probes supplement it.

## Timing evidence and limits

The complete A-B/B-A manifest binds the two exact engine trees above, preserves
the input, and validates identical saved state and warm continuation digest.
The wrapper changes only the baseline/candidate source roots and expected trees;
the reviewed 120-second child cap and process-group cleanup are reused.

| Pair | Baseline save seconds | Candidate save seconds | Save change | Warm-step change | Fresh-verify change |
| --- | ---: | ---: | ---: | ---: | ---: |
| A-B | 5.163358 | 4.586757 | -11.17% | +4.70% | +7.41% |
| B-A | 5.279999 | 4.823807 | -8.64% | +11.87% | +7.02% |

This supports a save-phase improvement on this small input. It does not support
a general continuation/end-to-end improvement, a mature-scale claim, or a
latency claim from instrumentation. The warm/fresh increases must remain in the
published result and consolidated closure. No causal diagnosis of those phases
is established by these two pairs.

## Findings

Critical: none. Important: none. Minor: none.

No actionable correctness, integrity, format, lifecycle, or maintainability
finding remains from this review. Final publication must carry the stated timing
limits; the coordinator already explicitly acknowledged those limits before
this report was written.

## Declined to judge

- Mature constructors and endurance performance: outside this bounded small
  save optimization, explicitly excluded by AGENTS and the plan.
- Main merge and default-format activation: excluded user authorization; this
  review is not permission for either action.
- Candidate hosted full-suite outcome: the bundled run is a later execution
  gate and had not completed when this source review was written.
- Causal attribution of warm/fresh timing increases: these raw pairs lack the
  evidence for such attribution; their observed increases are retained above.

## Assessment

Ready for the planned bundled candidate validation and publication: **yes**.
The optimized traversal preserves actual proof validation and immutable update
semantics across the reviewed code and independent adversarial probes. Final
work-group closure still records the bundled execution outcome and all timing
limitations in the existing consolidated closure register; this report adds no
open review finding.
