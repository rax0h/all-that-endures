"""World wiring for the checked catalog; no bootstrap or format migration here."""
import weakref

from .incremental_store import StoreIntegrityError
from .persistence_lazy_identity_coordinator import IdentityCoordinator
from .persistence_lazy_families import FAMILIES
from .persistence_lazy_identity import IncarnationId, Occurrence
from .persistence_lazy_nested_history import HISTORY_TYPES
from .persistence_adapters import AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY, PACKED_LIST_KIND


class OwnerKeyJournal(set):
    """Existing dirty keys notify their actual owner; no second value journal."""
    def __init__(self,table,values=()):
        super().__init__(values)
        self._table_ref=weakref.ref(table)

    def add(self,key):
        super().add(key)
        self._notify(key)

    def _notify(self,key):
        table=self._table_ref()
        bridge=getattr(table._session,'_identity_bridge',None) if table is not None else None
        if bridge is not None:bridge.note_owner((table._namespace,key))

    def discard(self,key):
        if key in self:
            super().discard(key);self._notify(key)

    def remove(self,key):
        super().remove(key);self._notify(key)

    def update(self,*others):
        for other in others:
            for key in other:self.add(key)

    def __ior__(self,other):
        self.update(other);return self


class EagerOwnerJournal(set):
    def __init__(self,bridge,values=()):
        super().__init__(values);self._bridge_ref=weakref.ref(bridge)

    def add(self,owner):
        super().add(owner)
        bridge=self._bridge_ref()
        if bridge is not None:bridge.note_owner(owner)

    def update(self,*others):
        for other in others:
            for owner in other:self.add(owner)

    def __ior__(self,other):
        self.update(other);return self


