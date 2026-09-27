# P1 architecture review — changes required before P2

Reviewed commit: `591b37076c611edcaf6852ca281888bf00cf5846`.
Actual branch head and its parent `8c8aea4...` verified. No World integration,
checkpoint replacement, simulation change, millennium run or merge in this review.

The implementation has the right standalone boundary and useful transaction
failure tests. **It is not approved for World integration yet.** Four groups of
reproducible correctness gaps remain. These are P1 repairs, not a request to
begin P2 or expand the storage design.

## Validation checked

* Existing focused tests independently rerun: **18 passed in 0.39 seconds**.
* [Isolated run 36297543686](https://github.com/rax0h/all-that-endures/actions/runs/36297543686)
  verified successful at `0ba5e2583a231cc6bc87d2a59a13f7b85a0f2f8e`.
  Its workflow reconstructs the two product files from checksum-verified payloads
  before testing. Local SHA-256 values match that successful workflow's required
  values: implementation `a9dd34908be2b7d4a0bf598bfead0d2bfb6b666e4fe8eb651b322a4e0f40716b`,
  tests `1283b7c0da7c419951fb9663227a29f4a02ae5188431ed2b22ed3e97dd21eb74`.
  The handoff reports 202 full-suite passes. No redundant full suite was run
  for this documentation-only review.
* The reproductions below were executed directly against the reviewed code.
  Passing the existing tests does not cover these cases.

## R1 — decoding a registered record changes its saved state

`TypedCodec._decode_value` calls `record_type(**kwargs)`. That executes `__init__`
and `__post_init__` a second time. A registered dataclass whose post-init adds
one to a field round-trips **4 to 5**. A field declared `init=False` instead
raises `CodecError: registered record construction failed` on restore.

Minimal reproduction:

```python
from dataclasses import dataclass
from ate_sim.incremental_store import TypedCodec
@dataclass
class Counter:
    n: int
    def __post_init__(self): self.n += 1
c = TypedCodec()
c.register_record('Counter', Counter)
x = Counter(3)
assert x.n == 4
assert c.decode(c.encode(x)).n == 5  # defect: persisted 4 became 5
```

Required repair: restore allowlisted dataclass fields without rerunning creation
logic, including frozen/slotted dataclasses and `init=False` fields. For supported
plain dataclasses, allocation plus direct field restoration is appropriate;
otherwise reject registration explicitly or require an explicit registered
restorer. Never silently run arbitrary creation hooks during load. Add tests
that prove initialization side effects do not occur and every saved field is exact.

## R2 — container subclasses silently lose semantics

The encoder uses `isinstance` for built-in containers, while decoding always
returns their base types. A real ATE `event_log.FrozenList([1])` becomes a normal
list: appending 2 after restore succeeds. Named tuples and custom dictionary/
list/set subclasses can likewise lose their type or behavior.

Required repair: encode exact supported built-in types only, unless a subclass
has an explicit allowlisted adapter/tag. Reject unsupported subclasses at encode
time rather than silently flattening them. A frozen-container adapter can come
with P2/P3; it need not be invented in this P1 repair. Add regression tests using
ATE's actual frozen containers and at least one custom/named container type.

## R3 — a successful commit can publish an invalid namespace inventory

`commit` validates only newly touched namespaces. After committing a `people`
record, an otherwise empty commit with `namespaces=()` succeeds and advances the
head. Its own `verify_all()` then fails with `record namespace missing from head
inventory`. The public API can therefore create a structurally invalid save.

Required repair: validate the complete retained inventory under the write
transaction, without scanning all stored payloads on ordinary commits. Maintain
per-namespace record/segment counts as bounded head metadata, updated from actual
insert/update/delete results; use those counts to reject removal of a nonempty
namespace. Removing an empty namespace may be supported deliberately. Immutable
segments also keep a namespace nonempty. Cover both records and segments, retries,
rollback and stale writers. Do not add a full historical scan to each save.

## R4 — scrub does not detect identity reassignment or missing committed data

The stored checksum covers only payload bytes. After saving `people[1]='Ada'`,
changing its SQL `typed_key` to encoded 2 leaves the checksum valid. Both
`read_record('people', 2)` and `verify_all()` accept Ada under the wrong identity.
Metadata such as segment ordinal/range/count or record schema is similarly
outside the payload checksum.

Separately, deleting all committed rows from `records` and `segments` while
leaving the published head intact produces this successful scrub:

```python
{'generation': 1, 'records': 0, 'segments': 0}
```

The existing missing-payload test requests an ID that never existed; it does
not test loss of committed data. Foreign keys alone cannot detect an orphaned
absence when no surviving membership references the removed record.

Required repair:

1. Bind checksum envelopes to record namespace, typed key, schema/codec and
   generation as well as payload; bind segment envelopes to namespace, ordinal,
   range, element count and generation as well as payload. Reads and scrub must
   validate the same envelopes. Storage hashes remain distinct from World.digest.
2. Protect per-namespace counts from R3 inside the head checksum. Full scrub must
   compare committed expectations with actual rows, detect loss and reject it.
   This is accidental corruption/consistency detection, not a tamper-proof or
   cryptographically authenticated save format.
3. Add tests for reassigned keys, altered record/segment metadata and deletion
   of previously committed unreferenced rows. Confirm failed scrub never repairs,
   defaults or regenerates facts silently.

Change the standalone persistence format version when its checksum/head layout
changes. Existing P1 fixture stores may be rejected explicitly; no deployed World
save uses this backend yet. Do not change legacy checkpoint schema 8.

## Bounded repair assignment for Sol

Fix R1–R4 in `incremental_store.py`; add targeted regressions to
`test_incremental_store.py`. Preserve atomic transaction/recovery behavior and
all existing P1 tests. Demonstrate that no-op saves and one-record changes do
not read/encode unrelated cold payloads. Run focused tests, then the existing
full unit suite once. Record exact results and commit SHA for review.

Do not wire World, build mutation adapters, replace checkpoint APIs, tune the
simulation, run a millennium or merge. Keep P2 blocked until this review passes.
The previously reported canonical digests remain historical evidence for the
unchanged simulation; these storage tests do not produce a new canonical world.
