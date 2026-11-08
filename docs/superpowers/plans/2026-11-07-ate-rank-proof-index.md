# Rank proof index implementation plan

> Implement inline using the existing dedicated branch and one whole-package independent review.

Goal: certify rank_neighbor's ordered selection, including negative gap proofs.
Spec: ../specs/2026-11-07-ate-rank-proof-index-design.md and the existing rank-neighbor handoff.
Stack: Python, SQLite, immutable OrderedSeekMap and existing scope publication.

Global constraints: preserve six-root certificates and existing defaults; cap
fields at 4096 bytes and windows at 1 MiB; no full-audit removal, main merge,
endurance or mature benchmark launch. Resolve every review finding in this group.

## Task 1: ordered index and atomic projection

- [ ] Add reverse seek tests for empty/prefix/zero/strict boundaries and retained roots; observe RED.
- [ ] Add seven-root bootstrap/commit/delete/recovery/compatibility tests; observe RED.
- [ ] Implement reverse_page and RankScope/root version 4; publish from existing query deltas.
- [ ] Extend existing six-root consumers without conflating rank and sequence roots.
- [ ] Run proof-seek, proof-scope, ranked projection and affected reference tests; expect all PASS.

Interfaces: OrderedSeekMap.reverse_page(root,before=None,limit=128); RankScope(ns,name);
bootstrap_scope_proofs(...include_rank=False); scope root 6 is rank directory.

## Task 2: native rank selection

- [ ] Reproduce coherent earlier/later inserts, omitted minimum, future interval, tie/exclusion and codec-before-check failures.
- [ ] Implement gated native neighbor using accepted forward/reverse seek and bounded exact physical windows.
- [ ] Opt-in proof copy rank_proofs=True; preserve default old representation.
- [ ] Verify stale caller pins, callback contexts, empty scopes, owner source authority and history-independent work.
- [ ] Run new/affected tests; expect all PASS; retain raw RED/GREEN evidence.

Interfaces: persistence_proof_native_rank.neighbor(store,authority,pin,namespace,scope,...)
routes only for an accepted seven-root context; six-root sessions keep legacy read.

## Task 3: integration and publication

- [ ] Canonical year and fresh-process equivalence on seven-root copy; verify source immutability.
- [ ] One independent package review; reproduce and close every actionable finding including Minor.
- [ ] Broad affected tests, exact runtime pins/fingerprints and one bundled hosted full/proof validation.
- [ ] Record source, results and remaining opening/mature gates without claiming unmeasured speed.

Review focus: arbitrarily long rank/key inputs before materialization; prefix
and equal-rank ordinal boundaries; paused/stale epoch; scope version downgrade;
seventh-root changes must not invalidate sequence-only structural reuse.