class WorldIdentityBridge:
    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        self._pending_owners=set()
        self._synchronizing=False
        bindings = session._family_bindings
        self.coordinator = IdentityCoordinator(session.store, session.pin, session._registry,
            load_owner=bindings.load_owner, resolve_path=bindings.resolve_path,
            install_path=bindings.install_path, mark_dirty=self._mark_dirty,
            preflight=session._ensure_people_mutation_allowed,
            encode_placement=bindings.encode_placement,
            prepare_owner_header=bindings.unchanged_owner_header)

    def note_owner(self,owner):
        self._pending_owners.add(owner)

    def _mark_dirty(self, owner):
        session = self._session_ref()
        table = session._family_bindings.tables.get(owner[0])
        # A removed owner already has an explicit family deletion journal.
        # Routing retirement must not ask changed() to resurrect that header.
        if table is not None and not table._visible(owner[1]):
            if owner[1] not in table._removed and table._baseline_exists(owner[1]):
                raise StoreIntegrityError('retired owner has no family deletion journal')
            return
        if table is None and owner in session._eager_tracker._deleted:
            return
        session._family_bindings.mark_dirty(owner)

    def synchronize_lazy_placements(self):
        """Reconcile only family-touched compact owners, never the live registry.

        The existing family binders supply complete current owner projections.
        A removed cold owner needs only its checked catalog metadata. This runs
        before shared routing, so pending replacement wins over pinned placement.
        """
        session = self._session_ref()
        if self._synchronizing:return
        self._synchronizing=True
        try:self._synchronize_pending(session)
        finally:self._synchronizing=False

    def _synchronize_pending(self,session):
        session._recursive_histories.synchronize()
        tracker = session._eager_tracker
        pending=tuple(self._pending_owners)
        self._pending_owners.difference_update(pending)
        try:
            if ('world.event_ids',0) in pending:self.synchronize_event_id_placements()
            if any(owner[0]==AGENCY_ACTIONS_NAMESPACE for owner in pending):self.synchronize_packed_actions()
            for owner in pending:
                table=session._family_bindings.tables.get(owner[0])
                if table is not None:
                    self._synchronize_owner(owner,table._visible(owner[1]))
                else:
                    adapter=FAMILIES.get(owner[0])
                    if adapter is not None and adapter.collection_kind in ('dict','events'):
                        value=None if owner in tracker._deleted else tracker._owner_value(owner,include_sealed_snapshot=True)
                        self._synchronize_owner(owner,value is not None)
        except BaseException:
            self._pending_owners.update(pending)
            raise

    def synchronize_event_id_placements(self):
        """Project the facade and its two fixed descriptor backing slots.

        The physical authority is still owner zero. Internal history references
        use this owner's checked projection, not a second ownership relation.
        """
        from .persistence_event_id_exceptions import PagedEventIdExceptions
        session = self._session_ref()
        coord, registry = self.coordinator, session._registry
        owner = ('world.event_ids', 0)
        facade = session.world.event_ids
        if facade.descriptor() is None:
            raise StoreIntegrityError('checked event-ID owner requires a compact descriptor')
        changes = coord._owner_changes(owner, ())
        before = {path: old for path, _, old in changes.values() if old is not None}
        if () not in before:
            raise StoreIntegrityError('checked event-ID owner lacks its facade incarnation')
        incarnation = IncarnationId(session.store.store_identity, before[()])
        coord.discover_group(incarnation)
        actual = registry.incarnation_for_object(facade)
        if actual is None:
            registry.bind(facade, incarnation=incarnation)
        elif actual != incarnation:
            raise StoreIntegrityError('event-ID facade disagrees with checked root identity')
        placements = [((), facade)]
        if isinstance(facade._exact, PagedEventIdExceptions):
            for name, proxy in zip(('removed', 'added'), facade._exact.histories):
                session._register_nested_overlay(proxy)
                placements.append(((('field', '_exact'), ('field', name)), proxy))
        current = {path: registry.incarnation_for_object(child).value for path, child in placements}
        if before != current:
            coord.replace_owner(owner, placements)

    def synchronize_packed_actions(self, subject=None):
        """Project the accepted packed current action body, not old histories.

        Logical action positions belong to one real packed physical source.
        Original object witnesses, not current ranks, preserve identity on trims.
        A direct mutation chooses its subject as the canonical shared copy before
        any field changes, then the checked coordinator stitches its peers.
        """
        session = self._session_ref()
        tracker, registry, coord = session._eager_tracker, session._registry, self.coordinator
        owner = (AGENCY_ACTIONS_NAMESPACE, PACKED_LIST_KEY)
        if tracker._manifest['collections'][owner[0]][0] != PACKED_LIST_KIND:
            raise StoreIntegrityError('checked action placements require an explicit packed copy upgrade')
        changes = coord._owner_changes(owner, ())
        before = {path: old for path, _, old in changes.values() if old is not None}
        originals = {}
        for key in {path[0][1] for path in before if path and path[0][0] == 'index'}:
            occurrences = tracker._identity_index.owner_occurrences.get((owner[0], key), ())
            prefix = tracker._owner_path((owner[0], key))
            for ident, obj, path in occurrences:
                relative = (('index', key),) + path[len(prefix):]
                if relative in before:
                    originals[ident] = (obj, before[relative])
        value = session.world.agency.actions
        rows = []
        tracker._identity_index._scan(value, (), rows)
        rows = [(ident, obj, path) for ident, obj, path in rows if path]
        if subject is not None and any(obj is subject for _ident, obj, _path in rows):
            original = originals.get(id(subject))
            if registry.incarnation_for_object(subject) is None and original is not None and original[0] is subject:
                coord.discover_group(original[1])
                registry.bind(subject, incarnation=IncarnationId(session.store.store_identity, original[1]))
        placements = []
        for _ident, _obj, path in rows:
            child = session._family_bindings.resolve_path(value, path)
            inc = registry.incarnation_for_object(child)
            original = originals.get(id(child))
            if inc is None and original is not None and original[0] is child:
                inc = IncarnationId(session.store.store_identity, original[1])
                coord.discover_group(inc)
                canonical = registry.object_for_incarnation(inc)
                if canonical is None:
                    registry.bind(child, incarnation=inc)
                else:
                    adapter = FAMILIES[owner[0]]
                    if adapter.identity_payload_bytes(session.store, session.pin, child) != adapter.identity_payload_bytes(
                            session.store, session.pin, canonical):
                        raise StoreIntegrityError('checked action payload copies disagree')
                    session._family_bindings.install_path(owner, path, canonical)
                    child = canonical
            if registry.incarnation_for_object(child) is None:
                registry.bind(child)
            placements.append((path, child))
        current = {path: registry.incarnation_for_object(child).value for path, child in placements}
        if before != current:
            coord.replace_owner(owner, placements)

    def stitch_eager_action_peers(self):
        """Canonicalize resident current copies before exposing an eager body.

        Groups come from the same checked coordinator. Cold lazy owner payloads
        stay unloaded; their normal checked binders select this canonical object
        later. This current-root initialization does not grant mutation dirt.
        """
        session = self._session_ref()
        registry, coord = session._registry, self.coordinator
        seen = set()
        for action in session.world.agency.actions:
            inc = registry.incarnation_for_object(action)
            if inc is None or inc.value in seen:
                continue
            seen.add(inc.value)
            placements = coord._current_placements(coord.discover_group(inc))
            try:
                for namespace, key, path in placements:
                    if namespace in session._family_bindings.tables:
                        continue
                    owner = (namespace, key)
                    value = session._family_bindings.load_owner(owner)
                    current = session._family_bindings.resolve_path(value, path)
                    if current is not action:
                        adapter = FAMILIES[namespace]
                        if adapter.identity_payload_bytes(session.store, session.pin, current, path) != adapter.identity_payload_bytes(
                                session.store, session.pin, action, path):
                            raise StoreIntegrityError('checked action payload copies disagree')
                        session._family_bindings.install_path(owner, path, action)
                    registry.attach_occurrence(action, Occurrence(namespace, key, path))
            finally:
                if hasattr(placements, 'close'):
                    placements.close()

    def _synchronize_owner(self, owner, exists):
        session = self._session_ref()
        coord, registry = self.coordinator, session._registry
        changes = coord._owner_changes(owner, ())
        before = {path: old for path, _, old in changes.values() if old is not None}
        placements = []
        if exists:
            value = session._family_bindings.load_owner(owner)
            if owner[0] not in session._family_bindings.tables:
                # The accepted eager tracker retains original object witnesses.
                # Inspect only this touched compact owner; checked histories are
                # identity leaves, never archive walks or a second catalog.
                tracker = session._eager_tracker
                absolute = tracker._owner_path(owner)
                originals = {path[len(absolute):]: obj for _ident, obj, path
                    in tracker._identity_index.owner_occurrences.get(owner, ())}
                rows = []
                from .persistence_identity import is_sealed_snapshot_owner
                if owner[0] == "world.events" and is_sealed_snapshot_owner(value):
                    rows.append((id(value.data), value.data, (("field", "data"),)))
                else:
                    tracker._identity_index._scan(value, (), rows)
                for _ident, child, path in rows:
                    inc = registry.incarnation_for_object(child)
                    if inc is None and path in before and originals.get(path) is child:
                        inc = registry.bind(child, incarnation=IncarnationId(
                            session.store.store_identity, before[path]))
                    if inc is None:
                        inc = registry.bind(child)
                    if type(child) in HISTORY_TYPES:
                        session._register_nested_overlay(child)
                    placements.append((path, child))
            else:
                for occurrence in registry.occurrences_for_owner(*owner):
                    try:
                        child = session._family_bindings.resolve_path(value, occurrence.path)
                    except (KeyError, IndexError, TypeError, AttributeError):
                        continue
                    inc = registry.incarnation_for_object(child)
                    if inc is not None:
                        placements.append((occurrence.path, child))
        current = {path: registry.incarnation_for_object(child).value for path, child in placements}
        if before != current:
            coord.replace_owner(owner, placements)

            session._recursive_histories.release_unowned_memos(set(before.values()) - set(current.values()))

    def finish_acknowledgement(self, delta):
        """Clear dirt for suppressed headers forced by this exact frozen delta."""
        session = self._session_ref()
        versions, _, _ = delta.decode(session.store.codec)
        for change in versions:
            table = session._family_bindings.tables.get(change.namespace)
            if table is None or change.delete:
                continue
            # The central family accepts supplied headers itself. Forced copies
            # have no family touched-key entry, but their complete bytes were
            # checked before capture and again before acknowledgement.
            table._dirty.discard(change.key)
            table._discard_clean_baseline(change.key)
            if dict.__contains__(table, change.key):
                table._lru[change.key] = None
            table._evict_clean()
