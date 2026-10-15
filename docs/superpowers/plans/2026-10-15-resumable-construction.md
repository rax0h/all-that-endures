# Resumable Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax.

**Goal:** Preserve completed preparation and commit work across construction interruption.

**Architecture:** A no-op private converter seam exposes existing sealed replay streams and commit/order inputs. Validation-only helpers retain closed database/spool files, authenticate exact typed manifests, and execute commit and order restoration on disposable copies before entering the existing verification pipeline.

**Tech Stack:** Python, SQLite, pytest, GitHub Actions artifact transport.

**Spec:** ../specs/2026-10-15-resumable-construction-design.md (approved October 15).

## Global Constraints

- Keep mature execution paused; preserve the 8 GiB address-space guard.
- No source, retained artifact, receipt or accepted destination overwrites.
- Reuse canonical replay rows without graph-wide reencoding during export.
- Existing original commit, order restoration and verifiers remain authoritative.
- Runtime seam changes require fresh focused, recovery and whole-suite validation.
- Producer provenance is checked through authenticated CI transport, independently of manifest hashes.

## Review Focus

- Foreign or inconsistent stream adapters/counts/seals must reject before mutation.
- Source generation, target identity/pin, typed commit arguments and stage lineage must match.
- Close/cleanup/interruption must not delete a previously completed stage.
- A recomputed transport hash cannot excuse logical row corruption.
- Retrying commit/order restoration must never rerun preparation or mutate earlier artifacts.

### Task 1: Durable preparation and replay

**Files:** Modify simulation/ate_sim/persistence_catalog_copy.py; create simulation/construction_checkpoint.py and simulation/tests/test_construction_checkpoint.py.

**Interfaces:** Private _construction_ready(target,pin,*,workspace,streams,commit); prepare(source,source_receipt,bundle,*,rules_id,context); validate_prepared(bundle,*,context). Seven streams: ordinary, versions, catalog, dependencies, identity, orders, states. Replay descriptors bind stream ID, adapter, count and seal; files are target.sqlite, spool.sqlite and manifest.json.

- [x] Write tests proving preparation stops before commit, exports existing stream bytes, closes writers, survives converter cleanup, preserves source and rejects malformed/foreign/corrupt bundles.
- [x] Run PYTHONPATH=.:simulation pytest -q simulation/tests/test_construction_checkpoint.py; observe missing implementation failure.
- [x] Add the no-op seam; implement preparation and strict manifest/file/pin/stream validation with read-only replay.
- [x] Run new tests and existing conversion/checkpoint focused tests; commit passing task.

### Task 2: Commit and order-restoration recovery

**Files:** Extend the same helper/tests; reuse simulation/complete_upgrade_checkpoint.py unchanged.

**Interfaces:** commit_prepared(prepared,bundle,*,context); restore_orders(prepared,committed,candidate,*,context). Committed manifest binds original preparation manifest hash; restored output exactly matches the existing unverified candidate schema.

- [x] Write tests for commit interruption/retry, order interruption/retry, exact ordinary-upgrade equivalence, corrupt logical rows with refreshed transport hashes, no overwrite, receipt failures and fresh-process CLI.
- [x] Run new tests and confirm the new APIs fail before implementation.
- [x] Implement the original commit on a disposable target copy; save before order restoration. Restore orders separately, preserving both earlier artifacts and producing the existing candidate manifest.
- [x] Run focused conversion, checkpoint and P5 recovery checks; commit passing task.

### Task 3: Fresh-runner proof and validation gates

**Files:** Create simulation/construction_checkpoint_ci.py, .github/workflows/stage-0-5-construction-proof.yml and workflow tests.

**Interfaces:** Dedicated proof branch; authenticated source/prepare/interrupt/commit/orders/storage/catalog/publish/continue/restore jobs. Source contains shared nested identities and counted history. An interruption proof consumes retained preparation, deliberately aborts a real commit and proves earlier bytes unchanged; subsequent jobs reuse preparation.

- [x] Write failing workflow/runner tests for stage dependencies, exact artifact membership and producer checks, bounded job limits, nonfatal diagnostics before mandatory stage upload, and absent mature starts.
- [x] Implement fresh-process stage runner and proof workflow; test locally.
- [x] Obtain one independent whole-change review; repair material findings with failing regressions.
- [ ] Publish exact source and pinned workflow on a dedicated branch; launch bounded proof plus applicable fresh recovery/full suite. Record links/results without waiting in the chat for long gates.

## Execution ruling

Daniel approved the explicit request to implement and test this revised split. Execute inline as offered; this is not another request to approve routine planning. Do not launch mature construction as part of this approval. The only independent agent is the final review required by executing-plans.
