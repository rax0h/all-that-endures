# Recursive registered record integration implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Native execution is already explicitly authorized by STAGE_0_5_SOL_61_EXECUTION.md; no new routine approval or delegation.

**Goal:** Admit declared mutable World records into recursive histories with one canonical native object and checked compact backing.

**Architecture:** Extend the existing checked physical catalog and incarnation relation. A dedicated immutable RecordReference points to an ordered, closed-schema record header; the canonical live value is the declared dataclass itself. Header children are existing history references or record references, and all publication continues through the existing frozen hybrid plan.

**Tech stack:** Python, WorldCodec, LazyRecordStore MVCC, existing identity coordinator/registry and mutation hooks.

**Spec:** simulation/STAGE_0_5_FINAL_ARCHITECTURE.md sections 4–8 and 10; simulation/STAGE_0_5_SOL_61_EXECUTION.md; exhaustive simulation/STAGE_0_5_FINAL_SCHEMA_INVENTORY.md.

## Global constraints

- No generic serializer, second identity registry, DAG, publisher, or ordinary-open migration.
- Preserve actual declared record classes, aliases, ordered fields, event seal metadata, and old generation values.
- Validate actual incoming D before owner changes; imported values do not inherit generated bounds.
- Only complete capability-6 conversion/open may advertise the finished format. Primitive/staged tests advertise no capability6.
- No Stage1, gameplay changes, PR14 changes/merge, force push or new endurance.
- Focused/affected checks per component; one final applicable full suite only at stable whole-Stage0.5 source.

## Review focus

- A frozen or foreign dataclass must not acquire a mutable backing merely by resembling a known type (task1).
- Missing/extra fields, invalid references and unknown stored type names fail closed without dynamic imports (task1).
- A native record shared with eager World state and two history owners must remain one object (task2).
- A held record removed from every owner must retain private edits without resurrecting World state (tasks2–3).
- Stale writers, closed aliases, callbacks and lost acknowledgement must not thaw or publish a different graph (task3).

### Task1: Closed record header and physical owner contract

**Files:** Create simulation/ate_sim/persistence_record_headers.py; modify persistence_adapters.py and persistence_history_owner_adapters.py; create simulation/tests/test_stage_0_5_final_record_headers.py.

**Interfaces:** RecordReference(incarnation:int), record_reference(value)->bool; record_header(record, *, values:tuple|None=None)->tuple; checked_record_header(header)->(declared_class, ordered_values, event_state); restore_record_header(header)->native_record; read_record_header(store,pin,incarnation)->tuple. Physical key is (incarnation,0) in aux.lazy.records.headers, schema1. Tag is recursive-record/v1; encoded reference tag typed-record/v1. A header contains the registered module/class schema name, one ordered value per declared field, and explicit event seal metadata only for Event.

- [x] Write failing cases for declared class/value round-trip, foreign/frozen rejection, malformed headers/references, exact child-placement witnesses and old/current point reads at H1k/H10k.
- [x] Run to confirm the missing primitive fails (missing module, collection error).
- [x] Implement exact closed references/header validation and restore, using existing schema and codec; no live object binding or publication inside helpers.
- [x] Register a concrete record physical adapter with field/index paths, exact child reference projection, no memberships and schema1.
- [ ] Run focused and affected catalog/codec/history tests; record actual source hashes and measured read bounds; commit with [skip ci].

### Task2: Native canonical record admission and assignment

**Files:** persistence_history_runtime.py; new focused record binding module; persistence_tracking.py only existing hook interfaces; persistence_lazy_identity_headers.py; persistence_lazy.py at recursive admission/decode/preparation integration points.

**Consumes:** Task1 header/reference and physical adapter.
**Produces:** Registry canonical object is the actual declared dataclass; record binding owns compact backing state, not another registered live object. Recursive admission returns RecordReference; checked decode verifies the physical placement before selecting/restoring the native object. Existing assignment hooks preflight all incoming fields, normalize children to canonical histories/records, and route affected owners before changes.

- [ ] Add failing native class, shared record, shared descendant, eager/lazy peer, replacement, cycle, failed assignment and cold reopen cases.
- [ ] Extend recursive preflight/admission/decode and compact identity-header comparisons without broadening immutable-value admission.
- [ ] Add bounded header/backing dirt discovery and physical field-child synchronization to existing D journals.
- [ ] Test exact aliases and values across save/reopen/detach; prove fixed input work at paired unrelated history scales.

### Task3: Existing publisher, leases, retirement and recovery

**Files:** persistence_history_dependencies.py; persistence_history_retirement.py; persistence_lazy.py; record binding module; focused record World tests.

**Consumes:** Task2 canonical record/backing interface.
**Produces:** Record dependencies borrow the same World publisher token; frozen record bytes/placement witnesses are captured/validated/acknowledged by the existing hybrid plan. Retained unowned records keep private overlays. Bounded retirement deletes record headers and child placements while old pins remain valid.

- [ ] Add failing last-owner/held alias/revival, collection, stale-session, close, before-commit/after-commit and corruption cases.
- [ ] Include record backing kind in dependency and bounded retirement authority with the exact header key (incarnation,0); never register a backing wrapper as the canonical object.
- [ ] Route pending record bytes through nested_history_version_changes and its existing acknowledgement boundary; avoid scanning clean registry or headers.
- [ ] Run focused and affected tests, record source/bounds evidence and commit [skip ci].

### Task4: Exhaustive schema evidence and integration boundary

**Files:** STAGE_0_5_FINAL_SCHEMA_INVENTORY.md; STAGE_0_5_FINAL_PROGRESS.md; machine-readable validation artifact; record/schema tests.

- [ ] Account explicitly for every declared record and field, generated guards and imported oversized/frozen/event compatibility boundaries; do not mistake task1 parser coverage for World record closure.
- [ ] Exercise all supported record value/child classes, fixed and unbounded topology, native operations and observable failure behavior.
- [ ] Mark record closure complete only after tasks2–3 and exhaustive field evidence pass. Complete promotion/equality/capability6/P5/final review remains separate work in the approved overall plan.
