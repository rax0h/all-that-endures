# Paged ownership repair candidate — 2026-10-08

Status: implemented and short-gate validated; **Stage 0.5 remains BLOCKED** on
remaining bounded-storage work and durable endurance evidence. No production
promotion, merge, broad migration, or endurance run is authorized by this file.

## Provenance

The patch is based on frozen implementation
`e8e216dd234f47dd2be9a96af1e8048798fa1ba0`, tree
`be89be21b9289fef7dfafbdb783b47a61f05faa9`. PR #14 remains draft at
`c29e3d06a0c9d219235e2b3f0390271bd1245aea` at the live check. All local production
module baseline blobs match the frozen source, allowing a retrieval-added final
newline. Affected test files were checked against/fetched from that frozen SHA;
older local copies were not published as changes.

Frozen full-suite run [37780238248](https://github.com/rax0h/all-that-endures/actions/runs/37780238248),
job `113321201762`, completed successfully: **889 passed in 2219.21s**. Its helper
commit `ff5e05ffb5203b51c44cbd3f8d82190ca3359942` has the same simulation source and
tests as the frozen implementation. That is baseline evidence, not a full-suite
claim for this patch.

## Changes and authority

- A versioned, checked `aux.lazy.household.member_backings` record maps a logical
  incarnation to its physical sequence key. Household IDs no longer determine
  the lifetime of a shared list. Replacement sequences use incarnation-qualified
  physical keys; surviving foreign owners retain the old authority.
- Normal append reads/writes bounded pages. Save publishes descriptor, pages,
  occurrence labels, current P2C links, World edits and generation using the
  existing P1/P4 transaction and recovery protocol. Descriptor preparation stays
  pending through before-commit failure, so retry cannot publish a dangling token.
- New list assignment and whole-Household insertion normalize before returning
  the bound field. Save does not exchange a previously observed list. Merge,
  split, deletion/reinsertion, retained aliases, and foreign-owner reactivation
  preserve logical identity. A retired external list can be reassigned within its
  original active session without changing its Python identity.
- Currency and genealogy child-list aliases use the same checked pager. Explicit
  genealogy detach materializes the shared list. List concatenation/repetition
  and comparison no longer diverge on the reproduced compatibility cases.
- Replacement retirement accounts for the persisted extent, including removed
  suffix pages/membership entries.
- Bootstrap rollback originals and temporary synthetic alias owners no longer
  retain a deleted household history after successful open/save.

Legacy paged snapshots remain readable; untouched scalar saves retain their
legacy empty placeholders. When a descriptor is needed, a compact reference and
reader-format requirement **4** are published in the same transaction. Reader
format 3 remains readable. Old format-3-only readers reject upgraded saves.
Current-head copy preserves the capability requirement. Format never downgrades
on later ordinary commits. This deliberately is not forward compatibility with
old writers. P1/P2/P3 and non-paged checkpoint APIs are not replaced.

Legacy shared household groups may have redundant owner-local physical
projections from conversion. Once the descriptor exists those copies are not
logical authority and are never consulted for that incarnation. Reclaiming all
such compatibility rows is explicit maintenance, not an ordinary append scan.

## Executed evidence

All tests used real SQLite stores. Fault hooks inject before/after commit only.

| Gate | Observed result | Boundary |
| --- | --- | --- |
| Original independent review probes | 6 passed | Reproduced failures first; deletion, merge, shrink, genealogy sharing, R1/R2 probes |
| New ownership regressions | 18 passed in 2.408s | Final source, including retained reinsertion and current-head copy |
| Existing household/sequence/default/recovery suites | 31 passed in 61.39s | After descriptor guard and reopened-owner fix; before the final retained-reinsertion extension |
| Ownership + currency/genealogy/identity/tracking/lifecycle/P2C gate | 95 passed, 2 subtests, 18.55s | Includes then-current 16 ownership cases; predates format guard and last reinsertion extension |
| Store + failure suite | 49 passed in 4.58s | After format guard/current-head-copy change |
| Independent P5 short control, seed 843000, 3+4+3 years | passed true | After reopened-owner fix; before final retained-reinsertion extension |

P5 final control digest:
`3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`.
The harness compares an unbound eager control, continued persistent world,
reopen, relocated backup, materialized detach, and checkpoint roundtrip.
No millennium/endurance was launched. No final whole-suite result is asserted.

The new 1,000/10,000-member surviving-wallet test asserts zero cached member IDs
on first open of that alias, <=512 cached IDs, <10,000 payload bytes read and
<5,000 written for point-open/append/save, and identical read/write operation
counts at the two sizes. This proves that operation's history bound. It does not
prove a bound on eager household count or global identity metadata.

Independent review exposed scalar-only dangling references, deleted-group
retention, and inserted-Household alias replacement. Each was reproduced and
regression-covered before correction. Subsequent P5 exposed an incarnation-key
being mistaken for a live household placement after reopen; its focused
regression now passes. This records findings addressed, not a blanket claim that
an independent reviewer approved every final byte.

## Remaining release blockers

1. Final exact-commit CI gate for this repair; see the bounded Sol assignment.
2. B4 from the [independent review](https://github.com/rax0h/all-that-endures/blob/c29e3d06a0c9d219235e2b3f0390271bd1245aea/simulation/STAGE_0_5_REPAIRED_CANDIDATE_REVIEW.md):
   eager event-ID set, eager current-link inventory, history-growing household
   records/settlement IDs, and ordinary living-member queries loading dead history.
   Nested property, beliefs, culture, institution membership/notices/records,
   divinity followers/relationships, closed conflicts/inquiries and threats also
   lack the claimed historical bound. Active/dirty/external working state must
   be measured separately from clean archive history. API-only growth and fixed
   geography must remain classified honestly; the earlier report has the table.
3. A retrievable late restore fixture. The previous year-1000 checksum/path is
   not an artifact. No independently retained copy was verified in the previous
   review. A replacement endurance run still requires explicit owner authorization
   after storage and validation blockers are resolved.

This candidate repairs demonstrated ownership failures. It is not permission to
relabel the remaining eager structures as bounded or accept/merge Stage 0.5.
