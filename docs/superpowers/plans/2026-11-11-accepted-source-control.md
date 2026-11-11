# Accepted Source Control Implementation Plan

> Execute inline in the existing dedicated branch; same whole-package reviewer
> closes this correction group. Preserve raw RED/GREEN evidence.

**Goal:** Reuse the exact accepted source digest and preserve timeout identity.
**Architecture:** Harness-only authentication boundary, unchanged runtime94267,
current actual post-rebase check and existing mandatory audits.
**Tech Stack:** Python stdlib, existing continuation validators, pytest, Actions.
**Spec:** docs/superpowers/specs/2026-11-11-accepted-source-control-design.md

## Global constraints

- No engine, old request/workflow, source bytes or semantic changes.
- Exact accepted member570001bytes/SHA5e54ce0e... and full original chain remain binding.
- No authority from a repository result summary; no claim of a new current digest.
- Actual post-rebase, source/catalog/proof/physical checks remain mandatory.
- No new mature attempt before successful compatible small hosted recovery proof.

## Review focus

- Valid digest with a different DB/producer/rules cannot enter the checkpoint.
- A wrapped alarm is censored timeout; ordinary payload damage is never hidden.
- Imported expectation cannot suppress a mismatching actual post-rebase digest.
- Smoke exercises accepted-control reuse without promoting smoke authority to mature.
- Changed code/context/expiry rejects reuse before expensive execution.

## Task1: Source control and honest timeout

Files: new simulation/stage_0_6_genesis_source_control.py; existing genesis_stages.py
and genesis_resume.py; new .github/tests/test_stage_0_6_genesis_source_control.py;
existing genesis_stages tests. Interface read_accepted_control(path, *, source,
rules_id, authority, source_ref, acceptance_ref, expected_member_bytes,
expected_member_sha256) returns validated digest and provenance. Production caller
supplies only fixed original pins after prepare_retained.

- [x] Add real small accepted receipt positive and mutation controls; observe RED.
- [x] Add real alarm through typed decoder and ordinary CodecError controls; observe RED.
- [x] Implement strict source control; connect mature stage without opening World.
- [x] Implement own-alarm-aware harness recorder without changing shared helpers.
- [x] Verify actual post-rebase equality, refusal of wrong control and raw file preservation.

## Task2: Bounded integration and closure

Files: new workflow/request; existing genesis_resume tests; specs/ledger/register.
- [x] Write cleanup-mode and actual budget-reserve regressions; observe RED.
- [x] Set after/fresh120min compute180min job; skip large cleanup only in smoke.
- [x] Exercise real small accepted-control branch in hosted smoke; fence every dependency.
- [x] Run complete affected harness suite under fingerprint-matched313.
- [x] Same independent reviewer closes all findings in the one closure register.
- [ ] Publish one consolidated smoke candidate, preserve its actual evidence.
- [ ] Only after smoke success, publish gated mature request; report actual remaining gates.
