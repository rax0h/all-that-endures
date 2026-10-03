# P3B identity primitives — architect acceptance

Accepted implementation: `b756023395a3acb2aa0bfae9326e76dc6f10cd4e`.
Baseline preserved: `0cd7d6bb52322d1fb416dbb4762a9239e1d8e5a7`.
Review date: 2026-10-03. PR #14 remains open and unmerged.

No blocking finding and no product-code correction was needed. Changes are
limited to `persistence_identity.py`, its new tests and validation document.
The accepted EventLog typed-value and captured-generation guards remain intact.

Accepted behavior:

* Explicit cold identity projection visits only eligible mutable tail Events,
  using absolute indices. Pending and disk history are excluded, as are
  individually sealed tail occurrences. Non-log occurrences remain current.
* EventLog root aliases use the same projection. Default identity traversal
  fails clearly on a disk-backed log before reading history. Explicit links
  into excluded occurrences fail seeding instead of being silently discarded.
* Helper iteration checks borrowed reader/store lifetime before each value.
* Batched owner retirement removes occurrences before recalculating affected
  links, releases index-only references, reanchors surviving aliases and emits
  a deterministic final patch. It does not scan unrelated owner graphs.

## Verified evidence

Inspected CI run `37141431849`, job `111256510775`, on candidate
`3efc00b1cff4c922009c029e00f4121afea239ba`:

* 16 focused tests passed in 13.51 seconds.
* 227 affected tests passed in 203.15 seconds.
* 394 full-suite tests passed in 463.92 seconds.

The landed product/test blobs match that candidate exactly. The final validation
document was added after testing; the candidate-only workflow was not landed.
Other candidate branches are not substitutes for the reviewed PR head.

Independent local review:

* All 16 focused tests passed again in 15.85 seconds.
* 200 deterministic synthetic parent/descendant alias cases passed an
  independent recursive occurrence oracle and exact removal/addition replay.
  Cases used varied retirement batches, duplicated owner inputs and varied
  original anchors. Surviving path maps, final links and repeated retirement
  were checked without using the implementation's link builder as the oracle.
* At 4 and 40 real disk segments: zero segment reads, zero pending decode/cache
  growth, and exactly 13 projected occurrences/paths for the fixed suffix.
* At 100/300/1,000 unrelated alias groups: one owner and occurrence removed,
  one affected group, two surviving paths examined, two old links removed and
  one new link added at every size.

The full suite was not repeated during review because the exact landed
product/test blobs already have verified full-suite evidence and no product
code changed. No millennium/endurance run or calibration was performed.

## Remaining boundary

This accepts identity enumeration and occurrence-index retirement primitives.
It does not accept a cold World session, restored continuation, atomic cold
save/recovery, or complete binding-memory reclamation. `_BINDINGS`, `_memo`,
tracking hooks and durable identity publication remain later integration work.

Next bounded assignment: `PERSISTENCE_P3B_IDENTITY_RESTORE.md` only. It adds
cold-safe path resolution, graph verification and mutable-tail relinking, with
no session creation/save or format integration. Decision B and the parent
`PERSISTENCE_P3B.md` architecture remain in force.
