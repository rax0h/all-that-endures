# Resumable Proof Genesis Implementation Plan

> For agentic workers: use executing-plans inline; same independent whole-package reviewer closes this group.

**Goal:** Preserve verified preparation across failure and avoid repeating green engine tests.
**Architecture:** Strict offline checkpoint chain around unchanged runtime94267, independent artifact provenance and bounded stages.
**Tech Stack:** Python stdlib/SQLite, existing persistence helpers, pytest/PyYAML, GitHub Actions v4 artifact transport.
**Spec:** docs/superpowers/specs/2026-11-10-resumable-proof-genesis-design.md

## Global constraints

- No changes to simulation/ate_sim or existing monolithic request/workflow.
- Keep mandatory audits/final World/physical validation and exact canonical bytes.
- Same original source29,922,463,744bytes/SHA4a39288b.../year1001/gen126.
- Authenticated green9e6 jobs may be reused only with matching runtime94267.
- No expensive mature dispatch before actual small hosted transport/recovery proof.
- Original source inputs immutable; work on distinct closed copies only.
- One bundled review; resolve all findings including Minor in consolidated register.

## Review focus

- Tampered, expired, wrong-stage/mode/context or wrong-code checkpoints fail before engine work.
- Partial output/publication/transfer failure never replaces a prior good checkpoint.
- Catalog adapter cannot replay unchecked bytes or borrow unrelated copy calls.
- All pre/post-rebase and final proof/physical checks still run after resume.
- Smoke results and green prerequisite jobs never imply mature acceptance.

## Task1: Receipt and artifact trust

Files: simulation/stage_0_6_genesis_checkpoint.py, simulation/stage_0_6_genesis_transport.py;
.github/tests/test_stage_0_6_genesis_checkpoint.py and transport.py.
Interfaces: context/fingerprint creation; validate/seal/load checkpoint; strict parent
stage and DB/data-ref schema; provenance authentication and bounded restoration.
- [x] Write real roundtrip and corruption/order/context/provenance/atomic publication tests; observe RED.
- [x] Implement strict validators, closed-file receipt sealing and authenticated streaming ZIP restore.
- [x] Run new test files and relevant existing artifact/retained controls; commit with raw evidence.

## Task2: Stage execution and recovery

Files: simulation/stage_0_6_genesis_stages.py; .github/tests/test_stage_0_6_genesis_stages.py.
Interfaces: run_stage(stage, input_bundle, destination, context, producer, budget)
returns a sealed local stage result; source_digest/capture/catalog/rebase/
after_digest/proofs/measure/fresh_restore compose only in order. Transport verification precedes use.
- [x] Write small real World chain, source immutability/identity/digest, failed stage recovery,
      retained real audit and strict one-shot transfer adapter controls; observe RED.
- [x] Implement stage functions with existing engine helpers and no algorithm changes.
- [x] Add original field-pair progress wrapper equality and bounded timeout tests.
- [x] Run targeted new/affected harness tests, not unrelated cold archive memory benchmark; commit.

## Task3: Green reuse, launcher and workflow

Files: simulation/stage_0_6_genesis_resume.py, simulation/stage_0_6_genesis_resume_request.json,
.github/workflows/stage-0-6-resumable-proof-genesis.yml, matching .github/tests test files.
Interfaces: gate verifies producer code/runtime and exact green jobs, discovers
compatible latest checkpoint; CLI prepares input/restores once/runs stage/seals
artifact refs; per-stage outputs drive skip/resume in new workflow only.
- [x] Write metadata green-job reuse, failed parent run, wrong runtime/code/artifact and
      workflow stage/skip/timeout/failure retention controls; observe RED.
- [x] Implement immutable data/metadata artifact references and retained original launch.
- [x] Record budgets/disk/expiry gates and reserve upload time; disallow unbounded retries.
- [x] Run complete new harness suite and original retained/benchmark boundary suite.

## Task4: Independent closure and protected CI

Files: existing bounded-genesis/closure.md (one register), resume-repair evidence,
AGENTS.md future expensive-run rule.
- [x] Preserve authenticated42823293423 green/failure evidence and phase timing analysis.
- [x] Same independent reviewer checks whole package and recovery/provenance invariants.
- [x] Close every actionable finding, verify final source fences and no engine change.
- [x] Publish one candidate to existing branch; small hosted smoke only first.
- [ ] Verify real checkpoint upload/download/restart success, then mature dispatch with
      explicit stage boundaries and green reuse; no monolithic rerun.
- [ ] Report actual live run, remaining unmeasured gates and bounded remaining risks.
