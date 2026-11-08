# Working agreement

Review findings must be resolved and verified within the overall work group that found or created them before that group is marked complete. This includes Minor findings. The user explicitly requires this; it overrides generic skill instructions to defer Minors. Do not carry findings into successive feature groups without explicit user acceptance.

Track findings in one consolidated closure register with origin, concrete action, evidence and status. Reconcile old notes against current code/tests. Preserve historical review evidence and link its disposition; do not erase raw logs or count their preserved whitespace as unfinished product work. A deliberate documented limit can be closed by making the intended contract precise and testing it.

Batch related cleanup and validation. Do not create a separate hosted CI cycle per finding. Use one independent whole-package review and fix actionable findings, including Minors. The user permits brief CI status checks on the hour while long runs are active; do not busy-poll. Benchmark-only harness/workflow changes should use targeted validation without automatically launching the full simulation suite. Stage0.5 original scope is complete; subsequent persistence performance/stabilization is Stage0.6, retaining existing filenames. No main merge, default format activation or endurance run is authorized by cleanup work.

For local persistence acceptance and profiling in this Work Mode workspace, use
the runtime qualified by the unchanged complete generated-year scenario:
system Python3.12.3/GCC13.3.0/SQLite3.45.1, or an isolated venv derived from it.
Here it is available through /usr/bin/python3. Verify its full fingerprint against
docs/performance/stage-0-6-current/fixture-construction/qualified-local-runtime.json;
the pathname alone is not qualification after an OS/runtime update. If it changes,
rerun the unchanged qualification scenario and record the new tuple before
accepting its persistence evidence. The bundled
Python3.12.14/Clang22.1.3/SQLite3.53.1 tuple remains unqualified for this complete
open/year/save/restore scenario, including native save/rollback, with unresolved
failures. Do not use that tuple's partial successes as complete acceptance.
This is a workspace-local evidence contract, not a universal supported-version
matrix, an engine-only causal diagnosis, or a repair/exoneration of application
code. Keep hosted CI's separately recorded runtime and results authoritative for
its own checks. Preserve all failure evidence and full audited opening.
