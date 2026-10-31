# Independent finite package review

Base: `0124dd8950febe9039534b528f2deea1f1e0b549`.
Reviewer: fresh Astra/high context, read-only, no implementation delegation.
Reviewed the two runtime files, new tests, plan/spec, native guard/publication,
source-witness, insertion, content, inventory and recovery paths.

No runtime or security defects identified. The original rows still pass through
the central transaction and all content/inventory checks. Mandatory predecessor,
payload, schema, kind and token validation precedes exemptions and continues
after budget exhaustion. Fresh/deleted/structural rows remain semantic input;
existing replacements contribute zero to insertion count changes. Excluding a
dependency row cannot hide a catalog source witness: it is not an owner family.

One Minor finding: three new test `read_version` calls omitted the required
`expected_record_schema=1`. Reviewer reproduced two failed budget tests and four
passing structural tests. Author fixed all three call sites; the six-case author
verification passed in 10.62 seconds. Final exact-source expanded tests passed.

Author also corrected the history-read sentinel to allow fresh page absence and
publication checks while rejecting unrelated existing bodies. Final scalar,
tail and fresh-backing cases pass with more than 512 borrowed backings.

After review, author bounded the classifier allocation: retain the original
preparation when no exemptions exist or more than 512 semantic rows remain.
This avoids materializing an oversized streamed preparation. Exact final 12-case
tests and two checkpoint/native-save cases passed after this final correction.
The broader 168-case run began before it; no exact-final-source claim is made
for that earlier batch. No second independent review is implied.

Limits: this review does not establish full-year sequence/ownership coverage,
mature latency, architecture promotion, default activation or full-suite success
on the new runtime. Those remain explicit gates.
