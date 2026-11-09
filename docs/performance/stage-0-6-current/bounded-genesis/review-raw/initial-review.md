# Independent whole-package review: initial findings

Reviewed against BASE `7df089ff2b347ae8e36bb535291591a5bb6dfb82`, including staged,
unstaged and new source, tests, workflow, mature request/harness and design/plan.
This is preserved initial review evidence; current disposition belongs in the
consolidated closure register and the separate closure review.

The complete workspace-local runtime fingerprint matched the qualification
contract: Python3.12.3/GCC13.3.0/SQLite3.45.1, including source ID, compile options,
Python/extension/loaded SQLite library hashes. See `fingerprint.json`.

1. **High — per-sequence physical inventories remain proportional to length.**
   `_verify_sequences` called `LazyOrderedSequence.scrub(_inventory=collect)`.
   Although the shared physical inventory used disk sets, `scrub` retained its
   `expected` sets, `occurrences` dictionary, `members` lists and `found_members`
   lists for the complete sequence. The qualified 1k/10k probe observed 1k/10k
   occurrence entries, 2020/20168 expected physical keys and two 1k/10k member
   inventories. Python traced peak increased523542→4156683bytes. This contradicts
   the fixed physical-inventory claim; it is not a native live-World registry
   cost. Recommended conversion-only disk sets and occurrence-rank/value lookup,
   retaining all structural/locator/member and orphan inventory checks.
   Evidence: `review_probes.py`, `probes.log`.

2. **Medium — query rebase locator omits a valid identity field.**
   `lazy_query_versions` permits multiple ordinals for the same
   namespace/index/value/record. `_bounded_rows` used a locator without ordinal,
   and the following UPDATE selected all such rows, collapsing their ordinal
   values and causing a uniqueness failure for a valid store. Include ordinal
   in both stable locator and row UPDATE predicate; retain the separately checked
   retired-group normalization. The implementer's preserved
   `multi-position-red.log` reproduced the failure before repair; the independent
   probe ran after that repair and verifies both memberships survive rebase.
   Evidence: `review_probes.py`, `probes.log`, sibling multi-position logs.

3. **High — frozen-map certification bypasses streaming history iteration.**
   `verify_type_witnesses` called `verify_frozen_certification`, whose map branch
   used `_ordered_entries()` directly. That creates a complete query-membership
   tuple, entries list and sorted result despite the new conversion `__iter__`.
   A clean checked frozen map reaches a rejecting `_ordered_entries` guard inside
   conversion. Recommended a checked streamed entries/value path for clean
   conversion maps, retaining default certification and deep-immutable rejection.
   Evidence: `frozen_map_probe.py`, `frozen-map.log`.

4. **Medium — new construction algorithms reach the default audited opener.**
   `_audit_world` calls `_verify_catalog`, which creates a workspace even outside
   `_CONVERSION_AUDITS`. Passing that workspace unconditionally to type, retired
   and sequence audits selected new construction algorithms during ordinary
   audited opening. The independent real conversion/open probe observed
   `conversion_scope=false,bounded_workspace=true`. Gate newly introduced
   workspace branches on the explicit conversion ContextVar to match the promised
   default-reader/audited-opener contract.
   Evidence: `default_audit_probe.py`, `default-audit.log`.

5. **Minor — the design overstates bounds and omits the existing live cost.**
   The initial design said disk scratch was bounded independently of row count.
   DiskSet/DiskLookup/replay/order tables consume disk proportional to indexed
   rows. Existing canonical digest sorting and restored World identity registry
   also retain native live objects/keys. State fixed Python/SQLite physical-row
   inventory budgets, proportional disk requirements, explicit single-row costs,
   and separate measured native live-World costs. Do not imply constant total RSS.

Construction-cost observation, not an additional correctness finding:1000 empty
scalar iterations created1000 SQLite files in0.68729s on this workspace. The
authenticated source contains1,157,640 nested descriptors. A shared construction
spool avoids file churn; actual mature construction remains a measured gate.

No further actionable finding arose from the full package review. In particular,
the mature harness binds the original accepted source, uses current reviewed
runtime/file fingerprints, requires proof and full-suite jobs before construction,
patches out full World audit fallback during interactive/fresh proof continuation,
checks the accepted year1002 digest after fresh restoration, preserves failure and
censored exit evidence, and requires real target measurements. The final request
runtime-tree and file fingerprints still need refreshing after closure edits.

No merge, default format activation, endurance run or mature acceptance is claimed.

## Acceptance failure discovered during closure

6. **High — unchanged complete generated-year construction fails.** At local
   checkpoint `b628bd10739bcba660be9f6bf700765f25cb7be7` (runtime tree
   `e68a2ea8b5f7c83a7aa4fd41e51f4cad4a60393e`), the qualified unchanged
   `run_proof_real_year_probe.py --rank-proofs --proof-only` driver fails after
   8.54seconds in legacy normalization, before interactive measurements.
   `_copy_with_checked_catalog`→`_restore_copy_ordinals`→`ReplayRows.__iter__`
   reports `StoreIntegrityError: conversion staging row/order checksum mismatch`.
   Do not publish or accept until cause, baseline/introduced status, fix and
   unchanged complete scenario validation are established. Parent is investigating
   against the preserved generated lazy source; this review has not inferred a
   cause. Evidence copied to `generated-year-construction-red.{log,json}`.
