# Action ability lifetime implementation plan

> **For agentic workers:** implement inline with superpowers:executing-plans;
> one independent package review after measurement, all findings closed together.

**Goal:** avoid reconstructing one action's clean ability bodies between passes.
**Architecture:** local strong references only; reuse existing canonical objects
and their checked lifetime. No persistence/cache/format policy change.
**Tech Stack:** existing Python/SQLite, qualified Python 3.13 runtime.
**Spec:** docs/superpowers/specs/2026-11-12-action-ability-lifetime-design.md

## Global constraints

Retain original selection/RNG/events and exact saved/continued state. Keep the
previous candidate's hosted gate 43336282110 separate. Do not repeat its full
suite locally or launch another expensive run before a measured candidate exists.

## Review focus

Missing/empty, partial, full and ceiling paths; mid-action body transitions;
lazy native canonical identity; action-lifetime release; no persistent tuple.

### Task 1: Retain one action's operands and measure the result

Files: agency.py; test_stage_0_6_action_ability_lifetime.py; performance evidence
under small-operation-profile/action-ability-lifetime/.

- [x] Add real proof-backed work regression: count successful AbilityProgress
  header loads during one action, requiring no repeated incarnation loads.
  Run it before code and retain the expected RED receipt.
- [x] Create a local ability tuple before PracticeBatch, use it for selection;
  rerun work regression plus existing advancement/stabilization controls.
- [x] Commit a local candidate after focused green; baseline is detached
  action-retention-baseline at 18923a4/runtime7347092a. Use existing exact-source
  paired driver, A-B/B-A; pin candidate engine and input bytes. Verify original
  input, saved year2 and independent continued year3 digests. No concurrent tests
  or CPU probes during raw comparisons.
- [x] Independent package review, close all optimization-package findings in bounded-genesis/closure.md;
  retain or reject based on work/latency evidence, then choose one hosted bundle.

Restart unit is a disposable small copy/trial. Existing phase budgets and outer
120s child cap plus bounded process-group cleanup apply. Completed reports
survive failure; restart only incompatible/unfinished trials. Original source
SHA2555675bd19ede5c6ed9b7619fab56d59098a8b358d9a9c3569cabccba22c554;
archive expires December11. Reserve15minutes for evidence publication.

Ruling: keep the existing rank-up response-model replacement limit explicit.
The new milestone scenario fails on baseline18923a4 as well as this candidate.
A trial topology-eligibility change was reverted after exposing the separately
unsupported partial-retirement fallback; no publisher/audit/retirement change is
part of this optimization. Eager/native progression and RNG agree before save;
the boundary test must refuse and resolve the unchanged generation. This does
not close rank-up save support or Stage0.6. Baseline negative and original
scenario failures are retained.

Measured ruling: retain the complete20 action/work improvement as a local
candidate (42.1%/60.6%in two bounded observations), with annual timings mixed.
No overall/mature or causal save claim. The full-source hosted gate remains
pending. Independent review's body-transition coverage and runtime-file wording
findings are resolved in W10b/W10e. Full-stage acceptance remains open, including
the confirmed pre-existing rank-up fresh-child publication blocker W10d.

Published candidate551d8d5b22d534766eddd84ccbde1416f7f03c7f, exact localbb8582c
tree80b70085073d0d5dfb4dc69b46d604621c62209f/runtime8cc642b2. Standard
validation43346515423 is pending behind existing43336282110. These two distinct
runtimes each have one bundle; no mature requests/default/main/endurance changed.
Candidate acceptance and W10d capability remain open after publication.
