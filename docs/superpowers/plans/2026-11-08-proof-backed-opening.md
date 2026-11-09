# Proof-backed World Opening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, task-by-task. Steps use checkbox syntax. Existing user authorization selects inline implementation and one independent whole-package review.

**Goal:** Open an externally accepted complete World through authenticated selected reads, without a full-history admission audit.

**Architecture:** Bootstrap the original accepted head before World decoding, bind the composed seven-root World context, and reuse canonical restoration with active native readers. Keep the existing registry/publisher and audited/default opener.

**Tech Stack:** Python3.12, SQLite, existing proof maps/seek roots; qualified local system-derived runtime.

**Spec:** docs/superpowers/specs/2026-11-08-proof-backed-opening-design.md

## Global Constraints

- Explicit API only; preserve existing audited/default behavior and format7.
- Require complete seven-root scope/v4 context and external32-byte commitment.
- No main merge, default activation, new format default or endurance run.
- One independent whole-package review; all Important and Minor findings close here.
- One bundled hosted full/proof gate after all local checks.

## Review Focus

- Initial constructor/pin/snapshot metadata cannot be decoded before accepted binding.
- Six-root compatibility remains audited; missing rank authority cannot mean empty.
- Original pin/epoch/components survive callback/concurrent/cleanup transitions.
- Failed restoration releases only owned operational resources without auditing history.
- Dormant cold corruption rejects when selected; no unrelated body scan during open.

## Task1: Accepted bootstrap and early native authority

**Files:** Create simulation/ate_sim/persistence_proof_open.py; modify persistence_proof_world_session.py, persistence_lazy_store.py and persistence_lazy.py in that directory. Test simulation/tests/test_stage_0_6_proof_open.py.

**Interfaces:** New open_proof_world_session(path, *, rules_id, expected_commitment,
paged_household_members=None). Extend _WorldProofAuthority(expected, *, proof_only=False).
Private persistence_proof_open.open_store(path, authority, *, rules_id) returns the
same LazyRecordStore with a verified provisional opening manifest. guard_head(store)
performs raw metadata budget/source checks before provisional head reads. Native
admit(pin) loads/composes the component context; proof_only skips full World audit.

- [x] Write red cases: new API opens with _audit_world/verify_all/catalog scrubs forbidden; six-root rejected and audited opener accepts it; wrong digest/rules/format/head/oversized metadata fail before decoding and leave no pin/transaction.
- [x] Run those cases; preserve actual red failures and negative controls.
- [x] Implement bounded raw metadata/manifest bootstrap on the existing guarded connection. Compare accepted encoded head before codec decode, protect pre-admission head reads and bind components before layout selection. Require seven scope roots.
- [x] Run the cases green, including parent/child fresh reopen and no-op/scalar save through the unchanged publisher.
- [x] Commit the coherent local source checkpoint with skip-ci.

## Task2: Restoration context, identity and failure ownership

**Files:** Same source module boundaries and test file; extend existing session tests only if the exact API contract requires it.

**Interfaces:** Reuse existing canonical restoration. Keep current-tail identity alias
restoration inside the owned opening-read scope for this API. A private opening
abort helper releases the exact owned lease using bounded operational authority;
no fallback full audit and no forged World head decoding.

- [x] Add red cases for selected coherently forged record/layout/descriptor, original pin/epoch drift during decode/restore, same/external writes, and failure on the last restoration operation.
- [x] Assert shared-history/current-tail aliases, stable ordinals, expected mutable tail bounds, no leaked transaction/pin/readers on healthy-source injected failures, and preservation of the original error.
- [x] Capture the immutable original opening context and recheck it before exposure and after snapshot cleanup. Keep complete-format admission replay rejection and private publisher capability boundaries.
- [x] Implement exact owned-pin abort cleanup with no body reads/retention work. Reject hostile operational schema/state rather than publishing or decoding a forged head.
- [x] Run focused cases plus existing metadata/native source/order/query/identity/roster/rank and recovery regressions once per coherent source revision; record results.

## Task3: Bounded cold work, complete continuation and review

**Files:** Test file above; .github/tests/run_proof_real_year_probe.py; matching launcher tests; .github/workflows/stage-0-5-proof-map-validation.yml; docs/performance/stage-0-6-current/proof-opening/.

**Interfaces:** Extend run(output, *, rank_proofs=False, proof_only=False) and CLI
--proof-only; proof-only requires --rank-proofs. Both parent and fresh-child runs
use the selected explicit API. Preserve the existing audited default and receipt
provenance; proof-opening audits must be counted/forbidden as well as save audits.

- [x] Add/run cold controls: archived sealed segment remains unread during opening, corrupted dormant body rejects on first access/verify_full; larger unrelated history does not add body reads. These arrived after the missing-API RED/bootstrap; retain an audited positive control for the new read counter rather than claiming a separate cold-control RED.
- [x] Add/run launcher checks for proof-only/rank eligibility and actual fresh-child mode propagation; preserve every eager/source-hash/fresh assertion.
- [x] Run selected broader regressions and static workflow/source checks, then commit clean source before the generated-year probe.
- [x] Run one complete original-driver proof-only generated year on the qualified runtime, with eager/fresh/source-immutable/zero-opening-audit assertions. Record raw and diagnostic phase times without mature claims.
- [x] Request the one independent whole-package review. Promote concrete reproductions, resolve every finding including Minor, and verify the final runtime source.
- [ ] Publish source/evidence with exact tree equivalence on the dedicated branch; launch one combined full/proof gate. No default/merge/endurance action.
