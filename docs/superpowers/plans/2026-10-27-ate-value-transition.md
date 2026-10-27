# Native World value-only proof transitions implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline implementation and dedicated branch publication already authorized; one fresh whole-package review.

**Goal:** Make existing native World value-only record saves independent of unrelated retained history, while retaining checked full-audit fallback for structural edits.
**Architecture:** Authenticate changed predecessor bytes through existing content/ordinary roots; validate unchanged reference projections and singleton inline identities, actual query projections, owner witness revisions and backing lease rosters. Reuse the existing five semantic fact roots only when complete owner/group/child scopes, allocator, collection order and inventory cardinalities remain unchanged. Native saves borrow a connection-owned SQL guard so preparation/acknowledgement cannot write unlisted durable data, and adopt an exact manifest/epoch inside a locked metadata check. Admission and uncertain recovery keep full audits.
**Tech stack:** Python, existing SQLite proof writer, frozen native participants, GuardedConnection authorizer.
**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md sections5.2–5.5; existing generation authority contract.

## Global constraints
- Preserve exact raw values, aliases, query semantics, iteration and receipt recovery.
- No generation-only success flag, second publisher/registry, default format7 activation, main merge or endurance run.
- Fast domain: existing lazy registered World record updates excluding Events, with identical declared reference paths/kinds/targets; changed inline identity must have an authenticated singleton group. No additions/deletions, backing value/shape edits, layout changes or allocator/identity changes. Nonsemantic source witness/lease updates are separately checked. Everything else retains explicit full audit.
- Default explicit opener still fully audits and restores canonically. No fast-open or mature performance acceptance claimed.
- Read zero unrelated historical payloads for a real native scalar save at1k/10k/100k retained values; report preparation/save/ack costs honestly.

## Review focus
1. Changed body swaps target or field kind; same path alone must not permit topology reuse.
2. Coherent false query/witness/lease updates, added/removed owner, ordinary layout edits or shared inline aliases must not receive fast certification.
3. Raw SQL/DDL during preparation or acknowledgement, cached prepared writes, replaced authorizers and external writes must not acquire a newly sampled trusted epoch.
4. Lost/partial acknowledgement must resolve the original frozen token/parent exactly once; recovery remains a disclosed full-audit path.
5. End-to-end native1k/10k/100k scalar saves must reject full-audit calls/unrelated history bodies, then reopen with exact logical values and canonical aliases.

## Task1: Changed-value semantic validator and existing-writer reuse
Create persistence_proof_world_value.py; modify manifest guard/stage. Consumes prepared frozen rows and accepted parent component/fact roots. Produces an operation-private value-only decision; stage must independently require unchanged complete structural roots/counts before fact reuse. RED tests: real scalar World transition no full audit; query derivation; reference swaps/shared identities/deletion/layout fallback and rollback. GREEN focused tests; checkpoint.

## Task2: Native bounded save acknowledgement and controls
Extend GuardedConnection with scoped source-write guarding, preserving installed authorizers and readonly fault callbacks; invalidate cached statements at publisher-window boundaries. Extend native proof authority to guard preparation/acknowledgement, permit only existing central publisher/full-audit writes, perform locked manifest/epoch checks for proven value transitions and no-ops, and retain full recovery/fallback audits. RED tests: scalar save rejects full audits/history reads; unsafe SQL at native acknowledgement/authorizer/cache edges; stale epochs and existing recovery matrix. Add actual native scaling driver at1k/10k/100k. GREEN focused and related suites; clean-source matrix checkpoint.

## Task3: Review and publish one bundle
Run all proof/native regressions and actual native matrix. One fresh Astra/high review and one Important/Critical RED→GREEN fix pass; defer minors with explicit costs. Publish one candidate, get CI link once and stop without polling. Full hosted simulation suite remains the acceptance gate.
