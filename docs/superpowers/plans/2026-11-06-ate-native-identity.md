# Native identity read implementation plan

> Execute inline with TDD and one independent final package review; AGENTS.md requires every finding including Minor closed here.

**Goal:** Certify native allocator and exact/owner/group occurrence reads.
**Architecture:** Accepted manifest allocator + scoped owner/group roots, bounded keyless indexed physical-next/point checks, existing snapshots/capabilities/registry.
**Tech stack:** Existing Python/SQLite/OrderedSeekMap/ValidationScope.
**Spec:** docs/superpowers/specs/2026-11-06-ate-native-identity.md.

## Global constraints

128positions+lookahead,1MiB page metadata,4,096-byte fields. Actual caller pin/original epoch. No source-body reads, new registry or publisher, full audit removal, main/default/mature/endurance action.

## Review focus

- Both directional commitments, allocator and raw interval must describe one occurrence.
- SQL cursor boundaries cannot skip duplicate locators, missing/extra keys, future intervals or final surplus.
- Unallocated groups, empty owners and missing points authenticate absence without hiding physical rows.
- Variable physical blobs cannot transfer before validation, and public yields retain no snapshot.
- Scoped caches/callbacks/rollback recovery cannot reuse a different accepted epoch or staging authority.

## Task1: Native read adapter

Create simulation/ate_sim/persistence_proof_native_identity.py and tests/test_stage_0_6_proof_native_identity.py. Modify existing LazyRecordStore allocator/point/owner/group seams only. Consume authority.pair[0].head.next_incarnation_id and read_components[1]; use sources._snapshot(actual pin). Produce existing state/point tuples and decoded occurrence iterator shapes.
- [x] RED coherent allocator/point/owner/group missing/extra/moved forgeries before decoding plus positive shapes.
- [x] Implement bounded allocator/current point checks, accepted owner/group joins, complete adaptive windows and original-epoch/pin snapshots.
- [x] GREEN extended budgets/overlaps/pins/paused/fault/recovery/cache/callback/catalog and existing native regression.

## Task2: Review and publication

- [x]1k/10k physical no-body instrumentation; long pages and exact generated-year eager/fresh/source-immutability checks.
- [x] One independent final review; all findings closed in consolidated register, preserve raw history.
- [x] Final source pin/fingerprints/workflow tests/clean launcher, exact local/API tree mapping and one bundled full/proof publication; verify both start.

Final runtime342regression/33launcher and canonical raw+diagnostic eager/fresh/hash/zero-save-audit pass. Independent46product+13probes, no actionable finding or deferred Minor. Reviewed sources match; runtimefddeb830, local60d471a/API2f01534 equal complete source tree4a181250. One bundled publication prepared; hosted completion remains pending.

All identity package gates closed by verified green42226884633.
