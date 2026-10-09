# Continuous repair ledger — plan: simulation/STAGE_0_5_CONTINUOUS_REPAIR_PLAN.md

Base: 5391b377180fb230ce4b80cbfd5e69d1997111aa. Production PR #14 unchanged at c29e3d06a0c9d219235e2b3f0390271bd1245aea.

Task 0: complete — read-only domain investigations finished; separate worktrees created. Shared-wallet missed-routing regression observed red: four failures in 0.29s, log `/workspace/scratch/c3a830e86cea/unloaded-alias-red.log`. No production implementation changed at this point.

## Preflight interface scan

| Tasks | Shared files/interface | Resolution |
|---|---|---|
| 1 / 2 | lazy_store.commit and format floor | Task 2 owns floor 5; root coalesces monotonic implementation. |
| 1 / 3,4,5,6 | persistence_lazy binding/identity maps and save publication | Separate worktrees; root integrates sequentially with touched-group routing as authority. |
| 2 / 3,4,5,6 | compact codec/canonical/detach allowlists | Concrete allowlisted types only; combine explicit entries and verify cross-family gates. |
| 3 / 6 | checked limited membership query | Common signature in spec; coalesce store implementation without dropping checks. |
| 4 / 5 | property typed histories | Task 5 provides primitive interface before Task 4 integration. Belief/practice/adoption work proceeds independently. |
| 5 / 6 | infrastructure provenance | Task 5 provides typed list interface; scalar record work proceeds independently. |
| 1 / 5 | incarnation-owned child backing and peer routes | Existing occurrence/P2C authority remains sole sharing authority; no duplicate identity registry. |
| 3 / 5 | ordered sequence mechanics | Household sparse positive-ID/rank pager remains specialized; generic typed list handles append-bounded histories. |
| 1 | tests vs implementation | Explicit raw payload copies, mutation-side/reopen-order, equality/identity replacement and old-pin coverage required. |
| 2 | tests vs implementation | Range verified from actual representatives; native fallback, protocol and atomic publication covered. |
| 3 | tests vs implementation | Separate history axes; duplicate occurrence order and sparse removal checked; preparedness arithmetic unchanged. |
| 4 | tests vs implementation | Strict thresholds/insertion order/snapshot timing and long-list byte bounds checked. |
| 5 | tests vs implementation | Child lists/maps/sets authoritative, aliases checked, no independent commits. |
| 6 | tests vs implementation | Genuine active growth separated from history; bounded predicate and legacy memberships checked. |

Ruling: Execute isolated unit work continuously and perform one final combined architectural review — the owner's latest instruction removes per-step review/approval stalls — cost if wrong: integration defects require rework before final CI; focused verification and final review remain mandatory.

Ruling: Preserve ordered native preparedness arithmetic during independent repairs — no reviewed exact bounded replacement exists yet — cost: this ordinary path remains a disclosed proof blocker until resolved; storage completion must not falsely claim that scan is bounded.

## Current status

Tasks1–6 were dispatched to isolated worktrees. Workers became unavailable after a reported usage limit; only the event-ID design and two capability tests were written before shutdown. Root preserved those partial artifacts and continued inline. Do not redispatch completed investigations or claim worker implementations exist.

Task1 correctness slice: shared-owner routing repaired. Nineteen regressions green;111 affected tests plus2 subtests green; P5 3+4+3 seed843000 passed. See STAGE_0_5_SHARED_OWNER_ROUTING_VALIDATION.md. Bounded discovery/versioned P2C witness work remains pending.

Published checkpoint: fa86f8e1e2ef9c17ee63ee2d67f91c9086c617e6, exact tree5518c99be866de8f6dd1f5c1d716617e7549b9c8 (matches local ddf4c99). All17 modified/new blobs and the full tree were compared exactly before a leased update of the repair branch. CLI push lacked credentials; the configured GitHub connection published the same checked source. PR#14 remains c29e3d06a0c9d219235e2b3f0390271bd1245aea.

Task1 reverse lookup foundation: implemented checked covering index/API, explicit source-preserving copy upgrade, old-pin and corruption validation. Reverse/store/failure gate:64 passed in5.86s. See STAGE_0_5_REVERSE_IDENTITY_VALIDATION.md. This is not yet ordinary-open/save integration.

