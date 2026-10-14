# SOL — Stage 0.5 complete-upgrade memory repair

## Assignment

Plan-only handoff requested by Daniel on 2026-10-14. Implement the repair using
[the implementation plan](../docs/superpowers/plans/2026-10-14-complete-upgrade-memory-repair.md).
This is substantial conversion work, not a one-line cleanup. Do not run another
unchanged large upgrade, increase runner memory to declare success, or discard
integrity checks. Own the repair, focused verification, and resumed validation;
do not request routine permission between the bounded tasks.

Repository: `rax0h/all-that-endures`.
Implementation branch: `sol/stage-0-5-complete-closeout`.
Verified pre-handoff head: `ba93a1f41f5b48927904a69fbc1ba3d5e3190894`.
Read the live branch before editing; this handoff will itself advance that head.
Current runtime product: `2bc3c85389760ff12578857f7d2a849bc5cf9201`.
Latest harness source: `ccba8cc6eba70965271d2570043829b3368e695a`.
Validation branch: `sol/stage-0-5-final-release-validation`.
Diagnostic workflow head: `0e1c309dd6ffcd3c45cac1ecfaf3e705edfbd145`.
No implementation was made as part of writing this handoff.

## Established failure

[Diagnostic run 38531810400](https://github.com/rax0h/all-that-endures/actions/runs/38531810400),
job `115745205236`, stopped with a normal Python `MemoryError` under an 8 GiB
address-space cap. The runner survived and uploaded diagnostic artifact
`11879904649`, ZIP SHA256
`a63c7436bdc3b3af2e1748c916bab44acc2fc5ff74b50d3306d120e5b6f6c402`.

Exact stack at pinned source:

```
persistence_catalog_copy.py:328 _copy_with_checked_catalog
  initial_catalog_delta(codec, versions, placements, ...)
persistence_lazy_identity_catalog.py:200 initial_catalog_delta
  ParticipantDelta.freeze(... version_changes=changes)
persistence_lazy_families.py:619 freeze
  tuple(codec.encode(...) for v in version_changes)
incremental_store.py:139 encode
  json.dumps(...).encode('utf-8')
MemoryError
```

The first catalog freeze failed at peak RSS 8,284,100 KiB. `_owner_sources`
finished beforehand. The first catalog is replaced by a second catalog after
graph normalization/promotion. However, the first call also validates source
placements and physical references: removing it wholesale would drop checks.
The final catalog would still need a memory-safe build and publication path.

The previous unrestricted complete-upgrade job `115682376629` in
[run 38508408370](https://github.com/rax0h/all-that-endures/actions/runs/38508408370)
exhausted roughly 16 GiB RAM plus 3 GiB swap before runner shutdown (exit143).
Disk still had 84 GiB free. This establishes a conversion memory problem.
The earlier exit139 during timed stack dumping was a separate diagnostic-crash
hypothesis; timed `faulthandler.dump_traceback_later` was removed. Do not restore it.

## Reusable evidence and checkpoints

| Item | Source | Use |
|---|---|---|
| Recovery, full simulation suite, canonical mature 1000 years | Run `38459262962`, successful first-attempt jobs | Evidence for runtime `2bc3c853…` only; new runtime changes need new applicable gates |
| Cold checkpoint | Run `38500678444`, artifact `11866834418` | Fallback; do not rebuild unless artifact verification fails |
| Native lazy checkpoint | Run `38508408370`, artifact `11870590333`, name `late-lazy-checkpoint` | Start the repaired complete upgrade here |
| Allocation traceback and resources | Run `38531810400`, artifact `11879904649` | Root-cause evidence; not final acceptance |

Lazy checkpoint ZIP: 1,339,563,957 bytes, SHA256
`409cf0230ff1606b7eddd587a69c22076c11447eb6497e642e584c4fd3b74ef9`.
It contains `checkpoint.json` and `p5-long-lazy.sqlite`, expires 2026-10-28.
Verify ZIP digest, receipt provenance, and the database SHA256 in the receipt.
Origin workflow: `124c3215468a60862b7848086f00a8e768a6ed66`.
Configuration: mature seed843000, bootstrap1000, milestones1001/1002,
complete format, rules `stage-0-5-final-release`.

The existing resume code requires the receipt's original `product_sha`.
A repaired product will have a new SHA. Add explicit provenance for both source
checkpoint product and executing repair candidate; do not rewrite the old receipt,
pass the old SHA while claiming it is the tested repair, or weaken configuration
matching. The plan specifies this work.

## Boundaries and completion

Preserve exact World values, RNG and continuation digests, aliases, NaN handling,
container ordering, high-water marks, event IDs, format6, source immutability,
atomic no-overwrite publication, and existing commit/recovery authority.
Temporary disk staging is disposable working data, not another persisted catalog,
backend, identity registry, or publisher. Ordinary save/open semantics and their
existing budgets remain unchanged. The exact-pressure O(H) cold-miss exception
remains disclosed; this repair makes no universal constant-memory/time claim.

No main/PR14 merge, default checkpoint replacement, rank/issue17 change, Stage1
work, or unrelated optimization. Long jobs run on GitHub; never keep chat waiting
for their completion. Existing authorization covers the scoped validation runs.

Completion requires: an end-to-end memory reduction through final commit/scrub;
focused equivalence/corruption/failure tests; one full suite and complete3+4+3 on
the repaired candidate; complete upgrade of the retained year1000 fixture;
independent exact1001/1002 continuation; and downloaded restore on a fresh runner.
All receipts must identify their actual source and candidate. No final acceptance
from a green diagnostic/checkpoint stage alone.
