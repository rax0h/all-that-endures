# Independent Stage 0.6 whole-world integration repair review

Reviewed commit 89835e2 against 7b0f694 in `/workspace/scratch/69c9a0951946/ate` (three runtime files, new continuation tests, proof workflow inclusion, retained profile evidence). Read-only review; no runtime/test changes made. Completed 2026-10-29.

## Findings

- Critical: none.
- Important: none.
- Minor evidence housekeeping: at review start, committed `docs/performance/stage-0-6-current/world-integration/targeted.log:1` contained only `No module named pytest`. This is failed setup, not regression evidence. Parent acknowledged and is replacing the final log with the fresh bounded regression outcome, preserving/classifying failed setup and earlier timeout as incomplete. Closure requirement: final closure register must cite the successful replacement outcome or explicitly classify an incomplete attempt without claiming a pass. This does not identify a runtime defect.

## Correctness and coverage

`persistence_proof_world.py:178` now supplies the partnership `(change.key, value)` shape required by `persistence_lazy.py:_institution_memberships`; distinct and self-pairs, missing memberships, wrong person and wrong ordinal are covered by the new test. This preserves validation rather than bypassing it.

`_record_hints` supplies the actual persisted `ResponseModel` class for `AbilityProgress`'s TYPE_CHECKING-only annotation. The test resolves every persisted class's fields and explicitly verifies this union. Bare-list handling uses `get_origin(annotation) or annotation`, admitting the documented list backing forms while retaining rejection of map/set backings and field-specific kind constraints.

`persistence_lazy.py:15307` derives structural ordering from each affected table's `_overlay_ordinals`; this is the same order used by `_planned_structural_ordinals` at line 3947. `persistence_lazy_participants.py:29` reorders only marked structural owner slots within each namespace; deleted/transient keys are excluded by the caller. Existing update/deletion slots and unrelated auxiliary writes retain their placement. Store publication assigns `final_next` ordinals on insertion/reinsertion in this order (`persistence_lazy_store.py:2187`), so planned query ordinals and physical collection ordinals agree even with reverse key order, reinsertion and discarded transient insertions.

All 30 `VERSION_FIELDS` and scalar record plans are processed. The caller's layout table includes people, aspiration/resource/material/index/currency/metaphysics/advancement/institution/transmission/motive/social/skill/lineage/genealogy/community tables and scalar tables. The existing freeze source-field coverage guard detects omitted declared version/identity fields. An independent short inline Python check passed across all 30 version fields plus scalar plans: structural slots reordered, auxiliary/existing-update slots preserved, original plan unchanged.

Ordering occurs before `freeze_hybrid_publication`. Frozen sources retain that sequence; `replay_plan` and `commit_arguments` decode captured bytes and original token/generation. Recovery therefore cannot accidentally rebuild insertion order from later live-table mutations. No second transaction or authority was introduced. Existing frozen participant/abort tests are included in the parent's current regression run.

## Regression evidence and limits

The preserved `continuation.log` reports **17 passed in 141.32s**, including the complete generated-world test at 136.89s. I inspected the test rather than repeating that expensive run: generated mature world, two pre-copy years, control digests for years 3 and 4, immutable source hash, two explicit proof saves with chained external commitments, no transaction spanning simulation steps, and a fresh Python subprocess restoring and digest-checking each saved year. Ordinary and proof social insertion/query order both pass in that preserved run. Workflow now includes this file alongside native proof session tests. The parent is running broader affected-family/frozen-recovery regression and harness checks; their result is not assumed here.

The profile report correctly labels the 60-second step sample as censored, overlapping inclusive times as overlapping, full save/warm year as unmeasured, and the different-runner open reduction as not a demonstrated optimization. No independent hosted artifact re-download was performed in this review.

## Architectural conclusion

The explicit bridge exists and the preserved test demonstrates complete generated-world continuation correctness across two saves and fresh-process restores. This is not mature-world performance acceptance. General full-world steps still reach `_audit_world` when the narrow reuse/value-transition conditions fail (`persistence_proof_manifest_publish.py:183`); the authority also performs audit handling for reaudited outcomes. Audited open remains deliberately full/slow. No default activation, merge, endurance run or mature performance claim is justified by this package.

Runtime review is complete with no actionable runtime defect found. Finish the minor evidence-log disposition in this work group's consolidated closure register and attach the parent's fresh regression results before marking the overall package complete.
