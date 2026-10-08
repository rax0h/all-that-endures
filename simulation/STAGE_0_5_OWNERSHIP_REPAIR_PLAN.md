# Paged sequence ownership repair

Goal: repair the demonstrated B1/B2/B3 ownership failures on frozen e8e216d,
without replacing P1 transactions, P2C links, or P3 event storage.

Architecture: a checked auxiliary incarnation-to-backing-key record lets an
existing paged sequence outlive its original household. Current P2C links and
checked occurrence labels still determine sharing. A backing key is storage
placement, never the authority for current object identity. New sequences use
incarnation-qualified keys; replacing a household cannot overwrite a surviving
old list. Descriptor, pages, occurrence labels, links and World edits commit in
the existing hybrid transaction and follow its existing recovery protocol.

Compatibility: old paged snapshots without descriptors use the checked
household occurrence and its original owner-local projection. Unchanged opens
and no-op saves do not migrate history. The first changed sequence installs its
descriptor atomically. Legacy redundant physical projections may remain as
unreferenced compatibility data; ordinary operations must never use them once
the descriptor exists. Non-paged snapshots remain unchanged.

## Work and evidence ledger

- [x] Verify live PR remains c29e3d0; frozen source is e8e216d. Final frozen
  full-suite run 37780238248 completed successfully. This does not validate repairs.
- [x] Reproduce deletion data loss, alias splitting, and stale membership index
  against the real SQLite implementation using the committed review probes.
- [x] Add permanent regression cases for ownership transitions, save failures,
  lost acknowledgements, stale writers, retained aliases, and append bounds.
- [x] Implement stable backing identity and reconcile current placements without
  cloning a shared live pager during save preparation.
- [x] Repair replacement suffix deletion and native list comparison/operators.
- [x] Run focused and affected gates; obtain independent findings and repair them.
  Final exact-commit CI remains assigned; see validation evidence boundaries.
- [x] Prepare an isolated repair branch descended from e8e216d, with evidence
  and the precise remaining bounded-storage assignments. Do not merge/promote.

Review focus: last household deletion with unloaded foreign owner; simultaneous
split/merge/replacement including key reuse; fail before commit and retry with
unchanged live aliases; commit then lose acknowledgement; read a foreign alias
first after reopen and after eviction. Each needs a behavioral regression.

Changes belong in persistence_lazy_household_members.py (checked sequence and
descriptor), persistence_lazy.py (ownership and publication), and focused tests.
No long tests, endurance simulation, gameplay changes, or broad family migration.

Release remains blocked on the separately documented residual eager inventory
and the missing retrievable endurance restore fixture. Do not recast this repair
as complete Stage 0.5 acceptance.

Execution ledger: independent-review findings and P5-discovered reopened-owner
regression were reproduced and fixed. Reader capability format 4 is transactional;
format 3 remains readable, and current-head copy preserves the capability floor.
See STAGE_0_5_OWNERSHIP_REPAIR_VALIDATION.md for exact gate boundaries.
