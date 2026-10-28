# Execution ledger — plan: docs/superpowers/plans/2026-10-25-ate-target-incoming-payloads.md

Baseline9d78631, CI40171262930 accepted:3965 full-suite/869 proof tests,20 complete matrices. Artifact ZIP digests, source head/runtime and new target/group driver/fixture hashes verified. Hosted target/group107.33/119.10/130.22ms; zero archive bodies. No World speed claim.

Pre-flight: existing target-group byte budget ends at complete group verification. Extend the private group source to charge its existing bytes into a parent and expose the private checked-snapshot body of target_group. Both public APIs retain existing transaction gates. Inert payload projection consumes raw accepted bodies; no native restoration or separate registry. Ordinary body authority is an explicit optional fourth pair, required when ordinary bodies are selected.

Design choice: a selected target's group determines bounded owners; scan those bodies to prove exact target-reference projection, rejecting extra aliases in fetched bodies. This does not discover entirely unindexed owners elsewhere or establish whole-World topology. Existing schema/adapter allowlists are reused; unsupported inline native aliases or inline key/set pointer routes fail closed. Complete child extents and namespace domain policies remain separate contracts.

Task1:35 initial tests RED (new modules absent); implementation and closed decoder followed. The owner commitment comparison now reuses the existing lazy-payload framing and ordinary record checksum contract, rather than a plain SHA assumption.40 incoming cases GREEN7.67s, including actual-record schemas/events, caller registry poison, exact selected-target alias projection, ordinary retained bodies, budgets, single body fetch per owner and one snapshot. New scaling guard case RED (new driver absent), then GREEN. Combined focused new/existing group and guard suite121 passed27.63s. AST/YAML/workflow shell syntax and whitespace pass. Private parent budget charge has no public API change.

Final verification:910 proof tests passed169.79s. Clean6f7b7fa archive matrix complete:164.22/147.23/204.15ms; zero archive payloads; source runtime/driver/all3 fixture hashes verified. No runtime changes after source checkpoint.

Final review: fresh Astra; no Critical/Important findings; independently71 focused tests passed26.93s.
Final: minor (deferred): reuse already checked Event-ID body across target and incoming phases; both reads are authenticated and charged. Narrow the per-owner single-read guarantee to the incoming phase, with no operation-wide raw-body-cache claim.

Final review scope decisions:
- Full simulation/hosted CI acceptance remains the next green gate; only proof/component readiness is claimed.
- Clean scaling was author-run and hash-verified, not independently rerun by the reviewer; results describe this bounded fixture and Python allocation, not World speed or process RSS.
- Previous ZIP/source receipt authenticity was author-verified; no independent reviewer retrieval is claimed.
- Post-checkpoint documentation edits are author-checked; no second code review is claimed.
- Native admission, mutable alias identity, namespace field-domain policies, child extents, recursive closure, complete inventory/unindexed owners and activation remain gated; enabling native behavior before those contracts would be unsound.
- Review authorizes candidate CI only; merge/production/World readiness remain unclaimed.

Current disposition: [consolidated cleanup register](review-cleanup/register.md) tracks closure of these historical Minor findings.
