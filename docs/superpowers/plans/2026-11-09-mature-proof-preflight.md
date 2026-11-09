# Mature proof preflight implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. Existing user continuation authorization preserves the native workflow and one independent end-package review.

**Goal:** Obtain authenticated mature-file resource evidence for proof genesis.
**Architecture:** Existing retained transport/acceptance joins feed a readonly
SQLite aggregate inventory; a dedicated bounded workflow emits evidence only.
**Tech Stack:** Python3.12, SQLite, existing GitHub Actions transport.
**Spec:** docs/superpowers/specs/2026-11-09-mature-proof-preflight-design.md

## Global constraints

- No ate_sim runtime changes, default opener changes, World decode/step/save,
  migration, main merge, endurance or duplicate full suite.
- Pin current green b9196f9/runtime6ca23be5208e8c198081c73b40806b42a4eb8626 and
  original retained source; never substitute historical source authority.
- One independent package review, every finding including Minor closed here.
- One source+archive+6GiB reserve, <=4096namespace groups,900s SQL inventory,
  35minute command/45minute job bounds and always-published failure evidence.

## Review focus

Wrong authority before SQLite use; borrowed/live source sidecars; BLOB transfer
or decode hidden in metadata collection; interrupted scans misreported complete;
stale config/fingerprint or wrong producer preceding large transport.

## One package: inventory, launcher and hosted request

Files: create simulation/stage_0_6_proof_mature_preflight.py,
.github/tests/test_stage_0_6_proof_mature_preflight.py,
.github/workflows/stage-0-6-proof-mature-preflight.yml,
simulation/stage_0_6_proof_mature_request.json. Update proof-opening hosted
closure and docs/performance/stage-0-6-current/mature-proof-preflight/.

- [x] RED real small SQLite inventory/zero decode/source unchanged and invalid
  hash/size/pin/rules/source/namespace/timeout controls; preserve output.
- [x] Implement inspect_database(path,authority,*,budget_seconds=900,output=None)
  with fixed aggregate SQL, bounded rows, readonly connection and error receipts.
- [x] Test/implement launch(root,config,expected_sha), current-source fence,
  original-authority match, disk floor before prepare_retained, always diagnostics.
- [x] Add bounded dedicated workflow/request fingerprints; run new+retained
  targeted tests, qualified-runtime and Python/YAML/Bash/source checks.
- [ ] Independent whole-package review; resolve every finding, verify exact final
  files, record source checkpoint and publish one benchmark-only request.
- [ ] Inspect hosted mature inventory; choose conversion budget from actual sizes.

Ruling: use the existing isolated sol/durable-proof-map checkout and ongoing
hands-off continuation authorization. No additional design/permission pause is
needed for this necessary read-only precursor to the already selected mature
validation. Missing format/size knowledge must be measured, not guessed as OOM.
