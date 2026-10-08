# Stage 0.5 continuous storage repair

## Authority and scope

Owner instruction: continue and get the storage fixes completed; Astra need not review every step. Execute focused verification within each unit, integrate the result, and obtain one final architectural review. Do not pause for approval of routine implementation choices.

Implementation base: `5391b377180fb230ce4b80cbfd5e69d1997111aa`; simulation source is the exact `171b18397b7f0ecb4ebfb218e60729308120c264` candidate already verified by 177 focused tests, P5 3+4+3, and CI run 37822170654 (907 tests plus two subtests). New work must be verified separately.

All changes are isolated from production PR #14. No merge, production promotion, Stage 1, balance/progression edits, or long endurance run is authorized by this plan. Launch the final full-suite CI once and publish its URL without waiting or polling. A new late-world capture remains a separate execution gate.

## Invariants

- Preserve exact facts, event values and causes, native collection semantics, insertion/occurrence order, RNG outcomes, sharing, retained aliases, and portable materializing detach.
- One existing hybrid SQLite transaction publishes payloads, query memberships, occurrence labels, P2C links, EventLog, counters, layout, receipts, and head. New children do not commit independently.
- Failure, uncertain acknowledgement, retry, stale pins, and competitor commits remain old-or-new and fail closed. Validate changed compact authority before publishing runtime state.
- Do not infer authoritative sets/maps from correlated history or truncate dormant facts. Separate genuine current working state from archive history.
- Explicit conversion, upgrade/copy, digest, export, archive, verification, materializing detach, and whole-container transformations may traverse requested history. Ordinary open, fixed current operations, no-op save, and small save may not hide full archive traversal.
- New lazy namespaces must be recognized through checked namespace/schema authority. Missing authority in an existing store means legacy restoration or explicit source-preserving upgrade, never silently empty state or hidden full-cost migration during ordinary open.
- Maintain explicit concrete persistence type allowlists. No blanket acceptance of arbitrary mutable protocols.
- Numerical gates use H=1,000 and H=10,000, fixed active/matching records and edits; record actual rows, bytes, sidecars, identity state and cache size. Do not substitute elapsed time or row counts for byte/retention evidence.

## Shared interfaces

`LazyRecordStore.identity_occurrences_for_incarnation(pin, incarnation_id)` returns checked `(owner_namespace, owner_key, occurrence_path)` occurrences at the pin, using an incarnation-leading index. It must not enumerate all owners. Owner lookup remains available. Old pins use versioned P2C target authority, not latest ordinary records.

`LazyRecordStore.query_memberships(pin, namespace, index_name, value, *, limit=None, exclude_keys=())` returns checked `(record_key, occurrence_ordinal)` pairs. Preserve existing checksum, owner visibility and membership validation. `query_keys` remains compatible. The household unit owns this API; the inquiry unit may supply its isolated implementation for integration if needed.

Reader capability floor for new compact authority is 5. `BOUNDED_AUTHORITY_FORMAT_VERSION = 5`; new readers accept 3/4/5; publication uses `max(current_format, required_format)` in the data transaction. The event-ID unit owns this shared change. Other unit branches may add the same minimal constant temporarily; integration keeps one monotonic implementation.

Typed nested history lives in `persistence_lazy_nested_history.py`: checked incarnation-owned descriptors and versioned scalar entries/pages. Lists use 128 entries and four clean pages. Scalar sets/maps use at most 256 clean entries. Preparation returns frozen `VersionChange` actions; only session publication advances pins and acknowledges them. Child references preserve their incarnation and are identity leaves for ordinary parent encoding/tracking. Explicit materialization uses one shared memo. The institution/divinity unit owns this primitive and communicates its interface to consumers before those integrations.

## Remaining ordinary scan requiring a separate proof

`engine._pressure` computes ordered native `sum(h.preparedness for h in settlement.households)` including extinct households. Changing it to occupied households or an associative/delta sum can change behavior and floating-point rounding. Preserve the current arithmetic while completing the independent storage units. Report the scan honestly; a claim that every ordinary path is bounded requires an exact arithmetic solution or a separately approved behavior change.

## Acceptance

Unit-specific tests must be observed failing for the defect before production implementation, then pass with appropriate existing affected gates. Each implementer writes a design/plan and measurements, runs focused gates only, and commits locally. Root integrates shared seams and resolves conflicts before an integrated P5 continuation, final architectural review, and the single full CI launch. A unit is not complete merely because its adapter exists: conversion, open exclusions, save, recovery, identity, lifecycle, legacy and detach must all be addressed.
