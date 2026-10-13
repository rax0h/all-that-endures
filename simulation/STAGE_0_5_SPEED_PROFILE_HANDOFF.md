# Stage 0.5 — bounded speed investigation, 2026-10-13

## Disposition

The next investigation in `STAGE_0_5_FINAL_CANDIDATE_HANDOFF.md` has been run.
The measured short prefix is dominated by checked identity reconciliation and
catalog work. Packed `Agency.actions` is a concrete reproducer; ordinary scalar
owner reconciliation is a second material cost. This is a diagnosis, **not a
performance repair or release acceptance**. Production source is unchanged.

Baseline: `c771824d5218ff171be7f034f76e5fc694b3353b`. The accepted production
boundary remains `5bf5c0192b307d15b9ab525cee20938584506ae6`, certified by the final
2,406-test/2-subtest suite and required 3+4+3 continuation recorded in the prior
handoff. No new full suite, long continuation, millennium, balance edit, format
change or PR14/main promotion was run here.

## Verified input and diagnostic limit

Used the previously retained `stage_0_5_verified_restore.zip`, SHA256
`2a77fbf1e6d05d89d9a76e2e2f72dc431377d78e8187ae8038e15e3e7503ab85`.
The extracted database matched
`ca75aa18d6b81642d8d102765dd790cd078fd6c64fe0ceac32d9fdfe24a25199` before use.
The harness copies it to a new operational path; the retained ZIP and extracted
source remain unchanged. Open observed year7/generation4.

Command (paths are examples after extracting the verified archive):

```bash
python simulation/profile_complete_restore.py restore.sqlite profile-output --budget 90
```

CPython3.12.14; cProfile enabled per phase; SQLite VM counter every10,000
instructions during simulation. Timings include profiler overhead and must not
be compared directly to the uninstrumented CI P5 timings. Open and close SQL
counts were not instrumented and are reported as null in the receipt. The first
harness printout used zero for those unmeasured counts; this reporting-only
correction does not change execution or the profile.

| Phase | Seconds | Outcome |
|---|---:|---|
| Open | 71.137 | Completed |
| One-year simulation attempt | 90.421 | Interrupted at the90s diagnostic budget; includes unwind |
| Save / full audit | — | Not reached; interrupted World never saved |
| Close | 0.188 | Completed |

The diagnostic budget stop is **not a correctness failure** and is not evidence
of a completed year. The script can run all four phases only if each completes
within its budget. A completed run checks exact independent digest, counters and
event projections; that comparison was not reached here.

## Attribution

Cumulative rows overlap and must not be added.

| Profile region | Calls | Cumulative seconds |
|---|---:|---:|
| Open: catalog `read_identity_group` | 1,360 | 61.525 |
| Open: `synchronize_packed_actions` | 1 | 38.104 |
| Open: `stitch_eager_action_peers` | 1 | 30.479 |
| Simulation prefix: `synchronize_lazy_placements` | 1,909 | 51.115 |
| Simulation prefix: `_owner_changes` | 2,592 | 28.412 |
| Simulation prefix: `_synchronize_owner` | 2,176 | 25.919 |
| Simulation prefix: `synchronize_packed_actions` | 1 | 22.874 |
| Simulation prefix: catalog `read_identity_group` | 781 | 22.682 |
| Simulation prefix: `_pressure` | 1 | 0.00215 |

The interrupted prefix reached `agency_step`; it did not cover later gameplay
phases or even the full agency loop. Approximately8.32million SQLite VM
instructions,406,179 SQLite execute calls,22,403 decoded payload reads,
18,815,350 decoded bytes,22,856 checked payload reads and292,580 pin-row checks
were recorded. SQLite execute self time was9.148s; the delay is not explained by
SQL execution alone. Python codec/checksum work, nested snapshot/pin checks,
catalog tree traversal and repeated reconciliation are substantial.

