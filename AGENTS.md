# Working agreement

Review findings must be resolved and verified within the overall work group that found or created them before that group is marked complete. This includes Minor findings. The user explicitly requires this; it overrides generic skill instructions to defer Minors. Do not carry findings into successive feature groups without explicit user acceptance.

Track findings in one consolidated closure register with origin, concrete action, evidence and status. Reconcile old notes against current code/tests. Preserve historical review evidence and link its disposition; do not erase raw logs or count their preserved whitespace as unfinished product work. A deliberate documented limit can be closed by making the intended contract precise and testing it.

Batch related cleanup and validation. Do not create a separate hosted CI cycle per finding. Use one independent whole-package review and fix actionable findings, including Minors. The user permits brief CI status checks on the hour while long runs are active; do not busy-poll. Benchmark-only harness/workflow changes should use targeted validation without automatically launching the full simulation suite. Stage0.5 original scope is complete; subsequent persistence performance/stabilization is Stage0.6, retaining existing filenames. No main merge, default format activation or endurance run is authorized by cleanup work.

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
