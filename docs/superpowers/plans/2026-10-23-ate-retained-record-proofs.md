# Retained record proof implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans, inline with one final independent review.

**Goal:** preserve exact old ordinary bodies and atomically maintain their content root through the existing save transaction.
**Architecture:** explicit audited bootstrap, immutable body map, root-selected raw reader; private opt-in commit request staged after the last precommit hook, existing recovery protocol.
**Tech stack:** Python, SQLite, existing ProofMap/update_sorted and receipts.
**Spec:** docs/superpowers/specs/2026-10-23-ate-retained-record-proofs.md

## Constraints

- No World selection, format activation, second publisher or collector.
- External expected authority required; current/previous live pin, closed codec, guarded body/metadata transfer.
- Default read limit1MiB; body maximum64MiB. Construction is explicit archive work.
- Root/body/data/head/receipt publication uses one existing commit transaction.

## Review focus

- Late fault hooks changing actual written bytes must not escape root binding.
- No-op, stale pin and acknowledgement recovery must not replay a transition or return an unrelated root.
- Retained source corruption and oversized TEXT/BLOB bodies must fail before unbounded transfer.
- Stale default-writer generations must fail closed; no accidental complete authority claim.
- Source/input spooling and sorted delta uniqueness must remain bounded and correctly rolled back.

## Task1: explicit constructor and retained reader

- [x] Write missing-module RED for framing, current/old bytes/absence, source/node/body corruption, context/index/budgets/hooks/transactions.
- [x] Implement persistence_proof_record.py bootstrap/certificate/raw reader using existing preimages; full verify outside ordinary paths.
- [x] Focused GREEN, commit and checkpoint.

## Task2: actual commit/recovery integration

- [x] Add RED for opt-in commit, actual changed-row binding, no-op/conflict, rollback phases, lost acknowledgement/exact token, default-writer gap, delete/reinsert and frozen/spilled prepared inputs.
- [x] Add private LazyRecordStore.commit request stage after before_commit; implement wrapper and existing resolve_commit composition.
- [x] GREEN focused and affected suite; commit/checkpoint.

## Task3: measured scaling and review

- [x] Driver at1k/10k/100k genuine unrelated ordinary records; separately report full bootstrap, actual point save and raw retained reads. Assert exact old/new results and zero unrelated payload SELECTs.
- [x] One independent review; substantive fix pass RED/GREEN +affected suite. Record every declined scope ruling.
- [x] Publish exact-tree CI candidate with full suite/all existing diagnostics, receipts and pending acceptance. No long polling/main merge/endurance.

Implementation/review/local gates complete; final publication checkbox denotes CI launch, not CI acceptance. Launch receipt/ledger record pending full suite.
