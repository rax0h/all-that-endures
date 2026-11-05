# Native collection order implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; one independent whole-package review. Close all findings including Minor per AGENTS.md.

**Goal:** Bind native lazy counts, key existence and key iteration to accepted World collection proofs.
**Architecture:** Accepted component context from the existing manifest loader feeds one focused native order adapter. Existing store seams retain native shapes and snapshots; physical indexed windows must equal accepted seek windows before key decoding. Keep audited admission and original publisher.
**Tech Stack:** Existing Python/SQLite/immutable ordered seek maps and ValidationScope.
**Spec:** docs/superpowers/specs/2026-11-05-ate-native-collection-order.md.

## Global constraints

128returned keys plus lookahead,32,760-byte typed keys,1MiB combined page metadata. Same source budgets, pin, guard, registry, publisher and format. No full opening audit removal or mature/default/main/endurance action.

## Review focus

Component context must never be accepted before manifest binding. Busy callbacks cannot obtain staging authority. Count-forged early termination and extra final-window rows reject. Every selected key must have its actual source checked before decode. Long-key page shrinking cannot skip/duplicate a key. Interrupted/paused iterator cannot retain a snapshot or mix generations. Scoped summaries must invalidate across writes and root changes.

## Task1: Native state/order and accepted context

Create simulation/ate_sim/persistence_proof_native_order.py and simulation/tests/test_stage_0_6_proof_native_order.py. Modify persistence_lazy_store.py state/order/iter_keys/lazy-declaration seams and persistence_proof_world_session.py component-context installation.
Interfaces: authority.read_components is the five accepted component pairs from manifests._load, captured after verification and refreshed with read_pin/pair. Adapter state_row(store,authority,g,ns), order_row(store,authority,g,ns,typed), iter_keys(store,authority,pin,ns,page_size) return existing native types; active/capability rules come from native_sources. Collection summaries may use existing ValidationScope immutable cache only.
- [x] RED real count/next/ordinal/missing/extra native corruption before output, supported absence and pagination controls.
- [x] Implement manifest-bound component context, bounded exact physical state/point joins and physical/proof page equality with lookahead before decoding, source checks and closed snapshots before yields.
- [ ] GREEN extended pagination, large-key/budget/pretransfer, epoch/snapshot, save/fault/alias/recovery and generated-year tests; verify all failure dispositions.

## Task2: Review, evidence and publication

- [ ] Retained1k/10k no-unrelated-body controls with physical selection instrumentation and measured page/source work. No mature claim.
- [ ] One independent whole-package review, author RED→GREEN corrections of every finding including Minor, one register/raw history.
- [ ] Runtime pin/fingerprints, clean launcher and canonical-year eager/fresh checks; exact local/API source tree mapping; one full/proof CI publication. Record remaining query/identity/raw-consumer gate explicitly.
