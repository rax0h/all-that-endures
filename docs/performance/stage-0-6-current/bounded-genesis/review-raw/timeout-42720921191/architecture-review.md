# Mature timeout: independent architecture review

Review target: published source85f87e1, mature job129577146906 in run42720921191.
This is a recommendation review, not implementation closure. No product code was
edited, no persistence acceptance/profile was run, and no CI was launched.

## Evidence and present findings

The downloaded artifact13738303791 is41503bytes with SHA256
`0abf6d7a4e8fc7cacf80897616c47b462125df660ba16d69d89949ccef7dae64`.
Its hash, source authority, receipts and failure stack were independently read.
`timing-summary.json` retains exact values and the copied original JSON/logs.

| Construction boundary | Observed duration |
| --- | ---: |
| Start→after_source_capture |3126.51s |
| after_source_capture→copy before_publish |3648.68s |
| after_private_copy→construction failure/cleanup |5826.71s |
| Complete construction budget consumption |12601.93s; censored |

The last interval includes the first catalog audit and short setup/cleanup; it is
not a completed catalog measurement. The failure stack is the second owner-tree
walk in `_verify_catalog`→`catalog._node`→`read_version`→`_read_snapshot_start`→
`_checked_head_row`→head checksum. Rebase, canonical digests and proof bootstraps
were never reached. Peak process RSS was406097920bytes; construction consumed
1059100328583logical read bytes,277823864read syscalls and236992901120physical
read bytes. Original source hash was unchanged. Memory boundedness has supporting
evidence, but audited construction has not met its existing budget.

**High: repeated operational/catalog validation is a demonstrated construction
bottleneck.** `_copy_current_checked_catalog` enters `read_snapshot` before
`_verify_catalog`; nested `checked_read_operation` is deliberately ineligible for
certificate reuse. `_read_snapshot_start` consequently repeats pin, head and
retention/operational checks for nested payload reads. In addition, the catalog
checks group→owner point paths, then owner completeness, then walks every owner
tree a second time for physical node inventory. Catalog descriptor checks are
also repeated by the per-group/per-owner methods.

**High: eliminating only this first catalog stall is insufficient evidence of
budget feasibility.** The format6 route statically calls `verify_all` at least11
times: source and copied head; after roster commit; before/after rebase; each of
five proof bootstraps; final World audit. Many calls inspect unchanged source
authority. The final World audit additionally reconstructs source/proof relations,
including per-record proof lookups. Those later phases are currently unmeasured.

**Local validation prerequisite changed.** The old qualified venv pathname now
resolves to Python3.13.5/GCC14.2.0/SQLite3.46.1 at `/usr/bin/python3.13`, with
different executable, extension, library hashes/options/source ID. See
`local-fingerprint.json`. The old complete-scenario qualification cannot qualify
this tuple. Use the unchanged complete qualification scenario and record its full
tuple/result before accepting new local persistence evidence. This observation
does not diagnose an engine or application cause.

## Recommended smallest sound repair

Use two explicit private custody boundaries; leave default readers, writers,
audited opening and standalone public bootstrap contracts intact.

1. **One owned, read-only catalog operation.** Enter the operation before any
   borrowed `read_snapshot`, using the existing `checked_read_operation` ownership
   contract. Do not declare an already borrowed transaction eligible. Keep a
   bounded cache of immutable descriptor/header/node facts. Add a private node
   inventory collector to the already checked owner walk, and use the returned
   `CheckedOwnerIdentity.exists` for live-owner inventory. This removes the
   immediately repeated `_owner` read/tree walk while retaining the exact same
   checked node inventory and owner↔occurrence completeness tests.

   Measure the hot path: existing `ValidationScope.can_reuse` still issues
   data/schema PRAGMAs each time, often several times per lookup. An owned scope
   alone is not evidence that SQL volume is low enough. If a conversion-specific
   read capability removes those repeated PRAGMAs, it must hold one stable owned
   snapshot, forbid writes/transaction escape, bind the exact connection/pin/codec,
   and expire unconditionally on exit. Keep ordinary scope semantics unchanged.

2. **One guarded post-rebase source-audit certificate for proof construction.**
   Finish all source mutations first: rebase, format metadata, dependency-token
   normalization and publisher pin setup. Create and verify exact required proof
   schemas and supporting source indexes before issuance. Begin an owned
   `BEGIN IMMEDIATE`, install an exact source-write guard, and mint a private,
   operation-local certificate only after the real source audit succeeds.

   Prefer private in-transaction builders behind unchanged standalone bootstrap
   wrappers, so all five component constructions and final World manifest share
   this one owned transaction. The certificate authorizes reuse of precisely the
   successful source checks across proof-only writes. It is not a persistent
   proof, a general `verified=True` flag or a global replacement of `verify_all`.
   Keep every component's budget/schema/type/allocator checks, collision checks,
   proof construction and the final World audit. Commit and publish only after
   those complete. Test and measure journal/disk requirements for the larger
   private transaction; do not assume they fit the existing headroom formula.

   If retaining the current per-bootstrap commits is substantially smaller, keep
   the same write guard installed across all boundaries, and check external
   `data_version` **inside each new `BEGIN IMMEDIATE`** before reuse. A check made
   before acquiring the transaction has a race. Revalidate exact source schemas,
   connection/pin/codec/authorizer custody at each entry. Proof writes legitimately
   change `total_changes` and main schema, so neither a raw epoch equality nor
   ignoring all changed epochs is a sound substitute for source immutability.

