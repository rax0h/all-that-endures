# Raw reference target verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove a selected closed backing reference has one existing, correctly typed, allocated, non-retired target under accepted content/scope/head roots.
**Architecture:** Reuse authenticated version content and scope roots; create no target registry, new publisher or native objects. Check four disjoint incarnation-backed descriptor namespaces plus the sole Event-ID owner-zero binding, validate exact descriptor kind/schema, and prove a live group/retirement state through checked catalog metadata. One pinned snapshot; explicit aggregate/source byte and traversal budgets. Complete outgoing relationships, member extents, canonical identity and full World topology remain separate admission requirements.
**Tech Stack:** Existing Python/SQLite, closed projection codec, content/scope/inventory readers and retirement verifier.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md; docs/performance/proof-map-foundation/NEXT_INTEGRATION.md.

## Global constraints
Existing authorizations: isolated branch, inline execution, routine decisions without approval questions; only fundamental invariant changes escalate. No World activation, main merge, endurance or node collection. Header validation never constructs native mutable objects or uses live registry. Reject unsupported references, allocator/context mismatch, wrong kind, competing target families, missing/empty/retired group, invalid header, source replacement and byte/depth exhaustion. Owner alias links/outgoing graph closure are not established by this point verifier.

## Review focus
- Same incarnation in two backing families is ambiguous even if the selected payload is valid.
- Event-ID target must use the exact owner-zero empty placement and compact descriptor.
- Retired or empty groups with retained descriptor bodies must fail.
- All root contexts and allocator bindings agree before exposing raw results; source schema guards precede inherited reads.
- Aggregate bounds include retirement-path metadata and exclude archive scans; retained-generation reads use exact accepted roots.

### Task1: Point target join
**Files:** new simulation/ate_sim/persistence_proof_target.py; new simulation/tests/proof_target_fixtures.py and test_stage_0_5_proof_target.py; diagnostic/workflow/evidence/docs.
**Consumes:** accepted content/scope/inventory certificate pairs, typed closed reference, fixed pin; existing checked descriptor/schema primitives.
**Produces:** read_reference_target(store,pin,reference,content_authority,scope_authority,inventory_authority,*,max_bytes=2097152,max_source_bytes=1048576,max_metadata_bytes=1048576) -> immutable raw descriptor result, or StoreError. It authenticates the selected target's backing/header and group liveness, not its full children/alias graph.
- [x] Write tests for all6 history kinds + record + native NaN + Event-ID, malformed/competing/missing targets, bounds/hooks/source replacement, allocator/retirement/group liveness, retained transitions.
- [x] Run feature tests RED for missing module.
- [x] Implement closed pointer classification and exact pinned target source join using existing roots. Validate physical root selection and all source bytes; avoid mutable restoration, global scans and second authority.
- [x] Run focused and affected tests, fresh whole-change review and one fix pass with RED regressions.
- [ ] Run clean1k/10k/100k actual archived-store point diagnostic outside bootstrap/audit timings, exact descriptor checks and zero unrelated archive payload reads. Full simulation/final-source scaling on candidate CI.
- [ ] Save concrete evidence and publish candidate, with remaining full topology gates explicit.

Execution: final822 proof tests green; one review/fix pass complete. Pre-fix archive matrix complete, final-source scaling/full suite assigned to candidate CI. Minor test-retention item is deferred in ledger.
