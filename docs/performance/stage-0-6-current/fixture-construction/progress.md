# Fixture-construction investigation

Baseline65cb777 (display-name-only child of tested8d0fea0), runtime
d91d48cc36dc4fa822b1bf5a52bca6a218437a28. Hosted full and proof jobs green;
4,911tests+2subtests9,304.06s. Full opening audit and persistence defaults stay.

Open observation: canonical same-process fixture construction fails in private
conversion/staging while exact-input fresh-process conversion passes. Existing
raw failures and retained continuation proof remain in ../native-metadata-boundary/.
No root cause or environment attribution established.

Next bounded experiment captures private target/workspace integrity at the first
failure, then compares bytes/read results on the existing and fresh connections.
Record construction phase boundaries and exact SQLite error codes. Do not add
retries or alter the publisher/validation contract before establishing cause.

Investigation preserved diagnostics01/02/04/05 plus traces and runtime tuples.
Trace05 shows hot-journal recovery truncation but its prior live raw copy can
release POSIX locks; reviewer identified this Important observer caveat. Diagnostic03
ptrace was denied before application execution; no escalation. Observer-only
original08 has no Python monkeypatch/raw-before-commit copy, passes construction/
opening/year, then raw.save fails epoch validation and raw.close requires recovery.
Its final writable file is generation0 but corrupt; template matches its original
hash and remains structurally healthy. No safe rollback or engine-only claim.

Unchanged canonical system07 passes all13phases on Python3.12.3/GCC13.3.0/SQLite3.45.1:
fresh setup, raw/diagnostic year3, eager/fresh restores, source immutable, zero
diagnostic save-time World audits. Raw opening11.031/year8.734/save6.927/fresh+digest
21.364s are small-world uncontrolled observations, not mature/controlled speed proof.

One independent whole-group review identifies1Important+3Minor evidence findings:
qualify raw observer effects; preserve provenance/stale-errno/stack limits; label
uncommitted snapshots incomplete; fingerprint actual loaded SQLite shared library.
All requested actions are implemented in this group, final focused/review closure
pending. AGENTS now provides a workspace-local qualified validation route, with
complete fingerprints and separately retained hosted CI authority. This is a
deliberately scoped operational contract, not an underlying repair or general
application exoneration. Further compatibility on the bundled tuple stays unqualified.

Final system-derived venv focused suite123passed231.27s. Resolved interpreter hash
matches system executable; actual loaded libsqlite3 binary/module/source/build
fingerprints recorded. Original canonical driver hash/runtime unchanged; all13
phases complete, zero diagnostic save-time World audits. JSON/JSONL/Python/C
static checks and product whitespace pass. Final independent closure follows.

Independent whole-group review complete: R1Important/R2Minor/R3Minor/R4Minor all
Closed. Reviewer independently confirms13original canonical phases,123focused
passes, full runtime fingerprints and preserved observer/failure qualifications.
No further actionable finding, no deferred Minor, no second review or duplicate
full suite. Publish benchmark/evidence/local operational contract with skip-ci.