The existing `NativeWriteGuard.publisher()` is not this guard: its publisher
capability permits all durable writes. New source authority needs a narrower
allowlist. No timeout increase is recommended as the repair.

## Guard and certificate requirements

- Protect all original persistence tables, including ordinary bodies/memberships,
  segments, every lazy version/state/identity table, store metadata, head,
  pins/receipts/attempts and maintenance authority. Use exact schema/database/object
  identities, not an `ate_*` prefix. Proof/scratch writes must have exact allowlists.
- Prevent source DDL, attach/detach, TEMP shadows, triggers, writable-schema and
  other mutating PRAGMAs, extension loading, unauthorized transaction control,
  authorizer replacement and callback/factory registration or replacement.
  Chain and restore the prior authorizer. Keep a sticky denied/invalidated state,
  including caught denial, savepoint rollback and whole-transaction rollback.
- Bind certificate custody to exact store and connection objects, codec identity
  and closed behavior, store identity, pin token/head, source schemas, format and
  raw accepted metadata. No cross-file/store/generation/rebase transfer. No public
  iterator or gameplay callback may carry the private capability out of its scope.
- Source-audit reuse does not establish integrity of new proof pages. Keep final
  physical integrity and all distinct World/proof-root correspondence checks.
  Do not infer append-only proof storage merely from an INSERT allowlist; test
  `INSERT OR REPLACE` and conflicting existing immutable nodes explicitly.
- On exception/cancellation, invalidate the certificate before cleanup, restore
  guards and discard the unpublished file. Preserve the primary error and source
  bytes. Release publisher pins after capability invalidation; publication remains
  atomic, no-overwrite, and after final audited success.

## Safe reductions versus distinct checks

| Repeated work | Safe reduction and required condition |
| --- | --- |
| Nested pin/head/retention checks during one catalog read | Reuse owned read authority; payload and structural checks remain |
| Owner completeness walk followed immediately by node-inventory walk | Emit the checked inventory during the first walk |
| Group point paths and complete owner relation | Keep initially; a future fused audit may replace point paths only after proving a **global** owner-leaf↔all-occurrence relation, including orphan occurrences for unknown owners |
| Rewriting every format6 dependency roster, advancing a storage generation, then immediately rebasing | Consider a format6-only private path: validate roster inventory/kinds and fold required expired-token clearing into the existing rebase rewrite. This stage is not wholly a no-op: token clearing must remain. Keep all complete-format/reference/graph checks; legacy/default copier stays unchanged |
| Source audit across post-rebase proof-only writes | Reuse only under the exact guarded certificate; no reuse across source mutations |
| Current retained views plus later historical checksum scan | A later one-pass audit may check each physical row once and feed all retained-view inventories; retain every historical checksum/structural, order/query/count/overlap/allocator condition. This is a separate algorithmic refactor, not the first repair |
| Final scope/content/directory proof reconstruction | Distinct current-source↔proof checks remain. Reusing construction roots would additionally require a proved immutable proof-output certificate; source immutability alone is insufficient |
| Canonical digest before/after rebase | Preserve both, with full alias/topology and allocator checks; source certificates do not replace this preservation check |

## Required negative controls and closure evidence

1. Owned versus borrowed scope, nested scope, foreign/released/moved pin, replaced
   store/connection/codec, stale scope after exit, exception and cancellation.
2. Corrupt payload/checksum and coherently changed source payload+checksums; missing
   or extra record/order/query/occurrence/group/link/owner/tree/type/retired rows;
   wrong allocator, source schema and metadata. Certificate issuance must fail.
3. During reuse, attempt INSERT/UPDATE/DELETE/REPLACE, same-value writes,
   write→rollback, source DDL/index changes, TEMP shadows, triggers, ATTACH,
   mutating PRAGMAs, authorizer/factory/function replacement and callback writes.
   Include SQL prepared/cached before guard installation. Denial cannot become
   authority to resume after a caught error.
4. If commits remain, an independent connection coherently changes source between
   phases; reuse must fail before decoding/constructing the next component. Under
   a single owned writer transaction, verify external writes cannot commit during
   custody. Also test unexpected commit/rollback/savepoint escape.
5. Positive proof-only bootstrap writes succeed; corrupted/conflicting proof
   bodies/roots, altered returned component authority and incomplete construction
   are still rejected by the final audit. No default public path selects reuse.
6. Cancellation at issuance, each construction phase and final audit leaves no
   destination, restores the prior authorizer/scope and preserves original bytes.
7. Count distinct full source audits and head/pin/operational queries on realistic
   1k/10k/100k catalog fixtures, including large aliases and owner trees beyond
   the cache limit. Verify bounded Python memory and disk growth separately.

Add low-cost phase receipts around full audit/catalog subpasses, rebase, each
forest build and final source/proof/World checks. Measure statement/read counts
by fixed phase counters, not an unbounded mature SQL trace. Current evidence cannot
predict that unexecuted phases fit12600seconds. Close the timeout finding only
after exact-source tests/review and the authenticated unchanged-budget mature run
demonstrate success, with all original source preservation and continuation gates.

The design/spec sentence prohibiting reuse across mutations needs a precise
update: the proposed exception is private source-audit fact reuse across guarded
derived proof writes while the complete source authority is unchanged. It is not
permission to reuse audits across arbitrary mutations. Group remains open.
