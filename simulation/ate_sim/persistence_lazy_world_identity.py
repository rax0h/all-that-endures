"""World wiring for the checked catalog; no bootstrap or format migration here."""
import weakref

from .incremental_store import StoreIntegrityError
from .persistence_lazy_identity_coordinator import IdentityCoordinator


class WorldIdentityBridge:
    def __init__(self, session):
        self._session_ref = weakref.ref(session)
        bindings = session._family_bindings
        self.coordinator = IdentityCoordinator(session.store, session.pin, session._registry,
            load_owner=bindings.load_owner, resolve_path=bindings.resolve_path,
            install_path=bindings.install_path, mark_dirty=self._mark_dirty,
            preflight=session._ensure_people_mutation_allowed,
            encode_placement=bindings.encode_placement,
            prepare_owner_header=bindings.unchanged_owner_header)

    def _mark_dirty(self, owner):
        session = self._session_ref()
        table = session._family_bindings.tables.get(owner[0])
        # A removed owner already has an explicit family deletion journal.
        # Routing retirement must not ask changed() to resurrect that header.
        if table is not None and not table._visible(owner[1]):
            if owner[1] not in table._removed:
                raise StoreIntegrityError('retired owner has no family deletion journal')
            return
        session._family_bindings.mark_dirty(owner)

    def synchronize_lazy_placements(self):
        """Reconcile only family-touched compact owners, never the live registry.

        The existing family binders supply complete current owner projections.
        A removed cold owner needs only its checked catalog metadata. This runs
        before shared routing, so pending replacement wins over pinned placement.
        """
        session = self._session_ref()
        coord, registry = self.coordinator, session._registry
        for namespace, table in session._family_bindings.tables.items():
            for key in tuple(table._effective_touched()):
                owner = namespace, key
                changes = coord._owner_changes(owner, ())
                before = {path: old for path, _, old in changes.values() if old is not None}
                placements = []
                if table._visible(key):
                    value = session._family_bindings.load_owner(owner)
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
