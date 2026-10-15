# Checkpointed upgrade validation implementation

Approved authority: ../specs/2026-10-15-checkpointed-upgrade-validation-design.md.

Runtime tree must remain c3229ed9ed46bd338bf31d76e7f037d0d77b87b6.

1. Add validation-only immutable capture, storage/catalog verification, and publication. Tests first: boundary after ordinal restoration, closed writer, source preservation, equivalent world/aliases, unchanged retained bytes, ordered receipts, exact lineage, malformed/corrupt inputs, faults, no overwrite. Run focused tests; expected all pass.
2. Add command-line/P5 bridge and safe artifact transport, then bounded fresh-process end-to-end/resume proof. Tests first; run harness and existing P5 regression tests; expected all pass.
3. Add separate checkpoint CI jobs with authenticated artifact provenance and dependencies, explicit limits/upload headroom and progress. Keep mature execution disabled until small runner proof and independent review pass. Publish to authorized branches, execute small CI proof, return links.
4. Independent whole-change review; fix material findings with reproducing tests. Record exact evidence and remaining mature acceptance limitations.

Shared interfaces: capture manifest binds immutable DB, source receipt and runtime/harness; each receipt binds exact preceding stage. CI authenticates artifact origin before the local harness consumes it. P5 bridge delegates accepted complete receipt generation to the existing runner.

Review focus: checkpoint trust is external artifact provenance plus exact lineage, not a self-hashed JSON assertion; crash ordering and hard-link lifetime; no SQLite byte changes during verification; checked pin release only on disposable publication copy; no accepted output on failed verification; retries preserve earlier artifacts.

## Mature construction follow-through after green proof

Run38756130032 passed all9jobs. Extend only CI wiring with pinned source/config,
green core-helper hashes, disk guards and construction progress; use a dedicated
branch so the green small proof does not repeat. Launch only unverified capture
with300m command/360m job limits. Inspect its timings/artifact before later large
verification. New source/config, original capture boundary and workflow tests
RED→GREEN;43 local checks passed4.36s (existing P5 bridge deselected; unchanged
core validated by green fresh-runner proof).
