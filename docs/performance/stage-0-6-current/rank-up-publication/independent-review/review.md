# Rank-up publication: one independent whole-package review

Review seat: `/root/rank_up_publication_review`. Read-only against `/workspace/scratch/d88f8db353e8/ate`; no source, index, or HEAD mutations. Review includes the complete current production/test diff, new retirement validator/test module, spec/plan, and the added pinned-header restoration fix. The parent implementation and final affected-suite run are separate from this review.

## Disposition

**No unresolved Critical, Important, or Minor findings.** One Important was found, reproduced, fixed by the implementation owner, and verified within this work group. This is an integrity review result, not a performance or full-suite acceptance claim.

| ID | Severity / origin | Concrete issue | Action and evidence | Status |
| --- | --- | --- | --- | --- |
| RUP-R1 | Important / independent review | `Retirements.__init__` classified initial jobs with Python tuple equality, then authenticated the supplied tuple rather than the canonical tuple. `False` in the integer cursor, float generation, or integer reclaimed flag could compare equal to a canonical initial job. A malformed frozen producer delta successfully committed a manifest that a subsequent full audited open rejected. | RED in `probes-initial-types-frozen.log` (phase `False` committed; audited reopen raised `invalid history retirement job`). Implementation now compares exact codec bytes and retains `initial.value`. Added production regressions exercise all three aliases, require precommit rejection and unchanged manifest/generation, then retry canonically. Read `docs/performance/stage-0-6-current/rank-up-publication/exact-types.log`: **3 passed in16.69s**. | Closed |

No separate Minor was raised for the initially sparse adversarial test coverage: the six independent corruption/recovery controls and one partial-audit control below provide concrete coverage for the examined new branches. They are retained as review evidence for the group.

## Reviewed authority and lifetime boundaries

- Existing-record child replacement is derived from accepted old payloads, not dirty flags. Exact registered class/seal and reference path/kind equality bound supported record edits; predecessor OwnerScope counts and every accepted path are checked. Deleting auxiliary owners removes their complete accepted paths. OwnerScope, GroupScope, semantic owner-projection roots, and exact canonical catalog changes are composed from those edits.
- Fresh forests retain parent allocator restrictions and descriptor/dependency/member-type validation. The newly closed roots cannot reach accepted old backings; every new edge is still included in fresh-cycle detection. Deferred old private backing publication remains on the fully checked fallback.
- Initial retirement jobs are now byte-canonical and exactly match old groups that lose their last placement. Background operations authenticate accepted jobs and pending-query membership, descriptor kind/backing fact, dependency source/kind/leases, retention floor, and authenticated child seek selection/exhaustion. Final physical deletion requires no remaining ChildScope children (or exactly the record/NaN header being deleted). Descriptor deletion also removes the accepted semantic backing/order facts.
- Background auxiliary owner deletion is reflected in the placement overlay before foreground last-owner detection, so descendant cleanup cascades. Unhandled/deleted sources cannot silently disappear from checking. Exact frozen catalog regeneration covers rotations, compacted ranges, and allocator gaps/unused groups. The existing source/catalog/projection/byte limits and96-row physical background budget remain explicit.
- Full World audit continues reconstructing all physical scope roots and checking all content/root counts before retirement-specific checks. Existing catalog/type/sequence authorities check queued/partial trees; the new audit checks pending projection, actual descriptor/dependency kind, partly-retired live placement/lease refusal, and scopes passed by the cursor. Global child-family/shape checks and complete World projections remain in place.
- Dependency filtering applies only to actual captured new descriptor publication in World retirement mode; the default standalone API is preserved. The frozen publication inventory is checked on reuse and cleared on accept/abort/close. Filtered private unpublished aliases retain their caller lifetime.
- The late pinned-header restoration fix is consistent with the source contract: exact saved header bytes imply no header payload publication, so only journaled outgoing owner routes are cancelled. The original checked placements are restored before private orphan decisions. Child backing overlays remain independent. No additional lifecycle defect was established.

## Independent probes and qualifications

- `runtime.json` verifies the qualified Python3.13.5/GCC14.2.0/SQLite3.46.1 executable, compiler, SQLite source ID and compile options, `_sqlite3` extension hash, loaded SQLite library path/hash, and qualification-receipt runtime-tree anchor against the saved qualification file.
- `probes-rejections-allow-recovery-audit.log`: **6 passed in34.55s**. Frozen producer corruption controls omit the initial retirement job, omit the background descriptor, dependency, or job, inject a live-target delete, and jump the initial cursor. Every attempt was rejected before physical generation advancement, resolved, and saved on canonical retry. Some unsupported/rejected shapes legitimately use the existing full checking path.
- `probe-partial-audit.log`: **1 passed in6.96s**. A real512-member/four-page list was retired with a bounded producer budget of4 for the probe, leaving one physical page within the current scope. Supported maintenance saved with full World audit forbidden; full audited opening accepted the valid partial tree. A coherent cursor advance injected after global source-root checks was then rejected by `audit_jobs` because a passed scope retained physical authority. The failed audited opening rolled back, and another full audited opening succeeded.
- `probes-initial-types-frozen.log` is intentionally preserved RED evidence from before RUP-R1 was fixed. `probes-initial-types.log` is an earlier downstream-mutation experiment that reached postcommit participant mismatch; it is not the clean reproducer or final verification.
- `probes-rejections.log` / `probe-omitted-descriptor-recovery.log` contain a review-harness-only false lead: forbidding the authority's legitimate audit after an early rejected preparation prevented settlement. Allowing the original recovery audit produced the six clean passes above; no engine recovery finding remains.
- Final `git diff --check` was clean.

## Declined to judge

- No full simulation-suite, hosted-CI, mature-constructor, endurance, or release/default-format activation judgment; those were excluded from this review task.
- No raw latency/scaling or memory measurements; probe durations are test receipts, not performance claims.
- No claim for unsupported topology becoming bounded, old-incarnation reuse, sequence physical retirement on the finite path, or runtimes outside the saved local qualification.
- Parent-reported real rank-up/body continuation, eight maintenance saves, fresh-process continuation, and private-restore results were read for context; they are not misrepresented as independently rerun review probes.
