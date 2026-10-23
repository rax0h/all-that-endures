# Generation authority implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans for inline implementation; one fresh final review.

**Goal:** bind immutable generation roots to exact source and recovery identity without activating World proof reads.
**Architecture:** closed binary manifest; bounded checked SQLite reader; pure successor and retention-root checks. Reuse existing receipts and live pin snapshots.
**Tech Stack:** Python, SQLite, SHA256 framed commitments, pytest.
**Spec:** docs/superpowers/specs/2026-10-23-ate-generation-authority.md

## Global constraints

- No new publisher/registry, format activation, World bypass or collection.
- External expected digest mandatory; canonical strict binary fields;2MiB aggregate cap.
- Current/previous live pin only. Old ordinary body availability remains gated.
- Exact existing receipt binding, closed codec/preflight, no unrelated payload bodies.

## Review focus

- Canonical alternate binary encodings or bool/int aliases must reject.
- Historical head/receipt availability must not be overstated.
- Missing/conflicting protected generations must fail closed without an ancestor scan.
- Source reads must guard SQL types/lengths before transferring blobs.
- Semantic root validity and publication obligations must never be implied by manifest hashing.

## Task1: canonical manifest and successor binding

- [ ] Write tests with independent framing vectors, round trip, field mutation and malformed types/lengths/parent/receipt/token/context.
- [ ] Run RED for missing module.
- [ ] Implement persistence_proof_generation.py closed types/codec and adjacent successor validation.
- [ ] Run all task tests GREEN, then commit.

## Task2: retained source and protected-root inventory

- [ ] Add test-only manifest-table construction and real source fixtures. Write RED for source corruption/context/budgets/retained head/receipt, and protection conflicts/missing roles.
- [ ] Implement read_generation_manifest and retained_roots; no writer or schema constructor in production.
- [ ] Run focused/affected tests GREEN; commit and checkpoint GitHub.

## Task3: final review, receipts, exact-tree CI

- [ ] One independent branch review; substantive findings get one RED/GREEN fix pass and affected suite.
- [ ] Add dedicated tests to existing CI; preserve full suite and all9scaling matrices.
- [ ] Record source/evidence, update NEXT_INTEGRATION, publish candidate/launch receipt. Full suite acceptance pending until authenticated. No long polling/endurance/main merge.
