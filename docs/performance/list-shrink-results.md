# Authenticated integer-list page shrinking

Baseline a1b2474, run40620095196, is accepted:4349 full-suite tests,1253 proof tests,28 matrices. Exact head/runtime, archive hashes and counts are in run-40620095196/acceptance.json.

Candidate removes integer pages without a full World audit, including truncation to empty. Each removed payload and its active empty owner header are authenticated against accepted content, and the exact inactive successor header is frozen privately. Removed pages must have exact lengths and integer values. The complete expected child directory is independently derived after old child-count and member checks; empty scopes are removed. Descriptor/order semantic facts change, while owner/group/sequence roots, allocator, event root and head namespace inventory remain gated. Absent additions and removed-page count are separately accounted in content cardinality. The existing collection/directory constructors, publisher and recovery remain authoritative.

Unsupported noninteger/reference-bearing transitions keep checked fallback. Boundary/zero/re-growth/alias, mixed independent growth+shrink, missing/extra page or header, false type/header and three publication fault seams are tested. Broad correctness and all28 matrices remain hosted gates; current local test scope and exact source hashes are in list-shrink/verification.json.

The native matrix removes128 values in a fresh session, measuring first access/mutation/save with both SQL tracing and interval-one VM instrumentation. Audited admission stays outside the interval; this is instrumented time. Selected payload SELECT counts include absence probes and are not disk reads or bytes. It forbids full save audit and unrelated history reads, then re-grows the removed page and reopens under full audited admission to check canonical aliases/size/values. Existing scalar/backing/tail/growth/reuse controls remain.

Broader structural/reference save paths, faster ordinary opening/default activation and mature-world targets remain unfinished. No main merge/default activation/endurance.

Review found and reproduced an Important aggregate-inspection issue with valid large integer pages: initial shrink preparation inspected4,621,923 old page bytes before fallback. The fix checks predecessor payload+membership lengths before reading, enforcing a4MiB aggregate frozen+old shrink-inspection budget. The accepted large-page case now falls back correctly and reopens with an empty aliased list; RED→GREEN22.27s. Final-source related/native/matrix verification follows this fix.

Deferred new Minor: the128 removed-page cap is per backing, while the complete request is bounded by512 changed rows and the byte budget; two backings can together remove more than128 pages. A global128page cap is not implemented in this candidate. Three prior Minors remain deferred: native authority header prose, closed-session SQLite-error behavior, and older fixed-shape classifier boundary coverage.

Final-source1k/10k/100k shrink instrumented first-access/mutation/save times708.91/785.00/623.69ms; VM steps494667/512062/512120; selected page payload SELECTs169/257/241; unrelated history payload SELECTs0 each. Selected queries include the128 individual pop operations and repeated selected-page lookups, not distinct page IO. Final audited re-growth/reopen checks pass.

Final fixed runtime08a515e8dcb652308431963bdf9275d0f8d4071e:154 related and120 native regression tests pass(274 distinct), with no failures/errors/skips. Separate budget regression repeated successfully. Independent review requested the budget fix; author verified itRED→GREEN and ran final-source suites/matrix. No second independent review of the fix is claimed.
