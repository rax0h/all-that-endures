# Execution ledger — plan: docs/superpowers/plans/2026-10-25-ate-target-group-join.md

Baseline: fdbed24, CI40166092367 accepted:3935 full-suite/839 proof tests,19 complete matrices; ZIP digests and head/runtime receipts checked. No World performance claim.

Pre-flight: one task; existing target returns a raw descriptor and group verifier consumes version/group/link/owner authority pairs. Derive those pairs under the same checked content/scope/inventory context; no interface changes to either verifier.

Design choice: compose the existing validators, preserving their physical source checks. A new catalog or broad bootstrap at read time would duplicate authority or restore archive work. Repeated selected-group enumeration is bounded by max_members and explicitly charged; source budget is sequentially partitioned before the final group check. This is an inactive semantic prerequisite, not complete World topology.

Existing dedicated checkout sol/durable-proof-map is reused under prior authorization. Full-suite CI is the acceptance boundary, in accordance with the user's instruction to hand back longer runs.

Task1 runtime: initial26 cases RED (module absent); fixture corrections after inspecting actual canonical link ordering and occurrence column names;29 new cases and83 existing target/group cases GREEN,112 passed17.77s. Later peers/owner radix/link deletion all reject while point-target control passes. Shared7000-byte budget rejects although each component independently fits;8000-byte composite passes.133-member group spans pages and retained canonical anchor changes are preserved. AST/YAML/shell syntax and diff whitespace checks pass. No existing runtime module changed.

Workflow budget: proof job ceiling40min (previous hosted19-matrix job26.5min plus new20th fixture matrix leaves insufficient margin under30min); per-operation VM/memory/source budgets and15min individual command ceilings unchanged.

Final review: Astra fresh context on fdbed24..8329e27; independently29 tests passed. No runtime correctness findings. Regraded sampled-VM telemetry finding Important for acceptance: a falsely labeled upper bound weakens the declared hard work guard. One fix pass: test_scaling_vm_guard_counts_short_statements_and_interrupts RED (new guard absent); implement interval-one interruption in a separate untimed replay, then rerun tests and clean scaling. Initial sampled VM rows are superseded, not accepted upper bounds.

Final review scope decisions:
- Candidate full-suite/hosted acceptance remains CI-owned; no full-suite claim for this candidate before green.
- Previous ZIP authenticity is verified by the author, not independently by the reviewer; retained digests/source receipts are the evidence.
- Incoming owner payload semantics, child extents, recursive closure, kind transitions and World topology remain gated; this raw operation must not admit World objects.
- Native admission, manifest publication, activation, full World performance and endurance remain gated; no runtime behavior was enabled.
- Unselected physical surplus remains full-audit work; selected proof completeness is not a physical inventory audit.
- Python allocation and bounded-fixture timing are reported, not total-process memory or universal latency.
- Existing primitives were traced where used, not independently audited in their entirety; existing proof suite remains required.
- Post-review docs/workflow and the telemetry fix are author-verified; no second review is claimed.

Final fix verified: test_scaling_vm_guard_counts_short_statements_and_interrupts RED→GREEN;30 new runtime/guard tests pass4.60s; final affected suite869/869 passes. Clean final scaling91ddda4 runtimecded2e0:100.97/101.05/122.10ms; zero archive bodies,22 selected metadata payload reads and enforced interval-one VM counts64,366/64,960/65,284. Runtime/driver/fixture hashes checked before retaining evidence. No deferred new Minor findings after evidence guard fix. Full simulation/hosted acceptance remains the next CI gate.
