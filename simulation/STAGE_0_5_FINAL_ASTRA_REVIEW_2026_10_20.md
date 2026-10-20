# Stage 0.5 final Astra review — 20 October 2026

## Decision

**ACCEPT the reviewed architecture and correctness candidate.** No new Critical or Important implementation finding remains from this review. The original R1 clean-retention, R2 lifecycle and R3 household-history blockers are closed in the reviewed implementation. The mature continuation and independent downloaded-restore evidence is accepted at its exact source boundary.

**Production promotion remains pending.** Candidate acceptance does not authorize a merge, change the default checkpoint API, approve interactive performance, or claim indefinite operation. The controlling architecture distinguishes candidate validation from owner release decisions. Preserve exact preparedness arithmetic; obtain the owner's disposition of its documented O(H) cold-miss latency and the measured mature-world cost before treating this as an unrestricted production release.

Recommendation: close the correctness/architecture work at this frozen candidate; accept the completed year-1001/year-1002 plus independent-restore endpoint as the developmental release evidence; carry performance work separately with measured budgets. Another long simulation is not required by any new finding in this review. Integration into PR #14 must be prepared separately against the current main branch and preserve these reviewed runtime bytes.

## Frozen source and evidence boundary

| Item | Verified identity |
| --- | --- |
| Review candidate | `fb75f1c49edda0731287acbf0054a1151ec318c9` |
| Candidate branch | `sol/stage-0-5-mature-continuation-stage` |
| Execution runtime | `2cbf3510ef1f0ad8ddd712a1c4174ccfa518291a` |
| Runtime subtree, `simulation/ate_sim` | `76dee76973928dbce72860156feb32f2d7f02f86` |
| Final acceptance harness | `7b188abd629d21b93b766c44fb5df0512d045bcf` |
| Full-suite/protocol proof source | `4fecd93fdcc5012a404afc07ce166cb7ff422f59` |
| Accepted final year / generation | 1002 / 127 |
| Store identity | `06d24556-2bb1-4086-93f7-448f23b7eb5a` |

Local Git comparisons confirmed the runtime subtree is identical to the execution pin and **all Python source and tests are byte-identical to the green full-suite proof source**. The twelve implementation fingerprints in the downloaded proof also match the review checkout. Changes since that proof are workflow/configuration pins, documentation and evidence. The final launch differs from its checked-out harness only in the launch workflow.

The 1,000-year input was constructed with an earlier pinned implementation. The final runtime continued and saved that mature world through years 1001 and 1002; separate processes audited, digested and restored it. This is not a claim that the final runtime ran an uninterrupted new millennium, or that two successful years prove every later state.

## Verified test and mature-world results

