# Fixture and native continuation runtime qualification

> November9 follow-up: the original successful qualification below is historical.
> Current repeats of the unchanged complete driver on the fingerprint-matched
> Python3.12.3/GCC13.3.0/SQLite3.45.1 tuple fail on both the bounded-genesis
> candidate and the untouched7df089f baseline. Candidate construction rejects
> staging integrity; baseline construction/raw year/save/fresh restore pass, then
> diagnostic save/close fail. Cause remains unassigned. There is no current local
> complete-acceptance claim and no engine-only attribution or application
> exoneration. Exact commands, source preservation, runtime and failure receipts
> are retained in ../bounded-genesis/ and its independent review-raw/. Hosted
> validation uses its separately recorded runtime and remains mandatory.

Hosted validation is green at8d0fea0:4,911tests,2subtests,one deliberate ZIP
warning,9,304.06s; the proof job also passed. Display-name-only child65cb777
retains the identical runtime tree d91d48cc36dc4fa822b1bf5a52bca6a218437a28.

The unchanged complete generated-year driver now passes on a recorded local
runtime. This establishes a working validation route. It does not repair or
attribute the failures observed on the bundled runtime.

| Execution | Observed outcome | Qualification |
|---|---|---|
| Original canonical system07: Python3.12.3/GCC13.3.0/SQLite3.45.1 | All13phases complete: fresh construction, raw/diagnostic year3, eager/fresh restoration, accepted-source immutability, zero diagnostic save-time World audits | Qualified for this acceptance scenario at the recorded runtime tree; no setup substitution |
| Diagnostic system06 | Construction passes | Instrumented supporting observation; not the unmodified acceptance run |
| Bundled diagnostic01/02 | Private staging read fails with SQLITE_CORRUPT; captured outer file also fails fresh-reader integrity | Failure reproduced; no source-code repair or cause established |
| Bundled diagnostic04 | Construction passes after extra integrity/read/copy observations | Observer changes prevent an uninstrumented-success claim |
| Bundled diagnostic05 | Staging file truncates13,045,760to9,818,112bytes via pager_playback from sqlite3PagerSharedLock; later malformed read | Prior live raw-copy operation can perturb locks; not proof of the original cause |
| Original canonical primary08 with only C truncate observer | Fresh construction, full opening and simulation year pass; raw.save rejects epoch mismatch; raw.close reports recovery required | Bundled tuple remains unqualified for complete native continuation, not merely construction |

Closed-process read-only inspection of primary08 finds the accepted template
unchanged and structurally valid at generation0. Its writable raw copy is also
generation0 but fails integrity: an internal tree references page7563 beyond the
file end. Neither file changes during that inspection. A rejected save therefore
does not establish safe rollback or a healthy writable copy on this tuple.

The whole runtime tuples differ in Python, compiler, SQLite source and build
options. runtime-comparison.json and qualified-local-runtime.json retain those
details and executable/module/loaded SQLite-library fingerprints. No SQLite-version-only diagnosis,
general compatibility matrix, universal application exoneration or mature-world
performance claim is made. AGENTS.md now requires the verified local route and
fingerprint checks for local persistence acceptance/profiling; hosted CI retains
its separately recorded runtime authority.

The C-only observer preserves the original driver, wraps ftruncate/ftruncate64
through RTLD_NEXT, examines existing descriptors and writes a separate log. Its
extra FD, allocations and timing remain observer effects. Source, compile/run
commands, source/binary/interpreter fingerprints and exact addr2line results are
preserved. Successful truncate errno values are stale and are not error evidence.
The original08 trace separates ordinary rollback stacks from its final shared-lock
recovery stack, but lacks timestamps: causal ordering relative to the epoch error
is not asserted. Symbolization describes a call path, not its initiating cause.

Historical diagnostic05 raw copies are retained with an explicit lock caveat.
SQLite documents that closing a separate raw descriptor can release same-process
POSIX advisory locks on an open database. See [SQLite locking caveat](https://www.sqlite.org/howtocorrupt.html#_posix_advisory_locks_canceled_by_a_separate_thread_doing_close_).
Also, failed-stage raw snapshots omit an active journal; they are forensic main-file
samples, not validated standalone databases. Their original-connection quick_check
does not change that limitation when the transaction is active and a fresh reader
is locked out.

One independent whole-package review found one Important and three Minor evidence
findings. All four are Closed, with no additional actionable finding or deferred Minor.
Their actions and independent verification remain in review.md. Focused validation
of the fingerprint-matched system-derived venv passes123metadata/head/recovery
cases in231.27s. JSON/JSONL/Python/C static checks pass; canonical driver hash
and runtime tree are unchanged. Runtime code, publication
and integrity checks remain unchanged. Benchmark/evidence-only publication uses
targeted validation and skip-ci; no duplicate full suite is launched.

Next Stage0.6 gates remain proof-backed opening/restoration, current-source mature
10sopening/2ssave/1syear evidence, and final architecture acceptance. Full audited
opening stays mandatory. No main merge, default activation or endurance run.
