# Stage 0.5 owner-witness repair: validation candidate

This continues the green packed-action repair at b91b0c8aa0d94bd99777e6ec14a125f947e1074a.
It targets repeated complete owner-tree validation identified in that run:
6,134 read_owner_identity calls, 16.789 cumulative profiled seconds. This is
overlapping attribution, not an independent sum or an endurance prediction.

## Implemented boundary

IdentityCatalog retains only completely checked, deeply immutable owner proofs.
The cache is derived metadata, not persisted authority or a live-object registry.
Each hit still enters the existing read_snapshot and validates the pin, head and
retention state. Its epoch includes connection identity, catalog and store codec
identities, captured generation, total_changes, data_version and schema_version.
The schema cookie covers same-connection DDL, which does not increment the data
counters. Borrowed transactions clear and bypass reuse, including nested reads
and savepoint rollback. No certificate validated in such a transaction escapes.

Retention is bounded by 256 entries, 4,096 occurrences and 256 KiB of estimated
entry/sidecar weight by default; supplied smaller catalog limits also apply.
OrderedDict container overhead is separately reported. Large spilled results
remain caller-owned and are never cached. Dirty placement overlays remain in the
existing coordinator and are reapplied independently of persisted proofs.

## Local evidence

- Original cost regression: five repeated reads decoded 20 payloads (RED).
  Candidate decodes zero payloads while retaining pin checks (GREEN).
- Eighteen new cases cover same/external writes, lost authority, checksum damage,
  generation movement, released/foreign pins, close, rollback, connection and
  both decoder replacements, schema destruction, eviction and spill bounds.
- Review found missing store-decoder and DDL invalidation. Three new cases
  reproduced those failures before extending the epoch; all now pass.
- Affected local gate: 62 passed, six costly cases deselected, 21.70 seconds.
  Includes existing World rollback/lost-ack/save/reopen cases. GitHub must run
  without these deselections. Python compileall and git diff --check passed.

The diagnostic harness adds --unprofiled (no cProfile or SQLite VM sampling;
ordinary I/O counters remain) and fails the process on budget failure. Phase
exceptions, including close failure, clear the JSON success flag. The eager
independent control remains outside individual phase alarms, inside the CI job
timeout. No gameplay, format, pressure arithmetic, RNG or save authority changed.

## Validation and acceptance

Exact-candidate GitHub validation is pending. The isolated validation workflow
will run the affected gate, complete simulation/tests suite, and four disposable
year-7-to-8 continuations: baseline and candidate, each profiled and unprofiled,
on the same runner with the same updated harness and original checksum-verified
restore. Every lane requires exact independent eager authority and the known
year-8 digest. Original restore bytes must remain unchanged. These are short
diagnostics, not a new P5 or endurance certification. One timing pair does not
establish a statistically stable speed ratio.

| Decision | Status |
|---|---|
| Bounded owner-certificate implementation | Implemented; local regressions green |
| Independent review | Corrected diff approved for exact-candidate validation; no outstanding Critical/Important findings |
| Exact-source full suite and short continuation | Pending GitHub result |
| Final whole-architecture acceptance | Not claimed by this bounded review |
| Exact pressure arithmetic | Preserved; cold-miss bounded-memory O(H) policy remains explicit |
| Performance/release target and final-source endurance policy | Owner decision after measured evidence |
| Main/PR14, rank issue17, checkpoint defaults, Stage1 | Unchanged; no promotion authorized |

The previous 2,413-test green suite and old P5 remain evidence for their exact
original sources, not this new runtime. Do not mark this candidate release-ready
until its own gates and the explicit acceptance decisions are resolved.

The independent reviewer also ran all 18 new cache tests (18 passed, 0.70s),
reproduced both original epoch gaps, and inspected their fixes. It declined to
certify whole-system correctness, measured performance or architecture/release
acceptance beyond the inspected cache/snapshot/spill/coordinator/harness scope.
