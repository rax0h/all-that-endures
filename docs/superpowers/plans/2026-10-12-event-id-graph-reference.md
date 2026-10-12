# Event-ID Facade References in Recursive Graphs

Continue the authorized complete Stage0.5 plan inline. The existing compact
World.event_ids owner remains the only Event-ID value authority. A recursive
page/entry/record needs a closed typed reference carrying that owner's checked
incarnation; the legacy tuple marker carries no identity and cannot distinguish
a literal tuple from a physical graph edge. Add a storage reference, not a new
facade, registry, descriptor, lease pool or value snapshot.

- [x] RED: codec and existing closed field/physical-owner reference contracts.
- [x] Add a closed positive-incarnation reference and existing-codec tag.
- [x] Explicit source copy replaces only legacy markers with matching captured
      facade labels, keeps the original root authority, checks target identity.
- [x] Runtime resolves the same native facade through its checked owner-zero
      placement; finite admission rejects foreign/closed authorities first.
- [x] Integrate shared routing, reference-header comparisons, frozen-plan
      publication, readonly rejection, copy/detach and recovery.
- [ ] Run focused/affected and fixed H1k/H10k gates; publish evidence.

Legacy family tuple markers retain compatibility until their explicit adapter
is integrated; literal lookalike tuples must remain values. Capability6 is still
withheld. Exotic resident Event-ID key equality remains a separate open boundary.

Resumed validation adds two RED boundaries: an unused legacy set snapshot
without a typed edge must remain compatible; a malformed compact descriptor
with fully refreshed, valid catalog witnesses must reject on current-source copy.
Typed-edge scrubbing now returns the used facade IDs and validates their sole
compact root descriptor before publication. Source witness corruption remains
a separate earlier check. No capability6 activation or exotic-key claim.
