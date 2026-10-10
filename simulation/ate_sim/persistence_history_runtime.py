"""Recursive values borrow the existing registry, physical catalog and publisher.

Only explicitly activated checked sessions select this runtime. Backing pages
contain compact references, never live child payload copies or a second DAG.
"""
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager
import sys
import weakref

from .incremental_store import StoreIntegrityError, StoreError, Membership
from .persistence_lazy_store import VersionChange
from .persistence_lazy_identity import IncarnationId, Occurrence
from .persistence_lazy_nested_history import (
    HISTORY_TYPES, HISTORY_CLASSES, reference, immutable_value,
    LazyHistoryList, LazyHistoryMap, PAGE_NAMESPACE, ENTRY_NAMESPACE, PAGE_SIZE,
)
from .persistence_history_owner_adapters import AUXILIARY_OWNER_FAMILIES
from .persistence_lazy_identity_catalog import OWNER_NAMESPACE
from .persistence_lazy_sequence import LazyOrderedSequence, NODE_NAMESPACE


@dataclass(frozen=True)
class PhysicalHistoryOwner:
    runtime: object
    owner: tuple
    value: tuple


class RecursiveHistoryRuntime:
    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        self._admitting = set()
        self._synchronizing = False
        self._source_leases = {}
        self._new_sources = []
        self._source_queue = deque()
        self._source_release_checks = 0

    def remember_source(self, source, proxy):
        """Track only input D/U; the existing memo owns each actual source."""
        marker = id(source), proxy._incarnation
        if self._source_leases.get(marker[0]) != marker[1]:
            self._source_leases[marker[0]] = marker[1]
            self._new_sources.append(marker)

    def _release_source(self, marker):
        source_id, incarnation = marker
        if self._source_leases.get(source_id) != incarnation:
            return True
        tracker = self.session()._eager_tracker
        pair = tracker._memo.get(source_id)
        self._source_release_checks += 1
        if (pair is None or type(pair[1]) not in HISTORY_TYPES
                or pair[1]._incarnation != incarnation):
            self._source_leases.pop(source_id, None)
            return True
        # CPython: the memo tuple and this temporary getrefcount argument are
        # the only two references when no caller/container holds the source.
        # Keeping the actual source until this check prevents address reuse
        # from ever identifying another object as the original alias.
        if sys.getrefcount(pair[0]) != 2:
            return False
        if tracker._memo_reverse.get(id(pair[1])) == source_id:
            tracker._memo_reverse.pop(id(pair[1]), None)
        tracker._memo.pop(source_id)
        self._source_leases.pop(source_id)
        return True

    def accept_source_memos(self):
        # Parents were admitted last. Release them before their descendants;
        # this pass costs actual new input D, never a clean archive inventory.
        for marker in reversed(self._new_sources):
            if not self._release_source(marker):
                self._source_queue.append(marker)
        self._new_sources.clear()

    def collect_source_memos(self, budget=256):
        for _ in range(min(budget, len(self._source_queue))):
            marker = self._source_queue.popleft()
            if not self._release_source(marker):
                self._source_queue.append(marker)

    def source_diagnostics(self):
        return {'source_memo_leases': len(self._source_leases),
                'new_source_memos': len(self._new_sources),
                'source_release_queue': len(self._source_queue),
                'source_release_checks': self._source_release_checks}

    def session(self):
        session = self._session_ref()
        if session is None:
            raise StoreError('recursive history session is closed')
        session._ensure_active()
        if session._state == 'recovery-required':
            raise StoreError('nested history read requires save acknowledgement')
        return session

    def initial_values(self, kind, value):
        self.validate_native(value)
        if kind == 'map':
            return {key: self.admit(child) for key, child in value.items()}
        if kind in ('list', 'sequence'):
            return [self.admit(child) for child in value]
        return value

    def validate_native(self, value, active=None):
        """Validate actual incoming D before allocating children or changing owners."""
        session = self.session()
        active = set() if active is None else active
        if type(value) in HISTORY_TYPES:
            if value._store is not session.store or value._pin != session.pin:
                raise StoreError('cross-session recursive history')
            value._ensure()
            return
        if reference(value) or immutable_value(value):
            session.store.codec.encode(value)
            return
        if type(value) not in (list, dict, tuple, set):
            raise TypeError('recursive history value is outside the typed container schema')
        if id(value) in active:
            raise TypeError('cyclic history value is outside the typed container schema')
        active.add(id(value))
        try:
            if type(value) is dict:
                from .persistence_lazy_nested_history import equality_key
                for key, child in value.items():
                    session.store.codec.encode(equality_key(key))
                    self.validate_native(child, active)
            elif type(value) is set:
                from .persistence_lazy_nested_history import equality_key
                for key in value:
                    session.store.codec.encode(equality_key(key))
            else:
                for child in value:
                    self.validate_native(child, active)
        finally:
            active.remove(id(value))

    def admit(self, value):
        session = self.session()
        session._ensure_people_mutation_allowed()
        self.validate_native(value)
        if type(value) in HISTORY_TYPES:
            session._register_nested_overlay(value)
            self.bind(value)
            return value.storage_reference()
        if reference(value) or immutable_value(value):
            return value
        if type(value) is tuple:
            return tuple(self.admit(child) for child in value)
        if type(value) not in (list, dict, set):
            raise TypeError('recursive history value is outside the typed container schema')
        tracker = session._eager_tracker
        memo = tracker._memo.get(id(value))
        if memo is not None and memo[0] is value and type(memo[1]) in HISTORY_TYPES:
            proxy = memo[1]
            session._register_nested_overlay(proxy)
            return proxy.storage_reference()
        if id(value) in self._admitting:
            raise TypeError('cyclic history value is outside the typed container schema')
        self._admitting.add(id(value))
        try:
            kind = {list: 'list', dict: 'map', set: 'set'}[type(value)]
            values = self.initial_values(kind, value)
            incarnation = session._registry.allocator.allocate()
            proxy = HISTORY_CLASSES[kind](session.store, session.pin, incarnation.value,
                initial_values=values, cache_budget=session._history_cache_budget, recursive=True)
            session._registry.bind(proxy, incarnation=incarnation)
            tracker._remember_memo(value, proxy)
            self.remember_source(value, proxy)
            session._register_nested_overlay(proxy)
            self.bind(proxy)
            return proxy.storage_reference()
        finally:
            self._admitting.remove(id(value))

    def bind(self, proxy):
        session = self.session()
        proxy._recursive = True
        proxy._recursive_runtime = self
        self.retain_pending_children(proxy)
        def guard():
            session._shared_object_routes(proxy)
        def changed():
            self.retain_pending_children(proxy)
            session._shared_object_routes(proxy)
            incarnation = session._registry.incarnation_for_object(proxy)
            coord = session._identity_coordinator
            placements = coord._current_placements(coord.discover_group(incarnation))
            try:
                if placements:
                    session._nested_dirty[incarnation.value] = proxy
            finally:
                if hasattr(placements, 'close'):
                    placements.close()
        def read_guard():
            session._ensure_active()
            if session._state == 'recovery-required':
                raise StoreError('nested history read requires save acknowledgement')
        proxy.bind(guard, changed, read_guard)

    def retain_pending_children(self, proxy):
        """Private unpublished D keeps canonical descendants alive through U.

        These references are not placements or a second identity authority.
        Publication clears them; only unpublished dirty payload is traversed.
        """
        if not proxy._new:
            return
        session = self.session()
        children = {}
        for source in self._changes(proxy):
            if source.delete:
                continue
            for _path, inc in AUXILIARY_OWNER_FAMILIES[source.namespace].reference_placements(source.value):
                child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                if child is None:
                    raise StoreIntegrityError('unpublished child lost its canonical object')
                children[inc] = child
        proxy._recursive_pending_children = children

    def decode(self, value, owner, path):
        if reference(value):
            session = self.session()
            parent = session._registry.object_for_incarnation(
                IncarnationId(session.store.store_identity, owner[1][0]))
            if parent is not None and parent._new:
                source = self._source_change(parent, owner)
                child = getattr(parent, '_recursive_pending_children', {}).get(value.incarnation)
                if source is not None and not source.delete and child is not None:
                    current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(source.value, path)
                    if current != value or child._kind != value.kind:
                        raise StoreIntegrityError('private recursive reference disagrees with its pending value')
                    return child
            if owner[0] == NODE_NAMESPACE:
                if (type(parent) is LazyOrderedSequence and parent._mutation_depth
                        and owner[1][1] in parent._recursive_preflight_leaves
                        and owner in parent._dirty):
                    # Caller iteration can read its native partial prefix.
                    # These leaves passed source/incoming preflight, but their
                    # physical routes cannot escape a rollback scope yet.
                    current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(parent._dirty[owner], path)
                    child = session._registry.object_for_incarnation(
                        IncarnationId(session.store.store_identity, value.incarnation))
                    if child is None:
                        child = HISTORY_CLASSES[value.kind](session.store, session.pin, value.incarnation,
                            cache_budget=session._history_cache_budget, recursive=True)
                        session._registry.bind(child, incarnation=IncarnationId(session.store.store_identity, value.incarnation))
                        session._register_nested_overlay(child)
                        self.bind(child)
                    if current != value or child._kind != value.kind:
                        raise StoreIntegrityError('pending recursive reference lacks its canonical child')
                    return child
            if session._lifecycle_operation is None:
                self.synchronize()
            coord = session._identity_coordinator
            rows = coord._owner_changes(owner, ())
            marker = coord._marker(owner, path)
            if marker not in rows or rows[marker][2] != value.incarnation:
                raise StoreIntegrityError('recursive reference lacks its checked physical placement')
            return session._bind_history_list(value, Occurrence(*owner, path),
                IncarnationId(session.store.store_identity, value.incarnation), kind=value.kind)
        if type(value) is tuple:
            return tuple(self.decode(child, owner, path + (('index', slot),)) for slot, child in enumerate(value))
        return value

    def validate_physical_children(self, owner, value):
        """A touched bounded page checks all existing child groups before edits."""
        refs = AUXILIARY_OWNER_FAMILIES[owner[0]].reference_placements(value)
        if not refs:
            return
        # Counted operations synchronize their prior D in the entry guard.
        # Their in-progress leaves must not publish placement overlays before
        # the sequence's rollback scope has accepted the complete journal.
        if owner[0] != NODE_NAMESPACE:
            self.synchronize()
        session = self.session()
        coord = session._identity_coordinator
        rows = coord._owner_changes(owner, ())
        for path, inc in refs:
            marker = coord._marker(owner, path)
            if marker not in rows or rows[marker][2] != inc:
                raise StoreIntegrityError('recursive reference lacks its checked physical placement')
            coord.discover_group(inc)

    def _changes(self, proxy):
        if type(proxy) is LazyHistoryList:
            owners = ((PAGE_NAMESPACE, (proxy._incarnation, number)) for number in tuple(proxy._dirty_pages))
        elif type(proxy) is LazyHistoryMap:
            owners = ((ENTRY_NAMESPACE, (proxy._incarnation, key)) for key in tuple(proxy._dirty_entries))
        elif type(proxy) is LazyOrderedSequence:
            owners = (owner for owner in tuple(proxy._dirty) if owner[0] == NODE_NAMESPACE)
        else:
            return
        for owner in owners:
            source = self._source_change(proxy, owner)
            if source is not None:
                yield source

    def _source_change(self, proxy, owner):
        """Resolve a requested pending physical key without visiting other D."""
        namespace, key = owner
        if key[0] != proxy._incarnation:
            raise StoreIntegrityError('physical history owner belongs to another backing')
        if type(proxy) is LazyHistoryList and namespace == PAGE_NAMESPACE:
            number = key[1]
            if number not in proxy._dirty_pages:
                return None
            deleted = number * PAGE_SIZE >= proxy._length
            value = None if deleted else tuple(proxy._dirty_pages[number])
            return VersionChange(namespace, key, value, delete=deleted)
        if type(proxy) is LazyHistoryMap and namespace == ENTRY_NAMESPACE and key[1] in proxy._dirty_entries:
            entry = proxy._dirty_entries[key[1]]
            return VersionChange(namespace, key, entry, delete=entry is None,
                memberships=() if entry is None else (Membership('incarnation', proxy._incarnation, entry[0]),))
        if type(proxy) is LazyOrderedSequence and namespace == NODE_NAMESPACE and owner in proxy._dirty:
            value = proxy._dirty[owner]
            if value is None or value[0] == 'leaf':
                return VersionChange(namespace, key, value, delete=value is None)
        return None

    @contextmanager
    def prepared_routes(self):
        """The caller synchronized D; routing cannot change backing values."""
        if self._synchronizing:
            raise StoreError('recursive save routing is reentrant')
        self._synchronizing = True
        try:
            yield
        finally:
            self._synchronizing = False

    def retire_unpublished_pages(self, proxy):
        session = self.session()
        coord = session._identity_coordinator
        if not proxy._new:
            raise StoreIntegrityError('recursive promotion has a published append source')
        for number in tuple(proxy._dirty_pages):
            owner = PAGE_NAMESPACE, (proxy._incarnation, number)
            if owner in coord.dirty_owners or owner in coord._by_owner:
                coord.retire_owner(owner)
                # This physical source never published and is removed from D.
                # Its cancelled routes need no witness/header/tombstone.
                coord.dirty_owners.discard(owner)

    def release_unowned_memos(self, incarnations):
        session = self.session()
        coord = session._identity_coordinator
        for inc in set(incarnations):
            obj = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
            if obj is None:
                continue
            current = coord._current_placements(coord.discover_group(inc))
            try:
                if not current:
                    session._eager_tracker._drop_memo_if_unowned(obj)
            finally:
                if hasattr(current, 'close'):
                    current.close()

    def synchronize(self):
        if self._synchronizing:
            return
        session = self.session()
        # Synchronization only reflects already guarded values in D. Pinned
        # reads remain available in a stale session; public edits still guard.
        coord = session._identity_coordinator
        self._synchronizing = True
        try:
            pending = deque(session._nested_dirty.values())
            processed = set()
            while pending:
                proxy = pending.popleft()
                if proxy._incarnation in processed:
                    continue
                if proxy._new:
                    placements = session._registry.occurrences_for_incarnation(
                        IncarnationId(session.store.store_identity, proxy._incarnation))
                    if not any(o.owner_namespace not in AUXILIARY_OWNER_FAMILIES
                               or o.owner_key[0] in processed
                               or o.owner_key[0] not in session._nested_dirty for o in placements):
                        continue  # Unattached input D belongs only to private aliases.
                processed.add(proxy._incarnation)
                for source in self._changes(proxy):
                    owner = source.namespace, source.key
                    adapter = AUXILIARY_OWNER_FAMILIES[source.namespace]
                    refs = () if source.delete else adapter.reference_placements(source.value)
                    # Earlier scalar-only pages have no physical catalog owner.
                    # Do not manufacture their missing witness on ordinary use.
                    present = session.store._visible_record_row(session.pin.captured_head,
                        OWNER_NAMESPACE, session.store.codec.encode(owner))
                    source_present = session.store._visible_record_row(session.pin.captured_head,
                        source.namespace, session.store.codec.encode(source.key))
                    if source.delete and source_present is None:
                        # A read may have checked an addition which was then
                        # cancelled. Retire only this dirty physical owner;
                        # never publish a witness for its absent source.
                        before = coord._owner_changes(owner, ())
                        removed = {inc for _path, _original, inc in before.values() if inc is not None}
                        if removed:
                            coord.retire_owner(owner)
                            self.release_unowned_memos(removed)
                        coord.dirty_owners.discard(owner)
                        continue
                    if not refs and present is None and source_present is not None and owner not in coord.dirty_owners:
                        continue
                    before = coord._owner_changes(owner, ())
                    current = {path: inc for path, _, inc in before.values() if inc is not None}
                    for _path, inc in refs:
                        child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                        if child is not None and child._new and inc not in processed:
                            session._register_nested_overlay(child)
                            pending.append(child)
                    if current == dict(refs):
                        # New scalar-only pages also need an empty completeness
                        # witness, before a later edit introduces references.
                        if present is not None or source_present is None:
                            coord.dirty_owners.add(owner)
                        continue
                    placements = []
                    for path, inc in refs:
                        child = session._registry.object_for_incarnation(IncarnationId(session.store.store_identity, inc))
                        if child is None:
                            ref = adapter.resolve_path(source.value, path)
                            child = HISTORY_CLASSES[ref.kind](session.store, session.pin, inc,
                                cache_budget=session._history_cache_budget, recursive=True)
                            session._registry.bind(child, incarnation=IncarnationId(session.store.store_identity, inc))
                            session._register_nested_overlay(child)
                            self.bind(child)
                        placements.append((path, child))
                    coord.replace_owner(owner, placements)
                    self.release_unowned_memos(set(current.values()) - {inc for _path, inc in refs})
        finally:
            self._synchronizing = False

    def load_owner(self, owner):
        session = self.session()
        proxy = session._nested_dirty.get(owner[1][0])
        source = self._source_change(proxy, owner) if proxy is not None else None
        if source is not None:
            if source.delete:
                raise StoreIntegrityError('recursive owner has a pending deletion')
            value = source.value
        else:
            value = session.store.read_version(session.pin, *owner, expected_record_schema=1).value
        return PhysicalHistoryOwner(self, owner, value)

    def resolve_path(self, physical, path):
        adapter = AUXILIARY_OWNER_FAMILIES[physical.owner[0]]
        value = adapter.resolve_path(physical.value, path)
        return self.decode(value, physical.owner, path)

    def install_path(self, owner, path, obj):
        session = self.session()
        physical = self.load_owner(owner)
        current = AUXILIARY_OWNER_FAMILIES[owner[0]].resolve_path(physical.value, path)
        incarnation = session._registry.incarnation_for_object(obj)
        if (not reference(current) or incarnation is None or current.incarnation != incarnation.value
                or current.kind != obj._kind or session._registry.object_for_incarnation(incarnation) is not obj):
            raise StoreIntegrityError('recursive reference resolves to a different canonical object')

    def unchanged_header(self, owner):
        session = self.session()
        value = self.load_owner(owner).value
        adapter = AUXILIARY_OWNER_FAMILIES[owner[0]]
        members = (Membership('incarnation', owner[1][0], value[0]),) if adapter.owner_kind == 'entry' else ()
        return VersionChange(*owner, value, memberships=members)
