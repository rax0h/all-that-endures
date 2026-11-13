# Independent benchmark clarification review

Reviewed 2026-11-12. Scope: repeat-comparison plan, runner, all four completed
run-1 reports and manifest, runtime qualification, preceding baseline/pair,
annual-ordinary historical result, and the new explanatory report. Production
code, index, branch and hosted CI were not changed or rerun by this review.

## Findings

1. **R1 / P2 — process-group cleanup can leave a descendant running.**
   Original `stop_group` returns when the leader has exited, and after TERM
   waits only for the leader before deciding whether KILL is needed. A tiny
   disposable reproduction with a child ignoring TERM produced leader return
   code -15 and child state S after `stop_group` returned. The reviewer then
   killed the whole disposable group. Address group lifetime independently of
   leader lifetime; verify leader-exits-on-TERM and already-exited-leader cases.
   Completed successful trial measurements are unaffected.
2. **R2 / Minor — the preflight source fence does not prove working files equal
   the pinned tree.** `git diff --quiet -- simulation/ate_sim` compares working
   files to the index, so staged changes can pass, and it omits untracked Python
   files. The runner then accepts those files as its expected runtime. Compare
   exact Python path/hash inventory with pinned Git tree contents, or combine
   HEAD comparison with explicit extra-file rejection. Independent review
   verified every recorded Python SHA and file path against the pinned Git
   blobs for all four completed trials; their actual evidence passes.
3. **R3 / Minor — qualification cadence is overstated in the plan.** The
   original plan says runtime fingerprint is rechecked, while the runner checks
   only `sys.version` per result. A separate valid full fingerprint exists for
   this session. Either enforce full per-trial qualification or state explicitly
   that full qualification is a session preflight and Python/source/input are
   checked per trial. Keep the actual successful receipt unchanged.

Findings must be resolved in the same consolidated closure register before this
review group is complete. Follow-up disposition will be appended here.

## Independent evidence checks

- Manifest has complete A-B/B-A order: pair1 baseline/candidate, then pair2
  candidate/baseline. Start timestamps are sequential, each report is complete,
  and phase CPU/wall entries exactly match the manifest after six-place rounding.
- For each report, every `runtime_files` entry was independently checked against
  `git cat-file blob` for the pinned runtime tree, including exact file inventory.
  Baseline is 41d21d8dfd2eedd44b35c12c894cbb4a59ba6058; candidate is
  4654b0194149f735a15c79507a6e57c88a7acbb2. Both copies of compare.py,
  its checkpoint/recorder support files and input.json have matching SHA256.
- All trials use input SHA256
  2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554,
  year1, generation0, seed843000, 26,206,208 bytes. The driver copies the source
  to a unique working SQLite file, verifies source before/after, and verifies
  runtime hashes before/after. Child import paths remain inside selected trees.
- Fresh verification is a separate interpreter. All saved states are year2,
  generation1, seed843000, digest
  cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451;
  continued year3 digest is
  a46d627d11ce2c12ff8f6fe0f14d01af35006afd56bdad3bf16417379b0166f3.
  The driver independently compares the saved digest with input.json and the
  fresh continuation with the original in-memory continuation.
- The full qualification receipt SHA matches qualified-local-runtime.json and
  every observed fingerprint field matches that file, including binary,
  extension, loaded SQLite library, source ID and compile options. Historical
  and resumed fingerprints also record matches without differences.
- Pair1 changes recompute to first step -21.4141%, save -0.5316%, warm -24.6119%;
  pair2 to first step -24.1287%, save +6.9615%, warm -13.4782%. The explanatory
  report rounds accurately and correctly claims no established save improvement.
- Phase ceilings are open60/first180/save120/warm180/fresh120 seconds, with
  a stricter 120-second outer whole-trial wall limit. Failures preserve the log,
  reports already written and completed earlier trials, then stop the matrix.
  Restart instructions use a fresh output path and forbid silently combining
  sessions. These lifecycle claims require R1 closure.

## Historical comparison boundaries

The earlier baseline-raw and preceding same-command-pair baseline have identical
runtime_files, Python version, input and restored-state objects. Their timing gap
is real and unexplained: save5.312/warm5.990 versus save7.722/warm9.224 seconds.
The prior pair host is Intel Xeon Platinum8573C; all four new trial before/after
contexts are AMD EPYC9V74. Earlier raw CPU identity is not recorded. These facts
show hardware varied across recorded sessions but do not establish the cause of
the earliest raw result or assign causal portions of the timing difference.

annual-ordinary/real-year-final.json really records raw simulated-year1.870353s
and save4.636500s, with audited admission9.252155s. Its accepted input is
bd8b3e978cb5ae6ca507bf08e2e2f884ec63365ddc892046d41c661a9d48b2af,
starting year2 and saving year3, runtime ae9a5833 on Python3.12.3/SQLite3.45.1.
Current year1 input, runtime, opening contract and continued digest differ.
The report preserves this faster observation and explicitly says that these
mismatches neither explain the gap nor prove the current engine matches the old
workload. No same-workload regression conclusion follows either way.

The report keeps mature targets and Stage0.6 acceptance open. No distributional,
cold-cache or mature-world claim is supported by four small-world observations.

## Final follow-up and disposition

R1 is CLOSED in consolidated W8c. The repaired runner handles group lifetime
independently of the leader, sends TERM even for an exited leader, waits bounded
grace, then sends KILL to the surviving group. Cleanup errors are retained with
the original trial failure. Both child-survival controls fail on the measured
runner and pass on the repair.

R2 is CLOSED in consolidated W8d. Tracked changes are compared with HEAD, and
exact Python inventory plus Git blob identity reject staged, untracked and
ignored extra sources. All three source-fence controls fail on the measured
runner and pass on the repair. The independent reviewer ran the final five
controls with the qualified313 interpreter: **5 passed in0.55s**. Author RED5
and GREEN5 evidence remains in harness-red/green.log and XML. This is targeted
harness validation; no simulation measurement or full suite was repeated.

R3 is CLOSED in consolidated W8d. The final plan and report now explicitly
state full fingerprint verification once for this measurement session, with
Python version, engine hashes, input and saved/continued state checked per trial.
Libraries were not rehashed between trials. The retained measurement runner
run-1/repeat-measured.py SHA256 was independently verified as
45b37efd0ef67802bf8d414cdb82b13ceef24c02386b2898728ae1945597b543.

All findings, including both Minors, are resolved in this work group. The final
clarification preserves unexplained historical timing gaps, claims only the
observed two-pair warm improvement, and leaves save/mature performance targets
and the separate hosted correctness gate open. No remaining actionable finding
was identified within this benchmark-only package.