Task2 foundation: monotonic floor5 support repaired and51 store/failure tests green. See STAGE_0_5_FORMAT_FLOOR_VALIDATION.md. Compact event-ID authority remains pending.

Task2 runtime component: concrete EventIdSet facade implemented;47 protocol/component cases cover exact range proof, fallback representatives, native conversions/operators, guarded changes, failing iterable partial mutation, iterator size changes, materialization memo and500 deterministic mixed operations. See STAGE_0_5_EVENT_ID_FACADE_VALIDATION.md. World disk/tracker/codec/save/recovery integration is still pending; existing Worlds have not switched representations.

Task6 correctness slice: current touched-membership candidates now replace obsolete per-key markers and prune empty buckets, rather than retaining lifetime status edits. Scaling1k/10k edits atD=1, shared candidate buckets, delete and failure/retry verified. See STAGE_0_5_TOUCHED_MEMBERSHIP_VALIDATION.md. Application bounded threshold and remaining scalar families are still pending.

Latest slice combined gate:143 passed in10.30s across facade, institution/scalar, unloaded alias, reverse identity, store and store failures. Latest P5 seed843000,3+4+3 paged households passed=true; finalyear10/events439 and exact control finaldigest3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e. Raw evidence continuous-repair-p5-final-slice.json retained for later CI upload. Diff whitespace check clean. No full-suite launch or final architecture sign-off yet.

Published preceding checkpoint: `6e33545dd3e854f6b649dc40accc272031f651d6`, exact tree `70ed7d7d7d5dfc803221681203453690935a2e0f`, matching local `f7556d3`. Continue publishing with a leased update; do not reset the divergent local/native commit graphs.

Task2 storage integration checkpoint: compact conversion/open/tracker/save/recovery, native codec/canonical/freeze and portable detach are connected. Range and fallback share one public facade, one hybrid commit and frozen recovery evidence. Tested wallet/eager set-field aliases use checked authority references and detach retains sharing. Numerical 1k/10k and sealed 2048/20480 gates pass. See `STAGE_0_5_EVENT_ID_INTEGRATION_VALIDATION.md`; its remaining compatibility/alias obligations prevent a claim that the whole Task2 or combined migration is complete. Next inline work: checked limited membership queries and the actual inquiry failed-application threshold consumer, with explicit legacy capability handling.

Task2 final checkpoint combined verification: 162 passed in 36.52s across event-ID integration/facade, adapters, tracking, currency, lifecycle and unloaded alias routing. P5 rerun after conversion report correction passed with destination format 5 and the same exact control digests. No full-suite or final reviewer invoked.

Tasks3–5 and remaining Task6 migrations: design complete, implementation pending. Task7: final integrated source, final architectural review and full-suite launch pending. No production promotion or long run performed. Resume inline implementation from these exact checkpoints; do not repeat completed investigations or initial green ownership CI.

Published event-ID checkpoint:`3cf9f5ec8f16e8af7a9d280fc8faa79c31fd5ea3`, exact tree`1ed0261b59eb6b64f45eb744271eb7797d569cc3`, matching local`e715f8d`. Fourteen blobs and the full tree were checked before a leased repair-branch update; PR#14 remained unchanged.

Task6 application predicate checkpoint:checked limited occurrence queries, complete converted branch/passed authority, bounded actual inquiry consumer and explicit legacy fallback are implemented. Current-source focused gate155 passed in37.99s; P5 seed8430003+4+3 passed with the exact eager-control digests. See`STAGE_0_5_BOUNDED_APPLICATION_QUERY_VALIDATION.md`. Current-source final full suite and final reviewer remain pending. Continue inline with remaining scalar families and nested-history integration.

Published application-query checkpoint:`344d3ad345c7fe6ff610ac86cf1caebeaf21cc8a`, exact tree`f648ec283addfb4cdd924be425ecfcc70eea9e81`, matching local`533ee26`. All11 changed blobs and the complete tree matched before a leased update. PR#14 remained unchanged.

