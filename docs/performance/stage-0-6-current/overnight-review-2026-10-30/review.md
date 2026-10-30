# Overnight reconciliation — October30,2026

Reviewed d070eb75685a549913a1e18da4690e42d42b2a2f through
a42f110ddad522aa73b7dfd5f6c03fbcdcf47e4a:16commits,12files,
809insertions/20deletions. No changes under simulation/ate_sim; no merge/default
activation/endurance/full suite/mature measurement was launched overnight.
The16commits are small steps of one retained-fixture transport package, not16new
simulation features. Seven progress comments were posted to Issue18 during this
interval. The scheduled task is disabled (observed is_enabled=false and no next
run); no automation settings were changed by this review.

## What actually happened

| Local CDT time | Work | Verified disposition |
|---|---|---|
|~1–2a.m.|Our previously launched full/proof and focused runs finished; task recorded JUnit trends|Both green on d070eb7, authenticated below|
|~3a.m.|Detected launcher still required expiring original artifacts despite retained copy|Valid reproducibility concern|
|~5a.m.|Added exact six-member retained ZIP staging|Local transport component|
|~6a.m.|Pinned successful retained-artifact producer metadata|Local provenance component|
|~7a.m.|Added bounded signed download|Local transport component|
|~8a.m.|Joined retained input to original save/acceptance authority and launcher; refreshed fingerprints|Not covered by older green CI; two defects found and corrected in this review|

No overnight mature-world timings were obtained. The task's latest report stated
that its nine integration cases were isolated/stubbed, not full29.9GB acceptance.
That qualification matters: all84 initial combined harness tests passed22.04s,
but their synthetic equal-runtime identities concealed an actual launch blocker.

## Verified CI evidence

Full/proof run41003344858 and focused run41003344742 are green at d070eb7.
Downloaded full-suite artifact12959630461 matched GitHub ZIP SHA256
8f90021019eb4717846696918b4dbd6fb11f948b8b97da5b04923ef235e8a29c.
Its source receipt names d070eb7/runtimefe7467eb2047aaee4debc48c5cad24a917895acd,
Python3.12.15/SQLite3.45.1. Pytest log:4411passed,1warning,2subtests passed,
7337.76s (~2h02m). JUnit counts4413including the two subtests and records
7337.592s at suite level; these are different reporting counters, not a failed
or missing test. Existing timing report's observational -1.58% suite change is
not a mature simulation speedup.

Focused artifact12954645891 matched GitHub ZIP SHA256
34417f8ae27404d401cc2612968e844e9d115bcd446c5cb494786a94e2481404.
Source SHA/runtime match, process exit0,12profiled selected cases135.602552s,
and7boundary regressions in audit-boundary.xml. Small structural fallback:
2World audits/1authority audit, instrumented save4.371934s. This differs from the
older6.476365s observation; runner and profiling variation prevent treating it
as an additional code improvement. Current mature open/save/warm acceptance is
still unmeasured. Original focused receipts are preserved alongside this report.

## Consolidated review closure

One independent whole-package review, preserved in independent-review.md:
0Critical,1Medium,1Minor. Author fixed both within this package; no second
independent approval is claimed after fixes.

| Finding | Action | Evidence/disposition |
|---|---|---|
| R1 Medium: historical retained runtime incorrectly required to equal current candidate runtime | Pin original retaining producer runtime63d5ac487d0157a5ef521b4def8ee9ce94532e0c independently of current candidate fe7467eb2047aaee4debc48c5cad24a917895acd; keep current-source fence | Distinct-runtime isolated fixture RED then GREEN; altered historical runtime still rejected. Real small saved/accepted bundle extracted, authenticated with original validators, published and restored with exact digest. Closed |
| R2 Minor: default urllib follows HTTPS-to-HTTP redirect before final scheme check | Validate every redirected URL before sending request; retain credential/port/fragment checks and token-free download request | Actual offline urllib redirect machinery rejects HTTP/credentialed target before issuing it; valid HTTPS redirect succeeds, no Authorization header. Closed |

The first offline redirect test needed handler priority and case-insensitive HTTP
headers corrected to exercise actual urllib redirect dispatch; those fixture
attempts are not product findings. The real small-world retained acceptance test
passed with no receipt-validator stubs; only network delivery is substituted.
It does not replace a hosted29.9GB download/acceptance test.

## Current boundary and next action

The simulation runtime is still the fully green d070eb7 runtime. Retained transport
repairs/fingerprints are harness-only, so a repeated two-hour simulation suite is
not justified. This review starts no CI or mature benchmark. Finish and preserve
the combined clean-checkout harness gate, then resume implementation from this
workspace. Before using the mature fixture, validate hosted retained transport and
capacity; benchmark exact current source with separate open/restore/step/save and
verification budgets. Remaining history-wide proof fallback is still an
architectural performance gate. Stage0.6 remains open.

Final combined clean-checkout gate:88passed,1expected duplicate-ZIP warning,
39.17s. Evidence:combined.log/combined.xml. Current runtime tree remains
fe7467eb2047aaee4debc48c5cad24a917895acd. All launcher fingerprints and workflow
YAML/bash checks pass. Both independent findings are closed; real29.9GB hosted
acceptance and mature performance remain explicit gates. No new CI launched.
