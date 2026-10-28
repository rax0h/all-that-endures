# Mature benchmark harness repair

Goal: recover trustworthy measurements and preserve the accepted input without
rerunning history, changing simulation rules, merging, or launching a mature run.

Authority: Issue #18 and its October 28 terminal handoff; AGENTS.md.

Execute inline, then obtain one independent whole-package review. This is a fresh
checkout on a new repair branch. Targeted checks are intentional: Issue #18
explicitly excludes another full suite merely to obtain green.

- [x] Retain and authenticate run 40712867500 raw evidence; report complete versus
  censored phases, runner differences and remaining cost.
- [x] Add failing small-fixture regressions for separately recorded preparation,
  optional independent operation budgets, fresh-open/digest timing, timeout
  receipts, and the actual Stage 0.6 workflow launcher. Fix and run focused tests.
- [x] Remove workflow-file edits as an expensive-run trigger. Preserve original
  authenticated source and acceptance ZIPs in a 90-day artifact, without
  extraction or simulation, with provenance and pinned size/hash verification.
- [x] Consolidate findings and their evidence, independently review, resolve all
  findings, publish one candidate and fetch its bounded job link once.

Review focus: saved output after interrupted warm work; failure before a session
exists; caller alarm preservation; timed-out restore receipts; original producer
identity versus mirror identity; no accidental mature/full-suite trigger.

Hosted archive retention remains pending its own run result. Local validation: 36 focused tests passed and actual Stage 0.6 measurement/restore/gate smoke passed. Independent review: four findings resolved; see consolidated register.

Reconciliation: source advanced to e3358b5 concurrently. Keep its canonical Stage 0.6 implementation and manual workflow, remove redundant legacy-helper changes/test, and retain the archive preservation addition. First combined check: 44 passed, source-fence smoke failed because fresh clone lacked b3030921 history. Fetch full ancestry, commit clean candidate, then rerun combined checks.

Reconciliation verified: 45 focused tests passed in 23.82s, including canonical workflow shell smoke; fingerprints/YAML/runtime/diff checks passed. Publication retains canonical source work without a second measurement or retention launch.
