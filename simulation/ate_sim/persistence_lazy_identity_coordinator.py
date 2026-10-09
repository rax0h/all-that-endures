"""Affected-group overlays; LazyIdentityRegistry alone owns live identity.

Runtime family adapters supply loading/path installation and dirty callbacks.
These callbacks must bypass user mutation notifications when stitching checked
copies. This module never commits, inventories the live registry, or infers
logical deletion from clean-cache eviction.
"""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
import sys
from .incremental_store import StoreIntegrityError, StoreConflictError
from .persistence_lazy_identity import IncarnationId, Occurrence
from .persistence_lazy_identity_catalog import IdentityCatalog, CheckedIdentityGroup
from .persistence_lazy_store import IdentityOccurrenceChange
from .persistence_lazy_families import ParticipantDelta


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
    size = sys.getsizeof(value)
    if type(value) in (tuple, list):
        size += sum(_heap_size(v, seen) for v in value)
    return size


class IdentityCoordinator:
    def __init__(self, store, pin, registry, *, load_owner, resolve_path, install_path,
                 mark_dirty, preflight, occurrence_limit=4096, byte_limit=2 * 1024 * 1024):
        if registry.store_identity != store.store_identity:
            raise StoreConflictError('identity coordinator registry belongs to another store')
        if type(occurrence_limit) is not int or occurrence_limit < 1 or type(byte_limit) is not int or byte_limit < 1:
            raise ValueError('identity cache budgets must be positive exact integers')
        self.store, self.pin, self.registry = store, pin, registry
        self.catalog = IdentityCatalog(store)
        with store.read_snapshot(pin):
            self._baseline_allocator = self.catalog._descriptor(pin)[2]
        registry.allocator.next_value = max(registry.next_incarnation, self._baseline_allocator)
        self.load_owner, self.resolve_path, self.install_path = load_owner, resolve_path, install_path
        self.mark_dirty, self.preflight = mark_dirty, preflight
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
        out = {self._marker((ns, key), path): (ns, key, path) for ns, key, path in group.occurrences}
        for marker in self._by_incarnation.get(group.incarnation_id, ()):
            change = self.placement_overlay[marker]
            if change.delete or change.incarnation_id != group.incarnation_id:
                out.pop(marker, None)
            else:
                out[marker] = change.owner_namespace, change.owner_key, change.occurrence_path
        return tuple(out.values())

    def routes_for_mutation(self, obj):
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
        try:
            installations = []
            for namespace, key, path in placements:
                owner = namespace, key
                value = self.load_owner(owner)
                current = self.resolve_path(value, path)
                if current is not obj:
                    if self.store.codec.encode(current) != self.store.codec.encode(obj):
                        raise StoreIntegrityError('checked shared placement payload copies disagree')
                    installations.append((owner, path))
                if owner not in owners:
                    owners.append(owner)
            # Validate the entire requested closure before stitching any copy.
            for owner, path in installations:
                self.install_path(owner, path, obj)
            for namespace, key, path in placements:
                self.registry.attach_occurrence(obj, Occurrence(namespace, key, path))
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

    def replace_placement(self, owner, path, obj):
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
        affected = {i for i in (original, old, chosen) if i is not None}
        # Remove superseded routes immediately. Only the original persisted
        # group and final local group need placement overlay entries.
        for inc in affected:
            entries = self._by_incarnation.get(inc)
            if entries is not None:
                entries.discard(marker)
                if not entries:
                    self._by_incarnation.pop(inc, None)
        for inc in affected:
            self.dirty_incarnations.add(inc)
        if chosen == original:
            self.placement_overlay.pop(marker, None)
            self._original.pop(marker, None)
            self._by_owner.get(owner, set()).discard(marker)
        else:
            self.placement_overlay[marker] = IdentityOccurrenceChange(*owner, path, chosen, delete=chosen is None)
            self._by_owner.setdefault(owner, set()).add(marker)
            for inc in {i for i in (original, chosen) if i is not None}:
                self._by_incarnation.setdefault(inc, set()).add(marker)
        for inc in affected:
            if inc not in self._by_incarnation and inc not in self._value_dirty_groups:
                self.dirty_incarnations.discard(inc)
        self._trim()
        self.dirty_owners.add(owner)
        self.mark_dirty(owner)

    def prepare_delta(self, owner_versions):
        self.preflight()
        if self._prepared is not None:
            return self._prepared.delta
        payloads = tuple(owner_versions)
        if not payloads and not self.placement_overlay:
            self.dirty_owners.clear()
            self.dirty_incarnations.clear()
            self._value_dirty_groups.clear()
            self._trim()
            return ParticipantDelta.freeze(self.store.codec, 'identity-coordinator')
        placements = tuple(self.placement_overlay.values())
        catalog_delta = self.catalog.prepare_delta(self.pin, payloads, placements,
                           next_incarnation_id=self.registry.next_incarnation)
        versions, ordinary, _ = catalog_delta.decode(self.store.codec)
        delta = ParticipantDelta.freeze(self.store.codec, 'identity-coordinator',
            version_changes=versions, ordinary_changes=ordinary, identity_changes=placements)
        self._prepared = PreparedCoordinatorState(delta, catalog_delta, self.pin.captured_head,
            self.registry.next_incarnation, tuple(sorted(self.placement_overlay)))
        return delta

    def validate_publication(self, delta, successor_pin):
        prepared = self._prepared
        if prepared is None or delta != prepared.delta:
            raise StoreConflictError('identity publication does not match the prepared plan')
        if successor_pin.store_identity != self.store.store_identity or successor_pin.captured_head != prepared.expected_generation + 1:
            raise StoreConflictError('identity publication has the wrong successor pin')
        self.catalog.validate_publication(prepared.catalog_delta, successor_pin)
        _, _, placements = delta.decode(self.store.codec)
        with self.store.read_snapshot(successor_pin):
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
        if self._accepted == (delta.fingerprint, successor_pin):
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

    def diagnostics(self):
        dirty_n = dirty_bytes = 0
        for key, (count, size) in self._weights.items():
            if key[1] in self.dirty_incarnations:
                dirty_n += count
                dirty_bytes += size
        return {'discovered_groups': len(self.discovered_groups),
                'discovered_occurrences': self._cache_occurrences,
                'identity_cache_python_bytes': self._cache_bytes,
                'clean_occurrences': self._cache_occurrences - dirty_n,
                'clean_python_bytes': self._cache_bytes - dirty_bytes,
                'dirty_group_occurrences': dirty_n, 'dirty_group_python_bytes': dirty_bytes,
                'dirty_owners': len(self.dirty_owners), 'dirty_groups': len(self.dirty_incarnations),
                'overlay_placements': len(self.placement_overlay), 'group_discoveries': self._discoveries}
