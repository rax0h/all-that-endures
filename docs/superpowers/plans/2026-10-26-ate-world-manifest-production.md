# Audited World manifest production implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Inline execution and dedicated branch publication already authorized.

**Goal:** Produce all seven manifest roots from one explicitly audited complete World snapshot and atomically publish/recover successor manifests through the existing writer.

**Architecture:** Reuse the established complete-format catalog/graph/type audit as construction authority. A checked, source-preserving copy creates a new store identity at generation0, retaining logical position, IDs, ordering, history, raw numeric values and aliases. Never fabricate a positive-generation parent manifest. Component constructors and World-wide inventory auditing run on that coherent new genesis; all successor roots and the manifest join the existing inventory writer. This inactive producer retains explicit full audit for changed World authority, reuses audited topology when its complete input roots are unchanged, and enables no fast World admission. Native affected-owner transitions remain the integration stage.

**Spec:** docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md; docs/superpowers/specs/2026-10-23-ate-generation-authority.md.

**Tech stack:** Python, existing SQLite writer and explicit copy protocol, immutable ProofMap roots.

## Constraints and rulings

- Generation0 alone has no parent/receipt; positive generations require exact verified predecessor and existing committed receipt.
- No source mutation, fake root, second publisher/object registry, automatic migration or main merge.
- Complete format6 contract is the source domain. Unsupported partial-retirement states or mixed inline/backing aliases must fail closed rather than gain invented guarantees.
- World-wide reference/owner/physical-parent inventory must be independently audited; component root hashes alone are insufficient.
- Changed World proof production may explicitly audit history; it is not an interactive save path. Unchanged complete inputs reuse the audit root. World integration and measured target latency remain separate.
- New proof files must reject old writers. Ordinary World activation remains blocked pending native participant/admission integration.
- Full simulation suite on hosted CI only; no long CI polling.

## Review focus

1. Source-copy genesis rebasing must update every MVCC/ordinary/segment/owner/session revision and checksum while preserving logical state and source bytes.
2. Global inventory must reject unindexed owners, missing/wrong backing kinds, extra children, inconsistent aliases and forged complete-format markers.
3. All seven roots must come from the same checked snapshot, not caller-supplied placeholders.
4. Same-transaction manifest publication, exact recovery and old-writer fencing must hold at all existing failure seams.
5. Metadata-only reuse must read zero history bodies; explicit audits must not be represented as bounded ordinary saves.

## Task1: Complete World audit and root composition

Create persistence_proof_world.py and real complete-format fixtures/tests. Reuse existing full catalog/sequence/member-type audits, supplement complete physical backing/owner reference joins, and build World topology/query composite roots. Fail tests first, implement, run focused checks and checkpoint.

## Task2: Checked genesis copy and manifest writer

Create persistence_proof_world_copy.py and persistence_proof_manifest_publish.py. Extend private inventory composition; fence proof format writes and block ordinary World activation. Tests first for new identity/genesis, unchanged logical data/source hash, real positive-generation rejection, mixed/stale components, seven roots, metadata reuse, all failure/reopen/retained pin/token seams. Implement and checkpoint after green checks.

## Task3: Review and publication

Run all proof tests and existing complete-copy/runtime cases. Record construction vs reuse work distinctly. One fresh Astra whole-package review; one RED→GREEN fix pass for Important/Critical findings. Publish one bundled candidate, obtain CI link and stop.
