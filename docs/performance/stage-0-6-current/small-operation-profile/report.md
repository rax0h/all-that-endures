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
