# Compact exact event-ID authority: design and plan

Spec: `STAGE_0_5_CONTINUOUS_REPAIR_SPEC.md` and `continuous-repair-briefs/event_ids.md`.

The normal authority is a verified `1..end` set, independently proved from actual set values. `EventIdSet(MutableSet)` keeps one public object across a transition to a populated tracked native-set fallback. The compact disk kind is `event-ids-range/v1`, its logical description is `(tag,end,0)`, and its single checked physical row is key `0` with `(0,(tag,end))`. Other exact sets keep checked stable ordinal rows. Ordinary range appends and saves touch the descriptor only; explicit whole-set transformations may materialize. Native conversions, operators, representatives, sharing, detached checkpoints, guards, and atomic recovery retain their contracts.

The reader capability floor is 5. New readers accept 3/4/5 and transactionally publish `max(current,required)`; older stores restore exactly. Compact successor bytes and semantics are checked before runtime EventLog adoption. The existing hybrid save remains the only commit owner.

## Implementation plan

> Agent execution: use executing-plans inline. No child agents or per-unit reviewer. Root integrates and runs the final review.

Goal: remove history-sized normal event-ID containers and open/save traversal while preserving exact authority.

Architecture: a concrete set facade supplies native behavior, a compact collection adapter supplies checked storage, and tracker hooks compose descriptor/fallback changes with the existing cold plan. Exact legacy fallback is deliberately resident; its explicit transition and restore costs are reported separately from compact normal gates.

Tech stack: Python, existing typed codecs and SQLite transactional stores, pytest.

Global constraints: capability floor 5; no independent child commit; preserve facts, causes, order, representatives, RNG, sharing and retained aliases; no source mutation during conversion; no full suite, endurance or GitHub writes in this unit.

Review focus: malformed descriptors must fail closed; duplicate/equal representatives preserve native semantics; self-assignment from augmented mutation succeeds; close never materializes range history; uncertain publication cannot clear an unacknowledged descriptor.

### Task 1: shared capability floor

Files: `ate_sim/persistence_lazy_store.py`, `tests/test_persistence_lazy_store.py`.
Interface: `BOUNDED_AUTHORITY_FORMAT_VERSION = 5`; `commit(required_format_version=...)` accepts 3/4/5 and never decreases the published floor.

- [ ] Add tests for 5 publication/open, no downgrade, and transactional rollback; observe red.
- [ ] Implement the minimal constant, accepted versions and monotonic transaction update; run focused store gates.
- [ ] Commit and send the minimal interface/commit to sibling units.

### Task 2: native exact facade and checked storage integration

Files: new `ate_sim/persistence_event_ids.py`, new `tests/test_persistence_event_ids_compact.py`; narrow changes in `core.py`, `canonical_stream.py`, `event_log.py`, `persistence_adapters.py`, `persistence_tracking.py`, `persistence_session.py`, `persistence_lazy.py`, `persistence_cold_save.py`.
Interface: `EventIdSet.from_values(values)`, `from_descriptor(end)`, `bind(tracker,namespace)`, native set methods, descriptor-aware adapter restore/conversion, tracker storage/close/detach behavior.

- [ ] Add behavior tests for native methods/operators, range proof, exact shapes, guard-before-noop, range conversion/open/save, and malformed authority; observe red.
- [ ] Implement concrete facade and allowlists, descriptor adapter, conversion/head/layout changes, and specialized tracker roots; run focused gates.
- [ ] Add and observe red recovery/lifecycle/retained-alias regressions, then implement successor validation and staged native detach.
- [ ] Run affected existing codec/tracking/lazy-open/cold-save/detach gates and commit.

### Task 3: numerical proof and handoff

Files: `STAGE_0_5_EVENT_ID_VALIDATION.md` and focused numerical tests.
Gates: 1k/10k range has zero resident members/ordinals, one persisted key and open authority row, zero member/order or ordinary emit/save ID visits, one descriptor write per emit, resident <=8 KiB and growth <=1 KiB, descriptor byte growth <=32, empty acknowledged journal. Sealed integration uses 2048/20480 plus fixed tail.

- [ ] Measure the specified counters/bytes and verify the native/corruption/legacy/failure matrix.
- [ ] Write exact red/green commands, measurements, local commits and limitations to validation report; inspect diff and commit.

## Ledger

- Base: `d603aec298c3328d8b71d4045cd98b90d527fc0b` in the pre-created isolated `event-id-work` worktree.
- Ruling: only focused tests run here; shared spec explicitly assigns the full suite and final reviewer to root integration.
