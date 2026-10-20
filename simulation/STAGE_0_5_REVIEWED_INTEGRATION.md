# Stage 0.5 reviewed integration preparation — 20 October 2026

This branch prepares the integration requested by the [final Astra review](STAGE_0_5_FINAL_ASTRA_REVIEW_2026_10_20.md). It combines the accepted candidate with the current main branch and preserves the reviewed implementation. Architecture/correctness acceptance is already recorded by Astra; the owner's developmental-release disposition and production promotion remain pending.

## Source boundary

| Input | Commit or tree |
| --- | --- |
| Accepted review | `f4c8ebdc068806e9cac4e7dccc3c2ed8abf45abd` |
| Current main integrated here | `1c46720c358a26d6b14b6f35121b23e77d3b27de` |
| Common ancestor | `5cb2a9cc9832d8e23ce48dd5207cf31efd9680f2` |
| PR #14 head observed before preparation | `c29e3d06a0c9d219235e2b3f0390271bd1245aea` |
| Preserved `simulation/ate_sim` subtree | `76dee76973928dbce72860156feb32f2d7f02f86` |
| Matching full-suite proof source | `4fecd93fdcc5012a404afc07ce166cb7ff422f59` |

Main contributes changes to only two paths since the common ancestor: `docs/LIVING_DESIGN.md` and `docs/research/HUMAN_CIVILIZATIONAL_CAUSALITY.md`. The sole merge conflict is the living document's cohesive-update date. The resolution keeps **2026-10-11**. A fresh three-way merge comparison verifies that every other living-document change merged automatically without manual alteration; the research document exactly matches main. Both the accepted branch's material-life/magic-design additions and main's newer scope/rank decisions are retained.

## Verification

All **377 Python source/test files** have the exact Git blob identities of the green full-suite proof source. The runtime subtree is unchanged. Existing evidence, harnesses, workflow pins, gameplay behavior, checkpoint format and default checkpoint APIs are unchanged from the accepted review. This documentation-only integration does not rerun or reattribute the historical full suite or mature simulation.

Fresh local continuation protocol checks: **87 passed in 46.69 seconds**, covering receipt validation, interrupted receipt handoff, continuation acceptance and independent restore validation. The command and log/JUnit hashes are recorded in [the integration validation receipt](stage_0_5_reviewed_integration_validation.json). The corresponding log and JUnit output are retained alongside that receipt. Markdown hard-break spaces inherited from main are intentionally preserved.

Live GitHub reads also confirmed that the [final restore acceptance](https://github.com/rax0h/all-that-endures/actions/runs/39357369211) and [historical full-suite proof](https://github.com/rax0h/all-that-endures/actions/runs/39177774744) are completed and successful at their original pinned commits.

## Release boundary

This is a separate integration preparation, not an update to PR #14 or main. It starts no endurance run and makes no claim of interactive performance or indefinite future correctness. The documented mature costs and exact ordered preparedness arithmetic remain as reviewed. The owner must still decide whether to accept those limits as the developmental Stage 0.5 baseline before promotion. The rank-rule migration tracked by issue #17 remains deferred gameplay work.

The accepted mature year-1002 artifact and its preservation requirement remain documented in the final Astra review. This preparation neither downloads that 4.481 GB archive again nor claims to extend its retention. The review records expiry on 2 November 2026; the artifact needs a verified longer-lived copy or retention action before then.

After the owner's release disposition, re-fetch main and PR #14 before updating the integration target. If either moved, reconcile against those new refs and repeat source-equivalence verification. The accepted runtime bytes must remain unchanged unless a separately reviewed implementation change is authorized.
