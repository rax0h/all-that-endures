# Collection namespace directory implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, then one fresh independent review.

**Goal:** Construct a complete collection namespace directory in one audited snapshot and read bounded raw namespace authorities.
**Architecture:** Existing ordered radix map and per-namespace roots, fixed immutable descriptor bodies, externally accepted outer certificate. No World selection.
**Tech Stack:** Python3.12, SQLite, pytest.
**Spec:** ../specs/2026-10-24-ate-collection-directory.md

## Global constraints

Namespace/cursor <=4096 UTF-8 bytes; page1..128; metadata budget1..67108864 bytes; exact mandatory external32-byte authority; one owned construction transaction and full audit; no payload reads in bounded directory reads.

## Review focus

- Generation-independent descriptors must retain exactly the same order/counters at a newer accepted generation.
- Coherent source tampering must still disagree with accepted descriptor authority.
- Empty database, declared-empty namespace and absent namespace must remain distinct.
- TEMP shadows, schema replacements and caller codec hooks must fail before arbitrary source use.
- Failure after several constructed namespaces must roll back all new roots and descriptor rows.

### Task1: complete source and raw reader

Files: create persistence_proof_collection_directory.py and test_stage_0_5_proof_collection_directory.py; factor private _construct_collection in persistence_proof_collection.py.
Consumes: existing audited collection construction, OrderedSeekMap, exact physical _state and closed snapshot guards. Produces the three public APIs and dataclasses specified above.

- [x] Write failing tests for complete sorted directory/page, selected absence, empty/declared-empty, old retained pin, forged authority/context, physical/descriptor/node/schema corruption, hook/budget/transaction rejection and rollback.
- [x] Run focused pytest; expect missing module failures.
- [x] Implement fixed immutable bodies and source construction, keeping one transaction and full audit. Add explicit source-wide orphan order/version namespace checks if inherited audit does not cover them.
- [x] Run directory and existing collection/publication tests; expect all pass.
- [x] Run affected proof/store tests; expect all pass. Measure1k/10k/100k archive directory reads, verify no payload reads and bounded namespace probes. Add dedicated tests/diagnostic to existing CI.
- [x] One fresh final independent review; one substantive RED/GREEN fix pass if needed. Record rulings and declined judgments.
- [ ] Publish source/evidence checkpoint and launch candidate full CI without long polling, merge or endurance.
