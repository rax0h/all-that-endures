# Native query membership implementation plan

> Implement inline with executing-plans, TDD and one independent final package review. Close every finding including Minor per AGENTS.md.

**Goal:** Bind native query result selection/completeness to accepted query scope proofs.
**Architecture:** Resolve existing accepted scoped-directory component; share bounded physical window SQL with native order, then certify selected actual source/owner memberships before key decoding. Preserve one publisher, scoped summaries and full audited opening.
**Tech stack:** Existing Python/SQLite/OrderedSeekMap/ValidationScope.
**Spec:** docs/superpowers/specs/2026-11-05-ate-native-query.md.

## Global constraints

128positions plus lookahead,1MiB page/exclusion metadata,4,096-byte query fields/keys. Same actual pin, original accepted epoch, source-body limits and exact capability checks. No full admission removal, main/default/mature/endurance action or raised application budgets.

## Review focus

- Limits/exclusions cannot change proof/physical positions or fetch excluded bodies.
- Missing/extra final rows, future starts/closures and duplicate intervals reject before selected key exposure.
- Actual caller pins and original epochs cannot be substituted, including limit0/empty scope and same-generation recovery.
- Invalid raw variable fields never enter SQLite materialization or survive in paused generators.
- Scope summaries never replace physical validation; callback/publisher staging cannot become native authority.

## Task1: Shared bounded query read adapter

Files: create persistence_proof_native_window.py and persistence_proof_native_query.py; modify persistence_proof_native_order.py and persistence_lazy_store.py; create tests/test_stage_0_6_proof_native_query.py.
Interfaces: shared physical_window(store,generation,namespace,after,limit,positions,*,query=None,max_key_bytes=32760) returns trusted-key/typed actual scalar rows; native query memberships(...,limit=None,exclude_keys=()) and iter_memberships(...) return existing native shapes. Consume authority.read_components[1], scope._resolve and native_sources._snapshot(actual pin); cache immutable root summaries only.
- [x] RED native missing/extra/ordinal and scope absence before key decode for tuple and streaming APIs; positive shape/limit/exclusions controls.
- [x] Implement shared current indexed materialization, bounded scope/root resolution, exact-window/source/owner checks, no snapshot/body retention across yields and original epoch binding.
- [x] GREEN extended pagination/large keys, budgets, pins, callbacks, scope corruption/cache invalidation, fault/recovery/aliases and existing order/source/session regression.

## Task2: Review, final evidence and publication

- [ ] Retained1k/10k body-selection/work controls; exact canonical generated-year eager/fresh continuation and source immutability; no timing win claim.
- [x] One independent whole-package review with all findings closed in one register; retain raw RED/GREEN evidence.
- [ ] Runtime pin/fingerprints, workflow inclusion, clean-source launcher/current-source verification and exact local/API tree mapping; publish one bundled full/proof run and verify both start.
