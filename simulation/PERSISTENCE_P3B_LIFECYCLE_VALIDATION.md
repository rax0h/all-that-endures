# P3B lifecycle — validation evidence

**Status:** implementation review input; not architect acceptance.
**Scope:** `simulation/PERSISTENCE_P3B_LIFECYCLE.md`.
**PR branch before landing:** `sim/stage-0-5-stabilization` at `d3dfe02728d38902e73cd7740fbbdebf32981aa9`.
**Final tested product/test bytes:** represented by candidate heads
`43f5f62ad7e16437c4313a2c57716508473956b9`,
`1b836fe16a5ffe0a375fa4599f61b1976c404d0d`, and
`44c462b7ea62b74f9ea8214954c5796905b120dd`.
Those heads differ only in candidate-only workflow scaffolding after the final
product/test changes.

## Implemented lifecycle surface

This slice adds explicit cold-session lifecycle and full-history operations while
preserving accepted atomic cold save/recovery and the normal checkpoint default:

- `session.detach(materialize_history=True)` with explicit opt-in materialization;
- `session.verify_history()`;
- guarded cold `World.digest()`;
- guarded streaming `history_archive.export_archive()`;
- deliberate cold rejection for schema-8 checkpoint dumps/save and direct
  disk-backed EventLog pickle;
- early cold-mode rejection for legacy P2 read/bind/write entry points;
- shared lifecycle operation guards for active/quiescent ownership;
- staged detach that preserves the same World and resident tail Event objects,
  current aliases, unsaved edits and exact logical F/N boundaries.

A late integration test exposed a detach bug in RecordTable staging: inserting a
live IndexedRecord into a staged RecordTable invoked RecordTable.__setitem__ and
attempted to rebind the live record during the guarded detach preparation phase.
The correction constructs the staged table with `dict.__setitem__` and defers
`_index_table` / `_index_key` rebinding until publication. This preserves the
pre-publication rollback boundary.

## Validation chronology

### Focused functional gate

Actions run `37255447422`, candidate
`592743d6e3b60a405beb31c0f380413c1a9a7858`:

- **77 passed, 3 deselected in 77.71 s**
- Covered lifecycle, cold session/open, EventLog, canonical digest and history
  archive behavior, excluding the 4/40/400 allocation measurement cases.

### Broad pre-correction diagnostic gate

Actions run `37256021379`, candidate
`427dfed9f003d58aa98c8265127508412763f3b4`:

- affected selection: **199 passed, 1 failed in 1053.14 s**
- full suite: **629 passed, 1 failed in 1560.93 s**

Both failures were the same test-only measurement assertion for the four-segment
archive case. The preceding digest had warmed the entire four-segment reader
cache, so archive correctly required zero additional physical segment reads
rather than eight. Product behavior was not implicated.

### Corrected four-segment measurement

Actions run `37260975859`, candidate
`e3cd6abfda6316af44111fcdbcaf82c174cc6ab7`:

- **1 passed in 8.36 s**
- measured four-segment archive reads: **0**, with the full four-segment prefix
  already resident after digest.

### Final targeted lifecycle proof after RecordTable correction

Actions run `37261345011`, candidate
`43f5f62ad7e16437c4313a2c57716508473956b9`:

- **18 passed in 14.74 s**
- includes state guards, partition-shape detach cases, reversible mid-prefix
  failure, warmed missing/corrupt segment verification, archive failure cleanup,
  alias preservation and short independent continuation through save/reopen,
  verify, archive, unsaved edit, detach, schema-8 checkpoint roundtrip and
  further simulation.

### Final exact-source full suite

Actions run `37261495839`, candidate
`1b836fe16a5ffe0a375fa4599f61b1976c404d0d`:

- **640 passed in 2287.60 s (0:38:07)**
- command: `PYTHONPATH=.:simulation python -m pytest -q simulation/tests`

This is the final full-suite gate after the RecordTable product correction.

