# Working agreement

Review findings must be resolved and verified within the overall work group that found or created them before that group is marked complete. This includes Minor findings. The user explicitly requires this; it overrides generic skill instructions to defer Minors. Do not carry findings into successive feature groups without explicit user acceptance.

Track findings in one consolidated closure register with origin, concrete action, evidence and status. Reconcile old notes against current code/tests. Preserve historical review evidence and link its disposition; do not erase raw logs or count their preserved whitespace as unfinished product work. A deliberate documented limit can be closed by making the intended contract precise and testing it.

Batch related cleanup and validation. Do not create a separate hosted CI cycle per finding. Use one independent whole-package review and fix actionable findings, including Minors. Respect the user's no-long-CI-polling preference: publish a candidate, fetch its run link once, and wait for the user's Green. No main merge, default format activation or endurance run is authorized by cleanup work.
