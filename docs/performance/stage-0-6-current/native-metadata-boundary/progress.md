# Execution ledger — plan: docs/superpowers/plans/2026-11-08-ate-native-metadata-boundary.md

Baseline98eb84a hosted green4872tests+2subtests9417.42s; proof-map successful.
The previous suite took7467.25s. Numerous old expensive tests slowed (history
streaming1026.31->1288.48s, scalar history331.00->491.32s, bootstrap289.98->345.02s).
The new native rank file spans~49s and rank projection~11s in the full-suite
log; proof-map's47rank cases50.91s. Thus new tests alone do not explain the
1950.17s increase. Runner variance versus indirect runtime cost is unresolved
without a controlled same-workload comparison; no slowdown cause is invented.

Preflight: public head APIs share one helper; cache guard must not require an
immutable reader's captured generation to equal a legitimately advanced head.
Retirement cache enters store.read_snapshot already; minimum facade reads use
the existing family/session guards plus checked marker/source reads. Establish
negative controls before claiming complete cache coverage.

Initial RED19fail/6pass48.05s includes one incorrect compatibility expectation:
publication intentionally closes/replaces the old prefix reader. Correct the
positive control to warm and reuse the replacement cache, retaining old close
behavior. First25GREEN49.38s. Additional paused-iterator control passes because
its existing self[index] iteration now uses the guard; cold segment decoder
mutation reproduces RED and is checked before cache insertion. Broad validation
and one independent package review follow, with full opening audit retained.

Boundary run63pass/2fail157.87s: two older tests used public generation as
unauthenticated diagnostics during partial acknowledgement/external corruption.
Ruling: public accepted metadata remains fail-closed in those states; assert
physical durable generation through explicit main.save_head scalar diagnostic
SQL, also assert public generation rejects, then retain original exact recovery/
reopen and no-op corruption rejection checks. Cost if wrong: client code that
used generation as an unsafe diagnostic now gets StoreError; native semantic
reads must not treat an uncertain/stale head as accepted. No runtime relaxation.

One independent review4Important+2Minor all closed: original transaction/pin,
post-cleanup epoch, original cold-source epoch, final scrub segment, redundant
warm SQL, arbitrary transaction error. Promoted9RED/1positive controls19.28s;
final39new cases70.00s GREEN. Independent warm SQL54->16, original-context and
owned/nested/iterator cleanup controls pass. Broader276pass/1old recovery
contract failure707.50s qualified; three targeted recovery cases9.49s GREEN.
Final exact source and canonical year gates follow before one bundled publish.

Final metadata/head source run46pass89.41s. Expanded generation-consumer sweep
21functions/74parameterized cases finds64failures/10pass220.12s. XML inspection
confirms all64stop at the same physical generation diagnostic after deliberately
failed saves, before recovery. Correct17assertion sites across6World test files
to explicit main.save_head scalar reads. Keep all rejection, exact recovery,
retry and fresh restoration assertions; unrelated raw-store tests stay intact.
This extends A2, not a new runtime relaxation. Final consumer rerun74passed266.47s.

Final static/collection checks pass:4911tests1.72s, all5workflow Bash blocks,
YAML, AST and product whitespace.170literal inventory anchors refreshed,54
anchors changed in edited store source. No runtime change after final46cases.