The affected command was not repeated after that narrow correction. Instead, the
changed lifecycle path was rerun directly (18/18) and then the entire
`simulation/tests` suite passed (640/640). This was an intentional reduction of
a redundant long run; the full suite includes the affected persistence tests.
The earlier affected run remains evidence for the broader pre-correction surface,
not evidence for bytes changed by the later RecordTable fix.

### Final 4/40/400 measurement gate

Actions run `37264362976`, candidate
`44c462b7ea62b74f9ea8214954c5796905b120dd`:

- **3 passed, 7 deselected in 1256.48 s (0:20:56)**
- command:
  `PYTHONPATH=.:simulation python -m pytest -q -s simulation/tests/test_persistence_history_operations.py -k streaming_history_bounds_and_detach_cost_are_measured`

No product/test bytes changed between the final full-suite candidate and this
measurement candidate; only temporary workflow text changed.

## Final measured history bounds

Fixture construction and cold open are outside the tracemalloc windows.
Allocation values below are incremental bytes observed around the named explicit
operation. The ordinary prefix reader remained capped at four decoded segments
in every measured streaming operation.

| Metric | 4 segments | 40 segments | 400 segments |
| --- | ---: | ---: | ---: |
| verify checked reads | 4 | 40 | 400 |
| verify checked bytes | 2,284,661 | 22,928,494 | 230,104,095 |
| verify peak allocation | 8,123,201 | 8,311,707 | 8,331,101 |
| verify retained allocation | 1,239,631 | 1,512,135 | 1,521,471 |
| digest segment reads | 4 | 40 | 400 |
| digest peak allocation | 9,875,189 | 10,703,497 | 10,723,336 |
| digest retained allocation | 3,287,639 | 3,288,401 | 3,298,977 |
| archive segment reads | 0 | 80 | 800 |
| archive peak allocation | 262,109 | 10,629,705 | 10,649,541 |
| archive retained allocation | 124,973 | 3,296,898 | 3,304,008 |
| detached compressed bytes | 30,503 | 211,688 | 2,011,907 |
| detach peak allocation | 8,203,229 | 8,605,162 | 10,435,211 |
| detach retained allocation | 151,644 | 547,669 | 2,371,830 |

Interpretation:

- `verify_history()` rereads exactly every captured segment through checked
  storage despite cache state; checked bytes scale with history.
- digest requires one logical history pass. Reader-cache residency remains <=4.
- archive performs its allowed node/causal streaming passes. At 4 segments the
  whole prefix remains warm from digest, so it performs zero additional physical
  reads; at 40/400 segments it performs 2x segment reads as the four-segment
  cache cannot retain the full prefix.
- verify/digest peak allocation stays approximately flat from 40 to 400
  segments, consistent with bounded decoded working state.
- detach is deliberately not bounded-total-memory: compressed output and legacy
  in-memory indexing grow with history. The increasing retained/peak figures are
  expected for explicit materialization.

The lifecycle measurement does not emit a separate numeric memo/identity-entry
count. Existing cold identity/open tests continue to prove that historical
prefix Events are not bound into current identity ownership, and the lifecycle
tests assert the reader cache bound. This document therefore does not claim a
new numeric memo-entry scaling measurement beyond those existing guarantees.

## Failure / ownership matrix

| Case | Evidence / behavior |
| --- | --- |
| default detach | rejects unless `materialize_history=True`; source remains active |
| current_people scope | lifecycle operation rejects before history work |
| active simulation step | lifecycle operation rejects before history work |
| reentrant lifecycle/save/close | rejected under operation guard |
| recovery-required | verify/detach reject; no implicit resolve |
| stale local branch | explicit detach materializes local branch; winner store is unchanged |
| directly closed store | lifecycle operations reject; no reopening by filename |
| detach mid-prefix failure | original World/log/store/generation/dirty state remain usable |
| detach staging failure | no source graph publication occurs |
| RecordTable current graph | staged structurally; live records rebind only at publication |
| warmed corrupt segment | verify_history fails through checked storage read |
| warmed deleted segment | verify_history fails through checked storage read |
| archive callback mutation | rejected by lifecycle guard |
| archive mid-encoding failure | no final archive; session remains usable |
| checkpoint cold World | rejects before digest/pickle/path mutation |
| direct disk EventLog pickle | rejects immediately |
| legacy read_snapshot | cold manifest rejected before verify_all |
| legacy bind_snapshot | cold manifest rejected before baseline bind |
| legacy write_snapshot | cold World rejected before audit/export/path side effects |
| successful detach | same World and tail Event identities; old log/session closed |
| detached continuation | digest/checkpoint/further simulation match independent control |

