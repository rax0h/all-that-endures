# Forensic repair implementation plan

> Execute inline via superpowers:executing-plans; bounded package-level independent review.

**Goal:** obtain trustworthy current-engine mature evidence without losing the authenticated inputs.
**Architecture:** preserve source carriers first; repair actual harness/runtime contracts; gate mature jobs on full tests and real transport smoke, retaining compatible closed checkpoints.
**Tech Stack:** qualifiedPython3.13.5/SQLite3.46.1 locally; pinned hosted software; existing Python/SQLite and GitHub workflows.
**Spec:** docs/superpowers/specs/2026-11-15-forensic-repair-design.md

## Global constraints
- Exact identity/state/history/source/acceptance authority and deterministic continuation.
- Mature10sopen/2ssave/1swarm; no default/main/endurance action.
- No expensive prerequisite reconstruction or repeated compatible green stages.
- No public fixture release or destructive asset replacement.

## Review focus
- Partial uploads, collisions, corrupt/truncated assets, source metadata drift and retry.
- Draft-only access, credentials not forwarded/logged, fixed repository provenance.
- Source/control/runtime pin mismatch rejected until semantically reviewed.
- External writes after audit, exact recovery, callback/codec and lease refusal.
- Closed output preservation through later timeout/cleanup/publication failures.

### Task1: protect fixtures
Files: simulation/stage_0_6_preserve_fixtures.py, .github/tests/test_stage_0_6_fixture_preservation.py, .github/workflows/stage-0-6-fixture-preservation.yml, preservation request/evidence.
Interface: preserve_file(api,release,source,identity,output,chunk_bytes) returns a fully round-trip-verified immutable archive manifest; no authority to open a World.
- [ ] RED fake-transport splitting/retry/corruption/duplicate/draft/mismatch gates on real local bytes.
- [ ] Minimal bounded draft asset implementation; GREEN and capacity/producer controls.
- [ ] Independent whole-package review, all findings closed; actual hosted small smoke before large copy.
- [ ] Preserve both original archives, source provenance and tested restoration path; report only verified completion.

### Task2: repair harness and measurement path
Files: source-control/compatibility, native audited recovery, benchmark runners/tests/configs, gate workflows and evidence.
- [ ] Reproduce complete.github/tests; qualify subprocess PATH, preserve first environment failures.
- [ ] RED source pin/audit epoch/benchmark support failures with actual cause evidence.
- [ ] Smallest compatible repairs, meaningful regressions, current engine and supported workflow pins.
- [ ] Full.github/tests quick required gate; one selected affected engine battery and one independent whole-package review.
- [ ] One bundled hosted proof/full engine gate if engine changed; reuse unchanged green otherwise.

### Task3: reproducibility and mature execution
- [ ] Explicit public baseline/candidate/input configuration; include or cross-reference raw baseline save profile and honest host-load evidence.
- [ ] Authenticate latest exact green, compatible hosted recovery smoke, source capacity and stage/output budgets.
- [ ] Launch one protected current-engine mature measurement after gates; retain closed stages and saved generation before fresh validation.
- [ ] Record actual/censored open/first/save/warm/fresh timings and exact year1002continuation; choose next optimization only from this evidence.

### Task4: findings and closure
- [ ] ReconcileF1–F18/N1–N6 with evidence, owners, severity/contract and acceptance; retrieve001 if available before judging under-specified items.
- [ ] Close the authorized work with measured gates, explicit remaining blockers and durable handoff; no stage-complete claim from a green badge.

Ledger: docs/performance/stage-0-6-current/forensic-repair/progress.md.
Baseline enginefd20cf17; green43670981744 newly observed successful, artifact authentication still required. Per-file and phase budgets are preflighted before launch; preservation has no World constructor. Preserve compatible completed test receipts; reserve publication/cleanup before starting the next expensive unit.
