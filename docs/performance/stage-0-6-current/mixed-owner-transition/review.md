# Independent package review: mixed native value/tail and fresh-owner proofs

Reviewed against green base `d80ceb80c6add545e1da0a87cf3cc26c8aff38e0` in one read-only review. Scope includes the mixed transition in `persistence_proof_world_insert.py`, the shared value-validator repair, the new mixed tests, scaling scenario and hosted workflow. The review includes author fixes within this original group, not another approval cycle. Only this review report and temporary probe outputs were written by the reviewer; no implementation, hosted workflow or additional agent was started.

Final disposition: no open actionable Critical, Important or Minor issue in this finite package. This is not Stage0.6 completion, mature-world latency acceptance or independent approval of arbitrary new backing/retirement transitions.

## Consolidated disposition

| ID | Origin / severity | Problem and action | Verification / status |
|---|---|---|---|
| MX-A1 | Root author / Important | The shared preexisting value path could accept a byte-identical registered scalar-owner rewrite without advancing its catalog source witness. Ordinary Event-ID source rewrites had the same revision problem. Require the exact source witness for authenticated unchanged registered bodies, retaining accepted projection facts without needless re-projection. Structural sequence branch metadata is explicitly excluded from catalog-owner classification in both validators. | Inspected the final repair. Independently passed all four absent/present witness regressions for lazy scalar partnership and ordinary Event-ID. Missing witnesses fail and recover the original generation; correct witnesses commit without full audit and survive audited reopen. Closed. |
| MX-C1 | Reviewer / contract clarification | The composition preserves independent byte limits in the insertion, value and tail validators. The insertion helper charges frozen input, predecessor sources and catalog dependencies; it is not a single4MiB total across every duplicate/helper read in the whole composed call. | Root accepted precise per-validator wording. This report records that contract explicitly; per-validator512-row/4MiB checks and catalog read charging remain in code. Closed as a documentation clarification, not a missing global-cap implementation claim. |

No additional actionable defect was found in the mixed composition or its harness.

## Integrity assessment

Fresh scalar owners retain accepted predecessor absence, declared lazy collection authority, exact field/query validation and contiguous fresh allocation. Existing input is partitioned from fresh owners and checked by the existing value/tail validator. Its exact updated owner witnesses are mandatory, including unchanged-body rewrites. New ordinary layout bytes are authenticated against the prior layout or original manifest and increment only the fresh owner families.

Canonical catalog regeneration includes all affected concrete lazy and ordinary owner sources, using the existing catalog primitive. Its overridden metadata reader authenticates every fetched predecessor against accepted content and charges it before use, including unchanged owner-tree nodes. Structural branch nodes remain metadata rather than being forced into concrete-owner catalog contracts. Extra/missing/malformed catalog rows cannot be hidden by partitioning.

Successor certification starts from prepared tail facts, adds exact fresh semantic placements, and compares the actual owner/group roots and allocator to independently reconstructed touched roots. The child root must equal the prepared tail child root; sequence structural root remains unchanged. Content count includes added and removed version rows. Event authority and namespace inventory remain unchanged. Existing query and collection publications retain their existing authenticated source/order checks. Unsupported topology still selects the checked fallback.

I independently combined distinct history growth and shrinkage with a new Person, an existing lazy value edit and an ordinary Settlement edit. It saved with full World audit forbidden and reopened under a full audit with exact contents and shared history identities.

I also forged unchanged physical RECORDS owner-tree membership bytes inside the writer, keeping body values and physical row checksums consistent. The new catalog reader rejected the save specifically with `insertion predecessor lacks accepted content`. The transaction rolled back, original-generation recovery succeeded and an unmodified retry committed. Thus unchecked physical checksums do not replace accepted content authority for these additional catalog dependencies.

The mixed scaling scenario measures a new Person plus existing skill, shared integer tail, ordinary value and year changes. It permits only the exact changed tail page in its first-save body-read attribution. It separates construction/full audited admission, traced save, raw save and VM work. Archives are retained history values, not years; full audit on fresh admission remains outside the save metric. The reviewer inspected the driver/workflow but did not independently rerun the complete1k/10k/100k matrix.

## Independent verification

- Initial mixed file:16 passed in26.01s.
- Combined distinct grow/shrink + fresh/lazy/ordinary owner probe: passed, with full audited restoration and alias identity checks.
- Unchanged owner-tree self-checksummed membership forgery: rejected by accepted content proof; rollback/recovery/retry passed.
- Source-only witness subset after repair:4 passed,16 deselected in4.45s.
- Final focused mixed+source-only subset after repair:9 passed,11 deselected in11.93s, including fresh-process mixed restoration, ordinary and shared backed values, same-page/growth/shrink tails and all source-only witness cases.

The root owns final full affected-suite, harness and exact-runtime scaling evidence; these are not claimed as independent reviewer executions.

## Reviewed final source fingerprints

```text
simulation/ate_sim/persistence_proof_world_insert.py 0214e74a640562a0919816cf03101f6719a6eb0a3dabf1c603eb068440b7d098
simulation/ate_sim/persistence_proof_world_value.py a13977f003a04921daedec8f869736cd648bee7c1c31472579fffa1284c14684
simulation/tests/test_stage_0_6_proof_world_mixed.py 5e1c7d3b224daef22a7fe446647e7947e8e94fc9ac081b9a2837bee8c638a569
.github/tests/run_proof_native_insert_scaling.py 9b0ed6781368f56793a5aa1406641c16177c521a30b2e0ef976331e316e63232
.github/workflows/stage-0-5-proof-map-validation.yml cd6ddbf89fd65bf690fbabe4a7c9842d58a00e76a44393bc524fc86d81b9f063
```