At open, catalog `_node` took48.035 cumulative seconds across4,874 calls;
`node_commit` alone took23.606 cumulative seconds. Action synchronization and
peer stitching independently visit groups through a clean cache capped at256.
The source shows repeated complete packed-owner projections and complete group
discovery on replacement even when most placements remain unchanged. A larger
cache alone would hide this case while weakening the clean-memory bound.

## Small controlled reproduction

```bash
timeout 120s python simulation/measure_complete_action_reconciliation.py action-output
```

Fresh complete-format fixtures with16 and128 existing scalar ActionRecords;
one appended action, then one scalar strength edit, then unchanged reconciliation.
Fixture creation/open are excluded. No other growing world state is present.
This measures current packed-body C work, not an alleged violation of a fixed-H
contract. The action values/length were checked; these diagnostic fixtures were
not saved or used as continuation acceptance evidence.

| Existing actions | Operation | Seconds | Payload reads | Owner catalog reads |
|---:|---|---:|---:|---:|
| 16 | Append + reconcile | 0.225 | 44 | 2 |
| 128 | Append + reconcile | 0.882 | 301 | 2 |
| 320 | Append + reconcile | 10.730 | 3,041 | 2 |
| 16 | Scalar edit + reconcile | 0.092 | 60 | 3 |
| 128 | Scalar edit + reconcile | 0.838 | 444 | 3 |
| 320 | Scalar edit + reconcile | 1.815 | 1,242 | 3 |
| 16 / 128 / 320 | Unchanged reconcile | <0.00002 | 0 | 0 |

Both small fixtures stayed within the256-group clean-cache cap and required zero
new group reads in these measured operations. Thus repeated full owner reads
are independently reproducible even without cache eviction.

A follow-up with320 actions (a separate90s process budget, completed) crossed
the clean-cache cap. Its single append required329 new group reads and9,710,278
payload bytes. The following scalar edit required zero group reads, but still
read1,242 payloads. This directly separates cache-eviction amplification from
the repeated packed-owner traversal. Reproduce with `--sizes 320` and a fresh
output directory. This is still a small synthetic component, not late-world or
complete-year evidence.

## Next bounded repair

Start with the packed action path, not a new persistence architecture. Preserve
the existing coordinator, registry, current authority and frozen publication.

1. Add a reproducing regression for repeated append/scalar edit with a packed
   action body larger than the256-group cache. Count owner/tree/group checks,
   not only wall time. Include shared ActionRecords in events/other owners.
2. Separate structural placement changes from scalar payload dirtiness using
   the existing mutation/placement journals. Avoid replacing/revalidating every
   unaffected action group after a suffix append. Any reuse must retain bounded
   memory and explicit generation/content validity; no unchecked cache bypass.
3. Preserve original-object identity through trims, moves, duplicate aliases,
   equal-but-distinct replacement, retained removed objects, mutable imported
   fields and cross-family sharing. Do not infer scalar-only supported input
   from ActionRecord's type annotations.
4. Keep corruption/missing-witness rejection, mutation preflight atomicity,
   lost acknowledgement and failed-save behavior. Include warmed-cache
   corruption and close/reopen in affected gates.
5. Once that repair is green, rerun the same verified restore operation with a
   fixed budget and exact independent authority. Report whether the entire year,
   save and audit completed; compare like-for-like instrumentation.
6. Evaluate residual compact scalar-owner journal reconciliation separately.
   No-op reconciliation is already zero-work; do not claim that old cumulative
   dirty-set rescan defect returned without a regression proving it.

This diagnostic tranche stops before changing identity semantics. A safe repair
requires distinguishing structural changes from payload dirtiness and proving
the affected shared-identity cases. It is not justified to delete checks or
increase unbounded cache retention just to obtain a faster number. Architecture
and release acceptance remain with Astra after measured repairs.

## Evidence files and checks

`stage_0_5_speed_profile.json` includes phase counters and the top60 profile rows
per phase. The two `stage_0_5_speed_profile_*.txt` files retain cumulative/self
profile tables. Both diagnostic scripts ran on the unchanged production source;
the script syntax check and `git diff --check` passed. No new production-test
pass is claimed. The previous green candidate remains the correctness baseline.
