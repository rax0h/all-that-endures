# P4.6 — advancement path lazy migration plan

**Date:** 2026-10-05
**Authority:** STAGE_0_5_SOL_EXECUTION_HANDOFF.md, PERSISTENCE_P4.md,
PERSISTENCE_P4_INVENTORY.md, and the accepted P4 lazy-family primitives.

## Residual measurement

Run 37398842779 on product head 339cb0635433444afd9274a2988fc476f5bf66dd
measured a fixed-shape advancement fixture with 1,000 vs 10,000 paths:

| Measure | 1,000 paths | 10,000 paths |
| --- | ---: | ---: |
| ordinary-open payload reads | 2,033 | 20,033 |
| ordinary-open payload bytes | 2,627,582 | 26,225,592 |
| resident advancement paths | 1,000 | 10,000 |
| point read after open | 0 | 0 |

The point read is free only because ordinary open already restores the complete
path archive. Advancement therefore remains a material P4 blocker.

## Scope

Migrate only `world.advancement.paths` in this slice. Preserve
`AdvancementState` rank-scope behavior and all magic-progression semantics.
Do not alter essence/stone rules, progression pacing, balance, rank targets,
RNG use or canonical digest meaning.

Each person path remains one canonical lazy owner record. A path contains a
bounded maximum of twenty abilities, so P4 may rewrite one changed path as one
payload. Archive-size independence is the requirement; per-path payload cost is
reported honestly.

## Mutable identity and tracking

The complete mutable path graph remains identity-bearing. Existing P2C
occurrence labels are authoritative and are migrated unchanged for every
mutable descendant beneath the path owner, including:

- `EssencePath`;
- `base_essences` and `abilities` lists;
- each `AbilityProgress`;
- each `Understanding` and its evidence/applications/transfers containers;
- each `ResponseModel` and its samples/coefficients containers;
- mutable dict/list descendants stored inside those bounded containers.

Scalar field assignment to any tracked path dataclass dirties the owning path.
Supported mutations through nested list/dict/set containers also dirty the same
owner. Retained nested aliases survive clean-cache eviction and reconnect to the
same persisted incarnation on reload. Replacing a nested object detaches the old
occurrence and never writes an obsolete retained alias into the replacement.

No new gameplay identity is introduced. Incarnation metadata remains storage
state only.

## Required behavior

- ordinary lazy open decodes zero advancement path payloads;
- `AdvancementState.path(pid)`, `essence_user(pid)`, `rank(pid)`,
  absorb/awaken/practice/practice_batch/blockers preserve exact behavior;
- point access loads only the requested path and its identity metadata;
- clean path cache is bounded at 256 owners;
- exact dict order, insert/delete/reinsert semantics;
- direct nested scalar/container edits are save-visible;
- no-op save writes zero path payloads;
- one changed path writes one path version plus only its identity/layout/head
  deltas, independent of historical path count;
- current P2C sharing links involving path descendants remain exact across
  lazy↔lazy and lazy↔eager owners;
- materializing detach restores a plain dictionary and ordinary nested
  containers while preserving sharing;
- stale/precommit/lost-ack behavior remains the accepted P4 contract;
- 1,000→10,000 path history keeps ordinary-open path payload loads at zero and
  one requested path bounded.

## Gate

Focused advancement persistence tests + existing advancement/understanding/
mastery tests, then affected P4 identity/lifecycle tests. Remeasure residual
families only after the path gate is green.


## Focused implementation evidence

Initial smoke run `37400214362` passed after excluding the new lazy namespace
from the accepted eager baseline-ordinal bootstrap. The smoke proved zero-load
open, one-path access, nested ability/understanding/response-model mutations,
save/reopen and explicit materializing detach/checkpoint portability.

Focused run `37400414548` passed **33/33 in 10.75s**. It combined the new
lazy-advancement persistence suite with the existing advancement,
magic-understanding and mastery-training suites. The implementation therefore
preserves the existing progression APIs while path storage is lazy.

Post-migration 1,000/10,000 scaling evidence and the broader affected P4 matrix
remain required before P4.6 is closed.
