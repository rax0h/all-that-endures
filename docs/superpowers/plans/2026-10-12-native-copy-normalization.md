# Native Copy Input Normalization Plan

The complete Stage0.5 directive authorizes inline implementation.

Goal: explicitly stage a standalone closed graph from known legacy tracked
containers, RecordTable roots, native registered records and existing recursive
history aliases. Preserve internal sharing with one memo and reject cycles and
unknown subclass state before any destination identity allocation.

Use a private copy primitive and an explicitly named recursive-runtime copy-input
entry point. Ordinary identity-preserving admission remains strict. The copy
creates new input objects; it never changes a source record, table index,
tracking binding, backing lease or pending overlay. Native readonly roles and
exact Event seal-state presence are preserved. No second registry/publisher.

This supports actual input staging for the remaining converter; it does not
establish preserved persistent incarnation mapping or complete format6 activation.
EventLog partition and source store captures remain their existing authorities.
Nested EventLog input is explicitly excluded from this finite-value primitive.

Tasks:
- [x] RED: real tracked World-log Event copied, admitted, edited and reopened.
- [x] Clone only concrete allowed containers and registered schema records.
- [x] Verify RecordTable/index source preservation, root wrappers, backed aliases,
      readonly snapshots, atomic invalid/cycle rejection and lifecycle failures.
- [x] Run focused/affected recursive gates and publish exact evidence.

Final25 focused passed in3.08s. Affected102 passed in20.80s before only the last
three tests (backed readonly copy and paired commit faults); production matches
both gates. Explicit runtime copy rejects foreign live bound sources: a separate
coherent source capture owns cross-store conversion. No ordinary admission change
or persistent incarnation rewrite is claimed. Actual default World/state fields
and indexed SkillState copy/admit/save/reopen are exercised; this is not the
exhaustive actual schema/byte closure gate.