## Compatibility boundaries

- `CHECKPOINT_SCHEMA` remains 8.
- Normal portable in-memory checkpoints remain supported.
- Cold checkpoint serialization is intentionally rejected until explicit detach.
- Direct disk-backed EventLog pickle is intentionally rejected.
- P2 read/bind/write remain valid for their genuine legacy formats and reject
  cold storage early.
- No schema bump, implicit migration, automatic detach, automatic archive or
  checkpoint-default replacement was added.
- Accepted cold save/recovery architecture was not restarted.
- No millennium/endurance, balance, Stage 1, merge or unrelated gameplay work
  was performed.

## Requirement matrix against lifecycle sections 2-10

| Section | Result |
| --- | --- |
| 2 shared operation/lifetime contract | implemented and covered by active/current-scope/reentrant/recovery/stale/closed tests |
| 3 explicit detach | implemented with staged history/current graph, alias/tail identity preservation, rollback and RecordTable-safe publication |
| 4 full-history verification | implemented using accepted checked prefix verification plus resident suffix validation and diagnostics |
| 5 digest/archive | guarded streaming implementation; internal digest avoids public reentrancy; archive preflight/failure cleanup covered |
| 6 legacy compatibility gates | cold checkpoint/pickle/P2 read-bind-write early rejection covered; schema 8 preserved |
| 7 task sequence/tests | focused, targeted, final full-suite and final measurement evidence recorded |
| 8 review focus | failed detach mutation, stale marker cleanup, supplied-digest preflight, early legacy rejection and sealed-tail preservation are covered |
| 9 parent close/detach/export contract | preserved; successful detach closes old cold ownership and returns portable World |
| 10 measurable bounds | 4/40/400 read/byte/allocation table recorded; bounded streaming vs explicit detach growth separated |

## Exact final product/test blobs

These blobs are the bytes intended for PR #14 landing and are identical to the
final tested candidate source/test bytes:

- `simulation/ate_sim/checkpoint.py` — `1033b2ef0b0b1cb048ec25f64adf4c64d234d147`
- `simulation/ate_sim/core.py` — `cefeef8a241995d29adb4891e71554947f1062f3`
- `simulation/ate_sim/event_log.py` — `77a21bb43815cafed28931dffdbb30fc12638eef`
- `simulation/ate_sim/history_archive.py` — `864edd014082de2742ac17ed391b3000472a2427`
- `simulation/ate_sim/persistence_adapters.py` — `150f6ea93f09973057c681896d5cbb38c01656c9`
- `simulation/ate_sim/persistence_lifecycle.py` — `4ae974399e76273be4ea8fac0b80c6e9e7c27f30`
- `simulation/ate_sim/persistence_tracking.py` — `2eb3238c096c28a79d2c4a54a05290a163e3e264`
- `simulation/tests/test_persistence_history_operations.py` — `3c4afc4cafcd936a7cffc119e30fb9da99be6fcf`
- `simulation/tests/test_persistence_lifecycle.py` — `3466c8628032f59895153168cac7e7fcd5c6083b`

The candidate-only workflow `.github/workflows/p3b-lifecycle-focused.yml` is
validation scaffolding and must not be landed.

## Remaining boundary

This file is an Astra review input, not self-acceptance. It does not declare P3B
or Stage 0.5 complete. P3B acceptance, later persistence work, checkpoint-default
changes, long-horizon simulation, Stage 1 and PR merge require subsequent review
and instruction.
