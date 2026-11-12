# Immutable descriptor fact reuse — Stage0.6

The broader closed-read guard is rejected. The current replacement reuses one
immutable identity catalog descriptor behind fresh, original native read
admission. It removes repeated descriptor proof work while preserving group
occurrence/link completeness, exact owner membership and all source checks.
This is a small operational improvement, not interactive-speed acceptance.

## Intermediate measurement — before schema-revision closure

Qualified Python3.13.5/GCC14.2.0/SQLite3.46.1 fingerprint matches the saved complete
generated-year qualification, including executable, extension and loaded library
hashes. Same immutable year1 input SHA256
2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554.
Candidate ran first; unchanged c6c7fcc baseline ran immediately afterward in a
separate detached worktree with exact runtime source fences. No concurrent tests
or reviewer ran during either raw measurement.

| Phase | Baseline seconds | Candidate seconds | Candidate change |
|---|---:|---:|---:|
| Open | 1.554 | 1.642 | +5.7% |
| First step | 12.377 | 9.526 | -23.0% |
| Save | 6.617 | 6.345 | -4.1% |
| Warm step | 8.698 | 7.889 | -9.3% |
| Fresh restore and step | 20.983 | 18.554 | -11.6% |

One adjacent reverse-order pair establishes these observations only; it is not a
latency distribution or mature-world result. Earlier baseline in this same group
was substantially faster (open1.087/first6.919/save4.507/warm5.751), demonstrating
host variation. First-step metadata rows reduce61171→57461; warm51359→47507;
save stays24929 because its borrowed path deliberately does not use the fact.
No meaningful save improvement is claimed from this pair.

Both runs preserve source and input. Fresh saved year2/generation1 digest is
cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451;
independent continued year3 digest is
a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.
Raw phase reports live in fact-raw and reverse-baseline-raw. Instrumented timings
are separate in fact-profile and must not replace these raw latency numbers.
Against the existing exact green-engine profile, warm guarded execute calls
reduce458816→386922. The replacement adds no authorizer install/remove churn;
its warm377group calls require378bounded registry snapshots including admission.

## Boundary and retained state

One descriptor competes with existing immutable owner facts under the existing
combined256-entry/256KiB maxima and smaller caller limits. Its individual bound
is32KiB and at most one quarter of that cache's byte budget. Complete retained
fence and registry metadata are accounted; globally owned schema code is not
charged again. Registry stamps retain actual bounded key/value references, not
recyclable integer addresses. The phase hook uses id plus weak reference.

Each hit requires original checked snapshot admission, active proof-only native
authority, matching pin/manifest/epoch, unchanged closed codec/registries/methods,
owned transaction and scope. Callback-capable SQL finishes before the final pure
Python fence. Callback history, writable blobs, deserialize and extension
activation/loading permanently select original full checks for that connection.
A monotonic guarded-SQL revision also binds facts and owner-cache epochs, so resetting SQLite schema_version cannot hide DDL replacement. Unknown SQL advances this revision; exact read PRAGMAs and literal SELECT are exempt. Literal WITH is exempt only when the entire raw text contains no INSERT/UPDATE/DELETE/REPLACE word token (case insensitive), a bounded SQLite grammar exclusion. Custom cursor history disqualifies facts; scripts always advance revision.
Borrowed/audited reads and publisher paths remain fully checking. A changed fence
cannot reuse an earlier fact; existing owner-cache clears also clear it. No new
SQL authorizer, read scope, transaction or final-exit cleanup exists.

The supported boundary is the guarded SQLite public API, not arbitrary Python or
native execution sandboxing. Existing schema/epoch checks cover backup target
replacement. setlimit/setconfig do not independently replace descriptor bytes.

## Rejected guard and review disposition

Original guard tests caught two real interrupted-operation defects: a guard left
installed after activation failure, and unreturned spill buffers retained after
final rejection while tracebacks remained alive. Removal of that implementation
removes both new failure seams. Full candidate patch/module/tests and failed logs
remain in rejected-guard and review-raw; no failing source was published.
A reviewer WAL test was invalid because the store requires DELETE journaling;
its corrected supported-mode case passed. These are separate from hosted CI.

