# Native metadata and cached event-prefix boundary

Baseline98eb84a/run42438098176 is green:4872tests+2subtests9417.42s;
proof-map successful. This package retains full audited opening and all current
persistence defaults. It does not qualify mature10sopen/2ssave/1syear targets.

Public generation, checked_head and head_metadata now join the accepted native
head before decoding. They preserve the original authority, read pin, epoch,
snapshot and transaction ownership through opener/result codecs and snapshot
cleanup. Native reads reject uncertainty/staleness until exact recovery. Legacy,
admission and owned publication paths retain their separate authority.

Warm sealed-prefix reads check the admitted source/pin/epoch without rereading
cached segment bodies. Cold reads and verify_full retain their original binding
through decoding; explicit verify_full still bypasses the cache. Paused iterators
recheck each event. Publication still closes the old reader; its replacement can
warm and reuse its own cache. Independent warm-point work54->16SQL statements;
length27->16. These are local work counts, not mature-world latency evidence.

One independent whole-package review found4Important+2Minor, all fixed and
covered by promoted negative controls. Consolidated findings/dispositions are
in review.md; raw review reproductions and every failed validation are retained.
The head diagnostic compatibility ruling changes test assertions, not runtime
trust: physical generation is read explicitly during uncertain recovery, while
public accepted reads remain blocked and original recovery/retry/fresh checks
remain intact.

Final source metadata/head46tests89.41s; new metadata39tests70.00s. Broad earlier
selection276passed/1old diagnostic-contract failure707.50s is supporting evidence
from before the final review fixes; all3first recovery controls9.49s passed.
Expanded74case recovery sweep passes266.47s, including all64formerly blocked
diagnostic cases; all17additional diagnostic sites are fixed. A clean canonical
generated-year receipt follows before publication.4911tests collect1.72s. Python AST, workflow YAML,
all5Bash blocks and product diff whitespace checks pass.170literal SQL/interval
inventory anchors are refreshed; dynamic SQL and pre-admission restoration
selection are explicitly outside the completeness claim.

Remaining gates: authenticate the actual opening path, including schema/rules/
format and restore inventory/selection/absence, with explicit six/seven-root
compatibility and corruption/recovery/fresh continuation while skipping the full
audit; obtain current-source mature performance evidence; final architecture
acceptance. Full audited opening stays mandatory until those opening proofs
close. No main merge, default activation, mature or endurance run is launched.
