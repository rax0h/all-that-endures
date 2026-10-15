# Catalog sequence scrub repair

## Scope and original failure

Source baseline: `b15f4e12730a2d542f55335f69a4a7f6e48a9346`.
Failed acceptance: [run 38645679329](https://github.com/rax0h/all-that-endures/actions/runs/38645679329), job `116163910403`.
Its full simulation suite and complete 3+4+3 recovery passed. The late upgrade
exited **124** at the workflow's **350-minute command timeout**. It did not raise
a new Python integrity assertion or MemoryError.

Observed timeline:

| Boundary | UTC | Elapsed from upgrade start |
|---|---|---:|
| Upgrade starts | October 14, 23:43:16 | 0 |
| Catalog commit finished | October 15, 02:56:12 | 11,575.96 seconds |
| `_verify_catalog` starts, following store verification | October 15, 03:43:10 | about 4 hours |
| Timeout | October 15, 05:33:19 | 350 minutes |

The old log contains no descriptor/namespace counts or per-sequence timings.
Therefore it establishes that catalog verification did not finish, but does not
identify which catalog substage occupied the final 110 minutes. Process RSS was
roughly 1 GiB near the end, with about 14 GiB available system memory and 35 GiB
free disk. Those samples do not establish a resource leak.

## Reproduction before behavior changes

`_verify_catalog` invoked `LazyOrderedSequence.scrub` for every active descriptor.
Each scrub fetched every visible key from each of six shared namespaces, decoded
all keys and retained only the current incarnation. This produces descriptor
count multiplied by namespace row count inventory work. Locator/tree validation
is additional work and remains necessary.

The probe uses independently persisted native sequences, each with sixteen copies
of integer 1 and checked member types, published in one coherent commit. Full
per-namespace and per-sequence measurements are committed in
`stage_0_5_catalog_scrub_measurements.json`.

| Descriptors | Physical rows | Old rows fetched | Repaired rows fetched | Old seconds | Repaired seconds |
|---:|---:|---:|---:|---:|---:|
| 8 | 288 | 2,304 | 288 | 0.027 | 0.036 |
| 32 | 1,152 | 36,864 | 1,152 | 0.164 | 0.112 |
| 128 | 4,608 | 589,824 | 4,608 | 1.663 | 0.447 |
| 512 | 18,432 | 9,437,184 | 18,432 | 22.820 | 1.919 |

At 512 descriptors, each of descriptor/node/parent/directory namespaces has 512
rows and each occurrence/member namespace has 8,192 rows. The old verifier
fetched those inventories 512 times each; the repair streams each once. Median
per-sequence scrub duration fell from 0.04349 to 0.00259 seconds. These are local
controlled measurements, not an estimate or acceptance result for year 1000.
Small inputs can be slower because the checked disposable sets have overhead.

RED integration proof: eight household sequences caused eight full key scans in
each namespace; the regression requires at most one. The new diagnostics test
also failed before the diagnostics context manager was added.

## Repair and integrity argument

Standalone `LazyOrderedSequence.scrub()` retains its behavior, including dirty
and new backings. Its private `_inventory` callback is allowed only for a clean
persisted backing. All existing structural, parent, locator, membership and
recursive value checks execute before expected keys are collected.

Catalog-only `_verify_sequences` gathers expected keys and active incarnations
in the existing checksummed `ConversionWorkspace`/`DiskSet` mechanism. It streams
each visible shared namespace once under one checked read snapshot. It rejects
duplicate visible keys before insertion, rejects any actual active key absent
from the expected set, authenticates all three disk inventories, and compares
cardinality. Subset plus equal cardinality proves exact inventory equality.
It does not cache aggregate shared namespace rows in Python or use `fetchall`.

Started retirement continues to exempt unreadable partially reclaimed trees.
Not-yet-started retirement still receives the complete scrub. Projections for
inactive incarnations retain their prior scope; surrounding copy/backing/store
validators remain responsible for broader orphan detection. Format, ordinary
save/open, commit/recovery, publication, source preservation and the 8 GiB guard
are unchanged. Existing per-sequence traversal memory is not newly bounded.

## Verification and independent review

- Baseline selected standalone scrub gate: 8 passed, 26 deselected, 4.02 seconds.
- New shared-inventory/probe coverage: 27 passed, 1.51 seconds.
- Broader sequence/catalog/complete-format/retirement/memory/preparation gate:
  187 passed, 125.64 seconds. This collected the original 26 new tests before the
  diagnostics test was appended; the later 27-test gate covers that addition.
- Coverage includes extra/missing projections in all five child namespaces,
  overlapping versions, retained old/current pins, standalone dirty/new state,
  started/nonstarted retirement, nine scratch deletion/key/checksum mutations,
  and unpublished-destination/source-byte preservation after sequence-inventory
  corruption. The diagnostics context restores all wrapped functions on exit.
- Independent scoped production-diff review found no Critical or Important
  issues and independently passed the original 26-test gate. It identified one
  minor publication-test targeting gap; the test was subsequently narrowed to
  inject only while `_verify_sequences` is active and the 27-test gate passed.
  The final diagnostics extension was verified locally, not independently.
- Candidate workflow YAML, every shell block and eight embedded Python blocks
  parse; changed Python files parse and `git diff --check` is clean.

## Remaining acceptance and instrumentation

Fresh whole-suite and complete 3+4+3 recovery must pass for this runtime before
the retained lazy-checkpoint conversion starts. The workflow also gates on exact
inventory row/scan counts at 8/32/128/512 descriptors. The original retained
artifact, source receipt, byte hash, 8 GiB cap and 350-minute command timeout are
preserved. A published complete checkpoint still precedes independent exact
year-1001/year-1002 continuation and downloaded restore on a fresh runner.

The diagnostics-only `verification_probe` records namespace descriptor/row
counts, physical inventory queries/rows, full store verification time,
type-witness time, sequence-verification time, and every sequence's length,
duration and payload/metadata reads. Every sequence goes to
`evidence/catalog-sequences.jsonl`; stdout prints bounded progress summaries.

This repair proves removal of the repeated scan on controlled fixtures.
Real retained-fixture timing, large-conversion peak memory, production-data
continuation equality and full Stage 0.5 acceptance remain unproven until those
jobs pass. Existing DiskSet design and the broader architecture were reused,
not independently redesigned or audited by this scoped review. The remaining
commit, store verification and identity work can still consume substantial time.
