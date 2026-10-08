# Bounded Sol assignment: close the ownership repair gate

Read `STAGE_0_5_OWNERSHIP_REPAIR_VALIDATION.md` first. Work on the published
`sim/stage-0-5-astra-ownership-repair` branch, not production PR #14. Verify its
live head and record the implementation commit and tree before making changes.
The parent implementation is e8e216dd234f47dd2be9a96af1e8048798fa1ba0.

## Authorized work

1. Run the exact candidate's focused gate once:

   ```sh
   PYTHONPATH=.:simulation python -m pytest -q \
     simulation/tests/test_stage_0_5_paged_ownership_repair.py \
     simulation/tests/test_stage_0_5_household_sequence.py \
     simulation/tests/test_stage_0_5_paged_household_world.py \
     simulation/tests/test_stage_0_5_r3_cross_family_extra.py \
     simulation/tests/test_stage_0_5_r3_recovery_extra.py \
     simulation/tests/test_stage_0_5_r3_default_mode.py \
     simulation/tests/test_persistence_lazy_currency.py \
     simulation/tests/test_persistence_lazy_genealogy.py \
     simulation/tests/test_persistence_lazy_identity.py \
     simulation/tests/test_persistence_lazy_store.py \
     simulation/tests/test_persistence_lazy_store_failures.py \
     simulation/tests/test_persistence_tracking.py \
     simulation/tests/test_persistence_lifecycle.py \
     simulation/tests/test_persistence_p2c.py
   PYTHONPATH=.:simulation python simulation/persistence_p5_validation.py \
     --seed 843000 --pre-years 3 --continuation-years 4 --reopen-years 3 \
     --paged-households --output ownership-p5.json
   ```

2. If these pass, freeze that implementation and start **one** full simulation
   suite (`python -m pytest -q simulation/tests`) in a manual CI helper branch.
   The helper may differ only by its workflow. Upload the pytest log, focused
   log, P5 JSON and provenance manifest. Publish the run URL immediately and
   stop; the owner will return when it finishes. Do not poll a long job or ask
   Astra to watch it. Use `[skip ci]` for ordinary commits if automatic workflows
   would start endurance. No workflow may invoke a long/endurance harness.
3. A concrete failure authorizes the smallest repair in the touched ownership,
   tracking, checked-format or copy/recovery path, plus its regression. Preserve
   the old-or-new transaction boundary, P2C current-link authority and P3 event
   machinery. Do not weaken tests, silently materialize cold history on ordinary
   access, drop duplicates/order, or substitute equal values for shared identity.
   Record red/green evidence and changed source; rerun affected gates only.
4. Record outcome against exact source/tree. Do not promote to PR #14, merge,
   claim Stage 0.5 completion, or begin a broader migration under this assignment.

## Ordered remaining architecture work (not authorized implementation here)

The truthful residual inventory is linked in the validation report. Resolve it
in independently measurable units, preserving already accepted adapters:

- **Event-ID authority:** exact compact membership for normal consecutive IDs;
  holes/extras/imported sets require exact checked representation, never an
  assumed range. Couple IDs with EventLog/tail/head publication and recovery.
  Grow sealed history 1k -> 10k with fixed tail and show bounded resident/open
  metadata. Exercise all supported set mutations and legacy restore explicitly.
- **Current identity discovery:** retain current links as durable P2C authority;
  checked per-owner/group lookup must replace the eager global link tuple, not
  merely hide it behind a wrapper that materializes during bind/save. Grow cold
  alias groups 1k -> 10k with fixed resident group count; cover both first-access
  orders, replacement, dead weak bindings, and missed dirty routing.
- **Household current access:** select living members without decoding dead
  Person history; preserve member-list order and duplicates. Paged membership
  has checked occurrence ordinals available; point/query intersections must be
  driven by the bounded current population and relevant matches. Test the same
  eight living people embedded in 1k and 10k historical members. Separately bound
  outer household rows and settlement household histories—per-list paging is
  not proof of an outer-table bound.
- **Other residual families:** property/provenance, beliefs, culture/adoption,
  institution histories, divinity histories, closed conflicts/inquiries and
  threats each need a specific hot/cold boundary and nested-field inventory.
  Each unit must define ordering/alias authority, dirty routing, lifecycle,
  compatibility and numerical open/read/write/cache gates before implementation.
  An active-record cap is not an archive cap. No generic wrapper or bulk migration
  is approved merely by this list.
- **Release evidence:** once all architectural blockers and affected gates are
  closed, retain a downloadable late-world backup with raw hash, sizes, seed,
  generation, schema/rules, source/tree/workflow provenance and restore digest.
  Verify a fresh download/restore. If the old fixture cannot be recovered,
  prepare durable capacity plus streaming compression/shards and request explicit
  authorization for one replacement run. Do not launch it under this handoff.

Restrictions remain: no Stage 1, balance or magic progression changes, unrelated
checkpoint-default replacement, endurance/millennium, or PR #14 merge.
