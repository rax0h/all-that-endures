# Consolidated proof-opening closure register

One independent whole-package review of276d323 follows integrated generated-year
validation. Its two findings and same-seat closure verification belong to this
work group. The bundled hosted gate remains pending.

| ID | Origin and finding | Concrete action | Evidence/status |
|---|---|---|---|
| A1 | Initial test used the wrong TypedCodec import | Import from incremental_store; preserve collection failure separately | Valid red19missing-API failures/1audited control; initial green20; Closed |
| A2 | Restore failure after capture could lose its owned lease | Retain the original pin before matching-snapshot setup and through final cleanup | restore-red/restore-green; Closed |
| A3 | Foreign private admission was consulted before exact capability validation | Validate exact authority type before callback/I/O dispatch | restore-red/restore-green; Closed |
| A4 | Late codec method changes escaped final restore checks | Check closed codec and original context before and after snapshot cleanup | restore-red/restore-green; Closed |
| A5 | Rebound cleanup touched a borrowed connection | Retain and restore lexical owned DB/codec before rollback/close; leave borrowed transaction open | restore-red/restore-green; Closed |
| A6 | Store identity and session-pin changes could survive return or redirect cleanup | Join identity to accepted manifest, validate original session binding and release only sticky original lease | owner-red3fail/owner-green35pass; Closed |
| A7 | Cancellation bypassed Exception-only restoration cleanup | Catch BaseException at the owned opening boundary and preserve the primary cancellation while cleaning up | cancel-red2pin leaks/cancel-green2pass3.40s; Closed |
| R1 Important | Reviewer: COMMIT can precede capture return/caller ownership; first closure also falsely owned a rejected duplicate token | Hold a private lexical resource owner; register the exact pin after successful INSERT and before phase hook/COMMIT; retain foreign rows, never discover/delete new-looking pins | review-red4fail; initial4green; collision-red1fail; closure-green5pass6.23s; independent final10pass13.46s plus after-INSERT/pre-registration KI/SystemExit probes. Closed by same review seat |
| R2 Minor | Reviewer: constructor failure/return cancellation left registry/session active | Own the in-construction session immediately after store/pin/world binding, before registry allocation; abort tolerates partially initialized state and closes registry/session | review-red4fail; review-green4pass5.17s; reviewer9controls13.02s including before-registry failure. Closed by same review seat |

Scope boundary: exact externally accepted seven-root/v4 snapshots only. This API
does not certify unvisited bytes. Dormant corruption rejects on selected access
or explicit full scrub; audited/default compatibility remains. Returned archived
payload bytes are measured separately from physical page I/O. Small-world
validation cannot establish mature-world10sopening/2ssave/1syear acceptance.

The initial review and raw probes are retained in review-raw/. Its seven
declined-to-judge items are accepted scope dispositions: mature/physical-I/O
evidence remains a separate gate; dormant bytes and arbitrary unaccepted roots
are outside this API's trust contract; bundled runtime stays unqualified; hosted
validation/endurance are not inferred; benchmark-only path filtering follows
AGENTS; preserved historical evidence is not unfinished product work. These
are tested/documented limits, not deferred actionable findings.

Final current-source regression113passed78.38s covers49opening/13launcher and
51existing default-store cases. Independent final production/test hashes match
final-source.json; closure-final.md confirms R1/R2 closed with no remaining
concrete issue. All author and independent findings, including Minor, are closed.
The final clean serial year and bundled hosted result remain separate gates.
