# Small operation cost investigation

Mature execution is intentionally paused. A functional smoke does not establish
the mature10sopen/2ssave/1swarm targets. The earlier successful42961490569 smoke,
on unchanged engine94267, already measured7.002ssave and7.913swarm. That warning
should have informed the next-run order sooner. New43035885119 attempt2 is also
functional-only:2.214sopen,10.448ssave and11.604swarm on its hosted VM. These
different VM observations are not a controlled before/after code comparison.

## Reproducible bounded diagnostic

The local input is the exact accepted proof-generation0 artifact13829902355
from42961490569. input.json records its independent external commitment,
archive hash/size and DB hash/size. Only that small7.4MB archive was downloaded;
the26.2MB database is retained unchanged outside the repository. Extraction and
database hashes were checked before execution and again after it. The runtime
subtree is94267; the complete local313qualification fingerprint was matched.

run_profile.py uses a distinct working copy, actual proof open, first year, save,
warm year and separate fresh-process verification. The saved year2/gen1/seed843000
digest exactly matchescebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451.
Full function/caller statistics, phase resources and logical store counters are
retained as JSON/text. The initial setup-error.log records a directory/file path
mistake before any profile execution; the corrected input was authenticated.

| Instrumented phase | Wall seconds | Function calls |
|---|---:|---:|
| Open | 3.364 | See open-calls.json |
| First year | 22.059 | 49,642,661 |
| Save | 15.985 | 41,148,996 |
| Warm year | 17.504 | 39,161,248 |

These times include cProfile overhead and use different software/hardware from
hosted CI. They are attribution evidence, not performance acceptance or a claimed
mature failure. Nested cumulative costs overlap and must not be summed.

## Concrete next boundary

The save executes54,080ProofMap._read calls and112,578decode_node calls; warm
executes42,840map reads and85,680decodes. Source inspection confirms SQL
ProofNodeStore.read hashes/decodes, then ProofMap._read hashes/decodes the same
bytes again. decode_node also re-encodes its decoded structure to check canonical
bytes. Save's node encoder runs93,861times. Warm identity owner/group paths and
whole-owner membership enumeration are another measured cost, not ordinary
gameplay logic to remove.

First bounded runtime attack: factor the redundant node parse while retaining
both physical-store and map-domain hashes, canonical decoding, root count/prefix
checks, size/type/address bounds and public standalone NodeStore validation.
Direct canonical branch checks may replace equivalent encoder roundtrips.
Do not introduce a long-lived read certificate or a broad mutable-object cache.
Measure this finite change before deciding a bounded node cache or proof-only
point-membership helper is justified. Existing audit/corruption/identity and
publisher/rollback/recovery contracts remain binding.

An engine change invalidates engine-green reuse and therefore requires one new
full/proof validation after focused correctness and local measurements. Do not
launch the old monolithic mature constructor or repeat expensive preparation
while a small bounded diagnostic can resolve the next question.

## Qualified successor profile

The [successor smoke](https://github.com/rax0h/all-that-endures/actions/runs/44873730573)
measured small save at 4.5389 s (4.3549 s CPU) and warm year at 4.7371 s
(4.7366 s CPU). It published the exact saved year-2 control. The previous
smoke recorded 4.5785 s and 4.5703 s with identical logical save and warm
counters. Runner differences prevent a controlled latency comparison.

The [short diagnostic](https://github.com/rax0h/all-that-endures/actions/runs/44875177238)
profiled the same operational entry points on a disposable copy of the
accepted proof database **14694752653**, with proof receipt **14695106875**
and fresh authority **14695785020**. The retained original SHA, exact
source/engine, Python 3.12.16 / SQLite 3.46.1 full fingerprint, and exact
fresh year-2 control passed. [Artifact 14695926192](https://github.com/rax0h/all-that-endures/actions/runs/44875177238/artifacts/14695926192)
is 276,376 bytes and SHA-256
`ac0fa4ce6ab56a9ac488dab8e8e6e7de5e19edb2f72cca66c5afd3aa17e9c430`.
Raw ZIP, complete call graphs and receipts are locally retained under
`.validation/successor-operation-44875177238/`.

| Profiled phase or function | Calls | Inclusive seconds |
|---|---:|---:|
| Save | 1 | 11.207 |
| Save preparation | 1 | 2.378 |
| Atomic proof commit | 1 | 5.642 |
| Save acknowledgement | 1 | 3.135 |
| Warm Simulation.run | 1 | 11.102 |
| Warm native record loads | 438 | 4.660 |
| Warm coordinator owner changes | 1,141 | 4.085 |
| Full owner identity reads within coordinator owner changes | 1,141 | 2.746 |
| Exact membership calls from the missing-owner fallback | 111 | 1.067 |

Nested cumulative time overlaps, including the native record and
owner-change paths. Profiled time includes instrumentation. The profiled
save matched all logical counters from the raw successor smoke. Six warm
counters differed, including metadata rows 32,615 to 35,519 and pin rows
33,259 to 36,355. The difference's cause remains unverified. Use these
calls to select and test a boundary, with a separate raw comparison before
any latency claim.

The first narrow experiment is checked absence during owner replacement.
The call graph identifies the coordinator's exception fallback after a
full owner lookup. It checks physical witness/source absence, then repeats
the corresponding proof route through exact membership. Review whether the
same complete absence proof can be returned within the original owned
read. Keep the public owner/membership behaviors, every source and placement
check, borrowed/snapshot rules, and distinct present-owner corruption.
Use exact saved and warm continuation parity and a bounded work result
before promoting the experiment to a new full engine qualification. Mature
proof duration, operation targets and exact year-1002 restore remain open.