| Evidence | Result |
| --- | --- |
| [Final proof run 39177774744](https://github.com/rax0h/all-that-endures/actions/runs/39177774744) | All 17 jobs succeeded, including interrupted-audit recovery, two saves, audits, digests, acceptance and independent restore |
| Full-suite job 117825088932 | **2,968 passed, 2 subtests passed**, 42 warnings, 5,359.67 seconds; completed log inspected |
| [Year 1001 acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39207586140) | Generation 126; audit/digest/counters and original independent control agree |
| [Year 1002 acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39317887835) | Generation 127; exact accepted predecessor and original independent control agree |
| [Continuation acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39327259797) | Ordered 1001/gen126 → 1002/gen127 evidence composed and retained |
| [Independent restore values](https://github.com/rax0h/all-that-endures/actions/runs/39330974146) | Fresh downloaded candidate copied, normally opened, actual snapshot and all 25 counters matched; retained inputs unchanged |
| [Independent restore digest](https://github.com/rax0h/all-that-endures/actions/runs/39346200620) | Separate fresh copy/open, actual full digest and all 25 counters matched; retained inputs unchanged |
| [Final restore acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39357369211) | Successful producer and mandatory upload; actual downloaded result authenticated and recursively validated locally |

Year-1001 digest: `57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed`.

Year-1002 and independently restored digest: `2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7`.

The reviewer downloaded the actual final acceptance ZIP, continuation ZIP, restore-values ZIP, restore-digest ZIP, proof ZIP and final diagnostics ZIP. Exact archive sizes/hashes and receipt-member hashes were checked. Each of the three separate observation receipts exactly matches its embedded final-acceptance counterpart. The independently uploaded diagnostic result matches the final uploaded result. The validator recursively checks original checkpoint authority, runtime, common candidate, predecessor, generation, counters, producer and physical receipt hashes.

The 4.481 GB mature database archive was not downloaded again during this review. Its live artifact metadata was checked, and the two completed fresh-runner restore jobs establish actual full download/hash/copy/open behavior. Metadata checks alone are not presented as a new database restore.

## Architecture findings and closure

| Requirement | Review disposition and concrete evidence |
| --- | --- |
| R1: clean retention and cache sidecars | Closed in inspected paths. `persistence_lazy.py` clean eviction drops baseline payload, presence, incarnation, ordinal and identity-label sidecars. `persistence_lazy_budget.py` charges payload/sidecars to shared budgets. Dirty state and externally retained aliases remain explicit costs. |
| R2: lifecycle and mutation exclusion | Closed. `_LazyLifetime.begin_operation` delegates to the actual session lifecycle guard; public operations reject closed backing, reentrancy and active simulation/current-people scopes. Close also checks active operations and pin-release state. Original adversarial R2 checks passed in this review. |
| R3: household and settlement histories | Closed for the required paths. Lazy headers and the counted ordered-sequence authority support local positional edits, duplicate/first-equal behavior, scalar updates without member-history reads, sharing, detach and recovery. The old append-page-only BLOCKED report is historical. |
| Checked identity and one publication authority | Complete mode uses the checked catalog/coordinator and skips the legacy global current-link reader. Participants validate frozen bytes and exact successor pins; they do not commit independently. Recovery reuses the captured hybrid plan. |
| Complete format and conversion | Exact capability-6 features and roots are required; competing/missing authority rejects. Explicit source-preserving copy upgrade retains the compatibility boundary. No implicit conversion on ordinary open. |
| Earlier independent-review repairs | Event-ID copy scrub validates exception semantics. Dirty reconciliation consumes actual pending notifications. The concrete schema inventory accounts for nested histories, generated bounds and imported immutable/input costs. |
| Latest physical-owner repair | The final full suite includes private/unowned backing, shared-child collection, reattachment, failure/lost-ack and omitted-changed-payload witness regressions. The mature saves now succeed on the exact repaired runtime. |

A separate fresh-context architecture reviewer performed source inspection and bounded checks. Its exact command/results are retained in `stage_0_5_final_astra_review_evidence.json`. The review is a focused architecture and evidence assessment, not an exhaustive proof of every source line or every future world.

## Performance and operational limits

The mature fixture is materially slow. These are actual phase measurements, not estimated performance or attributed root causes:

| Year 1002 operation | Elapsed time |
| --- | --- |
| Simulate one year | 3,430.78 seconds (57.18 minutes) |
| Incremental save | 2,923.70 seconds (48.73 minutes) |
| Restore-values runner normal open | 627.96 seconds (10.47 minutes) |
| Restore-digest runner normal open | 1,039.53 seconds (17.33 minutes) |
| Full audit | 4,647.82 seconds (77.46 minutes) |
| Independent full restored digest | 3,699.36 seconds (61.66 minutes) |

These measurements do not support interactive-runtime readiness. Exact ordered preparedness summation deliberately retains an O(H) cold miss with bounded memory. The timings do not establish that this pressure path explains all latency. The receipts reset I/O diagnostics after open, so they do not establish mature ordinary-open I/O counts. Source inspection and fixed-work scale tests support the stated structural bounds; attributing mature open cost requires a scoped profile if performance work is authorized.

Whole audit, digest, conversion, iteration and materializing detach retain their explicit full-state costs. Dirty/external-reference work and current eager topology/packed actions are not hidden in the clean-cache bounds. Maintenance removes at most 256 eligible rows per ordinary operation; fixed table ordering can delay lower-priority cleanup under sustained overload. Existing tests show bounded deletion and quiescent draining, not a universal backlog guarantee at arbitrary write rates.

## Retained artifacts and expiry

| Artifact | Identity and retention |
| --- | --- |
| [Mature saved candidate](https://github.com/rax0h/all-that-endures/actions/runs/39212571079/artifacts/12176425731) | 4,481,162,231-byte ZIP; SHA256 `61497cbf318a51d386cac114f5e93856965a4e94768c89775e520daf99345a70`; currently retained until **2026-11-02 09:10:38 UTC** |
| Saved database member | 30,224,322,560 bytes; SHA256 `02ac8fb650d0b34df47c642c8bacec3490404b6786fe39d9b0af3f02c04d1d13` |
| [Final restore acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39357369211/artifacts/12235349557) | 788,075-byte ZIP; SHA256 `cd40474e7422aa77ca2520e77130feb381f639ff362ae40ab1a60dcb655f41b5`; expires **2026-11-03 02:12:36 UTC** |
| Final acceptance member | `restore-verified.json`, 5,529,032 bytes; SHA256 `f843e4b5870b9d7dbfe6204bf1a85a142ce2552d5e813974d509f98624ae9fe6` |

The mature artifact is retrievable now, with actual successful restore evidence. It is not retained permanently: preserve a verified long-lived copy or extend retention before expiry. This review does not substitute the smaller year-7 artifact for the mature year-1002 deliverable. Immutable workflow receipts intentionally retain `stage_0_5_accepted: false`; final architectural disposition lives in this review, without rewriting historical evidence.

## Integration and next action

PR #14 remains draft/unmerged at `c29e3d06a0c9d219235e2b3f0390271bd1245aea`; it does not yet contain this reviewed candidate. The live main ref at final review was `1c46720c358a26d6b14b6f35121b23e77d3b27de`, later than the older PR metadata base. Integration must re-fetch both refs, reconcile any conflicts and prove runtime/evidence equivalence before promotion. Existing PR mergeability was reported false; this review has not resolved integration conflicts or certified a future merge tree.

The next owner decision is concrete: accept exact arithmetic and the disclosed latency as a **developmental Stage 0.5 baseline**, using the completed mature two-year/restore endpoint, with optimization tracked separately; then authorize preparation of PR #14's reviewed integration. This review recommends that disposition. Unrestricted production/interactive acceptance is not recommended at the measured speeds.

This documentation-only review changes no runtime, tests, workflow, gameplay rule or checkpoint format, launches no long run, and performs no merge. Earlier closeout documents remain historical evidence; their old BLOCKED status must not override this exact-candidate architecture decision.
