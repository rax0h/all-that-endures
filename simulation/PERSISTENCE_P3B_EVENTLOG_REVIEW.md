# P3B composite EventLog review

Reviewed Sol correction head:
`be5283c0d59ce9bf595ab1e2acd611503a781f4b`.
Original component: `69e748fe582b6949ef67b52cbbf6cd9b20cec938`.
P3A remains accepted at `1093dfac2d395424fb148562d504c008855e6a0f`.

## Findings and final corrections

Sol's correction fixes both original blockers: a suspended pending-history
iterator checks reader/store lifetime before returning every subsequent value;
prefix adoption rejects an unrelated store before discarding source chunks.
Checked comparison of newly transferred segments also rejects divergent
same-store payloads. Adoption remains limited to four chunks and never reads
older committed segments.

Review found two small remaining issues and corrected them directly:

* Ordinary Python equality rejected correctly persisted NaN values and accepted
  distinct typed/bit representations (`1`/True, `1`/`1.0`, positive/negative
  zero). Compare the accepted typed codec representation of each bounded source
  and replacement chunk instead. This preserves NaN payload bits and exact
  nested types without redefining the P3A format.
* An older same-store reader could replace a reader captured at a newer store
  generation. Reject a regressing captured generation before reading payloads
  or changing the runtime partition.

All five new regression cases failed against the reviewed head and passed with
these corrections. Failed adoption retains the old reader, pending bytes and
tail authority; successful adoption still transfers exactly the selected range.

## Verification

The reviewed Sol files match the successful isolated CI candidate
`daffe0fa602b76136a8f8fd3d388874f7c354da1` byte-for-byte; its only extra file
is the temporary validation workflow. Run `37105795282`, job `111153927099`,
reports 18 component, 206 affected and 373 full-suite tests passing.

Local final-code evidence:

* Five newly added typed-value/generation regressions: 5 passed.
* Component suite plus three original independent review probes: 26 passed
  in 20.32 seconds. The probes cover reader close, store close and wrong-store
  adoption; corresponding maintained coverage is in the component test file.
* Full suite on Python 3.12.14: **378 passed in 313.62 seconds**. Command:
  `PYTHONPATH=/tmp/ate-review-deps:simulation python -m pytest -q simulation/tests`.
  The temporary dependency directory supplies pytest only. All simulation
  Python files were checked against the reviewed tree: apart from these two
  intended product/test edits, downloaded copies differ only by a final blank
  line. No unrelated source edit is included in the commit.

No millennium/endurance or simulation calibration was run. The commit uses
`[skip ci]`; workflows and merge state remain unchanged.

## Acceptance boundary and next step

The composite EventLog component is accepted with the two final corrections.
This includes disk/pending/tail range routing, ordinary EventLog semantics,
bounded caches and year index, active-read-transaction reader capture, explicit
borrowed-backend lifetime, and checked bounded post-commit prefix adoption.

It does not constitute acceptance of a live cold World session, atomic World
save/recovery, cold identity binding/restore, detach, conversion or complete
bounded-memory continuation. Those remain P3B work. Stage 0.5 is not ready to
merge and decision B is unchanged.

Next Sol assignment: `PERSISTENCE_P3B_IDENTITY.md` only. The parent
`PERSISTENCE_P3B.md` is the full architecture, not a request to implement the
entire remaining body in the next turn.
