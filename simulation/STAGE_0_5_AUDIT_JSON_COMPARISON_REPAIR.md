# Audit JSON year-key comparison repair

The first independent mature audit, run39108569661/job117619605334, failed
October18,2026 at09:26:14UTC after completing the audit and closing its disposable
session. The command exited1 with `full saved audit differs from original
control`; it was not a timeout. Full saved-artifact transport authenticated
ZIP4419015875 bytes/SHA256
`67e52ba2f045f87b2a814e9d0dfe5b9ed7f24898d25a448437bd386869f46e2d`.
The actual audit took4684.422454324 seconds; open took1082.305118168 seconds.
The retained-input hash check returned before comparison rejected the result.
No audit receipt was published. `stage_0_5_audit1001_failure.json` binds the
real run, producer, phases and downloaded diagnostic hashes.

The successful year1001 SAVE is immutable and reusable: artifact12129336378,
run39098313631, generation126, database29922463744 bytes/SHA256
`4a39288b3af497e51dadf82f41cc371b714905380adfc75408c510e8ab2009e2`.
It remains retained until November1. Never simulate year1001 again merely to
run or repair verification. The original year1000 and original controls are
unchanged.

## Confirmed defect

P5's real `_audit` returns integer keys in `new_irons_by_year`. The original
control, loaded from JSON, has string keys. The previous `canonical()` sorted
Python keys before JSON converted them to strings. Years2 and10 therefore
produced different JSON strings despite equal JSON objects:

* Live integer keys: `{"2":1,"10":1}`.
* Loaded string keys: `{"10":1,"2":1}`.

`same()` compared those strings and rejected identical counts. The original
year1001 control reproduces the same guaranteed false rejection when its year
keys have the actual audit's integer type. A real World with rank-advance
history in years2 and10 also reproduces it after complete-format conversion
and ordinary reopen. The two-year proof fixture did not cross a digit-width
boundary, so it missed this case.

The failed mature job did not retain its observed audit values. This confirmed
comparison defect alone forces rejection even for equal mature data, but it is
not proof that every mature observation otherwise matched. Actual mature audit
and digest gates remain mandatory.

## Repair and safeguards

Canonical comparison now applies JSON key conversion before sorting. Duplicate
keys produced by that conversion reject, including integer1 plus string`1`.
JSON value types, counts, fields and array order remain strict. Receipt writing,
receipt hashing, stored format, persistence runtime, P5 audit/report helpers,
original context, configuration and independent controls are unchanged.

True audit mismatches still reject before publishing a receipt. Their errors
now include at most eight escaped JSON-pointer paths with bounded expected and
actual samples. Diagnostics never define acceptance or remove a comparison.
The existing audit_seconds timing-metadata limitation remains deferred.

Six regression assertions failed before implementation: two integer/string
year-map comparisons, converted-key collision rejection, the real complete
World audit/control comparison, and two missing diagnostic-detail cases.
The first repaired selection passed49 tests in58.46 seconds. The full affected
selection then passed134 tests in385.56 seconds, with one expected duplicate-ZIP
warning. A fresh independent Astra review found no blocking findings. Its new
diagnostic-only signed-zero detail edge is deferred and does not weaken rejection;
the existing audit_seconds metadata minor also remains deferred.

The reviewed tree882a00bfaa24d0e4c5c0dcaf7ffa7405b52d7bc0 was published as
`cdb0516b0423af24483eadcc5a18651e879bdc47`, all seven changed files byte/blob
read back exact. A single fresh proof launched as [run39139421134](https://github.com/rax0h/all-that-endures/actions/runs/39139421134)
on October18,2026 at15:12:23UTC. It completed successfully at17:08:05UTC. All17
jobs passed, including2948 full-suite tests plus two subtests and134 focused
checks. The four exact proof/restore/test-report ZIPs were downloaded, their
producing jobs authenticated and all member sizes/hashes checked. The recursive
restore receipt validates; its values job reports shared nested identity and
eight counted histories. All12 helper source files read back byte/blob exact,
and both runtime subtrees match the approved tree. Exact result evidence is
`stage_0_5_audit_json_repair_result.json`. Exact source,
review, evidence and next gates are in `stage_0_5_audit_json_repair_launch.json`
and `STAGE_0_5_AUDIT_JSON_REPAIR_REVIEW.md`.

The new proof12143847835 authorizes the repaired helper bytes; the prior proof
cannot cover them. One audit1001 retry was pinned and independently cleared by
Astra using the same retained artifact12129336378. The single launch is
[run39152488567](https://github.com/rax0h/all-that-endures/actions/runs/39152488567),
created October18 at18:04:35UTC. Exact source/review/dispatch evidence is in
`stage_0_5_audit1001_retry_launch_result.json`. The actual retry completed
successfully at19:21:19UTC; downloaded audit12148235361 matches the full original
control. Its physical JSON ordering exposes a separate downstream receipt
writer/readback rejection, reproduced in the exact consumer. See
`STAGE_0_5_AUDIT_RECEIPT_HANDOFF.md` and `stage_0_5_audit1001_result.json`.
Successful fixture proof
does not establish the actual mature audit outcome. No SAVE rerun, automatic downstream stage, monitoring,
endurance, main merge or Stage0.5 acceptance is authorized by this repair.
