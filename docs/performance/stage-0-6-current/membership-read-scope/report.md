# Exact membership read scope

Baseline hosted1d46590b/runtimeb45a0e4b is GREEN43654058724. Candidate local
enginee32f9509/runtimefd20cf1784a331de07f4979db71dda0f3d301771 changes one
closed read context, using existing checked_read_operation with catalog-derived
min(256KiB,self.byte_limit//6). All original descriptor, owner root, node locator/
commitment, path-collision, forward-occurrence and source/witness absence rules
remain. Existing descriptor facts may be reused only under their current native
source/custody fence; no new cache or cross-operation authority is introduced.

## Work and correctness

Native exact lookup RED23head checks→GREEN<=2. Generic present/absent lookups
validate operational rows once; configured128byte catalog receives at most21
cache bytes. Corruption after a successful lookup still rejects and cleans up.
248related tests/17files passed. Prior hosted durations were checked before
execution;300s/file900s/invocation,310s reserve. The expensive complete generated
year is reserved for hosted validation. Independent whole-package review has
0Critical/0Important/0Minor,22tiny probes passed after full qualified313 runtime
fingerprint verification. Production/test/workflow and XML/log hashes match.

Fresh same-source warm attribution retains180exact membership calls. SQL
240130→222140, head checks9165→7865, pin checks11056→9756, visible version reads
4694→4556. Reduction includes existing safely fenced descriptor facts, not a
claim to reread the catalog descriptor per use. Saved year2/gen1 and fresh year3
digests exactly equal baseline; original input and source/runtime are preserved.
Profiler timings are not raw latency.

## Raw observations and retention decision

Pinned A-B/B-A followed by reversed-order B-A/A-B confirmation:8independent
120s trials. Tests/profilers/reviewer CPU probes were idle during all raw trials.
Full engine inventory/Git bytes, imports, runtime, input hash, exact saved/fresh
continuation and original-source preservation checked. No trial/prefix was
repeated after failure; confirmation addressed a new save-timing concern.

| Pair | Warm baseline→candidate seconds | Save baseline→candidate seconds | Step/save/step reduction |
|---|---:|---:|---:|
|pair1|4.638→4.052|3.637→3.864|6.59%|
|pair2|4.688→4.211|4.213→4.395|2.73%|
|confirm1|4.231→4.085|3.767→3.929|2.98%|
|confirm2|4.428→3.917|3.831→3.714|6.23%|

Warm steps improve in all4paired comparisons (3.45–12.64%); measured first-step/
save/warm-step sequence improves2.73–6.59%. Save observations are higher in3pairs
and lower in1; no save-latency gain or cause for the variation is established.
The two-stage save profile shows unchanged prepare57042/commit98479/ack80020SQL
and3688/819/460headchecks, with16membership calls in preparation and none in
commit/ack. Identical counts do not prove identical latency. All mixed results
are preserved. Retain the concrete warm-operation benefit for one hosted gate;
no general overall/mature/interactive acceptance claim. Targets remain mature
10sopen/2ssave/1swarm and exact deterministic continuation.

## Evidence and next gate

Readable summary/comparison/config/runtime/review files sit beside this report.
evidence.zip preserves all original raw/profiler/XML/log/source receipts and the
initial warm profile as baseline-warm-profile/. Member hashes are recorded in
evidence-index.json. Extract here for inspection and compatible test resumption.
The warm attribution harness remains in ../warm-path-attribution/measure_warm.py.
Hosted acceptance is pending; no mature/default/main/endurance activation.
