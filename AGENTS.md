# Working agreement

At every start or resume, read `docs/CODEX_RESUME_STATE.md` first for the active task and first incomplete step, then `docs/CODEX_HANDOFF.md` and `docs/STAGE_0_6_CONTINUATION.md` for the Stage0.6 baseline. The handoff distinguishes the current qualified engine, completed small recovery and preserved mature restart point. Historical `/workspace/scratch/...` runtime paths below describe the old Work Mode environment, not the user's Windows clone; inspect and qualify a new runtime before accepting persistence/performance evidence.

## Interruption and usage-limit recovery

The user frequently reaches usage limits during a task. Keep `docs/CODEX_RESUME_STATE.md` current throughout work; do not depend on a final handoff, a usage warning or conversation memory. Keep it short and link detailed evidence rather than duplicating it. The user's latest instructions override an older checkpoint.

Before a meaningful editing chunk, long command or external mutation, save the objective, planned step, branch/HEAD, affected files, exact command or request identifier, and intended output/log location. After launch record process/session/CI IDs promptly; after each completed chunk record the verified result and next action. Mark uncertain outcomes explicitly as unknown. Update the checkpoint before switching tasks or stopping. Never store credentials or signed download URLs in it.

On resume, reconcile the checkpoint with actual `git status`, branch/HEAD, diff, output files and relevant process/CI status before acting. Preserve partial edits and user changes; do not reset, clean or automatically stash them. Check whether an interrupted command or external action finished before rerunning it. Reuse completed compatible tests and closed checkpoints; resume the first incomplete step, not the whole assignment. A recorded launch intent without a returned ID needs reconciliation, not an automatic second launch.

Write checkpoints to disk immediately. Include them in small coherent progress commits and sync within existing user authorization, especially before changing machines; do not commit broken code solely to make a checkpoint or launch CI for every note. Report the last verified state separately from pending work. A saved chat and repository checkpoint support recovery, but do not guarantee restoration of an executing command or unsaved reasoning.

## Review and validation

Review findings must be resolved and verified within the overall work group that found or created them before that group is marked complete. This includes Minor findings. The user explicitly requires this; it overrides generic skill instructions to defer Minors. Do not carry findings into successive feature groups without explicit user acceptance.

Track findings in one consolidated closure register with origin, concrete action, evidence and status. Reconcile old notes against current code/tests. Preserve historical review evidence and link its disposition; do not erase raw logs or count their preserved whitespace as unfinished product work. A deliberate documented limit can be closed by making the intended contract precise and testing it.

Batch related cleanup and validation. Do not create a separate hosted CI cycle per finding. Use one independent whole-package review and fix actionable findings, including Minors. The user permits brief CI status checks on the hour while long runs are active; do not busy-poll. Benchmark-only harness/workflow changes should use targeted validation without automatically launching the full simulation suite. Stage0.5 original scope is complete; subsequent persistence performance/stabilization is Stage0.6, retaining existing filenames. No main merge, default format activation or endurance run is authorized by cleanup work.

Before expensive runs, record the smallest failure/restart unit, which closed outputs survive failure, compatibility/expiry of reusable inputs and green tests, phase/transport budgets and reserved publication time. Prove restart and actual artifact upload/download on a small case before mature execution. Do not repeat completed compatible stages or unchanged green suites merely because a later stage failed. A new unknown bottleneck must be checked before rebuilding its expensive prerequisite prefix.

For local persistence acceptance and profiling in this Work Mode workspace, use
an unchanged complete generated-year qualified runtime and verify its full
fingerprint against docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json.
The November10 replacement OS tuple is Python3.13.5/GCC14.2.0/SQLite3.46.1;
/usr/bin/python3 and the system-derived isolated
/workspace/scratch/d88f8db353e8/ate-qualified-313/bin/python share it. The unchanged
complete13phase driver passed at85f87e1/runtimee68a2ea8 before repair edits;
evidence is bounded-genesis/timeout-repair/runtime-313-qualification.json.
The earlier3.12.3/GCC13.3.0/3.45.1 qualification and later local failures remain
historical evidence; its saved fingerprint is qualified-local-runtime-312-historical.json.
The old ate-qualified-python pathname now resolves to3.13 and must not be used
as a version assertion. If the tuple changes again, rerun complete qualification
before accepting evidence. Bundled3.12.14/Clang22.1.3/SQLite3.53.1 remains
unqualified with unresolved failures. These are scenario observations, not a
universal version matrix or an engine-only diagnosis/application exoneration.
Hosted CI records its separate runtime; preserve failures and full audited opening.
