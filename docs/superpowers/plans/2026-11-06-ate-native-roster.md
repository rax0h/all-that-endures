# Native roster implementation plan

> Execute inline with TDD and one independent whole-package final review. AGENTS.md requires all findings including Minor closed here.

**Goal:** Authenticate ordinary namespace enumeration completeness and verify catalog composition.
**Architecture:** Accepted manifest count + indexed selected-namespace count + existing actual source-root joins, all in the current checked snapshot. Test existing catalog composition without another registry/publisher.
**Tech stack:** Python/SQLite/existing closed metadata codec and ValidationScope.
**Spec:** docs/superpowers/specs/2026-11-06-ate-native-roster.md.

## Global constraints

Existing1MiB metadata/64MiB source-body bounds; same snapshot/epoch/capabilities. No unrelated body/archive scan, new root/index, full-audit removal, main/default/mature/endurance action.

## Review focus

- Accepted counts include both record/segment fields; lazy namespace declarations must still reject ordinary access.
- Count preflight occurs before payload selection; compensated deletion/addition cannot pass point-source checks.
- Metadata parsing/caching cannot call user codec hooks or replace physical validation.
- Public catalog caches and metadata-only owner witnesses cannot grant body authority or hide changed placements/links.
- Errors/callbacks/recovery must preserve the original checked snapshot and accepted context.

## Task1: Roster adapter and catalog coverage

Create persistence_proof_native_roster.py and tests/test_stage_0_6_proof_native_roster.py; modify native_sources.record_rows and the older source test's deliberately incomplete-roster expectation. Catalog runtime stays unchanged unless evidence identifies a defect.
Interfaces: expected_count(store,authority,manifest,namespace)->int, check_count(...)->int; consume manifest.head.namespace_counts, _namespace_counts and closed metadata codec; existing record_rows context retains shapes and actual-body _record validation.
- [x] RED missing/extra/compensated/head-forged native roster reads and positive empty/shape controls.
- [x] Implement closed accepted count metadata and physical count before body selection; verify final observed count.
- [x] GREEN extended metadata/cache/snapshot/recovery/segment and public catalog entrypoint tamper/alias tests; relevant native regression.

## Task2: Review and publication

- [x] Catalog seam-to-authority coverage table plus explicit remaining raw-consumer gate;1k/10k physical no-unrelated-body controls.
- [x] One independent whole-package review, close all findings including Minor and preserve raw history.
- [x] Final source pin/fingerprints/workflow tests/clean launcher/canonical eager+fresh checks, exact local/API tree mapping, one full/proof publication prepared.
- [ ] Hosted full/proof completion.
