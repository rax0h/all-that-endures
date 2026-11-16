# Retained Catalog Admission Implementation Plan

> Execute inline with executing-plans, then one independent whole-package review. Existing user execution authorization and checkpoint-reuse constraints apply.

**Goal:** reuse the exact old small/mature catalog under the newly qualified locator repair, resuming only rebase.
**Architecture:** strict ordinary compatibility plus a pinned, authenticated one-time catalog-parent/rebase-child context transition. Original receipts are never rewritten.
**Tech Stack:** existing Python/SQLite stage runner, qualified local3.13.5/SQLite3.46.1 and hosted3.12.16/SQLite3.46.1.
**Spec:** docs/superpowers/specs/2026-11-16-catalog-admission-design.md

## Global constraints
- Exact identity/state/history/source/control digest; no general compatibility relaxation.
- No completed prefix or unchanged green suite replay; no mature retry before small hosted recovery.
- Existing disk/phase/transport/publication reserves and target-miss behavior.

## Review focus
- A valid-looking attestation cannot grant authority without fixed committed pins and real producer checks.
- Recursion preserves old chain/context while admitting only rebase's exact cut.
- Changed runtime/engine/helper/control/data/expiry fails before expensive work.
- Interrupted rebase leaves old catalog unchanged and does not publish success.
- New sealed outputs and later validation retain/revalidate the admission cut.

### Task1: qualification and exact admission contract
- [x] Authenticate/download/hash new green artifacts and source/software/jobs; retain original evidence.
- [x] Create fixed contract from authenticated old catalog metadata, exact parent contexts/data refs and reviewed engine delta.
- [x] Record allowed source-control delta and all unchanged authority fields.

### Task2: structural and execution admission
Files: simulation/stage_0_6_catalog_admission.py, its JSON contract, genesis_checkpoint.py, genesis_resume.py, genesis_source_control.py, genesis_stages.py; .github/tests/test_stage_0_6_catalog_admission.py.
Interfaces: structural transition validator, validate_chain(root,value), inspect_prior/restore_prior(root,mode,run,artifact,workspace), attest(root,parent,successor_context).
- [x] RED real-record tests for forbidden cuts, tampered context/chain/contract/source and old producer/data rejection.
- [x] Add the narrow rebase exception with exact attestation; current-root validation remains mandatory.
- [x] Gate/run/transport/seal/control-chain integration; no general compatible() change.
- [x] GREEN real small pipeline, corruption/rollback/retention/equivalence and focused affected tests.

### Task3: review and protected launch
- [x] Update actual qualification pins/fingerprints, commit clean before full quick harness.
- [x] Independent whole-package review; close all findings including Minors.
- [x] Helper publication, explicit old-small-catalog smoke with actual crash/retry/fresh restore; authenticate result.
- [ ] One mature resume request with compatible smoke and old mature catalog; confirm skipped prefix and current stage.
- [ ] Retain exact results and outstanding targets in continuation/closure register.
