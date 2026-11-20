# A.T.E. — Codex desktop handoff

Updated November 20, 2026. Read this before continuing Stage 0.6.

## Repository and computer

- Repository: `rax0h/all-that-endures`.
- Working branch: **`sol/durable-proof-map`**. `main` is not the current Stage 0.6 branch; do not merge or switch to it for this work.
- Latest implementation commit: **`6c7ab0001f14dc95f0b09554a84939810e88e692`**. This handoff is a subsequent documentation-only commit; use `git rev-parse HEAD` for the current tip.
- Qualified engine tree: **`5464caa49acc4c27f24c247b60ee639afd9d150d`**.
- User's Windows clone: `C:\Users\Owner\Projects\all-that-endures`. It was inspected through Desktop Commander on device Larry and was clean, on the correct branch and implementation commit.
- Code, reviewed changes, test evidence, recovery contract and current operational request are on GitHub. The mature SQLite fixture is an authenticated GitHub Actions artifact, not an ordinary source file in the clone.

The user is transferring this project from ChatGPT Work Mode to Codex. Do not restart the implementation from earlier handoffs or rebuild completed expensive stages.

## Verified current state

Stage 0.5 original scope is complete. Stage 0.6 persistence/performance work remains open. The latest changes remove repeated proof-tree traversals from complete source audits and add exact recovery from an already completed after-digest checkpoint. Complete state/history, identity, relationships, ownership, integrity and deterministic continuation must remain intact.

