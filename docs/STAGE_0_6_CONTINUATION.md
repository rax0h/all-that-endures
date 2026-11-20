# Stage 0.6 current state

Updated November 20, 2026. Desktop continuation starts with [CODEX_HANDOFF.md](CODEX_HANDOFF.md).

Repository `rax0h/all-that-endures`, active branch **`sol/durable-proof-map`**. Latest implementation is **6c7ab0001f14dc95f0b09554a84939810e88e692**; later handoff commits change documentation/evidence only. Engine **5464caa49acc4c27f24c247b60ee639afd9d150d** is qualified. Stage0.5 original scope is complete; Stage0.6 and mature performance acceptance remain open.

## Verified results

- [Engine qualification43991230104](https://github.com/rax0h/all-that-endures/actions/runs/43991230104), public24c0c612: success. Full log5142passed plus2subtests/9481.56s; proof1968cases; helper404cases. Exact source/runtime/jobs/ZIPs are retained under `performance/stage-0-6-current/after-digest-admission/qualified/`.
- Recovery implementation: clean local432helper cases passed; independent86targeted and22adversarial checks passed; no actionable findings includingMinors. Engine and original catalog contract were unchanged.
- [Hosted small recovery44028694698](https://github.com/rax0h/all-that-endures/actions/runs/44028694698), public6c7ab000: **success**. Source-digest/capture/catalog/rebase/after-digest actually skipped. Proofs, measurement, fresh restore and acceptance passed.
- Actual proof worker exited77 before manifest publication, verified the original after-digest database unchanged, then retried from that exact immutable parent. Fresh restore: year2/generation1/seed843000/digest `cebc2fcd2660db6e87b9c29c3c8e88536a831214c306991778fba6ee58cc7451`, zero operational full World audits.
- [Companion helper44028694713](https://github.com/rax0h/all-that-endures/actions/runs/44028694713): success. Unchanged full-suite/proof-map jobs were skipped.

The November20 handoff authenticated all9small-run archives, successful checkpoint publication windows, both raw database members, all52producer critical blobs, recursive receipts and both admission-contract bindings. Exact evidence and summary are under `performance/stage-0-6-current/after-digest-admission/hosted-smoke-44028694698-*`.

These are **small functional recovery results**, not mature timing acceptance. Historical pending-run observations in older package records have been superseded by these verified results.

## Preserved mature restart

[Mature43918798385](https://github.com/rax0h/all-that-endures/actions/runs/43918798385) passed rebase and exact canonical after-digest, then proofs exhausted its12600-second compute cap. It never reached mature operation timings. The source comparison was subsequently repaired to traverse every reachable proof node once while preserving exact checked source commitments.

Resume point: **after_digest14267625292/run43918798385**, sharing closed rebase database **14261110486**. Year1001/generation0/seed843000, identity `6d0b5191-fd61-4bb8-845a-4dddbd0e3213`, raw29,409,034,240bytes/SHA256 `b1c7ffcd9379d246002d9052065a44d5de539606bb00c43ef7997785962521a5`. ZIP4,447,495,807bytes/SHA256 `bc71ac9e13f1d422cb2e242a9ae17613c9d1dc60a9e0db0ad52a668cf31ffd82`; expiresDecember16,2026,19:08:03UTC.

The exact after_digest->proofs contract is implemented, reviewed and proven by hosted small recovery44028694698. It preserves the inherited catalog cut and authenticates four original metadata/data refs. Ordinary compatibility remains strict. Current critical-helper fence has52paths and33explicit fingerprints. No new mature request has been activated; operational request remains the completed small smoke.

Do not repeat completed source/capture/catalog/rebase/after-digest. Do not rewrite parent receipts or re-pin control digests. The expected year1002digest stays `2a9b53ed70f47b49ca60711b6a5608ba694efaab9c4f125a923b0af97e07e4f7`. Original source fixtures are separately preserved in private draft446184821; preservation/source history is linked from the package READMEs.

## Acceptance still open

| Mature operation | Target | Current repaired proof path |
|---|---:|---|
| Open | <=10s | Unmeasured |
| Save | <=2s | Unmeasured |
| Warm year | <=1s | Unmeasured |
| Exact year1002continuation | Original accepted digest | Unmeasured |

Attribute remaining mature full-audit work before another long retry. The source-loop improvement does not bound full scope/collection/catalog/topology/fact work. Whole proofs remains the smallest expensive restart unit; unsealed partial output is never authoritative. Preserve compute/transport/upload reserves and actual disk checks. Do not repeat unchanged green full/proof suites for helper-only work.

## Desktop handoff

The user's clone is `C:\Users\Owner\Projects\all-that-endures`, already on the active branch and clean at inspection. Code and reviewed evidence are on GitHub; mature SQLite data are Actions artifacts and are not included by cloning source. The handoff adds the formerly unpublished launch record and actual completed results.

Observed Windows Python3.13.17/SQLite3.50.4/MSVC is not qualified for persistence/performance acceptance. Historical cloud Linux paths are not Windows paths; use qualified Linux CI or qualify a new runtime first. Full/proof artifacts expireDecember1, small recovery artifactsDecember17 and original mature dataDecember16; recheck live availability before use.

**Next:** continue from `CODEX_HANDOFF.md`: bounded remaining mature attribution, then—when ready—exact after-digest recovery using smoke44028694698 and mature resume43918798385. No main merge, default activation, gameplay migration or endurance run. Broader findings/deferrals remain in `performance/stage-0-6-current/forensic-repair/closure-register.md`.
