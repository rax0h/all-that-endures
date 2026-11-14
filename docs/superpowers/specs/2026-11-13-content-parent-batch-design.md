# Streamed content-parent proof checking

Continue the authorized Stage0.6 save-speed work. Previous annual-lifetime
engine457a619f/runtime95c61911 is hosted GREEN43501337447: full5115passed plus
2subtests; proof34XMLs1960overlapping cases plus scaling. Downloaded archive,
source and XML receipts are retained in rank-ecology-lifetime/hosted-43501337447.

The existing save profile shows54399proof-map node reads and258197SQL executions.
Content-parent validation performs independent get() proofs for every changed
version/event, before the same parent is traversed again for the successor merge.
Choose a stateless streamed verification of sorted expected memberships: visit
only the union of their checked paths, without retaining a cache between calls.

Implement verify_sorted(proof_map, root, members) in a focused module. Members
are (typed_key, expected_commitment_or_None) in strictly increasing domain-locator
order. Each selected node uses unchanged ProofMap._read (domain/hash/canonical
node/count/prefix checks); missing branches prove absence. Empty/late malformed,
unsorted/duplicate/colliding input and callback failures remain rejecting. Read
no unrelated bodies; use bounded stack/fanout and one current input, no global
cache or writes. A specific StoreIntegrityError subclass distinguishes expected
value mismatch for existing event-append conflict classification.

Integrate only _guard_content_parent. Bounded physical predecessor reads and all
existing byte/type budgets stay. Stage expected commitments in a TEMP SQLite
spool ordered by existing domain locator, verify each version/event parent map
before any source mutation. Drop temporary state on completion/failure. Preserve
existing version-integrity vs event-conflict errors. No change to roots, encoding,
content promises, publisher/recovery/lease rules or physical successor checks.

Alternatives: a session cache creates epoch/invalidation/lifetime authority;
removing predecessor checks weakens publication. Streaming the same proof is the
narrow selected implementation call. No new gameplay choice or approval needed
under the standing instruction to continue implementation.

RED→GREEN actual path-read count; equivalence to independent get for present and
absent keys; malformed data, corruption, rollback/faults, native save/reopen and
fresh-process exact-state checks. Qualified313; disposable existing small input.
One whole-package independent review, close all findings including Minors.
No mature/default/main/endurance activation. Mature targets remain open.

## Measured scope amendment: bounded memory first

The TEMP-only prototype reduced guard nodes5310→2043 but raw full saves were
slower in both paired observations; it is not promoted on that evidence. Test a
bounded in-memory expectation sorter, using the same TEMP spill on overflow.
Retained input charge is capped at1MiB: resident_bytes(row)+128 per entry, plus
initial list residency; the128bytes conservatively cover list over-allocation
and sorting keys/workspace. The current incoming/source row remains outside that
retained charge under unchanged existing source/locator/body bounds. This is not
a total-RSS/SQLite-page-cache bound. Streamed verification and all pre-write
physical checks are unchanged. Test normal and forced-spill publication/recovery;
remeasure before final related/hosted gates. Stop promotion if whole-save benefit
is not established; preserve negative variants and measurements.
