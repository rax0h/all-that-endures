# Stage 0.5 owner-witness repair: green validation handoff

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
  Includes existing World rollback/lost-ack/save/reopen cases. GitHub subsequently
  passed without these deselections. Python compileall and git diff --check passed.

The diagnostic harness adds --unprofiled (no cProfile or SQLite VM sampling;
ordinary I/O counters remain) and fails the process on budget failure. Phase
exceptions, including close failure, clear the JSON success flag. The eager
independent control remains outside individual phase alarms, inside the CI job
timeout. No gameplay, format, pressure arithmetic, RNG or save authority changed.

## Validation and acceptance

Exact candidate `ce7a5b5c0e195e3abf1aad99bbf6ad9039838877`, tree
`c40c4bfde4c79a20669685ff04086697e599505c`, passed
[GitHub run 38421286147](https://github.com/rax0h/all-that-endures/actions/runs/38421286147).
Workflow-only commit `a45edbf5409ab614df4ebe1cba15640ea8e65f1f` pins
that source explicitly. All three jobs succeeded. The isolated workflow
ran the affected gate, complete simulation/tests suite, and four disposable
year-7-to-8 continuations: baseline and candidate, each profiled and unprofiled,
on the same runner with the same updated harness and original checksum-verified
restore. Every lane matched exact independent eager authority and the known
year-8 digest. Original restore bytes remained unchanged. These are short
diagnostics, not a new P5 or endurance certification. One timing pair does not
establish a statistically stable speed ratio.

| Decision | Status |
|---|---|
| Bounded owner-certificate implementation | Implemented; local and GitHub regressions green |
| Independent review | Corrected diff approved for exact-candidate validation; no outstanding Critical/Important findings |
| Exact-source full suite and short continuation | Green: 2,431 tests plus 2 subtests; all four continuations exact |
| Final whole-architecture acceptance | Not claimed by this bounded review |
| Exact pressure arithmetic | Preserved; cold-miss bounded-memory O(H) policy remains explicit |
| Performance/release target and final-source endurance policy | Owner decision after measured evidence |
| Main/PR14, rank issue17, checkpoint defaults, Stage1 | Unchanged; no promotion authorized |

The previous 2,413-test green suite and old P5 remain evidence for their exact
original sources. This new runtime now has its own green suite and short paired
continuations. The explicit architecture and release decisions remain open.

The independent reviewer also ran all 18 new cache tests (18 passed, 0.70s),
reproduced both original epoch gaps, and inspected their fixes. It declined to
certify whole-system correctness, measured performance or architecture/release
acceptance beyond the inspected cache/snapshot/spill/coordinator/harness scope.

## Verified GitHub results

Affected: 129 passed in 80.11 seconds. Complete suite: 2,431 passed plus 2 subtests
in 5,023.20 seconds; zero failures, errors or skips. Both job artifacts record the
exact candidate and tree above. Suite wall time from a different runner/run is
not a controlled baseline performance comparison.

| Phase | Baseline unprofiled seconds | Candidate unprofiled seconds |
|---|---:|---:|
| Open | 4.315 | 4.367 |
| Simulate one year | 9.238 | 7.961 |
| Save | 5.390 | 5.436 |
| Full audit | 3.154 | 3.227 |
| Close | 0.034 | 0.037 |

The observed simulation reduction is 13.8% in this single ordered pair. Payload
reads fall from 44,281 to 29,863 (32.6%), and bytes read from 15,565,858 to
12,792,144 (17.8%); these simulation counters agree across profiled/unprofiled
modes. Save and audit remain roughly unchanged in unprofiled elapsed time, and
their candidate counters differ slightly between modes; mode-independent cache
residency/work is not claimed. Ordinary I/O diagnostics remain enabled.

All four lanes restore year7/generation4, finish year8 and match digest
`fce95e6b2541500e5104be2d92a2cbdc00255f70e20ed3755ee7472a2b9fa733`.
The source database SHA256 is
`ca75aa18d6b81642d8d102765dd790cd078fd6c64fe0ceac32d9fdfe24a25199`.

Raw four-lane metrics and selected overlapping attribution are committed in
`stage_0_5_owner_witness_comparison.json`; simulation/save profile text in
`stage_0_5_owner_witness_profiles.txt`; exact source, test summaries and artifact
checksums in `stage_0_5_owner_witness_validation.json`. All three downloaded ZIP
checksums were independently verified. Full raw artifacts expire October27:

- [Affected logs/JUnit](https://github.com/rax0h/all-that-endures/actions/runs/38421286147/artifacts/11825409977)
- [Complete-suite logs/JUnit](https://github.com/rax0h/all-that-endures/actions/runs/38421286147/artifacts/11830644931)
- [Paired metrics and profiles](https://github.com/rax0h/all-that-endures/actions/runs/38421286147/artifacts/11826179195)