Tasks4/6 scalar checkpoint:conflict/inquiry/threat records, independent resolution cells and belief cells now have checked lazy conversion/open and complete hybrid save/recovery/detach seams. Shared record routing, native numeric predicate equality, premature detach rebindings and recovery diagnostics regressions were observed red and repaired. Combined gate126 passed in58.93s; new family group23 passed in24.01s. P5 seed8430003+4+3 passed with the exact eager-control digests. See`STAGE_0_5_SCALAR_FAMILY_VALIDATION.md` for actual bounds and remaining proof obligations. Continue inline; this does not complete Tasks4/6 or authorize a final full-suite launch yet.

Published scalar checkpoint:2903af875f2844ae822907b78e8936e57b4dcb8e, exact tree807152e92875710c978923fa48f149b4314e8d83, matching localb8bd8d2. All8 changed blobs and the full tree matched before a leased update. PR#14 remained unchanged.

Tasks4/5/6 typed-list checkpoint:property headers/both histories and infrastructure headers/provenance now have complete conversion/open/hybrid-plan/identity/ack/recovery/detach seams. Raw wallet/eager aliases and whole-Property wallet copies preserve identity and route current edits, including after the last lazy owner is replaced. Native tuple collision, sort callbacks, uncertain reads, detach and no-op dirty-child retention reds were repaired. Final expanded history group31 passed in14.54s; after final journal pruning,73 affected tests passed in58.15s; preceding broader gate195 passed in89.26s. Final-source P5 seed8430003+4+3 passed with exact control digests and portable lanes. See STAGE_0_5_TYPED_HISTORY_VALIDATION.md for measured bounds and remaining obligations. Next inline work extends this same manager to typed maps/sets and their practice/institution/divinity consumers. Final combined review/full suite remain pending.

Published typed-list checkpoint:97fb63f1c666e1e7d89bb70dc883fac100cca59e, exact tree1edf0157fe4daa67ddbfb5d5af9ec0b95ae766b6, matching local7ce3e63. All14 changed blobs and the full tree matched before a leased update. PR#14 remained open/draft/unchanged at c29e3d06a0c9d219235e2b3f0390271bd1245aea.

Tasks4/5 typed map/set checkpoint:checked incarnation-owned scalar entries, practice traits, institution/branch collections and God/GAB/Church collections are connected through the same hybrid manager. Native numeric key representatives, guarded no-ops, iterator/reinsertion semantics, current shared wallet paths, replacement, recovery and detach are covered; acknowledgement now checks entry query witnesses. Combined gate161 passed in88.04s; divinity/canonical/archive gate12 passed in9.69s; final codec/identity/freeze cases2 passed in0.11s. Final-source P5 seed8430003+4+3 passed with exact control digests and portable lanes. See STAGE_0_5_TYPED_MAP_SET_VALIDATION.md. Next inline work:adoption scalar queries and their exact threshold/insertion-order consumers, then remaining community/token selection and household/identity proof work. No final reviewer/full suite or production promotion yet.

Published typed map/set checkpoint:1d06e8cd7396ef33d6c8b151836d9f92048ab8fa, exact tree1ce8862a30d018dadb078cd1f014418b18b4cf94, matching localc688282. All19 blobs and the full tree matched before the leased update. PR#14 remained unchanged.

Task4 adoption checkpoint:independent cells, five strict ordered threshold queries, independently checked versioned bucket counts/settlement markers, frozen auxiliary save evidence and actual culture/migration/trade/institution consumer seams are connected. Explicit insertion memberships preserve order across sorted write batches. Meaningful missing-query acknowledgement and no-op dirty-journal reds were repaired. Broader verification exposed the packed-agency surviving callback owner after rolling trim; preparation now uses the eager tracker’s current owner projection and skips the whole packed marker. The existing permanent regression passes. See STAGE_0_5_ADOPTION_QUERY_VALIDATION.md for measured gates and remaining obligations. Continue inline with community/token minimum selection and household/identity work; final combined Astra review/full-suite launch remain pending.

Final-source adoption gate:16 passed in11.31s after the packed-owner fix; final-source P5 passed with the exact control digests and portable lanes. Diff whitespace check clean.

Published adoption checkpoint:3b3d81a29126ef9dc911779339fe5d66adc1b941, exact treecd55bbb127655d31efe0000b06fdbaac9394d599, matching local0a82a36. All10 blobs and the full tree matched before the leased update; PR#14 remained open/draft/unchanged.

