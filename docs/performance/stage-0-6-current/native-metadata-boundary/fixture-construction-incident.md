# Fixture construction qualification

During the original metadata package's local validation, the canonical same-process
generated-year builder did not pass in this workspace.
This limitation is preserved independently from the successful native metadata
and retained-fixture continuation checks. Its cause is unresolved.

| Observation | Evidence |
|---|---|
| Candidate private complete-format conversion fails at12.283s and14.138s with SQLite malformed-database errors | final-year-construction-failure.json/.log; final-year-second-construction-failure.json/.log |
| Original cold and lazy inputs pass SQLite quick_check and retain generation2 | conversion-source-check.json |
| Fresh-process conversion of the exact first lazy input succeeds on green baseline98eb84a and candidate6a2a173; both output databases pass quick_check | conversion-comparison.json; conversion-green-baseline.log; conversion-candidate.log |
| An instrumented canonical attempt on green baseline fails in prepared namespace-count validation, before native continuation | baseline-canonical-failure.json; baseline-canonical-diagnostic.log |
| Earlier rank-package conversion observations also included SQLite and checked-spool errors | ../native-rank/closure.md and its preserved control logs |

The baseline canonical diagnostic wrapped catalog verification to capture a
failed target. It failed earlier in staging, so that capture hook was not reached.
The baseline failure is not represented as reproducing the exact candidate
SQLite error. Successful separate-process copies do not prove a cause or repair.
The candidate copy counter records zero head_row/codec_guard calls and1363
prefix_guard calls through legacy readers; copy construction has no admitted
World source authority. No source, SQL guard or corruption check was relaxed.

The continuation check uses the successfully converted current-source artifact,
bound to its exact SHA256 and runtime tree. retained_year_probe.py differs from
the canonical driver only in setup (AST comparison verifies the rest is identical).
It generates eager year2/year3 controls, opens a copy of the retained starting
snapshot with full audited admission and compares the initial canonical digest.
The original raw/diagnostic year, save, fresh-process restore, eager equality,
source-immutability and save-audit assertions then execute unchanged.

Both modes pass, including zero diagnostic save-time World audits. This proves
the retained fixture's native continuation contract. It does not qualify the
same-process builder, mature-world performance or proof-only opening. Those
qualifications remain explicit gates; no completed Stage0.6 claim is made.

Subsequent qualification is preserved in ../fixture-construction/. The unchanged
original full scenario passes on the fingerprinted system Python3.12.3/SQLite3.45.1
tuple, using fresh construction rather than the retained setup. The bundled
Python3.12.14/SQLite3.53.1 tuple remains unqualified: its original-driver C-only
repeat reaches native saving, then rejects an epoch mismatch and leaves its
disposable writable copy structurally damaged. The accepted template stays intact.
This broadens the compatibility limitation beyond construction; no underlying
repair, categorical engine-version cause or universal application safety is claimed.
