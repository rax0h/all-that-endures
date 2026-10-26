# Durable selected reference proofs implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans; inline execution and branch publication are already authorized.

**Goal:** Construct durable semantic certificates for bounded selected reference graphs, reuse unchanged facts across generations, and publish changed facts atomically with existing component roots and recovery receipts.

**Architecture:** A generation-independent descriptor records a checked closure digest, semantic summary, and complete content/scope dependency bindings. An immutable map selects descriptors for an explicitly bounded root inventory. The existing unified inventory writer owns successor publication; dependency comparisons use authenticated map paths and never infer unchanged semantics from generation numbers.

**Tech Stack:** Python, existing Typed/World codecs, SQLite, ProofMap.

**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md

## Global constraints

- Reuse the existing publisher, pin and exact recovery protocol. No second object registry or World format activation.
- Fetched/changed bytes remain checked; a retained certificate does not scrub unfetched physical data.
- Preserve raw typed, numeric, NaN, ordering, duplicate and alias semantics.
- Explicitly selected directed closures retain the existing raw closure contract, including its unsupported frozen cycles and unindexed-owner limitation. This is the first of the two planned durable-production milestones, not complete World target inventory.
- Up to 128 selected roots, 8192 dependencies and 1 MiB per descriptor, 4 MiB aggregate descriptors per operation. Each rebuilt closure retains existing shared target/edge/member/child/value/byte budgets.
- No long CI polling, endurance run or main merge.

## Review focus

1. New absent-key competitors, child rows or incoming owners must invalidate a previously valid descriptor.
2. Group verifier source reads and ordinary bodies must enter dependency bindings, including retirement/radix/link nodes.
3. Metadata-only, unrelated edits and no-ops must reuse semantic facts without fetching graph bodies; changed descendants and policies must revalidate.
4. Failure before commit and lost acknowledgement must recover exact old/new component and reference roots together, also after reopen.
5. Descriptor/schema substitution, stale/foreign authority, arbitrary transactions and budget boundaries must fail closed.

## Task 1: Durable checked descriptors

Files: create persistence_proof_reference.py and test_stage_0_5_proof_reference.py; modify reference_closure, target, target_incoming and identity_group only for private checked composition and local dependency capture.

Interfaces: bootstrap_reference_proofs(store,pin,references,content_authority,scope_authority,inventory_authority,*,record_authority); read_reference_certificate(store,pin,certificate,expected,reference). Produce a ReferenceCertificate with immutable map root, fixed selected references, exact component commitments and allocator. Descriptors hold no native objects.

- [x] Write failing tests for summary, mutable cycles, all nine kind coverage, exact raw bits, bounds, selected absence and malformed sources; run and observe missing API failure.
- [x] Capture all physical version/ordinary sources and selected scope dependencies during the existing closure verifier. Persist canonical checked descriptors and generation certificates under owned construction transaction.
- [x] Run focused tests; expect PASS. Commit checkpoint with [skip ci].

## Task 2: Incremental production and atomic publication

Files: create persistence_proof_reference_publish.py; modify inventory private composition; extend same tests and fixtures.

Interfaces: commit_reference_proofs(...,directory_authority,content_authority,*,scope_authority,record_authority,**save_arguments), resolve_reference_commit(same authorities,*,commit_token). Existing public inventory API remains compatible and rejects caller private arguments.

- [x] Write failing real writer tests for changed descendant, added competing descriptor/child, incoming owner and ordinary-body dirt, invalid frozen bit, unrelated updates, metadata-only, no-op, retained pin, three failure seams, reopen and wrong token.
- [x] Compare complete authenticated dependency paths against successor component roots. Rebuild changed closures, share unchanged descriptors and update only changed map leaves. Bind reference generation/parent/token to the same SQLite transaction after all component stages.
- [x] Run reference, closure, inventory/publication and related runtime tests; expect PASS. Commit checkpoint with [skip ci].

## Task 3: Work evidence, review and hosted validation

Files: add scaling driver, workflow entries, results, acceptance and ledger.

- [x] Run 1k/10k/100k unrelated history with unchanged selected graph: metadata-only certificate reuse and unrelated point-edit publication must read zero graph/unrelated archive bodies beyond the actually changed row. Record path work, time and memory; graph reconstruction must remain zero.
- [x] Run all proof tests locally plus related runtime cases; run syntax/whitespace checks. Full simulation suite runs in hosted CI, per user preference.
- [x] One fresh whole-package Astra review, one RED→GREEN fix pass for Important/Critical findings; defer minor findings with record.
- [x] Publish one substantive candidate, obtain next CI link and stop without polling.
