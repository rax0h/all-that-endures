# P4.10 — lazy skill histories

**Date:** 2026-10-05
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and accepted P4 behavior through P4.9.

## Residual evidence

Post-social residual run `37411805298` measured ordinary open at:

- 1,000-row fixture: **11,035 payload reads / 1,591,678 bytes**;
- 10,000-row fixture: **110,035 payload reads / 16,054,728 bytes**.

The largest remaining unbounded namespace is
`world.skills.skills`: **10,000 rows / 2,815,568 payload bytes**.
It also contributes **30,000 mutable identity occurrences** at 10k because
each `SkillHistory` owns its top-level record plus `teachers` and
`provenance` lists.

## Scope

Migrate only `world.skills.skills`.

Each `(person, domain)` key owns one `SkillHistory`. Preserve exact
`SkillState.get/practice/teach` semantics. No skill balance, learning-rate,
teacher, provenance, RNG or gameplay changes.

## Identity and mutation

`SkillHistory` becomes tracking-aware. The authoritative mutable occurrence
set per owner is exactly:

- top-level `SkillHistory`;
- `teachers` list;
- `provenance` list.

Both lists use bounded lazy runtime wrappers and retain their persisted
incarnations across cache eviction/reopen. Direct scalar field assignments,
list mutation and whole-list replacement dirty only that skill owner.

## Acceptance

- ordinary lazy open decodes zero skill payloads;
- `skills.get(person, domain)` loads at most one existing skill row or creates
  one new row;
- `practice()` and `teach()` preserve exact scalar/list behavior;
- direct `level/practice` edits and teachers/provenance mutations save/reopen;
- clean cache <=256 owners;
- no-op save writes zero skill payloads;
- one changed skill writes bounded evidence independent of historical skill
  count;
- insert/delete/reinsert preserves dictionary order;
- materializing detach restores plain `dict` + plain list values and remains
  checkpoint portable;
- existing development/current-standard/history tests remain green;
- 1k -> 10k skill history keeps ordinary-open skill payload work at zero and a
  fixed point mutation/save bounded.

After focused + scaling + affected gates, rerun residual inventory.


## Focused and scaling evidence

Product implementation head: `6c943bc883bfb5d06eb439d7141d1bca3818a584`.

Focused run `37412669585` passed **8/8 in 27.49s**.

Scaling run `37412803730` passed the 1,000/10,000 bounded-work proof:

| Measure | 1,000 skills | 10,000 skills |
| --- | ---: | ---: |
| ordinary-open payload reads | 33 | 33 |
| ordinary-open payload bytes | 16,658 | 16,660 |
| point payload reads | 1 | 1 |
| point payload bytes | 246 | 246 |
| one-skill save payload writes | 3 | 3 |
| one-skill save payload bytes | 409 | 409 |
| resident skills | 1 | 1 |

Affected P4 regression run `37413133031` passed **279/279 in 302.41s
(5:02)**. P4.10 is accepted closed on product head
`634c517d943b0d71c94fa9603a7ba87eda660add`.

Next action: rerun the residual eager inventory and select the next migration
strictly by measured remaining archive cost.
