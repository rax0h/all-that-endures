# P4.7 — institution record lazy migration plan

**Date:** 2026-10-05  
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and accepted P4 lazy-family behavior through P4.6.

## Residual evidence

Run 37402918457 on product head
583560db97f7e5921b553f0bda9be713c9c9fa0e measured the post-P4.6 residual
eager graph at 1,000 and 10,000 rows per candidate family.

At 10,000 rows, the three institution record namespaces alone retained:

- `world.institutions.applications`: 5,484,466 payload bytes;
- `world.institutions.magic_records`: 4,285,572 payload bytes;
- `world.institutions.notices`: 3,395,572 payload bytes.

Together they account for about 13.2 MB of the 70.7 MB synthetic residual-open
payload and are the largest coherent remaining archive family. Ordinary open
for the full residual fixture scaled from 29,035 reads / 7.00 MB at 1k to
290,035 reads / 70.7 MB at 10k.

## Scope

Migrate only these three scalar/tuple record tables:

- `world.institutions.magic_records`;
- `world.institutions.notices`;
- `world.institutions.applications`.

Keep `institutions`, `branches`, counters and their nested member/record/
notice/trainee sets eager in this slice. Re-measure them after the record
tables no longer dominate.

## Query authority

Persist only memberships required by existing behavior:

- magic records: `person`;
- notices: `status`, `cause_event`;
- applications: `passed`, `(person,society)`,
  `(person,society,passed)`.

Lazy tables retain exact RecordTable-compatible `ids` / `select` ordering:
stable increasing record IDs. Local unsaved field edits update query results
through the same final-state overlay used by previous P4 indexed families.

Update `records_for_person` to use the indexed table path rather than an
archive-wide `.values()` scan. Existing eager RecordTable fixtures must keep
the same result ordering.

## Identity / lifecycle

The three record dataclasses have no nested mutable fields, so each row carries
one top-level incarnation occurrence. Existing P2C cross-owner identity rules
still apply. Point access, direct field assignment, replacement, deletion,
reinsertion, stale save, failure recovery, cache pressure and materializing
detach use the accepted simple-record P4 machinery.

## Acceptance

- ordinary lazy open decodes zero payloads from all three namespaces;
- one point read decodes exactly one requested row;
- current queries decode only returned rows;
- clean cache <=256 per table;
- no-op save writes zero institution record payloads;
- one changed row writes one version plus exact membership/identity/head deltas;
- insert/delete/reinsert preserves dictionary order;
- query results match eager controls before save, after save/reopen and after
  direct indexed-field mutation;
- 1k -> 10k history keeps ordinary-open payload work flat and one fixed query
  bounded;
- detach/checkpoint portability and P4 affected regressions remain green.

After this gate, rerun the residual inventory and choose the next family by
measured remaining cost.
