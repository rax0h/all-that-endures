# Stage 0.6 current state

## Qualified source

Repository: `rax0h/all-that-endures`, branch `sol/durable-proof-map`.

- Engine: `84626841aa84b87a0564eda15200d83ea1478bb4`.
- Qualified public commit: `4eadb66855289b9983677815f402af1ceb94b37e`.
- Hosted qualification: run **43735593694**, with 5,123 full-suite tests and 2 subtests reported, 1,968 proof cases, and 330 harness cases passing.
- Current launcher helpers: `935df38b5f9267c25fddbea8bda0e3f50121b49f`, with the same engine.

The qualified full/proof jobs used Ubuntu 26.04.1 (image 20261111.196.1), Python 3.12.16 and SQLite 3.46.1. Current engine/staged workflows pin Ubuntu 26.04 and retain software/signature guards. Reuse the engine qualification for these helper changes.

## Active execution

The staged smoke **43778758497** passed at commit `935df38b`. Its 359 harness cases, every uploaded checkpoint, exact small-year fresh restore and real interrupted-worker recovery were authenticated from the completed producer jobs and checksum-verified archives. Fresh restore recovered year 2, generation 1 and the expected `cebc2fcd...` digest. This is functional qualification of a small generated world.

Request `preserved-current-engine-mature-2026-11-15-1` now activates one mature execution using smoke **43778758497** and the reviewed larger budgets. Source helpers, workflow and engine remain unchanged. This restores the original year-1001 world; it does not regenerate the millennium. Reuse sealed closed checkpoints and restart the first incomplete compatible stage. The old monolithic retry is disabled. See `performance/stage-0-6-current/forensic-repair/mature-launch-preflight.md` for the restart and resource contract.

## Preserved inputs

Private draft **446184821** holds both original archives with immutable part/manifest IDs. Preservation run **43734650623** reconstructed both complete ZIPs and matched their original hashes. Caller hop **43776600177** passed 357 harness cases and restored the original small archive through the actual consumer.

Draft access is scoped to the four jobs that read this input; consumer operations remain GET/download-only. The preserved copy is independent of the original mature Actions carrier's November 27 expiry. Original source/acceptance authority, database hash `4a39288b...`, archive hash `4f040569...`, and expected year-1002 digest `2a9b53ed...` are unchanged.

## Acceptance remains open

| Mature operation | Target | Current engine |
|---|---:|---|
| Open | ≤10 seconds | Unmeasured |
| Save | ≤2 seconds | Unmeasured |
| Warm year | ≤1 second | Unmeasured |
| Exact year-1002 continuation | Accepted control digest | Unmeasured |

A timing miss does not pass Stage 0.6. Existing protected policy retains the saved measurement checkpoint and stops before another expensive fresh digest if speed targets miss. Exact deep continuation acceptance is still required before completion. Annual throughput is distinct from player-response latency.

Historical `b45/fd20` public-commit replay is **non-mature** and mixed. It establishes no uniform speed or save-latency gain. This assignment includes no main merge, default-format activation, gameplay rank migration or endurance run.

## Evidence and next action

See `performance/stage-0-6-current/forensic-repair/launch-report.md` and its consolidated `closure-register.md`. Broader findings remain open or owner-deferred; original review 001 was not supplied. Indexed originals, qualified artifacts, all six save profiles, the public source map and raw replay are retained.

Earlier continuation text is preserved verbatim in `historical-continuation-before-staged-smoke.md` with a SHA256 index.

**Next:** confirm the mature request's hosted gate and first incomplete stage; retain its actual timings and exact-continuation disposition when available. A green engine/harness/smoke badge is not a mature performance result.
