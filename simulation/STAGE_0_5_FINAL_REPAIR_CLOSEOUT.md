# Stage 0.5 final-architect R1–R3 bounded closeout

**Source:** PR #14 / `sim/stage-0-5-stabilization`.
**Reviewed input:** `85f8ac6cb5fafac7c16f8a3bc2d203f3548aaad8`.
**Scope:** no P1/P2/P3 rewrite, balance changes, millennium/endurance,
checkpoint-default replacement, Stage 1 or merge.
**Disposition as of this evidence:** **BLOCKED — R3 unresolved**.
R1/R2 fixes and short tests below are not Stage 0.5 acceptance.

## Reproduced before production edits

A separate test-first commit `b40db547cb785a5bd83f5abdeb772e0bd94550bc`
ran five adversarial cases on the original persistence source.
GitHub Actions `37727798155`, job `113149826140`: **5 failed as
expected in 3.66 seconds**.

- R1: with 300 and 900 distinct people read and released, the
  in-session baseline payload cache held 300 and 900 encoded records,
  respectively, despite the advertised 256 clean resident limit.
- R2: the public digest callback mutated a retained person without
  rejection; digest from within `current_people_scope()` executed its
  callback rather than failing before work.
- R3: an ordinary lazy open exposed an eagerly allocated 1,000-ID
  `Household.members` native list; `sys.getsizeof` was 8,872 bytes.

The independent architect review provides more complete pre-repair
memory measurements; do not substitute these tests for the review's
evidence.

## R1 — implemented bounded clean lifetime

Product commits `8d6327db4ff803de2f468eed0771b3883b84c980`,
`614685c5e458ce78405a8400be19dcbda9278d74` and
`bb9dde0888eb34f77c941380172da9f15b1f799a`
collectively:

- remove cached clean payload/presence/ordinal/incarnation/identity-label
  sidecars when a clean owner leaves the LRU or step-hot window;
- avoid caching one-off positive and negative historical membership
  probes; omit archive-sized inactive query tuples from the cache;
- drop dead runtime World incarnation occurrences while preserving
  checked persistent occurrence labels, and preserve the standalone
  registry's previously accepted logical-placement-after-GC contract
  via the World-only `prune_dead_occurrences` mode;
- retain dirty owners and externally held aliases for existing
  reactivation/identity pathways.

This is an implementation summary, not a declaration that every nested
family has now been audited or that the full Stage 0.5 suite passed.

**Post-repair exact completed gates:**
- `37728222134`: 4/4 R1/R2 new tests in 2.66s; 67/67 existing
  people/genealogy/identity/lifecycle tests in 37.51s.
- `37728349130`: 8/8 R1/R2 new tests in 44.67s, including 1k and
  10k historical person traversal, repeated eviction/GC/misses,
  zero-write no-op save, full digest, one edit/save/reopen; and 67/67
  existing affected tests in 37.01s. Two of the original five
  repro dimensions (R3) remained excluded rather than falsified.

The 1k/10k tests require all four clean sidecar maps and runtime owner
occurrence indexes to hold at most 256 entries, and the sum of retained
person baseline payload bytes to be <=200,000. The tests passed.
Those thresholds are assertions, not exact measured retained byte totals;
do not claim the latter from this run.

## R2 — public operation guard repaired

Production commit `301f20d72baf0ff42d0d9f07829cb16734d821ff`
wires `_LazyLifetime.begin_operation/end_operation` through
`LazyWorldSession._begin_lifecycle_operation/_end_lifecycle_operation`,
preflights the open backing store before public operation callbacks,
and rejects `LazyWorldSession.close` during active lifecycle
operations, simulation steps or `current_people_scope()`.

Adversarial post-repair tests cover nested public digest, mutation,
save/detach/close attempted during digest, exception-guard release,
supplied-digest archive preflight in an active scope, and directly
closed-store preflight. Existing P3B lifecycle tests remain passing.

## R3 — independently reproduced, NOT repaired

The eager `world.households` row contains the complete nested
`Household.members` history; conversion/open still decode it,
and `Simulation._demography` appends new births. Neither a bounded
outer row count nor the established `world.agency.actions` cap
limits historical member ID growth.

**Do not count the unbounded R3 test as passing.** The standalone
architecture, storage/identity/save/lifecycle integration and
required 1k/10k append/snapshot/alias/recovery proof have not been
completed. See `STAGE_0_5_R3_SEQUENCE_REPAIR_PLAN.md` for the exact
remaining contract. An ad hoc compressed full list or visually small
wrapper is not a repair because normal append would still rewrite
all historical members. The Stage 0.5 gate stays **BLOCKED**.

## Retained year-1000 late-world fixture

The final architect review cites completed Actions long-horizon evidence
`37679777350`, job `112992483949`, including control/restored digest
`004ebc6ef7a62e39f867d7a3f96ccf9e88f1c7362fe73fe78a1e8dfb29d02725`.
The reported runner-local fixture was:

- `stage-0-5-final-endurance/p5-long-restore.sqlite`;
- year 1,000, generation 6;
- 5,124,976,640 bytes;
- SHA-256:
  `b775264dce1a202fdddfba4fa696455192906866bd9912673c9d26abcc797d63`;
- rules `stage-0.5-p5-long-v1`, schema `ate-world-p2a/1`.

Independent connector checks:
GitHub's artifacts list for run `37679777350` is **empty**.
Exact-name/hash-prefix searches in accessible connected Google Drive
(`p5-long-restore`, `stage-0-5-final-endurance`, `b775264dce1a202f`)
returned no matches. No retained late-world file has been verified
in those locations. This does **not** establish that no separate
copy exists outside those places. A reported runner-local pathname
and checksum do not constitute a durable downloadable fixture.
The earlier 10-year dry-run artifact `11439363432`, if retained,
is not a substitute for the year-1000 restore fixture.

Recovery requires locating an independently preserved copy of the
exact checksum or obtaining explicit authorization for a new
long-horizon capture after the architectural gate is green. Any new
capture needs a storage target that can retain an independently
audited ~5.13 GB file with provenance and retention policy.
**No new endurance run was launched in this closeout.**

## Additional final-code validation

A bounded affected matrix plus independent 3+4+3-year P5 short
continuation and canonical 10-year smoke was launched on
`7cb2a6000aa3eccaba6e3a9cd8da33f120f80654` as Actions run
`37728560768`. Its completion/conclusion must be recorded from
actual job evidence, not assumed here. The R3 failure remains a
release blocker irrespective of that result.

## Freeze boundary

Keep PR #14 draft/unmerged. Do not merge, start Stage 1, rebalance
magic, run millennium/endurance, or claim final Stage 0.5
architectural acceptance. The next allowed implementation work is
only the bounded R3 sequence integration and remaining R1/R2
regression findings, followed by short independent final-code gates.


## Follow-up: R3 bounded checked-page foundation

New standalone production primitive and focused regression tests were added
after this earlier blocked closeout report. See
`STAGE_0_5_R3_SEQUENCE_REPAIR_PLAN.md` for the exact 1k/10k read/append
measurements, completed run links, and remaining World-level failures.

This is a **bounded foundation**, not completed R3. PR #14's existing World
open/save path remains unchanged and eager for household member lists; the
optional integration prototype remains isolated on
`sim/stage-0-5-r3-implementation` until the ownership/identity, lifecycle
and independent continuation gates succeed. Stage 0.5 remains blocked.
