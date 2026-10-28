# Stage0.6 current-code mature baseline

> Execute inline using executing-plans/TDD; one independent Astra review before publishing measurement. No review findings deferred.

Goal: authenticate the accepted year1001 fixture, measure exact current runtime phases, attribute CI duration, and use measured bottlenecks for the next repair. Authority: Issue18 and user's full Stage0.6 brief; docs/superpowers/specs/2026-10-21-ate-incremental-proof-design.md.

Current source b3030921, runtime63d5ac487d0157a5ef521b4def8ee9ce94532e0c, both CI jobs green. Fixture12129336378/39098313631 expiresNov1; acceptance12165934374/39207586140 expiresNov2. Original baseline and workflows remain unchanged.

Design (reconciled October28): one existing workflow on sol/durable-proof-map, explicitly dispatched, current-source lane only. The prepared parallel workflow was never launched and has been removed. Pin reviewed green ancestor/runtime and harness fingerprints; retain original producer/archive/member/database/accepted-binding checks via existing transport helpers. Separate database initialization, restoration remainder, first year, save, warm year, hash verification and fresh-process open/digest. Measure CPU/RSS/process IO/application counters/storage, per-phase alarms with censored timeout receipts and always-upload diagnostics. Source hashing/copy/transport outside operational timers. Preserve authenticated fixture as30day artifact. No synthetic proof-save timing substituted for actual default mature path.

Budgets(not targets): open1800s, first/save/warm3000s each; fresh verification5400s. Full store scrub not run; digest and checked fresh restore remain separate. Working targets: open10s, warm1s, save2s; first/fresh restore no distinct numeric target. Existing millennium<=120s is separate. Stop on missing fixture rather than regenerate.

- [x] Authenticate fixture availability and prior CI archives; generate top test/call/setup/queue attribution and count/timing trend without rerunning slow suite.
- [x] RED actual small fixture harness/split timings/integrity/budget/provenance tests under .github/tests; implement benchmark helper+launch workflow, GREEN. Keep changes outside full-suite workflow path filters.
- [x] Validate exact workflow launcher on small fixture, YAML/bash and fingerprint gates. Prepared harness independently reviewed, all4 findings closed. Remote36a362d6 launched a different workflow concurrently; reconcile into that existing workflow without another automatic launch.40 reconciliation tests passed24.16s.
- [x] Retrieve actual run40712867500, verify artifact digest, preserve original receipts and compare historical timings/targets. Open454.541s, first4092.171s, save3219.980s, warm>=2452.955s timeout; fresh restore skipped. Performance acceptance fails.
- [ ] Secure fixture retention beforeNov1; configuration is ready, actual replacement upload is not verified.
- [ ] Bounded attribution of expensive default-path first year/save, then smallest demonstrated runtime repair and fresh validation. No proof-default activation or endurance authorization inferred. Stage0.6 remains open.
