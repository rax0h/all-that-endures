# Recursive Event snapshot integration

Native execution continues under the approved Stage0.5 architecture and execution
assignment. This closes the explicit Event boundary of the registered-record plan;
it is not a new approval, delegation or capability6 activation.

## Representation ruling

Use two closed history reference roles, `frozen-list` and `frozen-map`, backed by
the existing list pages/map entries and descriptor namespace. The mandatory
descriptor carries the same frozen role as the reference and dependency roster.
Readonly view classes reuse existing caches, physical placements and publication.
Their mutation entry rejects before consuming caller inputs. Their portable full
materialization is the existing exact FrozenList/FrozenDict codec representation.
Keep member-count witnesses in their existing base list/map schema, checking role
separately at the mandatory descriptor. No second registry, publisher, arbitrary
frozen-class inference or inline unbounded record header.

Event remains the actual native dataclass. Unsealed data uses ordinary recursive
histories. Event.seal preserves the native freeze operation, creating readonly
snapshot container backings rather than freezing a mutable alias in place.
Mutable record children retain their native freeze behavior and canonical sharing.
Explicit seal/materialization costs the actual snapshot input; ordinary reopen and
record header save must not walk archived data. Preserve absent/false/true seal
metadata and immutable mutation behavior.

## Tasks

- [x] TDD closed frozen reference/descriptor roles, readonly views, exact portable
  types, malformed role rejection, old-pin point reads and caller-input guards.
- [x] Add concrete FrozenList/FrozenDict admission to the existing recursive runtime
  and source memo; extend existing dependency/retirement/type-witness verification.
- [ ] TDD native Event admission, field assignment and seal hooks, aliases, mutable
  record children, eager event peers, cold reopen, faults, detach and corruption.
- [ ] Measure data point reads and header/scalar edit with fixed related U at paired
  unrelated H; publish source-bound evidence and update schema/closeout ledgers.

## Outstanding global boundaries

Actual special root collection imports, oversized imported tuple/string/bytes
classification, exhaustive schema and byte bounds remain separate closure work.
Persisted append/count-tree promotion, exotic key equality, complete capability6
ordinary open/source-copy, integrated P5, the one final applicable suite and fresh
independent review remain open. No Stage1, gameplay, PR14, merge or new endurance.

## Native mutable-log peer follow-through

A new native recursively backed Event appended to the mutable World log exposed
two equal bodies on reopen. Checked record load now selects its related resident
mutable-log root Event, compares the compact header before binding, and preserves
that native object as the sole registry canonical body. The first edit through
the World log acquires its record backing before the original setter. This follows
related checked placements only, without archived data or global registry scans.

Explicit full detach uses its one sharing memo to rewire only the staged standalone
EventLog tail when recursive materialization already cloned the same backed Event.
A before-publication fault leaves the publisher log/body unchanged. Legacy eager
TrackedDict Event imports and sealed tail/segment activation remain separate.
