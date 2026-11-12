# Exact placement read experiment — rejected as standalone latency repair

Published baseline7261d615/local46494a0 has engine0785bf9. Hosted43099834661 is
green:5042full tests and30proof XML suites plus scaling commands. This experiment
does not replace that validated runtime or authorize mature preparation.

## Raw sequential pair

Independent copies of the same authenticated small generation0/year1 input were
run sequentially under the same complete qualified313 fingerprint. Actual source
hashes and loaded module paths are fenced; original input bytes were preserved.

| Operation | Baseline seconds | Point candidate seconds |
|---|---:|---:|
| Open | 1.878 | 2.087 |
| First year | 12.580 | 12.003 |
| Save | 7.852 | 8.176 |
| Warm year | 9.544 | 9.150 |

One pair shows only4.1%warm reduction and4.1%save slowdown. It cannot establish
a useful latency gain or a distributional regression. This pair is not compared
to another day's/hosted VM's raw times. Both runs preserve saved generation1/
year2/seed843000/digestcebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451,
and independently continued year3 state equals the baseline and in-memory path.
No mature, interactive-target or byte-identical per-attempt manifest claim follows.

## What the separate profiles establish

Baseline profile is the already captured exact0785bf9source under factorization/
candidate-profile; new candidate-profile records the proposed two-file runtime.
Call counts are comparable attribution evidence; nested cumulative times overlap
and machine/instrumentation timing differences forbid adding or directly treating
those profile times as a controlled performance comparison.

| Warm work | Baseline | Point candidate |
|---|---:|---:|
| _owner_changes calls | 1,295 | 293 |
| read_owner_identity calls | 1,296 | 294 |
| _remember_owner cache misses admitted | 245 | 80 |
| Native identity point_row calls | 400 | 1,402 |
| Native identity _context calls | 1,941 | 2,613 |
| Guarded SQL execute calls | 458,816 | 416,146 |

The removed1002owner calls eliminate only165cache misses, not1002full inventories.
_state calls equal the _context counts in both profiles. Most removed owner
reads were already closed, epoch-checked owner-cache hits. The new path instead
does1002fresh exact owner/group proof lookups. It reduces logical SQL work about
9.3%, but the raw pair does not demonstrate sufficient speed improvement.

## Correctness and disposition

Nineteen focused controls passed29.45s; the strengthened complete-call-chain
work assertion separately passed1.44s. Independent six-case adversarial boundary
suite passed6.37s with exact source/software hashes. Ordinary/audited owner checks,
overlay replacement/tombstones/absence, physical proof refusal, wrong live kind,
private alias mutation and save recovery were exercised. Initial unsupported cold
graph/retirement fixture negatives are preserved and explained in progress.md.
They were not hidden by changing converters, audits or publication requirements.

Preserve the proposed production diff and tests as experimental evidence, then
restore the validated0785bf9production source. Do not land a new default helper,
add its tests to live CI, update engine authority or run another full engine suite
for this rejected candidate. Review evidence is under review-raw. Findings remain
in the consolidated bounded-genesis closure register; no safety finding is deferred.

## Next bounded investigation

The approved independent architecture review already identifies repeated proof
and descriptor validation as another cost. Inspect sharing verified immutable
proof facts inside one explicitly owned closed read operation, or a bounded batch
of proof/placement reads, before another expensive constructor. Existing
ValidationScope performs epoch SQL on every reuse; enabling it everywhere cannot
be assumed to improve latency. Any lower-cost scope needs concrete custody:
exact store/codec/pin/accepted manifest, guarded read-only transaction, callback/
publisher/rollback/recovery refusal, root count/prefix checks, explicit entry/byte
bounds and cold fully checking fallback. No scope may cross a gameplay callback,
public yield or simulation step. Measure this separately before selecting it.

Mature preparation and U10 remain paused/open. The green parsing improvement is
retained; this rejected experiment is evidence to refine the next attack.

### Follow-up entry-custody diagnostic on restored green source

probe_owned_reads.py wraps only diagnostic counters and the existing driver; it
creates no validation certificate, changes no production file and claims no raw
latency. Runtime file fences exactly equal baseline0785bf9, original input stays
unchanged, and exact saved/fresh continued state match again. During warm year,
all377read_identity_group calls enter without a borrowed transaction or active
read snapshot. All1296owner reads also enter at an owned boundary;940are cache
hits in this separate instrumented observation. Cache-hit count differs from the
older profile, so it is not treated as a fixed workload invariant. During save,
all106group reads enter borrowed transactions, making them ineligible for minting
a new closed read certificate.

This identifies a concrete next scope: a single proof-only read_identity_group
operation may own a short guarded read-only transaction and share its verified
metadata/proof facts inside that call. Existing save/publisher and borrowed reads
must fall back unchanged. Ownership is only a necessary condition, not proof that
all callback/codec/epoch/custody constraints are met. Implement and measure that
bounded scope before extending it; no blanket ValidationScope enabling or cache
across gameplay/steps is justified by this probe.
