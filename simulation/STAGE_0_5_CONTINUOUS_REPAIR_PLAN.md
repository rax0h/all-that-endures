# Stage 0.5 continuous repair plan

Spec: `simulation/STAGE_0_5_CONTINUOUS_REPAIR_SPEC.md`.
Ledger: `simulation/STAGE_0_5_CONTINUOUS_REPAIR_PROGRESS.md`.

Each unit is developed in an isolated Git worktree and committed locally. Root integrates changes to common files sequentially; no worker publishes GitHub branches or starts long tests. Integration rejects unverified partial migration, duplicated ownership authorities, and changes to simulation rules. User authorization selects one combined review rather than a per-unit reviewer/approval loop.

## Task 1: bounded identity discovery and complete mutation routes

Worktree: `/workspace/scratch/c3a830e86cea/identity-work`.
Brief: `simulation/continuous-repair-briefs/identity.md`.

- [ ] Check in unit design/plan and permanent red regression matrix.
- [ ] Add checked reverse occurrence index/API and pinned versioned P2C witnesses.
- [ ] Discover only requested/resident groups; preserve placement overlays and token-checked weak cleanup.
- [ ] Route mutations before preparation to all current containing payload owners; equal distinct replacement must split identity.
- [ ] Reconcile and acknowledge affected groups only; validate all failure and old-pin paths.
- [ ] Measure fixed K=4 groups at H=1k/10k and run existing identity/ownership/lifecycle focused tests.

## Task 2: compact exact event-ID authority

Worktree: `/workspace/scratch/c3a830e86cea/event-id-work`.
Brief: `simulation/continuous-repair-briefs/event_ids.md`.

- [ ] Implement explicit MutableSet protocol parity with a verified range and checked ordinal fallback.
- [ ] Integrate descriptor conversion/open/save/count validation, native codec/canonical and detach.
- [ ] Publish descriptor and EventLog under one frozen hybrid plan; validate successor before runtime adoption.
- [ ] Add monotonic capability floor 5 and legacy 3/4 preservation.
- [ ] Measure 1k/10k normal authority and test fallback, retained reference, failure, recovery and stale writer.

## Task 3: household records and ordered history

Worktree: `/workspace/scratch/c3a830e86cea/household-work`.
Brief: `simulation/continuous-repair-briefs/households.md`.

- [ ] Add checked occurrence-position memberships with bounded limit/exclusion queries.
- [ ] Add sparse ordered-ID pages and checked vacancy rank/select metadata; normal removal must not repage history.
- [ ] Make household outer records lazy; page Settlement.households through supported checked backing.
- [ ] Route living selectors through exact member occurrences while preserving duplicates and order.
- [ ] Integrate touched-only owner/sequence preparation, retirement, legacy, aliases, recovery and detach.
- [ ] Measure outer/member/settlement axes separately and preserve the unresolved preparedness arithmetic path.

## Task 4: economy and culture

Worktree: `/workspace/scratch/c3a830e86cea/economy-culture-work`.
Brief: `simulation/continuous-repair-briefs/economy_culture.md`.

- [ ] Migrate belief scalar rows, practice definitions/traits and adoption scalar rows.
- [ ] Add exact adoption threshold memberships and insertion-order consumer seams.
- [ ] Migrate property headers and both typed ordered histories using the common nested primitive.
- [ ] Integrate all conversion/open/save/identity/recovery/legacy/detach seams.
- [ ] Measure fixed active lookups and one long-history transfer at 1k/10k, including bytes.

## Task 5: typed nested histories and institution/divinity integration

Worktree: `/workspace/scratch/c3a830e86cea/nested-history-work`.
Brief: `simulation/continuous-repair-briefs/nested_history.md`.

- [ ] Implement checked incarnation-owned typed list/set/map primitives with native equality and bounded caches.
- [ ] Communicate stable primitive interfaces to property and infrastructure consumers.
- [ ] Integrate institution/branch histories and God/Church/GAB histories; retain actual current topology/cohorts.
- [ ] Implement candidate-point follower selection preserving sorted ID order and RNG.
- [ ] Test aliases/replacement/retirement/legacy/failure/detach and 1k/10k fixed-current gates.

## Task 6: remaining scalar records/maps and inquiry threshold

Worktree: `/workspace/scratch/c3a830e86cea/cold-record-work`.
Brief: `simulation/continuous-repair-briefs/cold_records.md`.

- [ ] Migrate conflict/inquiry/threat records and independent resolutions map.
- [ ] Add community lookup and resurrection-token active predicates preserving selection/tie order.
- [ ] Add branch/passed application memberships and bounded at-least-five predicate, including explicit legacy handling.
- [ ] Prune obsolete touched-membership buckets rather than retain lifetime edits.
- [ ] Page infrastructure provenance through the common primitive; all-assets decay remains genuine current work.
- [ ] Integrate all persistence/lifecycle/identity seams and measure 1k/10k fixed-current gates.

## Task 7: integration and release evidence

- [ ] Sequentially integrate local commits, including shared namespace/format/schema, binding maps and hybrid plan seams.
- [ ] Run appropriate combined focused ownership/cross-family/recovery gates and exact short eager/lazy continuation (P5 3+4+3, seed843000).
- [ ] Obtain one final architectural review of the combined source, measurements and ledger; fix material findings and verify affected gates.
- [ ] Publish reviewed repair branch and workflow-only full-suite helper with exact source/tree/test provenance.
- [ ] Launch exactly one final full-suite CI run, preserve focused/P5/provenance evidence, and return the run URL immediately.
- [ ] Report any remaining proof/behavior/capture gates explicitly; do not promote PR #14 or imply an endurance result.