| Evidence | Result |
|---|---|
| [Engine qualification43991230104](https://github.com/rax0h/all-that-endures/actions/runs/43991230104), implementation ancestor24c0c612 | Success: full log5142tests +2subtests, proof1968cases, helper404cases; qualified Python3.12.16/SQLite3.46.1 |
| Local recovery package | Clean432helper cases passed; independent86targeted +22adversarial cases passed; no actionable findings including Minors |
| [Hosted recovery44028694698](https://github.com/rax0h/all-that-endures/actions/runs/44028694698), current implementation6c7ab000 | Success: gate, proofs, measure, fresh-restore and acceptance; source-digest/capture/catalog/rebase/after-digest actually skipped |
| [Companion helper44028694713](https://github.com/rax0h/all-that-endures/actions/runs/44028694713) | Success; unchanged engine full-suite/proof-map jobs actually skipped |

The hosted recovery really exited77 inside an unfinished proof transaction, verified the original after-digest database unchanged, restored that same immutable parent in a fresh worker and retried successfully. Fresh restore produced year2/generation1/seed843000, digest **`cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451`**, with zero full World audits during operational restoration.

The handoff verification authenticated all9small-run archive hashes, both raw database members, successful checkpoint publication windows, recursive receipt links, both inherited admission contracts and all52producer critical blobs. Evidence is under `docs/performance/stage-0-6-current/after-digest-admission/hosted-smoke-44028694698-*`.

**This is small functional recovery evidence. It does not establish mature open/save/year performance or complete Stage 0.6.**

## Exact mature restart point — preserve it

Run **43918798385** passed rebase and the exact canonical after-digest check, then exhausted the210-minute proofs compute budget. It never reached mature operational measurement.

- Resume from **after_digest**, metadata artifact **14267625292** in run **43918798385**.
- Closed rebase database artifact **14261110486**, year1001/generation0/seed843000, identity `6d0b5191-fd61-4bb8-845a-4dddbd0e3213`.
- Raw database29,409,034,240bytes, SHA256 `b1c7ffcd9379d246002d9052065a44d5de539606bb00c43ef7997785962521a5`.
- Archive4,447,495,807bytes, SHA256 `bc71ac9e13f1d422cb2e242a9ae17613c9d1dc60a9e0db0ad52a668cf31ffd82`; expires **December16,2026,19:08:03UTC**.
- Original baseline digest remains `57f60fdf49e221af24ffc0a1f2d5a3885dd37c07db00d153171adcb91c579eed`.
- Expected saved year1002digest remains **`2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7`**.

Do not replay source/capture/catalog/rebase/after-digest, re-pin digests, rewrite old receipts, retarget the old catalog contract, or weaken ordinary `compatible()` checks. A new proofs-only admission contract already preserves and validates both historical context cuts. Every consumption reauthenticates four historical metadata/data refs.

The current request remains a completed **small smoke** request. No new mature retry was launched during this handoff. When mature readiness is established, the intended request inputs are `mode=mature`, `smoke_run_id=44028694698`, `resume_run_id=43918798385`, with a new unique request ID. Use the existing exact admission/gate; inspect compatibility, expiry and software before work. Changing critical helpers requires a new compatible small recovery; changing engine code requires appropriate qualification.

## What to do next

1. Read `AGENTS.md`, this file, `docs/STAGE_0_6_CONTINUATION.md`, the after-digest admission README/progress and the consolidated forensic closure register.
2. Check live branch/CI/artifact state; do not assume availability from old links. Qualified full/proof artifacts expire December1; current small recovery artifacts expire December17; original mature restart data expire December16.
3. Attribute remaining mature proof-audit cost **before another long retry**. The source-loop optimization was measured, but full scope reconstruction, collection/catalog/topology/fact work is not yet bounded by a new mature result. New diagnostics identify audit boundaries and source-root counts. Do not declare the entire210-minute stage safe from a small synthetic speedup alone.
4. Preserve/reuse compatible completed stages and unchanged green engine suites. The smallest current expensive restart unit is the whole proofs stage; incomplete/unsealed proof output is never authoritative.
5. Once ready, continue from the exact mature after-digest, then measure open/first year/save/warm year separately and verify exact year1002fresh restore. Report measured results and actual limitations.

Mature targets remain **open<=10s, save<=2s, warm year<=1s**. All three and mature exact year1002continuation remain unmeasured for this repaired proof path. First year is measured separately. Historical synthetic or older-path save timings must not be presented as current mature performance.

Existing proofs budgets: compute210minutes; restore30, database upload45, metadata5 and diagnostics5 reserved within a350-minute job. Keep disk/archive/member/journal headroom checks. Do not simply enlarge the compute budget to hope a run finishes. No main merge, default-format activation, gameplay/rank migration or endurance run is included.

## Runtime and desktop details

This Windows device currently has **Python3.13.17 / SQLite3.50.4 / MSVC**. That is an observed development runtime, **not a qualified persistence/performance environment**. No usable WSL distribution was confirmed. Native Windows may also lack POSIX facilities used by existing harnesses. Do not run the full Linux acceptance harness blindly and call environment failures engine regressions.

The existing qualified hosted environment is Ubuntu26.04/Python3.12.16/SQLite3.46.1, with full signature checked against retained inputs. The old cloud workspace's qualified local runtime is Python3.13.5/GCC14.2.0/SQLite3.46.1; its `/workspace/scratch/...` paths are historical cloud paths and are not paths on this PC. Use qualified Linux CI or explicitly qualify a new runtime before accepting persistence/performance evidence. Do not reinstall Python, enable WSL or change system security policy just to open this handoff.

Codex CLI0.169.1, the Codex desktop components and VS Code's OpenAI extension were found. PowerShell's npm `codex.ps1` wrapper is blocked by the current execution policy; the installed native `codex.exe` works. Native `codex app PATH` is the documented local command for opening the desktop workspace. Do not disable execution policy or bypass Codex sandbox/approval settings.

## Important source/evidence files

- `simulation/stage_0_6_after_digest_admission.py` and `.json`: current proofs-only recovery and fixed pins.
- `simulation/stage_0_6_catalog_admission.py` and `.json`: unchanged historical catalog contract.
- `simulation/stage_0_6_genesis_resume.py`, `_checkpoint.py`, `_stages.py`, `_source_control.py`: launcher, recursive receipts, stages and controls.
- `simulation/stage_0_6_genesis_resume_request.json`: operational request; deliberately excluded from critical helper fingerprints.
- `.github/workflows/stage-0-6-resumable-proof-genesis.yml`: bounded staged workflow.
- `.github/tests/run_genesis_recovery_drill.py`: real smoke-only crash/retry.
- `docs/performance/stage-0-6-current/after-digest-admission/`: latest qualification, reviewed recovery, preflight and hosted evidence.
- `docs/performance/stage-0-6-current/forensic-repair/closure-register.md`: consolidated findings and broader open/deferred items. Missing original review001 and owner-deferred gameplay issues must not be invented or silently closed.

Suggested first Codex message: **Read `AGENTS.md` and `docs/CODEX_HANDOFF.md`, report the verified state, then continue the bounded mature performance investigation while preserving all completed checkpoints.**
