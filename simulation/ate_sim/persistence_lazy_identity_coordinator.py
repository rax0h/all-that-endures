"""Affected-group overlays; LazyIdentityRegistry alone owns live identity.

Runtime family adapters supply loading/path installation and dirty callbacks.
These callbacks must bypass user mutation notifications when stitching checked
copies. This module never commits, inventories the live registry, or infers
logical deletion from clean-cache eviction.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from contextlib import contextmanager
import weakref
import sys
from .incremental_store import StoreIntegrityError, StoreConflictError, StoreFormatError, RecordChange
from .persistence_lazy_identity import IncarnationId, Occurrence
from .persistence_lazy_identity_catalog import IdentityCatalog, CheckedIdentityGroup, OWNER_NAMESPACE, placement_path
from .persistence_lazy_store import IdentityOccurrenceChange, VersionChange, ORDINARY_QUERY_OWNER_INDEX
from .persistence_lazy_families import ParticipantDelta, IDENTITY_OWNER_FAMILIES
from .persistence_lazy_spill import CheckedSpool


@dataclass(frozen=True)
class PreparedCoordinatorState:
    delta: ParticipantDelta
    catalog_delta: ParticipantDelta
    expected_generation: int
    next_incarnation: int
    overlay_fingerprint: tuple


def _heap_size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    if isinstance(value, CheckedSpool):
        return value.resident_bytes
    size = sys.getsizeof(value)
    if type(value) in (tuple, list):
        size += sum(_heap_size(v, seen) for v in value)
    return size


class IdentityCoordinator:
    def __init__(self, store, pin, registry, *, load_owner, resolve_path, install_path,
                 mark_dirty, preflight, encode_placement=None,
                 prepare_owner_header=None,
                 occurrence_limit=4096, byte_limit=2 * 1024 * 1024):
        if registry.store_identity != store.store_identity:
            raise StoreConflictError('identity coordinator registry belongs to another store')
        if type(occurrence_limit) is not int or occurrence_limit < 1 or type(byte_limit) is not int or byte_limit < 1:
            raise ValueError('identity cache budgets must be positive exact integers')
        self.store, self.pin, self.registry = store, pin, registry
        self.catalog = IdentityCatalog(store, occurrence_limit=occurrence_limit, byte_limit=byte_limit)
        with store.read_snapshot(pin):
            self._baseline_allocator = self.catalog._descriptor(pin)[2]
        registry.allocator.next_value = max(registry.next_incarnation, self._baseline_allocator)
        self.load_owner, self.resolve_path, self.install_path = load_owner, resolve_path, install_path
        self.mark_dirty, self.preflight = mark_dirty, preflight
        # Concrete World family adapters compare compact headers. Standalone
        # scalar fixtures retain their checked store codec; no history codec
        # or owner namespace is inferred by the coordinator.
        self.encode_placement = encode_placement
        self.prepare_owner_header = prepare_owner_header
        self._preparing_headers = False
        self.occurrence_limit, self.byte_limit = occurrence_limit, byte_limit
        self.discovered_groups = OrderedDict()
        self._cache_occurrences = self._cache_bytes = 0
        self._weights = {}
        self.placement_overlay = {}
        self._original = {}
        self._by_owner = {}
        self._by_incarnation = {}
        self.dirty_owners, self.dirty_incarnations = set(), set()
        self._value_dirty_groups = set()
        self._prepared = None
        self._accepted = None
        self._discoveries = 0
        self._routing = set()
        self._mutation_depth = 0

    def _marker(self, owner, path):
        return self.store.codec.encode((*owner, path))

    def _drop(self, key):
        self.discovered_groups.pop(key, None)
        occurrences, size = self._weights.pop(key)
        self._cache_occurrences -= occurrences
        self._cache_bytes -= size

    def _trim(self):
        while (self._cache_occurrences > self.occurrence_limit or self._cache_bytes > self.byte_limit
               or len(self.discovered_groups) > 256):
            key = next((k for k in self.discovered_groups if k[1] not in self.dirty_incarnations), None)
            if key is None:
                break  # Actual unsaved group state is reported separately.
            self._drop(key)

    def discover_group(self, incarnation):
        self.preflight()
        inc = incarnation.value if isinstance(incarnation, IncarnationId) else incarnation
        key = self.pin.captured_head, inc
        if key in self.discovered_groups:
            self.discovered_groups.move_to_end(key)
            return self.discovered_groups[key]
        if inc >= self._baseline_allocator:
            if not 0 < inc < self.registry.next_incarnation:
                raise StoreIntegrityError('unknown unallocated live incarnation')
            group = CheckedIdentityGroup(inc, (), (), None)
        else:
            group = self.catalog.read_identity_group(self.pin, inc)
        self._discoveries += 1
        value = group.occurrences, group.links, group.anchor
        size = _heap_size(value) + sys.getsizeof(group)
        self.discovered_groups[key] = group
        self._weights[key] = len(group.occurrences), size
        self._cache_occurrences += len(group.occurrences)
        self._cache_bytes += size
        self._trim()
        return group

    def _current_placements(self, group):
        out = CheckedSpool(self.store.codec, entry_limit=self.occurrence_limit,
                           byte_limit=self.byte_limit, unique=True)
        try:
            for ns, key, path in group.occurrences:
                marker = self._marker((ns, key), path)
                change = self.placement_overlay.get(marker)
                if change is None or (not change.delete and change.incarnation_id == group.incarnation_id):
                    out.add((ns, key, path))
            # Only final additions not already belonging to this pinned group
            # are appended. Overlay indexes carry D; no set of all G is needed.
            for marker in self._by_incarnation.get(group.incarnation_id, ()):
                change = self.placement_overlay[marker]
                if (not change.delete and change.incarnation_id == group.incarnation_id
                        and self._original.get(marker) != group.incarnation_id):
                    out.add((change.owner_namespace, change.owner_key, change.occurrence_path))
            return out.freeze()
        except BaseException:
            out.close()
            raise

    @contextmanager
    def _mutation(self):
        if self._preparing_headers:
            raise StoreConflictError('identity mutation is blocked during owner header preparation')
        self._mutation_depth += 1
        try:
            self.preflight()
            if self._prepared is not None:
                raise StoreConflictError('identity coordinator has an unacknowledged frozen plan')
            yield
        finally:
            self._mutation_depth -= 1

    def routes_for_mutation(self, obj):
        with self._mutation():
            return self._routes_for_mutation(obj)

    def stitch_for_read(self, obj):
        """Check and canonicalize current peers without granting mutation dirt."""
        with self._mutation():
            return self._routes_for_mutation(obj, mark_dirty=False)

    def _routes_for_mutation(self, obj, *, mark_dirty=True):
        self.preflight()
        if self._prepared is not None:
            raise StoreConflictError('identity coordinator has an unacknowledged frozen plan')
        incarnation = self.registry.incarnation_for_object(obj)
        if incarnation is None:
            return ()
        if incarnation.value in self._routing:
            raise StoreConflictError('reentrant shared mutation routing')
        group = self.discover_group(incarnation)
        placements = self._current_placements(group)
        if not placements:
            return ()  # Retained, unowned alias: never resurrect its old owners.
        self._routing.add(incarnation.value)
        owners = []
        owner_keys = set()
        try:
            installations = []
            for namespace, key, path in placements:
                owner = namespace, key
                value = self.load_owner(owner)
                current = self.resolve_path(value, path)
                if current is not obj:
                    encode = (self.store.codec.encode if self.encode_placement is None
                              else lambda child: self.encode_placement(owner, path, child))
                    if encode(current) != encode(obj):
                        raise StoreIntegrityError('checked shared placement payload copies disagree')
                    installations.append((owner, path))
                if owner not in owner_keys:
                    owners.append(owner)
                    owner_keys.add(owner)
            # Validate the entire requested closure before stitching any copy.
            for owner, path in installations:
                self.install_path(owner, path, obj)
            for namespace, key, path in placements:
                self.registry.attach_occurrence(obj, Occurrence(namespace, key, path))
            if not mark_dirty:
                self._trim()
                return tuple(owners)
            for owner in owners:
                self.dirty_owners.add(owner)
                self.mark_dirty(owner)
            self.dirty_incarnations.add(incarnation.value)
            self._value_dirty_groups.add(incarnation.value)
            # Keep actual unsaved source-group witnesses after clean trimming.
            cache_key = self.pin.captured_head, incarnation.value
            if cache_key not in self.discovered_groups:
                self.discovered_groups[cache_key] = group
                self._weights[cache_key] = len(group.occurrences), _heap_size((group.occurrences, group.links, group.anchor)) + sys.getsizeof(group)
                n, size = self._weights[cache_key]
                self._cache_occurrences += n
                self._cache_bytes += size
            return tuple(owners)
        finally:
            self._routing.remove(incarnation.value)
            if hasattr(placements, 'close'):
                placements.close()

    def replace_placement(self, owner, path, obj):
        with self._mutation():
            return self._replace_placement(owner, path, obj)

    def _replace_placement(self, owner, path, obj):
        self.preflight()
        if self._prepared is not None:
            raise StoreConflictError('identity coordinator has an unacknowledged frozen plan')
        marker = self._marker(owner, path)
        if marker not in self._original:
            self._original[marker] = self.catalog.read_identity_membership(self.pin, owner, path)
        original = self._original[marker]
        previous = self.placement_overlay.get(marker)
        old = original if previous is None else None if previous.delete else previous.incarnation_id
        if old is not None:
            self.discover_group(old)
        chosen = None if obj is None else self.registry.bind(obj).value
        if chosen is not None:
            self.discover_group(chosen)
        occurrence = Occurrence(*owner, path)
        self.registry.detach_occurrence(occurrence)
        if obj is not None:
            self.install_path(owner, path, obj)
            self.registry.attach_occurrence(obj, occurrence)
        self._record_placement_change(owner, path, original, old, chosen)
        self._trim()
        self.dirty_owners.add(owner)
        self.mark_dirty(owner)

    def _record_placement_change(self, owner, path, original, old, chosen):
        """Apply a prevalidated placement edit; no loading or user callbacks."""
        marker = self._marker(owner, path)
        affected = {i for i in (original, old, chosen) if i is not None}
        for inc in affected:
            entries = self._by_incarnation.get(inc)
            if entries is not None:
                entries.discard(marker)
                if not entries:
                    self._by_incarnation.pop(inc, None)
            self.dirty_incarnations.add(inc)
        if chosen == original:
            self.placement_overlay.pop(marker, None)
            self._original.pop(marker, None)
            entries = self._by_owner.get(owner)
            if entries is not None:
                entries.discard(marker)
                if not entries:
                    self._by_owner.pop(owner, None)
        else:
            self._original[marker] = original
            self.placement_overlay[marker] = IdentityOccurrenceChange(*owner, path, chosen, delete=chosen is None)
            self._by_owner.setdefault(owner, set()).add(marker)
            for inc in {i for i in (original, chosen) if i is not None}:
                self._by_incarnation.setdefault(inc, set()).add(marker)
        for inc in affected:
            if inc not in self._by_incarnation and inc not in self._value_dirty_groups:
                self.dirty_incarnations.discard(inc)

    def _owner_changes(self, owner, prefix):
        """Capture only metadata; no owner or child payload loading."""
        try:
            checked = self.catalog.read_owner_identity(self.pin, owner)
        except StoreIntegrityError:
            # Match the catalog's checked exact-membership new-owner rule.
            # A present source/witness can never become an empty/new owner.
            with self.store.read_snapshot(self.pin):
                witness = self.store._visible_record_row(self.pin.captured_head,
                    OWNER_NAMESPACE, self.store.codec.encode(owner))
                if witness is not None or self.catalog._has_source(self.pin, owner):
                    raise
                if self.catalog.read_identity_membership(self.pin, owner, ()) is not None:
                    raise StoreIntegrityError('new owner has a persisted placement')
            checked = None
        changes = {}
        try:
            if checked is not None:
                for path, original in checked.occurrences:
                    if path[:len(prefix)] != prefix:
                        continue
                    marker = self._marker(owner, path)
                    previous = self.placement_overlay.get(marker)
                    old = original if previous is None else None if previous.delete else previous.incarnation_id
                    changes[marker] = path, original, old
            for marker in self._by_owner.get(owner, ()):
                previous = self.placement_overlay[marker]
                if marker not in changes and previous.occurrence_path[:len(prefix)] == prefix:
                    changes[marker] = (previous.occurrence_path, self._original[marker],
                                       None if previous.delete else previous.incarnation_id)
            return changes
        finally:
            if checked is not None and isinstance(checked.occurrences, CheckedSpool):
                checked.occurrences.close()

    def replace_owner(self, owner, placements):
        """Replace a family's complete compact identity projection.

        Placements are explicit (owner-relative path, mutable object) pairs.
        Adapters supply the projection; this coordinator never walks a header
        or expands a history to infer it. Header publication stays central.
        """
        with self._mutation():
            self._replace_scope(owner, (), placements)

    def replace_subtree(self, owner, prefix, placements):
        """Replace explicit paths under one prefix, retaining other placements."""
        with self._mutation():
            self._replace_scope(owner, prefix, placements)

    def _replace_scope(self, owner, prefix, placements):
        placement_path(*owner, prefix)
        incoming = {}
        for path, obj in placements:
            placement_path(*owner, path)
            marker = self._marker(owner, path)
            if marker in incoming or path[:len(prefix)] != prefix or obj is None:
                raise ValueError('duplicate, absent or out-of-scope identity placement')
            # Validate every incoming mutable/codec/lease before allocating or
            # changing any route. A failed caller iterator leaves no journal.
            weakref.ref(obj)
            if self.encode_placement is None:
                self.store.codec.encode(obj)
            else:
                self.encode_placement(owner, path, obj)
            incoming[marker] = path, obj
        changes = self._owner_changes(owner, prefix)
        for path, original, old in changes.values():
            for inc in {i for i in (original, old) if i is not None}:
                self.discover_group(inc)
        # Existing incoming identities also require their complete group before
        # any new identity is allocated or any path is installed.
        for path, obj in incoming.values():
            inc = self.registry.incarnation_for_object(obj)
            if inc is not None:
                self.discover_group(inc)
        chosen = {}
        for marker, (path, obj) in incoming.items():
            chosen[marker] = self.registry.bind(obj).value
            if marker not in changes:
                original = self.catalog.read_identity_membership(self.pin, owner, path)
                changes[marker] = path, original, original
        # Parents precede children, independent of caller projection ordering.
        for marker, (path, obj) in sorted(incoming.items(),
                key=lambda item: (len(item[1][0]), self.store.codec.encode(item[1][0]))):
            self.install_path(owner, path, obj)
        for marker, (path, original, old) in changes.items():
            self.registry.detach_occurrence(Occurrence(*owner, path))
            inc = chosen.get(marker)
            if inc is not None:
                self.registry.attach_occurrence(incoming[marker][1], Occurrence(*owner, path))
            self._record_placement_change(owner, path, original, old, inc)
        self._trim()
        self.dirty_owners.add(owner)
        self.mark_dirty(owner)

    def retire_owner(self, owner):
        """Retire all final placements without loading an owner or history.

        Complete inventory/group validation precedes route changes. Pending
        deletions are actual output state, outside clean cache bounds. The
        caller deletes its header in the same central transactional plan.
        """
        with self._mutation():
            self._replace_scope(owner, (), ())

    def _force_owner_headers(self, versions, ordinary, value_changed_incarnations):
        """The publisher names actual backing writes; guarded no-ops add no rows."""
        forced_versions, forced_ordinary = [], []
        with self._mutation():
            self._preparing_headers = True
            try:
                selected = set(value_changed_incarnations)
                if any(type(inc) is not int or inc not in self._value_dirty_groups for inc in selected):
                    raise StoreIntegrityError('changed backing lacks its routed identity group')
                owners = set()
                for inc in selected:
                    group = self.discover_group(inc)
                    owners.update((namespace, key) for namespace, key, _path in self._current_placements(group))
                provided = {(change.namespace, self.store.codec.encode(change.key))
                            for change in (*versions, *ordinary)}
                for owner in sorted(owners, key=self.store.codec.encode):
                    if (owner[0], self.store.codec.encode(owner[1])) in provided:
                        continue
                    if self.prepare_owner_header is None:
                        raise StoreIntegrityError('changed backing requires a physical owner header')
                    source = self.prepare_owner_header(owner)
                    if (type(source) not in (VersionChange, RecordChange) or source.delete
                            or source.namespace != owner[0]
                            or self.store.codec.encode(source.key) != self.store.codec.encode(owner[1])):
                        raise StoreIntegrityError('physical owner header provider returned a different source')
                    (forced_versions if type(source) is VersionChange else forced_ordinary).append(source)
            finally:
                self._preparing_headers = False
        return tuple(forced_versions), tuple(forced_ordinary)

    def prepare_delta(self, owner_versions, *, ordinary_changes=(), value_changed_incarnations=(),
                      retirement_row_budget=0, protected_incarnations=()):
        if self._mutation_depth:
            raise StoreConflictError('identity save preparation is blocked during mutation')
        self.preflight()
        if self._prepared is not None:
            return self._prepared.delta
        payloads = tuple(owner_versions)
        ordinary_payloads = tuple(ordinary_changes)
        forced_versions, forced_ordinary = self._force_owner_headers(payloads, ordinary_payloads,
                                                                    value_changed_incarnations)
        payloads += forced_versions
        ordinary_payloads += forced_ordinary
        if not payloads and not ordinary_payloads and not self.placement_overlay:
            self.dirty_owners.clear()
            self.dirty_incarnations.clear()
            self._value_dirty_groups.clear()
            self._trim()
            if self.registry.next_incarnation == self._baseline_allocator and not retirement_row_budget:
                delta = ParticipantDelta.freeze(self.store.codec, 'identity-coordinator')
                catalog_delta = ParticipantDelta.freeze(self.store.codec, 'identity-catalog')
                self._prepared = PreparedCoordinatorState(delta, catalog_delta, self.pin.captured_head,
                    self.registry.next_incarnation, ())
                return delta
        placements = tuple(self.placement_overlay.values())
        catalog_delta = self.catalog.prepare_delta(self.pin, payloads, placements,
                           next_incarnation_id=self.registry.next_incarnation,
                           ordinary_changes=ordinary_payloads,
                           retirement_row_budget=retirement_row_budget,
                           protected_incarnations=(*protected_incarnations, *self.dirty_incarnations))
        versions, ordinary, _ = catalog_delta.decode(self.store.codec)
        delta = ParticipantDelta.freeze(self.store.codec, 'identity-coordinator',
            version_changes=forced_versions + versions, ordinary_changes=forced_ordinary + ordinary,
            identity_changes=placements)
        self._prepared = PreparedCoordinatorState(delta, catalog_delta, self.pin.captured_head,
            self.registry.next_incarnation, tuple(sorted(self.placement_overlay)))
        return delta

    def validate_publication(self, delta, successor_pin):
        self.store._ensure_open()
        prepared = self._prepared
        if prepared is None or delta != prepared.delta:
            raise StoreConflictError('identity publication does not match the prepared plan')
        if (successor_pin.store_identity != self.store.store_identity
            or successor_pin.token != self.pin.token
            or successor_pin.captured_head != prepared.expected_generation + 1):
            raise StoreConflictError('identity publication has the wrong successor pin')
        self.catalog.validate_publication(prepared.catalog_delta, successor_pin)
        versions, ordinary, placements = delta.decode(self.store.codec)
        with self.store.read_snapshot(successor_pin):
            for source in versions:
                if source.namespace not in IDENTITY_OWNER_FAMILIES:
                    continue  # Catalog metadata has its own frozen validation.
                key = self.store.codec.encode(source.key)
                row = self.store._visible_record_row(successor_pin.captured_head, source.namespace, key)
                if source.delete:
                    if row is not None:
                        raise StoreIntegrityError('deleted physical owner header remains visible')
                    continue
                if row is None:
                    raise StoreIntegrityError('missing acknowledged physical owner header')
                order = self.store._visible_order(source.namespace, key, successor_pin.captured_head)
                self.store._validate_owner_projection(source.namespace, key, successor_pin.captured_head, row, order)
                _, schema, generation, _, members = self.store._check_record_row(source.namespace, key, row, decode=False)
                expected_members = {(m.index_name, self.store.codec.encode(m.value), m.ordinal) for m in source.memberships}
                actual_members = {(name, self.store.codec.encode(value), ordinal) for name, value, ordinal in members}
                if (schema != source.record_schema or generation != successor_pin.captured_head
                        or row[2] != self.store.codec.encode(source.value) or expected_members != actual_members):
                    raise StoreIntegrityError('physical owner header disagrees with the frozen source')
            for source in ordinary:
                value = self.store.read_record(source.namespace, source.key, expected_record_schema=source.record_schema)
                if self.store.codec.encode(value) != self.store.codec.encode(source.value):
                    raise StoreIntegrityError('ordinary owner header disagrees with the frozen source')
                index = self.store.db.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?',
                    ('index', ORDINARY_QUERY_OWNER_INDEX)).fetchone()
                expected_sql = 'CREATE INDEX ordinary_query_owner ON query_membership(namespace,record_key)'
                if index is None or ''.join(index[0].split()).lower() != ''.join(expected_sql.split()).lower():
                    raise StoreFormatError('ordinary owner header validation requires an explicit indexed copy upgrade')
                # LIMIT detects one surplus row without reading an unrelated or
                # corrupt unbounded projection. This index is created by new
                # stores/copy upgrades, never by ordinary open or acknowledgement.
                expected = {(m.index_name, self.store.codec.encode(m.value), m.ordinal,
                             successor_pin.captured_head) for m in source.memberships}
                rows = self.store.db.execute(
                    f'SELECT index_name,index_value,ordinal,generation FROM query_membership INDEXED BY {ORDINARY_QUERY_OWNER_INDEX} '
                    'WHERE namespace=? AND record_key=? LIMIT ?',
                    (source.namespace, self.store.codec.encode(source.key), len(expected) + 1)).fetchall()
                self.store._query_rows += len(rows)
                if len(rows) != len(expected) or set(rows) != expected:
                    raise StoreIntegrityError('ordinary owner header query projection disagrees with the frozen source')
            for change in placements:
                try:
                    actual = self.store.read_identity_occurrence(successor_pin,
                        change.owner_namespace, change.owner_key, change.occurrence_path)
                except KeyError:
                    if change.delete:
                        continue
                    raise StoreIntegrityError('missing acknowledged identity placement') from None
                if change.delete or actual.incarnation_id != change.incarnation_id:
                    raise StoreIntegrityError('acknowledged identity placement mismatch')

    def accept_delta(self, delta, successor_pin):
        self.store._ensure_open()
        if self._accepted == (delta.fingerprint, successor_pin):
            self.store._require_pin(successor_pin)
            return
        self.validate_publication(delta, successor_pin)
        prepared = self._prepared
        if tuple(sorted(self.placement_overlay)) != prepared.overlay_fingerprint:
            raise StoreConflictError('identity overlay changed after preparation')
        self.pin = successor_pin
        self._baseline_allocator = prepared.next_incarnation
        self.placement_overlay.clear()
        self._original.clear()
        self._by_owner.clear()
        self._by_incarnation.clear()
        self.dirty_owners.clear()
        self.dirty_incarnations.clear()
        self._value_dirty_groups.clear()
        self.discovered_groups.clear()  # bounded clean entries plus actual D/G
        self._weights.clear()
        self._cache_occurrences = self._cache_bytes = 0
        self._prepared = None
        self._accepted = delta.fingerprint, successor_pin

    def abort_delta(self, delta, commit_token):
        """Release only the freeze after checked failure; retain dirty routes."""
        self.store._ensure_open()
        if (self._mutation_depth or self._prepared is None or delta != self._prepared.delta
            or self.pin.captured_head != self._prepared.expected_generation):
            raise StoreConflictError('identity abort does not match its frozen plan')
        from .persistence_lazy_publication_guard import checked_uncommitted_publication
        with checked_uncommitted_publication(self.store, self.pin, commit_token):
            self._prepared = None

    def diagnostics(self):
        dirty_n = dirty_bytes = 0
        for key, (count, size) in self._weights.items():
            if key[1] in self.dirty_incarnations:
                dirty_n += count
                dirty_bytes += size
        spilled = [value for group in self.discovered_groups.values()
                   for value in (group.occurrences, group.links) if isinstance(value, CheckedSpool)]
        return {'spilled_group_bytes': sum(value.disk_bytes for value in spilled),
                'spill_sqlite_cache_limit_bytes': len(spilled) * 128 * 1024,
                'discovered_groups': len(self.discovered_groups),
                'discovered_occurrences': self._cache_occurrences,
                'identity_cache_python_bytes': self._cache_bytes,
                'clean_occurrences': self._cache_occurrences - dirty_n,
                'clean_python_bytes': self._cache_bytes - dirty_bytes,
                'dirty_group_occurrences': dirty_n, 'dirty_group_python_bytes': dirty_bytes,
                'dirty_owners': len(self.dirty_owners), 'dirty_groups': len(self.dirty_incarnations),
                'overlay_placements': len(self.placement_overlay), 'group_discoveries': self._discoveries}
