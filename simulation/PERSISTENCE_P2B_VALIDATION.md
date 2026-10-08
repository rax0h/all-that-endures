# P2B final review and validation

Reviewed Sol implementation: `e5f07b4f040f8c0e9a32001f47579b055ea7bedd`.
This record supersedes the open assignments in the three earlier P2B reviews.
Disposition: **P2B accepted within its opt-in mutation/save/restore scope.**
Stage 0.5 remains decision B; the production boundaries below still apply.

## Verified Sol results

The four product/test files match both isolated CI candidates byte-for-byte:

* [Targeted run 36353518325](https://github.com/rax0h/all-that-endures/actions/runs/36353518325),
  `4ce981721921da7cda7cb7cb06184f1b6b5c2fab`: 111 passed in 87.14s.
* [Full run 36353647423](https://github.com/rax0h/all-that-endures/actions/runs/36353647423),
  `475691102703293e80980b8f5e21accc81c08da9`: 295 passed in 333.06s.

Independent review confirms simultaneous parent/descendant sharing restores
correctly. Local alias creation writes two payloads totaling 637 bytes at
100, 300 and 1,000 unrelated alias groups. It no longer rebuilds all alias links
or performs the previously measured quadratic prefix comparisons.

## Two small final repairs made during review

### Numeric replay order

The eleventh identity-delta save committed successfully but could not restore:
P1 namespace enumeration returned keys `0, 1, 10, 2, ...`, while delta replay
assumed numeric order. The P1 API explicitly makes no row-order guarantee.

Replay now validates integer/nonnegative sequence keys, sorts numerically, then
checks contiguous ordering. Gaps, duplicates, booleans and nonnumeric keys still
fail. A 24-save regression checks every restore, rebinds after the twelfth save,
and verifies both alias identity and subsequent values.

### Separate live collection layout from fixed bootstrap identity

An ordinary unshared wallet deletion still rewrote the bootstrap identity links
inside the manifest: 45,215 bytes at 100 unrelated alias groups and 385,416 bytes
at 1,000. The local-alias-only regression did not exercise structural metadata.

Structural saves now update a separate versioned `world_snapshot` record keyed
`collections/v1`. It contains the fixed-schema collection descriptions (kind,
count, cold-event chunk count) and no identity links. The original `manifest`
record remains unchanged; its identity links are the base for committed deltas.
The reader and binder combine the records inside their pinned read transaction.
Legacy one-record P2A metadata remains readable. Missing/unknown collection roots
and unexpected metadata records remain errors.

Measured wallet-deletion payload writes:

| Unrelated bootstrap alias groups | Payloads written | Payload bytes |
|---:|---:|---:|
| 100 | 1 | 7,517 |
| 300 | 1 | 7,517 |
| 1,000 | 1 | 7,518 |

The one-byte variation is the decimal collection count. The deleted wallet is
also removed transactionally; a deletion is not counted as a payload write.
The regression proves the base manifest is unchanged, restores and rebinds,
then inserts another wallet and verifies order and values after a second restore.

## Final validation

* Focused P1/P2A/P2B persistence battery: **120 passed in 53.54s**.
* Two additional commit-failure/lost-acknowledgement regressions: **2 passed in
  0.10s**. These combine a new alias and a structural edit, prove old-or-new atomic
  recovery, and verify retries do not publish duplicate identity deltas.
* Full unit/integration suite: **306 passed in 252.39s**, run once on the final
  implementation. This is local validation; Sol's earlier Actions results above
  apply to his preceding code. The final commit skips automatic CI because that
  workflow would launch an out-of-scope millennium; no gate was weakened.

The final code keeps simulation rules, RNG, legacy checkpoint APIs, archive
semantics and balance unchanged. No millennium was run for this repair/review.
Prior millennium evidence must not be represented as an incremental-persistence
performance measurement.

## Acceptance boundary and remaining production work

P2B is an opt-in mutation/saving layer. It does not make the current game save
path incremental by default, nor establish bounded resident memory or Stage 0.5
long-horizon readiness. Bootstrap/bind/full restore still walk all retained state.
Changed owning records may still contain growing nested histories; splitting
those records remains part of the persistence architecture work.

The new identity-delta namespace is append-only metadata and is replayed on bind
and restore. This solves changed-state save cost, but repeated alias changes can
grow replay history even if current identity state stays small. Before production
integration, give it a bounded current-state representation or an explicit safe
compaction policy. This is not simulated objective history and must not become
another permanent history-sized reload dependency. Keep atomicity, current alias
identity, legacy reads and corruption checks when addressing it.

The next architectural work remains persistence integration and cold historical
storage, with measured memory/load/save scaling and exact continuation. No P3
implementation, default checkpoint replacement, eviction, disk-backed EventLog,
Stage 1, long-horizon run or merge was performed in this review.
