# Existing Lease Proof Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Keep supported small saves on their authenticated proof path after borrowing many existing backings.

**Architecture:** Reuse the mandatory lease validator's accepted predecessor and token checks. Exempt a bounded authenticated existing-lease set only from semantic shape classification; publish the original frozen rows through the existing central transaction.

**Tech Stack:** Python 3.12, SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-10-31-ate-lease-proof-composition-design.md`

## Global Constraints

- Preserve the existing 512-row / 4 MiB semantic limits.
- Existing lease exemption has its own 4,096-row / 4 MiB old-plus-new budget.
- Publish and recover all original changes atomically; validate lease ownership even on fallback.
- No main merge, default activation, endurance or mature benchmark launch.
- Close every review finding in this group, including Minor.

## Review Focus

- Foreign publisher removal/addition must still fail before commit.
- Changed dependency memberships or malformed schema cannot bypass semantic checks.
- Fresh/deleted dependencies retain backing construction/retirement authority.
- Budget exhaustion must retain checked fallback without partially granting authority.
- Lost acknowledgements must resolve the original frozen lease/body transaction once.

### Task 1: Compose authenticated existing lease updates

**Files:**
- Modify: `simulation/ate_sim/persistence_proof_world_value.py`
- Modify: `simulation/ate_sim/persistence_proof_manifest_publish.py`
- Test: `simulation/tests/test_stage_0_6_proof_world_leases.py`

**Interfaces:**
- Consumes: `validate_lease_updates(store, request, versions)` and existing frozen prepared rows.
- Produces: a bounded immutable set of authenticated existing lease `(namespace, typed_key)` markers, or empty when the budget is exceeded.

- [x] Write and run a real native-session regression with over 512 borrowed existing backings, a supported scalar edit, no save audit, exact reopened digest and sharing.
- [x] Return the finite existing-lease marker set from mandatory validation and use it only to partition semantic classifier input.
- [x] Verify foreign tokens, changed memberships, fresh dependencies, budget fallback and interrupted publication/recovery with real stores.
- [x] Run affected lease/value/tail/insertion/forest/native-session tests and complete generated-world continuation.
- [x] Obtain one independent whole-package review and close every actionable finding.
- [x] Refresh runtime launch pin, run exact harness checks, preserve raw evidence and publish one bundled validation run for this runtime package.

Publication starts the existing full/proof workflow. Hosted completion is a separate pending gate; no mature performance or Stage 0.6 completion is claimed.
