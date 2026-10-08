# Shared-owner routing: correctness slice

Implementation starts from continuous-plan commit d603aec. This slice repairs missed payload publication; it does **not** complete bounded current-link discovery or the remaining historical-family migrations.

## Red evidence

With `PYTHONPATH=.:simulation`, `python -m pytest -q --tb=short simulation/tests/test_stage_0_5_unloaded_alias_routing.py` reproduced twelve semantic failures before production changes (0.57s): four shared-wallet owner copies stayed at iron=1 instead of9; four nested Person/wallet cases kept the wallet payload at wealth=1 instead of4; four equal-distinct replacements did not advance the generation or split sharing. A first attempt without the repository's required simulation import path failed at collection/runtime setup; that environment failure is not the semantic red evidence.

## Repair

- Resolve and preflight only current lazy owner placements of the edited incarnation before container/record mutation.
- Rehydrate unloaded peer payload owners and attach their routes before changing the shared value.
- Preserve the accepted zero Person payload-load path for a Person first loaded through a nested wallet alias.
- Notify every current containing payload owner after IndexedRecord edits, without changing ordinary RecordTable behavior.
- Treat equal distinct mutable values (including mutable descendants inside tuples) as identity changes; replacements remain separate from retained originals.
- Use the existing hybrid commit, checked occurrence registry and P2C sharing authority. Do not add another sharing authority or independent commit.

## Green evidence

Python3.12.14, ownership-gate-venv, `PYTHONPATH=.:simulation`.

- New regression file: **19 passed in3.31s**. Includes both edit/reopen orders, assign/update replacement, retained original after replacement, faults during version writes/before commit/after commit, and fixed two-owner routing amid1,000/10,000 unrelated wallets.
- Affected gates: new regression file (then17 cases), lazy currency, lazy people, lazy identity, lifecycle, paged ownership repair, R3 cross-family and R3 recovery: **111 tests and2 subtests passed in58.57s**. Two scaling cases were added and verified afterward; production source did not change between these runs.
- P5 seed843000, pre3 + continuation4 + reopen3, paged households: **passed=true**, finalyear10,439events. Exact control finaldigest `3301d4e4a6a2f415679cabe62754813440034cf4c190035c79ba82cc7b8e378e`; totaldigest `b31c2272d220a1624ff5ee204e229ccaf95adf9a7eaff86643b350567b5e9387`. Portable detached checkpoint and relocated restore succeeded. Raw JSON is retained as continuous-repair-p5.json for eventual CI evidence upload.
- `git diff --check`: clean.

The scaling regression checks exactly2 loaded/dirty wallet owners, no global live-binding scan during mutation, ≤8 payload writes and<16KiB written at both history sizes. It does **not** claim bounded ordinary identity open/no-op save: those global baseline inventories remain a separate repair.

No full suite, endurance, Stage1, production promotion or merge was performed. Final combined architectural review remains pending.
