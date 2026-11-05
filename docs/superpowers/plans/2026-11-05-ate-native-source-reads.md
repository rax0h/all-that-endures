# Native source proof joins implementation plan

> **For agentic workers:** Execute inline using superpowers:executing-plans; one fresh whole-package review, all Minor findings closed per AGENTS.md.

**Goal:** Authenticate the existing native byte-fetch paths against accepted World roots before decoding.
**Architecture:** A focused adapter supplies original native row layouts from checked raw sources and proof membership/absence. The existing authority carries its accepted pin; only the native publisher capability bypasses the adapter during staging. Audited admission remains mandatory.
**Tech Stack:** Existing Python/SQLite native runtime and immutable proof maps.
**Spec:** docs/superpowers/specs/2026-11-05-ate-native-source-reads.md.

## Global constraints

64MiB bodies,1MiB locator/metadata; existing store/pin/writer/codec/proof domains. No new default, migration, fast-open claim or mature launch. Existing recovery and source authority mandatory.

## Review focus

Busy preparation must not bypass proof joins; staged publisher reads must remain possible. Wrong generation and recovery pin drift must reject. Checksums recomputed over forged bodies must still fail before decoding. Oversized metadata/overlapping predecessors must reject before transfer. Failure must close cursors/snapshots and preserve dirty retry.

## Task1: Native byte source adapter and integration

Files: create simulation/ate_sim/persistence_proof_native_sources.py and simulation/tests/test_stage_0_6_proof_native_sources.py; modify persistence_lazy_store.py fetch seams and persistence_proof_world_session.py pin tracking.
Interfaces: adapter active(store) returns an admitted authority or None only before initial audit or inside native publisher capability. version_row(store,authority,g,ns,key), record_row(store,authority,ns,key), record_rows(store,authority,ns) (context-managed streaming roster), segment_row(store,authority,ns,ordinal) return original physical tuple shapes, or authenticated absence for points. Each owns/borrows the accepted pin snapshot.
- [x] RED real native checksum-consistent forged/missing/extra version, ordinary and segment reads with decode sentinels; correct fetched rows and schema failures; old/foreign generations; pretransfer overlap/metadata/budget cases.
- [x] Implement root joins using existing raw source validators and map commitments. Wire before decoding, exact pin updates on admit/commit/resolve, capability-specific staging exclusion.
- [x] GREEN source tests plus native session, ordinary, manifest/version/record/content and generated-year continuation cases; inspect all failures, no independent CI per fix.

## Task2: Bounded-work evidence, review and publication

Files: current native-source-reads evidence/register/closure, runtime launch pin and proof workflow.
- [x] Native point-read history scaling1k/10k, no unrelated page/segment fetch; preserve separate operation measurements and no mature claim.
- [x] One fresh whole-package review. Reproduce/fix every actionable finding, including Minor, retain raw evidence in one register.
- [ ] Exact source/pin/fingerprints, clean-source relevant harness and year continuation; publish one bundled full/proof CI candidate. Keep admission relation coverage and mature targets open.
