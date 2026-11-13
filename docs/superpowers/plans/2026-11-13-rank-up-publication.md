# Rank-up publication implementation plan

> Implement inline with superpowers:executing-plans. One independent whole-package
> review; close all findings together before one hosted bundle.

**Goal:** preserve exact canonical progression while saving rank-ups with bounded proofs.
**Architecture:** extend existing Forest/owner edits plus authenticated retirement
slice validation; reuse the original catalog and transaction publisher.
**Tech Stack:** existing Python/SQLite, qualified313 local runtime.
**Spec:** docs/superpowers/specs/2026-11-13-rank-up-publication-design.md

## Global constraints

No gameplay/identity/format/root-authority change. Existing512source/512catalog,
4MiB and4096projection limits and128row retirement budget. Preserve old raw
failures; retire the W10d negative expectations only after positive proof.

## Review focus

Fresh-child type/cycle closure; missing old owner paths; live aliases and foreign
leases; omitted/extra retirement rows or child scopes; rollback and independent
fresh-process continuation. Every class gets a regression or adversarial probe.

### Task1: Bounded existing-record child replacement

- [x] Add positive real rank-up save/reopen test with full audit forbidden. Observe
  RED against green8cc642b2 before implementation; record complete software fingerprint.
- [x] Route changed references away from parent-only value validation. Extend
  owner-edit derivation and catalog comparison to exact old/new auxiliary sources;
  use staged Forest headers and require fresh attached subgraphs to be closed.

### Task2: Retirement publication and complete audit

- [x] Validate initial jobs plus bounded old queue slices from accepted roots,
  dependencies/retention and exact owner deletion projection; update backing/order
  facts on final removal. Keep unsupported shapes on checked fallback.
- [x] Audit actual queued/partial state through existing authorities; prove corrupt
  jobs, missing/surplus physical rows and live placement refusal.
- [x] Repeated normal saves/reopens, old aliases/snapshot, corruption and commit
  fault controls; run focused/affected tests and exact small continuation/work
  observations before any expensive constructor.

### Task3: Review and publication

- [x] Independent whole-package review; resolve Important and Minor findings in
  bounded-genesis/closure.md. One final affected battery, then one hosted bundle.

Restart unit: one disposable small generated proof fixture/test or accepted-input
copy, never the original SQLite input. Each completed test/report survives later
failure. Reuse green43346515423 for unchanged dependencies; changed-engine final
gate remains separate. Tests bounded individually before broader runs; reserve
15minutes for publication. No main/default/endurance or mature request changes.

Implementation/review/focused steps complete. Final affected and exact-source hosted acceptance status is authoritative in the rank-up-publication report; the hosted gate is not implied by these implementation checkboxes.