Replacement controls cover warmed reuse, local/external/rollback/TEMP changes,
codec/registry/hook changes, borrowed/audited fallbacks, shared entry/byte bounds,
save-pin transition and opaque mutation APIs. Independent probes cover callback
registry mutation then unregister, released pin, exact physical descriptor
corruption even after epoch acknowledgement, one-entry forced-spill competition
and unchanged original callback/epoch behavior. Consolidated finding disposition
is in ../../bounded-genesis/closure.md.

Stage0.6/U10 remains open. Mature preparation is paused; no main merge, default
format activation or endurance run is included. Full hosted proof/simulation
validation of this replacement is required before declaring an engine green.
The existing hosted proof job has90minutes, full suite180minutes plus15minutes
job reserve, and per-command scaling bounds. Logs/XML upload on failure; mature
request files are unchanged, so expensive mature conversion stays disabled.

## Late independent DDL finding

The original301affected tests passed431.51s with7JUnit property-format warnings.
That is intermediate-source evidence: the independent reviewer subsequently
reproduced CREATE-AS/DROP/RENAME plus schema_version reset preserving the coarse
epoch while changing catalog bytes. Original proof rejects those bytes; the new
warmed fact wrongly accepted. No affected source was published. Independent RED
log is review-raw/descriptor-ddl-reset; first overly strict revision attempt
could not admit any fact (ddl-green.log, despite its original provisional name).
Final16focused controls pass18.11s, including a live DDL attack with metadata
inspection performed before warming. Thirteen extra revision controls pass0.42s.
They are separate cases. Existing compatible301results remain; final targeted
connection/scope controls and hosted full tests validate final source. Earlier
raw table is intermediate only until the final-source comparison below.

## Final source measurements and decision

After the DDL revision fix, both direction-balanced raw pairs preserve exact
source/input and the same saved/continued digests. No concurrent tests/reviewer
ran during timing. All observations are included below; neither warm result is
excluded. Pair1 ran candidate→baseline; pair2 ran baseline→candidate.

| Phase | Pair1 baseline | Pair1 candidate | Pair2 baseline | Pair2 candidate |
|---|---:|---:|---:|---:|
| Open | 1.171 | 1.896 | 1.310 | 1.871 |
| First step | 9.854 | 8.185 | 10.635 | 7.481 |
| Save | 5.383 | 5.372 | 9.071 | 5.240 |
| Warm step | 8.051 | 8.558 | 10.547 | 7.535 |
| Fresh restore and step | 20.022 | 17.368 | 22.603 | 20.463 |

First step improves16.9% and29.7% in these two observations. Warm is mixed:
+6.3% then−28.6%. Opening is slower in both pairs (+62.0% and +42.8%). Save varies strongly even on
baseline, so no measured save optimization is claimed. No consistent warm-step
improvement or latency distribution is established. Exact metadata work savings
remain61171→57461 first,51359→47507 warm; save24929unchanged. Final source reports
are final-raw/final-reverse-baseline-raw/final-baseline-raw-2/final-raw-2. Earlier
profile counter reduction is intermediate-source attribution only.

Retain the bounded descriptor proof-work reduction and observed first-step
improvement for bundled validation, with these limits explicit. The open/warm
tradeoffs require further performance work; this is not Stage0.6 acceptance.
No mature input construction or target-speed claim follows from these pairs.

Final source connection/custody suite:54passed20.81s in
final-guard-affected.log/xml. New focused controls comprise16cases in
final-focused and13additional revision cases in revision-controls. These are
29distinct cases; counts overlap other suites and are not summed as a total.
The301intermediate affected result remains explicitly separate. Independent
whole-package final signoff is review-raw/report.md. Hosted validation remains
pending; this document does not claim final hosted green.

Hosted43227352719 at exact published f6d5d2ba/runtime41d21d8 is now verified
green:5071full tests6060.896s; proof31XMLs1914tests plus scaling. Counts overlap.
Actual archive hashes/source records are in hosted-43227352719/summary.json.
This closes the hosted engine gate only; mature and interactive targets remain
open, and the mature job was skipped.
