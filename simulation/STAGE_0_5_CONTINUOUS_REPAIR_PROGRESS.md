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

Task2 foundation: monotonic floor5 support repaired and51 store/failure tests green. See STAGE_0_5_FORMAT_FLOOR_VALIDATION.md. Compact event-ID authority remains pending.

Tasks3–6: design complete, implementation pending. Task7: final integrated source, final architectural review and full-suite launch pending. No production promotion or long run performed.
