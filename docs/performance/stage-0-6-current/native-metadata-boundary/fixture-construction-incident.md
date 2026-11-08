# Fixture construction qualification

The canonical same-process generated-year builder did not pass in this workspace.
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
