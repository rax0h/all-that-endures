"""Recursive values borrow the existing registry, physical catalog and publisher.

Only explicitly activated checked sessions select this runtime. Backing pages
contain compact references, never live child payload copies or a second DAG.
"""
from dataclasses import dataclass
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
            session._register_nested_overlay(proxy)
            self.bind(proxy)
            return proxy.storage_reference()
        finally:
            self._admitting.remove(id(value))

    def bind(self, proxy):
        session = self.session()
        proxy._recursive = True
        proxy._recursive_runtime = self
        def guard():
            session._shared_object_routes(proxy)
        def changed():
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

    def decode(self, value, owner, path):
        if reference(value):
            session = self.session()
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
            for number, page in tuple(proxy._dirty_pages.items()):
                key = proxy._incarnation, number
                deleted = number * PAGE_SIZE >= proxy._length
                if not deleted or number * PAGE_SIZE < proxy._base_length:
                    if not deleted and proxy._store.codec.encode(tuple(page)) == proxy._baseline_page_bytes.get(number):
                        continue
                    yield VersionChange(PAGE_NAMESPACE, key, None if deleted else tuple(page), delete=deleted)
        elif type(proxy) is LazyHistoryMap:
            for key, entry in tuple(proxy._dirty_entries.items()):
                yield VersionChange(ENTRY_NAMESPACE, (proxy._incarnation, key), entry, delete=entry is None,
                    memberships=() if entry is None else (Membership('incarnation', proxy._incarnation, entry[0]),))
        elif type(proxy) is LazyOrderedSequence:
            for (namespace, key), value in tuple(proxy._dirty.items()):
                if namespace == NODE_NAMESPACE and (value is None or value[0] == 'leaf'):
                    yield VersionChange(namespace, key, value, delete=value is None)

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
            for proxy in tuple(session._nested_dirty.values()):
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
                    if not refs and present is None and source_present is not None and owner not in coord.dirty_owners:
                        continue
                    before = coord._owner_changes(owner, ())
                    current = {path: inc for path, _, inc in before.values() if inc is not None}
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
        source = next((v for v in self._changes(proxy) if (v.namespace, v.key) == owner), None) if proxy is not None else None
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
