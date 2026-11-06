# Whole-package review request

Repo: /workspace/scratch/2c32dac1599d/all-that-endures
Base: e423c94bdb41143f29fcb3f27a2803fac3ceffb1. Review final working-tree product files, including untracked native_roster module/tests; reviewed-hashes.json binds bytes. Only2runtime files changed. No catalog runtime change.
Spec: docs/superpowers/specs/2026-11-06-ate-native-roster.md
Plan: docs/superpowers/plans/2026-11-06-ate-native-roster.md
Register/rulings: docs/performance/stage-0-6-current/native-roster/review.md
Coverage: docs/performance/stage-0-6-current/native-roster/catalog-coverage.md

Review focus verbatim:
- Accepted counts include both record/segment fields; lazy namespace declarations must still reject ordinary access.
- Count preflight occurs before payload selection; compensated deletion/addition cannot pass point-source checks.
- Metadata parsing/caching cannot call user codec hooks or replace physical validation.
- Public catalog caches and metadata-only owner witnesses cannot grant body authority or hide changed placements/links.
- Errors/callbacks/recovery must preserve the original checked snapshot and accepted context.

Evidence: red.xml7failed20passed31deselected82.11s; green.xml65passed171.96s (initial roster16+sources49); extended.xml22passed73.47s; controls.xml3passed13.42s includes final segment and1k/10k instrumentation. Current broad regression and9new catalog cases running, not claimed green yet. Final source pin/clean launcher/canonical eager+fresh/generated-year and exact-tree publication remain author gates; do not waive them. Full local4790test suite is hosted once on bundled publication (prior source green above).

Only one whole-package reviewer. Return all actionable findings incl Minor with severity/line/evidence, plus any declined-to-judge assumptions. AGENTS.md requires all findings closed here. Independently inspect broad surrounding contracts, not only new tests. May run bounded read-only independent probes under /tmp for SQLite fixtures, logs/code only under this review-raw directory. Do not edit runtime/tests or other package files. Preserve every failed exploratory probe and distinguish fixture mistakes from product failures. Write final report whole-package-review.md here. No extra subagents, no git commit/push, no mature/default/main/endurance/CI launch. No second review is planned; author will fix and test actionable findings.
