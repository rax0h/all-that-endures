# Proof-only recursive placement reads

Status: measured and rejected as a standalone latency repair; production restored
to green0785bf9. See small-operation-profile/identity-point/report.md for evidence.

Continue the approved Stage0.6 performance investigation under
small-operation-profile/independent-review.md, second candidate. The native
execution workflow and semantic constraints are already authorized; this records
the bounded implementation choice rather than reopening routine approvals.

Goal: during RecursiveHistoryRuntime.decode, authenticate the exact current
owner/path placement without materializing every placement owned by that record.
Baseline is local46494a0 / published7261d615, same tree and engine0785bf9.
Hosted43099834661 passed5042full tests and all30proof test suites/scaling commands.
Existing qualified local software fingerprint remains mandatory.

Approaches considered:
- Keep complete owner enumeration: preserves current work but fails the measured
  performance goal; retain this contract for ordinary/audited readers.
- Exact catalog membership plus current overlay: bounded by owner depth, but
  repeats catalog descriptor/owner proofs that the accepted complete manifest
  already establishes for native proof reads.
- Selected: existing native exact occurrence API plus current overlay. Its owner
  AND group roots, allocator, physical interval/checksum, pin/head/epoch and
  admission checks bind the single occurrence to the accepted World. This removes
  redundant full catalog traversal without inventing a new trust authority.

Add IdentityCoordinator._placement_for_read(owner,path)->int|None. Only an active,
exact native authority with proof_only=True may select the point path. Validate
placement shape and call store.read_identity_occurrence even when an overlay
entry exists, so physical authority drift cannot hide behind local changes.
KeyError means authenticated point absence; other failures propagate. Apply the
coordinator's current replacement/tombstone after that baseline point check.
Other modes use unchanged _owner_changes(owner,()). No retained certificate/cache.

Recursive decode retains synchronization, pending private child handling, partial
sequence mutation handling, reference kind/incarnation checks, group discovery,
canonical registry object lookup and occurrence attachment. Mutation, replacement,
retirement, publication, recovery and audited admission retain complete closures.
No wire format, source control, gameplay, cache budget or mature trigger change.

Verify actual decode work, physical forgeries/absence, overlay replacement and
tombstone behavior, private/new owners, ordinary/audited fallback, lost/stale pin,
untracked SQL/callback/recovery refusal, alias replacement and save/fresh restore.
Measure before/after raw copies of the authenticated small input on the same
qualified software; profile separately. Keep source/import fences, exact saved
year2 digest and independently continued year3 equality. If performance does not
improve, do not claim this is a speed repair. Mature work remains paused.
