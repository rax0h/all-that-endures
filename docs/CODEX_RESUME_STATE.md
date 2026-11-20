# A.T.E. — active resume checkpoint

Updated November 20, 2026. This is a saved checkpoint, not a live process monitor. Replace the active fields as work advances; retain detailed evidence in the linked records. Follow the interruption rules in [AGENTS.md](../AGENTS.md).

## Active state

- **Current task:** make Codex recovery reliable when usage ends mid-task. Repository instructions and this active checkpoint are installed by the documentation-only commit containing this file.
- **Engineering status:** Stage0.6 remains open. The next engineering step has not been started by this setup.
- **Working branch:** `sol/durable-proof-map` on GitHub and the Windows clone. Check the actual branch and `git rev-parse HEAD` before editing; a cloud publication checkout may have a different local branch name.
- **Baseline:** handoff commit `c853058842f903e2bc8fa7f876d0d7664c8b5979`; this file is introduced by a subsequent commit. Do not reset to the baseline. Latest implementation is `6c7ab0001f14dc95f0b09554a84939810e88e692`; qualified engine tree is `5464caa49acc4c27f24c247b60ee639afd9d150d`.
- **Files changed for this setup:** `AGENTS.md`, `docs/CODEX_HANDOFF.md`, `docs/CODEX_RESUME_STATE.md`. No engine change or new acceptance result is implied.
- **Setup publication intent:** one documentation commit with `[skip ci]`, a leased fast-forward of `sol/durable-proof-map` from handoff baselinec8530588, then `git pull --ff-only origin sol/durable-proof-map` in `C:\Users\Owner\Projects\all-that-endures`. If interrupted before confirmation, compare the actual local/GitHub heads and inspect the diff before repeating a publication or pull.
- **Last verified engineering result:** [small recovery44028694698](https://github.com/rax0h/all-that-endures/actions/runs/44028694698) and [companion helper44028694713](https://github.com/rax0h/all-that-endures/actions/runs/44028694713) succeeded at implementation6c7ab000. Mature performance is still unmeasured. See [CODEX_HANDOFF.md](CODEX_HANDOFF.md) for the authenticated evidence and qualified runtime.
- **In flight / unknown:** no simulation, test or CI job was launched by this setup. This does not assert that no other job exists: inspect live status before launching or duplicating work. Check actual git status/diff for edits made since this checkpoint.

## First incomplete engineering step

1. Reconcile the live repository, relevant CI runs and artifact availability with [CODEX_HANDOFF.md](CODEX_HANDOFF.md), [STAGE_0_6_CONTINUATION.md](STAGE_0_6_CONTINUATION.md) and the [after-digest progress record](performance/stage-0-6-current/after-digest-admission/progress.md).
2. Continue **bounded attribution of the remaining mature proof-audit cost before another long retry**. Record the chosen diagnostic command, qualified environment, output paths and its restart unit here before starting it. No diagnostic command is currently pending.
3. Preserve the completed mature `after_digest` checkpoint from run43918798385: metadata14267625292, closed database14261110486. Do not rebuild source/capture/catalog/rebase/after-digest or treat partial proofs as authoritative. Exact hashes, compatibility rules, artifact expiries and budgets remain in the handoff.

No mature retry, main merge, default-format activation, gameplay/rank migration or endurance run is authorized by this checkpoint setup. Continue within the existing engineering scope and the user's latest instructions.

## Fields to maintain during the next task

- Updated time, active objective and first incomplete step.
- Branch/HEAD, dirty files and any partial edits that need reconciliation.
- Planned or running command/request, working directory/runtime, process/session/CI IDs and output/log paths.
- Last confirmed result and its inputs; pending or unknown outcomes kept separate.
- Exact next action, blockers and reusable checkpoints/tests with relevant compatibility or expiry.

Save before meaningful work and update after results. If a cutoff happens between launch and recording the returned ID, inspect actual processes/runs and outputs before issuing that action again.