Task6 community/token checkpoint:concrete lazy IndexedRecord families and checked linked minimum buckets are connected to local_root, diaspora and available_token. Native ID order (independent of key), original insertion ties, inactive roots and dead-person tokens remain authoritative. Exact numeric rank projections use existing query indexes for bounded neighbor discovery; linked metadata validates gaps. No new tables or open-time upgrades. Frozen auxiliary evidence shares the existing hybrid commit, with query/link acknowledgement checks, old-pin visibility and current overlay merging. Missing-query acknowledgement and repeated no-op dirty-history regressions were observed red and repaired. Final-source focused group23 passed in52.78s. Broader preceding source group75 passed in105.43s; separate unloaded-alias group19 passed in3.85s; earlier business/lifecycle/adoption group72 passed in52.05s. These overlap and are not a unique total. Final-source P5 seed8430003+4+3 passed with exact control digests and portable lanes. See STAGE_0_5_MINIMUM_SELECTION_VALIDATION.md. Continue inline with bounded identity discovery/versioned P2C witnesses, household outer/sparse histories and remaining broad protocol/alias/corruption proof. Final combined Astra review/full suite are not yet invoked.


## Household historical access and tail-delete follow-up (October 8, 2026)

These checkpoints are downstream of the accepted ownership repair and the Task 6 minimum-selection work. No production PR #14 promotion, full-suite release gate, or endurance capture was performed.

- Living household selection: current-person candidates are checked against authoritative versioned member occurrences; native sequence order and repeated member IDs remain intact. Migration and household splitting are routed through this selector. Focused gate **59 passed** with P5 3+4+3 green at tested source `00a0c693ed3e7a0d6b34241b230c564c2d6d7f73`, workflow `37870946768`.
- Owner-scoped membership index: new length schema 2 publishes `owner_member` memberships in the same page changes, avoiding a global per-member query across unrelated households. Existing schema 1 snapshots retain the checked legacy query without an implicit ordinary-open upgrade. Tests cover H=1k/10k independent households, old pins, duplicates and dirty/reopened pages. **63 passed**, P5 green at tested source `63400fb02841434c1d7b0e96fcc0d0e5cc4fb595`, workflow `37871823902`.
- Death, inheritance and household deactivation: `mortality.kill`, `Simulation._die` and `Simulation._demography` now use the current-person/checked-sequence selector instead of decoding every dead historical member. Eager/lazy parity, exact duplicate survivor effects and 1k/10k fixed-current load bounds are verified. The initial gate had one *test-ordering* failure: a full-world digest was measured before the ordinary-load bound. Measurement was moved before explicit materialization. Corrected final-source gate: **70 passed**, P5 green at `53575cfeb38fc20604e6e575628f682caa3fb70c`, workflow `37873110356`.
- Tail deletion: `LazyHouseholdMembers.__delitem__` updates just the final checked page and sequence length when removing its last element; `remove(exact_positive_int)` selects the first occurrence through checked owner-qualified occurrences before deleting. Earlier duplicates and unusual Python equality probes retain native behavior. Tests enforce bounded I/O at H=1k and H=10k, retained old pins, duplicate order, canceled append/pop and exact reopen. **44 passed**, P5 green at `7917a27498d927b5ad314c33f81e58bb2a622684`, workflow `37873256590`.

**Still unresolved / release blockers:** `_activate_household_pages` eagerly visits the full outer household collection on ordinary open; `_household_page_changes` and `_household_member_identity_changes` revisit full eager/paged owner inventories during small/no-op saves; arbitrary non-tail member removal still repacks history, requiring sparse rank/select pages; `Settlement.households` remains an eager growing list. Task 1 still requires bounded current identity discovery and versioned pinned P2C witnesses. `Simulation._pressure` preserves exact ordered floating-point preparedness arithmetic across historical household IDs and remains an explicit ordinary-path cost exception until an exact alternative or approved semantic change exists. Final cross-family broad regressions, integrated P5/recovery, single release full-suite gate, one independent architectural review and separately authorized endurance evidence have **not** been completed by these focused checkpoints.
